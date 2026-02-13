import config

def get_track_genres(track_artists, artist_genres_map, track_album=None, album_genres_map=None):
    """
    Combines all genres from a track's artists into a single set.
    """
    genres = set()
    for artist_id in track_artists:
        if artist_id in artist_genres_map:
            genres.update(artist_genres_map[artist_id])
    
    # 2026 Fallback: If no artist genres found, try album genres
    if not genres and track_album and album_genres_map:
        album_id = track_album.get('id')
        if album_id and album_id in album_genres_map:
            genres.update(album_genres_map[album_id])
            
    return genres

def categorize_tracks(tracks, artist_genres_map, album_genres_map=None):
    """
    Sorts a list of tracks into buckets based on config.GENRE_MAPPING.
    
    Args:
        tracks: List of dicts, each must have 'name', 'id', 'artists' (list of IDs), 'album' (dict with id).
        artist_genres_map: Dict mapping artist_id -> list of genre strings.
        album_genres_map: Dict mapping album_id -> list of genre strings (optional).
        
    Returns:
        Dict: { 'Bucket Name': [track_object, ...], ... }
    """
    # Initialise buckets
    sorted_playlists = {bucket: [] for bucket in config.GENRE_MAPPING.keys()}
    sorted_playlists[config.UNSORTED_PLAYLIST_NAME] = []
    
    # Safety
    if album_genres_map is None:
        album_genres_map = {}

    for track in tracks:
        track_name = track.get('name', 'Unknown')
        artist_ids = [artist['id'] for artist in track.get('artists', [])]
        track_album = track.get('album', {})
        
        # Get all genres for this track (from all its artists, maybe album)
        current_genres = get_track_genres(artist_ids, artist_genres_map, track_album, album_genres_map)
                
        # Flatten into a single string for easy substring matching
        # e.g. "rock classic rock pop"
        flat_genre_string = " ".join(current_genres).lower()
        
        matched_any = False

        for bucket_name, keywords in config.GENRE_MAPPING.items():
            # Check if any keyword for this bucket matches the track's genres
            match_found = False
            for keyword in keywords:
                if keyword in flat_genre_string:
                    match_found = True
                    break
            
            if match_found:
                sorted_playlists[bucket_name].append(track)
                matched_any = True
                
                # If STOP_AFTER_FIRST_MATCH is True, we stop after the first bucket match
                if config.STOP_AFTER_FIRST_MATCH:
                    break
        
        # If no buckets matched at all, add to Fallback
        if not matched_any:
            sorted_playlists[config.UNSORTED_PLAYLIST_NAME].append(track)
            
    return sorted_playlists
