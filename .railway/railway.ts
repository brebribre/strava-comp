import { defineRailway, github, postgres, preserve, project, service } from "railway/iac";

export default defineRailway(() => {
  const db = postgres("postgres");

  const backend = service("backend", {
    source: github("brebribre/strava-comp"),
    // Monorepo: only build from backend/, ignore the frontend.
    rootDirectory: "backend",
    // Railway assigns $PORT at runtime; binding 0.0.0.0 is required to be reachable.
    start: "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    // A 200 here means the app booted AND reached Postgres, so a broken DB link
    // fails the deploy instead of going live.
    healthcheck: "/health",
    healthcheckTimeout: 60,
    env: {
      // Internal reference — stays correct if the database is recreated.
      DATABASE_URL: db.env.DATABASE_URL,

      BACKFILL_DAYS: "7",
      COOKIE_SECURE: "true",
      // app.bruderbande.com and api.bruderbande.com share a registrable domain, so the
      // session cookie is same-site and first-party — "lax" is correct and safer than
      // "none". (On *.up.railway.app it had to be "none", because up.railway.app is a
      // public suffix, which made the two hosts different sites and the cookie third-party.)
      COOKIE_SAMESITE: "lax",

      // Secrets live in the Railway dashboard, never in this file.
      // preserve() keeps whatever is already set there instead of overwriting it.
      STRAVA_CLIENT_ID: preserve(),
      STRAVA_CLIENT_SECRET: preserve(),
      SECRET_KEY: preserve(),
      STRAVA_VERIFY_TOKEN: preserve(),
      STRAVA_REDIRECT_URI: preserve(),
      FRONTEND_ORIGIN: preserve(),
    },
  });

  const frontend = service("frontend", {
    source: github("brebribre/strava-comp"),
    rootDirectory: "frontend",
    build: "npm run build",
    // `serve -s` falls back to index.html, which history-mode routes need — without it
    // /join/<code> and /groups/5/feed 404 on a direct visit or refresh.
    start: "npm run start",
    env: {
      // VITE_* variables are baked in at BUILD time, not read at runtime — changing this
      // requires a rebuild, not just a restart. Not a secret, so it's declared here rather
      // than left to the dashboard, where forgetting it would ship a build pointing at
      // localhost.
      VITE_API_BASE_URL: "https://api.bruderbande.com",
    },
  });

  return project("Strava Brothers", {
    resources: [backend, db, frontend],
  });
});
