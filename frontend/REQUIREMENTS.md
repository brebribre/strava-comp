# Frontend Requirements — Strava Group Tracker

Architecture rules for the Vue frontend. These are binding: if a change can't be made
without breaking one of them, the rule gets discussed and updated here first, not
worked around in code.

---

## 1. Stack

| Concern | Choice |
|---|---|
| Build tool | **Vite** |
| Framework | **Vue 3** (`<script setup>`) |
| Language | **TypeScript** — no plain `.js` files |
| Styling | **Tailwind CSS v4** — utility classes in templates; design tokens in `src/style.css` |
| Router | Vue Router |

---

## 2. Layers

Four layers, each with one job. The direction of dependency is one-way:

```
View  →  Container  →  Hook  →  API hook  →  fetch
  ↘         ↘            ↘
   router    Reusable     Store (Pinia)
```

| Layer | Lives in | Named | May contain |
|---|---|---|---|
| **View** | `src/views/` | `<Name>View.vue` | Layout + `<router-view>` outlets. The router points here. |
| **Container** | `src/containers/` | `<Name>Container.vue` | Presentation + calls to hooks, routing, handlers/emits |
| **Reusable** | `src/reusables/` | `<Name>.vue` | Generic presentational pieces — buttons, tables, cards, inputs |
| **Hook** | `src/hooks/` | `use<Name>.ts` | Logic: state, transforms, business rules. Calls API hooks and stores. |
| **API hook** | `src/api/` | `use<Domain>Api.ts` | One per backend domain. HTTP only — no business logic. |
| **Store** | `src/stores/` | `use<Name>Store.ts` | Pinia. Shared cross-container state only. |

---

## 3. Views

- A View is what the **router** points at. Nothing else routes.
- A View owns **layout**, and may render **multiple containers**, including through
  nested `<router-view>` outlets.
- Example: a `SidebarView` renders the sidebar on the left and whatever container the
  child route resolves to on the right.

```vue
<!-- src/views/SidebarView.vue -->
<template>
  <div class="flex h-screen">
    <SidebarContainer class="w-64 shrink-0" />
    <main class="flex-1 overflow-y-auto p-6">
      <router-view />
    </main>
  </div>
</template>
```

- Views hold as little logic as possible. If a View needs logic, it belongs in a hook.

## 4. Containers

- A Container is a **feature**: the group dashboard, the login panel, the sidebar.
- **A container may render another container.** When the same feature block appears on two
  routes — e.g. the target hero on both the Target tab and the top of the Feed — it stays one
  container rather than becoming a reusable, because it knows about targets and athletes and
  so fails the "feature-agnostic" test in §5. Behaviour differences go through props
  (`show-edit`, `hide-when-unset`), not a copy.
- A Container **may have its own presentational markup**, but anything generic —
  buttons, tables, cards, spinners, empty states — comes from `src/reusables/`.
- The **only** TypeScript allowed inside a Container:
  1. **calling hooks** — `const { members, isLoading } = useGroupSummary(groupId)`
  2. **routing** — `router.push(...)`, reading `route.params`
  3. **component logic** — event handlers, `emit`, local UI-only refs
     (`const isMenuOpen = ref(false)`)

- Everything else — fetching, mapping, formatting, sorting, validation, business rules
  — goes in a hook. If a Container's `<script setup>` is doing arithmetic on data or
  shaping an API response, that code is in the wrong place.

```vue
<!-- src/containers/GroupSummaryContainer.vue -->
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useGroupSummary } from '@/hooks/useGroupSummary'
import DataTable from '@/reusables/DataTable.vue'

const route = useRoute()
const { members, isLoading, error, refresh } = useGroupSummary(Number(route.params.id))
</script>
```

## 5. Reusables

- Generic, feature-agnostic, no knowledge of Strava, groups, or athletes.
- Take props, emit events. No data fetching, no router access.
- If a reusable needs to know what a "group" is, it isn't a reusable — it's container
  markup.

## 6. Hooks

