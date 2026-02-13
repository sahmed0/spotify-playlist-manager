import config
import state
from spotify_client import SpotifyClient
from sorter import categorize_tracks

def main():
    print("Starting Spotify Sorter...")
    
    # Check for Dry Run
    if config.DRY_RUN:
        print(">>> DRY RUN MODE ENABLED <<<")

    # 0. Load State
    last_run = state.load_state()
    if last_run:
        print(f"Last sync detected: {last_run}")
        print("Checking for new songs only...")
    else:
        print("No previous state found. Running full sync.")
    try:
        client = SpotifyClient()
        user_id = client.get_current_user_id()
        print(f"Authenticated as user: {user_id}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # 2. Fetch Liked Songs
    liked_songs = client.fetch_current_user_saved_tracks()
    if not liked_songs:
        print("No liked songs found.")
        return

    # Filter for incremental sync
    new_songs = []
    latest_timestamp = last_run or "1970-01-01T00:00:00Z"
    
    for song in liked_songs:
        if state.is_track_newer(song['added_at'], last_run):
            new_songs.append(song)
            # Track the max timestamp we see
            if song['added_at'] > latest_timestamp:
                latest_timestamp = song['added_at']
    
    if not new_songs:
        print("No new songs found since last run.")
        return
        
    print(f"Found {len(new_songs)} new songs to sort.")

    # 3. Fetch Artist Genres
    # Collect all artist IDs from the songs
    all_artist_ids = set()
    for song in new_songs:
        for artist in song['artists']:
            all_artist_ids.add(artist['id'])
            
    artist_genres_map = client.fetch_artist_genres_in_batches(list(all_artist_ids))

    # 3.5. Fallback for Missing Genres (2026 Update)
    # Check which tracks have NO artist genres found
    album_ids_to_fetch = set()
    for song in new_songs:
        has_genres = False
        for artist in song['artists']:
            if artist_genres_map.get(artist['id']):
                has_genres = True
                break
        
        if not has_genres:
            # This track has no artist genres, try album genres
            if song.get('album') and song['album'].get('id'):
                album_ids_to_fetch.add(song['album']['id'])
                
    album_genres_map = {}
    if album_ids_to_fetch:
        print(f"Found {len(album_ids_to_fetch)} albums to check for fallback genres...")
        album_genres_map = client.fetch_album_genres_in_batches(list(album_ids_to_fetch))

    # 4. Sort Songs
    print("Sorting songs into buckets...")
    sorted_playlists = categorize_tracks(new_songs, artist_genres_map, album_genres_map)
    
    # 5. Review & Sync
    total_sorted = 0
    for bucket, songs in sorted_playlists.items():
        count = len(songs)
        total_sorted += count
        print(f"Bucket '{bucket}': {count} songs")
        
    print(f"Total songs processed for sorting: {total_sorted}")
    
    # Sync to Spotify
    print("\nSyncing to Spotify Playlists...")
    if config.DRY_RUN:
        print(">>> DRY RUN MODE ENABLED: No changes will be made to Spotify. <<<")

    for bucket, songs in sorted_playlists.items():
        if not songs:
            continue
            
        print(f"Syncing '{bucket}'... ({len(songs)} songs)")
        
        if config.DRY_RUN:
            print(f"   [DRY RUN] Would create/find playlist '{bucket}'")
            print(f"   [DRY RUN] Would add {len(songs)} songs.")
            continue

        # Get playlist ID (create if needed)
        playlist_id = client.get_or_create_playlist(user_id, bucket)
        
        # Get list of URIs
        track_uris = [s['uri'] for s in songs]
        
        # Update playlist (Safe Mode: Adds only missing tracks)
        if config.DRY_RUN:
             print(f"   [DRY RUN] Would call add_unique_tracks_to_playlist for {bucket}")
        else:
             client.add_unique_tracks_to_playlist(playlist_id, track_uris)
        
    # Save State (Only if not Dry Run)
    if not config.DRY_RUN and new_songs:
        print(f"\nSaving new state (Timestamp: {latest_timestamp})")
        state.save_state(latest_timestamp)
        
    # 6. Logging Unclassified Songs (2026 Update)
    unclassified_songs = sorted_playlists.get(config.UNSORTED_PLAYLIST_NAME, [])
    if unclassified_songs:
        print(f"Logging {len(unclassified_songs)} unclassified songs...")
        log_unclassified_songs(unclassified_songs)

    print("\nAll done! Enjoy your organized library.")

def log_unclassified_songs(songs):
    """
    Appends details of unclassified songs to a persistent log file.
    """
    log_file = "logs/unclassified_songs.log"
    import os
    import datetime
    
    # Ensure logs dir exists
    os.makedirs("logs", exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_file, "a", encoding="utf-8") as f:
        for song in songs:
            name = song.get('name', 'Unknown')
            artist_names = ", ".join([a['name'] for a in song.get('artists', [])])
            f.write(f"[{timestamp}] Song: \"{name}\" - Artist: \"{artist_names}\" (Details: No genres matched)\n")

if __name__ == "__main__":
    main()
