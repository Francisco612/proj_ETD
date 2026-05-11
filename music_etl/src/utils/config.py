"""
Carrega configurações do ficheiro YAML e variáveis de ambiente.
Ponto único de acesso a toda a configuração do projeto.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


def load_config() -> dict:
    """Carrega e retorna o dicionário de configuração."""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Override com variáveis de ambiente quando existirem
    if os.getenv("SPOTIFY_PLAYLIST_LIMIT"):
        config["spotify"]["playlist_limit"] = int(os.getenv("SPOTIFY_PLAYLIST_LIMIT"))
    if os.getenv("SPOTIFY_TRACKS_LIMIT"):
        config["spotify"]["tracks_limit"] = int(os.getenv("SPOTIFY_TRACKS_LIMIT"))
    if os.getenv("RAW_DATA_DIR"):
        config["paths"]["raw_data"] = os.getenv("RAW_DATA_DIR")

    return config


def get_spotify_credentials() -> tuple[str, str]:
    """Retorna (client_id, client_secret) do Spotify a partir do .env."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "Credenciais do Spotify não encontradas.\n"
            "1. Copia .env.example para .env\n"
            "2. Preenche SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET\n"
            "   (obtém em https://developer.spotify.com/dashboard)"
        )
    return client_id, client_secret
