# 🎵 Music & Entertainment ETL Pipeline

Pipeline modular de ETL para análise de dados musicais.

**Fontes:** Spotify Web API · Spotify Million Playlist Dataset · MusicBrainz API

---

## Estrutura do Projeto

```
music_etl/
├── config/
│   └── settings.yaml               # Configuração centralizada
├── data/
│   ├── raw/                        # Dados brutos (não versionados) — Camada Bronze
│   │   ├── spotify_api/            # Extraídos da Spotify Web API
│   │   │   ├── playlists/
│   │   │   ├── tracks/
│   │   │   ├── audio_features/
│   │   │   └── artists/
│   │   ├── mpd_dataset/            # Spotify Million Playlist Dataset
│   │   └── musicbrainz/            # MusicBrainz API
│   ├── staging/                    # Dados integrados e limpos (Semana 2) — Camada Silver
│   ├── gold/                       # Tabelas agregadas analíticas (Semana 2) — Camada Gold
│   └── metrics_quality/            # Relatórios de auditoria de Data Quality
├── docs/
│   └── data_sources_inventory.md
├── logs/                           # Logs de execução (não versionados)
├── orchestration/
│   └── pipeline_week1.py           # Flow Prefect — Semana 1
├── src/
│   ├── extract/
│   │   ├── spotify_auth.py
│   │   ├── extract_spotify_api.py
│   │   ├── extract_mpd.py
│   │   └── extract_musicbrainz.py
│   ├── transform/
│   │   ├── transform_staging.py        # Integração e limpeza (Silver)
│   │   ├── transform_quality.py        # Validação e Data Quality
│   │   └── transform_aggregations.py   # Agregações analíticas (Gold)
│   └── utils/
│       ├── config.py
│       └── logger.py
├── tests/
│   └── test_week1_extraction.py
├── .env.example
├── .gitignore
├── requirements.txt
└── run_extraction.py               # Script principal de extração
```

---

## Instalação e Configuração

### Requisitos Prévios

- Python 3.10 ou superior
- Ambiente Virtual (`venv`) ativo
- Ficheiro comprimido do MPD guardado localmente (ex: `C:\Users\...\Downloads\spotify_million_playlist_dataset.zip`)

### Instalação de Dependências

```bash
pip install -r requirements.txt
# Garanta que possui o pandas instalado para a fase de transformação:
pip install pandas
```

---

## Como Executar o Pipeline

### Semana 1 — Extração (Extract)

```bash
# Executar o fluxo completo de extração
python run_extraction.py

# Executar apenas o módulo específico do MPD (via streaming do ZIP)
python -m src.extract.extract_mpd
```

### Semana 2 — Transformação (Transform)

A fase de transformação processa o volume massivo de dados (mais de 3.3 milhões de linhas), higieniza o schema e gera as tabelas analíticas. Os scripts devem ser executados na seguinte ordem:

```bash
# 1. Executar a limpeza e o Left Join entre as fontes (Gera a Camada Silver)
python -m src.transform.transform_staging

# 2. Correr os testes de Data Quality (Gera relatórios em data/metrics_quality/)
python -m src.transform.transform_quality

# 3. Gerar as tabelas resumidas de métricas (Gera a Camada Gold)
python -m src.transform.transform_aggregations
```

---

## Perguntas Analíticas (Respondidas na Camada Gold)

**Como atributos de áudio (danceability, energy, valence) se relacionam com popularidade?**

**Existem perfis de playlists com "assinaturas sonoras" distintas?**

**Que padrões temporais ou de género musical explicam a aceitação do público?**
> Status: Respondido na tabela `dim_genre_ranking_gold_*.csv`, indicando o domínio absoluto do Hip Hop, Pop e Trap.

**Há diferenças entre mercados (PT vs US vs GB) nas playlists em destaque?**
> Status: Mapeado na tabela `dim_country_distribution_gold_*.csv`, revelando a dominância de consumo concentrada nos eixos US e CA.

---

## Fontes de Dados

| Fonte | Tipo | Uso |
|---|---|---|
| Spotify Web API | API | Playlists, tracks, audio features, artistas |
| Spotify MPD | Dataset estático (.zip pesado) | 1M playlists processadas via streaming de memória (Chunks) |
| MusicBrainz API | API complementar | Géneros, países e metadados biográficos de artistas |

**Estratégia de Cruzamento:** `artist_name` (Spotify MPD ↔ MusicBrainz) unificados através de um Left Join explícito na Camada Silver.

---

## Uso de IA

Este projeto usa IA de forma transparente, disciplinada e em conformidade com a abordagem Spec-Driven Development.

Toda a atividade, engenharia de prompts, validações críticas e decisões humanas estão documentadas em: `data/ai_usage_log.md`

---

## Estado do Projeto

| Semana | Módulo | Status | Entregáveis Principais |
|---|---|---|---|
| Semana 1 | Extração (Extract) | ✅ 100% Concluído | Ficheiros RAW (Bronze), Autenticação API, Integração Prefect |
| Semana 2 | Transformação (Transform) | ✅ 100% Concluído | Camada Silver (3.3M linhas), Camada Gold (Agregações), Relatório DQ |
| Semana 3 | Carregamento (Load) | 📅 Próximo Passo | Persistência em Base de Dados Local (SQLite/DuckDB) |
| Semana 4 | Visualização (Visualization) | ⏳ Em espera | Dashboard Analítico e Storytelling dos Dados |****