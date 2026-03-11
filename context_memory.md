# Context Memory (spotify-sorter)

**Current Project State & Architecture Initiative**
The application is transitioning from a monolithic, single-run sequence into a segmented, interactive CLI tool with 8 independent operations. 

## Architectural Constraints & Rules
- **Phase-by-Phase Approach:** All development should follow the `development_strategy.md` file located in the project root. We are currently tackling this structural rewrite one phase at a time.
- **NO `spotipy`:** The official Spotify API client (`spotipy`) is being completely removed. All interactions with the Spotify Web API must use direct HTTP requests (via the `requests` library).
- **Rate Limiting:** The existing Leaky Bucket rate limiter must be preserved and used for all direct API calls to ensure compliance with Spotify and Last.fm rate limits.
- **Database as Source of Truth:** `app_state.py` (SQLite) is replacing linear memory drops as the central state management. Tables like `liked_songs`, `users_playlists`, and `snapshots` must store the intermediate state so each CLI operation can run independently.
- **Interactive Console Mode:** User inputs (e.g. selecting playlists, authorising the app) must be done through standard `print()` and `input()` prompts in the `main.py` menu loop.

## The 8 Operations
1. Authenticate (Manual OAuth flow)
2. Fetch Liked Songs (Save to DB, update max offset memory)
3. Fetch Last.fm Tags (Enrich DB tracks)
4. Sort Songs (Apply config mapping, save bucket assignment to DB)
5. Fetch User Playlists (Store owned playlists to DB)
6. Create Missing Playlists (Reconcile config with DB and create on Spotify)
7. Snapshot Playlist (Fetch current tracks in playlist to DB)
8. Sync & Add Songs (Compare DB desired tracks vs Spotify snapshot, add missing, update snapshot)

## Current Status
- **Phase 1 (Completed):** The database schema in `app_state.py` has been redesigned for independent operations, and the interactive CLI menu loop in `main.py` is established.
- **Phase 2 (Completed):** `spotipy` library has been completely removed. A manual, requests-based OAuth flow is implemented in `auth_helper.py`, and `spotify_client.py` has been refactored to use a resilient `requests` session.
- **Phase 3 (Completed):** Data Fetching Operations (Operation 2 & 5) are implemented. Liked songs and user-owned playlists are successfully fetched from Spotify and stored in the local SQLite database. Resumable fetching for liked songs is supported via manual offsets.
- **Phase 4 (Completed):** Local Enrichment & Sorting. Operation 3 (Fetch Last.fm Tags) and Operation 4 (Sort Songs) are implemented. Tracks are enriched with Last.fm tags (with artist-level caching) and categorised into buckets in the local database based on `config.py` mappings.
**Note:** Do not run automatic tests for the repetitive spotify endpoints (like getting songs, adding songs, creating playlists, etc.) because the rate limiting makes these tests prohibitively long. The user will verify your changes manually.

- **Phase 5 (Completed):** Spotify Sync Operations. Operation 6 (Create Missing Playlists), Operation 7 (Snapshot Playlist), and Operation 8 (Sync & Add Songs) are implemented. The application can now reconcile configured playlists with Spotify, localise playlist states via snapshots, and incrementally sync sorted tracks back to Spotify.

- **Moving to Phase 6:** Final Review & Polish. This involves end-to-end testing, ensuring rate limits hold, and data remains consistent across all operations.
