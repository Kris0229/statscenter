# DEPLOY.md — 免費 Demo 環境部署手冊

> 目標:把系統架到免費雲端,給客戶點開測試、收反饋。
> 對象:不需工程背景,照步驟操作即可。
> 組合:Supabase(資料庫 + 檔案儲存)+ Render(後端 API)+ Vercel(前端)。
> 預計耗時:第一次約 60–90 分鐘。
>
> ⚠️ 免費環境限制(先知道,免得誤會是壞了):
> - Supabase 專案閒置一段時間會自動暫停 → 測試期間每隔幾天登入一次控制台即可喚醒。
> - Render 免費後端閒置 15 分鐘會休眠 → 客戶第一次點開會等 30–50 秒才有反應,之後就正常。這是正常現象,不是故障。
> - 這是「展示測試」用途,不是長期正式環境。客戶確認要用之後再升級付費方案。

---

## 前置準備

需要先有這三個帳號(都可用 GitHub 或 Google 登入,免費):
1. GitHub — 放程式碼:https://github.com
2. Supabase — https://supabase.com
3. Render — https://render.com
4. Vercel — https://vercel.com

並確認 Claude Code 已完成 Phase 0,程式碼已 push 到一個 GitHub repo(含 `.env.example`、`render.yaml`、`vercel.json`)。

---

## 步驟 1 — 建立資料庫(Supabase)

1. 登入 Supabase → 點 `New project`。
2. 填 Project name(例:`softball-league-demo`)、設定一組資料庫密碼(**請記下來**)、Region 選 `Northeast Asia (Tokyo)` 或 `Southeast Asia (Singapore)`(離台灣近)。
3. 等專案建立完成(約 2 分鐘)。
4. 取得資料庫連線字串:左側選單 `Project Settings` → `Database` → 找到 `Connection string` → 選 `URI` 格式。
   - 會長得像:`postgresql://postgres.[xxxx]:[你的密碼]@aws-...pooler.supabase.com:5432/postgres`
   - **把密碼填進去、整串複製起來**,這就是後面要用的 `DATABASE_URL`。
   - ⚠️ 建議用 `Connection pooling` 那一組(Transaction mode),Render 這類平台配合較穩。
5. (若使用照片上傳)取得儲存金鑰:`Project Settings` → `API` → 記下 `Project URL`(= `SUPABASE_URL`)和 `service_role` key(= `SUPABASE_SERVICE_KEY`,**這把是機密,勿外流**)。
6. (若使用照片上傳)建立儲存桶:左側 `Storage` → `New bucket` → 命名 `media` → 設為 Public(測試期方便看圖)。

---

## 步驟 2 — 部署後端 API(Render)

1. 登入 Render → `New` → `Web Service` → 連結你的 GitHub repo。
2. Render 會讀到 repo 裡的 `render.yaml`,大部分設定自動帶入。若需手動填:
   - Root Directory:`backend`
   - Runtime:`Python 3`
   - Build Command:`pip install -e .`(或 `pip install -r requirements.txt`,依 Claude Code 產出而定)
   - Start Command:`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Instance Type:**Free**
3. 設定環境變數(`Environment` 頁籤 → `Add Environment Variable`),對照 `.env.example`:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | 步驟 1 的連線字串 |
   | `JWT_SECRET` | 隨機長字串(可用密碼產生器產一組 32 字元以上) |
   | `JWT_ACCESS_TTL` | `900`(15 分鐘,秒) |
   | `JWT_REFRESH_TTL` | `1209600`(14 天,秒) |
   | `CORS_ORIGINS` | 先留 `*`,步驟 3 拿到前端網址後改成該網址 |
   | `STORAGE_BACKEND` | `supabase`(若不用照片,填 `local`) |
   | `SUPABASE_URL` | 步驟 1 的 Project URL |
   | `SUPABASE_SERVICE_KEY` | 步驟 1 的 service_role key |
   | `SUPERADMIN_EMAIL` | 系統管理員登入信箱(bootstrap 用) |
   | `SUPERADMIN_PASSWORD` | 系統管理員初始密碼(bootstrap 後請登入變更) |
4. 按 `Create Web Service`,等部署完成(約 3–5 分鐘)。完成後會給一個網址,例:`https://softball-api.onrender.com`。**記下這個後端網址。**
5. 測試後端活著:瀏覽器打開 `https://你的後端網址/api/v1/health`,應看到 `{"status":"ok"}`。

