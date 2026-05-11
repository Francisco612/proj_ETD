"""
Extração e inventário do Spotify Million Playlist Dataset (MPD).

O MPD é composto por 1000 ficheiros JSON (slices), cada um com 1000 playlists.
Total: ~1 milhão de playlists, ~66 milhões de track entries.

Este módulo:
  - Inventaria os ficheiros disponíveis
  - Lê em chunks para eficiência de memória
  - Produz estatísticas do dataset
  - Extrai uma amostra representativa para desenvolvimento

Dataset: https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge
Instrução de download: ver README.md, secção "Download do MPD"
"""

import json
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("extract_mpd")

# Pasta onde o MPD deve ser colocado (ver README)
MPD_DEFAULT_PATH = Path("data/raw/mpd_dataset")


def inventory_mpd(mpd_dir: Path | None = None) -> dict:
    """
    Inventaria os ficheiros do MPD disponíveis localmente.

    Args:
        mpd_dir: pasta com os slices JSON do MPD

    Returns:
        Dicionário com inventário: ficheiros encontrados, tamanho total, etc.
    """
    if mpd_dir is None:
        mpd_dir = MPD_DEFAULT_PATH

    mpd_dir = Path(mpd_dir)

    inventory = {
        "mpd_dir": str(mpd_dir),
        "inventoried_at": datetime.now().isoformat(),
        "dataset_found": mpd_dir.exists(),
        "slice_files": [],
        "total_files": 0,
        "total_size_mb": 0.0,
        "estimated_playlists": 0,
    }

    if not mpd_dir.exists():
        logger.warning(
            f"Pasta do MPD não encontrada: {mpd_dir}\n"
            "Coloca os ficheiros do MPD nessa pasta.\n"
            "Ver README.md -> secção 'Download do MPD'"
        )
        return inventory

    slice_files = sorted(mpd_dir.glob("mpd.slice.*.json"))

    if not slice_files:
        # Tenta também o formato challenge_set
        slice_files = sorted(mpd_dir.glob("*.json"))

    total_size = 0
    for f in slice_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        total_size += f.stat().st_size
        inventory["slice_files"].append({
            "filename": f.name,
            "size_mb": round(size_mb, 2),
        })

    inventory["total_files"] = len(slice_files)
    inventory["total_size_mb"] = round(total_size / (1024 * 1024), 1)
    inventory["estimated_playlists"] = len(slice_files) * 1000  # cada slice = 1000 playlists

    logger.info(f"MPD encontrado: {len(slice_files)} slices | {inventory['total_size_mb']} MB")
    logger.info(f"Playlists estimadas: ~{inventory['estimated_playlists']:,}")

    return inventory


