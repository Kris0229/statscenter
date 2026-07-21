# BUILD_SPEC — 棒壘聯盟成績管理系統 (Softball/Baseball League Stats System)

> This document is the executable build specification for Claude Code.
> It defines the tech stack, data model (full DDL), API contracts, computation rules,
> and a phased, test-driven build plan. Each phase has an explicit Definition of Done (DoD)
> and verification steps. Build phases in order. Do not start a phase until the previous
> phase's DoD passes.
>
> Companion document: `棒壘聯盟成績管理系統規格書.md` (functional spec, in Traditional Chinese).
> When this document and the functional spec conflict, THIS document wins on technical detail;
> the functional spec wins on business intent.

- Version: 1.2
- Date: 2026-07-11
- Data-entry model: single-game aggregate (NOT play-by-play)
- Data-entry context: post-game desktop entry, columns aligned to RTBA scoresheet
- v1.1: added §1.4 deployment environments (local Docker vs. free Supabase/Render/Vercel demo)
- v1.2: multi-tenant — added `super_admin` role, `leagues` table, `league_id` tenancy across all entities, §6.0 league-management API, and new Phase 1.5 (system admin & tenant isolation)

---

## 0. How Claude Code should use this document

1. Work phase by phase (Phase 0 → 7). Each phase is independently shippable and testable.
2. At the end of every phase, run the phase's **Verification** block and confirm the **DoD** checklist before proceeding.
3. Write tests as you go — every computation rule in §4 and every API endpoint in §6 must have at least one automated test.
4. Prefer clarity over cleverness. This is an internal league tool, not high-scale SaaS.
5. If a decision is ambiguous, follow the **Assumptions** in §1.3 and leave a `// TODO(confirm):` comment rather than blocking.
6. Do not invent stats columns. The stat set is fixed in §3 and §4; adding/removing columns requires a spec change.

---

## 1. Tech stack & project layout

### 1.1 Stack (fixed)
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.x (ORM), Alembic (migrations), Pydantic v2
- DB: PostgreSQL 15+ (dev may use Docker). Rationale: window functions + materialized views for leaderboards.
- Auth: JWT (access + refresh), `passlib[bcrypt]` for password hashing, role-based access control
- Frontend: React 18 + Vite + TypeScript, TanStack Query for data fetching, plain CSS or a light UI lib (no heavy design system needed)
- Excel: `openpyxl` (roster import/export), `pandas` optional for validation
- Testing: `pytest` + `httpx` (API), `pytest-asyncio`; frontend `vitest` + React Testing Library
- File storage: local disk in dev (`/media`), S3-compatible in prod (abstract behind a `StorageBackend` interface)

### 1.2 Repository layout
```
/backend
  /app
    /api          # FastAPI routers, one module per resource
    /core         # config, security, dependencies
    /db           # session, base, models
    /models       # SQLAlchemy models
    /schemas      # Pydantic request/response models
    /services     # business logic: stats calc, validation, aggregation
    /migrations   # Alembic
    main.py
  /tests
  pyproject.toml
/frontend
  /src
    /api          # typed API client
    /components
    /pages
    /lib          # stat formatting helpers (mirror backend §4)
  package.json
/docker
  docker-compose.yml   # postgres + backend + frontend for local dev
README.md
```

