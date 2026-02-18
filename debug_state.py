import sqlite3
import os

DB_FILE = "state.db"

if not os.path.exists(DB_FILE):
    print(f"Database file {DB_FILE} does not exist.")
else:
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        
        print(f"--- Inspecting {DB_FILE} ---")
        
        # Check app_state table
        print("\n[app_state Table]")
        try:
            rows = conn.execute("SELECT * FROM app_state").fetchall()
            if not rows:
                print("Table 'app_state' is empty.")
            for row in rows:
                print(f"Key: {row['key']}, Value: {row['value']}")
        except sqlite3.OperationalError as e:
            print(f"Error querying app_state: {e}")

        # Check other tables counts
        tables = ['processed_tracks', 'snapshots', 'playlist_cache', 'artist_cache', 'rate_limits', 'unclassified_songs']
        print("\n[Row Counts]")
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"{table}: {count}")
            except sqlite3.OperationalError:
                print(f"{table}: Table does not exist")

    except Exception as e:
        print(f"Error inspecting DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
