# Interface screenshots

[← Back to the README](../README.md)

The images in `docs/images/` are captures of the running application, with fictional data
created through the API. The logo is the same SVG the interface uses, from
`frontend/public/icons/`. They are neither mockups nor photographs of a physical iPhone.

The gallery runs the interface in English: the script sets the demonstration account's
language to `en` after registering it.

`frontend/scripts/demo-vehicle.jpg` is the vehicle photograph the script uploads. It comes
from [Volvo V60 (48566713551).jpg](https://commons.wikimedia.org/wiki/File:Volvo_V60_(48566713551).jpg)
on Wikimedia Commons, released under **CC0** — no attribution is required, and the credit
here is courtesy. It was cropped to the car and its number plate was pixelated, since the
interface shows a fictional plate and the original belongs to someone.

## Recreating the gallery

Use a local, disposable database. The script creates a fresh account and household on every
run, two vehicles and six months of demonstration records. The dates are relative to the
month of the capture. Do not run it against an installation holding real data.

From the repository root, start a database of its own:

```bash
docker run --rm -d --name rodiva-readme-db \
  -e POSTGRES_USER=rodiva -e POSTGRES_PASSWORD=rodiva \
  -e POSTGRES_DB=rodiva_demo \
  -p 127.0.0.1:55440:5432 postgres:16-alpine
```

Wait until `docker exec rodiva-readme-db pg_isready -U rodiva` reports it ready. In a
terminal for the API, once the backend dependencies are installed:

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://rodiva:rodiva@127.0.0.1:55440/rodiva_demo
export ENVIRONMENT=dev SECRET_KEY=readme-demo-local-only
export STORAGE_PATH=/tmp/rodiva-readme-storage
export ALLOW_PUBLIC_REGISTRATION=true
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18001
```

In a second terminal:

```bash
cd frontend
npm ci
npm run build
VITE_API_PROXY_TARGET=http://127.0.0.1:18001 npm run preview -- --host 127.0.0.1 --port 15173
```

In a third:

```bash
cd frontend
npx playwright install --with-deps chromium
node scripts/readme-screenshots.mjs
```

`SCREENSHOT_BASE_URL` picks another local address. The script refuses remote hosts. It needs
access to Google Fonts to use the typography the application loads.

It launches the browser with `LANG=en_GB.UTF-8`, because Chromium renders
`<input type="date">` in its own UI language rather than the page's: without it every form
in the gallery would read `mm/dd/yyyy` instead of `dd/mm/yyyy`.

## The images produced

| File | Contents | Viewport |
|---|---|---|
| `desktop-dashboard.png` | Main dashboard, light theme | 1440 × 1000 |
| `desktop-reports.png` | Reports | 1440 × 1000 |
| `desktop-dark.png` | Main dashboard, dark theme | 1440 × 1000 |
| `mobile-dashboard.png` | Main dashboard | 390 × 844 |
| `mobile-history.png` | History, scrolled to the records | 390 × 844 |
| `mobile-fuel.png` | Fuel form | 390 × 844 |

The mobile captures use Chromium with the iPhone 13 emulation profile at 2× scale, producing
780 × 1688 pixel images. The script waits for the data and the fonts, and checks that no page
is wider than its viewport — that guard is what caught a hidden file input stretching the
vehicle page and pushing the bottom navigation off screen. The themes and the navigation are
the application's own; no CSS is changed for the photographs.

After a run, open all six images and check the text, the data, the forms and the navigation
bar. The README links straight to the PNGs so they can be enlarged on GitHub.

Stop the API and the frontend with `Ctrl+C` and remove the temporary database:

```bash
docker stop rodiva-readme-db
```

The container was created with `--rm`; the demonstration data disappears when it stops.
