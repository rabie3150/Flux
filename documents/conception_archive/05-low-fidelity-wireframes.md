# Flux — Low-Fidelity Wireframes (Blueprints)

These are **text-based wireframes** (ASCII/block diagrams) showing layout and element placement. No colours, no fonts — just structure, hierarchy, and flow.

---

## 1. Dashboard (`/admin`)

```
+-------------------------------------------------------------------+
|  FLUX                          Dashboard  Pipelines  Workers  ... |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  |  SYSTEM HEALTH   |  |  STORAGE         |  |  NEXT ACTIONS    | |
|  |  Uptime: 14d     |  |  [=======---]    |  |  Render: 02:00   | |
|  |  Status: Green   |  |  3.2 / 5 GB      |  |  Post: 08:30     | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                   |
|  PIPELINES                        PLATFORM WORKERS                |
|  +---------------------------+    +---------------------------+   |
|  | [Quran Daily]    [Active] |    | [YouTube Ch1]  [OK]      |   |
|  | Queue: 3 ready            |    | Last: yesterday           |   |
|  | Stock: 12 clips, 45 imgs  |    | Next: today 08:30         |   |
|  | [View] [Settings]         |    | [Post Now]                |   |
|  +---------------------------+    +---------------------------+   |
|  | [+ Add Pipeline]          |    | [Telegram]     [OK]      |   |
|  |                           |    | Last: yesterday           |   |
|  |                           |    | Next: today 08:30         |   |
|  |                           |    | [Post Now]                |   |
|  +---------------------------+    +---------------------------+   |
|                                                                   |
|  RECENT ACTIVITY                                                  |
|  +-------------------------------------------------------------+  |
|  | Icon | Time  | Event                              | Pipeline |  |
|  | ---- | ----  | -----                              | -------- |  |
|  | [v]  | 08:30 | Posted to YouTube — Al-Baqarah 255 | Quran    |  |
|  | [r]  | 02:15 | Rendered video #128                | Quran    |  |
|  | [f]  | 00:05 | Fetched 5 clips from Source A      | Quran    |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
+-------------------------------------------------------------------+
```

**Layout notes:**
- Top nav persistent across all screens.
- Pipeline and worker cards are the primary focus — these are the "things that run."
- Activity log is scrollable; last 20 events.

---

## 2. Pipeline Detail — Ingredients Tab

```
+-------------------------------------------------------------------+
|  FLUX     ...  Pipelines  >  Quran Daily  >  Ingredients          |
+-------------------------------------------------------------------+
|                                                                   |
|  [Overview]  [INGREDIENTS]  [Production]  [Settings]              |
|                                                                   |
|  Filter: [All types v]  [All statuses v]  [Source: All v]         |
|                                                                   |
|  Bulk: [Approve selected] [Reject selected] [Delete selected]     |
|                                                                   |
|  +--------+  +--------+  +--------+  +--------+  +--------+       |
|  | [img]  |  | [img]  |  | [img]  |  | [img]  |  | [img]  |       |
|  | Clip #1|  | Clip #2|  | Img #1 |  | Img #2 |  | Vid #1 |       |
|  | 0:45   |  | 1:02   |  |        |  |        |  | 0:15   |       |
|  | [PEND] |  | [PEND] |  | [OK]   |  | [OK]   |  | [OK]   |       |
|  | [x]    |  | [x]    |  | [x]    |  | [ ]    |  | [ ]    |       |
|  +--------+  +--------+  +--------+  +--------+  +--------+       |
|                                                                   |
|  +--------+  +--------+  +--------+                               |
|  | [img]  |  | [img]  |  | [img]  |                               |
|  | Clip #3|  | Img #3 |  | Img #4 |                               |
|  | 0:30   |  |        |  |        |                               |
|  | [REJ]  |  | [OK]   |  | [PEND] |                               |
|  | [x]    |  | [ ]    |  | [x]    |                               |
|  +--------+  +--------+  +--------+                               |
|                                                                   |
|  Page [1] 2 3 ...  [20 per page v]                                |
+-------------------------------------------------------------------+
```

**Layout notes:**
- Grid of cards, 5 columns on desktop, 2 on mobile.
- Each card: thumbnail, title, duration, status badge (colour-coded in final), checkbox for bulk.
- Clicking a card opens a modal/preview overlay.

---

## 3. Pipeline Detail — Production Queue Tab

```
+-------------------------------------------------------------------+
|  FLUX     ...  Pipelines  >  Quran Daily  >  Production           |
+-------------------------------------------------------------------+
|                                                                   |
|  [Overview]  [Ingredients]  [PRODUCTION]  [Settings]              |
|                                                                   |
|  Status: [All v]  [Rendering]  [Ready]  [Published]  [Failed]     |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  | Thmb | Verse Ref        | BG Mode | Timing | Date   | Status |  |
|  | ---- | ---------        | ------- | ------ | ----   | ------ |  |
|  | [t]  | Al-Baqarah 2:255 | video   | medium | Apr 24 | READY  |  |
|  |      |                  |         |        |        | [Post] |  |
|  +-------------------------------------------------------------+  |
|  | [t]  | An-Nisa 4:59     | images  | fast   | Apr 23 | PUBLISH|  |
|  |      |                  |         |        |        | [View] |  |
|  +-------------------------------------------------------------+  |
|  | [t]  | Unknown          | video   | slow   | Apr 23 | UNKNWN |  |
|  |      |                  |         |        |        | [Fix]  |  |
|  +-------------------------------------------------------------+  |
|  | [t]  | Al-Fatiha 1:1    | images  | ken    | Apr 22 | FAIL   |  |
|  |      |                  |         |        |        | [Retry]|  |
|  +-------------------------------------------------------------+  |
|                                                                   |
+-------------------------------------------------------------------+
```

