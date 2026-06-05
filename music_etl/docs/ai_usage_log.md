# Registo de Uso de IA

## Projeto: Music & Entertainment ETL
## Abordagem: Spec-Driven Development

---

## Semana 1 — Extração

### Entrada 1 — Estrutura inicial do projeto

**Data:** 15 de Maio de 2026
**Ferramenta:** Claude (Anthropic)

**Intenção / Objetivo:**
Criar a estrutura modular do pipeline ETL para a Semana 1, incluindo
scripts de extração para Spotify API, MPD e MusicBrainz.

**Requisitos definidos antes da geração:**
- Pipeline modular com separação clara por módulo
- Configuração centralizada em .env + settings.yaml
- Logging estruturado
- Scripts reutilizáveis (não notebooks monolíticos)
- Tratamento de rate limits e erros
- Testes básicos de validação

**Critérios de aceitação:**
- `python run_extraction.py` corre sem erros
- Dados são guardados em data/raw/ com timestamp
- Logs são criados em logs/
- `pytest tests/` passa

**Output da IA:**
Estrutura completa de ficheiros com src/extract/, src/utils/, orchestration/, tests/

**Validação humana:**
- [x] Código revisto pelo grupo
- [x] Testado em ambiente local
- [x] Credenciais Spotify testadas
- [x] Nenhuma chave ou segredo nos ficheiros

**O que foi aceito / alterado / rejeitado:**
Aceite na totalidade a estrutura de pastas e a filosofia de configuração centralizada para garantir a reprodutibilidade.

**Impacto no projeto:**
Módulos de extração base funcionais e isolados, prontos a alimentar as fases seguintes.

---

## Semana 2 — Transformação

### Entrada 2 — Implementação da Camada Staging, Data Quality e Agregações

**Data:** 22 de Maio de 2026
**Ferramenta:** Gemini (Google)

**Intenção / Objetivo:**
Desenvolver os módulos de transformação de dados usando a biblioteca Pandas. O objetivo envolve o achatamento (flattening) do dataset volumoso (Spotify MPD), a integração via Join com os metadados da MusicBrainz, a criação de validações automáticas de qualidade e a geração de tabelas analíticas agregadas (Camada Gold).

**Requisitos definidos antes da geração:**
- Código modular e em scripts Python puros (`.py`), rejeitando arquiteturas monolíticas.
- Processamento performante e em memória controlada para lidar com mais de 3 milhões de linhas.
- Cumprimento de regras de Data Quality (remoção de duplicados, tratamento de nulos e filtragem de outliers).
- Production de um relatório de qualidade de dados (`.md` e `.json`) autónomo para auditoria técnica.
- Separação clara dos dados em camadas (Silver/Staging e Gold/Curated).

**Critérios de aceitação:**
- Execução do script `transform_staging.py` sem erros, gerando uma tabela unificada (Silver).
- Geração bem-sucedida do relatório de qualidade (`transform_quality.py`) acusando o estado das métricas.
- Criação de três tabelas analíticas leves (`transform_aggregations.py` para popularidade de artistas, géneros e países) prontas para consumo.

**Output da IA:**
Três scripts Python modulares (`transform_staging.py`, `transform_quality.py`, `transform_aggregations.py`) estruturados com logs e tratamento robusto de caminhos de ficheiros através da biblioteca `pathlib`.

**Validação humana:**
- [x] Código revisto e integrado na pasta `src/transform/`
- [x] Executado localmente no terminal da `venv` com sucesso
- [x] Verificado o volume final de dados (3.324.938 linhas processadas em menos de 1 minuto)
- [x] Confirmação da criação correta dos ficheiros CSV na pasta `data/staging/` e `data/gold/`

**O que foi aceito / alterado / rejeitado:**
Aceite a lógica de herança e enriquecimento de dados via Left Join. Foram validados criticamente os alertas de `WARNING` gerados no relatório de qualidade, sendo interpretados humanamente como corretos (ex: a alta taxa de nulos em `mb_end_date` comprova que a maioria dos artistas monitorizados continua no ativo, o que valida a integridade do dataset).

**Impacto no projeto:**
Conclusão total dos objetivos da Semana 2. Os dados de maior volume foram domados e as tabelas finais da Camada Gold ocupam agora escassos kilobytes, estando perfeitamente otimizadas para a fase de carregamento em base de dados e visualização gráfica.

---

## Semana 3 — Carregamento (Load)

### Entrada 3 — Modelação e Carregamento para Base de Dados Analítica DuckDB

**Data:** 30 de Maio de 2026
**Ferramenta:** Gemini (Google)

