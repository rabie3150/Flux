# Flux — Infrastructure & Deployment Plan

## 1. Deployment Target: Android Phone via Termux

The entire infrastructure is a single Android phone. This document describes how to turn that phone into a reliable 24/7 automation host.

---

## 2. Termux Environment Setup

### 2.1 Installation (One-Time)

```bash
# 1. Install Termux from F-Droid (NOT Play Store — Play Store version is outdated)
# https://f-droid.org/packages/com.termux/

# 2. Grant Android storage permission (required for external storage paths)
termux-setup-storage

# 3. Update packages
pkg update && pkg upgrade -y

# 4. Install core dependencies
pkg install -y python ffmpeg git openssh yt-dlp clang make libjpeg-turbo libpng

# 5. Optional but recommended
pkg install -y termux-api

# 6. Bootstrap Flux
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/flux/main/scripts/bootstrap.sh | bash
```

#### Bootstrap Script (`scripts/bootstrap.sh`)

```bash
#!/data/data/com.termux/files/usr/bin/bash
set -e

REPO_URL="https://github.com/YOUR_REPO/flux.git"
FLUX_DIR="$HOME/flux"

pkg install -y python ffmpeg git openssh yt-dlp clang make libjpeg-turbo libpng termux-api

mkdir -p "$FLUX_DIR"
cd "$FLUX_DIR"

if [ ! -d .git ]; then
    git clone "$REPO_URL" .
fi

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ensure external storage paths exist
mkdir -p /storage/emulated/0/Flux/library/production
mkdir -p /storage/emulated/0/Flux/thumbnails
mkdir -p /storage/emulated/0/Flux/logs
mkdir -p /storage/emulated/0/Flux/backups

# Enable SQLite WAL mode for better concurrency
sqlite3 "$FLUX_DIR/app.db" "PRAGMA journal_mode=WAL;" 2>/dev/null || true

# Setup Termux:Boot
mkdir -p "$HOME/.termux/boot"
cp "$FLUX_DIR/start.sh" "$HOME/.termux/boot/start-flux.sh"
chmod +x "$HOME/.termux/boot/start-flux.sh"

echo "[Flux] Bootstrap complete. Start with: ~/flux/start.sh"
```

### 2.2 Python Dependencies (`requirements.txt`)

```
fastapi==0.110.*
uvicorn[standard]==0.29.*
sqlalchemy==2.0.*
alembic==1.13.*
apscheduler==3.10.*
python-telegram-bot==21.*
httpx==0.27.*
Pillow==10.*
pydantic==2.6.*
pydantic-settings==2.2.*
cryptography==42.*
python-dotenv==1.0.*

# Platform workers
google-api-python-client==2.120.*
google-auth-oauthlib==1.2.*
instagrapi==2.0.*
```

### 2.3 Whisper.cpp (Local Transcription)

```bash
# Clone and build whisper.cpp for ARM
cd ~
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
# Termux requires explicit target
gmake -j$(nproc)

# Download tiny model (~75 MB)
bash models/download-ggml-model.sh tiny

# Test
./main -m models/ggml-tiny.bin -f samples/jfk.wav
```

---

## 3. Storage Layout

```
/storage/emulated/0/Flux/           # External storage (media, survives app uninstall)
├── library/
│   ├── quran_clips/                # Downloaded Quran shorts
│   ├── backgrounds/
│   │   ├── images/
│   │   └── videos/
│   └── production/                 # Rendered videos
├── thumbnails/
├── logs/
│   ├── app.log                     # Application log (rotated)
│   └── ffmpeg/                     # Per-render FFmpeg logs
└── temp/                           # Scratch space for renders

~/flux/                             # Internal storage (code, DB, configs)
├── main.py
├── plugins/
│   └── quran_shorts/
├── static/admin/
├── venv/
├── app.db                          # SQLite database
├── quran_text.db                   # Local Quran text for fuzzy matching
├── .env                            # Secrets (not in git)
└── alembic/                        # DB migrations
```

---

## 4. Process Management & Persistence

### 4.1 Keeping the Daemon Alive

| Threat | Mitigation |
|--------|------------|
| Android kills Termux | Acquire wake lock; disable battery optimization for Termux |
| Phone reboot | Termux:Boot add-on auto-starts daemon |
| Process crash | Systemd is unavailable; use a simple bash loop restart |
| Network change | Daemon binds to 127.0.0.1; admin panel accessed via SSH port-forward or Tailscale |

