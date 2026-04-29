# Phase 4 Detailed Plan: Content ID & Captions (Updated with Gemini AI)

## 1. Goal
Transform rendered video files into "ready-to-post" packages by identifying the Quranic verse reference, fetching its text/translations, and generating platform-optimized captions.

## 2. Technical Architecture

### 2.1 Verse Identification Pipeline (3-Tier Fallback)
The identification process runs as a post-render job in the `identifying` state.

| Tier | Method | Logic | Confidence |
|------|--------|-------|------------|
| **1** | **Metadata Regex** | Parse `quran_clip` title/description using surah mappings. | High (90%) |
| **2** | **Gemini AI Fallback** | Send video file or YouTube URL to Gemini API with specialized prompt. | High (85%) |
| **3** | **Manual UI** | Admin assigns verse via the dashboard production queue. | Absolute |

### 2.2 Gemini AI Integration & Key Rotation
- **API Keys:** Loaded from `GEMINI_API_KEYS` in `.env` as a JSON list.
- **Rotation:** Automatically switch to the next key on 429 (Rate Limit) or 401 (Invalid Key).
- **Service:** `GeminiAIClient` handles prompt engineering and response parsing.

### 2.3 Verse Data Service (quran.com)
- **Primary API:** `api.quran.com/api/v4`
- **Data Points:** Arabic Uthmani text, Sahih International translation, Tafseer (Kathir) snippet.
- **Cache Layer:** Persistent SQLite table `verse_cache` (Verse text is immutable).

---

## 3. Implementation Tasks

### 3.1 Core Engine Infrastructure
- [x] Add `identifying` status to `ProducedContent` in `models.py`.
- [ ] Implement `identify_produced_content` in `flux/core/pipeline.py`.
- [ ] Update `trigger_render` to automatically queue identification on success.

### 3.2 Identification Engine (`flux/plugins/quran/identify.py`)
- [x] Implement robust regex for 114 surahs (English/Arabic/Transliterated).
- [ ] Implement `identify_from_ai` (Gemini wrapper with key rotation).
- [ ] Implement pattern analysis based on 15 samples from `@Am9li9/shorts`.

### 3.3 Data Service (`flux/plugins/quran/api.py`)
- [ ] Implement `QuranAPIClient` (async httpx).
- [ ] Implement `VerseService` with `verse_cache` logic.

### 3.4 Caption Service (`flux/plugins/quran/plugin.py`)
- [ ] Implement `build_caption` hook.
- [ ] Define default Jinja2 templates for target platforms.

### 3.5 Admin UI Enhancements
- [ ] Add "Assign Verse" button to production queue table.
- [ ] Create reactive modal (Alpine.js) for manual surah/ayah selection.

---

## 4. Success Metrics
1. 80%+ of "clean" titles are auto-identified via regex.
2. Gemini fallback identifies 95%+ of remaining videos accurately.
3. No repeated API calls to quran.com for the same verse.
