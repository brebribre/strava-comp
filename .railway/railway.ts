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
      // Set to "none" only once the frontend is on a different domain than the API.
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

  return project("Strava Brothers", {
    resources: [backend, db],
  });
});
