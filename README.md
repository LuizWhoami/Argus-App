# Argus
 
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
