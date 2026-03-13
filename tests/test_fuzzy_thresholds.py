"""
Script to test different fuzzy matching thresholds on real data.
Helps determine the optimal MATCH_THRESHOLD by showing how many 
songs are rescued from 'Undefined' at each level.
"""
import json
from thefuzz import fuzz
import config
from app_state import getDbConnection

def test_thresholds(thresholds=[86, 88, 90, 92, 94, 96], sample_size=2000):
    print(f"--- Testing Fuzzy Matching Thresholds on tracks WITH tags ---")
    
    with getDbConnection() as conn:
        query = """
            SELECT trackName, artists, lastfmTags, sortedPlaylists 
            FROM likedSongs 
            WHERE lastfmTags IS NOT NULL
            LIMIT ?
        """
        rows = conn.execute(query, (sample_size,)).fetchall()
    
    actual_count = len(rows)
    if actual_count == 0:
        print("Error: No tracks with Last.fm tags found in database.")
        return
        
    print(f"Found {actual_count} tracks with tags to test.")
    
    results = {}
    for t in thresholds:
        results[t] = {"rescued": 0, "undefined": 0, "total_matches": 0}

    for row in rows:
        tags = [tag.lower().strip() for tag in (json.loads(row['lastfmTags']) if row['lastfmTags'] else [])]
        artists = json.loads(row['artists']) if row['artists'] else []
        artist_name = artists[0]['name'] if artists else "Unknown"
        track_name = row['trackName']

        for t in thresholds:
            matched_buckets = []
            for bucket_name, keywords in config.GENRE_MAPPING.items():
                match_found = False
                for keyword in keywords:
                    if isinstance(keyword, tuple):
                        all_parts_matched = True
                        for part in keyword:
                            part_lower = part.lower().strip()
                            part_matched = False
                            for tag in tags:
                                if fuzz.ratio(part_lower, tag) >= t:
                                    part_matched = True
                                    break
                            if not part_matched:
                                all_parts_matched = False
                                break
                        if all_parts_matched:
                            match_found = True
                    else:
                        keyword_lower = keyword.lower().strip()
                        for tag in tags:
                            if fuzz.ratio(keyword_lower, tag) >= t:
                                match_found = True
                                break
                    if match_found:
                        break
                if match_found:
                    matched_buckets.append(bucket_name)
                    if config.MAX_GENRE_PLAYLISTS_PER_SONG == 1:
                        break
            
            if not matched_buckets:
                results[t]["undefined"] += 1
            else:
                results[t]["total_matches"] += 1
                
    print(f"\n{'Threshold':<10} | {'Matched':<10} | {'Undefined':<10} | {'Match Rate'}")
    print("-" * 50)
    for t in thresholds:
        count = results[t]["total_matches"]
        undef = results[t]["undefined"]
        rate = (count / actual_count) * 100
        print(f"{t:<10} | {count:<10} | {undef:<10} | {rate:.1f}%")

    # Example of potential false positives at lower threshold
    print("\n--- Potential False Positives (Strict vs Loose) ---")
    print(f"{'Artist':<20} | {'Track':<30} | {'92% Match':<20} | {'86% Match'}")
    print("-" * 100)
    
    sample_rows = rows[:15]
    for row in sample_rows:
        tags = [tag.lower().strip() for tag in (json.loads(row['lastfmTags']) if row['lastfmTags'] else [])]
        artists = json.loads(row['artists']) if row['artists'] else []
        artist_name = artists[0]['name'] if artists else "Unknown"
        
        def get_buckets(threshold):
            buckets = []
            for b, kws in config.GENRE_MAPPING.items():
                m = False
                for kw in kws:
                    if isinstance(kw, tuple):
                        ap = True
                        for p in kw:
                            pl = p.lower().strip()
                            pm = any(fuzz.ratio(pl, tg) >= threshold for tg in tags)
                            if not pm: ap = False; break
                        if ap: m = True
                    else:
                        kl = kw.lower().strip()
                        if any(fuzz.ratio(kl, tg) >= threshold for tg in tags): m = True
                    if m: break
                if m:
                    buckets.append(b)
                    if config.MAX_GENRE_PLAYLISTS_PER_SONG == 1: break
            return buckets if buckets else ["Undefined"]

        b92 = get_buckets(92)
        b86 = get_buckets(86)
        
        if b92 != b86:
            print(f"{artist_name[:20]:<20} | {row['trackName'][:30]:<30} | {str(b92)[:20]:<20} | {str(b86)}")

if __name__ == "__main__":
    test_thresholds()
