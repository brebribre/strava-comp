# Backend — Strava Group Tracker

FastAPI + SQLModel + Postgres.

## Layout

```
app/
  main.py        composition root: creates the FastAPI app, middleware, mounts the router
  config.py      settings loaded from .env

  api/           HTTP layer — the only layer that knows about FastAPI
    router.py      aggregates every route module
    deps.py        shared dependencies (get_db; later get_current_athlete, require_group_member)
    routes/        one module per resource: health.py, later auth.py, groups.py, webhooks.py

  services/      business logic — takes a Session + plain args, returns plain data
                 raises domain errors; routes translate them to HTTP

  infra/         outbound connections
    db.py          engine, session, table creation
    strava.py      Strava API client (OAuth, activities, webhooks)

  models/        SQLModel tables (the DB schema)
  schemas/       Pydantic request/response shapes exposed by the API
```

**Dependency direction:** `api → services → infra`. Nothing in `services/` or `infra/`
imports FastAPI, and `infra/` never imports `services/`. `models/` and `schemas/` are
leaf modules both upper layers may read.

Adding an endpoint:
1. shape in `schemas/`, 2. logic in `services/`, 3. thin route in `api/routes/`,
4. register it in `api/router.py`.

## Running locally

Postgres (from the repo root):

```bash
docker compose up -d
```

Install and run:

```bash
cd backend && uv venv && uv pip install -r requirements.txt
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs — `/` redirects there. `/health` returns 200 only
if a `SELECT 1` against Postgres succeeds.
