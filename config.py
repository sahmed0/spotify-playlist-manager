"""
Configuration settings for the Spotify Sorter application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# Scope required for the app
SCOPE = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private"

# Sorting Configuration
# STOP_AFTER_FIRST_MATCH:
# True: Song goes into FIRST matching bucket only (Priority based on GENRE_MAPPING order).
# False: Song goes into ALL matching buckets (e.g. Rock AND Workout).
STOP_AFTER_FIRST_MATCH = False

GENRE_MAPPING = {
    # -------------------------------------------------------------------------
    # 1. SPECIFIC SUB-GENRES & NICHE STYLES
    # (Check these first to prevent them being swallowed by broad categories)
    # -------------------------------------------------------------------------

    # --- Specific Electronic & Dance ---
    'Techno': ['techno', 'detroit techno', 'minimal techno', 'acid techno', 'dub techno', 'industrial techno'],
    'House': [
        'house', 'deep house', 'tech house', 'progressive house', 'acid house',
        'tropical house', 'chicago house', 'future house', 'bass house', 'french house'
    ],
    'Trance': ['trance', 'psytrance', 'uplifting trance', 'goa trance', 'vocal trance', 'progressive trance'],
    'Dubstep': ['dubstep', 'brostep', 'riddim', 'deathstep', 'melodic dubstep'],
    'Drum and Bass': ['drum and bass', 'dnb', 'liquid funk', 'neurofunk', 'jump up'],
    'Jungle': ['jungle', 'ragga jungle', 'darkside', 'intelligent dance music'],
    'Garage': ['garage', 'uk garage', 'speed garage', '2-step', 'future garage', 'bassline'],
    'Synthpop': ['synthpop', 'synth-pop', 'electropop', 'futurepop', 'dark wave'],
    'Hyperpop': ['hyperpop', 'glitchcore', 'digicore', 'pc music', 'bubblegum bass'],

    # --- Specific Rock & Metal ---
    'Heavy Metal': [
        'metal', 'heavy metal', 'thrash metal', 'death metal', 'black metal',
        'metalcore', 'doom metal', 'power metal', 'groove metal', 'nu metal',
        'speed metal', 'sludge metal', 'symphonic metal', 'folk metal',
        'viking metal', 'industrial metal', 'gothic metal', 'grindcore', 'djent'
    ],
    'Punk & Post-Punk': [
        'punk', 'post-punk', 'punk rock', 'hardcore punk', 'pop punk',
        'skate punk', 'new wave', 'no wave', 'art punk', 'garage punk',
        'oi', 'crust punk', 'ska punk', 'riot grrrl'
    ],
    'Grunge': ['grunge', 'post-grunge', 'seattle sound'],
    'Shoegaze': ['shoegaze', 'dream pop', 'ethereal wave', 'nu gaze', 'blackgaze'],
    'Noise Rock': ['noise rock', 'noise pop', 'industrial rock', 'no wave', 'math rock'],
    'Psychedelic Rock': ['psychedelic rock', 'psych rock', 'acid rock', 'neo-psychedelia', 'space rock'],
    'Emo': ['emo', 'emo rap', 'screamo', 'midwest emo', 'emotional hardcore'],
    'Slowcore': ['slowcore', 'sadcore'],

    # --- Specific Hip Hop ---
    'Trap': ['trap', 'southern hip hop', 'atlanta hip hop', 'trap soul'],
    'Drill': ['drill', 'uk drill', 'chicago drill', 'brooklyn drill', 'ny drill'],
    'Grime': ['grime', 'uk garage', 'sublow', 'eskibeat'],
    'Jazz-Rap': ['jazz rap', 'jazz-rap', 'jazz hop', 'acid jazz'],
    'Horrorcore': ['horrorcore', 'horror hip hop', 'memphis rap'],
    'East Coast Hip Hop': ['east coast hip hop', 'new york hip hop', 'boom bap', 'mafioso rap'],
    'West Coast Hip Hop': ['west coast hip hop', 'g-funk', 'gangsta rap', 'hyphy'],

    # --- Specific Regional Rap ---
    'Dutch Rap': ['dutch rap', 'nederhop', 'dutch hip hop'],
    'German Rap': ['german rap', 'deutschrap', 'german hip hop'],
    'French Rap': ['french rap', 'rap francais', 'cloud rap francais'],
    'Australian Rap': ['australian rap', 'aussie hip hop', 'australian hip hop'],

    # --- Retro & Specific Pop/Soul ---
    'Disco': ['disco', 'nu-disco', 'italo disco', 'euro disco', 'post-disco', 'boogie'],
    'Motown': ['motown', 'the sound of young america', 'detroit soul'],
    'Northern Soul': ['northern soul', 'mod', 'rare soul'],
    'Doo-Wop': ['doo-wop', 'doo wop', 'street corner symphony'],
    'Madchester': ['madchester', 'baggy', 'alternative dance', 'grebo'],
    'Funk': ['funk', 'p-funk', 'funk rock', 'deep funk', 'go-go', 'boogie'],

    # --- Specific Regional / Cultural Styles ---
    'Afrobeats': ['afrobeats', 'afropop', 'afro fusion', 'alte', 'naija'],
    'Afropiano': ['amapiano', 'afropiano', 'log drum', 'kwaito'],
    'K-pop': ['k-pop', 'korean pop', 'k-rock', 'k-hip hop', 'korean r&b'],
    'Bollywood': ['bollywood', 'filmi', 'hindi film', 'indian pop'],
    'Bhangra': ['bhangra', 'modern bhangra', 'dhol'],
    'Punjabi Pop': ['punjabi pop', 'bhangra pop'],
    'Punjabi': ['punjabi', 'punjabi hip hop', 'punjabi folk'],
    'Sufi': ['sufi', 'sufi rock', 'qawwali fusion'],
    'Qawali': ['qawali', 'qawwali', 'ghazal'],
    'Reggaeton': ['reggaeton', 'neoperreo', 'cubaton'],
    'Dancehall': ['dancehall', 'bashment', 'ragga'],
    'Salsa & Tropical': ['salsa', 'bachata', 'merengue', 'cumbia', 'vallenato', 'tropical'],
    'Latin Urbano': ['latin urbano', 'urbano latino', 'latin hip hop', 'latin trap', 'dembow'],
    'Flamenco': ['flamenco', 'nuevo flamenco', 'rumba flamenca', 'flamenco pop'],

    # -------------------------------------------------------------------------
    # 2. BROAD / UMBRELLA GENRES
    # (Catch-alls for songs that didn't match the specific buckets above)
    # -------------------------------------------------------------------------

    'Rock': [
        'rock', 'hard rock', 'alternative rock', 'blues rock', 'southern rock',
        'garage rock', 'roots rock', 'pub rock', 'heartland rock', 'arena rock',
        'jam band', 'rock & roll', 'rock and roll', 'j-rock'
    ],
    'Pop': [
        'pop', 'dance pop', 'teen pop', 'boy band', 'girl group',
        'europop', 'bubblegum pop', 'art pop', 'sophisti-pop', 'power pop'
    ],
    'Hip Hop': [
        'hip hop', 'rap', 'underground hip hop', 'alternative hip hop',
        'hardcore hip hop', 'conscious hip hop', 'boom bap', 'turntablism'
    ],
    'Electronic': [
        'electronic', 'electronica', 'idm', 'downtempo', 'breakbeat',
        'electro', 'complextro', 'glitch', 'trip hop'
    ],
    'Dance': ['dance', 'eurodance', 'dance-pop', 'club', 'party'],
    'Indie': [
        'indie', 'indie rock', 'indie pop', 'alternative', 'indie folk',
        'lo-fi indie', 'chamber pop', 'twee pop', 'indietronica'
    ],
    'R&B': ['r&b', 'contemporary r&b', 'rhythm and blues', 'quiet storm', 'slow jam'],
    'Alternative R&B': ['alternative r&b', 'pbr&b', 'neo-soul', 'future soul'],
    'Soul': ['soul', 'blue-eyed soul', 'psychedelic soul', 'southern soul', 'chicago soul'],
    'Jazz & Soul': ['jazz', 'smooth jazz', 'fusion', 'bebop', 'swing', 'big band', 'cool jazz'],
    'Blues': ['blues', 'delta blues', 'chicago blues', 'electric blues', 'blues rock', 'country blues'],
    'Country': [
        'country', 'classic country', 'outlaw country', 'country pop',
        'country rock', 'western swing', 'honky tonk', 'nashville sound', 'bro-country'
    ],
    'Folk': ['folk', 'contemporary folk', 'traditional folk', 'indie folk', 'freak folk', 'anti-folk'],
    'Americana': ['americana', 'roots music', 'alt-country', 'texas country', 'bluegrass'],
    'Latin': ['latin', 'latin pop', 'musica mexicana', 'ranchera', 'norteno', 'mariachi'],
    'Reggae': ['regae', 'reggae', 'roots reggae', 'dub', 'rocksteady', 'lovers rock'],
    'Classical': [
        'classical', 'baroque', 'romantic', 'classical period', 'chamber music',
        'symphony', 'concerto', 'sonata', 'choral', 'renaissance', 'medieval'
    ],
    'Opera': ['opera', 'operetta', 'aria', 'bel canto'],

    # --- Broad Regional Buckets ---
    'African Music': ['african', 'highlife', 'soukous', 'juju', 'coupé-décalé', 'afrobeat', 'desert blues'],
    'Brazilian Music': [
        'brazilian', 'samba', 'bossa nova', 'mpb', 'baile funk',
        'funk carioca', 'tropicalia', 'pagode', 'forro', 'sertanejo'
    ],
    'French Music': ['french', 'chanson', 'variete francaise', 'nouvelle scene'],
    'French Pop': ['french pop', 'yé-yé', 'french indie pop'],
    'Italian Music': ['italian', 'italian pop', 'italo pop', 'canzone napoletana', 'opera pop'],
    'Turkish Music': ['turkish', 'turkish pop', 'turkish rock', 'anadolu rock', 'arabesque'],
    'Middle Eastern Music': ['middle eastern', 'arabic pop', 'dabke', 'khaliji', 'shaabi', 'levantine'],
    'Persian Music': ['persian', 'iranian', 'persian pop', 'bandari'],
    'Korean Music': ['korean', 'trot', 'k-indie', 'korean ballad'],
    'Japanese Music': ['japanese', 'j-pop', 'j-rock', 'city pop', 'kayokyoku', 'visual kei', 'anime'],
    'Thai Music': ['thai', 'thai pop', 't-pop', 'luk thung', 'mor lam'],
    'Chinese Music': ['chinese', 'c-pop', 'mandopop', 'cantopop', 'chinese indie'],
    'Pakistani Music': ['pakistani', 'pakistani pop', 'urdu', 'lollywood', 'pakistani rock', 'urdu pop'],
    'International': ['world', 'worldbeat', 'ethno', 'folklore', 'celtic', 'global bass'],

    # -------------------------------------------------------------------------
    # 3. VIBES & ACTIVITIES
    # (Matches based on function or mood rather than musical genre)
    # -------------------------------------------------------------------------

    'Workout': [
        'workout', 'gym', 'techno', 'house', 'upbeat', 'high tempo', 'drum and bass',
        'dnb', 'phonk', 'hardstyle', 'pump', 'cardio', 'running', 'fitness',
        'hardcore', 'jumpstyle', 'crossfit', 'tabata', 'power metal'
    ],
    'Driving': [
        'driving', 'road trip', 'classic rock', 'synthwave', 'yacht rock',
        'highway', 'night drive', 'outrun', 'retrowave', 'vaporwave', 'soft rock',
        'cruising', 'radio'
    ],
    'Chill': [
        'chill', 'lo-fi', 'downtempo', 'ambient', 'chillhop', 'acoustic',
        'study', 'relax', 'lounge', 'trip hop', 'meditation', 'easy listening',
        'coffee shop', 'sleep', 'rain', 'yoga', 'balearic', 'chillout'
    ],
    'Easy Listening': [
        'easy listening', 'adult contemporary', 'soft rock', 'lounge', 'exotica',
        'muzak', 'elevator music', 'light music', 'orchestral pop', 'space age pop'
    ],
    'New Age': ['new age', 'healing', 'meditative', 'nature sounds', 'gregorian chant'],
    'Instrumental': ['instrumental', 'soundtrack', 'score', 'cinematic', 'video game music', 'post-rock'],
}

# Songs that don't match any bucket go here
UNSORTED_PLAYLIST_NAME = "Unsorted"

# Safety: Set to True to run main.py with read-only API calls (eg fetch tracks/playlists), without making 'write' API calls (eg add/remove tracks).
DRY_RUN = False

# Batch Size: Maximum number of tracks to process per run.
# Set to None to process all new tracks.
MAX_TRACKS_TO_PROCESS = 50

# Set to True to force a re-fetch of playlists from Spotify, ignoring the local database cache.
# Useful if you created a playlist manually and want the script to see it immediately.
RESET_PLAYLIST_CACHE = False