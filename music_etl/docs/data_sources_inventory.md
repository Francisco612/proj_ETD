# Inventário de Fontes de Dados — Semana 1

## Projeto: Music & Entertainment ETL

---

## Fonte 1 — Spotify Web API (API Principal)

| Atributo | Detalhe |
|----------|---------|
| **Tipo** | API REST (JSON) |
| **URL** | https://api.spotify.com/v1 |
| **Autenticação** | Client Credentials (OAuth 2.0) |
| **Rate Limit** | ~100 req/min (varia por endpoint) |
| **Licença** | Spotify Developer Terms of Service |
| **Dados extraídos** | Playlists featured, tracks, audio features, artistas |

### Endpoints utilizados

| Endpoint | Dados | Paginação |
|----------|-------|-----------|
| `/browse/featured-playlists` | Playlists em destaque por mercado | offset/limit |
| `/playlists/{id}/tracks` | Tracks de uma playlist | offset/limit |
| `/audio-features` | Features de áudio (batch até 100) | batch |
| `/artists` | Metadados de artistas (batch até 50) | batch |

### Campos chave extraídos

**Playlists:** `id`, `name`, `description`, `owner`, `tracks.total`

**Tracks:** `id`, `name`, `duration_ms`, `popularity`, `explicit`, `artists`, `album`

**Audio Features:** `danceability`, `energy`, `key`, `loudness`, `speechiness`,
`acousticness`, `instrumentalness`, `liveness`, `valence`, `tempo`, `time_signature`

**Artistas:** `id`, `name`, `genres`, `popularity`, `followers`

---

## Fonte 2 — Spotify Million Playlist Dataset (Dataset Principal — Maior Volume)

| Atributo | Detalhe |
|----------|---------|
| **Tipo** | Dataset estático (JSON) |
| **URL** | https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge |
| **Volume** | ~5GB comprimido, ~33GB descomprimido |
| **Registos** | ~1.000.000 playlists, ~66.000.000 track entries |
| **Formato** | 1000 ficheiros JSON (slices), cada slice = 1000 playlists |
| **Licença** | Spotify Research — uso não comercial / académico |

### Justificação como "dataset de maior volume"

O MPD contém 1 milhão de playlists com ~66M entradas de tracks. O carregamento
completo em memória seria inviável (>10GB RAM). A estratégia de processamento
em chunks (slice a slice) é necessária para execução local eficiente.

### Campos por playlist

`pid`, `name`, `collaborative`, `modified_at`, `num_tracks`, `num_albums`,
`num_followers`, `num_edits`, `duration_ms`, `num_artists`, `tracks[]`

### Campos por track no MPD

`pos`, `artist_name`, `track_uri`, `artist_uri`, `track_name`, `album_uri`,
`duration_ms`, `album_name`

---

## Fonte 3 — MusicBrainz API (Fonte Complementar)

| Atributo | Detalhe |
|----------|---------|
| **Tipo** | API REST (JSON) |
| **URL** | https://musicbrainz.org/ws/2 |
| **Autenticação** | Não requer (rate limit: 1 req/s) |
| **Licença** | CC0 (domínio público) |
| **Uso** | Enriquecimento de géneros e metadados de artistas |

### Campos extraídos

**Artistas:** `mbid`, `name`, `type` (Person/Group), `country`, `area`,
`begin_date`, `end_date`, `genres[]`, `tags[]`

---

## Estratégia de Integração entre Fontes

| Cruzamento | Chave de Ligação | Objetivo |
|------------|-----------------|----------|
| Spotify API + MPD | `track_uri` / Spotify Track ID | Enriquecer tracks do MPD com audio features |
| Spotify API + MusicBrainz | `artist_name` (fuzzy match) | Adicionar géneros e dados biográficos |
| MPD + Spotify API | `playlist_name` (heurístico) | Comparar padrões de popularidade |

---

## Riscos Técnicos Identificados

| Risco | Mitigação |
|-------|-----------|
| Rate limits da Spotify API | Sleep entre requests, retry com backoff |
| MPD requer registo na AIcrowd | Documentado no README |
| MusicBrainz: artistas não encontrados | Match por nome + fallback gracioso |
| MPD: formato inconsistente entre slices | Leitura defensiva com try/except |

---

*Gerado automaticamente — Semana 1 — Music ETL Project*
