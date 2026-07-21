# 棒壘聯盟成績管理系統 (StatsCenter)

多租戶的棒壘聯盟成績管理平台。技術規格詳見 [`BUILD_SPEC.md`](./BUILD_SPEC.md);
免費雲端部署手冊詳見 [`DEPLOY.md`](./DEPLOY.md)。

**目前進度:Phase 1 — Data model & migrations**

---

## 專案結構

```
/backend       FastAPI + SQLAlchemy + Alembic
/frontend      React 18 + Vite + TypeScript + TanStack Query
/docker        docker-compose.yml (postgres + backend + frontend)
render.yaml    Render 後端部署設定
```

---

## 本機開發(Docker Compose)

```bash
# 從 repo root 執行
cd docker
docker compose up --build
```

啟動後:
- 後端 API: <http://localhost:8000/api/v1/health> → `{"status":"ok"}`
- 前端:<http://localhost:5173>
- Postgres: `localhost:5432` (user/pass: `postgres` / `postgres`, db: `statscenter`)

### 不用 Docker 本機跑後端

```bash
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.bootstrap_superadmin   # needs SUPERADMIN_EMAIL/PASSWORD in .env
python -m app.db.seed                   # optional: demo leagues/teams/players
uvicorn app.main:app --reload
```

### 不用 Docker 本機跑前端

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

---

## 測試

```bash
# 後端
cd backend && pytest

# 前端
cd frontend && npm test
```

---

## 免費 Demo 雲端部署(Supabase + Render + Vercel)

完整逐步手冊見 [`DEPLOY.md`](./DEPLOY.md)。核心一致性:所有環境差異
都由環境變數控制(`DATABASE_URL`、`STORAGE_BACKEND`、`CORS_ORIGINS`…),
程式碼在本機與雲端完全相同。

| 層 | 服務 | 用途 |
|---|---|---|
| DB + Storage | Supabase | Postgres 15 + 檔案儲存 |
| Backend | Render (Free web service) | FastAPI |
| Frontend | Vercel | 靜態網站 |

部署設定檔:
- `render.yaml` — Render 後端服務
- `frontend/vercel.json` — Vercel 前端
- `backend/.env.example`、`frontend/.env.example` — 環境變數清單

---

## Phase 進度

依 `BUILD_SPEC.md` §7:

- [x] **Phase 0** — Scaffold & infra
- [x] **Phase 1** — Data model & migrations
- [ ] Phase 1.5 — System admin & tenant isolation
- [ ] Phase 2 — Auth, accounts, teams, roster (含 Excel 匯入)
- [ ] Phase 3 — Score entry + validation + finalize
- [ ] Phase 4 — Leaderboards & player records
- [ ] Phase 5 — Boxscore
- [ ] Phase 6 — Score-entry UI
- [ ] Phase 7 — Media & reports
