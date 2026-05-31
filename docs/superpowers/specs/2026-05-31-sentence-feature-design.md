# Sentence Feature Design

> **Feature:** Add example sentences to language-learning short videos  
> **Approach:** Always-On Sentences (no toggle)  
> **Date:** 2026-05-31  
> **Status:** Approved

---

## 1. Goal

Every vocabulary card in a `flux_lang` video now includes a natural example sentence in the **target language**, displayed below the word pair and narrated after the translation.

## 2. User Experience

**Audio flow per word:**
1. Origin-language word spoken (source voice)
2. Target-language word spoken (target voice)
3. Target-language sentence spoken (target voice)

**Visual flow:**
1. Card shows source word (top)
2. Translation reveals (bottom, gold)
3. Example sentence fades in below the divider (off-white, target word highlighted in gold)

## 3. Data Model

Generator prompt now requests an additional field:

```json
{
  "source": "coffee",
  "target": "caffè",
  "phonetic": "CAFF-eh",
  "difficulty": "beginner",
  "category": "food",
  "example_sentence": "Vorrei un caffè, per favore."
}
```

- `example_sentence` is in the **target language**.
- If Gemini omits it, the renderer skips sentence text and TTS for that word silently.

## 4. Configuration Changes

### `flux_lang/config.py`

Add to `TimingConfig`:

```python
sentence_display_secs: float = 2.5
```

This controls sentence visibility duration and gives TTS audio room to finish.

## 5. Generator Changes

### `flux_lang/generator.py`

Update `PROMPT` to include:

```text
6. example_sentence — a natural sentence in {target_lang} using the target word
```

Parse `example_sentence` from JSON response. If missing or empty, default to `""`.

## 6. TTS / Audio Pipeline

### `flux_lang/renderer.py` — `_generate_audio_assets`

For each word, synthesize a 3rd audio track:
- File: `word_{i}_sentence.wav`
- Voice: target voice (same as translation)
- Text: `w["example_sentence"]`

Skip synthesis if `example_sentence` is empty.

**Audio filter delays:**
- Source audio: `block_start + 0.5s`
- Target audio: `block_start + en_display_secs + 0.5s`
- Sentence audio: `block_start + en_display_secs + reveal_hold_secs + 0.3s`
  - Sentence narrates after the translation beat finishes, giving a clean three-step flow.

## 7. Video Filter Changes

### `flux_lang/render_filters.py`

Extend `build_word_block_filters` (or add `build_sentence_filters`) to draw:
- Text: `example_sentence`
- Font size: 48px
- Color: `#DDDDDD`
- Position: below target text, inside the card
- Target word highlight: wrap the target word in `{\c#FFD700}` drawtext markup

The sentence overlay is enabled for the full block duration (`block_start` to `block_end`).

## 8. Timing

### Block duration formula

```python
block_dur = en_display_secs + reveal_hold_secs + sentence_display_secs + pause_between_secs
```

With defaults:
- Before: 2.5 + 3.0 + 1.0 = **6.5s**
- After:  2.5 + 3.0 + 2.5 + 1.0 = **9.0s**

A 5-word video goes from ~38s to ~53s total. This is acceptable for short-form.

**Card visibility:** `block_end` must also include `sentence_display_secs` so the backdrop blur and card overlay stay visible during the sentence phase.

## 9. Error Handling

| Scenario | Behavior |
|----------|----------|
| Gemini omits `example_sentence` | Empty string; skip TTS + drawtext for that word |
| Sentence TTS fails | Log warning; render video without sentence audio, text still shown |
| Sentence text is too long for card | Truncate with ellipsis at 80 chars; log warning |

## 10. Testing

- Unit test: Generator parses `example_sentence` correctly
- Unit test: Config loads `sentence_display_secs` default
- Integration test: Render a 1-word video with sentence and verify FFmpeg command contains sentence drawtext + audio inputs

## 11. Files Modified

| File | Change |
|------|--------|
| `flux_lang/config.py` | Add `sentence_display_secs` to `TimingConfig` |
| `flux_lang/generator.py` | Update prompt; parse `example_sentence` |
| `flux_lang/renderer.py` | Synthesize sentence TTS; add to audio filter chain |
| `flux_lang/render_filters.py` | Add sentence drawtext filters |

## 12. Out of Scope

- Config toggle to disable sentences (Approach 2)
- Animated slide-in for sentence text
- Source-language sentence translations
- Separate sentence-only video mode
