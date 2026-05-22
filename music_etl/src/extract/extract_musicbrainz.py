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
    "User-Agent": "MusicDataEnricherProject/1.0.4 (francisco.projectETD@gmail.com)",
    "Accept": "application/json",
}
RATE_LIMIT_SLEEP = 1.2  # Tempo mínimo em segundos entre pedidos à API
LAST_REQUEST_TIME = 0.0  # Guarda o timestamp do último pedido global

session = requests.Session()
session.headers.update(HEADERS)

def _make_request(url: str, params: dict) -> dict | None:
    """
    Função auxiliar que centraliza as chamadas HTTP e garante
    o cumprimento estrito do Rate Limit através do relógio do sistema.
    """
    global LAST_REQUEST_TIME

    # Calcula quanto tempo passou desde o último pedido
    now = time.time()
    elapsed = now - LAST_REQUEST_TIME

    # Se passou menos tempo do que o limite, espera a diferença
    if elapsed < RATE_LIMIT_SLEEP:
        time.sleep(RATE_LIMIT_SLEEP - elapsed)

    try:
        response = session.get(url, params=params, timeout=15)
        # Atualiza o timestamp imediatamente após receber a resposta
        LAST_REQUEST_TIME = time.time()

        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        logger.error(f"Erro na requisição para {url}: {e}")
        # Garante que o relógio atualiza mesmo em caso de erro para proteger o IP
        LAST_REQUEST_TIME = time.time()
        return None


def search_artist(artist_name: str) -> dict | None:
    """
    Procura um artista na MusicBrainz pelo nome usando sintaxe Lucene.

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

    data = _make_request(url, params)
    if data:
        artists = data.get("artists", [])
        return artists[0] if artists else None
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

    return _make_request(url, params)


def extract_artists_from_musicbrainz(
        artist_names: list[str],
        max_artists: int = 100,
) -> list[dict]:
    """
    Extrai metadados de artistas da MusicBrainz.

    Usa os nomes de artistas obtidos do Spotify para fazer lookup na MusicBrainz.
    Garante alto desempenho respeitando o relógio global de 1 req/segundo.

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
        # 1. Pesquisa o artista para obter o MBID
        search_result = search_artist(name)

        if not search_result:
            not_found.append(name)
            continue

        mbid = search_result.get("id")
        if not mbid:
            not_found.append(name)
            continue

        # 2. Vai buscar os detalhes avançados (Gêneros, Tags) usando o MBID
        details = get_artist_details(mbid)

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

    # Guarda resultados no diretório RAW
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
        # 1. Procura ambos os padrões de arquivos do Spotify
        patterns = ["user_top_artists_*.json", "artists_*.json"]
        all_files = []
        for p in patterns:
            all_files.extend(list(artists_dir.glob(p)))

        # 2. Filtra arquivos vazios e ordena pelo arquivo mais recente
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

    # Extrai nomes e remove duplicados mantendo a ordem
    artist_names = [a.get("name") for a in spotify_artists if a.get("name")]
    seen = set()
    unique_names = []
    for name in artist_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    logger.info(f"Artistas únicos do Spotify: {len(unique_names)}")

    # 3. Evita divisão por zero se a lista estiver vazia
    if not unique_names:
        logger.warning("Lista de artistas única está vazia. A abortar MusicBrainz.")
        return {"musicbrainz_matched": 0, "match_rate_pct": 0.0}

    enriched = extract_artists_from_musicbrainz(unique_names, max_artists=max_artists)

    # Cálculo seguro da percentagem de sucesso
    total_attempted = min(len(unique_names), max_artists)
    match_rate = round(len(enriched) / total_attempted * 100, 1) if total_attempted > 0 else 0.0

    return {
        "source_file": str(spotify_artists_file),
        "spotify_artists_count": len(unique_names),
        "musicbrainz_matched": len(enriched),
        "match_rate_pct": match_rate,
    }


if __name__ == "__main__":
    # Executa o script processando até 50 artistas para teste preliminar
    run_musicbrainz_extraction(max_artists=50)