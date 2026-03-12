"""
Main entry point for the Spotify Liked Songs Organiser application.
This exposes a robust, interactive CLI menu mapping to operations 1-8, 
orchestrating changes across the local SQLite database state and the Spotify API.
"""
import config
import app_state as state
import auth_helper
import lastfm_client
import sorter
from spotify_client import SpotifyClient

def op1Authenticate():
    """Operation 1: Initiates the manual OAuth authentication flow to generate a Spotify Refresh Token."""
    print("\n--- Operation 1: Authenticate ---")
    auth_helper.generateToken()

def op2FetchLikedSongs():
    """Operation 2: Fetches liked songs from Spotify and saves them to the local database."""
    print("\n--- Operation 2: Fetch Liked Songs ---")
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    maxInput = input("How many tracks to fetch? (Enter for all): ").strip()
    maxTracks = int(maxInput) if maxInput.isdigit() else None
    
    startOffset = state.getMemoryVal("likedSongsOffset", 0)
    if startOffset is not None:
        startOffset = int(startOffset)
        
    if startOffset > 0:
         print(f"Resuming from previous offset: {startOffset}")
         
    results, newOffset, isFullySynced = client.fetchCurrentUserSavedTracks(
        maxTracks=maxTracks, 
        startOffset=startOffset
    )
    
    if results:
        state.saveLikedSongs(results)
        print(f"Saved {len(results)} tracks to database.")
        
    state.setMemoryVal("likedSongsOffset", newOffset)
    
    if isFullySynced:
        print("Finished syncing all liked songs.")

def op3FetchLastfmTags():
    """Operation 3: Retrieves genre tags from Last.fm for tracks missing metadata in the database."""
    print("\n--- Operation 3: Fetch Last.fm Tags ---")
    
    limit = config.MAX_TRACKS_TO_PROCESS
    tracks = state.getTracksMissingTags(limit=limit)
    if not tracks:
        print("All tracks have Last.fm tags.")
        return
        
    print(f"Fetching tags for {len(tracks)} tracks...")
    
    tagsMap = lastfm_client.enrichTracks(tracks)
    
    print("\nSaving tags to database...")
    savedCount = 0
    for trackUri, tags in tagsMap.items():
        state.updateTrackTags(trackUri, tags)
        savedCount += 1
        
    print(f"Finished fetching Last.fm tags for {savedCount} tracks.")

def op4SortSongs():
    """Operation 4: Classifies unclassified tracks into genre buckets based on their Last.fm tags."""
    print("\n--- Operation 4: Sort Songs ---")
    
    tracks = state.getUnclassifiedTracks()
    if not tracks:
        print("No unclassified tracks found or all tracks are already ranked.")
        return
        
    print(f"Sorting {len(tracks)} tracks into buckets...")
    
    trackBucketsMap = sorter.categoriseTracks(tracks)
    
    for trackUri, buckets in trackBucketsMap.items():
        state.updateTrackSorting(trackUri, buckets)
        
    print(f"Finished sorting {len(trackBucketsMap)} tracks.")

def op5FetchUserPlaylists():
    """Operation 5: Synchronises the local cache of the user's Spotify playlists."""
    print("\n--- Operation 5: Fetch User Playlists ---")
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    client.refreshPlaylistCache(force=True)
    
    playlists = state.getAllCachedPlaylists()
    print(f"Successfully cached {len(playlists)} user playlists.")

