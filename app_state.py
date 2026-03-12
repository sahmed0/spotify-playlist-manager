"""
State management for the Spotify Liked Songs Organiser application using SQLite.
This provides a persistent local database to maintain independent operational 
state and ensure the system can resume smoothly after interruptions.
"""
import sqlite3
from datetime import datetime
import json

DB_FILE = "state.db"

def getDbConnection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def initDb():
    """
    Initialises the database schema if it does not exist.
    This sets up all required tables with camelCase columns.
    """
    with getDbConnection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS likedSongs (
                trackUri TEXT PRIMARY KEY,
                trackName TEXT,
                artists TEXT,
                addedAt DATETIME,
                lastfmTags TEXT,
                sortedPlaylists TEXT,
                isInvalid BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usersPlaylists (
                playlistId TEXT PRIMARY KEY,
                name TEXT,
                snapshotId TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                playlistId TEXT,
                trackUri TEXT,
                PRIMARY KEY (playlistId, trackUri)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS artistTagsCache (
                artistName TEXT PRIMARY KEY,
                tags TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trackTagsCache (
                trackUri TEXT PRIMARY KEY,
                tags TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rateLimits (
                bucketId TEXT PRIMARY KEY,
                timestamps TEXT,
                updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

initDb()

def getMemoryVal(key, default=None):
    """
    Returns a value from the memory table or default.
    This acts as a durable key-value store for application pointers like offsets.
    """
    with getDbConnection() as conn:
        row = conn.execute("SELECT value FROM memory WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else default

def setMemoryVal(key, value):
    """
    Sets or updates a value in the memory table.
    This persists metadata like offsets or user IDs across application runs.
    """
    with getDbConnection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        conn.commit()

def getRateLimitData(bucketId):
    """Retrieves stored timestamps for a rate limit bucket."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT timestamps FROM rateLimits WHERE bucketId = ?", (bucketId,)).fetchone()
        if row and row['timestamps']:
            try:
                return [float(t) for t in row['timestamps'].split(',')]
            except ValueError:
                return []
        return []

def saveRateLimitData(bucketId, timestamps):
    """Saves a list of timestamps for a rate limit bucket."""
    tsStr = ",".join(f"{t:.4f}" for t in timestamps)
    with getDbConnection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO rateLimits (bucketId, timestamps) VALUES (?, ?)",
            (bucketId, tsStr)
        )
        conn.commit()

def saveLikedSongs(tracks):
    """
    Saves a list of track dictionaries to the likedSongs table.
    This safely merges new fetches with existing tracks without destroying assigned tags.
    """
    if not tracks:
        return
        
    with getDbConnection() as conn:
        for track in tracks:
            artistsJson = json.dumps(track.get('artists', []))
            
            conn.execute('''
                INSERT OR REPLACE INTO likedSongs 
                (trackUri, trackName, artists, addedAt, lastfmTags, sortedPlaylists, isInvalid)
                VALUES (?, ?, ?, ?, 
                        COALESCE((SELECT lastfmTags FROM likedSongs WHERE trackUri = ?), NULL),
                        COALESCE((SELECT sortedPlaylists FROM likedSongs WHERE trackUri = ?), NULL),
                        COALESCE((SELECT isInvalid FROM likedSongs WHERE trackUri = ?), 0))
            ''', (
                track['uri'],
                track['name'],
                artistsJson,
                track['addedAt'],
                track['uri'],
                track['uri'],
                track['uri']
            ))
        conn.commit()

def getLatestTrackTimestamp():
    """Retrieves the addedAt timestamp of the most recently synced track."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT MAX(addedAt) as maxAddedAt FROM likedSongs").fetchone()
        return row['maxAddedAt'] if row else None

def getTracksMissingTags(limit=None):
    """Returns a list of tracks that lack lastfmTags."""
    with getDbConnection() as conn:
        query = "SELECT * FROM likedSongs WHERE lastfmTags IS NULL"
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query).fetchall()
        
        tracks = []
        for row in rows:
            track = dict(row)
            track['artists'] = json.loads(track['artists']) if track['artists'] else []
            tracks.append(track)
        return tracks

def updateTrackTags(trackUri, tags):
    """Updates the lastfmTags for a specific track."""
    with getDbConnection() as conn:
        conn.execute(
            "UPDATE likedSongs SET lastfmTags = ? WHERE trackUri = ?",
            (json.dumps(tags), trackUri)
        )
        conn.commit()

def countUnclassifiedTracks():
    """Returns the total number of tracks that have tags but are not yet sorted."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM likedSongs WHERE lastfmTags IS NOT NULL AND sortedPlaylists IS NULL AND isInvalid = 0").fetchone()
        return row['count'] if row else 0

def getUnclassifiedTracks(limit=None, offset=0):
    """
    Retrieves tracks that have Last.fm tags but have not yet been assigned to any buckets.
    Supports chunked retrieval via limit and offset.
    """
    query = "SELECT * FROM likedSongs WHERE lastfmTags IS NOT NULL AND sortedPlaylists IS NULL AND isInvalid = 0"
    params = []
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = [limit, offset]
        
    with getDbConnection() as conn:
        rows = conn.execute(query, params).fetchall()
        
        tracks = []
        for row in rows:
            track = dict(row)
            track['artists'] = json.loads(track['artists']) if track['artists'] else []
            track['lastfmTags'] = json.loads(track['lastfmTags']) if track['lastfmTags'] else []
            tracks.append(track)
        return tracks

def updateTrackSorting(trackUri, playlists):
    """Updates the sortedPlaylists for a specific track."""
    with getDbConnection() as conn:
        conn.execute(
            "UPDATE likedSongs SET sortedPlaylists = ? WHERE trackUri = ?",
            (json.dumps(playlists), trackUri)
        )
        conn.commit()

def getArtistTags(artistName):
    """Retrieves cached Last.fm tags for an artist."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT tags FROM artistTagsCache WHERE artistName = ?", (artistName,)).fetchone()
        if row and row['tags']:
            return json.loads(row['tags'])
        return None

def saveArtistTags(artistName, tags):
    """Saves Last.fm tags for an artist to avoid redundant API lookups."""
    with getDbConnection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO artistTagsCache (artistName, tags) VALUES (?, ?)",
            (artistName, json.dumps(tags))
        )
        conn.commit()

def getTrackTags(trackUri):
    """Retrieves cached Last.fm tags for a specific track."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT tags FROM trackTagsCache WHERE trackUri = ?", (trackUri,)).fetchone()
        if row and row['tags']:
            return json.loads(row['tags'])
        return None

def saveTrackTags(trackUri, tags):
    """Saves Last.fm tags for a specific track to avoid redundant API lookups."""
    with getDbConnection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO trackTagsCache (trackUri, tags) VALUES (?, ?)",
            (trackUri, json.dumps(tags))
        )
        conn.commit()

def bulkCachePlaylists(playlists):
    """Saves a list of playlist dictionaries to the usersPlaylists table incrementally."""
    if not playlists:
        return
        
    with getDbConnection() as conn:
        for pl in playlists:
            conn.execute(
                "INSERT OR REPLACE INTO usersPlaylists (playlistId, name, snapshotId) VALUES (?, ?, ?)",
                (pl['id'], pl['name'], pl.get('snapshot_id'))
            )
        conn.commit()

def cleanupOrphanedPlaylists(seenIds):
    """Removes playlists from the local cache that were not included in the last full sync batch."""
    if not seenIds:
        return
        
    placeholders = ",".join(["?"] * len(seenIds))
    with getDbConnection() as conn:
        conn.execute(f"DELETE FROM usersPlaylists WHERE playlistId NOT IN ({placeholders})", list(seenIds))
        conn.commit()

def getAllCachedPlaylists():
    """Returns all cached playlists as a {name: id} dictionary."""
    with getDbConnection() as conn:
        rows = conn.execute("SELECT name, playlistId FROM usersPlaylists").fetchall()
        return {row['name']: row['playlistId'] for row in rows}

def cachePlaylist(name, playlistId, snapshotId=None):
    """Adds a single playlist to the cache."""
    with getDbConnection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO usersPlaylists (playlistId, name, snapshotId) VALUES (?, ?, ?)",
            (playlistId, name, snapshotId)
        )
        conn.commit()

def deletePlaylistCache(playlistId):
    """Removes a single playlist from the cache."""
    with getDbConnection() as conn:
        conn.execute("DELETE FROM usersPlaylists WHERE playlistId = ?", (playlistId,))
        conn.execute("DELETE FROM snapshots WHERE playlistId = ?", (playlistId,))
        conn.commit()

def getPlaylistSnapshotId(playlistId):
    """Retrieves the snapshot ID stored in the playlist cache."""
    with getDbConnection() as conn:
        row = conn.execute("SELECT snapshotId FROM usersPlaylists WHERE playlistId = ?", (playlistId,)).fetchone()
        return row['snapshotId'] if row else None

def getLastSyncSnapshotId(playlistId):
    """Retrieves the snapshot ID corresponding to the tracks currently in our local snapshots table."""
    return getMemoryVal(f"lastSyncSnapshotId_{playlistId}")

def updateLastSyncSnapshotId(playlistId, snapshotId):
    """Saves the snapshot ID corresponding to our last successful sync/snapshot fetch."""
    setMemoryVal(f"lastSyncSnapshotId_{playlistId}", snapshotId)

def updatePlaylistSnapshotId(playlistId, snapshotId):
    """Updates the snapshot ID in the persistent playlist cache."""
    with getDbConnection() as conn:
        conn.execute("UPDATE usersPlaylists SET snapshotId = ? WHERE playlistId = ?", (snapshotId, playlistId))
        conn.commit()

def clearSnapshot(playlistId):
    """Removes all track URIs from the snapshots table for a given playlist."""
    with getDbConnection() as conn:
        conn.execute("DELETE FROM snapshots WHERE playlistId = ?", (playlistId,))
        conn.commit()

def addToSnapshotBatch(playlistId, trackUris):
    """Adds a batch of track URIs to the snapshots table for a given playlist."""
    if not trackUris:
        return
        
    with getDbConnection() as conn:
        conn.executemany(
            "INSERT INTO snapshots (playlistId, trackUri) VALUES (?, ?)",
            [(playlistId, uri) for uri in trackUris]
        )
        conn.commit()

def replaceSnapshotTracks(playlistId, trackUris):
    """Clears existing snapshot tracks for a playlist and inserts new ones. Now uses incremental helpers."""
    clearSnapshot(playlistId)
    if trackUris:
        addToSnapshotBatch(playlistId, trackUris)

def getSnapshotTracks(playlistId):
    """Retrieves all track URIs for a given playlist snapshot as a set."""
    with getDbConnection() as conn:
        rows = conn.execute("SELECT trackUri FROM snapshots WHERE playlistId = ?", (playlistId,)).fetchall()
        return {row['trackUri'] for row in rows}

def getTracksForPlaylist(playlistName):
    """
    Retrieves all track URIs from likedSongs assigned to the specified playlist.
    Uses SQLite JSON functions to filter directly in the database for maximum efficiency.
    """
    query = """
        SELECT trackUri 
        FROM likedSongs, json_each(likedSongs.sortedPlaylists) 
        WHERE (isInvalid IS NULL OR isInvalid = 0) 
        AND json_each.value = ?
    """
    with getDbConnection() as conn:
        rows = conn.execute(query, (playlistName,)).fetchall()
        return [row['trackUri'] for row in rows]

def markTrackInvalid(trackUri):
    """Flags a specific track URI as permanently invalid so it is never re-submitted to Spotify."""
    with getDbConnection() as conn:
        conn.execute(
            "UPDATE likedSongs SET isInvalid = 1 WHERE trackUri = ?",
            (trackUri,)
        )
        conn.commit()
