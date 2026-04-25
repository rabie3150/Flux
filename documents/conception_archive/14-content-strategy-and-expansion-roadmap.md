# Flux — Content Strategy & Expansion Roadmap

## 1. Content Philosophy

Flux is not a "Quran app." It is an **automation engine** that happens to start with Quran content. Every architectural decision must support arbitrary content types.

> **The app is idle most of the time (flux).** We fill that void with meaningful, scheduled content that respects the operator's values and audience.

---

## 2. Content Type Taxonomy

Future content types are categorized by **media format** and **production complexity**:

| Format | Complexity | Examples | Pipeline Type |
|--------|-----------|----------|---------------|
| **Short-form video** | High | Quran verses, motivational reels, news clips | Full pipeline (fetch → render → post) |
| **Static image + text** | Medium | Hadith cards, quote graphics, infographics | Image compose pipeline |
| **Image carousel** | Medium | Photo series, step guides, before/after | Multi-attachment pipeline |
| **Text-only thread** | Low | Daily reminders, news summaries, tips | Caption-only pipeline |
| **Curated repost** | Low | Sharing others' content with commentary | Pass-through pipeline |

---

## 3. The Quran Pipeline (v1.0) — Reference Implementation

| Attribute | Detail |
|-----------|--------|
| **Plugin** | `quran_shorts` |
| **Frequency** | 1 post/day |
| **Platforms** | YouTube, Telegram, Instagram, TikTok, X |
| **Source** | Whitelisted YouTube channels (Shorts) |
| **Render** | FFmpeg: colorkey + background overlay + Ken Burns |
| **Caption** | Verse ref + Arabic + translation + hashtags |
| **Approval** | Required for all ingredients |
| **Identity** | Verse identification via metadata/Whisper/manual |

This pipeline validates the entire architecture. Every feature it uses must be generic enough for other pipelines.

---

## 4. Expansion Roadmap

### 4.1 Phase 2: Image-Based Content (v1.1–v1.2)

#### Pipeline: Daily Hadith Cards
| Attribute | Detail |
|-----------|--------|
| **Plugin** | `hadith_cards` |
| **Frequency** | 1 post/day |
| **Platforms** | Instagram, Telegram, X |
| **Source** | Sunnah.com API or local database |
| **Render** | Pillow: text on template background |
| **Caption** | Hadith reference + narrator + translation + source link |
| **Approval** | Auto-approve (text API is trusted) |

**Why this is a good second pipeline:**
- Different render mode (`image_compose` vs `video_compose`).
- Tests the plugin architecture with non-video content.
- Lower resource usage (no FFmpeg).
- Different source type (API vs YouTube).

#### Pipeline: Islamic Quote Graphics
| Attribute | Detail |
|-----------|--------|
| **Plugin** | `quote_graphics` |
| **Frequency** | 1 post/day (alternating with Hadith) |
| **Source** | Curated local JSON file or simple API |
| **Render** | Pillow: quote text + attribution on aesthetic background |
| **Platforms** | Instagram, Telegram, X |

### 4.2 Phase 3: Multi-Format & Automation (v1.3–v1.5)

#### Pipeline: Daily Reminder Threads
| Attribute | Detail |
|-----------|--------|
| **Plugin** | `daily_reminders` |
| **Format** | Text-only or text + simple image |
| **Platforms** | Telegram, X |
| **Source** | Local JSON array of reminders |
| **Render** | None (text_only) |
| **Schedule** | 1 post/day |

#### Pipeline: News Summary Clips
| Attribute | Detail |
|-----------|--------|
| **Plugin** | `news_clips` |
| **Format** | Short video with headline overlay |
| **Source** | RSS feeds or news APIs |
| **Render** | FFmpeg: news footage + headline text + source citation |
| **Platforms** | YouTube, TikTok, X |
| **Approval** | Required (news must be factual and appropriate) |

#### Pipeline: Community Submission Queue
| Attribute | Detail |
|-----------|--------|
| **Plugin** | `community_queue` |
| **Format** | Any (image/video/text) |
| **Source** | Telegram bot submissions or email |
| **Render** | Passthrough or minimal |
| **Platforms** | All |
| **Approval** | Required (community content must be vetted) |

### 4.3 Phase 4: Intelligence & Personalization (v2.0+)

