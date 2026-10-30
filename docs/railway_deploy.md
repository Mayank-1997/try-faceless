# Deployment Plan — Vercel + Railway (~$5–7/mo)

| Piece | Host | Cost |
|---|---|---|
| Frontend (`frontend/apps/web`) | **Vercel** hobby | $0 |
| Backend (API + Celery worker + beat) | **Railway** single service | ~$5–7/mo usage |
| Postgres | **Neon** free tier | $0 |
| Redis | **Upstash** free tier | $0 |
| Media + workflow state | **Railway volume** `/app/storage` | ~$0.50 |
| Logs | Grafana Cloud Loki free | $0 |
| Video generation | fal.ai Kling (pay per use) | ~$1.89/15s clip |

---

## Step 0 — Pre-push checklist (no blockers)

1. **Init git + push** (repo is not initialised yet):
   ```powershell
   git init
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. **Verified safe**: `.env`, `storage/`, `backend/.venv`, `node_modules` are
   all in `.gitignore` — no secrets or generated media will be committed.
3. **No frontend images needed**: `.gitignore` blocks `*.png`/`*.jpg` globally
   but `frontend/` has no static image assets — nothing lost.
4. **Secrets stay out of git**: `FAL_KEY`, `GEMINI_API_KEY`, `LOKI_API_KEY`,
   `JWT_SECRET_KEY` must be set as platform env vars (below), never committed.

### Deploy files already in the repo

| File | Purpose |
|---|---|
| `backend/Dockerfile.railway` | Builds from repo root, runs `alembic upgrade head` then supervisord |
| `backend/deploy/supervisord.conf` | API (`:$PORT`) + `celery worker --pool=solo` + `celery beat` |
| `railway.toml` | `dockerfilePath=backend/Dockerfile.railway`, healthcheck `/health` |

---

## Step 1 — Neon Postgres (free)

1. neon.tech → new project → copy the **direct connection string**
   `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname`
2. Use it as `DATABASE_URL` on Railway — **the code normalises it to
   `postgresql+asyncpg://` automatically** (no manual driver edits).
3. Enable **connection pooling** off (alembic + asyncpg prefer direct) —
   or use the `-pooler` host if Neon requires it; asyncpg handles both.

## Step 2 — Upstash Redis (free)

1. upstash.com → create Redis → copy the **TLS endpoint** details
   (host, port, password).
2. The app supports TLS via `REDIS_USE_TLS=true` (added in this change) —
   `rediss://` is built automatically for the app's cache client.
3. Celery broker/backend must use `rediss://` URLs directly (see env below).

   If you'd rather skip Upstash entirely, Railway's Redis plugin is
   ~$0.50–1/mo — see Option B in the env block.

## Step 3 — Railway (backend)

1. `railway init` → **Deploy from GitHub repo** → this repo.
   `railway.toml` picks `backend/Dockerfile.railway` automatically.
2. **Storage → New Volume** → mount path `/app/storage` on the app service.
   This persists `final_video.mp4`, `workflow_state/` JSON, and project logs
   across redeploys.
3. **Settings → Resources** → 1–2 GB RAM (FFmpeg + Celery + uvicorn share
   one container; 512 MB will OOM mid-render).
4. Set env vars:

