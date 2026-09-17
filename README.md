# Fantasy Trade Evaluator

Propose a trade between two fantasy football teams and get back adjusted
weekly projections, a winner/loser verdict, and a written rationale — with
player headshots.

- **Frontend**: React + TypeScript + Tailwind (Vite)
- **Backend**: Python Flask. Holds the OpenAI API key server-side; the
  frontend never talks to OpenAI directly.
- **Data**: [Sleeper's free public API](https://docs.sleeper.com/) for
  player metadata, weekly projections, headshots, and trending players (no
  API key required).
- **LLM**: OpenAI Responses API, used only to adjust baseline projections for
  recent news and to write the trade verdict — it never invents baseline
  stats. Web search is used sparingly (see Cost controls below).
- **Database**: Postgres, used only for cost-control caching/quota state
  (verdict cache, per-player projection cache, daily eval quota). Nothing
  else in the app depends on it — leaderboards and player search work fine
  without it.

## Project structure

```
backend/    Flask API (Sleeper data adapter + OpenAI evaluation)
frontend/   React + TypeScript + Tailwind UI
```

## Setup

### 1. Database

The app needs a Postgres instance for cost-control caching (see below).
Point `DATABASE_URL` at any Postgres 15+ server; schema tables are created
automatically on first use (no separate migration step). For local dev with
Homebrew Postgres:

```bash
psql -d postgres -c "CREATE ROLE trade_app LOGIN PASSWORD 'trade_app_dev_password';"
psql -d postgres -c "CREATE DATABASE trade_evaluator OWNER trade_app;"
```

(Any other local or hosted Postgres works too — just set `DATABASE_URL`
accordingly in `backend/.env`.)

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-... and DATABASE_URL=...
```

Run the API server:

```bash
python run.py
```

The backend listens on `http://localhost:5001`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # optional — defaults to http://localhost:5001
npm run dev
```

The frontend runs on `http://localhost:5173` and talks to the Flask API via
`VITE_API_BASE_URL` (defaults to `http://localhost:5001`).

### 4. Use it

Open `http://localhost:5173`. Below the trade builder you'll see position
leaderboards (top scorers by position, season-to-date) by default. Search
for players to add to "Team A gives" and "Team B gives", then click
**Evaluate trade** — a fresh evaluation typically takes 5–15 seconds (or
10–30s if web search fires). Once a verdict comes back it replaces the
leaderboards in that space; use **← New trade** to clear the result and
bring the leaderboards back.

## Configuration

| Variable          | Where            | Purpose                                                                 |
| ------------------ | ---------------- | ------------------------------------------------------------------------ |
| `OPENAI_API_KEY`   | `backend/.env`   | Required (server demo key). Server-side only — never sent to the frontend. |
| `DATABASE_URL`     | `backend/.env`   | Required. Postgres connection string for cache/quota tables.            |
| `OPENAI_MODEL`     | `backend/.env`   | Optional. Defaults to `gpt-5.6-luna` (cheaper tier; see `backend/app/config.py`). |
| `OPENAI_REASONING_EFFORT` | `backend/.env` | Optional. Defaults to `low`.                                      |
| `OPENAI_MAX_TOOL_CALLS` | `backend/.env` | Optional. Caps web-search calls per evaluation; defaults to `1`.     |
| `FREE_EVALS_PER_USER_PER_DAY` | `backend/.env` | Optional. Daily quota per IP on the server key; defaults to `10`. |
| `EVAL_RATE_LIMIT`  | `backend/.env`   | Optional. Per-IP burst limit on `/api/evaluate`; defaults to `10 per minute`. |
| `NFL_SEASON`       | `backend/.env`   | Optional override if the auto-detected season is wrong.                 |
| `NFL_WEEK`         | `backend/.env`   | Optional override if the auto-detected week is wrong.                   |
| `VITE_API_BASE_URL`| `frontend/.env`  | Optional. Defaults to `http://localhost:5001`.                          |

### Cost controls

`/api/evaluate` is optimized in layers, cheapest checked first:

1. **Global verdict cache** (Postgres `verdict_cache`): identical trades
   (same players on each side regardless of order, same scoring format,
   same NFL week — pulled from `sleeper.app/v1/state/nfl`, hourly-cached)
   are served instantly from a cache shared across **every user**, no
   OpenAI call at all. The response carries `"cached": true` and the UI
   shows a "Cached — no API cost" pill.
2. **Per-player projection cache** (Postgres `player_proj_cache`): on a
   verdict-cache miss, any player already adjusted this week in some *other*
   trade (a player's news-driven adjustment doesn't depend on his trade
   partners) is reused as read-only context instead of being re-researched.
   Only genuinely new players are sent to the model; their results are
   written back after the call.
3. **Conditional web search**: the `web_search` tool is only attached when
   at least one new (non-cached) player is injured
   (`Questionable`/`Doubtful`/`Out`/`IR`/`PUP`) or on Sleeper's trending-add
   list. A trade of healthy, unremarkable starters skips search — and its
   fee — entirely. `max_tool_calls` caps it at one call when it does fire,
   backed by a system-prompt instruction to search at most once.
4. **Cheap model/reasoning + a compressed, byte-identical system prompt**
   (`backend/app/llm/evaluator.py`) for OpenAI's automatic prompt-caching
   discount, plus a compact (non-indented) JSON payload and 1–2 sentence
   caps on every rationale field.
5. **BYOK-ready**: `resolve_api_key()` takes the API key as a parameter
   (user's own key if the request includes one, else the server key) —
   nothing in the LLM call path reads a global/env key directly, so wiring
   up a real bring-your-own-key flow later is a small change.
6. **Guardrails**: a daily per-IP quota (`FREE_EVALS_PER_USER_PER_DAY`,
   server-key requests only — BYOK is exempt) backed by the Postgres
   `eval_quota` table, a per-IP rate limit on `/api/evaluate`
   (`EVAL_RATE_LIMIT`, via Flask-Limiter), and strict structured-payload
   validation (bounded name/team length, a fixed `injuryStatus` whitelist, a
   roster-size cap) so a client can never smuggle an arbitrary free-text
   prompt through to the model on the server's key.

There's no login system yet, so "per-user" above means per-IP — noted as a
known limitation, not a real identity system.

## How it works

1. **Data layer** (`backend/app/data/sleeper.py`): a provider-agnostic
   `SleeperProvider` fetches Sleeper's player metadata (~5MB) at most once a
   day, caching it to `backend/app/cache/players.json`. Weekly projections
   are cached per season/week and refreshed hourly. Player search and
   lookups always return a normalized `PlayerData` shape, so a future
   provider (or a Postgres-backed cache) can be swapped in without touching
   callers.
2. **LLM layer** (`backend/app/llm/evaluator.py`): sends only the players
   that need fresh adjustment to OpenAI's Responses API (already-adjusted
   players from the per-player cache go in as read-only context instead).
   The system prompt requires the model to *adjust* — never invent —
   baseline stats, grounded in real recent news, and to return only JSON
   matching the response schema. JSON parsing strips stray markdown fences
   and retries once on failure.
3. **Database layer** (`backend/app/db.py`): a small Postgres wrapper
   (connection pool + idempotent `CREATE TABLE IF NOT EXISTS` schema, run
   lazily on first use) backing the verdict cache, per-player projection
   cache, and daily quota counter described above.
4. **API** (`backend/app/routes.py`): `POST /api/evaluate` validates the
   request body (400 on bad input), checks the verdict cache, splits players
   into cached-context vs. needs-evaluation, enforces quota/rate limits,
   calls the LLM layer (500 with a clear message on LLM/parse failure),
   reassembles the full per-player breakdown, and writes both caches back.
   `GET /api/players/search?q=...` powers the frontend's player search.
   `GET /api/leaderboard?scoring=ppr` returns the top 10 season-to-date
   scorers per position, sourced from Sleeper's bulk stats endpoint and
   cached server-side (~hourly) so it's never recomputed per request.
5. **Frontend**: two team columns with player search/autocomplete, chips
   with headshots, a scoring-format selector, and — in the space below the
   builder — either the position leaderboards (default) or the trade verdict
   (after evaluating), toggled by a single `result` state value.

## Security

- `OPENAI_API_KEY` is only ever read server-side (`os.environ` via
  `python-dotenv`) and never appears in any frontend file or API response.
- `.env` files are gitignored; `.env.example` files document the required
  variables with no values.
- CORS is scoped to the `/api/*` routes; `FRONTEND_ORIGIN` restricts it to
  the deployed frontend's origin in production (defaults to `*` for local
  dev, where the Vite dev server needs to reach Flask with no extra config).

