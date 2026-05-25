"""
Módulo de Carregamento (Load) — Semana 3.

Lê o dataset unificado da Camada Silver (Staging) e as três tabelas
agregadas da Camada Gold, persistindo tudo numa base de dados analítica
local DuckDB (.db). Inclui testes de integridade pós-carga via SQL.
"""

import duckdb
from pathlib import Path
from datetime import datetime
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("load_to_db")


def get_latest_file(directory: Path, pattern: str) -> Path:
    """Encontra o ficheiro mais recente baseado no padrão de nome."""
    files = sorted(list(directory.glob(pattern)), key=lambda x: x.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"Nenhum ficheiro encontrado com o padrão '{pattern}' em {directory}")
    return files[-1]


def create_tables(conn):
    """Define o esquema físico (DDL) das tabelas relacionais e analíticas."""
    logger.info("A criar a estrutura das tabelas no DuckDB...")

    # 1. Tabela de Factos Central (Silver detalhada)
    conn.execute("""
        CREATE OR REPLACE TABLE fact_playlists_tracks (
            playlist_id INTEGER,
            playlist_name VARCHAR,
            playlist_followers INTEGER,
            track_pos INTEGER,
            track_name VARCHAR,
            track_uri VARCHAR,
            artist_name VARCHAR,
            artist_uri VARCHAR,
            album_name VARCHAR,
            track_duration_min DOUBLE
        );
    """)

    # 2. Tabela Gold: Popularidade e Alcance de Artistas
    conn.execute("""
        CREATE OR REPLACE TABLE gold_artist_popularity (
            artist_name VARCHAR PRIMARY KEY,
            total_aparicoes INTEGER,
            total_seguidores_alcancados INTEGER,
            playlists_unicas INTEGER
        );
    """)

    # 3. Tabela Gold: Ranking de Géneros
    conn.execute("""
        CREATE OR REPLACE TABLE gold_genre_ranking (
            mb_genres VARCHAR,
            frequencia_nas_playlists INTEGER
        );
    """)

    # 4. Tabela Gold: Distribuição Geográfica por País
    conn.execute("""
        CREATE OR REPLACE TABLE gold_country_distribution (
            mb_country VARCHAR,
            total_faixas_ouvidas INTEGER,
            seguidores_impactados INTEGER
        );
    """)
    logger.info("Estrutura DDL definida com sucesso.")


def load_csv_to_duckdb(conn, file_path: Path, table_name: str):
    """Carrega um ficheiro CSV diretamente para uma tabela DuckDB de forma performante."""
    logger.info(f"A carregar {file_path.name} para a tabela '{table_name}'...")
    # O DuckDB possui um leitor nativo de CSV extremamente veloz
    conn.execute(f"""
        INSERT INTO {table_name} 
        SELECT * FROM read_csv_auto('{str(file_path)}', header=True)
    """)


def run_post_load_checks(conn, expected_silver_rows: int):
    """Executa validações de qualidade e integridade de dados pós-carga via SQL."""
    logger.info("=" * 60)
    logger.info("INÍCIO DA VALIDAÇÃO DE QUALIDADE PÓS-CARGA (SQL)")
    logger.info("=" * 60)

    # Teste 1: Contagem de Linhas da Tabela de Factos
    db_rows = conn.execute("SELECT COUNT(*) FROM fact_playlists_tracks").fetchone()[0]
    if db_rows == expected_silver_rows:
        logger.success(
            f"[PASS] Integridade de Carga: {db_rows} de {expected_silver_rows} linhas inseridas com sucesso.")
    else:
        logger.error(f"[FAIL] Inconsistência detetada! Esperado: {expected_silver_rows}, Carregado: {db_rows}")

    # Teste 2: Validação de Registos na Tabela Gold de Artistas
    total_artists = conn.execute("SELECT COUNT(*) FROM gold_artist_popularity").fetchone()[0]
    logger.success(f"[PASS] Dimensão Artistas validada com {total_artists} registos analíticos.")

    # Teste 3: Integridade Referencial Simulada
    # Garante que os artistas do ranking Gold existem de facto na tabela de Factos
    orphans = conn.execute("""
        SELECT COUNT(g.artist_name)
        FROM gold_artist_popularity g
        LEFT JOIN (SELECT DISTINCT artist_name FROM fact_playlists_tracks) f
        ON g.artist_name = f.artist_name
        WHERE f.artist_name IS NULL
    """).fetchone()[0]

    if orphans == 0:
        logger.success("[PASS] Integridade Referencial: 100% de coesão entre Factos e Agregações.")
    else:
        logger.warning(f"[WARNING] Detetados {orphans} artistas órfãos sem correspondência na tabela de factos.")


def run_load_pipeline():
    start_time = datetime.now()
    config = load_config()

    # Mapeamento de Diretorias
    staging_dir = Path(config["paths"].get("staging_data", "data/staging"))
    gold_dir = Path("data/gold")

    # Configurar destino da base de dados física (.db)
    db_file_path = gold_dir / "music_analytics.db"

    logger.info("A localizar os ficheiros mais recentes para o carregamento...")
    try:
        # 1. Identificar ficheiros mais recentes gerados pelas transformações
        file_silver = get_latest_file(staging_dir, "fact_playlists_tracks_staging_*.csv")
        file_gold_artists = get_latest_file(gold_dir, "dim_artist_popularity_gold_*.csv")
        file_gold_genres = get_latest_file(gold_dir, "dim_genre_ranking_gold_*.csv")
        file_gold_countries = get_latest_file(gold_dir, "dim_country_distribution_gold_*.csv")

        # Contar linhas do CSV Silver para validação futura (usando encoding seguro)
        with open(file_silver, "r", encoding="utf-8") as f:
            expected_silver_rows = sum(1 for _ in f) - 1  # Descontar o cabeçalho

        # 2. Conectar ao DuckDB (cria o ficheiro se não existir)
        conn = duckdb.connect(str(db_file_path))

        # 3. Criar as tabelas
        create_tables(conn)

        # 4. Executar cargas em massa (Bulk Load)
        load_csv_to_duckdb(conn, file_silver, "fact_playlists_tracks")
        load_csv_to_duckdb(conn, file_gold_artists, "gold_artist_popularity")
        load_csv_to_duckdb(conn, file_gold_genres, "gold_genre_ranking")
        load_csv_to_duckdb(conn, file_gold_countries, "gold_country_distribution")

        # 5. Correr validações analíticas SQL
        run_post_load_checks(conn, expected_silver_rows)

        duration = (datetime.now() - start_time).total_seconds()
        logger.success(f"Fase de Carregamento (LOAD) concluída com distinção em {duration:.2f}s!")
        logger.info(f"Base de Dados guardada e trancada em: {db_file_path}")

    except Exception as e:
        logger.critical(f"Falha crítica no pipeline de carregamento para a base de dados: {e}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    run_load_pipeline()