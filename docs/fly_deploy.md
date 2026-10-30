# Deployment Plan — Vercel + Fly.io (~$5–7/mo)

| Piece | Host | Cost |
|---|---|---|
| Frontend (`frontend/apps/web`) | **Vercel** hobby | $0 |
| Backend (API + Celery worker + beat) | **Fly.io** single machine | ~$4-8/mo |
| Postgres | **Neon** free tier | $0 |
| Redis | **Upstash** free tier | $0 |
| Media + workflow state | **Fly volume** `/app/storage` | ~$0.15/GB |
| Logs | Grafana Cloud Loki free | $0 |
| Video generation | fal.ai Kling (pay per use) | ~$1.89/15s clip |

## Architecture

```
┌──────────────┐    HTTPS     ┌───────────────────────────────────┐
│ Vercel (web) │ ───────────► │ Fly machine (ai-studio-api)       │
│ Next.js UI   │              │  supervisord:                     │
└──────────────┘              │   ├ uvicorn  :8000  (API)         │
                              │   ├ celery worker --pool=solo     │
                              │   └ celery beat                   │
                              │  Volume: /app/storage (persistent)│
                              └──────────┬──────────────┬─────────┘
                                         │              │
                                  Neon Postgres   Upstash Redis
                                  (free)          (free, TLS)
```

## Files (all committed)

| File | Purpose |
|---|---|
| `fly.toml` | App config: build, env, healthcheck, volume mount, 2 GB RAM |
| `backend/Dockerfile.railway` | Same image as Railway — supervisord all-in-one |
| `backend/deploy/supervisord.conf` | API + worker + beat in one machine |

---

## Step 0 — Commit `fly.toml` first

```powershell
git add fly.toml docs/fly_deploy.md
git commit -m "add Fly.io deployment config"
git push
```

> ⚠️ **Order matters**: the `[[mounts]]` in fly.toml fails if the volume
> doesn't exist yet. Create it in Step 3 *before* deploying.

## Step 1 — Neon Postgres (free)

1. neon.tech → new project → copy the **direct connection string**
   `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname`
2. The app normalises `postgresql://` → `postgresql+asyncpg://`
   automatically (already in `config.py`).

## Step 2 — Upstash Redis (free)

1. upstash.com → create Redis → copy host, port, password.
2. `REDIS_USE_TLS=true` is already in fly.toml — the app builds `rediss://`
   automatically.
3. Celery broker/backend use `rediss://` URLs directly (secrets below).

## Step 3 — Fly volume (BEFORE deploy)

```powershell
fly volumes create aivideo_data --region sin --size 3
```

The `[[mounts]]` block in fly.toml expects this volume to exist in `sin`.

## Step 4 — Deploy via GitHub (the UI you're already on)

In the **Launch from GitHub** dialog:

1. **GitHub account**: `Mayank-1997` → search `Ai-Studio` (repo must be pushed first).
2. **Region**: `sin - Singapore` ✓ (already selected).
3. **CPU**: `shared-cpu-1x` ✓ · **Memory**: `2GB` ✓ (already selected).
4. **Internal port**: `8000` — change from the default `8080`.
5. **Environment variables**: you can leave this blank and use
   `fly secrets set` afterwards (keeps secrets out of the UI).
6. Deploy.

> The committed `fly.toml` provides app name, healthcheck, mounts, and env
> defaults — the UI will detect it.

## Step 5 — Secrets (via flyctl)

The UI env-var box is visible in logs — use `fly secrets` instead for
anything sensitive. Install flyctl, `fly auth login`, then:

