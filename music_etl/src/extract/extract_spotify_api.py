# extract_spotify_api.py

"""
Extração de dados da Spotify Web API.
Versão robusta contra:
- 403 Forbidden
- playlists inválidas
- playlists privadas
- market restrictions
- playlists sem tracks
"""

import json
import time
from pathlib import Path
from datetime import datetime

import spotipy

from src.extract.spotify_auth import get_spotify_client
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("extract_spotify")

# Apenas playlists oficiais / confiáveis
KNOWN_PLAYLIST_QUERIES = {
    "pop": ["Today's Top Hits", "Hot Hits Portugal"],
    "hiphop": ["RapCaviar", "Most Necessary"],
    "rock": ["Rock Classics", "Rock This"],
    "electronic": ["mint", "Electronic Circus"],
    "jazz": ["Jazz Classics", "Jazz Vibes"],
    "classical": ["Classical Essentials", "Classical New Releases"],
    "rnb": ["Are & Be", "R&B Hits"],
    "latin": ["Viva Latino", "Latin Pop Hits"],
    "chill": ["Chill Hits", "Lo-Fi Beats"],
    "indie": ["Indie Pop", "Indie Rock"],
    "workout": ["Beast Mode", "Power Workout"],
    "focus": ["Deep Focus", "Intense Studying"],
    "charts_pt": ["Top 50 - Portugal"],
    "charts_us": ["Top 50 - USA"],
    "viral": ["Viral 50 - Global"],
}

# Search terms mais limpos
SEARCH_TERMS = [
    "spotify editorial",
    "viral hits",
    "new music friday",
    "official pop",
    "official hip hop",
]


def _save_raw(data: dict | list, folder: Path, filename: str) -> Path:

    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = folder / f"{filename}_{timestamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.debug(
        f"Guardado: {path} "
        f"({path.stat().st_size / 1024:.1f} KB)"
    )

    return path


def extract_playlists(sp: spotipy.Spotify, config: dict) -> list[dict]:

    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "playlists"

    all_playlists = []
    seen_ids = set()

    logger.info("A localizar playlists oficiais por nome...")

    # ==========================================================
    # 1. PLAYLISTS OFICIAIS
    # ==========================================================

    for genre, queries in KNOWN_PLAYLIST_QUERIES.items():

        for query in queries:

            try:
                search_res = sp.search(
                    q=query,
                    type="playlist",
                    limit=5
                )

                items = search_res.get("playlists", {}).get("items", [])

                found = False

                for item in items:

                    if not item:
                        continue

                    owner_id = item.get("owner", {}).get("id", "")
                    pid = item.get("id")

                    # ignorar playlists sem owner válido
                    if not owner_id:
                        continue

                    if not pid or pid in seen_ids:
                        continue

                    full_playlist = sp.playlist(
                        pid,
                        fields=(
                            "id,"
                            "name,"
                            "description,"
                            "owner,"
                            "followers,"
                            "tracks.total,"
                            "public"
                        ),
                        market="from_token"
                    )

                    full_playlist["_category"] = genre
                    full_playlist["_source"] = "official_lookup"
                    full_playlist["_extracted_at"] = datetime.now().isoformat()

                    all_playlists.append(full_playlist)
                    seen_ids.add(pid)

                    logger.info(
                        f"  [{genre}] "
                        f"'{full_playlist.get('name')}': OK"
                    )

                    found = True
                    break

                if not found:
                    logger.warning(
                        f"  [{genre}] Nenhuma playlist oficial encontrada"
                    )

                time.sleep(0.2)

            except Exception as e:
                logger.warning(
                    f"  [{genre}] Erro ao localizar '{query}': {e}"
                )

    # ==========================================================
    # 2. PLAYLIST SEARCH EXTRA
    # ==========================================================

    logger.info(
        f"A pesquisar por {len(SEARCH_TERMS)} termos..."
    )

    for term in SEARCH_TERMS:

        try:
            result = sp.search(
                q=term,
                type="playlist",
                limit=10
            )

            items = result.get("playlists", {}).get("items", [])

            added = 0

            for item in items:

                if not item:
                    continue

                pid = item.get("id")

                if not pid or pid in seen_ids:
                    continue

                owner_id = item.get("owner", {}).get("id", "")
                public = item.get("public", False)

                # Ignorar privadas
                if public is False:
                    continue

                # Ignorar owners vazios
                if owner_id in ["", None]:
                    continue

                # Ignorar playlists pequenas
                total_tracks = item.get("tracks", {}).get("total", 0)

                if total_tracks < 5:
                    continue

                item["_category"] = "search"
                item["_search_term"] = term
                item["_source"] = "search"
                item["_extracted_at"] = datetime.now().isoformat()

                all_playlists.append(item)

                seen_ids.add(pid)

                added += 1

            logger.info(
                f"  ['{term}']: {added} playlists novas"
            )

            time.sleep(
                config["extraction"]["api"]["rate_limit_sleep_seconds"]
            )

        except Exception as e:
            logger.error(f"  Erro na pesquisa '{term}': {e}")

    saved_path = _save_raw(all_playlists, raw_dir, "playlists")

    logger.success(
        f"Total de playlists extraídas: "
        f"{len(all_playlists)} -> {saved_path}"
    )

    return all_playlists