- Named `use<Name>` in `src/hooks/use<Name>.ts`, one hook per file.
- Return a plain object of refs/computed/functions.
- A hook may call other hooks, **API hooks**, and **stores**. A hook never imports a component.
- Hooks own loading and error state, so containers can render it without owning it.
- Hooks hold the *business* logic: which window to request, how to sort members, how to
  format a duration. The raw HTTP call is not their job — that belongs to an API hook.

```ts
// src/hooks/useGroupSummary.ts
export function useGroupSummary(groupId: number) {
  const members = ref<MemberSummary[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  async function refresh() { /* fetch, map, set */ }
  onMounted(refresh)
  return { members, isLoading, error, refresh }
}
```

## 6a. API hooks

- **Every concrete backend call is a hook**, named `use<Domain>Api` in `src/api/`.
- **Split by domain, not one god-hook**: `useAuthApi`, `useGroupApi`, `useActivityApi`.
- Plain `fetch` — no axios. A single shared `request()` helper sets the base URL,
  `credentials: 'include'`, JSON headers, and turns non-2xx into a typed error.
- API hooks are **transport only**: call, parse, type, return. No loading refs, no sorting,
  no formatting, no defaults beyond what the endpoint requires. Those live in regular hooks.
- Return types come from `src/types/api.ts` and mirror the backend's response models.

```ts
// src/api/useGroupApi.ts
export function useGroupApi() {
  return {
    list: () => request<GroupRead[]>('GET', '/groups'),
    create: (name: string) => request<GroupRead>('POST', '/groups', { name }),
    join: (inviteCode: string) => request<GroupRead>('POST', '/groups/join', { invite_code: inviteCode }),
    members: (id: number) => request<GroupMember[]>('GET', `/groups/${id}/members`),
    summary: (id: number, days = 30) => request<GroupSummary>('GET', `/groups/${id}/summary?days=${days}`),
    trend: (id: number, days = 30) => request<GroupTrend>('GET', `/groups/${id}/trend?days=${days}`),
  }
}
```

| API hook | Wraps |
|---|---|
| `useAuthApi` | `GET /me`, `POST /auth/logout` (login is a full-page redirect, not fetch) |
| `useGroupApi` | `/groups`, `/groups/join`, `/groups/{id}/members`, `/summary`, `/trend` |
| `useActivityApi` | `POST /activities/sync` |

## 6b. Stores (Pinia)

- Pinia is for **shared state that outlives a single container**: the current athlete,
  the selected group. One store per file, `use<Name>Store` in `src/stores/`.
- A store is **not** a place for HTTP. Stores hold state; hooks call API hooks and write
  into stores.
- **Containers do not import stores directly** — they go through a hook (`useAuth()` wraps
  `useAuthStore()`). This keeps rule §7 intact: a container calls hooks, full stop.
  *(Say the word if you'd rather let containers read stores directly — it's less
  indirection, at the cost of a second thing containers are allowed to touch.)*

## 6c. Router guard

- Auth is enforced **once, in a router guard** — not per container.
- `useAuthStore` holds the current athlete. The guard resolves it (calling `/me` on first
  load), and redirects to `/login` when the backend answers `401`.
- Routes opt out with `meta: { public: true }` (the login page and the OAuth landing).
- **Where a login lands:** a plain login goes to `/recap` — the personal page is the more
  useful home than a list of groups. Arriving via an invite link (`?login=ok&group=<id>`)
  overrides that and lands in the group that was just joined. `/` and unknown paths also
  resolve to `/recap`, so the landing is the same however the app is opened.
- Because the session is an **HttpOnly cookie, JS can never read it** — "am I logged in?"
  is always answered by `/me` returning 200 vs 401, never by inspecting storage.

---

## 7. The TypeScript rule, stated plainly

> TypeScript lives in **containers** or **hooks** — nowhere else.

- **Views**: template and layout only.
- **Reusables**: props/emits only; no logic beyond rendering what they're given.
- **Containers**: hooks, routing, handlers/emits. Nothing more — no `fetch`, no stores, no
  data shaping.
- **Hooks**: business logic and state.
- **API hooks**: HTTP only.
- **Stores**: shared state only.

---

## 8. Directory layout

