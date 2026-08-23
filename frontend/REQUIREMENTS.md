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
| `GET /activities/{id}` | One activity in full: description, calories, splits, GPS polyline |
| `GET/PUT/DELETE /groups/{id}/target` | The group's training target |
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
| `/groups/:id/feed` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupFeedContainer` |
| `/groups/:id/summary` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupSummaryContainer` |
| `/groups/:id/target` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupTargetContainer` |
| `/groups/:id/settings` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `GroupSettingsContainer` |
| `/groups/:id/activities/:activityId` | `SidebarView` → `GroupView` | `SidebarContainer` + `GroupHeaderContainer` + `ActivityDetailContainer` |

`/groups/:id` redirects to the feed. **Two levels of nested `router-view`:** `SidebarView`
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

**Monochrome.** There is no accent colour: hierarchy comes from contrast, weight and fill.
All tokens live in `src/style.css` — components reference `bg-surface`, `text-ink-muted`,
`border-line` and so on, never a raw Tailwind palette colour like `slate-700`.

| Token group | Purpose |
|---|---|
| `canvas` / `surface` / `raised` | page → card → inset, in ascending contrast |
| `line` / `line-strong` | borders, and the border on hover |
| `ink` / `ink-muted` / `ink-subtle` / `ink-inverse` | text, and the "accent" fill |
| `--radius-sm…xl` (3–9px) | **subtle** corners; only avatars and swatches are rounder |
| `--duration-quick` (130ms) / `--duration-soft` (260ms), `--ease-out-soft` | one motion system |

**Dark mode overrides the CSS variables, not `@theme`.** Tailwind v4 hoists every `@theme`
block to `:root` regardless of any media query around it, so a `@theme` inside
`prefers-color-scheme: dark` applies unconditionally. Dark values are plain custom property
declarations on `:root` inside the media query.

**Motion is small and purposeful:**
- buttons and chips scale to `0.97` on press — the click should feel physical
- cards marked `interactive` lift 1px and darken their border on hover
- the tab underline scales in from the centre
- lists use `.animate-rise` (4px + fade), staggered up to four items
- everything is disabled under `prefers-reduced-motion: reduce`

**Charts** render to canvas and cannot read CSS variables, so `useSportColors` resolves the
palette in JS: a **tonal ramp** (dark→light, inverted for dark mode) assigned by position in
the sorted sport list, never hashed — hashing would drop adjacent stack segments onto
near-identical greys. Axis, grid and legend colours are passed explicitly per theme.

## 11b. Responsive rules

The app is used on phones as much as laptops, so **mobile is a first-class layout, not an
afterthought**.

- **Navigation**: below `lg`, the sidebar is an off-canvas drawer with a backdrop, opened
  from a top bar and closed automatically on navigation. From `lg` up it is static and in
  flow. State lives in `useUiStore` and is reached through `useSidebar()`.
- **No horizontal page scroll, ever.** Wide content (tables, charts) scrolls inside its own
  `overflow-x-auto` container. Check with
  `document.documentElement.scrollWidth === window.innerWidth`.
- **Tabs** scroll horizontally rather than wrapping (`overflow-x-auto whitespace-nowrap`).
- **Tables** keep `overflow-x-auto`; secondary detail (e.g. the per-sport list on the summary
  row) is `hidden sm:inline` rather than wrapping into a tall column.
- **Rows of actions** stack with `flex-col sm:flex-row`.
- Pixel-sized SVGs that CSS can't scale (the progress ring) read `useViewport()`.

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
3. **Where does the OAuth redirect land?** Currently `FRONTEND_ORIGIN` + `?login=ok`, handled
   by the `/login` route, whose guard forwards an authenticated athlete on to `/groups`.
4. **Maps** — activity routes are drawn as a plain SVG path from the decoded polyline
   (`usePolyline` + `RouteMap`), with no tile layer and no map library. Dense traces
   (court sports, laps) switch to a thin semi-transparent stroke so overlapping passes read
   as density. If real basemap tiles are ever wanted, that means adding Leaflet/MapLibre.
