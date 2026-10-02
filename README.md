cat > README.md << 'EOF'
# Aegis

> Agente autônomo de Bug Bounty — recon, API discovery e parameter extraction.
> Uso **exclusivo** em programas de Bug Bounty e ativos explicitamente autorizados.

![status](https://img.shields.io/badge/status-fase%201.5-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/uso-autorizado-red)

---

## ⚠️ Aviso legal

O Aegis executa recon **ativo** contra o alvo. Rodar contra qualquer domínio
sem autorização escrita é **crime** na maioria das jurisdições
(ex.: Lei 12.737/2012 no Brasil, CFAA nos EUA, Computer Misuse Act no Reino Unido).

- Use **apenas** em programas de Bug Bounty em que você esteja inscrito.
- Use **apenas** em ativos que você possui ou tem autorização formal para testar.
- O `scope engine` bloqueia o que **não** está declarado — o que está declarado,
  ele **presume autorizado**. A responsabilidade é sua.

O autor do Aegis não se responsabiliza por uso indevido.

---

## O que é

Aegis é um **agente autônomo de reconhecimento** orientado a evidências.
Ele não é "um script que roda nmap". Ele:

- valida escopo antes de qualquer coisa;
- enumera subdomínios, resolve DNS e faz HTTP probing;
- descobre APIs (Swagger, OpenAPI, GraphQL, REST) por path guessing;
- extrai parâmetros de query strings e formulários HTML;
- persiste tudo em banco relacional com histórico;
- expõe consultas prontas via CLI.

Ferramentas são **sensores**. O Aegis é o **cérebro** que decide o que rodar,
contra o quê, e o que fazer com o resultado.

---

## Arquitetura