```
frontend/
  src/
    views/          <Name>View.vue        — routed, layout + router-view outlets
    containers/     <Name>Container.vue   — features
    reusables/      <Name>.vue            — buttons, tables, cards, inputs
    hooks/          use<Name>.ts          — business logic and state
    api/            use<Domain>Api.ts     — HTTP calls, one hook per domain
                    request.ts            — shared fetch helper (base URL, credentials)
    stores/         use<Name>Store.ts     — Pinia, shared state
    types/          api.ts                — response types mirroring the backend
    router/         index.ts              — routes + auth guard
    main.ts
  index.html
  tailwind.config.js
  tsconfig.json
  vite.config.ts
```

**Naming note:** the convention is `use<Domain>Api` (capital A, lowercase pi) —
`useGroupApi`, not `useGroupAPI`. Pick one and never mix; this doc is the tiebreaker.

---

## 9. Backend contract

Base URL from `VITE_API_BASE_URL`:
- local `http://localhost:8000`
- production `https://backend-production-96ee.up.railway.app`

**Every request sends `credentials: 'include'`** — auth is an HttpOnly session cookie,
never a token in JS. The backend must list the frontend's origin in `FRONTEND_ORIGIN` /
`EXTRA_CORS_ORIGINS`.

| Endpoint | Purpose |
|---|---|
| `GET /auth/strava/login?invite=` | Full-page redirect (not fetch) — starts OAuth; `invite` is signed into the OAuth `state` and auto-joins after login |
| `GET /me` | Current athlete; `401` means logged out |
| `POST /auth/logout` | Clears the session |
| `GET /groups` | Groups the athlete belongs to |
| `POST /groups` | Create — `{ name }` |
| `POST /groups/join` | Join — `{ invite_code }` |
| `GET /groups/{id}/members` | Members of a group |
| `GET /groups/{id}/summary?days=30` | Per-member, per-sport totals |
| `GET /groups/{id}/trend?days=30` | Weekly buckets per member |
| `GET /groups/{id}/feed?limit=20&before=` | Shared timeline, newest first, cursor-paginated; includes `polyline` + `photo_url` for the card visual |
| `GET /push/config` | The VAPID public key a browser subscribes with |
| `POST/DELETE /push/subscriptions` | Register or forget this device |
| `POST /push/test` | Send yourself a notification, to prove a phone is set up |
| `GET /activities/{id}` | One activity in full: description, calories, splits, GPS polyline |
| `GET /recap?days=365` | Personal per-sport totals with growth vs the previous period |
| `GET /recap/{sport}?months=12` | One sport: monthly trend, bests, consistency |
| `GET /push/config` | The VAPID public key a browser subscribes with |
| `POST/DELETE /push/subscriptions` | Register or forget this device |
| `POST /push/test` | Send yourself a notification, to prove a phone is set up |
| `GET /activities/{id}` | One activity in full, incl. `exercises` parsed from a logged gym session |
| `GET/PUT/DELETE /groups/{id}/target` | The group's training target — `count`/`period`, `starts_at`–`until`, per-sport rules |
| `GET /groups/{id}/target/progress` | Every member's progress against it, current period |
| `POST /activities/sync?days=7` | Manual re-sync |

Cross-domain note: if the frontend and API end up on different domains, the backend
needs `COOKIE_SAMESITE=none` (with `COOKIE_SECURE=true`) or the session cookie is
silently dropped.

---

## 10. Planned screens

