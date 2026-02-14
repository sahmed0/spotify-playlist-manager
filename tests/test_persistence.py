import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
import state

class TestPersistence(unittest.TestCase):
    
    @patch('state.get_processed_tracks')
    @patch('state.is_track_newer')
    def test_filter_logic(self, mock_is_newer, mock_get_processed):
        # Setup
        mock_get_processed.return_value = {'spotify:track:1'}
        mock_is_newer.return_value = True
        
        liked_songs = [
            {'uri': 'spotify:track:1', 'name': 'Processed Song', 'added_at': '2023-01-01'},
            {'uri': 'spotify:track:2', 'name': 'New Song', 'added_at': '2023-01-02'}
        ]
                
        new_songs = []
        processed_tracks = state.get_processed_tracks()
        skipped_count = 0
        last_run = "2020-01-01"
        latest_timestamp = "2020-01-01"
        
        for song in liked_songs:
            if state.is_track_newer(song['added_at'], last_run):
                # Persistence Check
                if song['uri'] in processed_tracks:
                    skipped_count += 1
                    continue
                    
                new_songs.append(song)
        
        # Assertions
        self.assertEqual(len(new_songs), 1)
        self.assertEqual(new_songs[0]['uri'], 'spotify:track:2')
        self.assertEqual(skipped_count, 1)

if __name__ == '__main__':
    unittest.main()
