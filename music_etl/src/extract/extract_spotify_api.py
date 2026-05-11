"""
Extração de dados da Spotify Web API.

Extrai:
  - Playlists featured (destaque do Spotify)
  - Tracks de cada playlist
  - Audio features das tracks
  - Metadados de artistas

Todos os dados são guardados em formato JSON raw, sem modificações.
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


def _save_raw(data: dict | list, folder: Path, filename: str) -> Path:
    """Guarda dados brutos em JSON com timestamp no nome."""
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"{filename}_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug(f"Guardado: {path} ({path.stat().st_size / 1024:.1f} KB)")
    return path


def extract_featured_playlists(sp: spotipy.Spotify, config: dict) -> list[dict]:
    """
    Extrai playlists em destaque do Spotify para os mercados configurados.

    Args:
        sp: cliente Spotify autenticado
        config: dicionário de configuração

    Returns:
        Lista de dicionários com metadados de cada playlist
    """
    limit = config["spotify"]["playlist_limit"]
    pages = int(config.get("extraction", {}).get("api", {}).get("retry_attempts", 3))
    markets = config["spotify"]["markets"]
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "playlists"

    all_playlists = []

    for market in markets:
        logger.info(f"A extrair playlists featured para mercado: {market}")
        offset = 0

        for page in range(5):  # 5 páginas * 50 = 250 playlists por mercado
            try:
                result = sp.featured_playlists(
                    country=market,
                    limit=limit,
                    offset=offset,
                )
                items = result.get("playlists", {}).get("items", [])
                if not items:
                    logger.info(f"Sem mais playlists para {market} na página {page}")
                    break

                # Adiciona metadata de extração
                for item in items:
                    if item:
                        item["_extracted_market"] = market
                        item["_extracted_at"] = datetime.now().isoformat()
                        all_playlists.append(item)

                logger.info(f"  Página {page + 1}: {len(items)} playlists ({market})")
                offset += limit
                time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])

            except spotipy.SpotifyException as e:
                logger.error(f"Erro ao extrair playlists ({market}, offset={offset}): {e}")
                break

    # Guarda os dados brutos
    saved_path = _save_raw(all_playlists, raw_dir, "featured_playlists")
    logger.success(f"Total de playlists extraídas: {len(all_playlists)} -> {saved_path}")
    return all_playlists


def extract_playlist_tracks(
    sp: spotipy.Spotify,
    playlists: list[dict],
    config: dict,
    max_playlists: int = 50,
) -> list[dict]:
    """
    Extrai as tracks de cada playlist.

    Args:
        sp: cliente Spotify autenticado
        playlists: lista de playlists obtida de extract_featured_playlists
        config: dicionário de configuração
        max_playlists: limite de playlists a processar (para não exceder rate limits)

    Returns:
        Lista de dicionários com info de cada track + playlist de origem
    """
    limit = config["spotify"]["tracks_limit"]
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "tracks"
    all_tracks = []
    processed = 0

    playlists_to_process = [p for p in playlists if p is not None][:max_playlists]
    logger.info(f"A extrair tracks de {len(playlists_to_process)} playlists...")

    for playlist in playlists_to_process:
        playlist_id = playlist.get("id")
        playlist_name = playlist.get("name", "Unknown")

        if not playlist_id:
            continue

        try:
            offset = 0
            playlist_tracks = []

            while True:
                result = sp.playlist_tracks(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    fields="items(track(id,name,duration_ms,explicit,popularity,preview_url,track_number,"
                           "artists(id,name),album(id,name,release_date,total_tracks))),next",
                )

                items = result.get("items", [])
                if not items:
                    break

                for item in items:
                    track = item.get("track")
                    if track and track.get("id"):
                        track["_playlist_id"] = playlist_id
                        track["_playlist_name"] = playlist_name
                        track["_extracted_at"] = datetime.now().isoformat()
                        playlist_tracks.append(track)

                if not result.get("next"):
                    break
                offset += limit
                time.sleep(0.1)

            all_tracks.extend(playlist_tracks)
            processed += 1

            if processed % 10 == 0:
                logger.info(f"  Processadas {processed}/{len(playlists_to_process)} playlists | Total tracks: {len(all_tracks)}")

            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])

        except spotipy.SpotifyException as e:
            logger.error(f"Erro ao extrair tracks de '{playlist_name}' ({playlist_id}): {e}")
            continue

    saved_path = _save_raw(all_tracks, raw_dir, "playlist_tracks")
    logger.success(f"Total de tracks extraídas: {len(all_tracks)} -> {saved_path}")
    return all_tracks


def extract_audio_features(
    sp: spotipy.Spotify,
    tracks: list[dict],
    config: dict,
) -> list[dict]:
    """
    Extrai audio features para todas as tracks (em batches de 100).

    Audio features incluem: danceability, energy, key, loudness,
    speechiness, acousticness, instrumentalness, liveness, valence, tempo, etc.

    Args:
        sp: cliente Spotify autenticado
        tracks: lista de tracks obtida de extract_playlist_tracks
        config: dicionário de configuração

    Returns:
        Lista de dicionários com audio features por track_id
    """
    batch_size = config["spotify"]["audio_features_batch_size"]
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "audio_features"

    # Deduplica track IDs
    track_ids = list({t["id"] for t in tracks if t.get("id")})
    logger.info(f"A extrair audio features para {len(track_ids)} tracks únicas (batches de {batch_size})...")

    all_features = []
    errors = 0

    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(track_ids) + batch_size - 1) // batch_size

        try:
            features = sp.audio_features(batch)
            valid = [f for f in features if f is not None]
            all_features.extend(valid)

            logger.info(f"  Batch {batch_num}/{total_batches}: {len(valid)}/{len(batch)} features obtidas")
            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])

        except spotipy.SpotifyException as e:
            logger.error(f"Erro no batch {batch_num}: {e}")
            errors += 1
            time.sleep(config["extraction"]["api"]["retry_delay_seconds"])

    saved_path = _save_raw(all_features, raw_dir, "audio_features")
    logger.success(
        f"Audio features extraídas: {len(all_features)} tracks "
        f"({errors} batches com erro) -> {saved_path}"
    )
    return all_features


def extract_artists(
    sp: spotipy.Spotify,
    tracks: list[dict],
    config: dict,
    batch_size: int = 50,
) -> list[dict]:
    """
    Extrai metadados de artistas únicos a partir das tracks extraídas.

    Args:
        sp: cliente Spotify autenticado
        tracks: lista de tracks
        config: dicionário de configuração
        batch_size: número de artistas por chamada (max 50)

    Returns:
        Lista de dicionários com metadados de cada artista
    """
    raw_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "artists"

    # Recolhe todos os artist_ids únicos
    artist_ids = set()
    for track in tracks:
        for artist in track.get("artists", []):
            if artist.get("id"):
                artist_ids.add(artist["id"])

    artist_ids = list(artist_ids)
    logger.info(f"A extrair metadados de {len(artist_ids)} artistas únicos...")

    all_artists = []
    errors = 0

    for i in range(0, len(artist_ids), batch_size):
        batch = artist_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(artist_ids) + batch_size - 1) // batch_size

        try:
            result = sp.artists(batch)
            artists = result.get("artists", [])
            valid = [a for a in artists if a is not None]
            all_artists.extend(valid)

            if batch_num % 5 == 0 or batch_num == total_batches:
                logger.info(f"  Batch {batch_num}/{total_batches}: {len(valid)} artistas")
            time.sleep(config["extraction"]["api"]["rate_limit_sleep_seconds"])

        except spotipy.SpotifyException as e:
            logger.error(f"Erro no batch de artistas {batch_num}: {e}")
            errors += 1
            time.sleep(config["extraction"]["api"]["retry_delay_seconds"])

    saved_path = _save_raw(all_artists, raw_dir, "artists")
    logger.success(
        f"Artistas extraídos: {len(all_artists)} "
        f"({errors} erros) -> {saved_path}"
    )
    return all_artists


def run_spotify_extraction(max_playlists: int = 50) -> dict:
    """
    Executa a extração completa da Spotify Web API.

    Sequência:
      1. Autentica com a API
      2. Extrai playlists featured
      3. Extrai tracks dessas playlists
      4. Extrai audio features das tracks
      5. Extrai metadados dos artistas

    Args:
        max_playlists: número máximo de playlists a processar

    Returns:
        Dicionário com resumo da extração
    """
    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - SPOTIFY WEB API")
    logger.info("=" * 60)
    start_time = datetime.now()

    config = load_config()
    sp = get_spotify_client()

    # 1. Playlists
    playlists = extract_featured_playlists(sp, config)

    # 2. Tracks
    tracks = extract_playlist_tracks(sp, playlists, config, max_playlists=max_playlists)

    # 3. Audio Features
    features = extract_audio_features(sp, tracks, config)

    # 4. Artistas
    artists = extract_artists(sp, tracks, config)

    elapsed = (datetime.now() - start_time).total_seconds()

    summary = {
        "extracted_at": start_time.isoformat(),
        "duration_seconds": round(elapsed, 1),
        "playlists_count": len(playlists),
        "tracks_count": len(tracks),
        "unique_tracks": len({t["id"] for t in tracks if t.get("id")}),
        "audio_features_count": len(features),
        "artists_count": len(artists),
    }

    # Guarda resumo
    summary_path = Path(config["paths"]["raw_data"]) / "spotify_api" / "extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)
    logger.success(f"EXTRAÇÃO CONCLUÍDA em {elapsed:.1f}s")
    logger.info(f"  Playlists:      {summary['playlists_count']}")
    logger.info(f"  Tracks:         {summary['tracks_count']}")
    logger.info(f"  Tracks únicas:  {summary['unique_tracks']}")
    logger.info(f"  Audio features: {summary['audio_features_count']}")
    logger.info(f"  Artistas:       {summary['artists_count']}")
    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    run_spotify_extraction(max_playlists=50)
