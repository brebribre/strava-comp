# Strava Group Tracker — Development Step-by-Step

Concrete, ordered build steps. Each phase should be working and testable before moving to the next.

---

## Phase 0: Prerequisites ✅ DONE

- [x] Create a Strava app at [strava.com/settings/api](https://www.strava.com/settings/api) → get `Client ID` + `Client Secret`
- [x] Create a Railway account
- [x] Install locally: Python 3.11+, Node.js, `uv` or `pip`, Postgres (local Docker, or point at Railway's dev DB)
- [x] Create a GitHub repo with two folders: `/backend` (FastAPI) and `/frontend` (Vue)

---

## Phase 1: Backend Skeleton + Local DB Connection ✅ DONE

**Goal:** FastAPI app runs, connects to Postgres, has one working endpoint.

1. Scaffold FastAPI project — built with a layered structure rather than flat modules
   (`api → services → infra`); see [backend/README.md](backend/README.md):
   ```
   backend/
     app/
       main.py            app factory, middleware, router mount
       config.py
       api/               endpoints: router.py, deps.py, routes/
       services/          business logic
       infra/             db.py (engine/session) + strava.py (third-party client)
       models/            SQLModel tables
       schemas/           Pydantic request/response shapes
     requirements.txt
   ```
2. Install deps: `fastapi`, `uvicorn`, `sqlmodel`, `httpx`, `python-dotenv`, `itsdangerous`,
   `pydantic-settings`, `psycopg[binary]` (psycopg3 — note the `postgresql+psycopg://` URL scheme)
3. Set up `.env` locally with `DATABASE_URL` — Postgres runs via `docker-compose.yml` on host port **5433**
4. Write `infra/db.py`: SQLModel engine + session dependency
5. Write a throwaway `/health` endpoint that queries the DB (`SELECT 1`)
6. Run locally: `uvicorn app.main:app --reload` → hit `/health` → confirm 200 OK
7. Swagger UI at `/docs`, ReDoc at `/redoc`, raw schema at `/openapi.json`; `/` redirects to `/docs`

✅ **Checkpoint:** Backend runs locally and talks to Postgres. *(verified: `/health` → 200 with DB up, 500 with DB stopped)*

---

## Phase 2: Database Schema (Athletes, Activities, Groups) ✅ DONE

Notes from the build: Strava-supplied IDs (`athletes.athlete_id`, `activities.id`) are
`BIGINT` with `autoincrement=False` — activity IDs already exceed int32 and we always
supply them ourselves. All timestamps are `TIMESTAMPTZ`. `groups.created_by` is
`ON DELETE SET NULL` so a group outlives its creator; everything else cascades.

1. Define models in `app/models/` (SQLModel), one module per table:
   - `Athlete` (athlete_id, name, access_token, refresh_token, token_expires_at)
   - `Activity` (id, owner_id FK, sport_type, distance, moving_time, elapsed_time, elevation, avg_hr, start_date, raw_data JSONB)
   - `Group` (id, name, invite_code, created_by FK, created_at)
   - `GroupMembership` (group_id FK, athlete_id FK, joined_at) — composite primary key `(group_id, athlete_id)`
2. Add a startup hook or Alembic migration to create all four tables
   — done via `create_db_and_tables()` in the FastAPI lifespan; Alembic still to come
3. Manually insert fake rows (one athlete, one group, one membership), query them back, confirm relationships work
   — automated as `backend/scripts/check_schema_roundtrip.py`:
   ```bash
   cd backend && .venv/bin/python -m scripts.check_schema_roundtrip
   ```

✅ **Checkpoint:** Full schema exists, including groups, and round-trips correctly.
*(verified: JSONB round-trip, tz-aware timestamps, group join, unique invite_code, cascade + SET NULL deletes)*

---

## Phase 3: Strava OAuth (Login) Flow ✅ DONE

**Goal:** Clicking "Connect with Strava" logs a user in and stores their tokens.

Built beyond the plan: a signed `state` nonce (CSRF), a scope check that rejects a grant
without `activity:read_all`, `POST /auth/logout`, and error redirects back to the frontend
with an `?error=` param instead of raw 500s. **Before the manual test**, set the Strava app's
*Authorization Callback Domain* to `localhost`.

1. Build the authorize redirect endpoint:
   ```
   GET /auth/strava/login
   → redirects to https://www.strava.com/oauth/authorize?client_id=...&redirect_uri=...&response_type=code&scope=activity:read_all
   ```
2. Build the callback endpoint:
   ```
   GET /auth/strava/callback?code=...
   → exchange code for tokens via POST https://www.strava.com/oauth/token
   → upsert Athlete row (athlete_id, tokens, expiry)
   → sign a session cookie (itsdangerous), set it, redirect to frontend
   ```
3. Build `get_current_athlete` dependency that reads/validates the session cookie
4. Build a protected test endpoint `GET /me` returning the logged-in athlete's ID
5. **Test manually**: visit http://localhost:8000/auth/strava/login, log in with your own
   Strava account, confirm `/me` works and a row appears in `athletes`
   — everything *except* the consent screen is covered by `backend/scripts/check_auth_flow.py`
   (Strava's token endpoint stubbed):
   ```bash
   cd backend && .venv/bin/python -m scripts.check_auth_flow
   ```

✅ **Checkpoint:** You can log in via Strava and get a working session.
*(automated: authorize redirect, CSRF state, scope enforcement, upsert, cookie, /me, logout.
Manual: real login confirmed — athlete row written with both tokens, `/me` returned it)*

---

## Phase 4: Token Refresh Logic

1. Write `get_valid_access_token(athlete_id)`:
   - reads athlete from DB
   - if `token_expires_at` is past, calls Strava's refresh endpoint, updates DB, returns new token
   - else returns the stored token
2. Test: manually expire a token's timestamp in the DB, confirm it auto-refreshes on next use

✅ **Checkpoint:** Token refresh works without manual intervention.

---

## Phase 5: Groups — Create, Join, List

**Goal:** Athletes can form and join groups before any activity data is shown.

1. `POST /groups` — creates a group for the current athlete:
   - generate a random `invite_code` (e.g. `secrets.token_urlsafe(6)`)
   - insert into `groups`, then insert a `group_memberships` row for the creator
   - return `{ group_id, invite_code }`
2. `POST /groups/join` — body: `{ invite_code }`:
   - look up group by code, 404 if not found
   - insert `group_memberships` row for current athlete (ignore if already a member)
3. `GET /groups` — list all groups the current athlete belongs to
4. `GET /groups/{group_id}/members` — list athletes in a group (name + athlete_id)
5. Build a `require_group_member(group_id)` dependency — 403s if current athlete isn't in `group_memberships` for that group; use it on every group-scoped endpoint from here on
6. **Test**: create a group with your account, note the invite code, join it with a second test Strava account, confirm both show up in `/groups/{id}/members`

✅ **Checkpoint:** Groups can be created and joined; membership is enforced.

---

## Phase 6: Manual Activity Fetch + Historical Backfill

**Goal:** Pull and store an athlete's past activities.

1. Write `fetch_activities(athlete_id, after_timestamp)`:
   - calls `GET /athlete/activities?after=...&page=N&per_page=200` in a loop until an empty page
2. Write `save_activities_to_db(athlete_id, activities)` — upsert into `activities`
3. Wire backfill into the OAuth callback: right after first login, kick off a backfill for the last 3 months as a `BackgroundTask`
4. **Test**: log in with your real account, confirm your recent activities appear in `activities`

✅ **Checkpoint:** Logging in populates real historical data (independent of groups — this is per-athlete).

---

## Phase 7: Webhook Subscription + Handler

**Goal:** New activities get captured automatically going forward, for any athlete in any group.

1. Build webhook verification endpoint:
   ```
   GET /strava/webhook → validate hub.verify_token, echo back hub.challenge
   ```
2. Build event receiver endpoint:
   ```
   POST /strava/webhook → parse payload → create/update: fetch full activity + save; delete: remove from DB
   ```
   - Ack immediately, do DB work in a background task
3. Deploy backend to Railway (needed for a public HTTPS URL — or use `ngrok` to test locally first)
4. Register the subscription once via curl:
   ```bash
   curl -X POST https://www.strava.com/api/v3/push_subscriptions \
     -d client_id=... -d client_secret=... \
     -d callback_url=https://yourapp.up.railway.app/strava/webhook \
     -d verify_token=your_secret_string
   ```
5. **Test**: log an activity on Strava, confirm it lands in your DB within seconds. Note: this webhook is app-wide — it fires for every authorized athlete regardless of which group(s) they're in.

✅ **Checkpoint:** New activities auto-populate for every authorized athlete.

---

## Phase 8: Group Summary Endpoint

**Goal:** See every member's activity summary within a specific group.

1. `GET /groups/{group_id}/summary?months=3` (behind `require_group_member`):
   ```sql
   SELECT
     a.owner_id,
     ath.name,
     act.sport_type,
     COUNT(*) AS activity_count,
     SUM(act.distance) AS total_distance,
     SUM(act.moving_time) AS total_moving_time,
     AVG(act.average_heartrate) AS avg_hr
   FROM activities act
   JOIN group_memberships gm ON gm.athlete_id = act.owner_id
   JOIN athletes ath ON ath.athlete_id = act.owner_id
   WHERE gm.group_id = :group_id
     AND act.start_date >= NOW() - INTERVAL '3 months'
   GROUP BY a.owner_id, ath.name, act.sport_type;
   ```
2. Optional: `GET /groups/{group_id}/trend?months=3` — same join, bucketed by week, for a comparison chart across members
3. **Test**: call the endpoint for your test group, confirm it returns rows for every member, not just the caller

✅ **Checkpoint:** Backend can answer "how has everyone in this group been doing."

---

## Phase 9: Vue Frontend

1. Scaffold Vue app: `npm create vue@latest`
2. Build core pages:
   - **Login page** — "Connect with Strava" button
   - **Groups page** — list current athlete's groups; "Create Group" form; "Join Group" form (enter invite code)
   - **Group dashboard page** — `/groups/:id` — fetches `/groups/{id}/summary`, renders one card/row per member, plus a comparison chart if desired
3. Handle auth state: `credentials: 'include'` on all requests; configure CORS on FastAPI to allow the frontend origin with credentials
4. **Test locally**: log in, create a group, join it with a second account, confirm the group dashboard shows both members correctly

✅ **Checkpoint:** End-to-end flow works locally — login → create/join group → see everyone's data.

---

## Phase 10: Deploy Everything to Railway

1. Push backend to GitHub, connect to a Railway service
2. Add Postgres plugin to the same project → `DATABASE_URL` auto-injected
3. Set backend env vars: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_VERIFY_TOKEN`, `SECRET_KEY`
4. Update Strava app settings: Authorization Callback Domain → Railway backend domain
5. Deploy frontend (Railway service, or Vercel/Netlify) → point at deployed backend
6. Re-register the webhook subscription against the **production** callback URL
7. **Test**: full flow on production — login, create group, invite code, second person joins, webhook fires, dashboard renders

✅ **Checkpoint:** Fully deployed and working.

---

## Phase 11: Onboard Real Groups

1. Share the frontend URL with your brothers (or anyone)
2. Each logs in with Strava, either creates a group or joins via invite code
3. Confirm activities and group summaries populate correctly for everyone
4. Watch Railway logs during first logins/webhooks to catch edge cases (missing scopes, athletes with no recent activity, etc.)

✅ **Checkpoint:** Multiple independent groups working, each showing correct member-only data.

---

## Phase 12 (Later): Notifications

Deferred — WhatsApp real groups aren't viable at this scale (Meta requires 100k+ conversations/day). When ready:
- [ ] Decide: individual WhatsApp DMs (360dialog/Twilio) vs. Telegram/Discord bot with a real group
- [ ] Notification scope should follow group membership — notify all members of whichever group(s) the athlete belongs to
- [ ] Wire into the webhook handler (Phase 7), right after `save_activities_to_db`

---

## Suggested Pace

| Phase | Focus |
|---|---|
| 1–2 | Backend + DB foundation (including groups schema) |
| 3–4 | Auth |
| 5 | Groups: create/join/membership |
| 6–7 | Data fetching + webhooks |
| 8–9 | Group-aware API + frontend |
| 10–11 | Ship it, onboard real groups |
| 12 | Nice-to-have, no rush |

Each checkpoint is a natural stopping point — pausing between phases is fine.
