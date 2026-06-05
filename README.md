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
│   ├── raw/                   # Dados brutos (não versionados) - Camada Bronze
│   │   ├── spotify_api/       # Extraídos da Spotify Web API
│   │   │   ├── playlists/
│   │   │   ├── tracks/
│   │   │   ├── audio_features/
│   │   │   └── artists/
│   │   ├── mpd_dataset/       # Spotify Million Playlist Dataset
│   │   └── musicbrainz/       # MusicBrainz API
│   ├── staging/               # Dados integrados e limpos (Semana 2) - Camada Silver
│   ├── gold/                  # Base de dados relacional e agregados - Camada Gold
│   │   └── music_analytics.db # Ficheiro físico final da Base de Dados DuckDB
│   └── metrics_quality/       # Relatórios de auditoria de Data Quality
├── docs/
│   └── data_sources_inventory.md
├── logs/                      # Logs de execução (não versionados)
├── orchestration/
│   └── pipeline_week1.py      # Flow Prefect — Semana 1
├── api.py                     # Backend REST API com FastAPI & Swagger (Semana 4)
├── app.py                     # Frontend Dashboard Interativo com Streamlit (Semana 4)
├── src/
│   ├── extract/
│   │   ├── spotify_auth.py
│   │   ├── extract_spotify_api.py
│   │   ├── extract_mpd.py
│   │   └── extract_musicbrainz.py
│   ├── transform/
│   │   ├── transform_staging.py       # Integração e limpeza (Silver)
│   │   ├── transform_quality.py       # Validação e Data Quality
│   │   └── transform_aggregations.py  # Agregações analíticas (Gold)
│   └── load/
│       └── load_to_db.py              # Carregamento e validação SQL (Semana 3)
│   └── utils/
│       ├── config.py
│       └── logger.py
├── tests/
│   └── test_week1_extraction.py
├── .env.example
├── .gitignore
├── requirements.txt
└── run_extraction.py          # Script principal de extração
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
# Garanta que possui as bibliotecas da API e do ecossistema visual instaladas:
pip install pandas duckdb fastapi uvicorn streamlit plotly requests
```

---

## Como Executar o Pipeline

### Semana 1 — Extração (Extract)
```bash
# Executar o fluxo completo de extração
python run_extraction.py
```

### Semana 2 — Transformação (Transform)
```bash
# 1. Executar a limpeza e o Left Join (Gera a Camada Silver)
python -m src.transform.transform_staging

# 2. Correr os testes de Data Quality (Gera relatórios em data/metrics_quality/)
python -m src.transform.transform_quality

# 3. Gerar as tabelas resumidas de métricas (Gera a Camada Gold em CSV)
python -m src.transform.transform_aggregations
```

### Semana 3 — Carregamento (Load)
```bash
# Criar a estrutura física relacional e executar o Bulk Load analítico no DuckDB
python -m src.load.load_to_db
```

### Semana 4 — Visualização (Visualization & API)
Como o projeto adota uma arquitetura desacoplada de microsserviços, deve iniciar o backend e o frontend em terminais separados:

```bash
# Terminal 1: Iniciar o servidor Backend (FastAPI + Swagger)
uvicorn api:app --reload

