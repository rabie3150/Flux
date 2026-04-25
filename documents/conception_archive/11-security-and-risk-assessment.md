# Flux — Security & Risk Assessment

## 1. Threat Model

Flux runs on a personal device, managed by a single operator. The primary threats are:

1. **Unauthorized access** to the admin panel or SSH.
2. **Credential theft** — social media API keys, tokens, session cookies.
3. **Platform account bans** — due to automated behaviour detection.
4. **Data loss** — phone failure, corruption, accidental deletion.
5. **Supply chain** — malicious plugin or dependency.
6. **Content integrity** — wrong verse, inappropriate background.

---

## 2. Access Control

### 2.1 Admin Panel

| Decision | Rationale |
|----------|-----------|
| **No username/password auth** | Single operator; access control is network-level. Adding auth adds complexity and false security on an untrusted network anyway. |
| **Bind to `127.0.0.1:8000`** | Only localhost. LAN access via SSH port-forward (`ssh -L 8000:localhost:8000 phone`). Tailscale access via same port-forward. Admin panel never exposed to local WiFi. |
| **Do not expose 8000 to internet** | No router port forwarding for admin panel. Cloudflare Tunnel (if used) only exposes `/api/health`, not `/admin`. |
| **Optional: API key for `/api/system/remote`** | GitHub Actions remote trigger uses bearer token. Endpoint whitelists safe commands only. |

### 2.2 SSH

| Control | Implementation |
|---------|----------------|
| Key-based auth only | `PasswordAuthentication no` in `sshd_config` |
| ED25519 keys | Preferred over RSA; shorter, stronger |
| No root login | Termux has no root anyway |
| Tailscale required for remote | SSH port not exposed to public internet |

### 2.3 Telegram Bot

| Control | Implementation |
|---------|----------------|
| Bot token in `.env` | Never committed to git |
| Chat ID allowlist | Only configured chat ID receives notifications; others ignored |
| No command execution | Bot is read-only (notifications); no `/restart` or `/exec` commands |

---

## 3. Credential Security

### 3.1 Encryption at Rest

All platform credentials stored in `platform_workers.credentials_json` are encrypted before storage.

```python
from cryptography.fernet import Fernet
import os

MASTER_KEY = os.environ["FLUX_MASTER_KEY"]  # 32-byte base64 URL-safe key

cipher = Fernet(MASTER_KEY)

# Store
encrypted = cipher.encrypt(credentials_json.encode())
# Retrieve
decrypted = cipher.decrypt(encrypted).decode()
```

| Requirement | Detail |
|-------------|--------|
| Key source | `FLUX_MASTER_KEY` environment variable or `.env` file |
| Key generation | `Fernet.generate_key()` — operator saves this once |
| Key backup | Stored in password manager; without it, all credentials are lost |
| Algorithm | Fernet (AES-128 in CBC mode + HMAC) |
| Rotation | Operator can re-encrypt all credentials with a new key via CLI command |

### 3.2 Credential Types by Platform

| Platform | Stored Credentials | Sensitivity |
|----------|-------------------|-------------|
| YouTube | OAuth refresh token | High — can upload/delete videos |
| Telegram | Bot token | High — can post to all channels |
| Instagram | Session JSON (cookies + uid) | High — can post/DM |
| TikTok | Session cookies | High |
| X/Twitter | API bearer token / session | High |
| Pexels | API key | Medium — rate limit abuse only |
| Unsplash | API key | Medium |

### 3.3 OAuth Flow (YouTube)

- Client secret JSON stored encrypted.
- OAuth consent flow performed once on the operator's laptop.
- Refresh token is stored and used indefinitely; no password stored.
- If refresh token expires, operator re-authenticates via admin panel.

---

## 4. Platform Ban Risk Mitigation

This is the highest operational risk for Flux.

### 4.1 Rate Limiting & Behaviour Mimicry

| Rule | Implementation |
|------|----------------|
| Max 1 post per day per account | Hard limit in scheduler |
| Post at human hours | Schedule window: 07:00–21:00 local time |
| Random delay before post | `randint(0, 600)` seconds jitter |
| Random delay between actions | If multi-posting, 30–120s gap |
| No simultaneous logins | One session per account; reuse session file |
| Realistic user agent | Instagrapi defaults are acceptable |

### 4.2 Platform-Specific Defences

| Platform | Additional Defence |
|----------|-------------------|
| Instagram | Use `instagrapi` with session reuse; avoid login storms; warm up new accounts with manual posts for 2 weeks before automation |
| TikTok | Unofficial API only; no Selenium on Termux. Limit to 1/week. Manual upload as fallback. |
| X/Twitter | API v2 free tier for text + media. Text-only fallback if media upload fails. No Selenium on Termux. |

