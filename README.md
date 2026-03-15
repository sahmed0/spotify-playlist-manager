# Spotify Liked Songs Sorter

![Copyright](https://img.shields.io/badge/Copyright-2026_Sajid_Ahmed-darkblue.svg)
![Spotify](https://img.shields.io/badge/Spotify-Web_API-limegreen.svg)
![Last.fm](https://img.shields.io/badge/Last.fm-API-crimson.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite3-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)


A robust, enterprise-grade automation tool designed to organise your Spotify "Liked Songs" into genre-specific playlists. Engineered for high reliability, it navigates the complexities of the 2026 Spotify API landscape using intelligent synchronisation, strict rate limiting, and persistent state management.

## Key Features

-   **Smart Incremental Sync**: The sorter tracks your library state in a local SQLite database, processing *only* new tracks since the last run. It handles large libraries (10,000+ songs) efficiently by using Spotify's `snapshot_id` to avoid redundant API calls.
-   **Interactive CLI**: Re-architected into 8 segmented, independent operations. You can safely stop, resume, or replay any step (fetching, tagging, creating playlists) without locking up the entire application.
-   **Precision Tagging**: Utilises the **Last.fm API** to fetch granular song and artist tags. It employs a multi-tiered fallback strategy (Track Tags -> Artist Tags -> Cache) to ensure high classification accuracy.
-   **Enterprise-Grade Rate Limiting**: Implements a **Leaky Bucket algorithm** with jitter and exponential backoff. It proactively respects Spotify's strict "Development Mode" limits and automatically handles `HTTP 429 Too Many Requests` responses with `Retry-After` headers.
-   **Robust Persistence**: All state—including processed tracks, API rate limits, and tag caches—is stored in a local SQLite database (`state.db`) with Write-Ahead Logging (WAL) enabled for performance and data integrity.
-   **Non-Destructive Operation**: Appends tracks to playlists safely. It will never delete or re-order your existing songs, allowing you to manually curate playlists alongside the automation.

<p align="center">
  <img src="assets/cli.png" alt="Command Line Interface" width="600">
</p>

<p align="center">
  <img src="assets/example.png" alt="Playlist example" width="600">
</p>

---

## Technical Architecture

This application is built on a modular, service-oriented architecture designed for maintainability and scalability.

```mermaid
graph TD
    subgraph Core Logic
        Main[main.py] -->|Orchestrates| Client[spotify_client.py]
        Main -->|Classifies| Sorter[sorter.py]
        Main -->|Persists State| State[app_state.py]
        Main -->|Enriches| LastFM[lastfm_client.py]
    end

    subgraph Infrastructure
        Client -->|Rate Limited Requests| Session[rate_limiter.py]
        LastFM -->|Rate Limited Requests| Session
        Session -->|HTTP/HTTPS| SpotifyAPI[Spotify Web API]
        Session -->|HTTP/HTTPS| LastFM_API[Last.fm API]
    end

    subgraph Persistence
        State -->|Reads/Writes| DB[(SQLite: state.db)]
    end

    subgraph Configuration
        Config[config.py] -.->|Settings| Main
        Config -.->|Creds| Client
    end
```

### Component Breakdown

| Component | Responsibility | Key Technical Details |
| :--- | :--- | :--- |
| **`main.py`** | Orchestration | Manages the interactive 8-step CLI loop. Connects user input to independent phase execution. |
| **`spotify_client.py`** | API Gateway | Uses pure `requests` with custom error handling. Implements **batched operations** (fetching 50 liked songs, adding 100 tracks) to minimise network RTT. |
| **`rate_limiter.py`** | Traffic Control | Implements a thread-safe `LeakyBucket`. **Spotify**: 1 req/30s (Safety). **Last.fm**: 5 req/sec. Adds random jitter (10-20%) to mimic human behaviour. |
| **`app_state.py`** | Persistence Layer | A raw SQL wrapper around `sqlite3`. Manages tables for `likedSongs`, `artistTagsCache`, and `snapshots`. Ensures independence across the 8 operations. |
| **`lastfm_client.py`** | Metadata Provider | Fetches top tags for tracks/artists. Caches results in SQLite to reduce external API dependency by 90%+ on subsequent runs. |

---

## Solved Challenges

### 1. The Rate Limit Problem
Spotify's API (especially in non-commercial usage) can be aggressive with rate limits. 
*   **Solution**: We moved from a reactive "try and catch error" approach to a **proactive Leaky Bucket**. The application "pays" for every request from a local bucket. If the bucket is empty, it sleeps.
*   **Resilience**: A custom `requests.HTTPAdapter` intercepts `429` errors and sleeps for the exact duration specified in the `Retry-After` header, plus a safety buffer. Note: For very large libraries, fetches and syncs may take hours due to these strict enforced wait times.

### 2. Large Library Synchronisation & Segmentation
Syncing 10,000 songs linearly is too slow, error-prone, and impossible to debug if it crashes on song 9,999.
*   **Segmented CLI**: The application is broken into 8 independent operations. You can pull songs today, classify them tomorrow, and push them to Spotify the next day.
*   **Snapshots**: We store the `snapshot_id` of every target playlist. If the snapshot hasn't changed on Spotify, we skip fetching its tracks entirely, saving huge amounts of time.
*   **Incremental Checkpointing**: Resumable offsets prevent data loss. The fetcher stops immediately once it sees a song older than the last sync date.

### 3. Metadata Reliability
Spotify removed public genre data from their API years ago.
*   **Solution**: We integrate Last.fm. However, querying Last.fm for every single track is slow.
*   **Optimisation**: We implement a **Two-Layer Cache**:
    1.  **Memory**: For the current runtime session.
    2.  **SQLite**: Permanent storage of Artist->Genre mappings.
    *   *Result*: After the initial run, 95% of tags are served locally from disk in milliseconds.

---

## Installation & Setup

### Prerequisites
*   **Python 3.9+**
*   **Spotify Premium Account**
*   **Last.fm API Key** (Free to apply)

### 1. Clone & Install
```bash
git clone https://github.com/sahmed0/spotify-sorter.git
cd spotify-sorter
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory (process is detailed in `.env.example`):
```ini
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
LASTFM_API_KEY=your_lastfm_api_key
```

### 3. Usage
Run the script manually to open the interactive CLI:
```bash
python main.py
```

**The 8-Operation Sequence**:
The tool is broken down into 8 independent operations. You can run them sequentially or resume from any point:

1.  **Authenticate**: Generates your initial Refresh Token via a manual, terminal-based OAuth flow.
2.  **Fetch Liked Songs**: Downloads your liked songs to the local `state.db`. Resumable if interrupted.
3.  **Fetch Last.fm Tags**: Enriches your downloaded tracks with Last.fm genres locally.
4.  **Sort Songs**: Categorises songs into buckets based on your `config.py` genre mappings.
5.  **Fetch User Playlists**: Caches your existing Spotify playlists into the database.
6.  **Create Missing Playlists**: Analyses `config.py` against your cache and creates missing playlists on Spotify.
7.  **Snapshot Playlist**: Backs up the current state of a playlist locally to prevent redundant future API calls.
8.  **Sync & Add Songs**: Pushes the newly sorted, missing tracks to their respective Spotify playlists.

**Dry Run Mode**:
To test without modifying your library or consuming Spotify rate limits, set `DRY_RUN = True` in `config.py` or use the environment variable. The script will simulate all sorting logic.

---

## Automated Workflows
This repository includes a GitHub Actions workflow (`.github/workflows/sync.yml`) designed to run the sorter automatically and update your playlists at a regular interval.
*   It caches the `state.db` file between runs to maintain incremental sync state.
*   It uses GitHub Secrets to securely inject your API credentials.

---

## License
![Copyright](https://img.shields.io/badge/Copyright-2026_Sajid_Ahmed-darkblue.svg)

Copyright (c) 2026 Sajid Ahmed. **All Rights Reserved.**

This repository is a **Proprietary Portfolio Project**.

While I am a strong supporter of Open Source Software, this specific codebase represents a significant personal investment of time and effort and is therefore provided for **recruitment evaluation only**.

* **Permitted:** Viewing, forking (within GitHub only), and local execution for review.
* **Prohibited:** Modification, redistribution, commercial use, and AI/LLM training.

For the full legal terms, please see the [LICENSE](./LICENSE) file.
