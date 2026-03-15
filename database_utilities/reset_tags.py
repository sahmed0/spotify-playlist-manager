"""
Utility script to reset Last.fm tags in the database.
This clears lastfmTags for all tracks and empties the tag caches,
allowing for a completely fresh fetch from Last.fm.
"""
import os
import sys

# Ensure the root directory is in sys.path so we can import from app_state
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_state import getDbConnection

def reset_lastfm_tags():
    """Resets Last.fm tags data and caches in the database."""
    print("⚠️  This will clear all Last.fm tags for your liked songs.")
    print("It will ALSO empty the artist and track tag caches.")
    print("This will NOT delete track names, artists, or sorting status.")
    
    confirm = input("Are you sure you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        with getDbConnection() as conn:
            # 1. Clear lastfmTags in likedSongs
            cursor = conn.execute("UPDATE likedSongs SET lastfmTags = NULL")
            print(f"✅ Reset lastfmTags for {cursor.rowcount} tracks.")
            
            # 2. Clear artistTagsCache
            cursor = conn.execute("DELETE FROM artistTagsCache")
            print(f"✅ Cleared {cursor.rowcount} entries from artistTagsCache.")
            
            # 3. Clear trackTagsCache
            cursor = conn.execute("DELETE FROM trackTagsCache")
            print(f"✅ Cleared {cursor.rowcount} entries from trackTagsCache.")
            
            conn.commit()
            print("\nDatabase reset successfully. You can now run Operation 3 to re-fetch tags.")
            
    except Exception as e:
        print(f"\n❌ Error during reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_lastfm_tags()
