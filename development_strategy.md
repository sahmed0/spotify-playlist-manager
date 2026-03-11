# Spotify Sorter - Development Strategy

This document outlines a phased strategy to transform the `spotify-sorter` application from a sequential script into a segmented, independent-operation CLI tool. The goal is to tackle the architectural rewrite in small, verifiable steps.

## Phase 1: Database Redesign & CLI Foundation
**Objective:** Establish the new data models to store state between independent operations and set up the basic interactive CLI loop.
*   **Database (`app_state.py`):** Drop legacy tables (`processed_tracks`, `playlist_cache`) and create the new sequence-independent tables: `liked_songs`, `memory`, `users_playlists`, and `snapshots`.
*   **CLI (`main.py`):** Replace the linear execution flow with a `while True:` menu loop presenting options 1 through 8 (plus an exit option). Connect the options to placeholder functions.

## Phase 2: Independent Spotify Client & Authentication (Operation 1)
**Objective:** Remove `spotipy` completely and establish a manual OAuth flow using raw `requests` and the existing Leaky Bucket rate limiter.
*   **Spotify Client (`spotify_client.py`):** Remove all `spotipy` dependencies. Implement the `SpotifyClient` class using the `requests` library.
*   **Authentication (Op 1):** Write the logic to generate the Spotify Authorization URL, instruct the user to visit it, accept a redirected URL/code via the console, and exchange it for tokens (saving the refresh token to `.env`).

## Phase 3: Data Fetching Operations (Operations 2 & 5)
**Objective:** Implement the independent operations for fetching tracks and playlists from Spotify into the local database.
*   **Fetch Liked Songs (Op 2):** Implement `GET /me/tracks`, allowing the user to specify a number of tracks. Save them to the `liked_songs` table and update the `memory` table with the latest offset.
*   **Fetch User Playlists (Op 5):** Implement `GET /me/playlists`, fetching only owned playlists and saving them to the `users_playlists` table.

## Phase 4: Local Enrichment & Sorting (Operations 3 & 4)
**Objective:** Implement the offline/third-party data processing steps that operate purely on the database.
*   **Fetch Last.fm Tags (Op 3):** Modify `lastfm_client.py` to read tracks from `liked_songs` lacking tags, fetch them from Last.fm, and update the row in the database.
*   **Sort Songs (Op 4):** Modify `sorter.py` to process the `liked_songs` table, categorise tracks based on `config.py` definitions and Last.fm tags, and append the assigned playlist names to the `sorted_playlists` column in the database.

## Phase 5: Spotify Sync Operations (Operations 6, 7 & 8)
**Objective:** Implement the final operations that push aggregated changes back to Spotify or pull explicit snapshot states.
*   **Create Missing Playlists (Op 6):** Compare `config.py` buckets against `users_playlists`. For missing ones, use `POST /users/{user_id}/playlists` to create them and update the DB.
*   **Snapshot Playlist (Op 7):** Allow the user to select a playlist. Use `GET /playlists/{playlist_id}/items` to fetch all current tracks and save this "snapshot" to the `snapshots` table in the database.
*   **Sync & Add Songs (Op 8):** Allow the user to select a playlist. Search `liked_songs` for tracks assigned to it, check against the DB `snapshots` table to avoid duplicates, and use `POST /playlists/{playlist_id}/items` to add missing tracks in batches. Finally, update the snapshot in the database.

## Phase 6: Final Review & Polish
**Objective:** Conduct end-to-end testing of all operations interacting together in any non-sequential order, ensuring rate limits hold and data remains consistent.
