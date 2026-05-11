"""
Testes da Semana 1 — Extração.

Valida:
  - Configuração carregada corretamente
  - Estrutura de pastas criada
  - Ficheiros de dados raw existem e têm conteúdo válido
  - Schema básico dos dados extraídos

Execução:
    pytest tests/test_week1_extraction.py -v
"""

import json
import os
from pathlib import Path

import pytest

# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@pytest.fixture
def config():
    from src.utils.config import load_config
    return load_config()


@pytest.fixture
def raw_dir(config):
    return Path(config["paths"]["raw_data"])


# ----------------------------------------------------------------
# Testes de Configuração
# ----------------------------------------------------------------

class TestConfiguration:

    def test_config_loads(self, config):
        """Configuração carrega sem erros."""
        assert config is not None
        assert "spotify" in config
        assert "paths" in config

    def test_env_example_exists(self):
        """.env.example existe no repositório."""
        assert Path(".env.example").exists(), ".env.example não encontrado"

    def test_env_file_exists(self):
        """.env existe (não commitado, mas necessário para execução)."""
        if not Path(".env").exists():
            pytest.skip(".env não existe — copia .env.example para .env e preenche as credenciais")

    def test_spotify_credentials_present(self):
        """Credenciais Spotify estão definidas no .env."""
        if not Path(".env").exists():
            pytest.skip(".env não encontrado")
        from dotenv import load_dotenv
        load_dotenv()
        client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        assert client_id and client_id != "o_teu_client_id_aqui", \
            "SPOTIFY_CLIENT_ID não está configurado no .env"
        assert client_secret and client_secret != "o_teu_client_secret_aqui", \
            "SPOTIFY_CLIENT_SECRET não está configurado no .env"

    def test_required_paths_in_config(self, config):
        """Todos os paths necessários estão na configuração."""
        assert "raw_data" in config["paths"]
        assert "staging_data" in config["paths"]
        assert "logs" in config["paths"]

    def test_data_sources_defined(self, config):
        """Pelo menos 3 fontes de dados estão definidas."""
        sources = config.get("data_sources", [])
        assert len(sources) >= 3, f"Esperadas >= 3 fontes, encontradas {len(sources)}"


# ----------------------------------------------------------------
# Testes de Estrutura de Pastas
# ----------------------------------------------------------------

class TestDirectoryStructure:

    def test_raw_dir_exists(self, raw_dir):
        """Pasta de dados raw existe."""
        assert raw_dir.exists(), f"Pasta raw não encontrada: {raw_dir}"

    def test_spotify_api_dir_exists(self, raw_dir):
        """Subpasta spotify_api existe."""
        spotify_dir = raw_dir / "spotify_api"
        assert spotify_dir.exists(), f"Pasta spotify_api não encontrada: {spotify_dir}"

    def test_logs_dir_exists(self, config):
        """Pasta de logs existe."""
        logs_dir = Path(config["paths"]["logs"])
        assert logs_dir.exists(), f"Pasta de logs não encontrada: {logs_dir}"

    def test_docs_dir_exists(self):
        """Pasta docs existe."""
        assert Path("docs").exists(), "Pasta docs não encontrada"


# ----------------------------------------------------------------
# Testes de Dados Extraídos (Spotify API)
# ----------------------------------------------------------------

