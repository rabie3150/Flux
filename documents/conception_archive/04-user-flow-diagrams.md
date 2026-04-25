# Flux — User Flow Diagrams (Logic Flows)

All flows are described in **Mermaid diagram syntax** and plain-English walkthroughs. These represent the "hallways" between the "rooms" defined in the Information Architecture.

---

## 1. First-Time Setup Flow

The operator installs Flux on Termux and gets the first pipeline running.

```mermaid
flowchart TD
    A[Install Termux + packages] --> B[Run bootstrap script]
    B --> C{Bootstrap OK?}
    C -->|No| D[Check error log]
    D --> B
    C -->|Yes| E[Edit .env with API keys]
    E --> F[Start uvicorn daemon]
    F --> G[Port-forward admin panel: ssh -L 8000:localhost:8000 phone]
    G --> H[Open http://localhost:8000/admin]
    H --> I[First-run wizard]
    I --> J[Add YouTube channel to whitelist]
    J --> K[Add platform workers]
    K --> L[Trigger first fetch job]
    L --> M{Fetch successful?}
    M -->|No| N[Check source settings & retry]
    N --> L
    M -->|Yes| O[Clips appear in Pending]
    O --> P[Operator approves clips]
    P --> Q[System renders first video]
    Q --> R[Video enters Ready queue]
    R --> S[Operator tests manual post]
    S --> T[Enable daily schedule]
    T --> U[Setup complete]
```

**Key Decision Nodes:**
- Bootstrap OK? → Environment detection (Python version, FFmpeg, yt-dlp).
- Fetch successful? → Source validation (channel public? API key valid?).

---

## 2. Daily Autonomous Run Flow

The system runs without operator interaction for a typical 24-hour cycle.

```mermaid
flowchart TD
    A[00:00 Daemon heartbeat] --> B[Check schedules]
    B --> C{Any triggers?}
    C -->|No| Z[Idle until next check]
    C -->|Yes| D[Evaluate stock levels]
    D --> E{Stock below minimum?}
    E -->|Yes| F[Trigger fetch job]
    E -->|No| G[Skip fetch]
    F --> H{Storage budget OK?}
    H -->|No| I[Alert admin & pause fetch]
    H -->|Yes| J[Download ingredients]
    J --> K[Notify admin: N items pending]
    K --> Z
    G --> L[Check render queue]
    L --> M{Videos ready to render?}
    M -->|Yes| N[Acquire render lock]
    N --> O[FFmpeg render]
    O --> P{Render success?}
    P -->|No| Q[Mark failed, log error, alert if repeated]
    P -->|Yes| R[Extract thumbnail]
    R --> S[Verse identification]
    S --> T{Verse known?}
    T -->|No| U[Mark content_meta review_flag, notify admin]
    T -->|Yes| V[Build caption]
    V --> W[Move to Ready queue]
    W --> Z
    M -->|No| X[Check publish schedules]
    X --> Y{Any workers due?}
    Y -->|No| Z
    Y -->|Yes| AA[Select next unpublished video]
    AA --> AB[Post to platform]
    AB --> AC{Post success?}
    AC -->|No| AD[Retry 3× with backoff]
    AD --> AE{Still failed?}
    AE -->|Yes| AF[Flag worker error, notify admin]
    AE -->|No| W
    AC -->|Yes| AG[Record post, update status]
    AG --> AH{Auto-delete enabled?}
    AH -->|Yes| AI[Delete local MP4, keep metadata]
    AH -->|No| Z
    AI --> Z
```

**Idempotency Guards:**
- Render lock: only one FFmpeg process at a time.
- Post uniqueness: `(produced_content_id, worker_id)` unique constraint prevents duplicates.
- Schedule evaluation: APScheduler persists jobs in SQLite; resumes after reboot.

---

## 3. Admin Approval Flow

Operator reviews pending ingredients.

