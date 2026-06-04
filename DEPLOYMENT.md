# CineVault Deployment Guide

A production-ready checklist for deploying CineVault.

## TL;DR

```bash
# 1. Generate a strong secret
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# 2. Copy and fill the env template
cp .env.example .env
$EDITOR .env

# 3. Initialize the database
python3 -c "from app import app; from services.db_service import init_database; init_database()"

# 4. Run with a real WSGI server behind a reverse proxy
gunicorn -w 4 -b 127.0.0.1:55300 app:app
# or with waitress (the WSGI server already in requirements.txt)
waitress-serve --host 127.0.0.1 --port 55300 app:app
```

---

## 1. Pre-deployment checklist

### Secrets
- [ ] `SECRET_KEY` is a strong 64-char random hex (NOT a guessable word). The app raises `ValueError` on startup if this is missing.
- [ ] `DB_PASSWORD` is loaded from a secrets manager (AWS SSM, HashiCorp Vault, K8s Secret, Docker secret, etc.) — NOT a plaintext `.env` value committed to the repo or baked into a container image.
- [ ] First-time admin password `admin123` is changed before opening the service to users. The app enforces this via the `users.password_changed` flag — first login forces a password change.

### Reverse proxy (Nginx / Caddy / Cloudflare)
- [ ] `PROXY_FIX_DEPTH=1` in `.env` (if you have exactly one trusted reverse proxy in front).
- [ ] Nginx sets `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` and `proxy_set_header X-Forwarded-Proto $scheme;` — the app uses `werkzeug.middleware.proxy_fix.ProxyFix` and trusts XFF only for the configured depth.
- [ ] Do NOT trust client-sent XFF headers — `PROXY_FIX_DEPTH=0` is the default precisely because blindly trusting XFF is a well-known spoofing vector.
- [ ] HTTPS terminated at the proxy — the app does NOT enforce TLS itself.
- [ ] Rate limiting at the proxy (e.g., `limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;` for `/login` and `/api/*`).

### Database
- [ ] MySQL 8.0+ with `utf8mb4` (the schema uses utf8mb4 for emoji and CJK support).
- [ ] Dedicated database user with `SELECT, INSERT, UPDATE, DELETE` on the cinevault schema — no `GRANT`, no `DROP`, no DDL on the application connection.
- [ ] Backups enabled (`mysqldump`, Percona XtraBackup, or vendor-specific like RDS automated backups).
- [ ] Connection pool sized to expected concurrency (default 8 connections in `services/db_service.py`).
- [ ] Network ACL: MySQL accepts connections only from the app host, not `0.0.0.0`.

### Filesystem
- [ ] `VIDEO_ROOTS` set to the real video directories (NOT a guessable path like `/tmp`). This is a security boundary — the app refuses any `video_path` outside this list.
- [ ] Video files owned by the app user (or readable by it). If using an external drive, ensure it's mounted with a stable path (use `UUID=...` in `/etc/fstab`, not `/dev/sdX`).
- [ ] Thumbnail directory writable by the app user. If using a network mount, set `ENABLE_FS_WATCHER=0` to avoid polling overhead.
- [ ] `ffmpeg` in `$PATH`, or set `FFMPEG_PATH=/usr/bin/ffmpeg`. The bundled `./ffmpeg` binary is for development.

### Application
- [ ] Run with a real WSGI server (`gunicorn` / `waitress`) — NOT `flask run` or `python3 app.py` in production. Flask's dev server is single-threaded and explicitly warns against production use.
- [ ] App bound to `127.0.0.1` and fronted by a reverse proxy (or with strict source IP allowlisting via firewall).
- [ ] At least 1 GB RAM, 2 CPU cores. `ffmpeg` is single-threaded but library scans are parallel.
- [ ] Static files served by the proxy (or via `static_folder` mount) to avoid Python overhead.
- [ ] `sessions/` and `thumbnails/` directories exist and are writable.
- [ ] Log shipping configured (stdout/stderr to journald → journalbeat → your log aggregator).

---

## 2. First-run admin password change

The app ships with `admin` / `admin123`. On first login, the user is forced to change the password via the `password_changed=FALSE` flag.

Make sure:
- You do NOT expose the service to the internet before completing this step.
- The forced password change is tested manually (log in as `admin`, verify redirect to the change-password page).

To rotate the admin password from the command line, see `SECURITY.md` § "Recovery" — the canonical path is to log in as `admin`, change the password via the UI, and never put plaintext credentials in `.env` or commit history.

---

## 3. Optional: ENABLE_FS_WATCHER

Set `ENABLE_FS_WATCHER=1` to auto-invalidate the `LibraryCache` when files change on disk. Useful when adding/removing videos from a watch folder without restarting the app.

Adds ~5 s polling overhead. **Disable if your video library is on a slow or network filesystem** (NFS, SMB, FUSE) — the polling can keep the FS awake and chew through idle CPU time.

---

## 4. Health check

```bash
curl -s http://localhost:55300/health
# {"status": "healthy"}
```

Use this for your load balancer or Kubernetes liveness probe. The endpoint does not require auth and does not touch the database — it only confirms the WSGI process is up.

Example Kubernetes probe:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 55300
  initialDelaySeconds: 10
  periodSeconds: 30
```

---

## 5. Common deployment topologies

### 5a. Bare metal / VM

```
                ┌──────────────────────┐
   client ────► │  Nginx (TLS, XFF)    │ :443
                │  rate-limit /login   │
                └──────────┬───────────┘
                           │ 127.0.0.1:55300
                ┌──────────▼───────────┐
                │  gunicorn            │
                │  (4 workers × app)   │
                └──────────┬───────────┘
                           │ 3306
                ┌──────────▼───────────┐
                │  MySQL 8.0           │
                └──────────────────────┘
                           ▲
                ┌──────────┴───────────┐
                │  /var/lib/cinevault/ │
                │  videos, thumbnails  │
                └──────────────────────┘
```

`.env`: `PROXY_FIX_DEPTH=1`, `VIDEO_ROOTS=/var/lib/cinevault/videos`.

### 5b. Docker Compose (single host)

```
                ┌──────────────────────┐
   client ────► │  Caddy / Nginx       │ :443
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │  web (gunicorn)      │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │  db (mysql:8.0)      │
                └──────────────────────┘
```

A `docker-compose.yml` is included in the project root for this topology. It binds the web service to `127.0.0.1:55300` so you MUST put a reverse proxy in front (Caddy is recommended for automatic TLS via Let's Encrypt).

### 5c. Kubernetes

```
   Ingress (TLS) ──► Service ──► Deployment (gunicorn, ≥2 replicas)
                                    │
                                    ├──► Service ──► MySQL (StatefulSet or managed RDS)
                                    │
                                    └──► PVC for /videos (ReadWriteMany if multiple replicas)
```

Set `PROXY_FIX_DEPTH=1` and inject `SECRET_KEY` / `DB_PASSWORD` via `Secret` references in the Deployment manifest. Use a `CronJob` running `fix_thumbnails.py` if you need periodic self-heal of missing thumbnails.

---

## 6. Post-deployment smoke test

```bash
# 1. Health check
curl -fsS http://localhost:55300/health

# 2. Login as the (now-rotated) admin
curl -fsS -c /tmp/cookies.txt -X POST http://localhost:55300/login \
    -d "username=admin&password=$NEW_PASSWORD"

# 3. Fetch a video page (any video) — confirms DB + video scan work end-to-end
curl -fsS -b /tmp/cookies.txt http://localhost:55300/video/1
```

If all three return 200, you are good to open the service to users.
