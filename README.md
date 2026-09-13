# Rodiva

Gestão pessoal e familiar de veículos: histórico, custos, manutenção e obrigações de todos
os veículos de um agregado, numa única aplicação web responsiva — website completo no
computador e PWA instalável no iPhone, com o mesmo backend, contas e dados em todos os
dispositivos.

Cobertura funcional equivalente às funcionalidades públicas do [LubeLogger](https://docs.lubelogger.com/),
sem reproduzir o respetivo código ou desenho visual.

> **Estado:** fundação inicial. Autenticação local, agregados, garagem (veículos),
> quilometragem e abastecimentos estão implementados end to end; os restantes módulos descritos em
> `PRD/Especificacao_Funcional_Rodiva.md` seguem o plano de implementação da secção 30
> desse documento.

## Stack

FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · React 18 · Vite · TypeScript ·
Tailwind CSS v4 · Docker Compose.

## Arranque rápido (desenvolvimento)

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

Web: <http://localhost:5173> · API: <http://localhost:8000/api> · Docs: <http://localhost:8000/docs>

A API aplica as migrações no arranque, pelo que o primeiro `docker compose up` já sobe com o
esquema de base de dados atualizado.

## Sem Docker

```bash
# backend
cd backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## Estrutura do repositório

| Caminho | Conteúdo |
|---|---|
| `backend/` | Aplicação FastAPI, migrações Alembic, testes pytest |
| `frontend/` | Aplicação React + Vite, PWA, testes vitest |
| `PRD/` | Especificação funcional e técnica de referência |

## Testes e lint

```bash
cd backend  && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/pytest
cd frontend && npm run lint && npm test && npm run build
```

## Autenticação

A primeira versão usa apenas contas locais (correio eletrónico + palavra-passe), com sessão
por cookie assinado, `httponly` e `secure` fora de desenvolvimento. OpenID Connect está
planeado para a fase de paridade (ver secção 4 do documento de especificação).

## Licença

[AGPL-3.0-or-later](LICENSE).