# Terminal 2: Iniciar a interface do Dashboard (Streamlit)
streamlit run app.py
```

---

## Perguntas Analíticas (Respondidas na Camada Gold & Dashboard)

**Como atributos de áudio (danceability, energy, valence) se relacionam com popularidade?**
> Status: Tratado de forma macro através da concentração de recorrência e retenção de audiência. O pipeline demonstra um efeito *Winner-Take-All*, onde super-estrelas como Drake monopolizam as playlists.

**Existem perfis de playlists com "assinaturas sonoras" distintas?**
> Status: Analisado no painel de dispersão. A alta recorrência de hits dominantes indica uma forte homogeneidade na curadoria humana, criando assinaturas partilhadas em vez de nichos isolados.

**Que padrões temporais ou de género musical explicam a aceitação do público?**
> Status: Respondido na tabela `gold_genre_ranking` e validado graficamente. Os géneros urbanos dominam o mercado, liderados pelo Hip Hop (2.08M aparições), Pop (2.06M) e Trap (1.78M).

**Há diferenças entre mercados (PT vs US vs GB) nas playlists em destaque?**
> Status: Mapeado na tabela `gold_country_distribution` e traduzido por extenso. Revela um afunilamento massivo do consumo centrado no eixo norte-americano (Estados Unidos e Canadá), controlando mais de 80% do tráfego.

---

## Fontes de Dados

| Fonte | Tipo | Uso |
|---|---|---|
| Spotify Web API | API | Playlists, tracks, audio features, artistas |
| Spotify MPD | Dataset estático (.zip pesado) | 1M playlists processadas via streaming de memória (Chunks) |
| MusicBrainz API | API complementar | Géneros, países e metadados biográficos de artistas |

**Estratégia de Cruzamento:** `artist_name` (Spotify MPD ↔ MusicBrainz) unificados através de um Left Join explícito na Camada Silver.

---

## Modelação de Dados: Modelo Dimensional (Star Schema)

A arquitetura de armazenamento adota uma estratégia **Híbrida/Dimensional** no **DuckDB**. O microdado granular de interações está mapeado na tabela de factos central, enquanto os sumários estatísticos estão instanciados em tabelas Gold de alta performance indexadas e expostas por endpoints HTTP.

### Diagrama Entidade-Relação (ERD Textual)

```
        gold_genre_ranking
        [ mb_genres (FK) | frequencia_nas_playlists ]
                     │
                     ▼
           fact_playlists_tracks (Tabela Mãe de Factos)
           [ playlist_id (PK)       | playlist_name ]
           [ playlist_followers     | track_pos     ]
           [ track_name             | track_uri     ]
           [ artist_name (FK)       | album_name    ]
           [ track_duration_min     | ...           ]
                     ▲
                     │
           ┌─────────┴─────────┐
           │                   │
           ▼                   ▼
 gold_artist_popularity     gold_country_distribution
 [ artist_name (PK) ]       [ mb_country (PK) ]
 [ total_aparicoes  ]       [ total_faixas_ouvidas ]
 [ playlists_unicas ]       [ seguidores_impactados ]
```

### Decisões de Performance e Armazenamento
* **DuckDB (OLAP):** Escolha fundamentada na sua arquitetura de armazenamento colunar, permitindo a vetorização de queries e varrimento de milhões de linhas em milissegundos.
* **Tipagem Robusta:** As colunas temporais da MusicBrainz (`mb_begin_date` e `mb_end_date`) foram forçadas explicitamente como `VARCHAR` para acomodar anos de fundação truncados (ex: `"1969"`) sem induzir falhas de conversão no motor de dados.
* **Desacoplamento por API (FastAPI):** A camada física está isolada do cliente visual. Os dados chegam ao painel em formato JSON através de endpoints documentados nativamente via Swagger UI (`/docs`).

---

## Validação de Integridade Pós-Carga (Data Quality SQL)
A integridade da carga é auditada de forma síncrona pelo script através de asserções SQL diretas:
* **Integridade de Carga:** Verificação absoluta de correspondência matemática: **3.324.938 / 3.324.938 linhas** (`PASS`).
* **Integridade Referencial:** Query `LEFT JOIN` de orfandade acusando **0 artistas desalinhados** entre factos e agregados (`PASS`).

---

## Uso de IA

Este projeto usa IA de forma transparente, disciplinada e em conformidade com a abordagem *Spec-Driven Development*.
Toda a atividade, engenharia de prompts, validações críticas e decisões humanas estão documentadas em: `ai_usage_log.md`

---

## Estado do Projeto

| Semana | Módulo | Status | Entregáveis Principais |
|--------|--------|--------|------------------------|
| **Semana 1** | Extração (Extract) | 100% Concluído | Ficheiros RAW (Bronze), Autenticação API, Integração Prefect |
| **Semana 2** | Transformação (Transform) | 100% Concluído | Camada Silver (3.3M linhas), Camada Gold (Agregações), Relatório DQ |
| **Semana 3** | Carregamento (Load) | 100% Concluído | Esquema Estrela DuckDB, Script `load_to_db.py`, Validação SQL |
| **Semana 4** | Visualização (Visualization) | 100% Concluído | FastAPI Backend, Swagger UI, Dashboard Streamlit (Storytelling) |