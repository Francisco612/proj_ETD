"""
Módulo de API REST (Semana 4) — Servidor Backend com Swagger Automático.

Expõe os dados analíticos do DuckDB através de endpoints HTTP seguros,
gerando a documentação interativa OpenAPI (Swagger).
"""

from fastapi import FastAPI, Query, HTTPException
import duckdb
from pathlib import Path

app = FastAPI(
    title="🎵 Music Analytics API",
    description="API REST para consulta de métricas de playlists, artistas e géneros musicais do pipeline ETL.",
    version="1.0.0"
)

DB_PATH = Path("data/gold/music_analytics.db")


def query_db(sql: str, params: tuple = ()):
    """Abre uma ligação rápida, executa a query e fecha, retornando dicionários."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Base de dados física .db não encontrada.")

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = conn.execute(sql, params).fetchall()
        cols = [desc[0] for desc in conn.description]
        return [dict(zip(cols, row)) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na query SQL: {str(e)}")
    finally:
        conn.close()


@app.get("/", tags=["Geral"])
def read_root():
    """Endpoint de boas-vindas e verificação de estado da API."""
    return {"status": "Online", "projeto": "Music & Entertainment ETL", "versao": "1.0.0"}


@app.get("/api/v1/kpis", tags=["Métricas Globais"])
def get_macro_kpis():
    """Retorna os indicadores macro de volume do pipeline."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Base de dados não encontrada.")

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    total_tracks = conn.execute("SELECT COUNT(*) FROM fact_playlists_tracks;").fetchone()[0]
    total_artists = conn.execute("SELECT COUNT(*) FROM gold_artist_popularity;").fetchone()[0]
    total_countries = conn.execute(
        "SELECT COUNT(DISTINCT mb_country) FROM gold_country_distribution WHERE mb_country != 'Unknown';").fetchone()[0]
    conn.close()

    return {
        "total_linhas_silver": total_tracks,
        "total_artistas_gold": total_artists,
        "total_paises_gold": total_countries
    }


@app.get("/api/v1/countries/distribution", tags=["Geografia"])
def get_country_distribution():
    """Retorna a volumetria de consumo mapeada com os nomes por extenso dos países."""
    # Usamos um CASE WHEN para converter as siglas ISO para os nomes completos legíveis
    sql = """
        SELECT 
            CASE mb_country
                WHEN 'US' THEN 'Estados Unidos'
                WHEN 'CA' THEN 'Canadá'
                WHEN 'GB' THEN 'Reino Unido'
                WHEN 'JM' THEN 'Jamaica'
                WHEN 'PR' THEN 'Porto Rico'
                WHEN 'PT' THEN 'Portugal'
                ELSE mb_country
            END AS mb_country,
            total_faixas_ouvidas,
            seguidores_impactados
        FROM gold_country_distribution 
        WHERE mb_country != 'Unknown' 
        ORDER BY total_faixas_ouvidas DESC;
    """
    return query_db(sql)


@app.get("/api/v1/countries/distribution", tags=["Geografia"])
def get_country_distribution():
    """Retorna a volumetria de consumo mapeada por país de origem do artista."""
    sql = "SELECT * FROM gold_country_distribution WHERE mb_country != 'Unknown' ORDER BY total_faixas_ouvidas DESC;"
    return query_db(sql)


@app.get("/api/v1/artists/list", tags=["Artistas"])
def get_artists_list():
    """Retorna uma lista simples com o nome de todos os artistas para popular filtros."""
    sql = "SELECT artist_name FROM gold_artist_popularity ORDER BY artist_name;"
    res = query_db(sql)
    return [r["artist_name"] for r in res if r["artist_name"] is not None]


@app.get("/api/v1/artists/popularity", tags=["Artistas"])
def get_artists_popularity(artista: str = Query("Todos", description="Nome do artista para filtrar")):
    """Retorna os dados de alcance e popularidade dos artistas monitorizados."""
    if artista != "Todos":
        sql = "SELECT * FROM gold_artist_popularity WHERE artist_name = ?;"
        return query_db(sql, (artista,))
    else:
        sql = "SELECT * FROM gold_artist_popularity;"
        return query_db(sql)


@app.get("/api/v1/countries/list", tags=["Geografia"])
def get_countries_list():
    """Retorna a lista de países com nomes por extenso para popular os filtros."""
    sql = """
        SELECT DISTINCT 
            CASE mb_country
                WHEN 'US' THEN 'Estados Unidos'
                WHEN 'CA' THEN 'Canadá'
                WHEN 'GB' THEN 'Reino Unido'
                WHEN 'JM' THEN 'Jamaica'
                WHEN 'PR' THEN 'Porto Rico'
                WHEN 'PT' THEN 'Portugal'
                ELSE mb_country
            END AS pais_nome
        FROM gold_country_distribution 
        WHERE mb_country != 'Unknown' 
        ORDER BY pais_nome;
    """
    res = query_db(sql)
    return [r["pais_nome"] for r in res if r["pais_nome"] is not None]


@app.get("/api/v1/fact/sample", tags=["Microdados"])
def get_fact_sample(artista: str = "Todos", pais: str = "Todos", limit: int = 100):
    """Retorna uma amostra de linhas da tabela de factos adaptando os filtros de nomes por extenso."""
    # Fazemos a tradução inversa no WHERE para o filtro do ecrã bater certo com as siglas do DuckDB
    sql = """
        SELECT 
            playlist_name, 
            track_name, 
            artist_name, 
            album_name, 
            track_duration_min,
            CASE mb_country
                WHEN 'US' THEN 'Estados Unidos'
                WHEN 'CA' THEN 'Canadá'
                WHEN 'GB' THEN 'Reino Unido'
                WHEN 'JM' THEN 'Jamaica'
                WHEN 'PR' THEN 'Porto Rico'
                WHEN 'PT' THEN 'Portugal'
                ELSE mb_country
            END AS mb_country 
        FROM fact_playlists_tracks
    """
    conditions = []
    params = []

    if list(conditions): pass  # Apenas salvaguarda de sintaxe externa

    if artista != "Todos":
        conditions.append("artist_name = ?")
        params.append(artista)

    if pais != "Todos":
        # Mapeamento reverso para a query saber o que procurar na tabela original
        mapeamento_reverso = {
            'Estados Unidos': 'US', 'Canadá': 'CA', 'Reino Unido': 'GB',
            'Jamaica': 'JM', 'Porto Rico': 'PR', 'Portugal': 'PT'
        }
        sigla_pais = mapeamento_reverso.get(pais, pais)
        conditions.append("mb_country = ?")
        params.append(sigla_pais)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += f" LIMIT {limit};"
    return query_db(sql, tuple(params))