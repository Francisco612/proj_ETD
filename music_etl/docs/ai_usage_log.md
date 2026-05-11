# Registo de Uso de IA

## Projeto: Music & Entertainment ETL
## Abordagem: Spec-Driven Development

---

## Semana 1 — Extração

### Entrada 1 — Estrutura inicial do projeto

**Data:** [preencher]
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
- [ ] Código revisto pelo grupo
- [ ] Testado em ambiente local
- [ ] Credenciais Spotify testadas
- [ ] Nenhuma chave ou segredo nos ficheiros

**O que foi aceite / alterado / rejeitado:**
[preencher após revisão]

**Impacto no projeto:**
[preencher após execução]

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

---

*Este documento é um entregável obrigatório e será avaliado.*
