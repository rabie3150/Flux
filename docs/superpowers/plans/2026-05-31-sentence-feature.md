# Sentence Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add natural example sentences to every vocabulary card in `flux_lang` videos, narrated after the translation and displayed below the word pair.

**Architecture:** Extend the generator prompt to request `example_sentence`, add a 3rd TTS track per word, extend the FFmpeg filter chain with sentence drawtext, and lengthen each word block by `sentence_display_secs`.

**Tech Stack:** Python 3.11, Pydantic, Pillow, FFmpeg drawtext filters, Edge TTS / DeepInfra TTS

---

## File Structure

| File | Responsibility |
|------|---------------|
| `flux_lang/config.py` | Add `sentence_display_secs` to `TimingConfig` |
| `flux_lang/generator.py` | Request `example_sentence` from Gemini; parse it into word dicts |
| `flux_lang/render_filters.py` | Draw sentence text below target word; highlight target word in gold |
| `flux_lang/renderer.py` | Synthesize sentence TTS, add to audio mix, extend block timing |
| `tests/test_config.py` | Assert `sentence_display_secs` default |
| `tests/test_render_filters.py` | Assert sentence text appears in filter output |

---

## Task 1: Config — Add `sentence_display_secs`

**Files:**
- Modify: `flux_lang/config.py:62-68`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
def test_sentence_display_secs_default():
    from flux_lang.config import AppConfig
    cfg = AppConfig()
    assert cfg.timing.sentence_display_secs == 2.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_sentence_display_secs_default -v`
Expected: FAIL with `AttributeError: 'TimingConfig' object has no attribute 'sentence_display_secs'`

- [ ] **Step 3: Add `sentence_display_secs` to `TimingConfig`**

In `flux_lang/config.py`, add inside `TimingConfig`:

```python
sentence_display_secs: float = 2.5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_sentence_display_secs_default -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_config.py flux_lang/config.py
git commit -m "feat(config): add sentence_display_secs timing option"
```

---

## Task 2: Generator — Request and Parse `example_sentence`

**Files:**
- Modify: `flux_lang/generator.py:15-32`, `flux_lang/generator.py:96-107`
- Test: `tests/test_generator.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_generator.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.anyio
async def test_generate_includes_example_sentence():
    from flux_lang.generator import GeminiGenerator

    mock_text = json.dumps([{
        "source": "coffee",
        "target": "caffè",
        "phonetic": "CAFF-eh",
        "example_sentence": "Vorrei un caffè, per favore."
    }])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": mock_text}]}}]
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        generator = GeminiGenerator(api_keys=["fake-key"])
        result = await generator.generate("en", "it", "food", count=1)

        assert len(result) == 1
        assert result[0]["example_sentence"] == "Vorrei un caffè, per favore."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generator.py -v`
Expected: FAIL with `AssertionError` because `example_sentence` key is missing

- [ ] **Step 3: Update generator prompt and parsing**

In `flux_lang/generator.py`, update `PROMPT` (after the existing 5 fields):

```python
For each item, provide:
1. source — word/sentence in {source_lang}
2. target — exact translation in {target_lang}
3. phonetic — pronunciation guide for target
4. difficulty — {difficulty}
5. category — e.g. "greetings", "food", "numbers"
6. example_sentence — a natural sentence in {target_lang} using the target word
```

Update the parsing loop (around line 96) to include `example_sentence`:

```python
return [
    {
        "source_text": str(item["source"]),
        "target_text": str(item["target"]),
        "phonetic": str(item.get("phonetic", "")),
        "difficulty": str(item.get("difficulty", difficulty)),
        "category": str(item.get("category", theme)),
        "theme": theme,
        "example_sentence": str(item.get("example_sentence", "")),
    }
    for item in result
    if "source" in item and "target" in item
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_generator.py flux_lang/generator.py
git commit -m "feat(generator): request example_sentence from Gemini"
```

---

## Task 3: Render Filters — Add Sentence Drawtext

**Files:**
- Modify: `flux_lang/render_filters.py:297-430`
- Test: `tests/test_render_filters.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render_filters.py` inside `TestBuildWordBlockFilters`:

```python
def test_contains_example_sentence(self, config):
    config["timing"]["sentence_display_secs"] = 2.5
    result = build_word_block_filters(
        word_index=0, total_words=3, start_time=3.0,
        source_text="Hello", target_text="Ciao",
        phonetic_text="CHOW", config=config,
        example_sentence="Ciao, come stai?",
    )
    combined = " ".join(result)
    assert "Ciao, come stai?" in combined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render_filters.py::TestBuildWordBlockFilters::test_contains_example_sentence -v`
Expected: FAIL with `TypeError: build_word_block_filters() got an unexpected keyword argument 'example_sentence'`

- [ ] **Step 3: Add sentence parameter and drawtext filter**

Add a helper above `build_word_block_filters`:

```python
def _highlight_word(text: str, word: str, color: str = "#FFD700") -> str:
    """Wrap first occurrence of *word* in FFmpeg drawtext color markup."""
    import re
    if not word or not text:
        return text
    pattern = re.compile(rf"\b({re.escape(word)})\b", re.IGNORECASE)
    return pattern.sub(rf"{{\\c{color}}}\1{{\\c}}", text, count=1)
```

Update `build_word_block_filters` signature:

```python
def build_word_block_filters(
    word_index: int,
    total_words: int,
    start_time: float,
    source_text: str,
    target_text: str,
    phonetic_text: str,
    config: dict[str, Any],
    example_sentence: str = "",
) -> list[str]:
```

Add sentence handling after the phonetic block (before the final `return filters`):

```python
    # 3. Example sentence (below target text, inside card)
    if example_sentence:
        sentence_display = timing.get("sentence_display_secs", 0.0)
        sentence_start = start_time + en_display + reveal
        sentence_end = sentence_start + sentence_display
        # Use the extended block_end for card visibility; sentence text stays until end
        sentence_font_size = 48
        sentence_color = "#DDDDDD"
        highlighted = _highlight_word(example_sentence, target_text)
        wrapped_sentence = wrap_text(highlighted, max_chars=24)

        # Position below phonetic or target
        if show_phonetic:
            sentence_y_pos = "1240-th/2"
        else:
            sentence_y_pos = "1280-th/2"

        filters.append(
            build_animated_text(
                wrapped_sentence,
                start_time=sentence_start,
                end_time=sentence_end,
                y_pos=sentence_y_pos,
                config=config,
                fontsize=sentence_font_size,
                fontcolor=sentence_color,
                fade_in=0.3,
                fade_out=0.2,
                weight="Regular",
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_render_filters.py -v`
Expected: PASS (all existing tests plus the new one)

- [ ] **Step 5: Commit**

```bash
git add tests/test_render_filters.py flux_lang/render_filters.py
git commit -m "feat(render_filters): draw example sentence below word pair"
```

---

## Task 4: Renderer — Sentence TTS, Timing, and Audio Mix

**Files:**
- Modify: `flux_lang/renderer.py:66-167`, `flux_lang/renderer.py:231-551`

- [ ] **Step 1: Add sentence audio synthesis**

In `_generate_audio_assets`, update the word loop (around line 114):

```python
    enriched = []
    word_tasks = []
    for i, w in enumerate(words):
        s_path = temp_dir / f"word_{i}_source.wav"
        t_path = temp_dir / f"word_{i}_target.wav"
        sent_path = temp_dir / f"word_{i}_sentence.wav"

        word_tasks.append(
            _synthesize_with_fallback(w["source_text"], source_voice, source_voice_fallback, s_path)
        )
        word_tasks.append(
            _synthesize_with_fallback(w["target_text"], target_voice, target_voice_fallback, t_path)
        )

        enriched_word = {
            **w,
            "source_audio_path": str(s_path),
            "target_audio_path": str(t_path),
        }

        if w.get("example_sentence"):
            word_tasks.append(
                _synthesize_with_fallback(w["example_sentence"], target_voice, target_voice_fallback, sent_path)
            )
            enriched_word["sentence_audio_path"] = str(sent_path)

        enriched.append(enriched_word)
```

Update `total_audios` (around line 67):

```python
    total_audios = len(words) * 3 + 2  # source + target + sentence, plus intro + outro
```

- [ ] **Step 2: Update block timing in `render_video`**

Find the block timing section (around line 256):

```python
    sentence_display = timing.get("sentence_display_secs", 0.0)
    block_dur = en_display + reveal + sentence_display + pause
```

Update card overlay duration in the filter loop (around line 415):

```python
            block_end = block_start + en_display + reveal + sentence_display
```

All existing overlay `enable='between(t, ...)'` expressions already use `block_end`, so they will automatically extend.

- [ ] **Step 3: Add sentence audio to audio filter chain**

In the audio inputs loop (around line 327), add after target audio:

```python
        if w.get("sentence_audio_path"):
            input_args.extend(["-i", w["sentence_audio_path"]])
            sent_idx = current_input_idx
            current_input_idx += 1
            sent_delay_ms = int((block_start + en_display + reveal + 0.3) * 1000)
            audio_filters.append(f"[{sent_idx}:a]adelay={sent_delay_ms}|{sent_delay_ms}[a{i}sent]")
```

- [ ] **Step 4: Update audio mix labels and input count**

Update `word_audio_labels` (around line 465):

```python
    word_audio_labels = ""
    for i, w in enumerate(enriched_words):
        word_audio_labels += f"[a{i}s][a{i}t]"
        if w.get("sentence_audio_path"):
            word_audio_labels += f"[a{i}sent]"
```

Update `total_audio_inputs` (around line 469):

```python
    total_audio_inputs = (
        len(enriched_words) * 2
        + sum(1 for w in enriched_words if w.get("sentence_audio_path"))
        + (1 if intro_audio_path else 0)
        + (1 if outro_audio_path else 0)
        + (1 if ding_path else 0)
    )
```

- [ ] **Step 5: Pass `example_sentence` to `build_word_block_filters`**

In the word filter loop (around line 436):

```python
            w_filters = build_word_block_filters(
                word_index=i,
                total_words=len(enriched_words),
                start_time=block_start,
                source_text=w["source_text"],
                target_text=w["target_text"],
                phonetic_text=w.get("phonetic", ""),
                example_sentence=w.get("example_sentence", ""),
                config=cfg_dict,
            )
```

- [ ] **Step 6: Manual verification**

Run a quick render:

```bash
python -m flux_lang
```

Generate a 1-word video and visually confirm:
1. Source word appears first
2. Translation reveals with TTS
3. Sentence fades in below
4. Sentence TTS plays after translation

- [ ] **Step 7: Commit**

```bash
git add flux_lang/renderer.py
git commit -m "feat(renderer): synthesize and mix sentence TTS, extend block timing"
```

---

## Task 5: Fix Existing Tests for Timing Changes

**Files:**
- Modify: `tests/test_render_filters.py:87-106`

- [ ] **Step 1: Update config fixture**

Add `sentence_display_secs` to the fixture in `tests/test_render_filters.py`:

```python
    @pytest.fixture
    def config(self):
        return {
            "timing": {
                "en_display_secs": 2.0,
                "countdown_secs": 3.0,
                "reveal_hold_secs": 3.0,
                "sentence_display_secs": 2.5,
            },
            ...
        }
```

- [ ] **Step 2: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_render_filters.py
git commit -m "test(render_filters): add sentence_display_secs to test fixture"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Generator requests `example_sentence` → Task 2
- ✅ Config has `sentence_display_secs` → Task 1
- ✅ Sentence TTS synthesis → Task 4, Steps 1-3
- ✅ Sentence drawtext with word highlight → Task 3
- ✅ Extended block timing → Task 4, Step 2
- ✅ Error handling (empty sentence skipped) → Task 4, Step 1

**2. Placeholder scan:**
- No "TBD", "TODO", or vague instructions found.
- Every step includes exact file paths, code, and expected test output.

**3. Type consistency:**
- `example_sentence` is a `str` everywhere (default `""`)
- `sentence_display_secs` is a `float` in config and accessed via `timing.get("sentence_display_secs", 0.0)`
- Audio label pattern `[a{i}sent]` is consistent across filter creation and mix labels
