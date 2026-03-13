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
import time
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
    
    # Only use incremental sync cutoff if we have previously reached the very end of the library.
    # Otherwise, we might have "gaps" in the older part of the library that need filling.
    isTailComplete = state.getMemoryVal("libraryTailComplete") == "1"
    cutoffDate = state.getLatestTrackTimestamp() if isTailComplete else None
    
    if cutoffDate:
        print(f"Using incremental sync (cutoff: {cutoffDate})")
    elif isTailComplete:
        print("Initialising full sync (tail is complete, but no cutoff date found)...")
    else:
        print("Using full library fetch (tail is not yet complete)...")
         
    startTime = time.time()
    results, newOffset, isEndOfLibrary, wasCutoffReached = client.fetchCurrentUserSavedTracks(
        maxTracks=maxTracks, 
        startOffset=startOffset,
        cutoffDate=cutoffDate
    )
    endTime = time.time()
    
    duration = endTime - startTime
    minutes = int(duration // 60)
    seconds = duration % 60
    
    if minutes > 0:
        timeStr = f"{minutes}m {seconds:.2f}s"
    else:
        timeStr = f"{seconds:.2f}s"
    
    if isEndOfLibrary:
        print("Reached the end of your Spotify Liked Songs library.")
        state.setMemoryVal("libraryTailComplete", 1)
        
    if isEndOfLibrary or wasCutoffReached:
        print("Sync session finished.")
        state.setMemoryVal("likedSongsOffset", 0) # Reset offset for next sync

    print(f"\nFinished fetching liked songs session.")
    print(f"Time taken: {timeStr}")

def op3FetchLastfmTags():
    """Operation 3: Retrieves genre tags from Last.fm for tracks missing metadata in the database."""
    print("\n--- Operation 3: Fetch Last.fm Tags ---")
    
    limit = config.MAX_TRACKS_TO_PROCESS
    tracks = state.getTracksMissingTags(limit=limit)
    if not tracks:
        print("All tracks have Last.fm tags.")
        return
        
    print(f"Fetching tags for {len(tracks)} tracks...")
    
    startTime = time.time()
    lastfm_client.enrichTracks(tracks)
    endTime = time.time()
    
    duration = endTime - startTime
    minutes = int(duration // 60)
    seconds = duration % 60
    
    if minutes > 0:
        timeStr = f"{minutes}m {seconds:.2f}s"
    else:
        timeStr = f"{seconds:.2f}s"
        
    print(f"\nFinished fetching Last.fm tags for {len(tracks)} tracks.")
    print(f"Time taken: {timeStr}")

def op4SortSongs():
    """Operation 4: Classifies unclassified tracks into genre buckets based on their Last.fm tags."""
    print("\n--- Operation 4: Sort Songs ---")
    
    unclassifiedCount = state.countUnclassifiedTracks()
    if unclassifiedCount == 0:
        print("No new unclassified tracks found.")
        return

    print(f"Categorising {unclassifiedCount} tracks based on Last.fm tags...")
    
    batchSize = 500
    totalProcessed = 0
    # Safety mechanism to prevent infinite loops if DB updates fail
    maxBatches = (unclassifiedCount // batchSize) + 10
    batchCount = 0
    
    while batchCount < maxBatches:
        tracks = state.getUnclassifiedTracks(limit=batchSize, offset=0)
        if not tracks:
            break
            
        print(f" Processing batch of {len(tracks)} tracks ({totalProcessed}/{unclassifiedCount})...")
        results = sorter.categoriseTracks(tracks)
        
        if not results:
             print("   Warning: Batch processing returned no results. Breaking to avoid loop.")
             break

        for trackUri, buckets in results.items():
            state.updateTrackSorting(trackUri, buckets)
            totalProcessed += 1
            
        batchCount += 1
        if len(tracks) < batchSize:
            break
            
    if totalProcessed == 0:
        print("No tracks were processed.")
    else:
        print(f"Finished. Categorised {totalProcessed} tracks.")

def op5FetchUserPlaylists():
    """Operation 5: Synchronises the local cache of the user's Spotify playlists."""
    print("\n--- Operation 5: Fetch User Playlists ---")
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    startTime = time.time()
    client.refreshPlaylistCache(force=True)
    endTime = time.time()
    
    duration = endTime - startTime
    minutes = int(duration // 60)
    seconds = duration % 60
    
    if minutes > 0:
        timeStr = f"{minutes}m {seconds:.2f}s"
    else:
        timeStr = f"{seconds:.2f}s"
    
    playlists = state.getAllCachedPlaylists()
    print(f"Successfully cached {len(playlists)} user playlists.")
    print(f"Time taken: {timeStr}")

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
    startTime = time.time()
    for name in missingPlaylists:
        client.createPlaylistForCurrentUser(name)
    endTime = time.time()
    
    duration = endTime - startTime
    minutes = int(duration // 60)
    seconds = duration % 60
    
    if minutes > 0:
        timeStr = f"{minutes}m {seconds:.2f}s"
    else:
        timeStr = f"{seconds:.2f}s"
        
    print(f"Finished creating {len(missingPlaylists)} missing playlists.")
    print(f"Time taken: {timeStr}")

def _selectPlaylist(promptText):
    """
    Helper to select one or more playlists from the cache interactively.
    Returns a dictionary of {name: playlist_id} for selected playlists.
    """
    playlists = state.getAllCachedPlaylists()
    if not playlists:
        print("No playlists found in local cache. Run Operation 5 first.")
        return {}
        
    print("\nAvailable Playlists:")
    names = list(playlists.keys())
    names.sort()
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")
        
    choice = input(f"{promptText} (Enter 1-{len(names)}, e.g. '1, 5', or 'all'): ").strip().lower()
    
    if choice == 'all':
        return playlists
        
    selected = {}
    parts = [p.strip() for p in choice.split(',')]
    for part in parts:
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(names):
                name = names[idx]
                selected[name] = playlists[name]
            else:
                print(f"Warning: Index {part} is out of range and will be skipped.")
        elif part:
            print(f"Warning: '{part}' is not a valid number and will be skipped.")
            
    if not selected:
        print("No valid selection made.")
        
    return selected

def op7SnapshotPlaylist():
    """Operation 7: Records local snapshots of tracks currently in Spotify playlists."""
    print("\n--- Operation 7: Snapshot Playlist ---")
    
    selectedPlaylists = _selectPlaylist("Select playlists to snapshot")
    if not selectedPlaylists:
        return
        
    client = SpotifyClient(isDryRun=config.IS_DRY_RUN)
    
    print(f"Snapshoting {len(selectedPlaylists)} playlist(s)...")
    for name, playlistId in selectedPlaylists.items():
        print(f"\nSnapshotting '{name}'...")
        client.getPlaylistItems(playlistId)
        
    print("\nSnapshotting complete.")

def op8SyncAndAddSongs():
    """Operation 8: Pushes sorted tracks from the local database to respective Spotify playlists."""
    print("\n--- Operation 8: Sync & Add Songs ---")
    
    selectedPlaylists = _selectPlaylist("Select playlists to sync songs to")
    if not selectedPlaylists:
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
        
    startTime = time.time()
    
    print(f"Syncing {len(selectedPlaylists)} playlist(s)...")
    for name, playlistId in selectedPlaylists.items():
        syncSinglePlaylist(name, playlistId)
        
    endTime = time.time()
    
    duration = endTime - startTime
    minutes = int(duration // 60)
    seconds = duration % 60
    
    if minutes > 0:
        timeStr = f"{minutes}m {seconds:.2f}s"
    else:
        timeStr = f"{seconds:.2f}s"

    print(f"\nSync complete. Total time taken: {timeStr}")

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
    if config.MAX_GENRE_PLAYLISTS_PER_SONG is not None:
        print(f">>> MAX GENRE PLAYLISTS PER SONG: {config.MAX_GENRE_PLAYLISTS_PER_SONG} <<<")
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