### 4.3 Circuit Breaker

If a worker fails 3 consecutive posts:
1. Worker automatically paused.
2. Admin notified via Telegram.
3. Worker remains paused until admin manually investigates and resumes.

This prevents a misconfigured or banned account from hammering the platform and drawing more attention.

---

## 5. Content Integrity & Safety

### 5.1 Approval Gate

- **No automated content bypasses human review.**
- All ingredients start as `pending`.
- The operator must explicitly approve before use.
- Auto-approve can be enabled per ingredient type in settings, but is **disabled by default**.

### 5.2 Verse Identification Accuracy

| Tier | Method | Confidence | Action |
|------|--------|------------|--------|
| 1 | yt-dlp metadata regex | ~90% | Proceed if match |
| 2 | Whisper fuzzy match | ~70% | Proceed if confidence > 85% |
| 3 | Manual admin assignment | 100% | Required if tiers 1–2 fail |

**Rule:** Content with an unresolved `review_flag` in plugin metadata (e.g., `verse_unknown`) **cannot** enter the ready queue. The core engine checks the plugin metadata field; the specific reason is plugin-defined. It is a hard blocker.

### 5.3 Background Safety

| Control | Implementation |
|---------|----------------|
| Keyword allowlist | Only query Pexels/Unsplash with approved keywords |
| Keyword blocklist | Reject downloads matching blocklist |
| API safe-search | `?safe_search=true` on Pexels |
| Admin approval | All background media pending until approved |

---

## 6. Dependency & Supply Chain

| Control | Implementation |
|---------|----------------|
| Pin versions | All packages pinned in `requirements.txt` |
| Hash verification | Future: use `pip install --require-hashes` |
| Minimal dependencies | No heavy frameworks (no Django, no React build step) |
| Plugin audit | Plugin manifest validated; no network access during plugin load |
| No auto-update | Operator manually updates dependencies after reviewing changelogs |
| yt-dlp update | Weekly cron updates yt-dlp (trusted, high-velocity project) |

---

## 7. Data Privacy

| Principle | Implementation |
|-----------|----------------|
| No telemetry | Flux does not phone home; no analytics, no crash reporting |
| No cloud storage | All data stays on the phone |
| Minimal API exposure | Only platform APIs are called; no third-party tracking |
| Log sanitization | Credentials redacted from all logs |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation | Residual Risk |
|------|------------|--------|------------|---------------|
| SSH brute force | Low | High | Key-only auth, Tailscale, SSH on non-standard port (8022), no public IP | Very Low |
| Credential leak from backup | Low | High | Encrypt DB backups, password manager for `.env` | Very Low |
| Instagram ban | Medium | Medium | Rate limits, session reuse, circuit breaker | Low |
| TikTok ban | Medium | Medium | Minimal use, unofficial API only | Low |
| Wrong verse published | Low | Critical | 3-tier ID + manual block + no auto-publish unknown | Very Low |
| Inappropriate background | Low | Critical | Keyword filters + admin approval gate | Very Low |
| Phone theft | Low | Medium | No sensitive data on external storage; DB encrypted; admin panel on localhost only | Low |
| Malicious plugin | Low | High | Only install trusted plugins; review code; sandbox limited | Low |
| yt-dlp breaks | Medium | Low | Weekly auto-update; fetch failure is non-critical | Low |
| Storage full | Medium | Low | Hard budget + auto-cleanup + alerts | Very Low |
| SQLite corruption | Low | Medium | Daily backups + WAL mode | Very Low |

---

## 9. Incident Response Playbook

### 9.1 Account Banned

1. Check email/SMS for platform notice.
2. Log into platform manually to confirm.
3. In Flux admin: disable worker, note reason.
4. Create new account if appropriate.
5. Add new worker with fresh credentials.
6. Review recent posts for possible trigger (over-posting? flagged content?).

### 9.2 Wrong Content Published

1. Immediately delete post manually from platform if possible.
2. In Flux: mark post as `retracted` in post_records.
3. Investigate root cause: verse ID failure? Background leak?
4. Fix pipeline config or add manual review for affected content type.
5. Notify community if necessary (transparent correction).

### 9.3 Unauthorized Access Suspected

1. Check `activity_log` for unknown IPs or actions.
2. Rotate `FLUX_MASTER_KEY` and re-encrypt all credentials.
3. Rotate SSH keys.
4. Regenerate Telegram bot token.
5. Review platform sessions and revoke unknown ones.

### 9.4 Phone Lost or Stolen

1. Revoke all OAuth tokens via platform security pages (Google, Meta, X).
2. Regenerate Telegram bot token.
3. Set up Flux on replacement phone using code + DB backup.
4. Old phone's data is encrypted (Android FBE) but treat as compromised.
