import json

# --- CONFIGURATION (My_Mappings) ---
# These are your "Buckets". You can add or remove keywords here to tune the sorting.
GENRE_MAPPING = {
    'Hip Hop': ['rap', 'hip hop', 'trap', 'drill', 'detroit hip hop'],
    'Rock': ['rock', 'metal', 'punk', 'grunge', 'indie', 'glam rock'],
    'Pop': ['pop', 'dance', 'k-pop', 'synth-pop'],
    'Electronic': ['house', 'techno', 'edm', 'dubstep', 'electronica', 'electro'],
    'Jazz & Soul': ['jazz', 'soul', 'r&b', 'blues', 'funk', 'motown'],
    'Classical': ['classical', 'orchestra', 'piano', 'baroque'],
    'Country & Folk': ['country', 'folk', 'americana'],
    'Chill': ['lo-fi', 'downtempo', 'ambient', 'chillhop']
}

OTHER_BUCKET = "Unsorted"

def test_my_sorter():
    # 1. LOAD data FROM "mock_data.json"
    try:
        with open('mock_data.json', 'r') as f:
            data = json.load(f)
        print(f"Successfully loaded {len(data)} songs.")
    except FileNotFoundError:
        print("Error: 'mock_data.json' not found. Make sure it's in the same folder.")
        return

    # 2. CREATE a results dictionary
    # We initialize it with empty lists for each bucket defined above
    results = {bucket: [] for bucket in GENRE_MAPPING.keys()}
    results[OTHER_BUCKET] = []

    # 3. FOR EACH song IN data
    for song in data:
        found = False
        song_genres = song.get('genres', []) # Get the list of genres safely
        song_name = song.get('name', 'Unknown Track')
        
        # Flatten the song's genres into a single lowercase string for easy matching
        # e.g., ['Rock', 'Pop'] becomes "rock pop"
        # This helps match "hip hop" against "Hip Hop" easily
        flat_song_genres = " ".join(song_genres).lower()

        # FOR EACH genre_bucket, keywords IN My_Mappings
        for bucket_name, keywords in GENRE_MAPPING.items():
            # IF any keyword is in song['genres']
            for keyword in keywords:
                if keyword in flat_song_genres:
                    # ADD song['name'] TO results[genre_bucket]
                    results[bucket_name].append(song_name)
                    found = True
                    break # Stop checking keywords for this specific bucket
            
            if found:
                break # Stop checking other buckets (Song is sorted, move to next song)

        # IF found is False
        if not found:
            results[OTHER_BUCKET].append(song_name)

    # 4. PRINT results
    print("\n--- Sorting Results ---")
    for bucket, songs in results.items():
        if songs: # Only print buckets that actually have songs
            print(f"\n📁 {bucket} ({len(songs)} songs):")
            for s in songs:
                print(f"   - {s}")
        else:
            print(f"\n📁 {bucket}: (Empty)")

# Run the function
if __name__ == "__main__":
    test_my_sorter()