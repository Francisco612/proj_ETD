"""
Módulo de Extração Filtrada e Otimizada do Spotify MPD (Million Playlist Dataset).

Lê o arquivo comprimido (.zip) em modo stream sem descompactar no disco,
filtrando faixas e playlists com base nos artistas validados na etapa da MusicBrainz.
"""

import json
import zipfile
from pathlib import Path
from datetime import datetime

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("extract_mpd")

# Caminho absoluto ou relativo para o teu ficheiro pesado descarregado
ZIP_FILE_PATH = Path(r"C:\Users\franc\Downloads\spotify_million_playlist_dataset.zip")


def load_target_artists(mb_json_path: Path) -> set[str]:
    """Lê os artistas do teu ficheiro JSON e devolve um set para buscas rápidas."""
    try:
        with open(mb_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Guardamos os nomes em lowercase para evitar problemas de maiúsculas/minúsculas
        artists = {item["spotify_artist_name"].lower() for item in data if "spotify_artist_name" in item}
        logger.info(f"Ficheiro de referência carregado: {len(artists)} artistas alvo mapeados.")
        return artists
    except Exception as e:
        logger.error(f"Erro ao ler ficheiro de referência {mb_json_path}: {e}")
        return set()


def extract_filtered_mpd(zip_path: Path, target_artists: set[str], limit_files: int = None):
    """
    Abre o ZIP em modo stream, processa cada ficheiro JSON interno em chunks
    e extrai apenas os dados relacionados com os artistas alvo.
    """
    config = load_config()
    output_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "playlists"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists():
        logger.error(f"O ficheiro original do MPD não foi encontrado em: {zip_path}")
        return

    logger.info(f"A abrir o arquivo MPD: {zip_path.name}...")

    playlists_filtradas = []
    ficheiros_processados = 0

    with zipfile.ZipFile(zip_path, "r") as z:
        # Listar todos os ficheiros lá dentro (geralmente na pasta 'data/' do zip)
        json_files = [f for f in z.namelist() if f.endswith(".json") and "mpd.slice." in f]

        if limit_files:
            json_files = json_files[:limit_files]

        total_files = len(json_files)
        logger.info(f"Total de fatias (slices) detetadas no ZIP: {total_files}")

        for file_info in json_files:
            ficheiros_processados += 1

            # Lê o ficheiro de 1000 playlists diretamente da memória RAM temporária (Stream)
            with z.open(file_info) as f:
                slice_data = json.loads(f.read().decode("utf-8"))

            # Iterar pelas playlists do slice
            for playlist in slice_data.get("playlists", []):
                contem_artista_alvo = False
                faixas_filtradas = []

                # Analisar as músicas da playlist
                for track in playlist.get("tracks", []):
                    artist_name = track.get("artist_name", "").lower()

                    if artist_name in target_artists:
                        contem_artista_alvo = True
                        faixas_filtradas.append({
                            "pos": track.get("pos"),
                            "track_name": track.get("track_name"),
                            "track_uri": track.get("track_uri"),
                            "artist_name": track.get("artist_name"),
                            "artist_uri": track.get("artist_uri"),
                            "album_name": track.get("album_name"),
                            "duration_ms": track.get("duration_ms")
                        })

                # Se a playlist tiver pelo menos uma música dos teus artistas, guardamos os metadados dela
                if contem_artista_alvo:
                    playlists_filtradas.append({
                        "pid": playlist.get("pid"),
                        "name": playlist.get("name"),
                        "num_tracks": playlist.get("num_tracks"),
                        "num_albums": playlist.get("num_albums"),
                        "num_followers": playlist.get("num_followers"),
                        "tracks": faixas_filtradas  # Apenas as faixas que nos interessam
                    })

            if ficheiros_processados % 10 == 0 or ficheiros_processados == total_files:
                logger.info(f"  Progresso: {ficheiros_processados}/{total_files} fatias do ZIP analisadas.")

    # Guardar o resultado final consolidado na tua pasta RAW do projeto
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"mpd_filtered_{timestamp}.json"

    output_data = {
        "extracted_at": datetime.now().isoformat(),
        "total_playlists_matched": len(playlists_filtradas),
        "playlists": playlists_filtradas
    }

    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(output_data, out_f, ensure_ascii=False, indent=2)

    logger.success(f"Extração Concluída! {len(playlists_filtradas)} playlists intersetadas -> {output_path}")


def run_mpd_extraction():
    logger.info("=" * 60)
    logger.info("INÍCIO DA EXTRAÇÃO - SPOTIFY MPD (STREAMING)")
    logger.info("=" * 60)

    config = load_config()

    # 1. Localizar o ficheiro da MusicBrainz que geraste para servir de filtro
    mb_dir = Path(config["paths"]["raw_data"]) / "musicbrainz"
    mb_files = sorted(list(mb_dir.glob("artists_musicbrainz_*.json")), key=lambda x: x.stat().st_mtime)

    if not mb_files:
        logger.error("Ficheiro artists_musicbrainz_*.json não encontrado em data/raw/musicbrainz/.")
        return

    latest_mb_file = mb_files[-1]

    # 2. Carregar o set de artistas
    target_artists = load_target_artists(latest_mb_file)

    if not target_artists:
        logger.warning("Nenhum artista disponível para filtragem. A abortar.")
        return

    # 3. Executar o pipeline de streaming do ZIP externo
    # Podes adicionar limit_files=50 dentro de extract_filtered_mpd para testar mais rápido se quiseres!
    extract_filtered_mpd(ZIP_FILE_PATH, target_artists)


if __name__ == "__main__":
    run_mpd_extraction()