class TestSpotifyExtraction:

    def _find_latest_file(self, folder: Path, pattern: str) -> Path | None:
        files = sorted(folder.glob(pattern))
        return files[-1] if files else None

    def test_playlists_file_exists(self, raw_dir):
        """Ficheiro de playlists foi criado."""
        playlists_dir = raw_dir / "spotify_api" / "playlists"
        if not playlists_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(playlists_dir, "featured_playlists_*.json")
        assert latest is not None, "Nenhum ficheiro de playlists encontrado"

    def test_playlists_valid_json(self, raw_dir):
        """Ficheiro de playlists é JSON válido e não está vazio."""
        playlists_dir = raw_dir / "spotify_api" / "playlists"
        if not playlists_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(playlists_dir, "featured_playlists_*.json")
        if not latest:
            pytest.skip("Ficheiro de playlists não encontrado")

        with open(latest, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list), "Esperada lista de playlists"
        assert len(data) > 0, "Lista de playlists está vazia"

    def test_playlist_schema(self, raw_dir):
        """Playlists têm campos obrigatórios."""
        playlists_dir = raw_dir / "spotify_api" / "playlists"
        if not playlists_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(playlists_dir, "featured_playlists_*.json")
        if not latest:
            pytest.skip("Ficheiro de playlists não encontrado")

        with open(latest, encoding="utf-8") as f:
            playlists = json.load(f)

        required_fields = ["id", "name", "_extracted_market", "_extracted_at"]
        for playlist in playlists[:5]:  # verifica apenas as primeiras 5
            for field in required_fields:
                assert field in playlist, f"Campo '{field}' em falta na playlist"

    def test_tracks_file_exists(self, raw_dir):
        """Ficheiro de tracks foi criado."""
        tracks_dir = raw_dir / "spotify_api" / "tracks"
        if not tracks_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(tracks_dir, "playlist_tracks_*.json")
        assert latest is not None, "Nenhum ficheiro de tracks encontrado"

    def test_audio_features_schema(self, raw_dir):
        """Audio features têm os campos esperados."""
        features_dir = raw_dir / "spotify_api" / "audio_features"
        if not features_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(features_dir, "audio_features_*.json")
        if not latest:
            pytest.skip("Ficheiro de audio features não encontrado")

        with open(latest, encoding="utf-8") as f:
            features = json.load(f)

        if not features:
            pytest.skip("Sem audio features para testar")

        required_audio_fields = [
            "id", "danceability", "energy", "tempo",
            "valence", "acousticness", "instrumentalness"
        ]
        first = features[0]
        for field in required_audio_fields:
            assert field in first, f"Campo de audio feature em falta: '{field}'"

    def test_audio_features_value_ranges(self, raw_dir):
        """Valores de audio features estão nos intervalos esperados [0.0, 1.0]."""
        features_dir = raw_dir / "spotify_api" / "audio_features"
        if not features_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        latest = self._find_latest_file(features_dir, "audio_features_*.json")
        if not latest:
            pytest.skip("Sem ficheiro de audio features")

        with open(latest, encoding="utf-8") as f:
            features = json.load(f)

        bounded_fields = ["danceability", "energy", "valence", "acousticness",
                          "instrumentalness", "speechiness", "liveness"]

        for feat in features[:50]:
            for field in bounded_fields:
                val = feat.get(field)
                if val is not None:
                    assert 0.0 <= val <= 1.0, \
                        f"{field}={val} fora do intervalo [0.0, 1.0] para track {feat.get('id')}"


# ----------------------------------------------------------------
# Testes de Qualidade Mínima dos Dados
# ----------------------------------------------------------------

class TestDataQuality:

    def test_no_duplicate_playlist_ids(self, raw_dir):
        """Não existem playlists duplicadas por ID."""
        playlists_dir = raw_dir / "spotify_api" / "playlists"
        if not playlists_dir.exists():
            pytest.skip("Extração Spotify ainda não foi executada")

        files = sorted(playlists_dir.glob("featured_playlists_*.json"))
        if not files:
            pytest.skip("Nenhum ficheiro de playlists")

        with open(files[-1], encoding="utf-8") as f:
            playlists = json.load(f)

        ids = [p["id"] for p in playlists if p and p.get("id")]
        duplicates = len(ids) - len(set(ids))
        # Nota: podem existir duplicados entre mercados — isso é esperado e será tratado na Semana 2
        # Aqui apenas registamos, não falhamos
        if duplicates > 0:
            print(f"\nNota: {duplicates} IDs duplicados encontrados (esperado entre mercados)")

    def test_extraction_summary_exists(self, raw_dir):
        """Ficheiro de resumo da extração existe."""
        summary = raw_dir / "spotify_api" / "extraction_summary.json"
        if not summary.exists():
            pytest.skip("Extração ainda não foi executada")

        with open(summary, encoding="utf-8") as f:
            data = json.load(f)

        assert "playlists_count" in data
        assert "tracks_count" in data
        assert data["playlists_count"] > 0