### 4.2 Startup Script (`~/flux/start.sh`)

```bash
#!/data/data/com.termux/files/usr/bin/bash
# Flux startup script

cd ~/flux
source venv/bin/activate

# Acquire wake lock	ermux-wake-lock

# Ensure storage paths exist
mkdir -p /storage/emulated/0/Flux/library/production
mkdir -p /storage/emulated/0/Flux/thumbnails
mkdir -p /storage/emulated/0/Flux/logs

# Run with auto-restart on crash
while true; do
    echo "[$(date)] Starting Flux daemon..." >> /storage/emulated/0/Flux/logs/app.log
    uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
    echo "[$(date)] Flux exited. Restarting in 10s..." >> /storage/emulated/0/Flux/logs/app.log
    sleep 10
done
```

### 4.3 Termux:Boot Integration

Create `~/.termux/boot/start-flux.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
# This runs on every boot
sshd  # Start SSH daemon
~/flux/start.sh &
```

Make executable:
```bash
chmod +x ~/.termux/boot/start-flux.sh
```

---

## 5. Reachability for GitHub Actions Watchdog

The phone needs a public URL for GitHub Actions to reach it. Cloudflare Tunnel is the recommended zero-config option.

```bash
# Download cloudflared binary for ARM64
cd ~
curl -L --output cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared

# Login (one-time; opens browser)
./cloudflared tunnel login

# Create and run tunnel (example)
./cloudflared tunnel create flux-phone
./cloudflared tunnel route dns flux-phone flux-phone.yourdomain.trycloudflare.com
# Run via tmux or integrate into start.sh
# To keep cloudflared running, add to start.sh before uvicorn:
#   nohup ~/cloudflared tunnel run flux-phone > /dev/null 2>&1 &
```

**Security:** The tunnel only needs to expose `/api/health` and `/api/system/remote`. The admin panel (`/admin/*`) must NOT be routed through the tunnel. Use `ingress` rules in `cloudflared config.yml` to restrict paths.

---

## 6. Remote Access Strategy

### 6.1 LAN Access (Primary)

The daemon binds to `127.0.0.1:8000`. The admin panel is never exposed to the local network. Access it via SSH port-forwarding:

```bash
# On your laptop, while on the same Wi-Fi:
ssh -L 8000:localhost:8000 <phone-ip> -p 8022
# Then open http://localhost:8000/admin in your browser
```

- Find phone IP: `ifconfig` or `ip addr show wlan0` in Termux.
- This also works over Tailscale: `ssh -L 8000:localhost:8000 100.x.x.x -p 8022`

### 6.2 Tailscale (Recommended for Remote)

Tailscale creates a secure mesh VPN. Install the **Tailscale Android app** (Play Store/F-Droid), sign in, and keep it running. Termux inherits the Tailscale network interface automatically.

```bash
# Verify Tailscale IP is reachable from Termux
ip addr show tun0

# Operator can SSH from anywhere:
# ssh user@100.x.x.x
# Or port-forward admin panel:
# ssh -L 8000:localhost:8000 100.x.x.x
```

**Why Tailscale:**
- No router port forwarding needed.
- Works across Wi-Fi, 4G, and changing IPs.
- Free for personal use (up to 20 devices).
- Admin panel stays on `127.0.0.1` — never exposed to local WiFi.

### 6.3 SSH Daemon

```bash
# Start SSH (already in boot script) — binds to 0.0.0.0:8022 by default in Termux
sshd

# Disable password auth; force key-only
mkdir -p ~/.ssh
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAA... your-key
EOF
chmod 600 ~/.ssh/authorized_keys
# No passwd setup = no password login possible
```

---

## 7. Watchdog & External Monitoring

### 7.1 Strategy: GitHub Actions Watchdog + Reachability Relay

The phone has no public IP. GitHub Actions runners are external. To bridge them, the phone maintains an outbound tunnel to a stable public URL.

**Reachability options (pick one):**

| Option | Setup | Pros | Cons |
|--------|-------|------|------|
| **Cloudflare Tunnel** | Install `cloudflared` binary in Termux | Free, stable URL, no open ports | Requires Cloudflare account |
| **Router DDNS + Port Forward** | Forward router port 8000 → phone:8000 | No third-party tunnel | Needs static IP or DDNS; blocked by CGNAT |
| **ngrok** | Run ngrok agent in Termux | Easy setup | Free URL changes every restart |

