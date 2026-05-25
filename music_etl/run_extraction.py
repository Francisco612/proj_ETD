"""
Script Principal de Orquestração do Pipeline de Extração (Semana 1).

Utiliza a biblioteca Prefect para gerir o fluxo sequencial das tarefas
de extração das três fontes de dados (Spotify API, MusicBrainz API e MPD).
"""

from prefect import flow, task
from src.utils.logger import get_logger

# Importar os runners de cada script de extração
from src.extract.extract_spotify_api import run_spotify_extraction
from src.extract.extract_musicbrainz import run_musicbrainz_extraction
from src.extract.extract_mpd import run_mpd_extraction

logger = get_logger("run_extraction")


# Transformar as funções importadas em Tasks do Prefect para monitorização correta
@task(name="Extrair_Spotify_API")
def task_spotify():
    return run_spotify_extraction()

@task(name="Extrair_MusicBrainz_API")
def task_musicbrainz():
    return run_musicbrainz_extraction()

@task(name="Extrair_Spotify_MPD")
def task_mpd():
    return run_mpd_extraction()


@flow(name="Music_ETL_Extraction_Pipeline")
def music_etl_flow():
    logger.info("A iniciar o pipeline de extração de dados musicais...")

    # 1. Extrair dados da API do Spotify (Gera a lista inicial de artistas e músicas do utilizador)
    logger.info("Passo 1: A iniciar extração da API do Spotify...")
    task_spotify()

    # 2. Extrair dados da API MusicBrainz
    # Vai buscar os géneros e países e valida os IDs (MBIDs) para servirem de filtro
    logger.info("Passo 2: A iniciar extração da API MusicBrainz...")
    task_musicbrainz()

    # 3. Extrair dados do Spotify MPD
    # Filtra o ZIP gigante com base nos artistas validados no passo anterior
    logger.info("Passo 3: A iniciar extração do Spotify MPD (Streaming do ZIP)...")
    task_mpd()

    logger.info("Pipeline de extração concluído com sucesso!")


if __name__ == "__main__":
    # Executa o fluxo sequencial reproduzível do Prefect
    music_etl_flow()