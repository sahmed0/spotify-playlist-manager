import pytest
import sorter
import config

# Mock Data
MOCK_GENRES = {
    'artist_rock': ['rock', 'hard rock'],
    'artist_pop': ['pop', 'dance pop'],
    'artist_techno': ['techno', 'minimal techno'],
    'artist_metal': ['thrash metal', 'metal'],
    'artist_chill': ['ambient', 'lo-fi'],
    'artist_amb_rock': ['ambient', 'post-rock'], # Both chill and rock
}

@pytest.fixture
def run_sorter():
    """Helper to run sorter with specific MatchOnce setting"""
    def _run(tracks, match_once):
        # Temporarily override config
        original_match = config.STOP_AFTER_FIRST_MATCH
        config.STOP_AFTER_FIRST_MATCH = match_once
        try:
            return sorter.categorize_tracks(tracks, MOCK_GENRES)
        finally:
            config.STOP_AFTER_FIRST_MATCH = original_match
    return _run

def test_basic_sorting(run_sorter):
    tracks = [
        {'id': '1', 'name': 'Rock Song', 'artists': [{'id': 'artist_rock'}], 'uri': '1'}
    ]
    results = run_sorter(tracks, match_once=False)
    assert len(results['Rock']) == 1
    assert results['Rock'][0]['name'] == 'Rock Song'

def test_fallback_bucket(run_sorter):
    tracks = [
        {'id': '2', 'name': 'Unknown Song', 'artists': [{'id': 'unknown_artist'}], 'uri': '2'}
    ]
    results = run_sorter(tracks, match_once=False)
    assert len(results['Unsorted']) == 1

def test_multi_match(run_sorter):
    """Test that a song goes to multiple buckets if MATCH_ONCE is False"""
    
    tracks = [
        {'id': '3', 'name': 'Complex Song', 'artists': [{'id': 'artist_amb_rock'}], 'uri': '3'}
    ]
    results = run_sorter(tracks, match_once=False)
    
    assert len(results['Rock']) == 1
    assert len(results['Chill']) == 1
    assert results['Rock'][0]['name'] == 'Complex Song'
    assert results['Chill'][0]['name'] == 'Complex Song'

def test_priority_match(run_sorter):
    """Test that a song stops after first match if MATCH_ONCE is True"""
    
    tracks = [
        {'id': '3', 'name': 'Complex Song', 'artists': [{'id': 'artist_amb_rock'}], 'uri': '3'}
    ]
    results = run_sorter(tracks, match_once=True)
    
    # Count how many buckets it landed in
    matches = 0
    for bucket in results:
        if results[bucket]:
            matches += 1
            
    assert matches == 1

def test_case_insensitivity(run_sorter):
    """Ensure 'Rock' matches 'rock'"""
    # MOCK_GENRES has lowercase 'rock', Sorter logic lowercases everything.
    tracks = [
        {'id': '1', 'name': 'Rock Song', 'artists': [{'id': 'artist_rock'}], 'uri': '1'}
    ]
    results = run_sorter(tracks, match_once=False)
    assert len(results['Rock']) == 1

def test_diff_logic():
    from spotify_client import SpotifyClient
    
    existing = {'uri:1', 'uri:2', 'uri:3'}
    incoming = ['uri:2', 'uri:3', 'uri:4', 'uri:5']
    
    # specialised function logic check
    to_add = SpotifyClient.identify_missing_tracks(incoming, existing)
    
    assert len(to_add) == 2
    assert 'uri:4' in to_add
    assert 'uri:5' in to_add
    assert 'uri:2' not in to_add

def test_album_genre_fallback():
    """Test that if artist has no genres, we use album genres"""
    
    # 1. Track with artist that has NO genres
    track = {
        'id': 'fallback_track', 
        'name': 'Fallback Song', 
        'artists': [{'id': 'artist_unknown'}], 
        'album': {'id': 'album_rock'},
        'uri': 'fallback:1'
    }
    tracks = [track]
    
    # 2. Artist genres map is empty for this artist
    artist_genres = {} 
    
    # 3. Album genres map has the genre
    album_genres = {
        'album_rock': ['rock', 'classic rock']
    }
    
    # 4. Run sorter with both maps
    # Use default config (MATCH_ONCE=False)
    results = sorter.categorize_tracks(tracks, artist_genres, album_genres)
    
    # 5. Verify it landed in 'Rock' bucket
    assert len(results['Rock']) == 1
    assert results['Rock'][0]['name'] == 'Fallback Song'
