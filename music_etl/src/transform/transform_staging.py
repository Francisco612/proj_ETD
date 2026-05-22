"""
Módulo de Transformação - Camada Staging (Silver).

Lê os dados brutos (RAW) do MPD filtrado e os dados da MusicBrainz,
aplica regras de limpeza, normalização e qualidade usando o Pandas,
e prepara os dados para a modelação analítica.
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("transform_staging")


def load_latest_raw_file(directory: Path, pattern: str) -> Path | None:
    """Auxiliar para encontrar o ficheiro mais recente numa pasta de dados brutos."""
    files = sorted(list(directory.glob(pattern)), key=lambda x: x.stat().st_mtime)
    return files[-1] if files else None


def transform_mpd_to_staging() -> pd.DataFrame | None:
    """
    Lê o JSON do MPD filtrado, achata a estrutura de playlists/tracks
    e limpa/normaliza os dados criando um DataFrame do Pandas.
    """
    config = load_config()
    raw_mpd_dir = Path(config["paths"]["raw_data"]) / "spotify_api" / "playlists"

    latest_mpd = load_latest_raw_file(raw_mpd_dir, "mpd_filtered_*.json")
    if not latest_mpd:
        logger.error("Nenhum ficheiro MPD filtrado encontrado na pasta RAW.")
        return None

    logger.info(f"A carregar dados brutos do MPD: {latest_mpd.name}")
    with open(latest_mpd, "r", encoding="utf-8") as f:
        mpd_data = json.load(f)

    playlists = mpd_data.get("playlists", [])

    # 1. ACHATAMENTO (Flattening) do JSON para estrutura tabular
    rows = []
    for playlist in playlists:
        # Metadados da playlist
        pid = playlist.get("pid")
        playlist_name = playlist.get("name", "Sem Nome").strip()
        num_followers = playlist.get("num_followers", 0)

        # Iterar pelas faixas da playlist
        for track in playlist.get("tracks", []):
            rows.append({
                "playlist_id": pid,
                "playlist_name": playlist_name if playlist_name else "Sem Nome",
                "playlist_followers": num_followers,
                "track_pos": track.get("pos"),
                "track_name": track.get("track_name", "Desconhecido").strip(),
                "track_uri": track.get("track_uri"),
                "artist_name": track.get("artist_name", "Desconhecido").strip(),
                "artist_uri": track.get("artist_uri"),
                "album_name": track.get("album_name", "Desconhecido").strip(),
                "duration_ms": track.get("duration_ms", 0)
            })

    # Criar o DataFrame do Pandas
    df_mpd = pd.DataFrame(rows)
    logger.info(f"DataFrame inicial criado com {len(df_mpd)} linhas (músicas em playlists).")

    # 2. REGRAS DE DATA QUALITY & LIMPEZA (Semana 2)
    # Remover duplicados exatos (caso existam no log bruto)
    df_mpd = df_mpd.drop_duplicates()

    # Validação de qualidade: Duração tem de ser positiva e maior que zero
    invalid_duration = df_mpd[df_mpd["duration_ms"] <= 0]
    if not invalid_duration.empty:
        logger.warning(f"Foram detetadas {len(invalid_duration)} linhas com durações inválidas. A remover...")
        df_mpd = df_mpd[df_mpd["duration_ms"] > 0]

    # 3. NORMALIZAÇÃO DE MÉTRICAS
    # Converter milissegundos para minutos (arredondado a 2 casas decimais)
    df_mpd["track_duration_min"] = round(df_mpd["duration_ms"] / 60000, 2)
    # Podemos agora descartar a coluna antiga em milissegundos para poupar espaço
    df_mpd = df_mpd.drop(columns=["duration_ms"])

    return df_mpd


def transform_musicbrainz_to_staging() -> pd.DataFrame | None:
    """Lê o JSON enriquecido da MusicBrainz e transforma num DataFrame limpo."""
    config = load_config()
    raw_mb_dir = Path(config["paths"]["raw_data"]) / "musicbrainz"

    latest_mb = load_latest_raw_file(raw_mb_dir, "artists_musicbrainz_*.json")
    if not latest_mb:
        logger.error("Nenhum ficheiro MusicBrainz encontrado na pasta RAW.")
        return None

    logger.info(f"A carregar metadados da MusicBrainz: {latest_mb.name}")

    # O Pandas consegue ler diretamente uma lista de dicionários JSON simples para DataFrame
    df_mb = pd.read_json(latest_mb)

    # Limpeza básica de strings para o join não falhar por espaços invisíveis
    df_mb["spotify_artist_name"] = df_mb["spotify_artist_name"].str.strip()

    # Tratamento de nulos em colunas críticas
    df_mb["mb_country"] = df_mb["mb_country"].fillna("Unknown")
    df_mb["mb_type"] = df_mb["mb_type"].fillna("Unknown")

    return df_mb


def run_staging_transformation():
    logger.info("=" * 60)
    logger.info("INÍCIO DA TRANSFORMAÇÃO - CAMADA STAGING (SILVER)")
    logger.info("=" * 60)

    # 1. Processar dados do Spotify MPD
    df_spotify = transform_mpd_to_staging()

    # 2. Processar dados da MusicBrainz
    df_musicbrainz = transform_musicbrainz_to_staging()

    if df_spotify is None or df_musicbrainz is None:
        logger.error("Falha ao gerar os DataFrames de Staging. A abortar pipeline.")
        return

    # 3. O JOIN CRÍTICO (Requisito mínimo do projeto: Cruzamento de fontes)
    logger.info("A executar o Merge (Join) entre as duas fontes de dados...")

    # Fazemos um Left Join usando o nome do artista como chave de ligação
    df_staging_final = pd.merge(
        df_spotify,
        df_musicbrainz,
        left_on="artist_name",
        right_on="spotify_artist_name",
        how="left"
    )

    # Remover coluna duplicada do join se necessário
    if "spotify_artist_name" in df_staging_final.columns:
        df_staging_final = df_staging_final.drop(columns=["spotify_artist_name"])

    # 4. GRAVAR RESULTADOS (Camada Silver)
    config = load_config()
    staging_dir = Path(config["paths"].get("staging_data", "data/staging"))  # Fallback se não definido no yaml
    staging_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = staging_dir / f"fact_playlists_tracks_staging_{timestamp}.csv"

    # Guarda em CSV (podes mudar para .parquet se o professor preferir)
    df_staging_final.to_csv(output_path, index=False, encoding="utf-8")

    logger.success(f"Camada Staging concluída com sucesso! Ficheiro gerado com {len(df_staging_final)} linhas.")
    logger.success(f"Destino: {output_path}")


if __name__ == "__main__":
    run_staging_transformation()