| Feature | Description |
|---------|-------------|
| **Best-time-to-post** | Analyze historical engagement (where API permits) and auto-adjust schedules |
| **A/B testing framework** | Test two caption variants or thumbnail choices across platform accounts |
| **AI-assisted captioning** | Optional OpenAI API integration for generating hooks/variations |
| **Content calendar** | Visual monthly calendar showing scheduled posts across all pipelines |
| **Cross-pipeline coordination** | Ensure Quran and Hadith posts don't clash (e.g., Friday Quran, Saturday Hadith) |

---

## 5. Platform-Content Matrix

Not all content belongs on all platforms. The matrix below guides which pipelines attach to which workers:

| Content | YouTube | Telegram | Instagram | TikTok | X |
|---------|---------|----------|-----------|--------|---|
| Quran video | ✅ | ✅ | ✅ Reels | ✅ | ⚠️ Truncated caption |
| Hadith image | ❌ | ✅ | ✅ Feed | ❌ | ✅ |
| Quote graphic | ❌ | ✅ | ✅ Feed | ❌ | ✅ |
| Text reminder | ❌ | ✅ | ❌ | ❌ | ✅ |
| News clip | ✅ | ✅ | ✅ Reels | ✅ | ⚠️ Link only |
| Community image | ❌ | ✅ | ✅ Feed | ❌ | ✅ |

**Design implication:** The pipeline-worker attachment UI must warn or prevent mismatches (e.g., trying to post a text-only reminder to YouTube).

---

## 6. Content Calendar Strategy

### 6.1 Weekly Rhythm (Example)

| Day | Morning | Evening |
|-----|---------|---------|
| Monday | Quran verse (YT + IG + TG) | — |
| Tuesday | Hadith card (IG + TG + X) | — |
| Wednesday | Quran verse (YT + IG + TG) | — |
| Thursday | Quote graphic (IG + TG + X) | — |
| Friday | Quran verse (YT + IG + TG + TT) | Jummah reminder (TG + X) |
| Saturday | Hadith card (IG + TG + X) | — |
| Sunday | Quran verse (YT + IG + TG) | Weekly digest (TG) |

**Principle:** Spread content types across the week. Avoid over-posting to any single platform. Respect religious significance (e.g., Friday posts).

### 6.2 Seasonal Content

| Occasion | Content Adjustment |
|----------|-------------------|
| Ramadan | Increase frequency to 2/day; special Ramadan templates |
| Eid | Pause automated posts; schedule Eid greetings manually |
| Hajj | Hajj-themed content from curated sources |
| Islamic New Year | Historical/educational content |

---

## 7. Branding & Voice Guidelines

Even though Flux is automated, the output should feel human and consistent.

### 7.1 Tone

- **Quran content:** Reverent, accurate, unadorned. Let the text speak.
- **Hadith content:** Respectful, scholarly, accessible.
- **Reminders:** Warm, encouraging, concise.
- **News:** Neutral, factual, cited.

### 7.2 Visual Consistency

| Element | Guideline |
|---------|-----------|
| Fonts | Use consistent Arabic (Amiri/Scheherazade) and Latin (Inter/Roboto) fonts across all image pipelines |
| Colour palette | Define a palette per account; Quran = deep greens/blues; Hadith = warm earth tones |
| Watermark | Optional small account handle in corner; never obstruct content |
| Aspect ratios | 9:16 for video, 1:1 for image feed, 16:9 for YouTube standard |

---

## 8. Content Quality Gates

Every piece of content, regardless of pipeline, must pass:

1. **Source verification:** Is the source trustworthy?
2. **Accuracy check:** Is the religious content correct? (Quran verses, hadith references)
3. **Visual appropriateness:** Does the background/image contain anything inappropriate?
4. **Caption review:** Are there typos? Is the formatting correct?
5. **Platform compliance:** Does it meet the platform's terms and format requirements?

**Automation reduces labour, not responsibility.** The operator remains accountable for every post.

---

## 9. Audience Growth Strategy

| Tactic | Implementation |
|--------|----------------|
| **Consistent timing** | Post at the same time daily (builds anticipation) |
| **Cross-platform funnel** | YouTube for discovery → Telegram for community → X for reach |
| **Hashtag research** | Maintain a living list of effective hashtags per platform; rotate to avoid shadowban |
| **Engagement hooks** | End captions with questions or reflections (where platform supports comments) |
| **Collaboration** | Future: community queue allows follower submissions |
| **Analytics feedback loop** | Track which verses/formats perform best; weight future selection |