```mermaid
flowchart TD
    A[Admin receives Telegram alert] --> B[Opens admin panel]
    B --> C[Navigates to Ingredient Library]
    C --> D[Filters: Status = Pending]
    D --> E[Reviews item thumbnail/preview]
    E --> F{Content appropriate?}
    F -->|Yes| G[Clicks Approve]
    G --> H[Item enters approved pool]
    H --> I{Batch approve?}
    I -->|Yes| J[Selects multiple, clicks Bulk Approve]
    I -->|No| K[Done]
    F -->|No| L[Clicks Reject]
    L --> M[Item marked rejected]
    M --> N{Auto-delete rejected?}
    N -->|Yes| O[Delete file, reclaim storage]
    N -->|No| P[Keep file, marked rejected]
```

---

## 4. Adding a Platform Worker Flow

Operator connects a new social media account.

```mermaid
flowchart TD
    A[Admin opens Workers page] --> B[Clicks Add Worker]
    B --> C[Selects platform: YouTube / Telegram / Instagram / TikTok / X]
    C --> D{Platform?}
    D -->|YouTube| E[Upload OAuth client_secret.json]
    E --> F[Browser opens for OAuth consent]
    F --> G[Tokens stored encrypted]
    D -->|Telegram| H[Enter bot token + channel ID]
    H --> I[Test post to channel]
    D -->|Instagram| J[Enter username/password or session JSON]
    J --> K[System validates login via Instagrapi]
    D -->|TikTok / X| L[Enter session cookies or API keys]
    L --> M[Test login via API or manual session import]
    G --> N[Configure schedule]
    I --> N
    K --> N
    M --> N
    N --> O[Optional: caption override & hashtags]
    O --> P[Associate with pipeline(s)]
    P --> Q[Worker active]
```

---

## 5. Future Pipeline Creation Flow

Adding a new content type (e.g., "Daily Hadith") after Quran is stable.

```mermaid
flowchart TD
    A[Operator decides new content type] --> B[Writes or downloads plugin]
    B --> C[Places plugin in ./plugins/{name}/]
    C --> D[Restarts daemon]
    D --> E{Plugin valid?}
    E -->|No| F[Read validation errors in logs]
    F --> B
    E -->|Yes| G[Plugin appears in Plugin Manager]
    G --> H[Enable plugin]
    H --> I[Create new Pipeline]
    I --> J[Select plugin: Hadith]
    J --> K[Configure plugin-specific sources]
    K --> L[Assign platform workers]
    L --> M[Set schedule]
    M --> N[Pipeline runs first cycle]
```

**Plugin Validation Checks:**
- `plugin.yaml` manifest present and schema-valid.
- Required hooks implemented: `fetch()`, `render()`, `build_caption()`.
- API version compatibility.
- No filename collisions with core.

---

## 6. Error Recovery Flow

What happens when things go wrong.

```mermaid
flowchart TD
    A[Error detected] --> B{Error type?}
    B -->|Fetch fail| C[Log error, skip source, retry next cycle]
    B -->|Render fail| D[Mark video failed, release render lock, alert if 3+ consecutive]
    B -->|Post fail| E[Retry 3× with backoff]
    E --> F{Still failing?}
    F -->|Yes| G[Mark worker error, pause worker, notify admin]
    F -->|No| H[Post succeeded, clear error]
    B -->|Storage full| I[Pause all fetch & render jobs, notify admin]
    B -->|Phone reboot| J[Termux:Boot restarts daemon]
    J --> K[APScheduler resumes from SQLite]
    K --> L[Mark interrupted renders as pending]
    B -->|Verse unknown| M[Move to manual-review queue]
    M --> N[Admin assigns verse via UI]
    N --> O[Resume pipeline]
```

---

## 7. Remote SSH Management Flow

Operator accesses the system remotely.

```mermaid
flowchart TD
    A[Operator away from home] --> B[SSH into phone via reverse tunnel or DDNS]
    B --> C{SSH success?}
    C -->|No| D[Check GitHub Actions watchdog status]
    D --> E[Trigger remote wake/restart via GitHub Action]
    C -->|Yes| F[Option 1: CLI management]
    F --> G[Read logs, restart daemon, check storage]
    C -->|Yes| H[Option 2: Port-forward admin panel]
    H --> I[ssh -L 8000:localhost:8000 phone]
    I --> J[Open http://localhost:8000/admin on laptop]
    J --> K[Full admin access as if on LAN]
```

**Security note:** SSH is key-based only. Admin panel remains bound to localhost during remote access; port-forwarding is the secure tunnel.
