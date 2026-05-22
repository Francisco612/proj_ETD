"""
Módulo de Transformação Avançada - Camada Curated (Gold).
Pega no dataset massivo de staging e cria agregações analíticas estruturadas
para responder às perguntas de negócio no Dashboard de forma instantânea.
"""

import ast
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("transform_aggregations")


def run_aggregations_generation():
    logger.info("=" * 60)
    logger.info("INÍCIO DA AGREGAÇÃO ANALÍTICA - CAMADA GOLD")
    logger.info("=" * 60)

    config = load_config()
    staging_dir = Path(config["paths"].get("staging_data", "data/staging"))
    gold_dir = Path("data/gold")
    gold_dir.mkdir(parents=True, exist_ok=True)

    # 1. Localizar o ficheiro Staging mais recente
    files = sorted(list(staging_dir.glob("fact_playlists_tracks_staging_*.csv")), key=lambda x: x.stat().st_mtime)
    if not files:
        logger.error("Nenhum ficheiro de staging encontrado para agregação.")
        return

    latest_staging = files[-1]
    logger.info(f"A processar agregações analíticas a partir de: {latest_staging.name}")

    # Carregar apenas as colunas necessárias para poupar memória na agregação
    cols_to_use = ["playlist_id", "playlist_followers", "artist_name", "mb_country", "mb_genres"]
    df = pd.read_csv(latest_staging, usecols=cols_to_use)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # -------------------------------------------------------------------------
    # AGREGAÇÃO 1: Top Artistas por Alcance e Recorrência (Pergunta 1 do Enunciado)
    # -------------------------------------------------------------------------
    logger.info("A calcular popularidade e relevância dos artistas...")
    artist_summary = df.groupby("artist_name").agg(
        total_aparicoes=("playlist_id", "count"),
        total_seguidores_alcancados=("playlist_followers", "sum"),
        playlists_unicas=("playlist_id", "nunique")
    ).reset_index()

    # Ordena pelos artistas mais recorrentes
    artist_summary = artist_summary.sort_values(by="total_aparicoes", ascending=False)

    artist_out = gold_dir / f"dim_artist_popularity_gold_{timestamp}.csv"
    artist_summary.to_csv(artist_out, index=False, encoding="utf-8")
    logger.info(f"  -> Tabela 'Popularidade Artistas' gerada: {artist_summary.shape[0]} linhas.")

    # -------------------------------------------------------------------------
    # AGREGAÇÃO 2: Análise Geográfica (De onde vêm os artistas das playlists?)
    # -------------------------------------------------------------------------
    logger.info("A calcular distribuição geográfica dos artistas ouvidos...")
    df_countries = df.groupby("mb_country").agg(
        total_faixas_ouvidas=("playlist_id", "count"),
        seguidores_impactados=("playlist_followers", "sum")
    ).reset_index().sort_values(by="total_faixas_ouvidas", ascending=False)

    country_out = gold_dir / f"dim_country_distribution_gold_{timestamp}.csv"
    df_countries.to_csv(country_out, index=False, encoding="utf-8")
    logger.info(f"  -> Tabela 'Distribuição Geográfica' gerada: {df_countries.shape[0]} linhas.")

    # -------------------------------------------------------------------------
    # AGREGAÇÃO 3: Explodir Géneros Musicais (Estratégia Avançada de Data Science)
    # Como mb_genres vem como uma lista em formato string '["pop", "rap"]', precisamos de a extrair
    # -------------------------------------------------------------------------
    logger.info("A extrair e explodir chaves de géneros musicais (MusicBrainz)...")

    # Filtrar nulos e linhas sem géneros para acelerar o processo
    df_genres = df[["playlist_id", "mb_genres"]].dropna()

    def safe_parse_list(val):
        try:
            return ast.literal_eval(val) if isinstance(val, str) else []
        except:
            return []

    df_genres["mb_genres"] = df_genres["mb_genres"].apply(safe_parse_list)

    # Dar o "explode" do pandas para transformar cada item da lista numa linha dedicada
    df_genres_exploded = df_genres.explode("mb_genres")
    df_genres_exploded = df_genres_exploded.dropna(subset=["mb_genres"])

    # Agrupar e contar a dominância de cada género musical
    genre_summary = df_genres_exploded.groupby("mb_genres").agg(
        frequencia_nas_playlists=("playlist_id", "count")
    ).reset_index().sort_values(by="frequencia_nas_playlists", ascending=False)

    genre_out = gold_dir / f"dim_genre_ranking_gold_{timestamp}.csv"
    genre_summary.to_csv(genre_out, index=False, encoding="utf-8")

    logger.success(f"Camada GOLD de agregações gerada com sucesso em: {gold_dir}")


if __name__ == "__main__":
    run_aggregations_generation()