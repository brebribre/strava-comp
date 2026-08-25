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

## Phase 4: Token Refresh Logic ✅ DONE

> ℹ️ **Resolved blocker, worth remembering.** The data API briefly returned
> `403 {"resource":"Application","field":"Status","code":"Inactive"}`: Strava's Developer
> Program Standard Tier requires the **app owner to hold a paid Strava subscription**.
> Without it, OAuth and token refresh keep working while every data endpoint
> (`/athlete`, `/athlete/activities`, webhooks) is refused — so this failure mode looks like
> a code bug but isn't. Fixed by subscribing on the owning account (2026-08-23).
> Verified since: `/athlete` 200, `/athlete/activities` 200 returning private activities too.

1. Write `get_valid_access_token(athlete_id)`:
   - reads athlete from DB
   - if `token_expires_at` is past, calls Strava's refresh endpoint, updates DB, returns new token
   - else returns the stored token
2. Test: manually expire a token's timestamp in the DB, confirm it auto-refreshes on next use
   — automated in `backend/scripts/check_token_refresh.py`:
   ```bash
   cd backend && .venv/bin/python -m scripts.check_token_refresh          # stubbed
   cd backend && .venv/bin/python -m scripts.check_token_refresh --live   # real Strava refresh
   ```

Implementation notes: lives in `app/services/tokens.py`; refreshes 5 minutes early so a token
can't expire mid-call; locks the athlete row `FOR UPDATE` so concurrent webhook deliveries
can't race two refreshes; persists the refresh token too, since Strava may rotate it; raises
`ReauthorizationRequired` when the refresh token is rejected.