def extract_mpd_sample(
    mpd_dir: Path | None = None,
    max_slices: int = 10,
    output_dir: Path | None = None,
) -> dict:
    """
    Lê os primeiros N slices do MPD e extrai estatísticas + amostra.

    Leitura eficiente em chunks — nunca carrega o dataset completo em memória.

    Args:
        mpd_dir: pasta com os slices JSON
        max_slices: número de slices a processar (cada slice = 1000 playlists)
        output_dir: pasta de output (default: data/raw/mpd_dataset/processed)

    Returns:
        Dicionário com estatísticas da extração
    """
    config = load_config()

    if mpd_dir is None:
        mpd_dir = MPD_DEFAULT_PATH
    mpd_dir = Path(mpd_dir)

    if output_dir is None:
        output_dir = Path(config["paths"]["raw_data"]) / "mpd_dataset" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    slice_files = sorted(mpd_dir.glob("mpd.slice.*.json"))
    if not slice_files:
        slice_files = sorted(mpd_dir.glob("*.json"))

    if not slice_files:
        logger.error(
            f"Nenhum ficheiro MPD encontrado em {mpd_dir}.\n"
            "Vê o README.md para instruções de download."
        )
        return {"error": "MPD não encontrado", "mpd_dir": str(mpd_dir)}

    slices_to_process = slice_files[:max_slices]
    logger.info(f"A processar {len(slices_to_process)} slices do MPD...")

    # Acumuladores de estatísticas
    total_playlists = 0
    total_tracks = 0
    all_track_uris = set()
    artist_counts = {}
    playlist_lengths = []
    sample_playlists = []  # primeiras 100 playlists para amostra

    for slice_path in tqdm(slices_to_process, desc="Slices MPD"):
        try:
            with open(slice_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            playlists = data.get("playlists", [])

            for playlist in playlists:
                total_playlists += 1
                tracks = playlist.get("tracks", [])
                total_tracks += len(tracks)
                playlist_lengths.append(len(tracks))

                for track in tracks:
                    uri = track.get("track_uri", "")
                    all_track_uris.add(uri)
                    artist = track.get("artist_name", "Unknown")
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1

                # Guarda amostra das primeiras 100 playlists
                if len(sample_playlists) < 100:
                    sample_playlists.append({
                        "pid": playlist.get("pid"),
                        "name": playlist.get("name"),
                        "num_tracks": len(tracks),
                        "num_followers": playlist.get("num_followers", 0),
                        "modified_at": playlist.get("modified_at"),
                        "collaborative": playlist.get("collaborative", False),
                    })

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erro ao ler {slice_path.name}: {e}")
            continue

    # Top artistas por frequência
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:50]

    stats = {
        "extracted_at": datetime.now().isoformat(),
        "slices_processed": len(slices_to_process),
        "total_playlists": total_playlists,
        "total_track_entries": total_tracks,
        "unique_track_uris": len(all_track_uris),
        "unique_artists": len(artist_counts),
        "avg_playlist_length": round(sum(playlist_lengths) / len(playlist_lengths), 1) if playlist_lengths else 0,
        "min_playlist_length": min(playlist_lengths) if playlist_lengths else 0,
        "max_playlist_length": max(playlist_lengths) if playlist_lengths else 0,
        "top_50_artists": [{"artist": a, "track_entries": c} for a, c in top_artists],
    }

    # Guarda outputs
    stats_path = output_dir / "mpd_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    sample_path = output_dir / "mpd_sample_playlists.json"
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_playlists, f, ensure_ascii=False, indent=2)

    # Guarda amostra em CSV para fácil inspeção
    if sample_playlists:
        df = pd.DataFrame(sample_playlists)
        df.to_csv(output_dir / "mpd_sample_playlists.csv", index=False, encoding="utf-8")

    logger.success(f"MPD processado: {total_playlists:,} playlists | {total_tracks:,} track entries")
    logger.info(f"  Tracks únicas (URIs): {len(all_track_uris):,}")
    logger.info(f"  Artistas únicos:      {len(artist_counts):,}")
    logger.info(f"  Comprimento médio:    {stats['avg_playlist_length']} tracks")
    logger.info(f"Stats guardadas em: {stats_path}")

    return stats


def run_mpd_extraction(max_slices: int = 10) -> dict:
    """
    Ponto de entrada principal para extração do MPD.

    Args:
        max_slices: número de slices a processar (10 = 10.000 playlists)

    Returns:
        Dicionário com inventário + estatísticas
    """
    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - MPD DATASET")
    logger.info("=" * 60)

    inventory = inventory_mpd()

    if not inventory["dataset_found"]:
        logger.warning(
            "\n⚠️  MPD não encontrado!\n"
            "Para fazer o download do MPD:\n"
            "  1. Vai a https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge\n"
            "  2. Regista-te e aceita os termos\n"
            "  3. Faz download dos ficheiros\n"
            "  4. Extrai para: data/raw/mpd_dataset/\n"
            "\nEsta extração fica pendente até teres o dataset.\n"
            "As outras extrações (Spotify API, MusicBrainz) funcionam sem ele."
        )
        return inventory

    stats = extract_mpd_sample(max_slices=max_slices)
    return {**inventory, **stats}


if __name__ == "__main__":
    run_mpd_extraction(max_slices=10)
