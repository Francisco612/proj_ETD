# 🎵 Music & Entertainment ETL Pipeline

Pipeline modular de ETL para análise de dados musicais.
Fontes: Spotify Web API · Spotify Million Playlist Dataset · MusicBrainz API

---

## Estrutura do Projeto

```
music_etl/
├── config/
│   └── settings.yaml          # Configuração centralizada
├── data/
│   ├── raw/                   # Dados brutos (não versionados)
│   │   ├── spotify_api/       # Extraídos da Spotify Web API
│   │   │   ├── playlists/
│   │   │   ├── tracks/
│   │   │   ├── audio_features/
│   │   │   └── artists/
│   │   ├── mpd_dataset/       # Spotify Million Playlist Dataset
│   │   └── musicbrainz/       # MusicBrainz API
│   └── staging/               # Dados transformados (Semana 2)
├── docs/
│   └── data_sources_inventory.md
├── logs/                      # Logs de execução (não versionados)
├── orchestration/
│   └── pipeline_week1.py      # Flow Prefect — Semana 1
├── src/
│   ├── extract/
│   │   ├── spotify_auth.py
│   │   ├── extract_spotify_api.py
│   │   ├── extract_mpd.py
│   │   └── extract_musicbrainz.py
│   └── utils/
│       ├── config.py
│       └── logger.py
├── tests/
│   └── test_week1_extraction.py
├── .env.example
├── .gitignore
├── requirements.txt
└── run_extraction.py          # Script principal
```

---

## Instalação e Configuração

### 1. Pré-requisitos

- Python 3.11+
- PyCharm (ou outro editor)
- Git

### 2. Clonar e criar ambiente virtual

```bash
# No terminal do PyCharm (ou Windows PowerShell na pasta do projeto):
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 3. Configurar credenciais Spotify

**Passo a passo para criar a app no Spotify:**

1. Vai a https://developer.spotify.com/dashboard
2. Inicia sessão com a tua conta Spotify (ou cria uma)
3. Clica em **"Create app"**
4. Preenche:
   - App name: `MusicETL`
   - App description: `Student ETL project`
   - Redirect URI: `http://localhost:8080` (obrigatório, mas não usado)
   - APIs: seleciona **Web API**
5. Aceita os termos e clica **Save**
6. Na página da app, clica em **Settings** para ver o `Client ID` e `Client Secret`

Depois:

```bash
# Copia o ficheiro de exemplo
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux

# Abre o .env e preenche as credenciais:
# SPOTIFY_CLIENT_ID=xxxxx
# SPOTIFY_CLIENT_SECRET=xxxxx
```

> ⚠️ **NUNCA** commites o ficheiro `.env` — está protegido pelo `.gitignore`

### 4. Download do MPD (Spotify Million Playlist Dataset)

O MPD é o dataset de maior volume do projeto (~5GB comprimido).

1. Vai a https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge
2. Cria conta na AIcrowd e aceita os termos
3. Faz download dos ficheiros `.zip`
4. Extrai para a pasta: `data/raw/mpd_dataset/`

A estrutura esperada:
```
data/raw/mpd_dataset/
├── mpd.slice.0-999.json
├── mpd.slice.1000-1999.json
├── ...
└── mpd.slice.999000-999999.json
```

> ℹ️ Enquanto não tens o MPD, podes correr o projeto só com as outras fontes.
> O script deteta automaticamente se o MPD está presente.

---

## Execução

### Extração completa (todas as fontes)

```bash
python run_extraction.py
```

### Extração por fonte

```bash
# Só Spotify API
python run_extraction.py --source spotify

# Só MPD (precisa do dataset descarregado)
python run_extraction.py --source mpd

# Só MusicBrainz (precisa do Spotify ter corrido antes)
python run_extraction.py --source mb
```

### Com Prefect (orquestração)

```bash
python orchestration/pipeline_week1.py

# Para ver o dashboard Prefect (opcional):
prefect server start
# Abre http://localhost:4200
```

### Testes

```bash
pytest tests/test_week1_extraction.py -v
```

---

## Perguntas Analíticas

1. **Como atributos de áudio (danceability, energy, valence) se relacionam com popularidade?**
2. **Existem perfis de playlists com "assinaturas sonoras" distintas?**
3. **Que padrões temporais ou de género musical explicam a aceitação do público?**
4. **Há diferenças entre mercados (PT vs US vs GB) nas playlists em destaque?**

---

## Fontes de Dados

| Fonte | Tipo | Uso |
|-------|------|-----|
| Spotify Web API | API | Playlists, tracks, audio features, artistas |
| Spotify MPD | Dataset estático (maior volume) | 1M playlists para análise de padrões |
| MusicBrainz API | API complementar | Géneros e metadados de artistas |

Cruzamento: `track_uri` (MPD ↔ Spotify) · `artist_name` (Spotify ↔ MusicBrainz)

---

## Uso de IA

Este projeto usa IA de forma transparente e documentada.
Ver: `docs/ai_usage_log.md` (criado ao longo do projeto)

---

## Estado do Projeto

| Semana | Módulo | Estado |
|--------|--------|--------|
| 1 | Extração | ✅ Em curso |
| 2 | Transformação | ⏳ Pendente |
| 3 | Carregamento | ⏳ Pendente |
| 4 | Visualização | ⏳ Pendente |