✅ **Checkpoint:** Token refresh works without manual intervention.
*(verified: stubbed — valid/expired/near-expiry/revoked/unknown-athlete paths; live — back-dated
the real athlete's expiry, confirmed the call went to Strava and fresh credentials were stored)*

---

## Phase 5: Groups — Create, Join, List ✅ DONE

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
   — automated with two seeded athletes (no second Strava account needed):
   ```bash
   cd backend && .venv/bin/python -m scripts.check_groups
   ```
   For manual multi-member testing, drop a fake member into a group by invite code:
   ```bash
   cd backend && .venv/bin/python -m scripts.dev_seed_member <invite_code> "Dev Brother"
   cd backend && .venv/bin/python -m scripts.dev_seed_member --remove
   ```
   Dev athletes use IDs ≥ 999_100_000 and hold no usable tokens, so activity syncing skips them.

Implementation notes: `join` is idempotent (a shared link can be clicked twice); `invite_code`
is only ever returned to existing members; `require_group_member` returns the `Group` so routes
don't reload it, and 404s a missing group before 403ing a non-member.

✅ **Checkpoint:** Groups can be created and joined; membership is enforced.
*(verified: 25 seeded checks — create/join/idempotent-join/bad-code 404/list-scoping/member list,
plus 403 for non-members, 403 across groups, 404 for missing groups, 401 anonymous on every route.
Live: real group "Alvin Brothers" created over HTTP as athlete 168817846 with a dev member joined)*

---

## Phase 6: Manual Activity Fetch + Historical Backfill ✅ DONE

**Goal:** Pull and store an athlete's past activities.

Backfill window is **7 days**, not 3 months — set by `BACKFILL_DAYS` in `.env`.

1. Write `fetch_activities(athlete_id, after_timestamp)`:
   - calls `GET /athlete/activities?after=...&page=N&per_page=200` in a loop until an empty page
2. Write `save_activities_to_db(athlete_id, activities)` — upsert into `activities`
3. Wire backfill into the OAuth callback: right after first login, kick off a backfill for the last
   `BACKFILL_DAYS` days as a `BackgroundTask`
4. **Test**: log in with your real account, confirm your recent activities appear in `activities`
   ```bash
   cd backend && .venv/bin/python -m scripts.check_activities          # stubbed
   cd backend && .venv/bin/python -m scripts.check_activities --live   # real Strava fetch
   ```
   `POST /activities/sync?days=N` re-runs the sync on demand (added for testing; the Phase 9
   frontend can use it as a manual refresh).

Implementation notes: writes go through a Postgres `INSERT … ON CONFLICT DO UPDATE`, so a re-sync
updates renamed/edited activities in place instead of duplicating them. `created_at` is excluded
from the update set, so it keeps meaning "first seen". Batches are de-duplicated by ID before
insert, since one statement cannot touch the same row twice. Backfill failures are caught and
logged — a Strava outage must never break the login redirect.

✅ **Checkpoint:** Logging in populates real historical data (independent of groups — this is per-athlete).
*(verified: 22 stubbed checks incl. field mapping, upsert-not-duplicate, in-batch dedupe, empty
result, login-triggered backfill and login surviving a backfill failure. Live: 6 real activities
stored — Runs, WeightTraining, Tennis)*

---

## Phase 7: Webhook Subscription + Handler ✅ DONE

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
   ```bash
   cd backend && .venv/bin/python -m scripts.check_webhooks
   ```

Implementation notes:
- `GET /strava/webhook` echoes `hub.challenge` only when `hub.verify_token` matches
  `STRAVA_VERIFY_TOKEN` (constant-time compare).
- `POST /strava/webhook` **always** returns 200, even for garbage payloads — Strava requires an
  ack within 2 seconds and may disable a subscription that errors. Real work runs in a background
  task with its own DB session.
- Events for athletes we don't have are ignored without calling Strava. This matters because one
  Strava app serves both local and production, so **both deployments receive every event**.
- `aspect_type: delete` removes the row; athlete deauthorization deletes the Athlete row, which
  cascades to their activities and memberships (groups they created survive, `created_by` is
  SET NULL).
- **Strava allows only one subscription per application.** `GET /push_subscriptions` lists it;
  delete the old one before registering a new callback URL.

Registered subscription: **id 367982** → `https://backend-production-96ee.up.railway.app/strava/webhook`
(production only — local development receives no events while this is registered).

Deployment gotcha: Railway did **not** auto-deploy on push even though the service showed the
GitHub repo as its source, because the source was set via `railway config apply` rather than
through the dashboard's connect flow, so no GitHub webhook was registered. Reconnect the repo in
Settings → Source, or deploy manually with `railway up --service backend`.

✅ **Checkpoint:** New activities auto-populate for every authorized athlete.
*(verified locally: 20 checks — handshake incl. wrong token and wrong mode, create/update/delete,
unknown athlete, malformed and non-JSON payloads, Strava failure mid-handling, deauthorization.
Still pending: registering the push subscription against the deployed URL)*

---

## Phase 8: Group Summary Endpoint ✅ DONE

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
2b. Added beyond the plan: `GET /groups/{group_id}/feed?limit=&before=` — every member's
   activities newest-first, for the Strava-style group feed. Cursor-paginated on `start_date`
   rather than offset, so activities arriving mid-scroll can't duplicate or skip rows.
2a. `GET /groups/{group_id}/trend` weeks carry a **`by_sport` breakdown**, so the chart can
   stack by activity type. Per-sport counts and times always sum to the week's totals.

2b-i. Feed items also carry `polyline` (Strava's `summary_polyline`, not the full-resolution
   one — the card only draws a thumbnail) and `photo_url`, so every card can show a visual.

2c. Also added: `GET /activities/{activity_id}` — full detail for one activity. The list and
   webhook payloads are Strava `SummaryActivity` (resource_state 2), which has no description,
   calories or splits, so the first view enriches from Strava's detailed endpoint
   (resource_state 3) and caches it back into `raw_data`. Enrichment uses the **owner's** token,
   never the viewer's; authorization is "owner, or shares a group with the owner". If Strava is
   unreachable the endpoint degrades to stored data with `is_detailed: false` rather than failing.

2d. `enrich_recent()` runs as a background task after every sync and backfill, upgrading up to
   10 recent summary-only activities to detailed payloads. Without it, backfilled activities
   would never have photos or descriptions at all. Bounded on purpose: one Strava request per
   activity against a 200-per-15-minutes budget, and it stops early on any error rather than
   burning what's left.
3. **Test**: call the endpoint for your test group, confirm it returns rows for every member, not just the caller
   ```bash
   cd backend && .venv/bin/python -m scripts.check_summary
   ```

Implementation notes:
- Parameter is **`?days=`** (default 30, max 365), not `?months=` — `BACKFILL_DAYS` is 7, so a
  3-month default would mostly return empty windows.
- Members come from `group_memberships`, not from the activity rows, so **someone who did nothing
  still appears with zeroes** instead of vanishing from the leaderboard.
- Response nests per-sport breakdowns inside each member, and members are sorted by moving time
  (most active first) — the comparison the group actually wants.
- Overall `avg_heartrate` is weighted by activity count across sports, so a single long ride
  doesn't count the same as five runs. Activities without HR are excluded rather than counted as 0.
- Onboarding helper: `scripts/add_member.py --list` shows athletes/groups; `add_member.py
  <athlete_id> <invite_code>` puts a brother into a group after they log in, so they never need
  to touch Swagger.

✅ **Checkpoint:** Backend can answer "how has everyone in this group been doing."
*(verified: 24 checks — per-sport splits, window filtering, HR averaging and nulls, inactive
members included, non-members excluded, ordering, days validation, weekly trend buckets,
403/401/404 access control. Live: real summary over 6 activities in group "Alvin Brothers")*

---

## Phase 5b: Invite Links ✅ DONE (added beyond the original plan)

Sharing a group is a link — `https://<frontend>/join/<invite_code>` — not a code to type.

- **Already logged in:** the `/join/:code` route joins immediately and lands them in the group.
- **Not logged in:** the code is passed to `GET /auth/strava/login?invite=…`, which **signs it
  into the OAuth `state`**. After the athlete authorizes, the callback joins them and redirects
  to `?login=ok&group=<id>`, and the router guard sends them straight into that group.

The code rides in the signed state rather than in browser storage, so it survives the trip to
Strava even in a fresh browser, and cannot be swapped for another group's code en route —
tampering fails the existing CSRF check.

A bad code never blocks login: the athlete is logged in regardless and told the link is stale
(`?invite_error=not_found`).

Copy-link buttons live in the group header and in Manage groups (with a `document.execCommand`
fallback for when the Clipboard API is unavailable).

✅ **Checkpoint:** anyone with the link ends up in the group, account or not.
*(verified: 12 checks — logged-out visitor joins through the full OAuth round trip, redirect
names the group, tampered state rejected, re-joining is a no-op with no duplicate membership,
unknown code 404. Live: logged-in join redirects to the group, bad link shows a clear message,
logged-out visit redirects to Strava.)*

---

## Phase 8b: Group Targets ✅ DONE (added beyond the original plan)

A group can set a shared training target: **N qualifying exercises per week / month / year,
until a given date**, with per-sport rules for what counts as an exercise.

Model: `group_targets`, keyed by `group_id` (one target per group, so saving replaces rather
than accumulating). Rules live in a JSONB column, so adding a sport or a new kind of threshold
needs no migration.

Qualification: time is the universal fallback (`default_min_minutes`, default 30). A sport may
add a distance threshold, and the two are **OR'd** — a short but long run still counts, which is
what "for run it is time or range" means. Evaluated in Python rather than SQL: the rules are
per-sport and OR'd across thresholds, which makes for an unreadable query at no benefit at this
data size.

Endpoints (all members-only):
- `GET /groups/{id}/target`, `PUT` to set/replace, `DELETE` to remove — 404 when unset
- `GET /groups/{id}/target/progress` — every member's count for the **current** period,
  furthest-ahead first, with `remaining`, `percent` (capped at 100), `days_left_in_period`,
  `periods_remaining` and `is_expired`

Frontend: **Target** tab shows the logged-in athlete's standing as a big progress ring plus a
table of everyone else; **Settings** tab (also reachable from Manage groups) edits the target.

✅ **Checkpoint:** targets are stored, enforced consistently, and visible per member.
*(verified: 45 checks — qualification incl. time-or-distance, exactly-at-threshold, unknown
sports, null sport_type; period maths incl. leap February and December rollover; replace-not-
duplicate; over-achievement clamping; expiry; 403/401 access control; delete. Live: set 4/week
via the UI, edited to 6/week, ring and table updated.)*

---

## Phase 9: Vue Frontend ✅ DONE (local) — not yet deployed

1. Scaffold Vue app: `npm create vue@latest`
2. Build core pages:
   - **Login page** — "Connect with Strava" button
   - **Groups page** — list current athlete's groups; "Create Group" form; "Join Group" form (enter invite code)
   - **Group dashboard page** — `/groups/:id` — fetches `/groups/{id}/summary`, renders one card/row per member, plus a comparison chart if desired
3. Handle auth state: `credentials: 'include'` on all requests; configure CORS on FastAPI to allow the frontend origin with credentials
4. **Test locally**: log in, create a group, join it with a second account, confirm the group dashboard shows both members correctly

Architecture is specified in [frontend/REQUIREMENTS.md](frontend/REQUIREMENTS.md) — Vite + Vue 3 +
TypeScript + Tailwind 4, layered `View → Container → Hook → API hook → fetch`, Pinia for shared
state, router guard for auth, Chart.js for the trend chart.

Built: `LoginView`, `SidebarView`, `GroupView` (nested tabs); containers `Login`, `Sidebar`,
`GroupList`, `GroupHeader`, `GroupFeed`, `GroupSummary`; reusables (button, input, card, alert,
table, chart, avatar, stat row, tab link, empty state); hooks (`useAuth`, `useGroup`, `useGroups`,
`useGroupFeed`, `useGroupSummary`, `useGroupTrend`, `useActivitySync`, `useFormat`,
`useLoginError`); API hooks (`useAuthApi`, `useGroupApi`, `useActivityApi`).

The group page has tabs: **Feed** (Strava-style timeline — every member's activities grouped by
day, with avatars, sport badges and per-sport stats), **Summary**, **Target** and **Settings**.

The **Feed leads with the target widget** — the same progress ring and headline as the Target
tab, minus the edit button, and silent when no target is set. Both routes render one
`TargetHeroContainer`, differing only by props.

The Summary chart has two shapes, because the two questions are different:
- **Moving time** — one series per member, side by side, for comparing people.
- **Activities** — **stacked by sport**, colour-coded, for seeing what the training was made of.

Both are filterable by **sport** and by **athlete** (chips; empty selection means everything).
Sport colours are fixed per sport in `useSportColors`, so a sport looks the same in every chart;
unknown sports hash into a fallback palette rather than colliding on first-seen order.

✅ **Checkpoint:** End-to-end flow works locally — login → create/join group → see everyone's data.
*(verified in-browser against the real local backend: guard redirects to /login when logged out,
sidebar + group list render real groups, dashboard shows real totals per member with inactive
members at zero, window switcher refetches `?days=`, Chart.js renders weekly moving time.
Not yet verified: `Connect with Strava` locally — Strava's single callback domain points at
Railway, so OAuth is only exercisable in production.)*

---

## Phase 9b: Mobile ✅ DONE

The fixed 256px sidebar took two-thirds of a 375px screen, leaving content clipped off-canvas.
Below `lg` it is now an off-canvas drawer (backdrop, close button, auto-closes on navigation);
from `lg` up it is unchanged. Tabs scroll horizontally, action rows stack, wide tables scroll
inside their own container, and the progress ring shrinks on phones.

Rules are written down in [frontend/REQUIREMENTS.md](frontend/REQUIREMENTS.md) §11b.

✅ **Checkpoint:** every screen usable on a phone.
*(verified at 375×812, 768×1024 and desktop: feed, summary, target, settings, manage groups,
activity detail, login. No horizontal page overflow on any of them.)*

---

## Phase 9c: Monochrome redesign ✅ DONE

Greyscale throughout — no accent colour, hierarchy from contrast and weight. Subtle corners
(3–9px), and small deliberate motion: press-scale on buttons and chips, 1px card lift on hover,
a tab underline that scales in, and a 4px staggered rise on lists. All of it disabled under
`prefers-reduced-motion`.

Tokens and the motion system are documented in
[frontend/REQUIREMENTS.md](frontend/REQUIREMENTS.md) §11a.

Gotcha worth remembering: **Tailwind v4 hoists `@theme` to `:root` regardless of a surrounding
media query**, so `@media (prefers-color-scheme: dark) { @theme { … } }` applies the dark palette
unconditionally — light mode silently rendered dark. Dark values must be plain custom property
declarations on `:root` inside the media query.

✅ **Checkpoint:** consistent monochrome UI in both themes.
*(verified: light and dark at desktop and 375px, including the stacked chart's tonal ramp
inverting per theme.)*

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

## Phase 13: Personal Recap ✅ DONE (added beyond the original plan)

A personal, per-sport growth view — no group involved. Lives in the sidebar under **You**,
separate from Groups.

**Prerequisite:** the recap needed history the app never had. `BACKFILL_DAYS` capped every sync
at a week, so the database held 24 activities. The sync ceiling is now 10 years
(`POST /activities/sync?days=2000`), which pulled **160 activities across 14 months** — the list
endpoint returns 200 per request, so even years cost a handful of calls.

**What the data supports** (measured across the real activities): distance/time/elevation on all,
`average_speed` on all, heart rate on ~85%, `suffer_score` on ~85%, cadence on ~80%, calories on
only ~40% — so calories can't be a headline metric.

Endpoints:
- `GET /recap?days=` — every sport's totals beside the equivalent previous period, ordered by
  time invested (commitment) rather than distance, which would always rank running first
- `GET /recap/{sport}?months=` — monthly volume, pace/speed and HR trend, personal bests
  (longest, fastest, most elevation, hardest effort by relative effort), and consistency
  (active weeks, longest streak, biggest gap)

Two decisions worth keeping:
- **Growth is suppressed when the comparison window predates the athlete's first activity.**
  Otherwise the recap reports "+1133%", which measures when someone started using Strava rather
  than any change in training. The API returns `baseline_complete: false` and the UI explains why.
- **The performance chart overlays pace against heart rate on two axes**, with the pace axis
  reversed so improvement always points up. Pace falling while HR holds or drops is the single
  clearest picture of getting fitter — and it only reads that way overlaid.

### Effort zones (why heart rate, not workout types)

The obvious categorisation — interval / threshold / long / easy — turned out to be
unsupportable, and the data said so:

| Signal | Coverage across 115 runs |
|---|---|
| Strava's `workout_type` tag | **0 tagged** (114 null, 1 "default") — it's only set manually |
| `splits_metric` / `laps` (needed to detect intervals) | **7** — only enriched activities have them |
| Average heart rate | **101** |

So runs are bucketed by **average heart rate as a percentage of an estimated maximum**
(standard five zones: Recovery / Easy / Steady / Threshold / Hard). It covers 88% of runs, and
**pace at a fixed effort is a better definition of improvement** than counting sessions by type.

The max is estimated, since reading Strava's configured zones needs `profile:read_all`, which
this app doesn't request: the 95th percentile of recorded maximums (robust against a single
sensor spike), falling back to the hardest average scaled up, then to a generic default.

