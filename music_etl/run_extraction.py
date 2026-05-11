"""
Script principal de extração — Semana 1.

Uso:
    python run_extraction.py                    # extrai tudo
    python run_extraction.py --source spotify   # só Spotify API
    python run_extraction.py --source mpd       # só MPD
    python run_extraction.py --source mb        # só MusicBrainz

    python run_extraction.py --source spotify --max-playlists 20
    python run_extraction.py --source mpd --max-slices 5
    python run_extraction.py --source mb --max-artists 50
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("run_extraction")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline de extração — Music & Entertainment ETL"
    )
    parser.add_argument(
        "--source",
        choices=["spotify", "mpd", "mb", "all"],
        default="all",
        help="Fonte a extrair (default: all)",
    )
    parser.add_argument(
        "--max-playlists",
        type=int,
        default=50,
        help="Máx playlists a processar do Spotify (default: 50)",
    )
    parser.add_argument(
        "--max-slices",
        type=int,
        default=10,
        help="Máx slices do MPD a processar (default: 10 = 10.000 playlists)",
    )
    parser.add_argument(
        "--max-artists",
        type=int,
        default=100,
        help="Máx artistas a enriquecer com MusicBrainz (default: 100)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start = datetime.now()

    logger.info("=" * 60)
    logger.info("MUSIC ETL — PIPELINE DE EXTRAÇÃO (SEMANA 1)")
    logger.info(f"Fonte: {args.source.upper()}")
    logger.info("=" * 60)

    results = {}

    # -------------------------------------------------------
    # Spotify Web API
    # -------------------------------------------------------
    if args.source in ("spotify", "all"):
        try:
            from src.extract.extract_spotify_api import run_spotify_extraction
            results["spotify"] = run_spotify_extraction(
                max_playlists=args.max_playlists
            )
        except EnvironmentError as e:
            logger.error(f"Spotify: {e}")
            logger.warning("Skipping Spotify extraction — configura o .env primeiro.")
            results["spotify"] = {"error": str(e)}

    # -------------------------------------------------------
    # MPD Dataset
    # -------------------------------------------------------
    if args.source in ("mpd", "all"):
        from src.extract.extract_mpd import run_mpd_extraction
        results["mpd"] = run_mpd_extraction(max_slices=args.max_slices)

    # -------------------------------------------------------
    # MusicBrainz
    # -------------------------------------------------------
    if args.source in ("mb", "all"):
        from src.extract.extract_musicbrainz import run_musicbrainz_extraction
        results["musicbrainz"] = run_musicbrainz_extraction(
            max_artists=args.max_artists
        )

    # -------------------------------------------------------
    # Resumo final
    # -------------------------------------------------------
    elapsed = (datetime.now() - start).total_seconds()
    results["total_duration_seconds"] = round(elapsed, 1)
    results["run_at"] = start.isoformat()

    summary_path = Path("data/raw/full_extraction_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info("=" * 60)
    logger.success(f"EXTRAÇÃO COMPLETA em {elapsed:.1f}s — {summary_path}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    main()
