# picopals 🥚

A Tamagotchi-style virtual pet as an installable **PWA**. An egg hatches after
**one minute** into one of four friends — a **dog**, **cat**, **frog**, or
**rabbit** — which you raise with three buttons, just like the real toy. Scales
from phone to desktop.

```
┌────────────┐      ┌─────────┐   ┌─────────┐   ┌─────────┐
│  Frontend  │      │ Backend │   │  MySQL  │   │  Redis  │
│  Vite/JS   │      │ FastAPI │──▶│ durable │   │  live   │
│  (nginx)   │      │         │──▶│  saves  │   │  state  │
└─────▲──────┘      └────▲────┘   └─────────┘   └─────────┘
      │  static          │ /api/*
      └──────────┬───────┘
            ┌────┴────┐
            │  Caddy  │  reverse proxy / single entrypoint  :8080
            └─────────┘
```

- **Frontend** — Vite + vanilla JS, canvas pixel-art LCD, three-button menu,
  hamburger drawer (settings / about / reset), PWA (manifest + service worker),
  fully responsive.
- **Backend** — FastAPI. **Redis** holds each pet's *live* condition (lazily
  fast-forwarded by elapsed time on every read). **MySQL** holds the durable
  save (user id + recovery code + pet snapshot).
- **Caddy** — the only exposed port; serves the static frontend and proxies
  `/api/*` to FastAPI, so the browser is same-origin (no CORS in prod).
- Everything is **Dockerised** and wired in `docker-compose.yml`.

## Quick start (Docker)

> Requires Docker Desktop. Nothing else needs to be installed.

```bash
cp .env.example .env        # then edit the passwords
docker compose up --build
```

Open **http://localhost:8080**. The egg hatches a minute after your first
visit.

## Local development — containerised (recommended)

No Node/Python needed on the host — just Docker. This runs the **Vite dev
server in a Node container** with hot-module reload, alongside the same MySQL,
Redis, and a `--reload` FastAPI:

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

- App with HMR: **http://localhost:5173** (edit files under `frontend/` and the
  browser reloads)
- API + Swagger docs: **http://localhost:8000/api/docs**
- MySQL and Redis are published on `localhost:3306` / `localhost:6379` too.

There's no Caddy/nginx in dev — Vite serves the app and proxies `/api` straight
to the backend container.

## Local development (without Docker)

You'll need **Node 20+** and **Python 3.12+**.

```bash
# --- backend (needs MySQL + Redis running; the easiest is the two containers) ---
docker compose up -d mysql redis
cd backend
python -m venv .venv && . .venv/Scripts/activate   # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# point at the containers exposed on localhost (see note below) or use sqlite
set DATABASE_URL=mysql+pymysql://tama:tama_change_me@localhost:3306/picopals
set REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload --port 8000

# --- frontend ---
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api -> http://localhost:8000
```

> The compose file doesn't publish MySQL/Redis ports by default. For local
> backend dev, either add `ports:` to those services or run the whole stack in
> Docker and develop only the frontend against it.

## How to play

The device has three buttons (also bindable on keyboard):

| Button | Keyboard | Does |
|--------|----------|------|
| **A** | `A` / `←` | move the cursor between icons |
| **B** | `B` / `Space` / `Enter` | select / confirm |
| **C** | `C` / `→` / `Esc` | cancel / back |

Icons: **Meal** & **Snack** (feed), **Play**, **Clean** (poop), **Med** (cure
sickness), **Light** (sleep), **Scold** (discipline), **Stats** (status screen).

Hunger and happiness drain over time; neglect causes sickness; poop piles up and
must be cleaned. Turning the light off slows everything down while your pet
sleeps.

### Egg hatching timeline

| Time | Behaviour |
|------|-----------|
| 0–10s | egg sits still |
| 10–20s | egg rumbles |
| 20–30s | egg rumbles and cracks |
| 30s | hatches into a random species |

## No login, but recoverable

On first visit the backend mints a **unique user id** (stored in `localStorage`)
plus a friendly **recovery code** like `WARM-FROG-7Q2K`. The pet lives on the
server keyed by that id.

If cookies/storage are cleared or you switch device or IP, open the **hamburger
→ Settings → Recover a pet** and enter your saved recovery code to restore the
exact pet from MySQL. Your recovery code is always shown in Settings — write it
down.

## API

All routes are under `/api` (same-origin via Caddy). Interactive docs at
`/api/docs` (FastAPI/Swagger) when the backend is reachable directly.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/users` | mint a user + recovery code + lay an egg |
| `GET` | `/api/users/{id}` | fetch user + current pet |
| `POST` | `/api/users/recover` | restore by `recovery_code` |
| `GET` | `/api/pets/{id}` | poll the live pet condition |
| `POST` | `/api/pets/{id}/hatch` | hatch a ready egg |
| `POST` | `/api/pets/{id}/action` | `feed_meal`,`feed_snack`,`play`,`clean`,`medicine`,`discipline`,`toggle_light` |
| `POST` | `/api/pets/{id}/name` | name the pet |
| `POST` | `/api/pets/{id}/reset` | lay a fresh egg (keeps the user) |
| `GET` | `/api/health` | liveness + Redis/MySQL status |

## Tests

Unit tests for the API and the pure pet-simulation logic live in
[`tests/`](tests/) with a beginner-friendly guide — see
[`tests/README.md`](tests/README.md).

```bash
cd tests
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

They use SQLite + an in-memory Redis fake, so **no MySQL/Redis is needed** to
run them.

## Project layout

```
picopals/
├── docker-compose.yml      # mysql, redis, backend, frontend, caddy
├── Caddyfile               # reverse proxy
├── .env.example
├── backend/                # FastAPI + SQLAlchemy + redis
│   ├── app/
│   │   ├── main.py         # app + /api/health
│   │   ├── pet_logic.py    # pure simulation (decay, hatch, actions)
│   │   ├── crud.py         # Redis<->MySQL coordination
│   │   ├── routers/        # users.py, pets.py
│   │   └── ...
│   ├── init.sql            # MySQL schema
│   └── Dockerfile
├── frontend/               # Vite + vanilla JS PWA
│   ├── src/
│   │   ├── game.js         # controller: bootstrap, polling, 3-button state machine
│   │   ├── render.js       # canvas LCD renderer
│   │   ├── sprites.js      # pixel-art egg + 4 creatures
│   │   └── ...
│   ├── public/             # manifest, service worker, icon
│   ├── nginx.conf
│   └── Dockerfile
└── tests/                  # pytest suite + guide
```

## Notes & next steps

- PWA icons are provided as a single scalable SVG. For the widest install
  support you may want to add rasterised `192×192` and `512×512` PNGs and list
  them in `manifest.webmanifest`.
- The simulation is intentionally friendly (no permadeath) given the brief.
  Tuning lives at the top of `backend/app/pet_logic.py`.