Known limitation: a true interval session averages out to Z3/Z4 and is indistinguishable from
a tempo run. Fixing that means enriching every run for split data (~1 API call each).

✅ **Checkpoint:** each sport's growth is visible over months.
*(verified: 26 checks — growth maths, baseline suppression, pace vs speed per sport family,
bests selection, consistency, empty sports, auth. Live: 14 months of real running shows pace
7:30 → 6:32 /km while average HR fell 168 → 150.)*

---

## Phase 12: Notifications ✅ DONE (Telegram)

WhatsApp was ruled out: Meta's Groups API only works with groups **the business creates via
the API** (invite-only, max 8 participants, Official Business Account required) — there is no
way to post into an existing personal group. Telegram has none of those limits.

**Connecting a chat requires no chat id.** The group's Settings page shows a pairing code; the
user adds `@BruderBandeBot` to their Telegram chat and sends `/connect <CODE>`. The bot reports
the chat back through a Telegram webhook (`POST /telegram/webhook`, verified with
`TELEGRAM_WEBHOOK_SECRET`), the app stores the chat id and title, and the settings page updates
itself while the user watches. The code rotates on use, so a forwarded message can't be replayed.
`/disconnect` in the chat unlinks it, as does Disconnect in the app.

One-time per environment:
```bash
cd backend && .venv/bin/python -m scripts.setup_telegram_webhook https://api.bruderbande.com
```
Telegram allows one webhook URL per bot, so pointing it at production means local `/connect`
stops working (use `--delete` while developing).

