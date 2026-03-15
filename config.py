"""
Configuration settings for the Spotify Liked Songs Organiser application.
This centralises all environment variables and categorisation rules to maintain 
a single source of truth for the sorting logic and API configurations.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

APP_NAME = "liked songs manager"
APP_VERSION = "2.2.0"

SCOPE = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private"

# The maximum number of genre playlists a single song can be assigned to.
# Set to None for no limit.
MAX_GENRE_PLAYLISTS_PER_SONG = 2

UNDEFINED_TAG = "Undefined"

IS_DRY_RUN = False

# This maximum only applies to Last.fm (Spotify limit is defined by user in CLI)
MAX_TRACKS_TO_PROCESS = 1000

SHOULD_RESET_PLAYLIST_CACHE = False

GENRE_MAPPING = {
    # -------------------------------------------------------------------------
    # 1. SPECIFIC SUB-GENRES & NICHE STYLES
    # -------------------------------------------------------------------------

    # --- Specific Electronic & Dance ---
    'Techno': ['techno', 'detroit techno', 'minimal techno', 'acid techno', 'dub techno', 'industrial techno', 'hard techno', 'melodic techno'],
    'House': [
        'house', 'deep house', 'tech house', 'progressive house', 'acid house',
        'tropical house', 'chicago house', 'future house', 'bass house', 'french house', 'lo-fi house', 'microhouse', 'electro house'
    ],
    'Drum and Bass': ['drum and bass', 'liquid funk', 'neurofunk', 'jump up', 'darkstep', 'techstep', 'jungle', 'ragga jungle', 'darkside'],
    'Garage': ['garage', 'uk garage', 'speed garage', '2-step', 'future garage', 'bassline'],
    'Synthpop': ['synthpop', 'electropop', 'futurepop', 'dark wave', 'coldwave', 'minimal wave'],
    'Hyperpop': ['hyperpop', 'glitchcore', 'digicore', 'pc music', 'bubblegum bass', 'deconstructed club'],
    'UK Indie': ['britpop', 'art pop', 'mod revival', 'neo-psychedelia', 'post-britpop', 'shoegaze influence', 'madchester', 'baggy', 'alternative dance', 'grebo', ('uk', 'indie pop'), ('british', '90s'), ('uk', '90s rock')],

    # --- Specific Rock & Metal ---
    'Heavy Metal': ['heavy metal', 'thrash metal', 'doom metal', 'power metal', 'speed metal', 'nwobhm', 'hair metal'],
    'Death Metal': [
        'death metal', 'black metal', 'metalcore', 'groove metal', 'nu metal', 'sludge metal', 'symphonic metal', 
        'folk metal', 'viking metal', 'industrial metal', 'gothic metal', 'grindcore', 'djent', 'deathcore', 
        'post-metal', 'symphonic black metal'],
    'Hard Rock': ['hard rock', 'blues rock', 'glam rock', 'arena rock', 'sleaze rock', 'stoner rock', 'psychedelic rock', 'alternative metal', 'funk metal', 'southern rock', 'industrial rock', 'power pop', ('blues', 'rock')],
    'Punk & Post-Punk': [
        'punk', 'post-punk', 'hardcore punk', 'pop punk', 'skate punk', 'new wave', 'no wave', 
        'art punk', 'garage punk', 'oi', 'crust punk', 'ska punk', 'riot grrrl', 'post-hardcore', 'd-beat', ('punk', 'rock')],
    'Grunge': ['grunge', 'post-grunge', 'seattle sound'],
    'Shoegaze': ['shoegaze', 'dream pop', 'ethereal wave', 'nu gaze', 'blackgaze', 'noise pop', 'slowcore', 'sadcore', ('indie', 'ambient'), ('rock', 'ethereal'), ('indie', 'dreamy')],
    'Noise Rock': ['noise rock', 'industrial rock', 'no wave', 'math rock', 'noise'],
    'Psychedelic Rock': ['psychedelic rock', 'acid rock', 'neo-psychedelia', 'space rock', 'krautrock'],
    'Emo': ['emo', 'emo rap', 'screamo', 'midwest emo', 'emotional hardcore', 'skramz'],

    # --- Specific Hip Hop ---
    'Trap': ['trap', 'southern hip hop', 'atlanta hip hop', 'trap soul', 'latin trap', 'crunk', 'plugg'],
    'Drill': ['drill', 'uk drill', 'chicago drill', 'brooklyn drill', 'ny drill'],
    'Grime': ['grime', 'sublow', 'eskibeat'],
    'Jazz-Rap': ['jazz rap', 'acid jazz', 'jazz hop'],
    'Horrorcore': ['horrorcore', 'memphis rap', 'phonk'],
    'East Coast Hip Hop': ['east coast hip hop', 'east coast rap', 'new york hip hop', 'boom bap', 'mafioso rap'],
    'West Coast Hip Hop': ['west coast hip hop', 'west coast rap', 'g-funk', 'gangsta rap', 'hyphy', 'compton'],

    # --- Specific Regional Rap ---
    'Dutch Rap': ['dutch rap', 'nederhop', ('dutch', 'hip hop'), ('netherlands', 'rap')],
    'German Rap': ['german rap', 'deutschrap', ('german', 'hip hop'), ('germany', 'rap'), ('austria', 'rap'), ('swiss', 'rap')],
    'French Rap': ['french rap', 'cloud rap francais', ('french', 'hip hop'), ('france', 'rap')],
    'Australian Rap': ['australian rap', 'aussie hip hop', ('australian', 'hip hop'), ('australia', 'rap')],

    # --- Retro & Specific Pop/Soul ---
    'Disco': ['disco', 'nu-disco', 'italo disco', 'euro disco', 'post-disco', 'boogie', 'space disco', ('70s', 'dance', 'retro')],
    'Motown': ['motown', 'detroit soul', ('soul', 'detroit', '60s')],
    'Vintage R&B': ['northern soul', 'mod', 'rare soul', 'doo-wop', 'street corner symphony', ('soul', '60s', 'r&b'), ('r&b', 'soul', '50s'), ('soul', '70s', 'r&b')],
    'Funk': ['funk', 'p-funk', 'funk rock', 'deep funk', 'go-go', 'boogie', ('soul', 'groove', '70s')],

    # --- Specific Regional / Cultural Styles ---
    'Afrobeats': ['afrobeats', 'afropop', 'afro fusion', 'alte', 'naija', 'amapiano'],
    'K-pop': ['k-pop', 'k-rock', 'k-hip hop', 'korean r&b'],
    'Bollywood': ['bollywood', 'filmi', 'hindi film', 'indian pop'],
    'Punjabi Pop': ['punjabi pop', 'bhangra pop', 'punjabi hip hop', ('punjabi', 'bhangra', 'pop'), ('bhangra', 'hip hop')],
    'Desi': ['desi', 'punjabi', 'punjabi folk', ('india', 'folk'), ('pakistan', 'folk'), ('punjabi', 'folk')],
    'Qawwali': ['sufi', 'sufi rock', 'qawwali fusion', 'qawwali', 'ghazal', ('islamic', 'folk'), ('pakistan', 'traditional')],
    'Reggaeton': ['reggaeton', 'neoperreo', 'cubaton', ('latin', 'reggae'), ('latin', 'dancehall')],
    'Dancehall': ['dancehall', 'bashment', 'ragga', ('caribbean', 'dance'), ('jamaica', 'dance')],
    'Salsa': ['salsa', 'bachata', 'merengue', 'cumbia', 'vallenato', 'tropical'],
    'Latin Urban': ['latin urbano', 'latin hip hop', 'latin trap', 'dembow', ('latin', 'hip hop'), ('latin', 'rap'), ('latin', 'trap'), ('spanish', 'rap')],
    'Flamenco': ['flamenco', 'nuevo flamenco', 'rumba flamenca', 'flamenco pop', ('spanish', 'folk'), ('spain', 'acoustic')],

    # -------------------------------------------------------------------------
    # 2. BROAD / UMBRELLA GENRES
    # -------------------------------------------------------------------------

    # --- Electronic ---
    'Chill Electronic': ['downtempo', 'idm', 'trip hop', 'chillout', 'ambient', ('electronic', 'chill'), ('electronic', 'relax'), ('electronic', 'ambient')],
    'Club Electronic': ['electronic', 'breakbeat', 'electro', 'complextro', 'glitch', 'edm', ('electronic', 'party'), ('electronic', 'club')],
    'Dance': ['dance', 'eurodance', 'dance-pop', 'club', 'party', 'vocal trance'],

    # --- Indie ---
    'Indie Rock': ['indie rock', 'alternative', 'slacker rock', 'post-punk revival', ('indie', 'rock')],
    'Indie Pop': ['indie pop', 'chamber pop', 'twee pop', 'indietronica', 'bedroom pop', 'jangle pop', ('indie', 'pop')],
    'Indie Folk': ['indie folk', 'freak folk', 'anti-folk', 'singer-songwriter', ('indie', 'folk'), ('indie', 'acoustic')],

    'R&B': ['r&b', 'contemporary r&b', 'quiet storm', 'slow jam', 'new jack swing', ('urban', 'pop'), ('soul', 'pop')],
    'Alternative R&B': ['alternative r&b', 'neo-soul', 'future soul', ('alternative', 'indie', 'r&b')],
    'Soul': ['soul', 'blue-eyed soul', 'psychedelic soul', 'southern soul', 'chicago soul', ('classic', 'r&b')],
    'Jazz': ['jazz', 'smooth jazz', 'fusion', 'bebop', 'swing', 'big band', 'cool jazz', 'vocal jazz', 'hard bop', ('jazz', 'soul')],
    'Blues': ['blues', 'delta blues', 'chicago blues', 'electric blues', 'blues rock', 'country blues', ('acoustic', 'blues')],
    'Country': [
        'country', 'classic country', 'outlaw country', 'country pop', 'country rock', 
        'western swing', 'honky tonk', 'nashville sound', 'bro-country', 'alt-country', ('country', 'pop'), ('country', 'rock')
    ],
    'Folk': ['folk', 'contemporary folk', 'traditional folk'],
    'Americana': ['americana', 'roots music', 'texas country', 'bluegrass'],
    'Latin': ['latin pop', 'musica mexicana', 'ranchera', 'norteno', 'mariachi', 'bolero'],
    'Reggae': ['reggae', 'roots reggae', 'dub', 'rocksteady', 'lovers rock', 'ska'],
    'Classical': [
        'classical', 'baroque', 'chamber music', 'symphony', 'concerto', 
        'sonata', 'choral', 'renaissance', 'medieval', 'contemporary classical', ('orchestral', 'instrumental')
    ],
    'Opera': ['opera', 'operetta', 'aria', 'bel canto'],

    # --- Broad Regional Buckets ---
    'African Music': ['african', 'highlife', 'soukous', 'juju', 'coupé-décalé', 'afrobeat', 'desert blues', ('africa', 'traditional')],
    'Brazilian Music': ['brazilian', 'samba', 'bossa nova', 'mpb', 'baile funk', 'tropicalia', 'pagode', 'forro', 'sertanejo', ('brazil', 'pop'), ('brazilian', 'acoustic')],
    'French Music': ['french', 'chanson', 'variete francaise', 'nouvelle scene', ('french', 'acoustic'), ('france', 'traditional')],
    'French Pop': ['french pop', 'yé-yé', 'french indie pop', ('france', 'pop')],
    'Italian Music': ['italian', 'italian pop', 'canzone napoletana', 'opera pop', ('italy', 'pop')],
    'Turkish Music': ['turkish', 'turkish pop', 'turkish rock', 'anadolu rock', 'arabesque', ('turkey', 'rock')],
    'Middle Eastern Music': ['middle eastern', 'arabic pop', 'dabke', 'khaliji', 'shaabi', 'levantine', ('middle east', 'traditional')],
    'Persian Music': ['persian', 'persian pop', 'bandari', ('iran', 'pop'), ('iran', 'persian', 'traditional')],
    'Japanese Music': ['j-pop', 'j-rock', 'city pop', 'kayokyoku', 'visual kei', 'anime', 'shibuya-kei', ('japanese', 'pop'), ('japan', 'rock')],
    'Chinese Music': ['c-pop', 'mandopop', 'cantopop', 'chinese indie', ('chinese', 'pop'), ('china', 'indie')],
    'Pakistani Music': ['pakistani pop', 'lollywood', 'pakistani rock'],
    "Indian Music": ["indian","indian pop","bollywood","filmi","hindi","desi", "hindustani","indian classical","bhangra","tollywood","kollywood","raga","sitar","tabla","indian indie"]
}