### 1.3 Assumptions (used when spec is silent)
- League type: softball, 7 regulation innings (`innings_per_game = 7`). Parameterized per season.
- **Multi-tenant: the system hosts multiple leagues.** Tenancy is enforced by a `league_id` foreign key on every business entity (NOT separate databases). Current isolation model: **fully isolated** — teams, players, games, and leaderboards never cross leagues; every query filters by the caller's `league_id`.
- **Future-proofing (do NOT build now, but don't preclude):** cross-league players may be needed later. To keep that door open, model a player as `players` (roster membership within one league) that MAY later reference a shared `persons` table. For now `players` is self-contained; add a nullable `person_id` column reserved for future use, left null.
- One league has multiple seasons. No cross-team players within a season (single roster membership per league).
- Video stored as external link (YouTube) in MVP to avoid storage cost; photos stored via StorageBackend.
- Language: UI defaults to Traditional Chinese (zh-Hant). API is English-keyed JSON.
- Timezone: Asia/Taipei. Store timestamps in UTC, present in local.

### 1.4 Deployment environments (local vs. free demo)

> Two environments. The code must not change between them — everything environment-specific
> reads from env vars (`DATABASE_URL`, `STORAGE_*`, `CORS_ORIGINS`, `JWT_SECRET`, ...).
> Claude Code: produce a `.env.example` for both backend and frontend, a `render.yaml` for the
> backend service, and a `vercel.json` (or Netlify equivalent) for the frontend, so the demo
> environment can be stood up without hand-configuration.

**A. Local development** — Docker Compose (`/docker/docker-compose.yml`): `postgres` + `backend` + `frontend`. This is the source of truth for dev/test; all `pytest`/`vitest` run here.

**B. Free demo/UAT environment** — for letting the client click through and give feedback. Zero-cost, managed services. NOT a long-term production target (free tiers are shrinking and idle-suspend). Recommended stack (verified 2026-07):

| Layer | Service | Free-tier limit (approx., 2026) | Notes / caveats |
|---|---|---|---|
| Database + file storage | **Supabase** | 500 MB Postgres, 1 GB file storage, auth (50K MAU) | Standard Postgres → our DDL, materialized views, window functions all work as-is. Free project **auto-pauses when idle** — log in occasionally during the test window. |
| Backend API (FastAPI) | **Render** (free web service) | 512 MB RAM, 0.1 CPU | **Spins down after ~15 min idle; first request then takes ~30–50s to wake.** Acceptable for click-through demos. Upgrade to Starter (~US$7/mo) to remove sleep. |
| Frontend (React/Vite) | **Vercel** or **Netlify** | Generous static hosting, no sleep | Standard split: static frontend on Vercel/Netlify, API elsewhere. |

Why not others: Fly.io no longer offers a free tier for new users (2-hour trial only); Railway removed its permanent free tier (post-trial credit is negligible). Render is the last mainstream PaaS with a real free web-service tier, hence the pick.

**Simpler variant (fewer services):** let Supabase provide database + storage + **auth** (skip hand-rolled JWT for the demo); FastAPI then only serves stats computation, validation, and aggregation. Trade-off: mild Supabase coupling. If chosen, keep the JWT code path behind the same `AuthProvider` interface so switching back for production is a config change, not a rewrite.

**Environment variables (both envs read these):**
- Backend: `DATABASE_URL`, `JWT_SECRET`, `JWT_ACCESS_TTL`, `JWT_REFRESH_TTL`, `CORS_ORIGINS`, `STORAGE_BACKEND` (`local|supabase|s3`), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (if storage=supabase)
- Frontend: `VITE_API_BASE_URL`

**StorageBackend mapping:** local disk in dev → Supabase Storage in demo → S3-compatible in production. All behind the `StorageBackend` interface (§1.1); the concrete class is selected by `STORAGE_BACKEND`.

**Migration path to production (post-UAT):** when the client commits, move DB to Supabase Pro (~US$25/mo) or self-hosted Postgres, backend to Render Starter or a small VPS, keep frontend on Vercel/Netlify. Because everything is env-driven, this is a redeploy, not a rewrite. Data migrates via `pg_dump`/`pg_restore` (standard Postgres both ends).

---

## 2. Roles & permissions (enforce server-side)

| Role | Code | Scope | Capabilities |
|---|---|---|---|
| System admin | `super_admin` | Global (all leagues) | Create/suspend leagues, create the first `admin` account per league, manage system-wide settings. Does NOT do day-to-day league operations. |
| League admin | `admin` | One league | Full within own league: teams, roster import, score entry, review roster requests, media, reports, league params, accounts |
| Team captain | `power` | One team (in one league) | Request roster changes (needs admin approval), view team/player stats, upload media |
| Player | `user` | Self (in one league) | View stats/leaderboards/boxscores, upload media, update own avatar |

Tenancy & rules:
- **Every business entity carries `league_id`. Every query filters by the caller's `league_id`** — enforce in a base query dependency, not ad hoc per endpoint. A user (except `super_admin`) belongs to exactly one league; their token carries `league_id` and it is applied automatically.
- `super_admin` is the ONLY role that operates across leagues, and only for league lifecycle (create/suspend) + bootstrapping a league's first `admin`. It does not enter scores or manage rosters.
- New leagues are created **manually by `super_admin` only** (no self-service application flow in scope).
- Every mutating endpoint checks role. Enforce in a FastAPI dependency (`require_role(...)`), never trust the client.
- Cross-tenant access is a security defect: an `admin` of league A must get 404 (not 403 — don't leak existence) when touching league B's resources.
- `power` roster mutations create a `roster_change_request` (status `pending`) — they do NOT mutate `players` directly.
- `user` may only mutate `players.photo` for their own linked `player` row.
- Deleting a player is a soft delete (`status = 'left'`); historical stat lines are retained.

---

## 3. Data model — full DDL

> Generate Alembic migrations from these. IP is stored as integer `outs` (1 inning = 3 outs); never store float innings.
> All monetary/rate stats are COMPUTED, never stored.

```sql
-- === tenancy: leagues (top level) ===
CREATE TYPE entity_status AS ENUM ('active', 'inactive');

CREATE TABLE leagues (
  id         BIGSERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  slug       TEXT UNIQUE NOT NULL,        -- URL-safe key, e.g. 'rtba'
  logo_url   TEXT,
  status     entity_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- === accounts & orgs ===
-- super_admin: global, league lifecycle only. admin/power/user: scoped to one league.
CREATE TYPE user_role AS ENUM ('super_admin', 'admin', 'power', 'user');

CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  league_id     BIGINT REFERENCES leagues(id),        -- NULL only for super_admin
  email         CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name  TEXT NOT NULL,
  role          user_role NOT NULL DEFAULT 'user',
  status        entity_status NOT NULL DEFAULT 'active',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((role = 'super_admin' AND league_id IS NULL)
      OR (role <> 'super_admin' AND league_id IS NOT NULL))
);

CREATE TABLE seasons (
  id                  BIGSERIAL PRIMARY KEY,
  league_id           BIGINT NOT NULL REFERENCES leagues(id),
  year                INT NOT NULL,
  name                TEXT NOT NULL,
  innings_per_game    INT NOT NULL DEFAULT 7,
  pa_qualifier_factor NUMERIC(4,2) NOT NULL DEFAULT 2.00,  -- min PA = team games * factor
  ip_qualifier_factor NUMERIC(4,2) NOT NULL DEFAULT 1.00,  -- min IP = team games * factor
  is_current          BOOLEAN NOT NULL DEFAULT false,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teams (
  id              BIGSERIAL PRIMARY KEY,
  league_id       BIGINT NOT NULL REFERENCES leagues(id),
  name            TEXT NOT NULL,
  logo_url        TEXT,
  captain_user_id BIGINT REFERENCES users(id),
  status          entity_status NOT NULL DEFAULT 'active',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (league_id, name)   -- team name unique within a league, not globally
);

CREATE TYPE player_status AS ENUM ('active', 'left');

CREATE TABLE players (
  id         BIGSERIAL PRIMARY KEY,
  league_id  BIGINT NOT NULL REFERENCES leagues(id),
  team_id    BIGINT NOT NULL REFERENCES teams(id),
  user_id    BIGINT REFERENCES users(id),          -- nullable: not every player has an account
  person_id  BIGINT,                                -- RESERVED for future cross-league identity; keep NULL for now
  name       TEXT NOT NULL,
  number     SMALLINT NOT NULL CHECK (number BETWEEN 0 AND 99),
  positions  TEXT,                                  -- CSV e.g. 'P,SS'
  bats       CHAR(1) CHECK (bats IN ('R','L','S')),
  throws     CHAR(1) CHECK (throws IN ('R','L')),
  photo_url  TEXT,
  status     player_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (team_id, number) DEFERRABLE INITIALLY DEFERRED  -- allow swaps within a txn
);

-- === roster change workflow ===
CREATE TYPE roster_req_type AS ENUM ('rename', 'renumber', 'add', 'remove');
CREATE TYPE roster_req_status AS ENUM ('pending', 'approved', 'rejected');

CREATE TABLE roster_change_requests (
  id           BIGSERIAL PRIMARY KEY,
  league_id    BIGINT NOT NULL REFERENCES leagues(id),
  team_id      BIGINT NOT NULL REFERENCES teams(id),
  type         roster_req_type NOT NULL,
  payload      JSONB NOT NULL,          -- {player_id?, name?, number?, ...}
  status       roster_req_status NOT NULL DEFAULT 'pending',
  reason       TEXT,                    -- rejection reason
  requested_by BIGINT NOT NULL REFERENCES users(id),
  reviewed_by  BIGINT REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at  TIMESTAMPTZ
);

-- === games ===
CREATE TYPE game_status AS ENUM ('scheduled','in_progress','final','postponed','cancelled');

CREATE TABLE games (
  id            BIGSERIAL PRIMARY KEY,
  league_id     BIGINT NOT NULL REFERENCES leagues(id),
  season_id     BIGINT NOT NULL REFERENCES seasons(id),
  game_date     DATE NOT NULL,
  start_time    TIME,
  venue         TEXT,
  game_type     TEXT NOT NULL DEFAULT 'regular',   -- regular | playoff
  home_team_id  BIGINT NOT NULL REFERENCES teams(id),
  away_team_id  BIGINT NOT NULL REFERENCES teams(id),
  status        game_status NOT NULL DEFAULT 'scheduled',
  line_score    JSONB,   -- {"home":[1,0,3,...],"away":[...],"home_e":0,"away_e":1}
  code          TEXT,    -- e.g. 'G6'
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finalized_at  TIMESTAMPTZ,
  CHECK (home_team_id <> away_team_id)
);

-- === stat lines (single-game aggregate, RTBA-aligned) ===
CREATE TABLE batting_lines (
  id         BIGSERIAL PRIMARY KEY,
  game_id    BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  player_id  BIGINT NOT NULL REFERENCES players(id),
  bat_order  SMALLINT,       -- 1..N; substitutes share order with sub_index
  sub_index  SMALLINT NOT NULL DEFAULT 0,
  pos        TEXT,
  -- PA breakdown (RTBA): pa = ab + sh + sf + bb + hp + io + tie
  pa   SMALLINT NOT NULL DEFAULT 0,
  ab   SMALLINT NOT NULL DEFAULT 0,
  sh   SMALLINT NOT NULL DEFAULT 0,
  sf   SMALLINT NOT NULL DEFAULT 0,
  bb   SMALLINT NOT NULL DEFAULT 0,
  hp   SMALLINT NOT NULL DEFAULT 0,   -- HBP
  io   SMALLINT NOT NULL DEFAULT 0,   -- interference / non-AB reach (confirm w/ RTBA)
  tie  SMALLINT NOT NULL DEFAULT 0,   -- other special reach (confirm w/ RTBA)
  -- results
  r    SMALLINT NOT NULL DEFAULT 0,
  h    SMALLINT NOT NULL DEFAULT 0,
  b2   SMALLINT NOT NULL DEFAULT 0,
  b3   SMALLINT NOT NULL DEFAULT 0,
  hr   SMALLINT NOT NULL DEFAULT 0,
  rbi  SMALLINT NOT NULL DEFAULT 0,
  so   SMALLINT NOT NULL DEFAULT 0,
  sb   SMALLINT NOT NULL DEFAULT 0,
  cs   SMALLINT NOT NULL DEFAULT 0,
  gidp SMALLINT NOT NULL DEFAULT 0,
  e    SMALLINT NOT NULL DEFAULT 0,
  UNIQUE (game_id, player_id),
  CHECK (h >= b2 + b3 + hr),
  CHECK (pa = ab + sh + sf + bb + hp + io + tie)
);

CREATE TYPE pitch_decision AS ENUM ('W','L','SV','BS','HLD','SVO','none');

CREATE TABLE pitching_lines (
  id        BIGSERIAL PRIMARY KEY,
  game_id   BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  player_id BIGINT NOT NULL REFERENCES players(id),
  seq       SMALLINT NOT NULL DEFAULT 1,   -- appearance order
  decision  pitch_decision NOT NULL DEFAULT 'none',
  outs      SMALLINT NOT NULL DEFAULT 0,   -- IP as outs; 1 inning = 3
  np        SMALLINT NOT NULL DEFAULT 0,   -- number of pitches
  bf        SMALLINT NOT NULL DEFAULT 0,   -- batters faced
  ab        SMALLINT NOT NULL DEFAULT 0,   -- opponent AB
  h         SMALLINT NOT NULL DEFAULT 0,
  hr        SMALLINT NOT NULL DEFAULT 0,
  bb        SMALLINT NOT NULL DEFAULT 0,
  hp        SMALLINT NOT NULL DEFAULT 0,
  so        SMALLINT NOT NULL DEFAULT 0,
  r         SMALLINT NOT NULL DEFAULT 0,
  er        SMALLINT NOT NULL DEFAULT 0,
  wp        SMALLINT NOT NULL DEFAULT 0,
  gs        BOOLEAN NOT NULL DEFAULT false,
  cg        BOOLEAN NOT NULL DEFAULT false,
  sho       BOOLEAN NOT NULL DEFAULT false,
  sv        BOOLEAN NOT NULL DEFAULT false,
  svo       BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (game_id, player_id, seq),
  CHECK (er <= r)
);

-- === media & reports ===
CREATE TYPE media_type AS ENUM ('photo','video','link');
CREATE TABLE media (
  id          BIGSERIAL PRIMARY KEY,
  game_id     BIGINT REFERENCES games(id),
  player_id   BIGINT REFERENCES players(id),
  uploader_id BIGINT NOT NULL REFERENCES users(id),
  type        media_type NOT NULL,
  url         TEXT NOT NULL,
  status      entity_status NOT NULL DEFAULT 'active',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
  id             BIGSERIAL PRIMARY KEY,
  game_id        BIGINT NOT NULL REFERENCES games(id),
  title          TEXT NOT NULL,
  content        TEXT,
  cover_media_id BIGINT REFERENCES media(id),
  author_id      BIGINT NOT NULL REFERENCES users(id),
  published_at   TIMESTAMPTZ
);

CREATE TABLE audit_logs (
  id         BIGSERIAL PRIMARY KEY,
  entity     TEXT NOT NULL,
  entity_id  BIGINT NOT NULL,
  action     TEXT NOT NULL,
  before     JSONB,
  after      JSONB,
  actor_id   BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_batting_game ON batting_lines(game_id);
CREATE INDEX idx_batting_player ON batting_lines(player_id);
CREATE INDEX idx_pitching_game ON pitching_lines(game_id);
CREATE INDEX idx_pitching_player ON pitching_lines(player_id);
CREATE INDEX idx_games_season ON games(season_id, status);
-- tenancy indexes (every league-scoped list query filters on league_id)
CREATE INDEX idx_users_league ON users(league_id);
CREATE INDEX idx_teams_league ON teams(league_id);
CREATE INDEX idx_players_league ON players(league_id);
CREATE INDEX idx_seasons_league ON seasons(league_id);
CREATE INDEX idx_games_league ON games(league_id, status);
```

> Note: `media` and `reports` derive their league via `game_id → games.league_id` (JOIN-filter), so they don't carry a redundant `league_id`. `audit_logs` is global (records `super_admin` actions too) and stores `league_id` in its `after`/`before` JSON when applicable.

### 3.1 Leaderboard aggregation (materialized views)
Only lines from `games.status = 'final'` count. Refresh on finalize (§6.4) or via `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

```sql
CREATE MATERIALIZED VIEW mv_batting_season AS
SELECT p.id AS player_id, g.league_id, g.season_id, p.team_id,
       COUNT(DISTINCT bl.game_id) AS g,
       SUM(bl.pa) pa, SUM(bl.ab) ab, SUM(bl.r) r, SUM(bl.h) h,
       SUM(bl.b2) b2, SUM(bl.b3) b3, SUM(bl.hr) hr, SUM(bl.rbi) rbi,
       SUM(bl.bb) bb, SUM(bl.hp) hp, SUM(bl.sf) sf, SUM(bl.sh) sh,
       SUM(bl.so) so, SUM(bl.sb) sb, SUM(bl.cs) cs
FROM batting_lines bl
JOIN games g   ON g.id = bl.game_id AND g.status = 'final'
JOIN players p ON p.id = bl.player_id
GROUP BY p.id, g.league_id, g.season_id, p.team_id;

CREATE MATERIALIZED VIEW mv_pitching_season AS
SELECT p.id AS player_id, g.league_id, g.season_id, p.team_id,
       COUNT(DISTINCT pl.game_id) AS g,
       SUM(CASE WHEN pl.gs THEN 1 ELSE 0 END) gs,
       SUM(CASE WHEN pl.decision='W' THEN 1 ELSE 0 END) w,
       SUM(CASE WHEN pl.decision='L' THEN 1 ELSE 0 END) l,
       SUM(CASE WHEN pl.decision='SV' THEN 1 ELSE 0 END) sv,
       SUM(CASE WHEN pl.cg THEN 1 ELSE 0 END) cg,
       SUM(CASE WHEN pl.sho THEN 1 ELSE 0 END) sho,
       SUM(pl.outs) outs, SUM(pl.np) np, SUM(pl.bf) bf, SUM(pl.ab) ab,
       SUM(pl.h) h, SUM(pl.hr) hr, SUM(pl.bb) bb, SUM(pl.hp) hp,
       SUM(pl.so) so, SUM(pl.r) r, SUM(pl.er) er
FROM pitching_lines pl
JOIN games g   ON g.id = pl.game_id AND g.status = 'final'
JOIN players p ON p.id = pl.player_id
GROUP BY p.id, g.league_id, g.season_id, p.team_id;
```

> Leaderboard queries filter these views by `league_id` (+ optional `season_id`, `team_id`).

---

## 4. Computation rules (must have unit tests)

> Implement in `services/stats.py`. Frontend mirrors formatting only, never recomputes authoritative values.
> Guard every division by zero → return `None`/`null`, display as `—`.

| Stat | Formula | Notes |
|---|---|---|
| AVG | `h / ab` | 3 decimals, drop leading 0 → `.311` |
| OBP | `(h + bb + hp) / (ab + bb + hp + sf)` | denominator excludes SH |
| SLG | `tb / ab`, `tb = (h - b2 - b3 - hr) + 2*b2 + 3*b3 + 4*hr` | singles = h−2B−3B−HR |
| OPS | `obp + slg` | |
| IP (display) | `outs // 3` + `.` + `outs % 3` | e.g. 22 outs → `7.1` |
| ERA | `er * innings_per_game * 3 / outs` | uses season `innings_per_game`; NOT hardcoded 9 |
| WHIP | `(bb + h) / (outs / 3)` | |
| OppAVG | `h / ab` (pitching_lines.ab) | opponent batting avg |
| Qualified (bat) | `pa >= ceil(team_games * pa_qualifier_factor)` | for rate-stat leaderboards |
| Qualified (pit) | `outs/3 >= team_games * ip_qualifier_factor` | |

Rounding: all displayed numbers pass through explicit rounding. Rate stats to 3 decimals (AVG/OBP/SLG/OPS), ERA/WHIP to 2 decimals.

### 4.1 Validation rules (entry-time, block finalize)
Per batting line: `pa = ab+sh+sf+bb+hp+io+tie`; `h >= b2+b3+hr`.
Per pitching line: `er <= r`.
Per game (on finalize):
- Sum(home batting `r`) == home line_score total; same for away.
- Sum(away pitching `r`) == home total runs; same swapped.
- Sum(both teams pitching `outs`) ≈ game outs (allow walk-off / mercy short innings → warn, not block).
- RTBA cross-check per team: `Σr + LOB + PO == Σ(pa消化)` where PO derives from outs. Provide LOB/PO inputs; warn if mismatch.

---

## 5. Excel roster import (Phase 2)
- Template columns (sheet `roster`): `number, name, positions, bats_throws, email, phone, birthdate`
- Flow: upload → parse with openpyxl → validate each row → return preview `{valid_rows, errors:[{row, field, msg}]}` → client confirms → commit.
- Modes: `append` | `replace` (replace requires `confirm=true`).
- Validation: number 0–99 unique within team; name required; email format; dedupe by number.
- Provide `GET /teams/{id}/roster/template.xlsx` to download the blank template.

---

## 6. API contract (REST, JSON, `/api/v1`)

Auth: `POST /auth/login` → `{access_token, refresh_token}`; `POST /auth/refresh`. Bearer token on all others.
The access token carries `role` and (for non-super_admin) `league_id`. **All league-scoped endpoints implicitly filter by the token's `league_id`** — clients never pass `league_id` on those; the server derives it. Cross-tenant access → 404.
Error shape: `{"detail": "...", "code": "..."}`. Use 401/403/404/409/422 appropriately.

### 6.0 System admin — league management (super_admin only)
```
GET    /admin/leagues                       list all leagues
POST   /admin/leagues              (super)  {name, slug, logo_url?}  create league
PATCH  /admin/leagues/{id}         (super)  update / suspend (status)
POST   /admin/leagues/{id}/admins  (super)  bootstrap a league's first admin {email, display_name, password}
```
`super_admin` is created by a one-off bootstrap script/seed (not via API). These endpoints are the ONLY ones where `league_id` is passed explicitly. All other roles never see this router.

### 6.1 Accounts & teams (league-scoped: league_id from token)
```
POST   /auth/login
POST   /auth/refresh
GET    /me
GET    /teams
POST   /teams                      (admin)  {name, logo_url?, captain_user_id?}
GET    /teams/{id}
PATCH  /teams/{id}                 (admin)
GET    /teams/{id}/players
POST   /teams/{id}/players         (admin)  single manual add
POST   /teams/{id}/roster/import   (admin)  multipart xlsx, ?mode=append|replace&confirm=
GET    /teams/{id}/roster/template.xlsx
PATCH  /players/{id}/photo         (owner|admin) avatar update
```

### 6.2 Roster change workflow
```
POST   /teams/{id}/roster-requests (power)  {type, payload}
GET    /roster-requests            (admin: all | power: own team)
POST   /roster-requests/{id}/approve (admin)
POST   /roster-requests/{id}/reject  (admin) {reason}
```

### 6.3 Games & score entry
```
GET    /games?season_id=&team_id=&status=
POST   /games                      (admin)
GET    /games/{id}
PATCH  /games/{id}                 (admin)  line_score, status, meta
PUT    /games/{id}/batting         (admin)  {team_id, lines:[BattingLine...]}  upsert whole team
PUT    /games/{id}/pitching        (admin)  {team_id, lines:[PitchingLine...]}
POST   /games/{id}/validate        (admin)  returns {ok, checks:[{name, ok, detail}]}
POST   /games/{id}/finalize        (admin)  runs validate; if ok → status=final, refresh MVs, write audit
GET    /games/{id}/boxscore                 computed boxscore payload (see §6.5)
```

### 6.4 Leaderboards & records
```
GET /leaderboards/batting?season_id=&team_id=&sort=hr&order=desc&qualified=true&limit=&offset=
GET /leaderboards/pitching?season_id=&team_id=&sort=era&order=asc&qualified=true
GET /players/{id}/stats?season_id=            career + per-season + game log
GET /players/{id}/gamelog?season_id=
```
`sort` accepts any display column (hr, avg, obp, ops, so, era, whip, w, sv, ...). Server computes rate stats and applies `qualified` filter for rate-stat sorts.

### 6.5 Boxscore payload (shape)
```json
{
  "game": {"id":..,"date":..,"venue":..,"code":"G6","status":"final"},
  "line_score": {"away":[..7 innings..],"home":[..],
                 "away_totals":{"r":15,"h":22,"e":1},"home_totals":{...}},
  "away": {"team":{...},
    "batting":[{"order":1,"sub":0,"name":"彭曜威","pos":"CF",
                "ab":4,"r":1,"h":2,"rbi":1,"bb":0,"so":1,"avg":".333"}, ...],
    "batting_notes":{"2B":[...],"3B":[...],"HR":[...],"SB":[...],"LOB":9},
    "pitching":[{"name":"李耀明","ip":"7.0","h":9,"r":3,"er":3,"bb":4,"so":10,
                 "hr":0,"era":"3.86","decision":"W"}, ...]},
  "home": {...}
}
```

---

## 7. Phased build plan (build in order)

Each phase: implement → write tests → run **Verification** → check **DoD**.

### Phase 0 — Scaffold & infra
- Create repo layout (§1.2), Docker compose (postgres + backend + frontend), FastAPI hello, Vite app.
- Alembic initialized; `/api/v1/health` returns `{status:"ok"}`.
- Produce deploy artifacts per §1.4: `.env.example` (backend + frontend), `render.yaml` (backend), `vercel.json` or `netlify.toml` (frontend). All config via env vars — no hardcoded URLs/secrets.
- **Verification:** `docker compose up` boots all 3; `curl /api/v1/health` → 200; frontend loads blank page hitting health endpoint; a fresh clone + `.env` copy runs with no code edits.
- **DoD:** clean boot from zero, README documents both local (Docker) and demo (Supabase/Render/Vercel) setup, CI runs `pytest` (empty pass), deploy artifacts present and reference only env vars.

### Phase 1 — Data model & migrations
- Implement all §3 tables + enums + constraints + indexes as SQLAlchemy models and one Alembic migration. Include `leagues` and the `league_id` FKs / tenancy CHECK on `users`.
- Seed script: 1 `super_admin`; 2 leagues each with 1 `admin`, 1 season, 2 teams, ~9 players.
- **Verification:** `alembic upgrade head` succeeds on empty DB; `alembic downgrade base` then `upgrade head` is clean; seed runs; insert a batting_line violating `pa = ab+...` is rejected by DB CHECK (test); inserting a non-super_admin user with NULL `league_id` is rejected by the tenancy CHECK (test).
- **DoD:** schema matches §3 exactly; all CHECK constraints enforced (incl. tenancy CHECK); seed creates 2 isolated leagues; seed idempotent.

### Phase 1.5 — System admin & tenant isolation
- Bootstrap script to create the initial `super_admin` (env-driven credentials, not via API).
- `super_admin` league-management endpoints (§6.0): list/create/suspend leagues, bootstrap a league's first `admin`.
- Tenant-scoping dependency: derive `league_id` from token and inject into every league-scoped query; `super_admin` bypasses only on the `/admin/leagues` router.
- **Verification (tests):**
  - `super_admin` creates league B + its admin; new admin can log in scoped to B.
  - `admin` of league A calling `/admin/leagues` → 403.
  - `admin` of A requesting a team that belongs to B → 404 (not 403 — no existence leak).
  - Leaderboard/teams/players lists for A never include B's rows even with a forged `league_id` query param.
- **DoD:** every league-scoped list is provably filtered by token `league_id`; a cross-tenant read test exists for teams, players, games, and leaderboards; `super_admin` cannot enter scores or manage rosters (no such routes exposed to it).

### Phase 2 — Auth, accounts, teams, roster (incl. Excel)
- JWT login/refresh, `require_role` dependency, password hashing.
- Team CRUD (admin), manual player add, `PATCH /players/{id}/photo` (owner/admin).
- Excel import (§5): template download, upload → preview → commit, append/replace.
- Roster change workflow (§6.2): power creates request, admin approves/rejects, approval mutates players + writes audit_log.
- **Verification (tests):**
  - `power` calling `POST /teams` → 403; `admin` → 201.
  - Import a 9-row valid xlsx → 9 players; import with duplicate number → error rows returned, nothing committed.
  - `power` submits rename request → players unchanged; admin approves → player renamed + audit row exists.
  - `user` updates own photo → 200; updates another player's photo → 403.
- **DoD:** all permission matrix rows (§2) covered by a test; import round-trips template.

### Phase 3 — Score entry + validation + finalize
- Game CRUD, `PUT /games/{id}/batting|pitching` (whole-team upsert), line_score patch.
- `services/stats.py` implements all §4 formulas + §4.1 validations, fully unit-tested.
- `POST /validate` returns structured checks; `POST /finalize` blocks on failure, sets `final`, writes `finalized_at`, refreshes MVs, writes audit.
- **Verification (tests):**
  - Load the RTBA sample game (運動家 vs 巨人, G6) as a fixture; batting `pa=ab+sh+sf+bb+hp+io+tie` holds for all 9; finalize succeeds.
  - Mutate one batter's `r` so team R ≠ line_score → `/validate` returns that check `ok:false`; `/finalize` → 409.
  - Unit tests for AVG/OBP/SLG/OPS/ERA/WHIP with known inputs (include a divide-by-zero → null case).
  - ERA uses season innings_per_game (test 7-inning vs 9-inning give different ERA for same line).
- **DoD:** every formula in §4 has ≥1 passing test; finalize is transactional (partial failure rolls back).

### Phase 4 — Leaderboards & player records
- Materialized views (§3.1); leaderboard endpoints with sort/order/qualified/pagination.
- Rate-stat sorts apply the qualifier filter (min PA / min IP) by default, toggleable.
- Player stats: career + per-season + game log.
- **Verification (tests):**
  - Seed 2 finalized games; `GET /leaderboards/batting?sort=hr&order=desc` returns players HR-descending.
  - `sort=avg&qualified=true` hides a player below min PA; `qualified=false` shows them.
  - Ties share rank; changing `order` flips direction.
  - `GET /players/{id}/gamelog` returns one row per finalized game with that game's line.
- **DoD:** leaderboard query < 500ms on ~1k lines; every sortable column works; qualifier math matches §4.

### Phase 5 — Boxscore
- `GET /games/{id}/boxscore` returns §6.5 shape; running season AVG shown per batter (as-of that game).
- Frontend boxscore page mirroring MLB Gameday layout: line score, both batting tables, batting notes (2B/3B/HR/SB/LOB), both pitching tables with W/L/SV.
- **Verification:** boxscore of the RTBA sample renders; totals row equals line_score totals; W goes to 李耀明.
- **DoD:** printable view; shareable URL; numbers reconcile with line_score.

### Phase 6 — Score-entry UI
- React grid entry screen (post-game desktop), columns aligned to RTBA order (PA breakdown block + results block; pitching with NP/BF/AB).
- Live validation mirrors §4.1: row highlights on `pa` mismatch / `h<2B+3B+HR`; footer shows the R+LOB+PO check; finalize disabled until server `/validate` passes.
- Keyboard Tab/arrow navigation across cells.
- **Verification:** entering the RTBA sample and hitting finalize creates a final game; introducing a PA-breakdown error blocks finalize and highlights the row.
- **DoD:** a scorer can enter one full game from the paper sheet without leaving the keyboard.

### Phase 7 — Media & reports
- Photo upload via StorageBackend (local dev), video as YouTube link; associate to game/player.
- Admin report editor: auto-fill score + W/L pitcher + highlights (HR, multi-hit, 10+ SO); publish → public report page.
- Admin can hide media; uploader can delete own.
- **Verification:** upload photo → appears on game media wall; generate report → highlights list is correct for the sample game; `power`/`user` cannot publish reports.
- **DoD:** media permissions enforced; report page renders with cover + body + linked boxscore.

---

## 8. Non-functional requirements
- Security: HTTPS, server-side RBAC on every mutation, upload MIME whitelist, PII (email/phone) visible only to admin + the owner.
- Audit: roster changes and post-finalize edits write `audit_logs` (before/after).
- Performance: leaderboard < 2s (MV + index); finalize recompute < 5s.
- Backups: nightly DB dump; media on object storage.
- i18n: UI zh-Hant; keep user-facing strings in a single resource file.

## 9. Open items (leave TODO(confirm), don't block)
1. RTBA `io` / `tie` exact definitions → confirm with league; affects PA breakdown + OBP denominator.
2. League baseball vs softball & innings_per_game per season → currently 7.
3. Video self-host vs YouTube link → currently link.
4. Public (no-login) historical leaderboard pages → out of MVP scope.

## 10. Global Definition of Done
- All phase DoDs pass in order.
- `pytest` and `vitest` green in CI.
- A scorer can: create a game → enter it from the RTBA sheet → finalize → see it in leaderboards, player pages, and a boxscore — end to end, with all validation active.