Setup: bot `@BruderBandeBot` via @BotFather; `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`
on the backend.

How it works: the webhook stores the activity, then announces it to every group the athlete
belongs to that has a chat connected **and** whose target rules the activity satisfies (no
target ⇒ everything qualifies). The message is a server-rendered PNG card captioned
"*Name* just did *Activity*!".

Implementation notes:
- The card is rendered **twice** — canvas in the browser for in-app sharing, Pillow on the
  server for notifications, since a webhook has no browser. `app/services/share_card.py` and
  `useShareCard.ts` must be kept in step when restyling.
- Inter is vendored as a variable font (`app/assets/fonts/Inter.ttf`, OFL) — Pillow needs a
  real TTF and system fonts can't be relied on in a container.
- A `(activity_id, group_id)` row is **claimed before sending**, because Strava fires `create`
  and often `update` for the same activity; the claim is released if the send fails so a retry
  can still work.
- Settings live in a new `group_integrations` table rather than a column on `groups`, because
  `SQLModel.create_all` creates new tables but never alters existing ones — a new column would
  exist locally and be silently missing in production.

✅ **Checkpoint:** finishing a qualifying activity posts a card to the group's Telegram chat.
*(verified: 17 checks with the API stubbed — qualification, dedupe, failure/retry, access
control — plus a real card posted to the "JJB" group.)*

---

## Phase 12 (original plan): Notifications

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
