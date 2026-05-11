"""
Módulo de autenticação com a Spotify Web API.
Usa Client Credentials Flow (sem necessidade de login do utilizador).
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from src.utils.config import get_spotify_credentials
from src.utils.logger import get_logger

logger = get_logger("spotify_auth")


def get_spotify_client() -> spotipy.Spotify:
    """
    Cria e retorna um cliente autenticado da Spotify Web API.

    Returns:
        spotipy.Spotify: cliente autenticado pronto a usar.

    Raises:
        EnvironmentError: se as credenciais não estiverem configuradas.
        spotipy.SpotifyException: se a autenticação falhar.
    """
    client_id, client_secret = get_spotify_credentials()

    logger.info("A autenticar com a Spotify Web API...")

    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )

    sp = spotipy.Spotify(
        auth_manager=auth_manager,
        requests_timeout=10,
        retries=3,
    )

    # Teste rápido para confirmar que a autenticação funcionou
    try:
        sp.search(q="test", limit=1, type="track")
        logger.success("Autenticação com Spotify bem-sucedida!")
    except Exception as e:
        logger.error(f"Falha na autenticação: {e}")
        raise

    return sp
