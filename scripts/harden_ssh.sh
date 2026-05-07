#!/usr/bin/env bash
# SSH hardening for Flux on Termux
#
# Disables password authentication and enforces key-only access.
# Run this AFTER you've added your SSH public key to authorized_keys.
#
# Usage:
#   chmod +x scripts/harden_ssh.sh
#   ./scripts/harden_ssh.sh

set -euo pipefail

SSH_DIR="$HOME/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"

echo "=== Flux SSH Hardening ==="

# ── 1. Ensure .ssh directory exists with correct permissions ──────────
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# ── 2. Check authorized_keys ─────────────────────────────────────────
if [ ! -f "$AUTH_KEYS" ]; then
    echo ""
    echo "[ERROR] No authorized_keys file found at $AUTH_KEYS"
    echo ""
    echo "  Add your public key first:"
    echo "    echo 'ssh-ed25519 AAAA... your-key' >> $AUTH_KEYS"
    echo ""
    echo "  Then re-run this script."
    exit 1
fi

KEY_COUNT=$(grep -c '^ssh-' "$AUTH_KEYS" 2>/dev/null || echo "0")
if [ "$KEY_COUNT" -eq "0" ]; then
    echo ""
    echo "[ERROR] authorized_keys exists but contains no SSH keys."
    echo "  Add your public key and re-run."
    exit 1
fi

chmod 600 "$AUTH_KEYS"
echo "[1/4] authorized_keys: $KEY_COUNT key(s) found"

# ── 3. Disable password authentication ───────────────────────────────
# In Termux, sshd config is at $PREFIX/etc/ssh/sshd_config
SSHD_CONFIG="${PREFIX:-/usr}/etc/ssh/sshd_config"

if [ -f "$SSHD_CONFIG" ]; then
    # Backup original
    cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.$(date +%Y%m%d)" 2>/dev/null || true

    # Apply hardening settings
    apply_setting() {
        local key="$1"
        local value="$2"
        if grep -q "^${key}" "$SSHD_CONFIG"; then
            sed -i "s/^${key}.*/${key} ${value}/" "$SSHD_CONFIG"
        elif grep -q "^#${key}" "$SSHD_CONFIG"; then
            sed -i "s/^#${key}.*/${key} ${value}/" "$SSHD_CONFIG"
        else
            echo "${key} ${value}" >> "$SSHD_CONFIG"
        fi
    }

    apply_setting "PasswordAuthentication" "no"
    apply_setting "PermitEmptyPasswords" "no"
    apply_setting "ChallengeResponseAuthentication" "no"
    apply_setting "PubkeyAuthentication" "yes"
    apply_setting "PrintMotd" "no"
    apply_setting "PrintLastLog" "yes"

    echo "[2/4] sshd_config hardened (password auth disabled)"
else
    echo "[2/4] sshd_config not found at $SSHD_CONFIG (Termux may use different path)"
    echo "  In Termux, password auth is disabled by default when no password is set."
    echo "  Ensure you have NOT run 'passwd' to set a password."
fi

# ── 4. Restart sshd ──────────────────────────────────────────────────
if command -v sshd &>/dev/null; then
    pkill sshd 2>/dev/null || true
    sshd
    echo "[3/4] sshd restarted with hardened config"
else
    echo "[3/4] sshd not found — install with: pkg install openssh"
fi

# ── 5. Summary ────────────────────────────────────────────────────────
echo "[4/4] Done!"
echo ""
echo "  SSH is now configured for key-only access."
echo "  Test from your laptop:"
echo "    ssh -p 8022 $(whoami)@<phone-ip>"
echo ""
echo "  If locked out, use Termux app directly to fix authorized_keys."
