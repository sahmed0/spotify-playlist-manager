"""
Logic for categorisation of tracks based on genre mapping.
This ensures tracks are correctly assigned to logical buckets, allowing 
the system to group disparate Last.fm tags into unified Spotify playlists.
"""
import config

def categoriseTracks(tracks):
    """
    Sorts a list of tracks into buckets based on config.GENRE_MAPPING.
    This provides the core logic to map raw metadata into actionable groupings.

    Args:
        tracks: List of dicts, each representing a track from the database.
                Must have 'trackUri' and 'lastfmTags'.

    Returns:
        Dict: { 'trackUri': ['Bucket Name', ...], ... }
    """
    trackBucketsMap = {}
    
    for track in tracks:
        trackUri = track['trackUri']
        # Ensures comparison ignores case and whitespace for reliable mapping.
        currentGenres = [g.lower().strip() for g in track.get('lastfmTags', [])]
        
        hasMatchedAny = False
        assignedBuckets = []

        for bucketName, keywords in config.GENRE_MAPPING.items():
            hasMatch = False
            for keyword in keywords:
                # Seek a direct match within the specific tag list to avoid fuzzy overlaps.
                if keyword.lower().strip() in currentGenres:
                    hasMatch = True
                    break
            
            if hasMatch:
                assignedBuckets.append(bucketName)
                hasMatchedAny = True
                if config.SHOULD_STOP_AFTER_FIRST_MATCH:
                    break
        
        if not hasMatchedAny:
            assignedBuckets.append(config.UNSORTED_PLAYLIST_NAME)
            
        trackBucketsMap[trackUri] = assignedBuckets
            
    return trackBucketsMap
