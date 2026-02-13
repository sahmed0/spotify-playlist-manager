import json
import os
from datetime import datetime

STATE_FILE = "state.json"

def load_state():
    """Returns the last_run_timestamp (ISO format string) or None."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_run_timestamp')
        except:
            return None
    return None

def save_state(timestamp):
    """Saves the given timestamp to state.json."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_run_timestamp': timestamp}, f)
        
def is_track_newer(track_added_at, last_run_timestamp):
    """
    Checks if the track is newer than the last run.
    Timestamps are expected to be ISO 8601 strings.
    """
    if not last_run_timestamp:
        return True
        
    # Simple string comparison works for ISO 8601 if timezones match (usually UTC 'Z')
    return track_added_at > last_run_timestamp
