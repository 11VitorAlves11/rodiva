# Rodiva

Gestão pessoal e familiar de veículos: histórico, custos, manutenção e obrigações de todos
os veículos de um agregado, numa única aplicação web responsiva — website completo no
computador e PWA instalável no iPhone, com o mesmo backend, contas e dados em todos os
dispositivos.

Cobertura funcional equivalente às funcionalidades públicas do [LubeLogger](https://docs.lubelogger.com/),
sem reproduzir o respetivo código ou desenho visual.

> **Estado:** em desenvolvimento. Inclui contas e agregados, garagem, histórico,
> abastecimentos e carregamentos elétricos, intervenções, despesas, documentos,
> lembretes, planeamento, inventário, equipamento, inspeções, pesquisa, relatórios
> e importação CSV dos registos principais. A cobertura funcional integral ainda está
> por concluir.

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

## Testes e lint

```bash
cd backend  && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/pytest
cd frontend && npm run lint && npm test && npm run build
```

## Autenticação

As contas locais usam palavra-passe com hashing e cookies de sessão assinados,
`httponly` e `secure` em produção. As sessões são guardadas no servidor e podem
ser revogadas individualmente ou todas de uma vez nas definições.

A recuperação de palavra-passe está disponível quando SMTP estiver configurado
(ver `.env.example`). A alteração ou recuperação da palavra-passe revoga outras
sessões. OIDC continua por implementar.

Os recursos estão documentados em `/api/v1`; os endereços `/api` anteriores mantêm
compatibilidade. A autenticação continua em `/auth`.

## Segurança

A API responde com `Content-Security-Policy`, `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy` e `Cross-Origin-Opener-Policy` em todas as
respostas, incluindo transferências de anexos; o nginx que serve a aplicação
aplica a política equivalente aos ficheiros estáticos. Com `ENVIRONMENT=prod`
acresce `Strict-Transport-Security`.

`ALLOWED_HOSTS` restringe os nomes de anfitrião aceites. Fica aberto por omissão,
porque uma instalação auto-hospedada não consegue adivinhar o seu próprio nome;
uma instância acessível a partir da internet deve indicá-lo.

## Licença

[AGPL-3.0-or-later](LICENSE).
