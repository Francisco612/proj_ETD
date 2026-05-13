"""
Extração de metadados complementares da MusicBrainz API.

MusicBrainz é uma base de dados open-source de metadados musicais.
Usamos como fonte complementar para enriquecer géneros e info de artistas.

API: https://musicbrainz.org/doc/MusicBrainz_API
Rate limit: 1 req/segundo (sem autenticação)
"""

import json
import time
from pathlib import Path
from datetime import datetime

import requests

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("extract_musicbrainz")

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "MusicETLProject/1.0 (student-project; contact@example.com)",
    "Accept": "application/json",
}
RATE_LIMIT_SLEEP = 1.1  # segundos entre requests (respeita o limite de 1/s)


def search_artist(artist_name: str) -> dict | None:
    """
    Procura um artista na MusicBrainz pelo nome.

    Args:
        artist_name: nome do artista

    Returns:
        Primeiro resultado encontrado ou None
    """
    url = f"{MUSICBRAINZ_BASE_URL}/artist"
    params = {
        "query": f'artist:"{artist_name}"',
        "limit": 1,
        "fmt": "json",
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        artists = data.get("artists", [])
        return artists[0] if artists else None

    except requests.RequestException as e:
        logger.error(f"Erro ao pesquisar artista '{artist_name}': {e}")
        return None


def get_artist_details(mbid: str) -> dict | None:
    """
    Obtém detalhes completos de um artista pelo MusicBrainz ID (MBID).

    Args:
        mbid: MusicBrainz Identifier do artista

    Returns:
        Dicionário com detalhes do artista ou None
    """
    url = f"{MUSICBRAINZ_BASE_URL}/artist/{mbid}"
    params = {
        "inc": "tags+genres+ratings",
        "fmt": "json",
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        logger.error(f"Erro ao obter detalhes do artista MBID={mbid}: {e}")
        return None


def extract_artists_from_musicbrainz(
    artist_names: list[str],
    max_artists: int = 100,
) -> list[dict]:
    """
    Extrai metadados de artistas da MusicBrainz.

    Usa os nomes de artistas obtidos do Spotify para fazer lookup na MusicBrainz.
    Respeita o rate limit de 1 request/segundo.

    Args:
        artist_names: lista de nomes de artistas
        max_artists: máximo de artistas a processar

    Returns:
        Lista de dicionários com metadados enriquecidos
    """
    config = load_config()
    raw_dir = Path(config["paths"]["raw_data"]) / "musicbrainz"
    raw_dir.mkdir(parents=True, exist_ok=True)

    artists_to_process = artist_names[:max_artists]
    logger.info(f"A extrair {len(artists_to_process)} artistas da MusicBrainz...")

    enriched_artists = []
    not_found = []

    for i, name in enumerate(artists_to_process):
        # Search
        search_result = search_artist(name)
        time.sleep(RATE_LIMIT_SLEEP)

        if not search_result:
            not_found.append(name)
            continue

        mbid = search_result.get("id")
        if not mbid:
            not_found.append(name)
            continue

        # Get details
        details = get_artist_details(mbid)
        time.sleep(RATE_LIMIT_SLEEP)

        if details:
            enriched = {
                "spotify_artist_name": name,
                "mbid": mbid,
                "mb_name": details.get("name"),
                "mb_type": details.get("type"),
                "mb_country": details.get("country"),
                "mb_area": details.get("area", {}).get("name") if details.get("area") else None,
                "mb_begin_date": details.get("life-span", {}).get("begin"),
                "mb_end_date": details.get("life-span", {}).get("end"),
                "mb_genres": [g.get("name") for g in details.get("genres", [])],
                "mb_tags": [t.get("name") for t in details.get("tags", [])[:10]],
                "_extracted_at": datetime.now().isoformat(),
            }
            enriched_artists.append(enriched)

        if (i + 1) % 10 == 0:
            logger.info(f"  Progresso: {i + 1}/{len(artists_to_process)} artistas")

    # Guarda resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = raw_dir / f"artists_musicbrainz_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_artists, f, ensure_ascii=False, indent=2)

    logger.success(
        f"MusicBrainz: {len(enriched_artists)} artistas encontrados | "
        f"{len(not_found)} não encontrados -> {output_path}"
    )

    if not_found:
        logger.debug(f"Artistas não encontrados: {not_found[:10]}{'...' if len(not_found) > 10 else ''}")

    return enriched_artists


def run_musicbrainz_extraction(
        spotify_artists_file: Path | None = None,
        max_artists: int = 100,
) -> dict:
    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - MUSICBRAINZ")
    logger.info("=" * 60)

    config = load_config()
    artists_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "artists"

    if spotify_artists_file is None:
        # 1. Procura ambos os padrões
        patterns = ["user_top_artists_*.json", "artists_*.json"]
        all_files = []
        for p in patterns:
            all_files.extend(list(artists_dir.glob(p)))

        # 2. FILTRO CRÍTICO: Ordena por tempo mas só aceita ficheiros que NÃO estejam vazios
        valid_files = sorted(
            [f for f in all_files if f.stat().st_size > 0],
            key=lambda x: x.stat().st_mtime
        )

        if not valid_files:
            logger.error("Nenhum ficheiro de artistas com conteúdo encontrado.")
            return {"error": "Sem dados de entrada válidos"}

        spotify_artists_file = valid_files[-1]

    logger.info(f"A usar artistas de: {spotify_artists_file}")

    try:
        with open(spotify_artists_file, "r", encoding="utf-8") as f:
            spotify_artists = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Ficheiro corrompido: {spotify_artists_file}")
        return {"error": "JSON corrompido"}

    artist_names = [a.get("name") for a in spotify_artists if a.get("name")]
    seen = set()
    unique_names = []
    for name in artist_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    logger.info(f"Artistas únicos do Spotify: {len(unique_names)}")

    # 3. EVITAR DIVISÃO POR ZERO
    if not unique_names:
        logger.warning("Lista de artistas única está vazia. A abortar MusicBrainz.")
        return {"musicbrainz_matched": 0, "match_rate_pct": 0.0}

    enriched = extract_artists_from_musicbrainz(unique_names, max_artists=max_artists)

    # Cálculo seguro da percentagem
    total_attempted = min(len(unique_names), max_artists)
    match_rate = round(len(enriched) / total_attempted * 100, 1) if total_attempted > 0 else 0.0

    return {
        "source_file": str(spotify_artists_file),
        "spotify_artists_count": len(unique_names),
        "musicbrainz_matched": len(enriched),
        "match_rate_pct": match_rate,
    }


if __name__ == "__main__":
    run_musicbrainz_extraction(max_artists=50)
