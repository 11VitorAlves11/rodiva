<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/icons/symbol-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="frontend/public/icons/symbol-light.svg" />
    <img src="frontend/public/icons/symbol-light.svg" width="140" height="140" alt="Rodiva logo: a wheel shaped as a road" />
  </picture>
</p>

<h1 align="center">Rodiva</h1>
<p align="center"><strong>Your vehicles' whole life, in one place.</strong></p>
<p align="center">
  Fuel, costs and maintenance for the whole household.<br />
  On your computer, on your phone, and on your own server.
</p>

<p align="center">
  <a href="https://github.com/11VitorAlves11/rodiva/releases"><img src="https://img.shields.io/github/v/release/11VitorAlves11/rodiva?style=flat-square&color=B94A22&label=release" alt="Latest release" /></a>
  <a href="https://github.com/11VitorAlves11/rodiva/actions/workflows/ci.yml"><img src="https://github.com/11VitorAlves11/rodiva/actions/workflows/ci.yml/badge.svg" alt="CI status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-171C20?style=flat-square" alt="AGPL-3.0-or-later licence" /></a>
  <img src="https://img.shields.io/badge/web-PWA-B94A22?style=flat-square" alt="Website and installable PWA" />
</p>

<p align="center">
  <a href="#the-interface">See the interface</a> ·
  <a href="#features">Features</a> ·
  <a href="#try-it-locally">Install</a> ·
  <a href="https://github.com/11VitorAlves11/rodiva/releases">Releases</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href="docs/images/desktop-dashboard.png"><img src="docs/images/desktop-dashboard.png" width="1100" alt="Rodiva dashboard on a computer, showing vehicles, average consumption, recent history, monthly spending and upcoming reminders" /></a>
</p>

## What is Rodiva?

Rodiva is an open source application for managing a household's vehicles. It tells you what
each vehicle costs, tracks consumption between fill-ups, and keeps services, insurance and
inspections in order, with a history the whole family shares.

It works as a website on a computer and as an **installable PWA on iPhone and Android**.
Accounts and data are the same on every device. The application is self-hosted: the database
and the documents stay on whatever infrastructure you install it on.

## The interface

Get to know the application without installing anything. The images below are **real
screenshots of the interface with fictional demonstration data**, in European Portuguese —
the default language, alongside English, French and Spanish. Click an image to open it full
size.

### On a phone

The garage dashboard, the history and a new fill-up, with navigation always within reach in
the bottom bar. The **+** button opens a fuel entry and lets you pick the vehicle.

<table>
  <tr>
    <th align="center">Your garage</th>
    <th align="center">History and spending</th>
    <th align="center">Recording a fill-up</th>
  </tr>
  <tr>
    <td width="33%" align="center"><a href="docs/images/mobile-dashboard.png"><img src="docs/images/mobile-dashboard.png" width="280" alt="Rodiva at iPhone size: garage dashboard with odometer, consumption and spending" /></a></td>
    <td width="33%" align="center"><a href="docs/images/mobile-history.png"><img src="docs/images/mobile-history.png" width="280" alt="Rodiva at iPhone size: history of fill-ups, maintenance and expenses" /></a></td>
    <td width="33%" align="center"><a href="docs/images/mobile-fuel.png"><img src="docs/images/mobile-fuel.png" width="280" alt="Rodiva at iPhone size: fuel form with date, odometer, litres and price" /></a></td>
  </tr>
</table>

*Captured at an iPhone 13 viewport (390 × 844) in a browser with mobile emulation.
Installing it as a PWA gives the same interface.*

### On a computer

More room to read costs, compare vehicles and follow the history.

<p align="center">
  <a href="docs/images/desktop-reports.png"><img src="docs/images/desktop-reports.png" width="1100" alt="Rodiva reports on a computer, with costs, distance, consumption and a monthly breakdown" /></a>
</p>

