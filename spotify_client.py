"""
Spotify API client wrapper with rate limiting and state management.
This routes all requests through the Leaky Bucket rate limiter, preventing 
blocks from Spotify by maintaining safe API usage throughput.
"""
import base64
import time
import requests
import config
import rate_limiter
import app_state as state

class SpotifyAPIError(Exception):
    """Custom exception for Spotify API errors."""
    pass

def retryOnTokenFailure(func):
    """
    Decorator to retry a function call once if a 401 Access Token Expired error occurs.
    This guarantees long-running processes do not crash simply because the 1-hour token expired.
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print(f"   !!! 401 Unauthorized during {func.__name__}. Force refreshing token...")
                self._forceRefreshToken()
                print(f"   !!! Retrying {func.__name__}...")
                return func(self, *args, **kwargs)
            else:
                raise
    return wrapper

class SpotifyClient:
    """
    A wrapper around `requests` that resiliently handles rate limits and session management.
    """
    def __init__(self, isDryRun=False):
        self.session = rate_limiter.createResilientSession(bucket=rate_limiter.spotifyBucket)
        self.isDryRun = isDryRun
        
        self.authSession = rate_limiter.createResilientSession(bucket=None)
        self.accessToken = None
        
        if config.REFRESH_TOKEN:
            self._forceRefreshToken()

    def _get(self, endpoint, params=None):
        """Helper to make GET requests to Spotify API"""
        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {self.accessToken}"} if self.accessToken else {}
        response = self.session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint, payload=None):
        """Helper to make POST requests to Spotify API"""
        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {self.accessToken}"} if self.accessToken else {}
        response = self.session.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _forceRefreshToken(self):
        """
        Manually refresh the access token using the REFRESH_TOKEN.
        """
        try:
            print("Attempting to refresh access token (Explicit Flow)...")
            if not config.REFRESH_TOKEN:
                print("   !!! Error: No REFRESH_TOKEN found in config/env. Cannot refresh.")
                return

            authStr = f"{config.CLIENT_ID}:{config.CLIENT_SECRET}"
            authB64 = base64.b64encode(authStr.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {authB64}"
            }
            
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": config.REFRESH_TOKEN
            }

            response = self.authSession.post("https://accounts.spotify.com/api/token", data=payload, headers=headers)

            if response.status_code == 200:
                tokenInfo = response.json()
                
                self.accessToken = tokenInfo.get('access_token')
                expiresIn = tokenInfo.get('expires_in')
                print(f"   -> Successfully refreshed access token. Expires in: {expiresIn}s")
                
                if 'refresh_token' in tokenInfo and tokenInfo['refresh_token'] != config.REFRESH_TOKEN:
                    print("   !!! WARNING: A new refresh token was issued!")
                    print("   !!! You must update your .env / GitHub Secrets with the new token:")
                    print(f"   {tokenInfo['refresh_token']}")
            else:
                error_msg = f"Error refreshing token: {response.status_code} {response.text}"
                print(f"   !!! {error_msg}")
                raise SpotifyAPIError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network Error refreshing token explicitly: {e}"
            print(f"   !!! {error_msg}")
            raise SpotifyAPIError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected Error refreshing token explicitly: {e}"
            print(f"   !!! {error_msg}")
            raise SpotifyAPIError(error_msg) from e

    @retryOnTokenFailure
    def getCurrentUserId(self):
        """
        Fetches the current user's ID.
        """
        cachedId = state.getMemoryVal("spotifyUserId")
        if cachedId:
            return cachedId
            
        print("Fetching current user profile...")
        userId = self._get("me")['id']
        state.setMemoryVal("spotifyUserId", userId)
        return userId

    @retryOnTokenFailure
    def fetchCurrentUserSavedTracks(self, maxTracks=None, cutoffDate=None, startOffset=0):
        """
        Fetches all liked songs from the user's library.
        This writes them to the local database, respecting a provided offset for resumable chunks.
        
        Args:
            maxTracks (int): Maximum number of tracks to fetch.
            cutoffDate (str): ISO 8601 timestamp. If a track is older than this, stop fetching.
            startOffset (int): Offset to start fetching from (for incremental sync).
        """
        results = []
        if maxTracks:
            limit = min(50, maxTracks)
        else:
            limit = 50 
            
        offset = startOffset
        
        print(f"Fetching liked songs starting from offset {offset}...")
        shouldStopFetching = False
        isFullySynced = False
        
        while True:
            try:
                print(f"   Requesting liked songs batch (offset {offset})...") 
                response = self._get("me/tracks", params={"limit": limit, "offset": offset})
                items = response['items']
                
                if not items:
                    isFullySynced = True 
                    break
                
                for item in items:
                    if cutoffDate and item['added_at'] <= cutoffDate:
                        print(f"   -> Reached previously sync'd track ({item['added_at']}). Stopping fetch.")
                        shouldStopFetching = True
                        isFullySynced = True 
                        break
                        
                    track = item['track']
                    simpleTrack = {
                        'id': track['id'],
                        'name': track['name'],
                        'uri': track['uri'],
                        'addedAt': item['added_at'], 
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name']
                        },
                        'artists': [{'id': a['id'], 'name': a['name']} for a in track['artists']]
                    }
                    results.append(simpleTrack)
                    
                    if maxTracks and len(results) >= maxTracks:
                        shouldStopFetching = True
                        break
                
                offset += len(items) 
                
                if shouldStopFetching:
                    break
                    
                print(f"Fetched {len(results)} songs... (Total offset: {offset})", end='\r')

                if response['next'] is None:
                    isFullySynced = True
                    break
                    
            except Exception as e:
                print(f"\nError fetching songs at offset {offset}: {e}")
                break
                
        print(f"\nTotal liked songs fetched: {len(results)}")
        return results, offset, isFullySynced

    @retryOnTokenFailure
    def createPlaylistForCurrentUser(self, name):
        """
        Creates a new playlist for the current user.
        This ensures unsorted or missing buckets map physically to the user's Spotify account.

        Args:
            name (str): The name of the playlist.
            
        Returns:
            str: The ID of the created playlist.
        """
        if self.isDryRun:
            print(f"   [DRY RUN] Would create playlist '{name}'")
            return f"DRY_RUN_ID_{name}"

        userId = self.getCurrentUserId()
        print(f"Creating new playlist: {name}")
        
        payload = {
            "name": name,
            "description": f"Auto-generated {name} playlist"
        }
        
        playlistId = None
        try:
             print(f"   Requesting creation of playlist '{name}' on Spotify...")
             playlistId = self._post(f"users/{userId}/playlists", payload=payload)['id']
             
        except Exception as e:
             raise SpotifyAPIError(f"Failed to create playlist '{name}': {e}") from e
             
        if playlistId:
            state.cachePlaylist(name, playlistId)
                
        return playlistId

    @retryOnTokenFailure
    def refreshPlaylistCache(self, force=False):
        """
        Fetches all user playlists and caches them into the database.
        
        Args:
            force (bool): If True, ignore DB cache and force fetch from API.
        """
        print("Building playlist cache...")
        
        if not force:
            dbCache = state.getAllCachedPlaylists()
            if dbCache:
                print(f"   Loaded {len(dbCache)} playlists from local database.")
                return

        allPlaylists = []
        limit = 50 
        offset = 0

        userId = self.getCurrentUserId()
        
        while True:
            print(f"   Fetching playlists from Spotify... (offset {offset})")

            response = self._get("me/playlists", params={"limit": limit, "offset": offset})
            
            for pl in response['items']:
                if pl['owner']['id'] == userId:
                    allPlaylists.append(pl)
                
            if not response['next']:
                break
            offset += limit
            
        print(f"\n   Cache built. Found {len(allPlaylists)} playlists. Saving to DB...")
        state.bulkCachePlaylists(allPlaylists)

    @retryOnTokenFailure
    def getOrCreatePlaylist(self, name):
        """
        Finds a playlist by name for the user, or creates it if missing.
        This provides a seamless wrapper so the sync engine does not need to handle creation.
        """
        dbCache = state.getAllCachedPlaylists()
        if not dbCache:
            self.refreshPlaylistCache()
            dbCache = state.getAllCachedPlaylists()
            
        if name in dbCache:
            return dbCache[name]
            
        newId = self.createPlaylistForCurrentUser(name)
             
        return newId

    @retryOnTokenFailure
    def getPlaylistTracks(self, playlistId):
        """
        Fetches all track URIs currently in the playlist.
        This checks the snapshot ID first, completely skipping the heavy API fetch 
        if Spotify confirms the playlist has not been modified.
        """
        if playlistId.startswith("DRY_RUN_ID"):
             return set()

        try:
            response = self._get(f"playlists/{playlistId}", params={"fields": "snapshot_id"})
            currentSnapshot = response['snapshot_id']
            
            storedSnapshot = state.getStoredSnapshotId(playlistId)
                    
            if currentSnapshot == storedSnapshot:
                print(f"Snapshot match for {playlistId} ({currentSnapshot[:8]}...). Loading from DB.")
                return state.getSnapshotTracks(playlistId)
                
            existingUris = set()
            limit = 100 
            offset = 0
            
            print(f"Snapshot changed or new. Fetching tracks for {playlistId}...")
            
            while True:
                print(f"   Requesting playlist items for {playlistId} (offset {offset})...")
                response = self._get(f"playlists/{playlistId}/items", params={"fields": "items(track(uri)),next", "limit": limit, "offset": offset})
                items = response['items']
                
                for item in items:
                    if item and item.get('track'):
                        existingUris.add(item['track']['uri'])
                
                if offset > 0:
                     print(f"   Fetching playlist tracks... ({len(existingUris)} found)", end='\r')

                if not response['next']:
                    break
                offset += limit
                
            if not self.isDryRun:
                state.updateSnapshotId(playlistId, currentSnapshot)
                state.replaceSnapshotTracks(playlistId, existingUris)
                
            return existingUris

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"   !!! Playlist {playlistId} not found (404). Invalidating cache...")
                state.deletePlaylistCache(playlistId)
                return set() 
            else:
                raise

    @retryOnTokenFailure
    def addUniqueTracksToPlaylist(self, playlistId, trackUris, onBatchSuccess=None):
        """
        Adds ONLY missing tracks to the playlist.
        This inherently prevents track duplication by calculating the diff 
        against the local snapshot before issuing any POST requests.
        
        Args:
            playlistId: Target playlist.
            trackUris: List of track URIs to add.
            onBatchSuccess (callable, optional): Function to call with list of added URIs 
                                                   after each successful batch.
        """
        if not trackUris:
            return        
        
        uniqueTrackUris = list(dict.fromkeys(trackUris))
        
        existingUrisInPlaylist = self.getPlaylistTracks(playlistId)        
        if existingUrisInPlaylist is None:
            existingUrisInPlaylist = set()
            
        toAdd = [uri for uri in uniqueTrackUris if uri not in existingUrisInPlaylist]
        
        if not toAdd:
            print("   -> No new tracks to add.")
            return

        if self.isDryRun:
            print(f"   [DRY RUN] Would add {len(toAdd)} new tracks to {playlistId}...")
            return

        validUris = []
        for uri in toAdd:
            if isinstance(uri, str) and uri.startswith("spotify:track:"):
                validUris.append(uri)
            else:
                print(f"   Warning: Skipping invalid/local URI: {uri}")
        
        if not validUris:
            print("   -> No valid tracks to add after filtering.")
            return

        print(f"   -> Adding {len(validUris)} new tracks...")
        
        def _addBatchWithFallback(batch):
            if not batch:
                return 0
                
            try:
                payload = {"uris": batch}
                if len(batch) > 1:
                     print(f"   Requesting to add batch of {len(batch)} tracks to {playlistId}...")
                response = self._post(f"playlists/{playlistId}/items", payload=payload)
                
                if not self.isDryRun:
                    if 'snapshot_id' in response:
                        state.updateSnapshotId(playlistId, response['snapshot_id'])
                    currentSnapshotTracks = state.getSnapshotTracks(playlistId)
                    currentSnapshotTracks.update(batch)
                    state.replaceSnapshotTracks(playlistId, currentSnapshotTracks)
                
                if onBatchSuccess:
                    try:
                        onBatchSuccess(batch)
                    except Exception as e:
                        print(f"   Warning: Checkpoint callback failed: {e}")
                        
                return len(batch)
                
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 400:
                    if len(batch) == 1:
                         badUri = batch[0]
                         print(f"\n   !!! 400 Bad Request on single URI: {badUri}")
                         print(f"   !!! Marking {badUri} as invalid in local database to prevent future sync failures.")
                         if not self.isDryRun:
                             state.markTrackInvalid(badUri)
                         return 0
                    
                    print(f"   !!! 400 Bad Request on batch of {len(batch)}. Splitting to isolate invalid URI(s)...")
                    mid = len(batch) // 2
                    leftBatch = batch[:mid]
                    rightBatch = batch[mid:]
                    
                    addedCount = 0
                    addedCount += _addBatchWithFallback(leftBatch)
                    addedCount += _addBatchWithFallback(rightBatch)
                    return addedCount
                    
                elif e.response is not None and e.response.status_code == 404:
                    print(f"\n   !!! 404 Not Found adding batch to {playlistId}. Playlist likely deleted.")
                    print("   !!! Invalidating cache and retrying setup...")
                    
                    state.deletePlaylistCache(playlistId)
                    
                    print("   !!! State cleaned. Please run script again to recreate playlist.")
                    raise 
                else:
                    print(f"   Error adding batch to {playlistId}: {e}")
                    raise
            except Exception as e:
                print(f"\nError adding batch to {playlistId}: {e}")
                raise

        batchSize = 100 
        totalAdded = 0
        
        for i in range(0, len(validUris), batchSize):
            batch = validUris[i : i + batchSize]
            try:
                addedThisBatch = _addBatchWithFallback(batch)
                totalAdded += addedThisBatch
                if len(batch) > 1 and addedThisBatch > 0:
                     print(f"   -> Successfully processed batch {i//batchSize + 1} ({addedThisBatch} new songs synced)...")
            except Exception as e:
                 print(f"   -> Sync for playlist {playlistId} halted due to error.")
                 break