---

## 步驟 3 — 跑資料庫 migration 與種子資料

第一次要把資料表建進 Supabase。兩種做法擇一:

**做法 A(推薦,Render Shell):**
1. Render 後端服務頁 → 上方 `Shell` 頁籤 → 開啟終端機。
2. 執行 migration:`alembic upgrade head`
3. 建立系統管理員(super_admin,一次性,帳密由環境變數指定):`python -m app.db.bootstrap_superadmin`
4. 執行種子資料(建立範例聯盟、聯盟管理員、球隊):`python -m app.db.seed`(實際指令依 Claude Code 產出的 README 為準)。
   > 多聯盟說明:登入後,系統管理員可再開立新聯盟並指派各聯盟的管理員;各聯盟資料互相隔離。

**做法 B(本機執行):**
1. 在自己電腦的專案資料夾,把 `.env` 的 `DATABASE_URL` 設成步驟 1 的 Supabase 連線字串。
2. 執行 `alembic upgrade head` 與種子指令。

完成後到 Supabase → `Table Editor`,應該看得到 `users`、`teams`、`players`… 等資料表。

---

## 步驟 4 — 部署前端(Vercel)

1. 登入 Vercel → `Add New` → `Project` → 匯入同一個 GitHub repo。
2. 設定:
   - Root Directory:`frontend`
   - Framework Preset:`Vite`(通常自動偵測)
   - Build Command:`npm run build`(自動)
   - Output Directory:`dist`(自動)
3. 環境變數(`Environment Variables`):
   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | 步驟 2 的後端網址,例 `https://softball-api.onrender.com/api/v1` |
4. 按 `Deploy`,等完成(約 2 分鐘)。會給一個前端網址,例:`https://softball-league-demo.vercel.app`。

---

## 步驟 5 — 回頭鎖定 CORS(安全)

1. 回 Render 後端 → `Environment` → 把 `CORS_ORIGINS` 從 `*` 改成步驟 4 的前端網址(例 `https://softball-league-demo.vercel.app`)。
2. 儲存後 Render 會自動重新部署。

---

## 步驟 6 — 驗收(交付客戶前自己先走一遍)

依 BUILD_SPEC §10 的端到端流程確認:
1. 開前端網址 → 用種子建立的管理員帳號登入。
2. 建立一支球隊 → 用 Excel 匯入或手動加球員。
3. 建立一場比賽 → 依 RTBA 紙本補登打擊/投手成績 → 定稿。
4. 到排行榜、球員個人頁、Boxscore 確認數字正確出現。
5. (若啟用照片)上傳一張比賽照片,確認顯示。

全部通過 → 把前端網址 + 一組測試帳號給客戶。

---

## 常見問題

**Q:客戶說「點進去轉很久才有反應」?**
A:Render 免費後端休眠喚醒需 30–50 秒,屬正常。給客戶測試前可先自己打開一次 `/health` 把它喚醒。要完全消除延遲,把 Render 升 Starter 方案(約 US$7/月)。

**Q:過幾天回來系統連不上資料庫?**
A:Supabase 免費專案閒置會暫停。登入 Supabase 控制台點一下專案即可恢復。

**Q:圖片上傳失敗?**
A:確認步驟 1 的 `media` bucket 已建立且為 Public,且 Render 環境變數 `STORAGE_BACKEND=supabase` 與金鑰正確。

**Q:改了程式碼要怎麼更新線上版?**
A:push 到 GitHub 的主分支,Render 和 Vercel 都會自動重新部署,不用手動操作。

---

## 轉正式環境(客戶確認採用後)

- 資料庫:Supabase 升 Pro(約 US$25/月,移除暫停、加大容量與備份),連線字串不變。
- 後端:Render 升 Starter(約 US$7/月,移除休眠),或搬到小型 VPS。
- 前端:維持 Vercel/Netlify 免費層即可。
- 因為全靠環境變數驅動,升級是「改方案 + 重新部署」,不需改程式。
- 資料若需搬遷:`pg_dump` 匯出、`pg_restore` 匯入,兩端都是標準 PostgreSQL。
