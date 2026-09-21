# Contribuir para a Rodiva

Projeto pessoal, self-hosted. Este documento descreve como preparar o ambiente e correr os
testes localmente.

## Ambiente

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

Sem Docker, ver "Running without Docker" no [`README.md`](README.md).

## Convenções

- Commits em inglês, imperativo, [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:` `fix:` `docs:` `refactor:` `test:` `chore:`.
- Textos de interface e documentação funcional em português de Portugal (PT-PT).
- Código, comentários e nomes de variáveis em inglês.
- Nunca commitar sem lint e testes a passar.

## Backend

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
export DATABASE_URL="postgresql+asyncpg://rodiva:rodiva@localhost:5432/rodiva_test" \
  ENVIRONMENT=test AUTH_MODE=local SECRET_KEY=test-secret
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app
.venv/bin/alembic upgrade head
.venv/bin/pytest
```

Uma nova tabela ou coluna exige uma migração Alembic:

```bash
.venv/bin/alembic revision --autogenerate -m "descrição da alteração"
```

## Frontend

```bash
cd frontend
npm install
npm run lint
npm test
npm run build
```

## Modelo de dados

Regras gerais (ver secção 23 da especificação):

- Identificadores UUID, datas em UTC.
- Valores monetários e quantidades usam `Numeric`, nunca `float`.
- Todas as tabelas de negócio ligadas a um agregado incluem `household_id` e são filtradas
  no servidor — nunca apenas na interface.
- Eliminação recuperável: `deleted_at` / `deleted_by` em vez de remover a linha.