**Layout notes:**
- Table view for production queue — more data-dense than cards.
- Status is the primary visual differentiator.
- "Unknown" status has a prominent "Fix" action to assign verse reference.

---

## 4. Worker Detail / Config

```
+-------------------------------------------------------------------+
|  FLUX     ...  Workers  >  YouTube Channel 1                      |
+-------------------------------------------------------------------+
|                                                                   |
|  [Overview]  [Schedule]  [CAPTION]  [Logs]                        |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  |  Platform: YouTube                                          |  |
|  |  Account:  MyQuranChannel                                   |  |
|  |  Status:   Active (last post: Apr 24 08:30)                 |  |
|  |  Pipelines attached: Quran Daily                            |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  SCHEDULE                                                         |
|  +-------------------------------------------------------------+  |
|  |  Mode: ( ) Manual only   (*) Cron expression                |  |
|  |  Cron: [0 8 * * *         ]  (= daily at 08:00)             |  |
|  |  Timezone: [UTC v]                                          |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  CAPTION OVERRIDE                                                 |
|  +-------------------------------------------------------------+  |
|  |  [x] Use global template                                    |  |
|  |  [ ] Use custom template                                    |  |
|  |  Template:                                                  |  |
|  |  +-------------------------------------------------------+  |  |
|  |  | {verse_ref}                                            |  |  |
|  |  | {arabic_text}                                          |  |  |
|  |  | {translation}                                          |  |  |
|  |  | Follow for daily Quran verses. #islam #quran          |  |  |
|  |  +-------------------------------------------------------+  |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  HASHTAGS                                                         |
|  +-------------------------------------------------------------+  |
|  |  [islam] [quran] [muslim] [dailyquran] [islamicreminder]   |  |
|  |  [+ Add hashtag]                                            |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  DANGER ZONE                                                      |
|  +-------------------------------------------------------------+  |
|  |  [Disconnect Account]  [Delete Worker & History]            |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
+-------------------------------------------------------------------+
```

**Layout notes:**
- Tabbed interface for different config categories.
- Danger zone at bottom, visually separated.
- Caption template uses variable substitution (`{verse_ref}`, etc.).

---

## 5. System Settings — Global

```
+-------------------------------------------------------------------+
|  FLUX     ...  System  >  Settings                                |
+-------------------------------------------------------------------+
|                                                                   |
|  [General]  [Library]  [Sources]  [Captions]  [Timing]  [Security]
|                                                                   |
|  GENERAL                                                          |
|  +-------------------------------------------------------------+  |
|  |  Storage budget (GB):        [ 5        ]                   |  |
|  |  Auto-delete published:      [x] Yes  ( ) No                |  |
|  |  Timezone:                   [Africa/Casablanca v]          |  |
|  |  Telegram alert chat ID:     [123456789 ]                   |  |
|  |  Log retention (days):       [ 7        ]                   |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  RENDER SETTINGS                                                  |
|  +-------------------------------------------------------------+  |
|  |  Max concurrent renders:     [ 1        ]                   |  |
|  |  Thermal pause threshold:    [ 45 degrees C ]               |  |
|  |  Default preset:             [medium v]  (ultrafast, fast)  |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|  [Save Changes]  [Reset to Defaults]                              |
|                                                                   |
+-------------------------------------------------------------------+
```

**Layout notes:**
- Form-based settings with clear labels and input types.
- Tabbed categories prevent overwhelming the user.
- Save/Reset actions are sticky or at bottom.

---

## 6. Mobile Compact View (Admin Panel on Phone Browser)

Since the admin panel is accessed on the phone's own browser occasionally, the layout collapses:

```
+------------------+
| FLUX    [=] Menu |
+------------------+
| System: Green    |
| Storage: 3.2/5GB |
+------------------+
| [Quran Daily]    |
| Queue: 3 ready   |
| [View Pipeline >]|
+------------------+
| [YouTube Ch1]    |
| Next: 08:00      |
| [Post Now]       |
+------------------+
| [Telegram]       |
| Next: 08:00      |
| [Post Now]       |
+------------------+
| Recent Activity  |
| [v] 08:30 Posted |
| [r] 02:15 Render |
| [f] 00:05 Fetch  |
+------------------+
```

**Layout notes:**
- Single column, stacked cards.
- Hamburger menu for navigation.
- Touch-friendly buttons (min 44px height).
- Activity log truncated to 5 items.

---

## 7. Modal — Ingredient Preview & Approval

```
+------------------------------------------+
|  Preview Ingredient            [X]       |
+------------------------------------------+
|                                          |
|  +------------------------------------+  |
|  |                                    |  |
|  |         [VIDEO PREVIEW]            |  |
|  |         (or image thumbnail)       |  |
|  |                                    |  |
|  +------------------------------------+  |
|                                          |
|  Title:    Al-Baqarah 2:255 — Ayatul    |
|            Kursi (source: YouTube)       |
|  Duration: 0:58                          |
|  Size:     4.2 MB                        |
|  Source:   youtube.com/watch?v=...       |
|                                          |
|  Status:   PENDING APPROVAL              |
|                                          |
|  [  Approve  ]  [  Reject  ]  [Skip]    |
+------------------------------------------+
```

**Layout notes:**
- Modal overlays the current screen; background dims.
- Primary action (Approve) is the most prominent button.
- Source link opens in new tab.
