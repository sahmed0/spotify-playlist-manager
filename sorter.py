"""
Logic for categorisation of tracks based on genre mapping.
This ensures tracks are correctly assigned to logical buckets, allowing 
the system to group disparate Last.fm tags into unified Spotify playlists.
"""
from thefuzz import fuzz
import config

# Threshold for similarity score (0-100). Use test_thresholds.py to find the optimal threshold for your GENRE_MAPPING.
MATCH_THRESHOLD = 92

def categoriseTracks(tracks):
    """
    Sorts a list of tracks into buckets based on config.GENRE_MAPPING.
    This uses fuzzy matching to map raw Last.fm tags into unified buckets.

    Args:
        tracks: List of dicts, each representing a track from the database.
                Must have 'trackUri' and 'lastfmTags'.

    Returns:
        Dict: { 'trackUri': ['Bucket Name', ...], ... }
    """
    trackBucketsMap = {}
    
    for track in tracks:
        trackUri = track['trackUri']
        # Normalise tags for comparison.
        currentTags = [tag.lower().strip() for tag in track.get('lastfmTags', [])]
        
        hasMatchedAny = False
        assignedBuckets = []

        for bucketName, keywords in config.GENRE_MAPPING.items():
            hasMatch = False
            for keyword in keywords:
                # Support "AND" logic via tuples: (tag1, tag2) means both must match.
                if isinstance(keyword, tuple):
                    # Check if every part of the tuple matches at least one tag.
                    all_parts_matched = True
                    for part in keyword:
                        part_lower = part.lower().strip()
                        part_matched = False
                        for tag in currentTags:
                            if fuzz.ratio(part_lower, tag) >= MATCH_THRESHOLD:
                                part_matched = True
                                break
                        if not part_matched:
                            all_parts_matched = False
                            break
                    if all_parts_matched:
                        hasMatch = True
                else:
                    # Original single-keyword "OR" logic.
                    keywordLower = keyword.lower().strip()
                    for tag in currentTags:
                        if fuzz.ratio(keywordLower, tag) >= MATCH_THRESHOLD:
                            hasMatch = True
                            break
                
                if hasMatch:
                    break
            
            if hasMatch:
                assignedBuckets.append(bucketName)
                hasMatchedAny = True
                
                # Stop if we've reached the user-defined maximum playlists per song.
                if config.MAX_GENRE_PLAYLISTS_PER_SONG is not None:
                    if len(assignedBuckets) >= config.MAX_GENRE_PLAYLISTS_PER_SONG:
                        break
        
        if not hasMatchedAny:
            assignedBuckets.append(config.UNDEFINED_TAG)
            
        trackBucketsMap[trackUri] = assignedBuckets
            
    return trackBucketsMap