| Route | View | Containers |
|---|---|---|
| `/login` | `LoginView` | `LoginContainer` |
| `/join/:code` (public) | `JoinView` | `JoinInviteContainer` |
| `/groups` | `SidebarView` | `SidebarContainer` + `GroupListContainer` |
| `/groups/:id/summary` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupSummaryContainer` |
| `/groups/:id/feed` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupFeedContainer` |
| `/groups/:id/settings/{members,target,notifications}` | `SidebarView` → `GroupView` → `GroupSettingsView` | + `GroupSettingsNavContainer` + the section's container |
| `/recap` | `SidebarView` | `SidebarContainer` + `RecapOverviewContainer` — one row per sport, big icon + name, chevron to open |
| `/recap/:sport` | `SidebarView` | `SidebarContainer` + `SportRecapContainer` |
| `/groups/:id/settings` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupSettingsContainer` |
| `/groups/:id/activities/:activityId` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `ActivityDetailContainer` |

`/groups/:id` redirects to the **summary** — the target and week-by-week progress are what people open a group for. Settings pages all share one root class (`max-w-2xl space-y-4`) so switching sections doesn't shift the layout. **Two levels of nested `router-view`:** `SidebarView`
renders the sidebar plus a child outlet; `GroupView` renders the group header and tabs plus
its own outlet, so the tabs stay mounted while feed/summary swap underneath — the pattern
described in §3.

---

## 11. Charts

Investigated 2026-08-23. Sizes are npm *unpacked* (not shipped bundle size — all of these
tree-shake); downloads are weekly, as a maintenance signal.

| Library | Vue wrapper | Unpacked | Weekly DL | Last publish | Notes |
|---|---|---|---|---|---|
| **Chart.js** | `vue-chartjs` 5.3.4 | 6.2 MB | 12.6M | 2026-07 | Canvas. Small runtime (~60 KB gz), first-class TS types, enormous adoption |
| **ECharts** | `vue-echarts` 8.1.0 | 60 MB | 5.0M | 2026-08 | Most powerful. Tree-shakes to ~150-300 KB. Overkill for two charts |
| **ApexCharts** | `vue3-apexcharts` 1.11.1 | 18.4 MB | 2.1M | wrapper 2026-03 | Prettiest defaults; heaviest of the three, and the Vue wrapper lags the core |
| **Unovis** | `@unovis/vue` 1.6.7 | 0.4 MB | 161K | 2026-06 | Modern, Vue-first, small. Much smaller community — more risk if you hit a bug |

**Decision: Chart.js + `vue-chartjs`.** ✅ chosen 2026-08-23

Reasoning for *this* project: the trend view is a handful of series (one per brother) over
a few weeks — a grouped bar or multi-line chart. That's squarely what Chart.js does, at the
smallest real bundle cost, with the best odds that any question has already been answered
somewhere. `vue-chartjs` is a thin typed wrapper, actively published.

Trade-off worth knowing: Chart.js renders to **canvas**, so charts can't be styled with
Tailwind classes — colours and fonts are passed as options. If the design later needs
DOM/SVG charts styled by Tailwind, Unovis or hand-rolled SVG is the direction, not Chart.js.

Upgrade path: if the dashboard grows into something richer (zoom, brushing, many series),
swap to ECharts. Keeping all chart code inside a container + hook pair means that swap
touches one container, not the app.

## 11a. Visual design

**Dark only, pine accent.** There is no light theme and no runtime theming — the tokens in
`src/style.css` are the design. `color-scheme: dark` is declared so native controls (date
pickers, spinners, scrollbars) follow, and the browser never renders a light variant the
palette isn't built for.

| Token group | Purpose |
|---|---|
| `accent` (`#047857`) / `accent-contrast` / `accent-soft` | everything *active*: primary buttons, tabs, selected nav, progress fills, the GPS trace |
| `canvas` / `surface` / `raised` | page → card → inset, in ascending contrast |
| `line` / `line-strong` | **dividers and control outlines** — not card edges (see below) |
| `ink` / `ink-muted` / `ink-subtle` / `ink-inverse` | text |
| `--radius-sm…xl` (3–9px) | **subtle** corners; only avatars and swatches are rounder |
| `--duration-quick` (130ms) / `--duration-soft` (260ms), `--ease-out-soft` | one motion system |

Surfaces aren't neutral greys: each mixes a share of the accent into a dark base
(`color-mix(in srgb, var(--color-accent) 12%, #0a0a0a)` and upward), so the app reads as one
colour rather than a grey app with green buttons. Cards carry slightly more than the page, which
keeps the depth ordering visible through the tint.

**Cards carry no border.** The surface tint is what separates a card from the page; an outline
on top of it states the same thing twice and makes a stack of cards read as a grid of boxes.
This follows from the tint doing the work — so it holds for `AppCard` and for the modal panel,
and the rule is: *if a thing is a card, its edge comes from its background, not a border.*

