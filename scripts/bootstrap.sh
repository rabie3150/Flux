#!/data/data/com.termux/files/usr/bin/bash
# Flux bootstrap script for Termux
# Usage: curl -fsSL https://raw.githubusercontent.com/YOURNAME/flux/main/scripts/bootstrap.sh | bash

set -e

REPO_URL="https://github.com/YOURNAME/flux.git"
FLUX_DIR="$HOME/flux"

echo "[Flux] Bootstrapping..."

# 1. Grant storage permission
if [ ! -d /storage/emulated/0/Flux ]; then
    echo "[Flux] Run 'termux-setup-storage' if this fails..."
fi

# 2. Install system dependencies
pkg update -y
pkg install -y python ffmpeg git openssh yt-dlp clang make libjpeg-turbo libpng termux-api termux-boot

# 3. Create project directory
mkdir -p "$FLUX_DIR"
cd "$FLUX_DIR"

# 4. Clone or pull
if [ ! -d .git ]; then
    echo "[Flux] Cloning repository..."
    git clone "$REPO_URL" .
else
    echo "[Flux] Pulling latest..."
    git pull origin main
fi

# 5. Python environment
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Ensure storage paths
mkdir -p /storage/emulated/0/Flux/library/production
mkdir -p /storage/emulated/0/Flux/thumbnails
mkdir -p /storage/emulated/0/Flux/logs
mkdir -p /storage/emulated/0/Flux/backups

# 7. Initialize database (if not exists)
if [ ! -f "$FLUX_DIR/app.db" ]; then
    echo "[Flux] Initializing database..."
    python -c "import asyncio; from flux.db import init_db; asyncio.run(init_db())" 2>/dev/null || true
fi

# 8. Enable WAL mode
sqlite3 "$FLUX_DIR/app.db" "PRAGMA journal_mode=WAL;" 2>/dev/null || true

# 9. Setup Termux:Boot
mkdir -p "$HOME/.termux/boot"
cp "$FLUX_DIR/scripts/start.sh" "$HOME/.termux/boot/start-flux.sh"
chmod +x "$HOME/.termux/boot/start-flux.sh"

# 10. Create .env if missing
if [ ! -f "$FLUX_DIR/.env" ]; then
    cp "$FLUX_DIR/.env.example" "$FLUX_DIR/.env"
    echo "[Flux] Created .env — edit it with your secrets!"
fi

echo "[Flux] Bootstrap complete."
echo "[Flux] Next steps:"
echo "    1. Edit $FLUX_DIR/.env with your API keys"
echo "    2. Run: $FLUX_DIR/scripts/start.sh"
echo "    3. Port-forward: ssh -L 8000:localhost:8000 <phone-ip> -p 8022"
