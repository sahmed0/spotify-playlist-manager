"""
Main entry point for the Spotify Sorter application.
"""
import config
import state
from spotify_client import SpotifyClient
from sorter import categorise_tracks
from lastfm_client import LastFMClient
import time
from datetime import datetime, timezone, timedelta


def main():
    """
    Execute the main logic of the Spotify Sorter.

    Authenticates with Spotify, fetches liked songs, retrieves genre tags from Last.fm,
    sorts songs into playlists, and syncs changes to Spotify.
    """
    print("Starting Spotify Sorter...")
    
    # Check for Dry Run
    if config.DRY_RUN:
        print(">>> DRY RUN MODE ENABLED <<<")

    # 1. Load State
    last_run = state.load_state()
    if last_run:
        print(f"Last sync detected: {last_run}")
        print("Checking for new songs only...")
    else:
        print("No previous state found. Running full sync.")
    try:
        client = SpotifyClient(dry_run=config.DRY_RUN)
        user_id = client.get_current_user_id()
        print(f"Authenticated as user: {user_id}")
        
        # Build cache immediately as requested
        # Check if we should force refresh (e.g. if user added playlists manually outside the script)
        force_refresh = getattr(config, 'RESET_PLAYLIST_CACHE', False)
        client.refresh_playlist_cache(force=force_refresh)
        
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # 2. Fetch Liked Songs
    # Determine max tracks based on config
    max_tracks = config.MAX_TRACKS_TO_PROCESS
    
    # If Dry Run is enabled and no specific limit is set, default to 10 for safety
    if config.DRY_RUN and max_tracks is None:
        max_tracks = 10

    # Incremental Sync Setup
    start_offset = 0
    if not last_run:
        start_offset = state.get_sync_offset()
        if start_offset > 0:
            print(f"Resuming initial sync from offset {start_offset}...")
        
    liked_songs, new_offset, fully_synced = client.fetch_current_user_saved_tracks(
        max_tracks=max_tracks, 
        cutoff_date=last_run,
        start_offset=start_offset
    )
    
    if not liked_songs:
        print("No (new) liked songs found in this batch.")
        if fully_synced:
             print("Library scan complete.")
    
    # Filter for incremental sync
    new_songs = []
    latest_timestamp = last_run or "1970-01-01T00:00:00Z"
    processed_tracks = state.get_processed_tracks()
    skipped_count = 0
    
    for song in liked_songs:
        if state.is_track_newer(song['added_at'], last_run):
            # Persistence Check: Skip if already processed
            if song['uri'] in processed_tracks:
                skipped_count += 1
                continue
                
            new_songs.append(song)
            # Track the max timestamp we see
            if song['added_at'] > latest_timestamp:
                latest_timestamp = song['added_at']
    
    if skipped_count > 0:
        print(f"Skipped {skipped_count} songs already processed.")
    
    if not new_songs:
        print("No (new) songs to sort in this batch.")
        # Fall through to allow saving state if needed
        
    print(f"Found {len(new_songs)} new songs to sort.")

    if config.DRY_RUN:
       print(">>> DRY RUN: Processing limited to fetched songs (max 10) <<<")

    # 3. Fetch Genres (via Last.fm - Track Tags > Artist Tags)
    print("Fetching tags from Last.fm (Track -> Artist fallback)...")
    
    # Store tags per song URI (most specific)
    track_tags_map = {}
    
    try:
        lastfm = LastFMClient()
        total_songs = len(new_songs)
        
        for i, song in enumerate(new_songs):
            song_name = song['name']
            # Use primary artist for simplicity
            primary_artist = song['artists'][0]['name'] if song['artists'] else "Unknown"
            
            # 1. Try Track Tags
            tags = lastfm.fetch_track_tags(primary_artist, song_name)
            source = "Track"
            
            # 2. Fallback to Artist Tags
            if not tags:
                # Check DB Cache first
                cached_tags = state.get_artist_tags(primary_artist)
                if cached_tags is not None:
                     tags = cached_tags
                     source = "Artist (DB Cache)"
                else:
                    # Fetch from API
                    tags = lastfm.fetch_artist_tags(primary_artist)
                    # Update DB Cache
                    state.save_artist_tags(primary_artist, tags)
                    source = "Artist (API)"
            
            track_tags_map[song['uri']] = tags
            print(f"[{i+1}/{total_songs}] {song_name} ({primary_artist}) -> {source}: {tags[:3]}...", end='\r')
            
        print("\nLast.fm tagging complete.")

    except Exception as e:
        print(f"\nLast.fm Error: {e}")
        track_tags_map = {}

    # 4. Sort Songs
    print("Sorting songs into buckets...")
    
    sorted_playlists = categorise_tracks(new_songs, track_tags_map)
    
    # 5. Review & Sync
    total_sorted = 0
    for bucket, songs in sorted_playlists.items():
        count = len(songs)
        total_sorted += count
        print(f"Bucket '{bucket}': {count} songs")
        
    print(f"Total playlist placements: {total_sorted}")
    print(f"Unique songs sorted: {len(new_songs)}")
    
    # Sync to Spotify
    print("\nSyncing to Spotify Playlists...")
    if config.DRY_RUN:
        print(">>> DRY RUN MODE ENABLED: No changes will be made to Spotify. <<<")
    
    all_processed_uris = set()

    for bucket, songs in sorted_playlists.items():
        if not songs:
            continue
            
        print(f"Syncing '{bucket}'... ({len(songs)} songs)")
        
        # Get playlist ID (create if needed)
        playlist_id = client.get_or_create_playlist(bucket)
        
        # Get list of URIs
        track_uris = [s['uri'] for s in songs]
        
        # Update playlist (Safe Mode: Adds only missing tracks)
        client.add_unique_tracks_to_playlist(playlist_id, track_uris)
        
        # Keep track of what we've handled
        for uri in track_uris:
            all_processed_uris.add(uri)

    # Handling for Unsorted playlist - we also consider these "processed" 
    unsorted_songs = sorted_playlists.get(config.UNSORTED_PLAYLIST_NAME, [])
    for s in unsorted_songs:
        all_processed_uris.add(s['uri'])
    
    # Save State (Only if not Dry Run)
    if not config.DRY_RUN:
        # 1. Update Processed Tracks (Always safe)
        if all_processed_uris:
            print(f"Marking {len(all_processed_uris)} tracks as processed in DB...")
            state.bulk_mark_tracks_as_processed(list(all_processed_uris))

        # 2. Update Sync State
        if fully_synced:
             print("\nInitial library sync complete! You are now up to date.")
             
             # SAFETY: Set the last_run timestamp to 7 days ago instead of NOW.
             # This ensures the next "Maintenance Run" scans the last week of history,
             # catching any songs the user might have added while the initial sync was running.
             safe_checkpoint = datetime.now(timezone.utc) - timedelta(days=7)
             state.save_state(safe_checkpoint.isoformat())
             state.clear_sync_offset() # Done with offset
        elif new_offset > 0:
             # If we advanced the offset
             print(f"\nPartial sync complete. Saved progress at offset {new_offset}. Run again to continue.")
             state.save_sync_offset(new_offset)
        
    # 6. Logging Unclassified Songs
    unclassified_songs = sorted_playlists.get(config.UNSORTED_PLAYLIST_NAME, [])
    if unclassified_songs:
        print(f"Logging {len(unclassified_songs)} unclassified songs...")
        state.log_unclassified_songs(unclassified_songs)

    print("\nAll done! Enjoy your organized library.")



if __name__ == "__main__":
    main()
