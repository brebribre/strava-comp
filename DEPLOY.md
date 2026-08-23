# Deploying the backend to Railway

Railway builds from GitHub, so everything here starts with your code pushed to
`brebribre/strava-comp`. The repo is already prepared for it:

| File | Why it matters |
|---|---|
| `backend/railway.json` | Start command (`--host 0.0.0.0 --port $PORT`), health check on `/health` |
| `backend/.python-version` | Pins Python 3.12 so Nixpacks doesn't pick something older |
| `backend/requirements.txt` | What Nixpacks installs |
| `app/config.py` | Rewrites Railway's `postgresql://` into the `postgresql+psycopg://` form SQLAlchemy needs |

---

## Two Strava limits to know before you start

**1. One API application per Strava account.** You cannot have separate dev and prod
apps on the same account, and there is only *one* "Authorization Callback Domain" field.
Pointing it at your Railway domain means local OAuth stops working, and vice versa.
It is a five-second edit, so switch it when you switch environments — or make a second
Strava account if you want both live at once.

**2. New apps may connect only ONE athlete by default.** Strava raises this to 999 after
a review request. Until then your brothers will hit
`403 Limit of connected athletes exceeded` when they try to log in. Request the increase
early — it isn't instant. See the FAQ link at the bottom.

---

## Step 1 — Push to GitHub

```bash
git add -A && git commit -m "backend: phases 1-6" && git push
```

## Step 2 — Create the Railway project

Dashboard route (easiest the first time):

1. [railway.com/new](https://railway.com/new) → **Deploy from GitHub repo** → pick `strava-comp`
2. Railway will try to build from the repo root and fail — that's expected, fix it in step 3.

CLI route, if you prefer:

```bash
brew install railway
```

```bash
railway login && railway init
```

## Step 3 — Point the service at `backend/`

This is the step people miss on a monorepo. In the service → **Settings** → **Source**:

- **Root Directory**: `backend`
- **Config file path**: `backend/railway.json` (Railway wants this path from the repo root,
  *not* relative to the root directory you just set)

Then redeploy. Nixpacks will detect `requirements.txt` and install with pip.

## Step 4 — Add Postgres

1. In the project canvas: **New** → **Database** → **PostgreSQL**
2. Open your **backend** service → **Variables** → **New Variable**:

   ```
   DATABASE_URL = ${{Postgres.DATABASE_URL}}
   ```

   That `${{...}}` is a Railway variable reference — it stays correct if the database is
   ever recreated. Use the private/internal URL Railway offers; traffic stays inside the
   project and doesn't count as egress.

Tables are created automatically on boot by `create_db_and_tables()` in the app lifespan.
(That's fine now; a real Alembic migration is worth adding before there's data you care about.)

## Step 5 — Set the remaining variables

In the backend service → **Variables** → **Raw Editor**:

```
STRAVA_CLIENT_ID=<from strava.com/settings/api>
STRAVA_CLIENT_SECRET=<from strava.com/settings/api>
STRAVA_REDIRECT_URI=https://<your-service>.up.railway.app/auth/strava/callback
STRAVA_VERIFY_TOKEN=<any random string you invent, needed in Phase 7>
SECRET_KEY=<a NEW random value — do not reuse the local one>
COOKIE_SECURE=true
BACKFILL_DAYS=7
FRONTEND_ORIGIN=https://<your-frontend-domain>
```

Generate a fresh `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Notes:
- `SECRET_KEY` signs session cookies. Reusing your local one means a cookie minted on your
  laptop is valid in production. Use a different value.
- Leave `COOKIE_SAMESITE` alone for now. Set it to `none` only once the frontend lives on a
  *different* domain than the API — browsers require `Secure=true` alongside it, which you
  already have in production.
- `EXTRA_CORS_ORIGINS` takes a comma-separated list if you need to allow more than one origin.

## Step 6 — Get a public URL

Service → **Settings** → **Networking** → **Generate Domain**. Pick the port Railway
suggests. You'll get `https://<something>.up.railway.app`.

Now go back and make `STRAVA_REDIRECT_URI` (step 5) match that domain exactly.

## Step 7 — Point Strava at it

[strava.com/settings/api](https://www.strava.com/settings/api) → **Authorization Callback
Domain** → `<something>.up.railway.app` (bare host — no `https://`, no path).

Remember: this breaks local login until you set it back to `localhost`.

## Step 8 — Verify

```bash
curl -s https://<your-domain>/health
```

Expect `{"status":"ok","database":"ok"}` — a 200 here proves the app booted *and* reached
Postgres. Then open `https://<your-domain>/docs`, and log in once via
`https://<your-domain>/auth/strava/login` to confirm OAuth works against the new domain.

Watch the deploy logs in the Railway dashboard while you do it — the backfill runs in the
background after login and logs how many activities it stored.

---

## Then: Phase 7 webhooks

With a public HTTPS URL, register the subscription once:

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=<id> -F client_secret=<secret> \
  -F callback_url=https://<your-domain>/strava/webhook \
  -F verify_token=<the STRAVA_VERIFY_TOKEN you set>
```

Strava immediately calls `GET /strava/webhook` on your service to verify, so the app must
already be deployed and healthy when you run this.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Build succeeds, deploy crashes instantly | Root Directory not set to `backend` |
| `ModuleNotFoundError: psycopg2` | `DATABASE_URL` didn't go through `config.py`'s rewrite — check the variable is set on the *backend* service |
| Health check fails, logs show connection refused | Start command not binding `0.0.0.0`/`$PORT` — confirm `railway.json` is being read |
| `redirect_uri` mismatch at Strava | `STRAVA_REDIRECT_URI` and the callback domain disagree, or one has a trailing slash |
| `403 Application Status Inactive` | The app owner's Strava subscription lapsed |
| `403 Limit of connected athletes exceeded` | The default 1-athlete cap — request an increase from Strava |

Sources: [Railway monorepo docs](https://docs.railway.com/guides/monorepo),
[Strava API FAQ](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906)
