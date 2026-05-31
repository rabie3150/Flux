# Generation Dashboard Design

> **Approach:** A — "Mission Control" Dashboard  
> **Date:** 2026-05-31

## Problem
Current GenerateScreen duplicates settings (source/target lang, theme, word count) and has poor step visualization — just a progress bar + plain text.

## Solution
Replace with a single-screen dashboard: read-only mission card, step timeline, word preview, and result panel.

## Layout (Terminal)
```
┌─ Flux Language Shorts ───────────────────────────────┐
│ Mission: 5 Italian Food Words                       │
│ English → Italian  |  Theme: food  |  TTS: Edge     │
│ Source: Aria  |  Target: Elsa                       │
│                                                     │
│ [      🚀  GENERATE      ]                          │
├─ Pipeline ──────────────────────┬─ Words Preview ──┤
│ ✓ Vocabulary     5 words        │ 1. Hello → Ciao  │
│ ✓ Backgrounds    3 images       │ 2. Water → Acqua │
│ ⏳ TTS Audio     Word 3/5       │ 3. Bread → Pane  │
│ ○ FFmpeg Render                 │ 4. ...           │
│                                 │ 5. ...           │
├─ Result ────────────────────────────────────────────┤
│ [bold green]Saved: .\output\lang_food_12345.mp4    │
│ [Open Folder]                                       │
└─────────────────────────────────────────────────────┘
```

## Components

### Mission Card (top)
- Pulled entirely from `AppConfig` — no editable inputs
- Shows: source→target languages, word count, theme, TTS provider, voice names
- One prominent **"Generate"** button (primary variant)

### Step Timeline (left, ~40% width)
Vertical list of 4 steps, each with:
- Icon: `○` pending / `⏳` active / `✓` complete / `✗` failed
- Step name
- Detail text (e.g., "5 words", "3 images", "Word 3/5", "1:00 elapsed")

Steps:
1. **Vocabulary** — call Gemini, show word count when done
2. **Backgrounds** — fetch images, show count when done
3. **TTS Audio** — synthesize audio, show `Word N/M` progress
4. **FFmpeg Render** — compose video, show elapsed time

### Words Preview (right, ~60% width)
- `DataTable` with columns: `#`, `Source`, `Target`, `Phonetic`
- Populates after vocab step completes
- Zebra stripes, read-only

### Result Panel (bottom, auto-height)
- Hidden until generation completes
- Shows: output path, file size, duration estimate
- Buttons: **Open Folder**, **Generate Another**

## States

| State | Mission Card | Timeline | Words | Result |
|-------|-------------|----------|-------|--------|
| Idle | Visible | All pending | Empty | Hidden |
| Running | Disabled button | Active step highlighted | Fills after step 1 | Hidden |
| Success | "Generate Another" button | All complete | Full table | Shown |
| Failed | "Retry" button | Failed step red | Partial | Error message |

## Keyboard / Mouse
- **Tab** cycles: Generate button → Open Folder → Generate Another
- **Enter** activates focused button
- **Mouse click** on any button
- **g** shortcut on MainScreen to jump directly to Generate

## No Duplication Rule
All config lives in Settings. Generate screen is purely:
- Read-only display of current config
- One-shot execution
- Result presentation
