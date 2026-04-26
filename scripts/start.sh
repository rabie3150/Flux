#!/data/data/com.termux/files/usr/bin/bash
# Flux startup script

set -e

FLUX_DIR="$HOME/flux"
cd "$FLUX_DIR"

# Activate virtual environment
source venv/bin/activate

# Acquire wake lock
termux-wake-lock

# Ensure external storage paths exist
mkdir -p /storage/emulated/0/Flux/library/production
mkdir -p /storage/emulated/0/Flux/thumbnails
mkdir -p /storage/emulated/0/Flux/logs
mkdir -p /storage/emulated/0/Flux/backups

# Enable WAL mode on startup (fallback to python if sqlite3 CLI missing)
python -c "import sqlite3; conn=sqlite3.connect('$FLUX_DIR/app.db'); conn.execute('PRAGMA journal_mode=WAL'); conn.close()" 2>/dev/null || true

# Run with auto-restart on crash
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Flux daemon..." >> /storage/emulated/0/Flux/logs/app.log
    uvicorn flux.main:app --host 127.0.0.1 --port 8000 --log-level info
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Flux exited. Restarting in 10s..." >> /storage/emulated/0/Flux/logs/app.log
    sleep 10
done
