# Argus App
 
> Agente autônomo de Bug Bounty — recon, API discovery, crawling e parameter extraction.
> Uso **exclusivo** em programas de Bug Bounty e ativos explicitamente autorizados.

![status](https://img.shields.io/badge/status-v0.3.0-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![django](https://img.shields.io/badge/django-5.x-green)
![license](https://img.shields.io/badge/uso-autorizado-red)

> *Argus Panoptes — o gigante de cem olhos que nunca dormia.*
> Vê tudo, mas só relata o que foi autorizado a ver.
---

## ⚠️ Aviso legal

O Argus executa recon **ativo** contra o alvo. Rodar contra qualquer domínio
sem autorização escrita é **crime** na maioria das jurisdições
(Lei 12.737/2012 no Brasil, CFAA nos EUA, Computer Misuse Act no Reino Unido).

- Use **apenas** em programas de Bug Bounty em que você esteja inscrito.
- Use **apenas** em ativos que você possui ou tem autorização formal.
- O scope engine bloqueia o que **não** está declarado — o que está declarado,
  ele **presume autorizado**. A responsabilidade é sempre sua.

O autor do Argus não se responsabiliza por uso indevido.

---

## O que é

Argus é uma **plataforma autônoma de reconhecimento** orientada a evidências.
Não é "um script que roda nmap". Ele:

- valida escopo antes de qualquer coisa;
- enumera subdomínios, resolve DNS e faz HTTP probing;
- faz crawling real com katana (headless + JS analysis);
- descobre APIs (Swagger, OpenAPI, GraphQL, REST);
- extrai parâmetros de query strings e formulários HTML;
- persiste tudo em banco relacional com histórico;
- expõe consultas via CLI **e** interface web (Django);
- executa scans de forma assíncrona com estados explícitos.

Ferramentas são **sensores**. Argus é o **cérebro** que decide o que rodar,
contra o quê, e o que fazer com o resultado.

**Princípio fundamental:** `tool-agnostic + evidence-driven + scope-aware + modular`.
EOF
echo "OK bloco 1/6"

cat >> README.md << 'EOF'

---

## Features

| Categoria | O que faz |
|-----------|-----------|
| **Scope engine** | wildcards, precedência de exclusão, validação em 3 camadas |
| **Recon passivo/ativo** | subfinder, dnsx, httpx |
| **Crawling** | katana com headless + JS analysis |
| **API discovery** | Swagger, OpenAPI, GraphQL, REST |
| **Parameter extraction** | query strings + forms HTML |
| **CLI** | Typer + Rich + shell interativo com histórico |
| **Web** | Django 5 + Bootstrap + HTMX + DRF |
| **Execução assíncrona** | Celery + Redis (fallback em thread para dev) |
| **Estados de scan** | queued / running / completed / failed / cancelled |
| **Multi-tenant** | cada usuário vê só seus programas e scans |
| **Cancelamento** | botão na UI + checagem cooperativa no worker |
| **Auditoria** | ScanStage + ScanEvent registram cada etapa |

---

## Instalação

### Requisitos

- Python 3.10+
- Go 1.21+ (para as ferramentas de recon)
- Linux, macOS ou WSL2

### 1. Clonar e criar venv

```bash
git clone <repo> Argus-App
cd Argus-App
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-web.txt
```

### 2. Instalar ferramentas
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

# Argus — Roadmap

> Agente autônomo de Bug Bounty orientado a evidências.
> **Uso exclusivo em programas autorizados.**

*Argus Panoptes — cem olhos, um escopo.*

---

## Status atual

| Versão | Fase | Estado |
|--------|------|--------|
| 0.1.0 | Fundação (CLI + core) | ✅ |
| 0.2.0 | API Discovery | ✅ |
| 0.3.0 | Crawling (katana) | ✅ |
| 0.4.0 | Orquestração assíncrona | ✅ |
| 0.5.0 | Web multi-tenant | ✅ |
| 0.6.0 | Diff + curadoria | ✅ |
| 0.7.0 | Export (md/csv/json) | ✅ |
| 0.8.0 | Wordlists + API Recon | ✅ |
| 0.9.0 | Redesign UI (Cyber Ops) | ✅ |
| 1.0.0 | Findings (nuclei) | 🔄 próxima |
| 1.1.0 | Reporting profissional | ⏳ |
| 1.2.0 | AI Orchestrator | ⏳ |

---

## Princípios inegociáveis

1. **Escopo primeiro.** Nada roda sem validar contra o programa.
2. **Exclusão tem precedência** sobre inclusão.
3. **Ferramenta reportando ≠ vulnerabilidade.** Sem evidência = SUSPICIOUS.
4. **Nenhuma técnica destrutiva** sem autorização escrita explícita.
5. **Nenhuma evidência** armazena tokens/PII em claro.
6. **IA não executa nada** sem regra explícita no escopo.
7. **Critérios de parada claros.** O agente sabe quando parar.
8. **Tool-agnostic.** Core conhece abstrações, não ferramentas.

---

## ✅ v0.1.0 — Fundação

**CLI + scope engine + recon passivo/ativo**

- Scope engine com wildcards + precedência
- Wizard interativo (`argus init`)
- Shell com histórico (`~/.argus_history`)
- Adapters: **subfinder**, **dnsx**, **httpx**
- Banco SQLite + SQLAlchemy
- Banner ASCII + auto-descoberta de binários Go em `~/go/bin`

## ✅ v0.2.0 — API Discovery

**Descoberta de APIs + extração de parâmetros**

- Wordlist de paths (~130 entradas configuráveis)
- Classificador de API (swagger / openapi / graphql / rest)
- Filtro de status por tipo (rejeita 404)
- Extração de params (query + forms HTML)
- Rate limit propagado

## ✅ v0.3.0 — Crawling

**Reconhecimento dinâmico via katana**

- Adapter katana (headless + JS analysis)
- Endpoint model + deduplicação
- Integração: URLs do crawl alimentam API discovery
- Flag `--crawl-depth`

## ✅ v0.4.0 — Orquestração

**Scans assíncronos com estado**

- Celery + Redis (fallback thread para dev)
- Máquina de estados: `queued → running → completed/failed/cancelled`
- `ScanStage` + `ScanEvent` (auditoria)
- Cancelamento cooperativo (polling entre eventos)
- Pipeline como **gerador de eventos** (sem prints)

## ✅ v0.5.0 — Web Multi-tenant

**Plataforma Django com isolamento por owner**

- Apps: `accounts`, `programs`, `assets`, `scans`, `orchestration`, `results`
- CRUD de programas + editor de escopo
- Multi-tenant (filtro por `owner` em todas as views)
- 4 abas de achados por scan (assets/endpoints/apis/params)
- Páginas de etapa (`/scans/<pk>/stage/<nome>/`)
- Testes de isolamento (52+)

## ✅ v0.6.0 — Diff + Curadoria

**Comparação entre scans + verificação manual**

- Diff presença: novos / removidos / inalterados
- Diff conteúdo: mudança de campo (IP, status, content-type)
- Snapshot por scan (permite detectar mudanças)
- 4 estados de curadoria: `discovered / interesting / verified / false_positive`
- Revisar / excluir scan (com confirmação)
- Backfill de scans antigos (`--force`)

## ✅ v0.7.0 — Export

**Relatórios prontos para bug bounty**

- Markdown (relatório estruturado)
- CSV (planilha)
- JSON (integração)
- Todos respeitam a verificação humana

## ✅ v0.8.0 — Wordlists + API Recon

**Gerenciamento e trigger dedicado**

- App `wordlists` (upload + colar + drag-drop)
- 5 tipos: api / content / params / subdomains / useragent
- Comando `seed_wordlists` (builtin)
- Página `/results/api-recon/`: trigger + resultados por tipo
- Scans API-only (`is_api_recon`: sem crawl)

## ✅ v0.9.0 — Redesign UI

**ARGUS // CYBER OPERATIONS**

- Design system (tokens CSS, tipografia)
- Sidebar fixa + header com status
- Dark mode (Bootstrap 5.3 + `data-bs-theme`)
- Paleta verde neon sobre preto
- Responsivo (grid, flexbox, mobile)
- Sem hover animado em tabelas/cards/botões
- Correção de contraste (texto em fundo escuro)

---

## 🔄 v1.0.0 — Findings (nuclei)

**Transformar recon em vulnerabilidades**

### Adapters
- `NucleiAdapter` (já existe no core — falta UI)
- Modo passivo por padrão: `-tags exposure,misconfig,tech,ssl,dns`
- Templates CVE/injection exigem flag explícita

### Model
- `Finding`:
  - `scan`, `asset`, `endpoint`
  - `template_id`, `title`, `severity`
  - `evidence` (sanitizado), `curl_command`
  - `verification`: suspicious / verified / false_positive
  - `confidence`: 0.0 – 1.0
  - `first_seen`, `last_seen`
- Deduplicação por `(asset, url, template_id)`

### Etapa no pipeline
- `vulns` (step 7) entre API e params
- Eventos: `finding.found`
- **Nunca** marcar `verified` automaticamente

### UI
- 5ª aba no scan: **Findings**
- Página `/results/findings/` com filtros por severidade
- Cards de severidade no dashboard
- Evidência expansível + curl reproduzível

### Critérios de aceite
- Nenhum finding é `verified` sem ação humana
- Templates destrutivos bloqueados por padrão
- Evidência nunca expõe tokens/PII em claro

---

## ⏳ v1.1.0 — Reporting profissional

**Relatórios exportáveis + histórico**

- Gerador HTML self-contained (offline)
- Template com identidade Argus
- Timeline visual de scans
- Comparação de findings entre scans
- Diff de severidade (novos críticos desde ontem)
- Sumário executivo gerado (estrutura, não IA)
- Integração: botão "Gerar relatório" no scan

## ⏳ v1.2.0 — AI Orchestrator

**IA como camada de raciocínio, não de execução**

### Entregas
- Decision Engine (qual ferramenta rodar agora)
- Priority Score por asset:
  - exposição, tipo, tech, endpoints sensíveis
- Adaptive scanning (profundidade conforme sinal)
- Deduplicação semântica (LLM classifica findings similares)
- Critérios de parada explícitos
- Custo de LLM medido e limitado por scan

### Guardrails
- IA não executa nada sem regra explícita
- Envio apenas de dados estruturados (nunca logs crus)
- Fallback quando API do LLM falha

---

## Backlog (não priorizado)

- **Filtros salvos** em `/results/` (views por usuário)
- **Notificações** (Discord/Slack/Telegram)
- **Modo daemon** (watch de alvos cadastrados)
- **Multi-programa** em paralelo
- **Integração** HackerOne / Bugcrowd (import de escopo)
- **Export STIX 2.1** para threat intel
- **Gráficos** no dashboard (scans/dia, top hosts)
- **Port scan** (naabu + nmap) — Fase 2 original ainda pendente
- **JS Analysis** profundo (segredos, endpoints hardcoded)
- **OpenAPI parser** (transformar spec em endpoints testáveis)

---

## Fora de escopo (decisão arquitetural)

- Exploração destrutiva automatizada
- Coleta indiscriminada de dados
- Execução arbitrária de comandos via UI
- Armazenamento de credenciais de terceiros
- Scanners "one-shot" sem parsing estruturado
- Ferramentas que exigem root

---

## Métricas de qualidade

| Métrica | Meta |
|---------|------|
| Cobertura de testes | > 70% |
| Tempo de resposta (p95) | < 300ms |
| Scans canceláveis | 100% |
| Achados rastreáveis | 100% |
| Isolamento multi-tenant | 100% |

---

## Aviso legal

Uso exclusivo em programas de Bug Bounty e ativos com autorização escrita.
Rodar contra qualquer domínio sem autorização é crime na maioria das
jurisdições (Lei 12.737/2012 BR, CFAA US, CMA UK).

---

*Última atualização: 2026-10 · Mantenedor: luizwhoami*
