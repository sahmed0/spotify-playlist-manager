"""
Utility script to reset the sorting status in the database.
This allows you to re-run the categorisation logic from scratch 
without losing your cached Last.fm tags.
"""
import sqlite3
import sys
from app_state import getDbConnection

def reset_sorting_tags():
    print("⚠️  This will clear all genre bucket assignments for your liked songs.")
    print("It will NOT delete track names, artists, or Last.fm tags.")
    
    confirm = input("Are you sure you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        with getDbConnection() as conn:
            # 1. Clear bucket assignments
            cursor = conn.execute("UPDATE likedSongs SET sortedPlaylists = NULL")
            print(f"✅ Reset sorting for {cursor.rowcount} tracks.")
            
            # 2. Clear memory value for progress (Operation 7/8 usually uses this)
            conn.execute("DELETE FROM memory WHERE key = 'current_operation_offset'")
            
            conn.commit()
            print("\nDatabase reset successfully. You can now run Operation 7 to re-classify songs.")
            
    except Exception as e:
        print(f"Error during reset: {e}")

if __name__ == "__main__":
    reset_sorting_tags()
