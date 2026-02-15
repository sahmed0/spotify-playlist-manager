"""
State management for the Spotify Sorter application using SQLite.
"""
import sqlite3
import time
from datetime import datetime

# Configuration
DB_FILE = "state.db"

def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # Balance safety and speed as requested
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Initialise the database schema if it doesn't exist."""
    with get_db_connection() as conn:
        # Enable Write-Ahead Logging for concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Table for simple key-value pairs (e.g., last_run_timestamp)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Table for playlist snapshots
        conn.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                playlist_id TEXT PRIMARY KEY,
                snapshot_id TEXT
            )
        ''')
        
        # Table for processed tracks
        conn.execute('''
            CREATE TABLE IF NOT EXISTS processed_tracks (
                track_uri TEXT PRIMARY KEY,
                timestamp_added DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_processed_tracks_timestamp 
            ON processed_tracks(timestamp_added)
        ''')
        
        # Table for unclassified songs logs
        conn.execute('''
            CREATE TABLE IF NOT EXISTS unclassified_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_uri TEXT,
                track_name TEXT,
                artist_name TEXT,
                logged_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table for artist tags cache
        conn.execute('''
            CREATE TABLE IF NOT EXISTS artist_cache (
                artist_name TEXT PRIMARY KEY,
                tags TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for playlist cache (name -> id)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS playlist_cache (
                name TEXT PRIMARY KEY,
                playlist_id TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        
        conn.commit()

# Initialise DB
init_db()

# --- Public Interface ---

def load_state():
    """Return the last_run_timestamp (ISO format string) or None."""
    return get_last_run_timestamp()

def get_last_run_timestamp():
    """Return the last_run_timestamp (ISO format string) or None."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", ('last_run_timestamp',)).fetchone()
        return row['value'] if row else None

def save_state(timestamp):
    """Update the last_run_timestamp."""
    save_last_run_timestamp(timestamp)

def save_last_run_timestamp(timestamp):
    """Update the last_run_timestamp."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
            ('last_run_timestamp', timestamp)
        )
        conn.commit()

def get_stored_snapshot_id(playlist_id):
    """Return the stored snapshot_id for a given playlist or None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT snapshot_id FROM snapshots WHERE playlist_id = ?",
            (playlist_id,)
        ).fetchone()
        return row['snapshot_id'] if row else None

def update_snapshot_id(playlist_id, snapshot_id):
    """Update the snapshot_id for a given playlist."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO snapshots (playlist_id, snapshot_id) VALUES (?, ?)",
            (playlist_id, snapshot_id)
        )
        conn.commit()

def get_processed_tracks():
    """Return a set of track URIs that have been processed."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT track_uri FROM processed_tracks").fetchall()
        return {row['track_uri'] for row in rows}

def mark_track_as_processed(track_uri):
    """Add a track URI to the processed list."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_tracks (track_uri) VALUES (?)",
            (track_uri,)
        )
        conn.commit()

def bulk_mark_tracks_as_processed(track_uris):
    """Add multiple track URIs to the processed list efficiently."""
    if not track_uris:
        return
        
    with get_db_connection() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO processed_tracks (track_uri) VALUES (?)",
            [(uri,) for uri in track_uris]
        )
        conn.commit()

def is_track_newer(track_added_at, last_run_timestamp):
    """
    Check if the track is newer than the last run.

    Timestamps are expected to be ISO 8601 strings.
    """
    if not last_run_timestamp:
        return True
        
    # Simple string comparison works for ISO 8601 if timezones match (usually UTC 'Z')
    return track_added_at >= last_run_timestamp

def log_unclassified_songs(songs):
    """
    Log unclassified songs to the database.

    Expects a list of song dictionaries with 'uri', 'name', and 'artists'.
    """
    if not songs:
        return

    with get_db_connection() as conn:
        for song in songs:
            name = song.get('name', 'Unknown')
            # Extract primary artist or join all? content used join, let's use join to be safe
            artist_names = ", ".join([a['name'] for a in song.get('artists', [])])
            uri = song.get('uri', '')
            
            conn.execute(
                "INSERT INTO unclassified_songs (track_uri, track_name, artist_name) VALUES (?, ?, ?)",
                (uri, name, artist_names)
            )
        conn.commit()

def get_artist_tags(artist_name):
    """Return a list of tags for an artist from the cache, or None if not found."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT tags FROM artist_cache WHERE artist_name = ?", (artist_name,)).fetchone()
        if row:
            return row['tags'].split(',') if row['tags'] else []
        return None

def save_artist_tags(artist_name, tags):
    """Save a list of tags for an artist to the cache."""
    tags_str = ",".join(tags)
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO artist_cache (artist_name, tags) VALUES (?, ?)",
            (artist_name, tags_str)
        )
        conn.commit()

def get_all_cached_playlists():
    """Return a dict of {name: playlist_id} from the database."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, playlist_id FROM playlist_cache").fetchall()
        return {row['name']: row['playlist_id'] for row in rows}

def cache_playlist(name, playlist_id):
    """Save a single playlist to the cache."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO playlist_cache (name, playlist_id) VALUES (?, ?)",
            (name, playlist_id)
        )
        conn.commit()



