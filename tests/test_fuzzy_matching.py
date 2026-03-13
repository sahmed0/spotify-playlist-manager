"""
Debug script to test fuzzy matching on real data from state.db.
It fetches a sample of tracks (prioritising 'Undefined' ones) and predicts their new buckets.
"""
import sqlite3
import json
import sorter
import config
from app_state import getDbConnection

def debug_on_real_data(sample_size=100):
    print(f"--- Debugging Fuzzy Matching on {sample_size} real tracks ---")
    
    with getDbConnection() as conn:
        # Prioritise tracks that are currently bucketed as 'Undefined'
        # to see if the new logic rescues them.
        query = """
            SELECT trackName, artists, lastfmTags, sortedPlaylists 
            FROM likedSongs 
            WHERE lastfmTags IS NOT NULL
            ORDER BY (CASE WHEN sortedPlaylists LIKE '%"Undefined"%' THEN 0 ELSE 1 END), RANDOM()
            LIMIT ?
        """
        rows = conn.execute(query, (sample_size,)).fetchall()
        
    tracks_for_sorter = []
    for row in rows:
        tracks_for_sorter.append({
            'trackUri': row['trackName'], # Using name as placeholder ID for display
            'lastfmTags': json.loads(row['lastfmTags']) if row['lastfmTags'] else []
        })
        
    # Run the new fuzzy sorter
    predictions = sorter.categoriseTracks(tracks_for_sorter)
    
    # Print results
    print(f"{'Artist':<20} | {'Track Name':<30} | {'New Buckets'}")
    print("-" * 140)
    
    rescued_count = 0
    for row, track in zip(rows, tracks_for_sorter):
        old_buckets = json.loads(row['sortedPlaylists']) if row['sortedPlaylists'] else ["Not Sorted"]
        
        # Format artist name
        artistsJSON = json.loads(row['artists']) if row['artists'] else []
        artist_name = artistsJSON[0]['name'] if artistsJSON else "Unknown"
        
        new_buckets = predictions[track['trackUri']]
        
        prefix = ""
        if "Undefined" in old_buckets and "Undefined" not in new_buckets:
            prefix = "✅ "
            rescued_count += 1
            
        tags_str = str(track['lastfmTags'])[:40]
        print(f"{artist_name[:20]:<20} | {prefix + row['trackName'][:27]:<30} | {str(new_buckets):<40} | Tags: {tags_str}")

    print("-" * 140)
    print(f"Rescued {rescued_count} tracks from 'Undefined' in this sample!")

if __name__ == "__main__":
    debug_on_real_data()
