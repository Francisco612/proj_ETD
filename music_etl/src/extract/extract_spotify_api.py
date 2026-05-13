"""
Extração de dados da Spotify Web API.

Estratégia (pós restrições 2024-2026):
  - /me/playlists         → playlists do utilizador autenticado (acesso garantido)
  - /me/top/tracks        → top tracks pessoais (requer OAuth)
  - /me/top/artists       → top artistas pessoais (requer OAuth)
  - /search               → tracks por género (acesso garantido)
  - /audio-features       → features de áudio por batch
  - /artists              → metadados de artistas por batch

Nota: playlists criadas pelo Spotify (owner=spotify) foram removidas
da API pública em 2024. Apenas playlists do utilizador são acessíveis.
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

# Géneros para pesquisa de tracks via /search
GENRE_SEARCHES = [
    "genre:pop",
    "genre:hip-hop",
    "genre:rock",
    "genre:electronic",
    "genre:jazz",
    "genre:classical",
    "genre:r-n-b",
    "genre:latin",
    "genre:indie",
    "genre:metal",
    "genre:soul",
    "genre:dance",
    "year:2024",
    "year:2023",
    "year:2022",
]


def _save_raw(data: dict | list, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"{filename}_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug(f"Guardado: {path} ({path.stat().st_size / 1024:.1f} KB)")
    return path


def extract_user_playlists(sp: spotipy.Spotify, config: dict) -> list[dict]:
    """
    Extrai as playlists do utilizador autenticado.
    Inclui playlists próprias e seguidas (públicas e privadas com scope).
    """
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "playlists"
    all_playlists = []
    offset = 0
    limit = 50

    logger.info("A extrair playlists do utilizador autenticado...")

    while True:
        try:
            result = sp.current_user_playlists(limit=limit, offset=offset)
            items = result.get("items", [])
            if not items:
                break

            for item in items:
                if item and item.get("id"):
                    item["_source"] = "user_playlists"
                    item["_extracted_at"] = datetime.now().isoformat()
                    all_playlists.append(item)

            logger.info(f"  Offset {offset}: {len(items)} playlists")

            if not result.get("next"):
                break
            offset += limit
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"Erro a extrair playlists do utilizador: {e}")
            break

    logger.success(f"Playlists do utilizador: {len(all_playlists)}")
    saved_path = _save_raw(all_playlists, raw_dir, "user_playlists")
    return all_playlists


def extract_user_top_tracks(sp: spotipy.Spotify, config: dict) -> list[dict]:
    """
    Extrai as top tracks do utilizador nos 3 períodos temporais.
    Endpoint: GET /me/top/tracks
    """
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "tracks"
    all_top_tracks = []
    time_ranges = ["short_term", "medium_term", "long_term"]

    logger.info("A extrair top tracks do utilizador (3 períodos)...")

    for time_range in time_ranges:
        try:
            result = sp.current_user_top_tracks(limit=50, time_range=time_range)
            items = result.get("items", [])

            for track in items:
                if track and track.get("id"):
                    track["_source"] = "user_top_tracks"
                    track["_time_range"] = time_range
                    track["_extracted_at"] = datetime.now().isoformat()
                    all_top_tracks.append(track)

            logger.info(f"  [{time_range}]: {len(items)} tracks")
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"  Erro em {time_range}: {e}")

    saved_path = _save_raw(all_top_tracks, raw_dir, "user_top_tracks")
    logger.success(f"Top tracks extraídas: {len(all_top_tracks)} -> {saved_path}")
    return all_top_tracks


def extract_user_top_artists(sp: spotipy.Spotify, config: dict) -> list[dict]:
    """
    Extrai os top artistas do utilizador nos 3 períodos temporais.
    Endpoint: GET /me/top/artists
    """
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "artists"
    all_top_artists = []
    time_ranges = ["short_term", "medium_term", "long_term"]

    logger.info("A extrair top artistas do utilizador (3 períodos)...")

    for time_range in time_ranges:
        try:
            result = sp.current_user_top_artists(limit=50, time_range=time_range)
            items = result.get("items", [])

            for artist in items:
                if artist and artist.get("id"):
                    artist["_source"] = "user_top_artists"
                    artist["_time_range"] = time_range
                    artist["_extracted_at"] = datetime.now().isoformat()
                    all_top_artists.append(artist)

            logger.info(f"  [{time_range}]: {len(items)} artistas")
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"  Erro em {time_range}: {e}")

    saved_path = _save_raw(all_top_artists, raw_dir, "user_top_artists")
    logger.success(f"Top artistas extraídos: {len(all_top_artists)} -> {saved_path}")
    return all_top_artists


def extract_tracks_by_genre_search(sp: spotipy.Spotify, config: dict) -> list[dict]:
    """
    Pesquisa tracks por género via /search (limit=10, máximo actual).
    Produz uma amostra diversificada por género para análise.
    """
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "tracks"
    all_tracks = []
    seen_ids = set()

    logger.info(f"A pesquisar tracks por {len(GENRE_SEARCHES)} géneros/anos...")

    for query in GENRE_SEARCHES:
        try:
            result = sp.search(q=query, type="track", limit=10)
            items = result.get("tracks", {}).get("items", [])

            added = 0
            for track in items:
                if track and track.get("id") and track["id"] not in seen_ids:
                    track["_source"] = "genre_search"
                    track["_search_query"] = query
                    track["_extracted_at"] = datetime.now().isoformat()
                    all_tracks.append(track)
                    seen_ids.add(track["id"])
                    added += 1

            logger.info(f"  ['{query}']: {added} tracks novas")
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"  Erro em '{query}': {e}")

    saved_path = _save_raw(all_tracks, raw_dir, "genre_search_tracks")
    logger.success(f"Tracks por pesquisa de género: {len(all_tracks)} -> {saved_path}")
    return all_tracks


def extract_playlist_tracks(
    sp: spotipy.Spotify,
    playlists: list[dict],
    config: dict,
    max_playlists: int = 50,
) -> list[dict]:
    """Extrai tracks das playlists do utilizador."""
    limit = config["spotify"]["tracks_limit"]
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "tracks"
    all_tracks = []

    playlists_to_process = [p for p in playlists if p][:max_playlists]
    logger.info(f"A extrair tracks de {len(playlists_to_process)} playlists do utilizador...")

    for playlist in playlists_to_process:
        pid = playlist.get("id")
        pname = playlist.get("name", "Unknown")
        if not pid:
            continue

        try:
            offset = 0
            count = 0
            while True:
                result = sp.playlist_tracks(pid, limit=limit, offset=offset)
                items = result.get("items", [])
                if not items:
                    break

                for item in items:
                    track = item.get("track")
                    if not track or not track.get("id"):
                        continue
                    if track.get("type") != "track":
                        continue
                    track["_playlist_id"] = pid
                    track["_playlist_name"] = pname
                    track["_source"] = "user_playlist_tracks"
                    track["_extracted_at"] = datetime.now().isoformat()
                    all_tracks.append(track)
                    count += 1

                if not result.get("next"):
                    break
                offset += limit
                time.sleep(0.2)

            logger.info(f"  ✓ '{pname}': {count} tracks")
            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])

        except spotipy.SpotifyException as e:
            logger.warning(f"  ✗ '{pname}': {e.http_status} — a saltar")
            continue
        except Exception as e:
            logger.error(f"  ✗ '{pname}': {e}")
            continue

    saved_path = _save_raw(all_tracks, raw_dir, "playlist_tracks")
    logger.success(f"Tracks de playlists: {len(all_tracks)} -> {saved_path}")
    return all_tracks


def extract_audio_features(
    sp: spotipy.Spotify,
    tracks: list[dict],
    config: dict,
) -> list[dict]:
    """Extrai audio features em batches de 100."""
    batch_size = config["spotify"]["audio_features_batch_size"]
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "audio_features"

    track_ids = list({t["id"] for t in tracks if t.get("id")})
    logger.info(f"A extrair audio features para {len(track_ids)} tracks únicas...")

    all_features = []
    total_batches = (len(track_ids) + batch_size - 1) // batch_size if track_ids else 0

    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        try:
            features = sp.audio_features(batch)
            valid = [f for f in features if f is not None]
            all_features.extend(valid)
            if batch_num % 5 == 0 or batch_num == total_batches:
                logger.info(f"  Batch {batch_num}/{total_batches}: {len(all_features)} acumuladas")
            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])
        except Exception as e:
            logger.error(f"  Erro batch {batch_num}: {e}")

    saved_path = _save_raw(all_features, raw_dir, "audio_features")
    logger.success(f"Audio features extraídas: {len(all_features)} -> {saved_path}")
    return all_features


def extract_artists_from_tracks(
    sp: spotipy.Spotify,
    tracks: list[dict],
    config: dict,
    batch_size: int = 50,
) -> list[dict]:
    """Extrai metadados de artistas únicos a partir das tracks."""
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "artists"

    artist_ids = list({
        a["id"]
        for t in tracks
        for a in t.get("artists", [])
        if a.get("id")
    })
    logger.info(f"A extrair metadados de {len(artist_ids)} artistas únicos...")

    all_artists = []
    total_batches = (len(artist_ids) + batch_size - 1) // batch_size if artist_ids else 0

    for i in range(0, len(artist_ids), batch_size):
        batch = artist_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        try:
            result = sp.artists(batch)
            valid = [a for a in result.get("artists", []) if a]
            all_artists.extend(valid)
            if batch_num % 5 == 0 or batch_num == total_batches:
                logger.info(f"  Batch {batch_num}/{total_batches}: {len(all_artists)} acumulados")
            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])
        except Exception as e:
            logger.error(f"  Erro batch artistas {batch_num}: {e}")

    saved_path = _save_raw(all_artists, raw_dir, "artists")
    logger.success(f"Artistas extraídos: {len(all_artists)} -> {saved_path}")
    return all_artists


def run_spotify_extraction(max_playlists: int = 50) -> dict:
    """
    Executa a extração completa da Spotify Web API.

    Sequência:
      1. Playlists do utilizador autenticado
      2. Tracks dessas playlists
      3. Top tracks pessoais (3 períodos)
      4. Top artistas pessoais (3 períodos)
      5. Tracks por pesquisa de género
      6. Audio features de todas as tracks
      7. Metadados de artistas
    """
    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - SPOTIFY WEB API")
    logger.info("=" * 60)
    start_time = datetime.now()

    config = load_config()
    sp = get_spotify_client()

    # 1. Playlists do utilizador
    playlists = extract_user_playlists(sp, config)

    # 2. Tracks das playlists
    playlist_tracks = extract_playlist_tracks(sp, playlists, config, max_playlists=max_playlists)

    # 3. Top tracks pessoais
    top_tracks = extract_user_top_tracks(sp, config)

    # 4. Top artistas pessoais
    top_artists = extract_user_top_artists(sp, config)

    # 5. Tracks por género (diversidade para análise)
    genre_tracks = extract_tracks_by_genre_search(sp, config)

    # Combina todas as tracks para audio features e artistas
    all_tracks = playlist_tracks + top_tracks + genre_tracks

    # 6. Audio features
    features = extract_audio_features(sp, all_tracks, config)

    # 7. Artistas (tracks + top artistas já extraídos)
    all_artists_from_tracks = extract_artists_from_tracks(sp, all_tracks, config)

    elapsed = (datetime.now() - start_time).total_seconds()

    summary = {
        "extracted_at": start_time.isoformat(),
        "duration_seconds": round(elapsed, 1),
        "playlists_count": len(playlists),
        "playlist_tracks_count": len(playlist_tracks),
        "top_tracks_count": len(top_tracks),
        "genre_search_tracks_count": len(genre_tracks),
        "total_tracks": len(all_tracks),
        "unique_tracks": len({t["id"] for t in all_tracks if t.get("id")}),
        "audio_features_count": len(features),
        "top_artists_count": len(top_artists),
        "artists_from_tracks_count": len(all_artists_from_tracks),
    }

    summary_path = Path(config["paths"]["raw_data"]) / "spotify_api" / "extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)
    logger.success(f"EXTRAÇÃO CONCLUÍDA em {elapsed:.1f}s")
    logger.info(f"  Playlists:           {summary['playlists_count']}")
    logger.info(f"  Tracks (playlists):  {summary['playlist_tracks_count']}")
    logger.info(f"  Tracks (top pessoal):{summary['top_tracks_count']}")
    logger.info(f"  Tracks (género):     {summary['genre_search_tracks_count']}")
    logger.info(f"  Tracks únicas:       {summary['unique_tracks']}")
    logger.info(f"  Audio features:      {summary['audio_features_count']}")
    logger.info(f"  Artistas:            {summary['artists_from_tracks_count']}")
    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    run_spotify_extraction(max_playlists=50)