def extract_playlist_tracks(
        sp: spotipy.Spotify,
        playlists: list[dict],
        config: dict,
        max_playlists: int = 50
) -> list[dict]:

    limit = config["spotify"]["tracks_limit"]

    raw_dir = (
            Path(config["paths"]["raw_data"])
            / "spotify_api"
            / "tracks"
    )

    all_tracks = []

    playlists_to_process = playlists[:max_playlists]

    logger.info(
        f"A extrair tracks de "
        f"{len(playlists_to_process)} playlists..."
    )

    for playlist in playlists_to_process:

        pid = playlist.get("id")
        pname = playlist.get("name", "Unknown")

        if not pid:
            continue

        total_extracted = 0

        try:

            offset = 0

            while True:

                result = sp.playlist_items(
                    pid,
                    offset=offset,
                    limit=limit,
                    market="from_token",
                    additional_types=("track",)
                )

                items = result.get("items", [])

                if not items:
                    break

                for item in items:

                    track_data = item.get("track")

                    # Ignorar episódios/podcasts/etc
                    if not track_data:
                        continue

                    if track_data.get("type") != "track":
                        continue

                    if not track_data.get("id"):
                        continue

                    track_data["_playlist_id"] = pid
                    track_data["_playlist_name"] = pname
                    track_data["_extracted_at"] = (
                        datetime.now().isoformat()
                    )

                    all_tracks.append(track_data)

                    total_extracted += 1

                if not result.get("next"):
                    break

                offset += limit

                time.sleep(0.2)

            logger.info(
                f"  OK: '{pname}' "
                f"({total_extracted} tracks)"
            )

        except spotipy.SpotifyException as e:

            logger.error(
                f"  Playlist bloqueada: '{pname}' | "
                f"status={e.http_status} | "
                f"msg={e.msg}"
            )

            continue

        except Exception as e:

            logger.error(
                f"  Erro inesperado em '{pname}': {e}"
            )

            continue

    _save_raw(all_tracks, raw_dir, "playlist_tracks")

    logger.success(
        f"Tracks extraídas: {len(all_tracks)}"
    )

    return all_tracks


def extract_audio_features(
        sp: spotipy.Spotify,
        tracks: list[dict],
        config: dict
) -> list[dict]:

    batch_size = config["spotify"]["audio_features_batch_size"]

    raw_dir = (
            Path(config["paths"]["raw_data"])
            / "spotify_api"
            / "audio_features"
    )

    track_ids = list({
        t["id"]
        for t in tracks
        if t.get("id")
    })

    logger.info(
        f"A extrair audio features para "
        f"{len(track_ids)} tracks únicas..."
    )

    all_features = []

    for i in range(0, len(track_ids), batch_size):

        batch = track_ids[i:i + batch_size]

        try:

            features = sp.audio_features(batch)

            all_features.extend([
                f for f in features
                if f is not None
            ])

            time.sleep(
                config["extraction"]["api"]["rate_limit_sleep_seconds"]
            )

        except Exception as e:
            logger.error(f"Erro features: {e}")

    _save_raw(all_features, raw_dir, "audio_features")

    return all_features


def extract_artists(
        sp: spotipy.Spotify,
        tracks: list[dict],
        config: dict,
        batch_size: int = 50
) -> list[dict]:

    raw_dir = (
            Path(config["paths"]["raw_data"])
            / "spotify_api"
            / "artists"
    )

    artist_ids = set()

    for track in tracks:

        for artist in track.get("artists", []):

            if artist.get("id"):
                artist_ids.add(artist["id"])

    artist_ids = list(artist_ids)

    logger.info(
        f"A extrair metadados de "
        f"{len(artist_ids)} artistas únicos..."
    )

    all_artists = []

    for i in range(0, len(artist_ids), batch_size):

        batch = artist_ids[i:i + batch_size]

        try:

            result = sp.artists(batch)

            all_artists.extend(
                result.get("artists", [])
            )

            time.sleep(
                config["extraction"]["api"]["rate_limit_sleep_seconds"]
            )

        except Exception as e:
            logger.error(f"Erro artistas: {e}")

    _save_raw(all_artists, raw_dir, "artists")

    return all_artists


def run_spotify_extraction(max_playlists: int = 50) -> dict:

    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - SPOTIFY WEB API")
    logger.info("=" * 60)

    start_time = datetime.now()

    config = load_config()

    sp = get_spotify_client()

    playlists = extract_playlists(sp, config)

    tracks = extract_playlist_tracks(
        sp,
        playlists,
        config,
        max_playlists=max_playlists
    )

    features = extract_audio_features(
        sp,
        tracks,
        config
    )

    artists = extract_artists(
        sp,
        tracks,
        config
    )

    elapsed = (
        datetime.now() - start_time
    ).total_seconds()

    summary = {
        "extracted_at": start_time.isoformat(),
        "duration_seconds": round(elapsed, 1),
        "playlists_count": len(playlists),
        "tracks_count": len(tracks),
        "unique_tracks": len({
            t["id"]
            for t in tracks
            if t.get("id")
        }),
        "audio_features_count": len(features),
        "artists_count": len(artists),
    }

    summary_path = (
            Path(config["paths"]["raw_data"])
            / "spotify_api"
            / "extraction_summary.json"
    )

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)

    logger.success(
        f"EXTRAÇÃO CONCLUÍDA em {elapsed:.1f}s"
    )

    return summary


if __name__ == "__main__":
    run_spotify_extraction(max_playlists=50)