Borders are still right for two other jobs, and those stay:
- **Controls** — inputs, secondary buttons, avatars, code chips. An input needs a visible target
  before it's focused, and a background alone doesn't say "type here".
- **Dividers** — the sidebar's right edge, the header's bottom rule, rows inside a card. These
  are lines *between* things, not outlines *around* them.

An interactive card therefore can't signal hover by brightening its edge; it lifts
(`-translate-y-px`) and its surface goes to `raised` instead.

**Body text stays neutral.** The accent marks what's active; colouring everything is what makes
a strong hue exhausting.

## 11a-i. Logo

`AppLogo` renders the **BRUDERBANDE** wordmark: extra-bold, uppercase, tracked out at
`0.18em` and stretched `scaleX(1.12)` — wider than tall by construction, since no system font
ships an extended width. Sizes `sm` / `md` / `lg`; an `align` prop sets the transform origin,
because the stretch grows from that origin and a left-anchored logo drifts right of centre
when its parent centres it.

Used in the sidebar, the mobile top bar, the login screen — and redrawn on the **share card**
by `drawWordmark` in `useShareCard`, which places glyphs one at a time (canvas has no
dependable `letterSpacing` across browsers) and applies the same stretch, so the wordmark
matches wherever it appears.

## 11c. Share cards

An activity can be exported as a **1080×1350 PNG** — the 4:5 portrait shape chat apps and
stories show without cropping. Rendered with `useShareCard`:

- **Always dark**, regardless of the viewer's theme. The image ends up in other people's
  chats, where it should look deliberate rather than inherit whatever mode the sender had on.
- Contents: profile row (initials avatar, athlete name, date/time), the **sport icon**, sport
  label, activity title (wrapped to two lines, ellipsised), a two-column stat grid of up to six
  metrics, and a `bruderbande.com` footer.
- Drawn with the **Canvas 2D API and `Path2D`**, reusing the same icon path data as
  `SportLoader` (`useSportIcon`) — no screenshot library, no extra dependency.
- Sharing prefers the **Web Share API with a file**, which opens the OS share sheet and can
  hand the image straight to WhatsApp. Where that isn't supported (most desktop browsers) the
  button falls back to a download, decided by `navigator.canShare` rather than by guessing
  from the user agent.
- The user sees a **preview before sending**, as on Strava.

## 11a-ii. Sport icons

`SportIcon` renders a sport with **Material Symbols** (Apache 2.0), compiled in at build time
by `unplugin-icons` — no runtime fetch, and only the icons actually referenced are bundled.
Chosen over the alternatives because it was the only set carrying a real `badminton` icon
alongside full coverage of everything else Strava reports.

Arbitrary `sport_type` values collapse to one of 15 families via `useSportIcon().resolve()`,
so `TrailRun`, `VirtualRide` and `EBikeRide` all land somewhere sensible; anything unknown
falls back to a generic exercise icon.

Used in the recap (sport cards, per-sport header), the group feed and activity detail (sport
badges) and the summary totals row.

**Two places deliberately keep hand-drawn paths**: `SportLoader`, because it animates limbs
that no icon set provides, and the share card, which strokes the same path data onto a canvas
with `Path2D`.

## 11b. Responsive rules

The app is used on phones as much as laptops, so **mobile is a first-class layout, not an
afterthought**.

- **The phone shell is an app shell, not a page.** Below `lg` there are two fixed pieces and
  no browser-shaped chrome between them:
  - a **profile bar** at the top — avatar and first name on the left, a settings button on the
    right whose menu holds Log out. No navigation lives in it.
  - a **floating tab bar** at the bottom — Recap and Groups, inset from the edges with rounded
    corners and its own shadow, sitting above `env(safe-area-inset-bottom)`. A tab owns
    everything beneath it, so `/recap/Run` keeps Recap lit and `/groups/5/feed` keeps Groups.

  From `lg` up both disappear and the sidebar is static and in flow, doing both jobs.