**Recommended:** Cloudflare Tunnel. It gives `https://flux-phone.yourdomain.trycloudflare.com` that survives reboots and IP changes.

### 7.2 GitHub Actions Watchdog

Free tier: 2,000 minutes/month. A 15-second `curl` check every 30 minutes = ~48 runs/day × 30 × 15s = **360 minutes/month**. Well within limits.

`.github/workflows/watchdog.yml`:
```yaml
name: Flux Watchdog
on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
  workflow_dispatch:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Health check
        run: |
          HEALTH_URL="${{ secrets.FLUX_HEALTH_URL }}"  # Cloudflare Tunnel URL
          STATUS=$(curl -fsS -o /dev/null -w "%{http_code}" "$HEALTH_URL/api/health" || echo "000")
          if [ "$STATUS" != "200" ]; then
            echo "Flux unreachable (HTTP $STATUS). Sending alert..."
            curl -s "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
              -d "chat_id=${{ secrets.TELEGRAM_CHAT_ID }}" \
              -d "text=🚨 Flux watchdog: unreachable (HTTP $STATUS)"
            exit 1
          fi
          echo "Flux healthy."
```

### 7.3 GitHub Actions Remote Trigger

`.github/workflows/remote-command.yml`:
```yaml
name: Remote Command
on:
  workflow_dispatch:
    inputs:
      command:
        description: 'Command'
        required: true
        default: 'status'
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -fsS -X POST "${{ secrets.FLUX_HEALTH_URL }}/api/system/remote" \
            -H "Authorization: Bearer ${{ secrets.FLUX_REMOTE_KEY }}" \
            -d "{\"command\":\"${{ github.event.inputs.command }}\"}"
```

Operator triggers from GitHub mobile app or web UI. Commands: `status`, `restart`, `trigger_fetch`, `trigger_post`.

---

## 8. Backup Strategy

### 7.1 What to Back Up

| Data | Location | Backup Method | Frequency |
|------|----------|---------------|-----------|
| SQLite DB | `~/flux/app.db` | `rclone` to cloud or `git` to private repo | Daily |
| `.env` secrets | `~/flux/.env` | Password manager (Bitwarden, KeePass) | On change |
| Rendered videos | External storage | Optional; can be re-rendered | — |
| Source clips | External storage | Not backed up; can re-download | — |
| Code | `~/flux/` | Git repository (GitHub/GitLab) | On every change |
| Bootstrap script | `~/flux/scripts/bootstrap.sh` | Version controlled | On every change |

### 7.2 Automated DB Backup

```bash
# Add to APScheduler: daily at 04:00
sqlite3 ~/flux/app.db ".backup '/storage/emulated/0/Flux/backups/app-$(date +%Y%m%d).db'"
# Keep last 7 backups, delete older
find /storage/emulated/0/Flux/backups/ -name "app-*.db" -mtime +7 -delete
```

---

## 9. Update & Maintenance

### 9.1 Updating the App

```bash
cd ~/flux
source venv/bin/activate

# Pull latest code
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Restart daemon
pkill -f uvicorn
# Boot script will auto-restart, or run manually
```

### 9.2 Updating yt-dlp

```bash
pip install -U yt-dlp
# Or via Termux package:
pkg upgrade yt-dlp
```

### 9.3 Log Rotation

```python
# Python logging config
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "/storage/emulated/0/Flux/logs/app.log",
    maxBytes=5_000_000,  # 5 MB
    backupCount=5
)
```

---

## 10. Disaster Recovery

| Scenario | Recovery Steps |
|----------|---------------|
| Phone dies / lost | Install Termux on new phone, clone repo, restore DB backup, copy `.env`, run start script. All media can be re-downloaded/re-rendered. |
| DB corruption | Restore from latest daily backup. If no backup, re-approve ingredients and re-render — posts history is lost but system function recovers. |
| Account banned | Create new account, add new worker, delete old worker. Pipelines unaffected. |
| Render engine broken | Switch to `-preset ultrafast` or 720p output via settings. Debug FFmpeg command separately. |
| Termux broken | Clear data, reinstall from F-Droid, run `termux-setup-storage`, re-run bootstrap. Config and media are on external storage. |
