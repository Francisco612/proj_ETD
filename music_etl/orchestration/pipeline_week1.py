"""
Orquestração da Semana 1 com Prefect.

Define o flow de extração como tasks independentes e monitorizadas.
Permite re-execução de tasks falhadas e visualização no Prefect UI.

Como usar:
    python orchestration/pipeline_week1.py

Para ver o dashboard Prefect (opcional):
    prefect server start
    # abre http://localhost:4200
"""

from prefect import flow, task
from prefect.logging import get_run_logger


@task(name="extract-spotify-api", retries=2, retry_delay_seconds=30)
def task_extract_spotify(max_playlists: int = 50) -> dict:
    """Task de extração da Spotify Web API."""
    logger = get_run_logger()
    logger.info(f"Iniciando extração Spotify (max {max_playlists} playlists)")

    from src.extract.extract_spotify_api import run_spotify_extraction
    return run_spotify_extraction(max_playlists=max_playlists)


@task(name="extract-mpd-dataset", retries=1)
def task_extract_mpd(max_slices: int = 10) -> dict:
    """Task de extração do MPD."""
    logger = get_run_logger()
    logger.info(f"Iniciando extração MPD (max {max_slices} slices)")

    from src.extract.extract_mpd import run_mpd_extraction
    return run_mpd_extraction(max_slices=max_slices)


@task(name="extract-musicbrainz", retries=2, retry_delay_seconds=60)
def task_extract_musicbrainz(max_artists: int = 100) -> dict:
    """Task de extração MusicBrainz (depende da Spotify estar concluída)."""
    logger = get_run_logger()
    logger.info(f"Iniciando extração MusicBrainz (max {max_artists} artistas)")

    from src.extract.extract_musicbrainz import run_musicbrainz_extraction
    return run_musicbrainz_extraction(max_artists=max_artists)


@task(name="generate-inventory-report")
def task_generate_report(spotify_result: dict, mpd_result: dict, mb_result: dict) -> None:
    """Gera relatório de inventário das fontes."""
    import json
    from pathlib import Path
    from datetime import datetime

    logger = get_run_logger()

    report = {
        "generated_at": datetime.now().isoformat(),
        "week": 1,
        "phase": "Extract",
        "sources": {
            "spotify_api": spotify_result,
            "mpd_dataset": mpd_result,
            "musicbrainz": mb_result,
        },
    }

    path = Path("docs/week1_inventory_report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Relatório de inventário gerado: {path}")


@flow(name="music-etl-week1-extraction", log_prints=True)
def week1_extraction_flow(
    max_playlists: int = 50,
    max_slices: int = 10,
    max_artists: int = 100,
):
    """
    Flow principal de extração — Semana 1.

    Execução sequencial:
      1. Spotify API (playlists + tracks + audio features + artistas)
      2. MPD Dataset (inventário + amostra) — em paralelo com Spotify
      3. MusicBrainz (enriquecimento de artistas — depende do Spotify)
      4. Relatório de inventário
    """
    print("🎵 Music ETL — Semana 1: Extração")

    # Spotify e MPD podem correr sem dependência entre si
    spotify_result = task_extract_spotify(max_playlists=max_playlists)
    mpd_result = task_extract_mpd(max_slices=max_slices)

    # MusicBrainz precisa dos artistas do Spotify
    mb_result = task_extract_musicbrainz(max_artists=max_artists)

    # Relatório final
    task_generate_report(spotify_result, mpd_result, mb_result)

    print("✅ Extração concluída!")


if __name__ == "__main__":
    week1_extraction_flow(
        max_playlists=50,
        max_slices=10,
        max_artists=100,
    )