**Intenção / Objetivo:**
Desenhar o esquema relacional final (Star Schema), criar as tabelas analíticas com tipos de dados explícitos e automatizar a carga em massa (Bulk Load) da Camada Silver e Camada Gold para dentro de um motor de armazenamento local DuckDB.

**Requisitos definidos antes da geração:**
- Escolha justificada de um motor de armazenamento OLAP colunar para alta performance local.
- Criação física das tabelas via SQL/DDL dinâmico e tratamento de tipos de dados complexos.
- Implementação de um módulo de integridade pós-carga com queries SQL de validação.
- Orquestração sem dependência de persistência volátil (RAM).

**Critérios de aceitação:**
- Criação física do ficheiro local `data/gold/music_analytics.db`.
- Carregamento bem-sucedido de 3.324.938 linhas sem truncagem de schemas.
- Validação pós-carga com 100% de coesão referencial (`PASS`) impressa nos logs.

**Output da IA:**
Script modular `load_to_db.py` com integração nativa do leitor analítico do DuckDB (`read_csv_auto`), parametrização explícita de tipos varchar e rotinas SQL de contagem.

**Validação humana:**
- [x] Script integrado e executado com sucesso em 7.25 segundos.
- [x] Ligação estabelecida e validada visualmente na aba Database do PyCharm Professional.
- [x] Tratamento crítico do erro de conversão de tipos resolvido (forçada a leitura de `mb_begin_date` e `mb_end_date` como `VARCHAR` para suportar anos isolados como '1969' sem quebrar o pipeline).
- [x] Verificação bem-sucedida das constraints de Chaves Primárias e integridade referencial.

**Impacto no projeto:**
A Semana 3 está totalmente concluída. O pipeline saiu do ciclo de ficheiros planos soltos e passou para uma base de dados analítica relacional trancada, otimizada e pronta para alimentar de forma instantânea as consultas do Dashboard.

---

## Semana 4 — Visualização e Storytelling

### Entrada 4 — Desenvolvimento da Arquitetura REST e Dashboard Interativo Desacoplado

**Data:** 05 de Junho de 2026
**Ferramenta:** Gemini (Google)

**Intenção / Objetivo:**
Criar uma infraestrutura distribuída de microsserviços desacoplada para disponibilizar e visualizar as métricas de negócio da base de dados DuckDB, gerando uma API REST intermédia documentada e um painel visual focado em Data Storytelling.

**Requisitos definidos antes da geração:**
- Isolamento total da camada física de dados através de chamadas HTTP (rejeitando conexões diretas da UI à BD).
- Desenvolvimento do servidor backend em scripts Python puros recorrendo à framework FastAPI.
- Geração automática de documentação técnica interativa e tipada via OpenAPI (Swagger UI).
- Otimização e tradução em tempo real de siglas ISO de países (ex: 'US', 'PT') para nomes por extenso legíveis usando instruções SQL `CASE WHEN`.
- Construção de interface frontend reativa em Streamlit estruturada em colunas assíncronas, containers estéticos e separadores de inspeção.

**Critérios de aceitação:**
- Execução síncrona do backend (`api.py`) e frontend (`app.py`) em portas de rede independentes.
- Resposta em formato JSON íntegro no ecossistema Swagger no endpoint `/docs`.
- Renderização em tempo real de painéis gráficos em Plotly com caixas de conclusões reativas e filtros dinâmicos na barra lateral sem perdas ou latências.

**Output da IA:**
Códigos e arquiteturas completos estruturados em dois ficheiros funcionais (`api.py` e `app.py`) integrando os pacotes `fastapi`, `uvicorn`, `streamlit`, `plotly` e `requests`.

**Validação humana:**
- [x] Servidor local e interface testados em simultâneo com sucesso no browser.
- [x] Verificada a reatividade imediata das queries analíticas ao alterar filtros na barra lateral.
- [x] Confirmação visual de que as siglas foram substituídas por nomes de países por extenso em todos os componentes.
- [x] Integração final do histórico e governança com a revisão técnica do ficheiro `.gitignore`.

**O que foi aceito / alterado / rejeitado:**
Aceite o padrão de desacoplamento completo por ser uma prática de nível empresarial. O grupo aplicou validações manuais sobre o mapeamento reverso dos filtros para garantir que a tradução de strings do ecrã não quebrasse as pesquisas indexadas do motor SQL do DuckDB.

**Impacto no projeto:**
Módulo da Semana 4 concluído a 100%. O ecossistema ETL saiu de uma lógica puramente sequencial de processamento de ficheiros locais e transformou-se numa aplicação corporativa moderna distribuída, interativa e pronta a ser apresentada e avaliada pelo corpo docente.