- **No scrollbar tracks on phones.** Every scroll container below `lg` keeps its scrolling and
  loses its bar (`scrollbar-width: none` plus the `::-webkit-scrollbar` reset) — a native list
  moves without a gutter down its side. Desktop keeps its scrollbars, where they are how you
  know a panel scrolls at all.
- **The notch is paid for, not avoided.** `viewport-fit=cover` plus a translucent status bar
  means the page owns the whole screen, so the top bar and the drawer add
  `env(safe-area-inset-top)` to their own padding and the tab bar adds
  `env(safe-area-inset-bottom)`. On anything without a notch those resolve to `0`, so a
  laptop, an Android phone and a browser tab are all untouched — which is why the insets go
  on the components rather than into a device check.
- **Zoom is off on phones.** `maximum-scale=1, user-scalable=no, viewport-fit=cover` plus
  `touch-action: manipulation` and no tap highlight. iOS Safari ignores `user-scalable=no` on
  purpose, so `main.ts` also refuses Safari's `gesture*` events — that is the part that
  actually stops a pinch. Scrolling is untouched. This is a deliberate trade: it costs pinch
  zoom, which is a real accessibility affordance, in exchange for the app feeling installed.
- **No horizontal page scroll, ever.** Wide content (tables, charts) scrolls inside its own
  `overflow-x-auto` container. Check with
  `document.documentElement.scrollWidth === window.innerWidth`.
- **Tabs** scroll horizontally rather than wrapping (`overflow-x-auto whitespace-nowrap`).
- **Tables** keep `overflow-x-auto`; secondary detail (e.g. the per-sport list on the summary
  row) is `hidden sm:inline` rather than wrapping into a tall column.
- **Rows of actions** stack with `flex-col sm:flex-row`.
- Pixel-sized SVGs that CSS can't scale (the progress ring) read `useViewport()`.

**List pages share one row shape.** The recap and the group list are the same object: a
full-width card per item, an oversized icon and name, a line of ordinary text beneath, and a
chevron saying the row opens. Adding to such a list is a `+` button beside the page title that
opens `AppModal` — a bottom sheet on a phone, a dialog on a laptop — rather than forms sitting
permanently above the list.

**Page titles are one size everywhere.** `PageTitle` (`text-3xl` / `sm:text-4xl`, truncating)
is the heading on Recap, a sport, a group, an activity and the group list. Pages differ in what
sits *beside* the title, never in how big it is.

Verified at 375×812, 768×1024 and desktop.

## 12. Running it

```bash
cd frontend && npm install
```

```bash
cd frontend && npm run dev
```

`VITE_API_BASE_URL` comes from `.env` (localhost:8000) or `.env.production` (Railway). The
backend must be running, and its `FRONTEND_ORIGIN` must match the frontend's origin or CORS
blocks every request.

**Local OAuth caveat:** Strava allows one callback domain per app. While it points at the
Railway domain, "Connect with Strava" cannot complete against a local backend. For local UI
work, mint a session cookie instead — print one from the backend venv with
`create_session_token(<athlete_id>)`, then in the browser console:
`document.cookie = "sgt_session=<token>; path=/"`.

## 13. Open questions

1. **Container ↔ store access** — this doc says containers reach stores *through hooks*, to
   keep the container rule to one thing. Confirm, or relax it to allow direct store use.
2. **Duplicated `/groups` fetch** — `SidebarContainer` and `GroupListContainer` each call
   `useGroups()`, so both fetch on mount. Harmless now; the fix is a groups store, once
   question 1 is settled.
3. **Where does the OAuth redirect land?** `FRONTEND_ORIGIN` + `?login=ok`, handled by the
   `/login` route, whose guard forwards an authenticated athlete on to `/recap` — or to the
   joined group when the invite flow added `&group=<id>`.
4. **Maps** — activity routes are drawn as a plain SVG path from the decoded polyline
   (`usePolyline` + `RouteMap`), with no tile layer and no map library. Dense traces
   (court sports, laps) switch to a thin semi-transparent stroke so overlapping passes read
   as density. If real basemap tiles are ever wanted, that means adding Leaflet/MapLibre.