def op6CreateMissingPlaylists():
    """Operation 6: Identifies and creates playlists on Spotify that exist in config but not on the account."""
    print("\n--- Operation 6: Create Missing Playlists ---")
    
    expectedPlaylists = list(config.GENRE_MAPPING.keys())
        
    cachedPlaylists = state.getAllCachedPlaylists()
    
    missingPlaylists = [name for name in expectedPlaylists if name not in cachedPlaylists]
    
    if not missingPlaylists:
        print("All configured playlists already exist in the database cache.")
        return
        
    print(f"Found {len(missingPlaylists)} missing playlists. These will be created on Spotify:")
    for p in missingPlaylists:
        print(f" - {p}")
        
    confirm = input("Proceed with creating these playlists? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
        
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    for name in missingPlaylists:
        client.createPlaylistForCurrentUser(name)
        
    print(f"Finished creating {len(missingPlaylists)} missing playlists.")

def _selectPlaylist(promptText):
    """Helper to select a playlist from the cache interactively."""
    playlists = state.getAllCachedPlaylists()
    if not playlists:
        print("No playlists found in local cache. Run Operation 5 first.")
        return None, None
        
    print("\nAvailable Playlists:")
    names = list(playlists.keys())
    names.sort()
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")
        
    choice = input(f"{promptText} (Enter 1-{len(names)}, or 'all'): ").strip().lower()
    
    if choice == 'all':
        return 'all', playlists
        
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            name = names[idx]
            return name, playlists[name]
            
    print("Invalid selection.")
    return None, None

def op7SnapshotPlaylist():
    """Operation 7: Records a local snapshot of tracks currently in a Spotify playlist."""
    print("\n--- Operation 7: Snapshot Playlist ---")
    
    name, playlistData = _selectPlaylist("Select a playlist to snapshot")
    if not name:
        return
        
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    if name == 'all':
        playlists = playlistData
        print(f"Snapshotting all {len(playlists)} playlists...")
        for plName, plId in playlists.items():
            print(f"\nSnapshotting '{plName}'...")
            client.getPlaylistItems(plId)
        print("\nFinished snapshotting all playlists.")
    else:
        playlistId = playlistData
        print(f"Snapshotting '{name}'...")
        client.getPlaylistItems(playlistId)
        print("Snapshot complete.")

def op8SyncAndAddSongs():
    """Operation 8: Pushes sorted tracks from the local database to their respective Spotify playlists."""
    print("\n--- Operation 8: Sync & Add Songs ---")
    
    name, playlistData = _selectPlaylist("Select a playlist to sync songs to")
    if not name:
        return
        
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    def syncSinglePlaylist(plName, plId):
        print(f"\nSyncing '{plName}'...")
        
        targetUris = state.getTracksForPlaylist(plName)
        if not targetUris:
            print(f"No sorted tracks found for '{plName}' in the local database.")
            return
            
        print(f"Found {len(targetUris)} target tracks in local DB for '{plName}'.")
        
        client.addUniqueTracksToPlaylist(plId, targetUris)
        
    if name == 'all':
        playlists = playlistData
        print(f"Syncing all {len(playlists)} playlists...")
        for plName, plId in list(playlists.items()):
            syncSinglePlaylist(plName, plId)
        print("\nFinished syncing all playlists.")
    else:
        syncSinglePlaylist(name, playlistData)
        print("\nSync complete.")

def printMenu():
    """Displays the main interactive menu for the Spotify Liked Songs Organiser."""
    print("\n" + "="*40)
    print(" Spotify Liked Songs Organiser CLI")
    print("="*40)
    print("1. Authenticate")
    print("2. Fetch Liked Songs")
    print("3. Fetch Last.fm Tags")
    print("4. Sort Songs")
    print("5. Fetch User Playlists")
    print("6. Create Missing Playlists")
    print("7. Snapshot Playlist")
    print("8. Sync & Add Songs")
    print("0. Exit")
    print("="*40)

def mainLoop():
    """
    Executes the main interactive loop of the Spotify Liked Songs Organiser.
    This maintains the terminal UI running indefinitely until explicit exit.
    """
    print("Starting Spotify Liked Songs Organiser...")
    state.initDb() 
    
    if config.IS_DRY_RUN:
        print(">>> DRY RUN MODE ENABLED <<<")
    if config.SHOULD_STOP_AFTER_FIRST_MATCH:
        print(">>> SORT AFTER FIRST MATCH ENABLED <<<")
    if config.SHOULD_RESET_PLAYLIST_CACHE:
        print(">>> RESET PLAYLIST CACHE ENABLED <<<")

    while True:
        printMenu()
        choice = input("Select an operation (0-8): ").strip()

        if choice == '0':
            print("Exiting...")
            break
        elif choice == '1':
            op1Authenticate()
        elif choice == '2':
            op2FetchLikedSongs()
        elif choice == '3':
            op3FetchLastfmTags()
        elif choice == '4':
            op4SortSongs()
        elif choice == '5':
            op5FetchUserPlaylists()
        elif choice == '6':
            op6CreateMissingPlaylists()
        elif choice == '7':
            op7SnapshotPlaylist()
        elif choice == '8':
            op8SyncAndAddSongs()
        else:
            print("Invalid selection. Please enter a number between 0 and 8.")

if __name__ == "__main__":
    mainLoop()
