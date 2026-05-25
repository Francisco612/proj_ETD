# Registo de Uso de IA

## Projeto: Music & Entertainment ETL
## Abordagem: Spec-Driven Development

---

## Semana 1 — Extração

### Entrada 1 — Estrutura inicial do projeto

**Data:** [preencher data da semana passada]
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
- Logs são criados em logs/\n- `pytest tests/` passa

**Output da IA:**
Estrutura completa de ficheiros com src/extract/, src/utils/, orchestration/, tests/

**Validação humana:**
- [x] Código revisto pelo grupo
- [x] Testado em ambiente local
- [x] Credenciais Spotify testadas
- [x] Nenhuma chave ou segredo nos ficheiros

**O que foi aceite / alterado / rejeitado:**
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
- Processamento performante e em memória controlada (streaming/chunks) para lidar com mais de 3 milhões de linhas.
- Cumprimento de regras de Data Quality (remoção de duplicados, tratamento de nulos e filtragem de outliers).
- Produção de um relatório de qualidade de dados (`.md` e `.json`) autónomo para auditoria técnica.
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

**O que foi aceite / alterado / rejeitado:**
Aceite a lógica de herança e enriquecimento de dados via Left Join. Foram validados criticamente os alertas de `WARNING` gerados no relatório de qualidade, sendo interpretados humanamente como corretos (ex: a alta taxa de nulos em `mb_end_date` comprova que a maioria dos artistas monitorizados continua no ativo, o que valida a integridade do dataset).

**Impacto no projeto:**
Conclusão total dos objetivos da Semana 2. Os dados de maior volume foram domados e as tabelas finais da Camada Gold ocupam agora escassos kilobytes, estando perfeitamente otimizadas para a fase de carregamento em base de dados e visualização gráfica.

---

## Template para novas entradas

### Entrada N — [título]

**Data:**
**Ferramenta:**

**Intenção / Objetivo:**

**Requisitos definidos antes:**

**Critérios de aceitação:**

**Output da IA:**

**Validação humana:**
- [ ] Código revisto
- [ ] Testado
- [ ] Sem dados sensíveis

**O que foi aceite / alterado / rejeitado:**

**Impacto no projeto:**