## Deployment

This is a two-service app (Flask backend + static frontend) plus Postgres —
it fits a traditional persistent-host platform (Railway, Render, Fly.io, a
VPS) better than a serverless-first one, since the backend keeps a
connection pool and an in-process rate limiter that both assume one
long-running process. Steps below are for Railway; Render's flow is nearly
identical (Web Service + Static Site + a managed Postgres instance) using
the same `backend/Procfile` and `frontend` build/start commands.

1. **Push to GitHub.** Create a repo on github.com, then:
   ```bash
   git remote add origin https://github.com/<you>/<repo>.git
   git branch -M main
   git push -u origin main
   ```
2. **Add Postgres.** In a new Railway project: "New" → "Database" →
   "PostgreSQL". Railway exposes its connection string as
   `${{Postgres.DATABASE_URL}}` for other services in the project to
   reference.
3. **Backend service.** "New" → "GitHub Repo" → this repo.
   - Root directory: `backend`
   - Railway auto-detects Python + `requirements.txt`; the start command
     comes from `backend/Procfile` (gunicorn, 2 workers, 90s timeout to
     cover slower web-search evaluations).
   - Variables: `OPENAI_API_KEY` (your key), `DATABASE_URL` (reference the
     Postgres service above), optionally `OPENAI_MODEL` /
     `FREE_EVALS_PER_USER_PER_DAY` / `EVAL_RATE_LIMIT` to override defaults.
   - Settings → Networking → Generate Domain. Note the resulting URL.
4. **Frontend service.** "New" → "GitHub Repo" → same repo, as a second
   service in the same project.
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Start command: `npm run start` (serves the built `dist/` via `serve`,
     reading Railway's injected `$PORT`)
   - Variables: `VITE_API_BASE_URL` = the backend URL from step 3.
   - Generate a domain for this service too.
5. **Lock down CORS.** Back on the backend service, set `FRONTEND_ORIGIN` to
   the frontend's URL from step 4 and redeploy, so `/api/*` only accepts
   requests from your deployed frontend (not `*`).
6. **Verify.** Open the frontend URL — search, leaderboards, and Evaluate
   trade should all work against the deployed backend and Postgres.

Postgres schema tables are created automatically on first `/api/evaluate`
call (`app/db.py`'s `ensure_schema()`), no migration step needed.
