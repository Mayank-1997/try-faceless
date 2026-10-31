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
  REDIS_PORT="6379" `
  REDIS_PASSWORD="<upstash-token>" `
  CELERY_BROKER_URL="rediss://default:<token>@<host>:6379/0?ssl_cert_reqs=CERT_REQUIRED" `
  CELERY_RESULT_BACKEND="rediss://default:<token>@<host>:6379/0?ssl_cert_reqs=CERT_REQUIRED" `
  JWT_SECRET_KEY="<random 64+ chars>" `
  GEMINI_API_KEY="<key>" `
  FAL_KEY="<fal-key>" `
  STOCK_PEXELS_API_KEY="<key>" `
  STOCK_PIXABAY_API_KEY="<key>" `
  STOCK_UNSPLASH_API_KEY="<key>" `
  LANGFUSE_ENABLED="true" `
  LANGFUSE_PUBLIC_KEY="..." `
  LANGFUSE_SECRET_KEY="..." `
  LANGFUSE_HOST="https://cloud.langfuse.com" `
  LOKI_ENABLED="true" `
  LOKI_URL="https://logs-prod-028.grafana.net" `
  LOKI_USER="<id>" `
  LOKI_API_KEY="<glc_...>" `
  -a ai-studio-api
```

> **Upstash gotchas (verified 2026-10-30):**
> - The console's `UPSTASH_REDIS_REST_TOKEN` doubles as the TCP password.
> - **Only DB `0` exists** — `rediss://.../1` fails with `Only 0th database
>   is supported`. Broker and result backend share `/0` (celery namespaces
>   result keys, so this is safe).
> - Celery **requires** `?ssl_cert_reqs=CERT_REQUIRED` on `rediss://` URLs.
> - `KLING_API_KEY` is not needed — `KlingSettings.api_key` reads `FAL_KEY`.
> - Stock providers use `STOCK_*_API_KEY` names, not `PEXELS_API_KEY`.

Setting secrets **restarts** the machine — that's normal. If the machine was
already `stopped` (e.g. after crash-looping), secrets updates won't boot it —
run `flyctl machine start <id> -a ai-studio-api`.

## Step 6 — Verify backend

```powershell
fly logs -a ai-studio-api        # watch init_db → supervisord → uvicorn
fly status -a ai-studio-api      # machine should be "started"
```

Then: `curl https://ai-studio-api.fly.dev/health` → `{"status":"healthy"}`

Expected log lines: `database schema initialised` → `default_roles_seeded` →
`database_connected` → `celery@<id> ready.` → `Connected to rediss://...`.

> **Schema init**: the CMD is `python deploy/init_db.py && alembic stamp head
> && supervisord ...` — NOT `alembic upgrade head`. Migration `0002` FKs to
> `users` (auth tables have no migration; dev relies on `create_all`).
> `init_db.py` runs the same `create_all` in production, `stamp head` marks
> migrations applied so future upgrades stay no-ops.

## Step 7 — Vercel (frontend)

1. vercel.com → **Import Project** → `Mayank-1997/try-faceless`.
2. **Root directory**: `frontend` (monorepo — Vercel detects Turborepo +
   picks `apps/web`).
3. Env vars:

```env
NEXT_PUBLIC_API_BASE_URL=https://ai-studio-api.fly.dev/api/v1
NEXT_PUBLIC_VIDEO_PROVIDER=kling
# NEXT_PUBLIC_WS_URL — leave UNSET (no socket.io backend; realtime no-ops)
```

The URL must include `/api/v1`; the frontend reads
`NEXT_PUBLIC_API_BASE_URL`, not `NEXT_PUBLIC_API_URL`. Set it for the
**Production** environment and redeploy after changing it (Next.js embeds
`NEXT_PUBLIC_*` variables at build time).

4. Deploy → copy your `https://<app>.vercel.app` domain → update Fly:

```powershell
flyctl secrets set CORS_ORIGINS="https://<app>.vercel.app" -a ai-studio-api
```

> `CORS_ORIGINS` is **comma-separated** — no JSON brackets.
> A Vercel `500 FUNCTION_INVOCATION_FAILED` on the initial page is a frontend
> runtime error, not a CORS failure. Inspect the failed request in Vercel
> **Project → Logs** (filter to the deployment and `/`), and use the exception
> and stack trace to diagnose it before changing the backend.

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
| Volume required before mount | ✅ `fly volumes create` BEFORE deploy |
| `DATABASE_URL` driver scheme | ✅ auto-normalised to `+asyncpg`/`+psycopg2` |
| Upstash TLS | ✅ `REDIS_USE_TLS=true` → `rediss://` |
| Upstash DB index | ✅ only DB `0` — both celery URLs use `/0` |
| Upstash REST→TCP token | ✅ REST token works as TCP password |
| Celery `ssl_cert_reqs` | ✅ `?ssl_cert_reqs=CERT_REQUIRED` appended |
| `JWT_SECRET_KEY` default `"change-me"` | ✅ random 64-char secret set |
| `CORS_ORIGINS` JSON brackets | ⚠️ comma-separated only |
| `NEXT_PUBLIC_WS_URL` | ⚠️ leave unset — no socket.io backend |
| ffmpeg in container | ✅ installed in `Dockerfile.railway` |
| Auth tables (no migration) | ✅ `deploy/init_db.py` + `alembic stamp head` |
| Deploy to existing app | ✅ use `flyctl deploy` — GitHub UI only creates NEW apps |
| Stopped machine after crash-loop | ✅ `flyctl machine start <id>` |
| Machine sleep | ✅ `auto_stop_machines = "off"` — worker/beat stay alive |
| Shared storage api↔worker | ✅ single machine + volume |
| Build context size | ✅ `.dockerignore` — 6.1 GB → ~750 KB upload |

## Cost check

| Resource | Usage | Est./mo |
|---|---|---|
| shared-cpu-1x @ 2 GB, 24/7 | ~1.5-2 GB avg incl. spikes | ~$6-9 |
| Volume (3 GB) | | ~$0.45 |
| Neon + Upstash + Vercel + Grafana | | $0 |
| **Total infra** | | **~$5-8/mo** |
| fal.ai (50 × 15s clips) | | ~$95 |
