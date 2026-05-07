#!/usr/bin/env bash
# Cloudflare Tunnel setup for Flux on Termux (ARM64)
#
# This script downloads cloudflared, creates a tunnel, and configures
# restricted ingress rules so only /api/health and /api/system/remote
# are exposed — the admin panel stays localhost-only.
#
# Usage:
#   chmod +x scripts/setup_cloudflare_tunnel.sh
#   ./scripts/setup_cloudflare_tunnel.sh
#
# Prerequisites:
#   - Cloudflare account with a domain (free plan works)
#   - Or use a quick tunnel (no domain needed) for testing

set -euo pipefail

CLOUDFLARED_BIN="$HOME/bin/cloudflared"
TUNNEL_NAME="${FLUX_TUNNEL_NAME:-flux-phone}"
CONFIG_DIR="$HOME/.cloudflared"
CONFIG_FILE="$CONFIG_DIR/config.yml"

echo "=== Flux Cloudflare Tunnel Setup ==="

# ── 1. Download cloudflared if not present ────────────────────────────
if [ ! -f "$CLOUDFLARED_BIN" ]; then
    echo "[1/5] Downloading cloudflared for ARM64..."
    mkdir -p "$(dirname "$CLOUDFLARED_BIN")"

    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) BINARY_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" ;;
        x86_64|amd64)  BINARY_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
        armv7l|armhf)  BINARY_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm" ;;
        *)             echo "[ERROR] Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    curl -L --output "$CLOUDFLARED_BIN" "$BINARY_URL"
    chmod +x "$CLOUDFLARED_BIN"
    echo "[OK] cloudflared downloaded to $CLOUDFLARED_BIN"
else
    echo "[1/5] cloudflared already installed at $CLOUDFLARED_BIN"
fi

$CLOUDFLARED_BIN version

# ── 2. Authenticate (one-time) ────────────────────────────────────────
if [ ! -f "$CONFIG_DIR/cert.pem" ]; then
    echo ""
    echo "[2/5] Authenticating with Cloudflare..."
    echo "  A browser will open. Authorize the tunnel for your domain."
    echo "  If no browser is available, copy the URL and open it manually."
    echo ""
    $CLOUDFLARED_BIN tunnel login
else
    echo "[2/5] Already authenticated (cert.pem exists)"
fi

# ── 3. Create tunnel ─────────────────────────────────────────────────
EXISTING=$($CLOUDFLARED_BIN tunnel list | grep "$TUNNEL_NAME" || true)
if [ -z "$EXISTING" ]; then
    echo "[3/5] Creating tunnel: $TUNNEL_NAME"
    $CLOUDFLARED_BIN tunnel create "$TUNNEL_NAME"
else
    echo "[3/5] Tunnel '$TUNNEL_NAME' already exists"
fi

# Get tunnel UUID
TUNNEL_UUID=$($CLOUDFLARED_BIN tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo "  Tunnel UUID: $TUNNEL_UUID"

# ── 4. Generate config ───────────────────────────────────────────────
echo "[4/5] Generating config at $CONFIG_FILE"
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" << EOF
# Flux Cloudflare Tunnel Configuration
# Only exposes health and remote endpoints — admin panel stays private.
tunnel: $TUNNEL_UUID
credentials-file: $CONFIG_DIR/$TUNNEL_UUID.json

ingress:
  # Health check — required by GitHub Actions watchdog
  - hostname: "*"
    path: /api/health
    service: http://localhost:8000
  # Remote command — required by GitHub Actions remote trigger
  - hostname: "*"
    path: /api/system/remote
    service: http://localhost:8000
  # Block everything else (admin panel, API, etc.)
  - service: http_status:404
EOF
echo "[OK] Config written"

# ── 5. Instructions ──────────────────────────────────────────────────
echo ""
echo "[5/5] Setup complete!"
echo ""
echo "  To start the tunnel:"
echo "    $CLOUDFLARED_BIN tunnel run $TUNNEL_NAME"
echo ""
echo "  To start automatically with Flux, add to scripts/start.sh:"
echo "    nohup $CLOUDFLARED_BIN tunnel run $TUNNEL_NAME > /dev/null 2>&1 &"
echo ""
echo "  To route DNS (replace with your domain):"
echo "    $CLOUDFLARED_BIN tunnel route dns $TUNNEL_NAME flux.$YOUR_DOMAIN"
echo ""
echo "  For quick testing without a domain:"
echo "    $CLOUDFLARED_BIN tunnel --url http://localhost:8000"
echo "    (generates a temporary *.trycloudflare.com URL)"
echo ""
echo "  GitHub Secrets to set:"
echo "    FLUX_HEALTH_URL = https://flux.yourdomain.com"
echo "    FLUX_REMOTE_KEY = (same as FLUX_REMOTE_KEY in .env)"
echo "    TELEGRAM_BOT_TOKEN = (your bot token)"
echo "    TELEGRAM_CHAT_ID = (your chat ID)"