```env
APP_ENV=production
APP_DEBUG=false

# --- Neon (direct string; app normalises the driver) ---
DATABASE_URL=postgresql://<neon-user>:<neon-pass>@<neon-host>/<neon-db>

# --- Redis ---
# Option A: Upstash (free, TLS)
REDIS_HOST=<upstash-host>
REDIS_PORT=<upstash-port>
REDIS_PASSWORD=<upstash-pass>
REDIS_USE_TLS=true
CELERY_BROKER_URL=rediss://default:<pass>@<host>:<port>/1
CELERY_RESULT_BACKEND=rediss://default:<pass>@<host>:<port>/2
# Option B: Railway Redis plugin (~$0.50-1/mo)
# CELERY_BROKER_URL=${{Redis.REDIS_URL}}/1
# CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/2

# --- Storage (must match the volume mount) ---
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/app/storage

# --- Auth (REQUIRED — "change-me" default is insecure) ---
JWT_SECRET_KEY=<random 64+ chars>

# --- CORS: comma-separated, NO brackets ---
CORS_ORIGINS=https://your-app.vercel.app

# --- Providers ---
GEMINI_API_KEY=<key>
USE_VEO=false
USE_KLING=true
KLING_ENABLED=true
FAL_KEY=<fal-key>
KLING_API_KEY=<fal-key>

# --- Stock media (research flow, all free) ---
PEXELS_API_KEY=<key>
PIXABAY_API_KEY=<key>
UNSPLASH_API_KEY=<key>

# --- Observability (optional) ---
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LOKI_ENABLED=true
LOKI_URL=https://logs-prod-028.grafana.net
LOKI_USER=<instance-id>
LOKI_API_KEY=<glc_...>
```

5. Railway injects `PORT` automatically — supervisord binds uvicorn to it.

## Step 4 — Vercel (frontend)

1. vercel.com → **Import Project** → same GitHub repo.
2. **Root directory**: `frontend` (the monorepo root — Vercel detects
   Turborepo + picks `apps/web`).
   - If it doesn't auto-detect: set root dir `frontend`, framework
     `Next.js`, install cmd `pnpm install`, build cmd
     `pnpm --filter web build` (or `turbo run build --filter=web`).
3. Env vars on Vercel:

```env
NEXT_PUBLIC_API_URL=https://<service>.up.railway.app
NEXT_PUBLIC_VIDEO_PROVIDER=kling
# NEXT_PUBLIC_WS_URL — leave UNSET: the backend has no Socket.IO server,
# realtime updates gracefully no-op without it.
```

4. Deploy → get `https://<app>.vercel.app` → add it to Railway
   `CORS_ORIGINS`.

## Step 5 — Smoke test

- [ ] `curl https://<service>.up.railway.app/health` → `{"status":"healthy"}`
- [ ] Vercel site loads → register/login works (first user seeds roles)
- [ ] Research flow project → assets are `stock_image`/`stock_footage` ($0)
- [ ] Direct cinematic project → Kling clip generates
- [ ] Completed project → **Download Video** streams `final_video.mp4`
- [ ] Restart Railway service → videos + checkpoints survive (volume)
- [ ] Grafana `{app="ai_video_studio"}` shows live logs

## Known blockers & how they're handled

| Blocker | Status |
|---|---|
| `.env` committed | ✅ gitignored — no secrets leak |
| Railway build context | ✅ Dockerfile uses `backend/`-prefixed COPY paths |
| `DATABASE_URL` driver scheme | ✅ auto-normalised to `+asyncpg`/`+psycopg2` |
| `JWT_SECRET_KEY` default `"change-me"` | ⚠️ **must set** a real value on Railway |
| `CORS_ORIGINS` JSON format | ⚠️ comma-separated only — no `[]` brackets |
| Upstash TLS | ✅ `REDIS_USE_TLS=true` → `rediss://` built automatically |
| `NEXT_PUBLIC_WS_URL` | ⚠️ leave unset — no socket.io backend exists |
| ffmpeg in container | ✅ installed in `Dockerfile.railway` |
| Alembic on startup | ✅ `alembic upgrade head` in CMD before supervisord |
| Shared storage api↔worker | ✅ single service + volume (Railway volumes can't cross services) |
| Frontend build needs pnpm/turbo | ⚠️ Vercel root dir = `frontend`, build filter `web` |

## Cost sanity check

| Resource | Usage est. | Cost |
|---|---|---|
| Railway app service | ~0.5-0.8 GB RAM idle, spikes ~2 GB on render | ~$6-9/mo usage |
| Volume | ~5 GB | ~$0.75 |
| **After $5 Hobby credit** | | **~$5-10/mo total** |
| fal.ai (50 × 15s clips) | | ~$95/mo |

If Neon/Upstash's free tiers feel risky for the demo, Railway's own
Postgres+Redis plugins add ~$3-5/mo but keep everything in one dashboard.
