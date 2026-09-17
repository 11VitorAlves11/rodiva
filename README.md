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

## Cópias de segurança

A aplicação guarda o histórico em dois sítios: a base de dados e o volume de
armazenamento com os ficheiros carregados. É preciso salvaguardar os dois — a base
de dados sabe que anexos existem, o volume tem os bytes, e cada um sozinho repõe
uma instalação que lista documentos que não abre, ou que guarda ficheiros que
ninguém referencia.

```bash
./scripts/backup.sh                      # escreve em ./backups, mantém as 14 mais recentes
./scripts/backup.sh /destino 30          # destino e retenção próprios
./scripts/restore.sh backups/rodiva-…    # repõe; pede confirmação escrita
```

Cada cópia é uma pasta com `database.sql.gz`, `storage.tar.gz` e um `manifest.txt`
com a data e a versão. Correr a partir da pasta do `docker-compose.yml`, com a
stack a funcionar. Para uma cópia diária, agendar o `backup.sh` no cron do
anfitrião e guardar o destino fora da máquina.

A reposição substitui o estado por inteiro: esvazia o esquema antes de reproduzir
o dump, para que repor uma cópia antiga numa instância já migrada não deixe
tabelas órfãs das migrações posteriores.

Reponha uma cópia de vez em quando para um ambiente de teste: uma salvaguarda que
nunca foi reposta é uma suposição, não um backup.

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
