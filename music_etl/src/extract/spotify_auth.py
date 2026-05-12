# spotify_auth.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.utils.config import get_spotify_credentials
from src.utils.logger import get_logger

logger = get_logger("spotify_auth")


def get_spotify_client() -> spotipy.Spotify:
    client_id, client_secret = get_spotify_credentials()

    # IMPORTANTE:
    # Este URI tem de ser exatamente igual ao configurado
    # na Spotify Developer Dashboard
    redirect_uri = "http://127.0.0.1:8080/callback"

    # Scopes necessários
    scope = (
        "playlist-read-private "
        "playlist-read-collaborative "
        "user-read-private "
        "user-library-read"
    )

    logger.info("A iniciar fluxo de autorização OAuth (Spotify)...")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        open_browser=True,
        cache_path=".spotify_cache",
        show_dialog=False
    )

    sp = spotipy.Spotify(
        auth_manager=auth_manager,
        requests_timeout=15,
        retries=5
    )

    try:
        user = sp.current_user()

        logger.success(
            f"Autenticação OAuth bem-sucedida! "
            f"User: {user.get('display_name', 'Unknown')}"
        )

    except Exception as e:
        logger.error(f"Erro na autenticação Spotify: {e}")
        logger.info(
            "Verifica:\n"
            "- Redirect URI\n"
            "- Client ID / Secret\n"
            "- Permissões OAuth\n"
            "- Ligação internet"
        )
        raise

    return sp