```powershell
fly secrets set `
  DATABASE_URL="postgresql://<neon-user>:<neon-pass>@<neon-host>/<neon-db>" `
  REDIS_HOST="<upstash-host>" `
  REDIS_PORT="<upstash-port>" `
  REDIS_PASSWORD="<upstash-pass>" `
  CELERY_BROKER_URL="rediss://default:<pass>@<host>:<port>/1" `
  CELERY_RESULT_BACKEND="rediss://default:<pass>@<host>:<port>/2" `
  JWT_SECRET_KEY="<random 64+ chars>" `
  GEMINI_API_KEY="<key>" `
  FAL_KEY="<fal-key>" `
  KLING_API_KEY="<fal-key>" `
  PEXELS_API_KEY="<key>" `
  PIXABAY_API_KEY="<key>" `
  UNSPLASH_API_KEY="<key>" `
  LANGFUSE_PUBLIC_KEY="..." `
  LANGFUSE_SECRET_KEY="..." `
  LOKI_ENABLED="true" `
  LOKI_URL="https://logs-prod-028.grafana.net" `
  LOKI_USER="<id>" `
  LOKI_API_KEY="<glc_...>" `
  -a ai-studio-api
```

Setting secrets **restarts** the machine — that's normal.

## Step 6 — Verify backend

```powershell
fly logs -a ai-studio-api        # watch alembic → supervisord → uvicorn
fly status -a ai-studio-api      # machine should be "started"
```

Then: `curl https://ai-studio-api.fly.dev/health` → `{"status":"healthy"}`

Expected log lines: `alembic upgrade head` → `default_roles_seeded` →
`database_connected` → `loki_log_shipping_enabled`.

## Step 7 — Vercel (frontend)

1. vercel.com → **Import Project** → `Mayank-1997/Ai-Studio`.
2. **Root directory**: `frontend` (monorepo — Vercel detects Turborepo +
   picks `apps/web`).
3. Env vars:

```env
NEXT_PUBLIC_API_URL=https://ai-studio-api.fly.dev
NEXT_PUBLIC_VIDEO_PROVIDER=kling
# NEXT_PUBLIC_WS_URL — leave UNSET (no socket.io backend; realtime no-ops)
```

4. Deploy → copy your `https://<app>.vercel.app` domain → update Fly:

```powershell
fly secrets set CORS_ORIGINS="https://<app>.vercel.app" -a ai-studio-api
```

> `CORS_ORIGINS` is **comma-separated** — no JSON brackets.

## Step 8 — Smoke test

- [ ] `GET /health` → `{"status":"healthy"}`
- [ ] Vercel site → register/login (first user seeds roles)
- [ ] Research flow → assets are `stock_image`/`stock_footage` at $0
- [ ] Direct cinematic → Kling clip generates
- [ ] Completed project → **Download Video** streams `final_video.mp4`
- [ ] `fly ssh console -a ai-studio-api` → `ls /app/storage/projects/` shows files (volume works)
- [ ] Grafana `{app="ai_video_studio"}` shows live logs

## Blockers handled

| Blocker | Status |
|---|---|
| Volume required before mount | ⚠️ `fly volumes create` BEFORE deploy |
| `DATABASE_URL` driver scheme | ✅ auto-normalised to `+asyncpg`/`+psycopg2` |
| Upstash TLS | ✅ `REDIS_USE_TLS=true` → `rediss://` |
| `JWT_SECRET_KEY` default `"change-me"` | ⚠️ **must set** via `fly secrets` |
| `CORS_ORIGINS` JSON brackets | ⚠️ comma-separated only |
| `NEXT_PUBLIC_WS_URL` | ⚠️ leave unset — no socket.io backend |
| ffmpeg in container | ✅ installed in `Dockerfile.railway` |
| Alembic migrations | ✅ `alembic upgrade head` in CMD |
| Machine sleep | ✅ `auto_stop_machines = "off"` — worker/beat stay alive |
| Shared storage api↔worker | ✅ single machine + volume |

## Cost check

| Resource | Usage | Est./mo |
|---|---|---|
| shared-cpu-1x @ 2 GB, 24/7 | ~1.5-2 GB avg incl. spikes | ~$6-9 |
| Volume (3 GB) | | ~$0.45 |
| Neon + Upstash + Vercel + Grafana | | $0 |
| **Total infra** | | **~$5-8/mo** |
| fal.ai (50 × 15s clips) | | ~$95 |