<details>
  <summary><strong>See the dark theme</strong></summary>
  <p>The application follows a light theme, a dark one, or whatever the device prefers.</p>
  <p align="center"><a href="docs/images/desktop-dark.png"><img src="docs/images/desktop-dark.png" width="1100" alt="Rodiva's main dashboard in the dark theme" /></a></p>
</details>

## Features

| | What you can do |
|---|---|
| **Shared garage** | Manage several vehicles, photos, purchase and sale details, household members and permissions. |
| **Consumption and distance** | Record fill-ups, electric charges and odometer readings; follow consumption and efficiency. |
| **Costs and maintenance** | Keep work records, parts, expenses, insurance, taxes, documents and notes. |
| **Planning** | Set reminders by date or distance, plan work and read the calendar. |
| **Equipment and inventory** | Track tyres, accessories, consumables and stock movements; build inspection checklists. |
| **Search and reports** | Filter the history, use tags, read costs and export reports; import records from CSV. |
| **Integrations** | Connect Google Calendar, API keys, webhooks, OIDC and Web Push notifications, once configured. |
| **Preferences** | Choose Portuguese, English, French or Spanish, and a theme per device. |

**Project status:** under active development. Some features are still growing; OIDC and Web
Push need configuration and validation in the environment they are used in. The
[releases](https://github.com/11VitorAlves11/rodiva/releases) track what changed.

## Try it locally

Needs Git, Docker and Docker Compose. To bring up the development environment:

```bash
git clone https://github.com/11VitorAlves11/rodiva.git
cd rodiva
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

Open **[http://localhost:5173](http://localhost:5173)** and create your account and your
household. The API applies its migrations on startup.

API: <http://localhost:8000/api> · Interactive documentation: <http://localhost:8000/docs>

### On your own server

[`docker-compose.yml`](docker-compose.yml) ships PostgreSQL, the API and the frontend behind
nginx. Set `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env`, terminate HTTPS at your reverse
proxy, and run:

```bash
docker compose up --build -d
```

The frontend listens on port `8080` by default (`WEB_PORT`). In production the session
cookies require HTTPS. `ALLOW_PUBLIC_REGISTRATION` controls whether new accounts can sign
themselves up.

The notes on [authentication, backups, restores and security](docs/OPERATIONS.md) go with the
settings in [`.env.example`](.env.example).

### Installing it on a home screen

Once your instance is reachable over HTTPS:

- **iPhone:** in Safari, open the share menu and choose **Add to Home Screen**.
- **Android:** in a supporting browser, use **Install app** or **Add to Home screen**.

## Development and documentation

<details>
  <summary><strong>Running without Docker</strong></summary>

Needs a running PostgreSQL, Python 3.12+ and Node.js 22+. Point `DATABASE_URL` at your
database and give `STORAGE_PATH` a writable directory.

```bash
# API terminal
cd backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
export DATABASE_URL=postgresql+asyncpg://rodiva:password@localhost:5432/rodiva
export STORAGE_PATH=/tmp/rodiva-storage
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend terminal, from the repository root
cd frontend
npm install
npm run dev
```

</details>

**FastAPI · SQLAlchemy · Alembic · PostgreSQL · React · TypeScript · Vite · Tailwind CSS**

| Path | Contents |
|---|---|
| [`backend/`](backend/) | API, migrations and pytest suite |
| [`frontend/`](frontend/) | Responsive interface, PWA and Vitest/Playwright suites |
| [`scripts/`](scripts/) | Backup and restore |
| [`docs/`](docs/) | Operations and application imagery |

- [Setting up and running the tests](CONTRIBUTING.md)
- [Operations, authentication and backups](docs/OPERATIONS.md)
- [How to refresh the README screenshots](docs/SCREENSHOTS.md)
- [Report a problem or suggest an improvement](https://github.com/11VitorAlves11/rodiva/issues)

Rodiva takes the public feature set of [LubeLogger](https://docs.lubelogger.com/) as its
functional reference, with its own implementation and its own visual identity.

## Licence

[AGPL-3.0-or-later](LICENSE).
