"""Tests for language_shorts render filter primitives."""

from __future__ import annotations

import pytest

from flux_lang.render_filters import (
    build_drawtext,
    build_word_block_filters,
    escape_text,
    _resolve_font_path,
)


# ---------------------------------------------------------------------------
# escape_text
# ---------------------------------------------------------------------------

class TestEscapeText:
    def test_empty_string(self):
        assert escape_text("") == ""

    def test_plain_text(self):
        assert escape_text("Hello world") == "Hello world"

    def test_colon(self):
        assert escape_text("Hello: world") == "Hello\\: world"

    def test_single_quote(self):
        assert escape_text("It's") == "It\\'s"

    def test_backslash(self):
        assert escape_text("path\\to") == "path\\\\to"

    def test_combined(self):
        result = escape_text("It's a: test\\path")
        assert "\\\\" in result
        assert "\\'" in result
        assert "\\:" in result

    def test_unicode(self):
        # Non-ASCII should pass through unmodified
        assert escape_text("Come stai?") == "Come stai?"
        assert escape_text("こんにちは") == "こんにちは"


# ---------------------------------------------------------------------------
# build_drawtext
# ---------------------------------------------------------------------------

class TestBuildDrawtext:
    @pytest.fixture
    def config(self):
        return {"style": {"fontfile": None}}

    def test_basic_output(self, config):
        result = build_drawtext(
            "Hello", 0.0, 3.0, y_pos=500,
            config=config, fontsize=64, fontcolor="white",
        )
        assert "drawtext=" in result
        assert "text='Hello'" in result
        assert "enable='between(t,0.00,3.00)'" in result
        assert "fontsize=64" in result
        assert "fontcolor=white" in result
        assert "y=500" in result
        assert "x=(w-tw)/2" in result

    def test_shadow_default_on(self, config):
        result = build_drawtext("Hi", 0, 1, 100, config=config)
        assert "shadowcolor=black@0.6" in result

    def test_shadow_off(self, config):
        result = build_drawtext("Hi", 0, 1, 100, config=config, shadow=False)
        assert "shadow" not in result

    def test_escapes_special_chars(self, config):
        result = build_drawtext("It's a: test", 0, 1, 100, config=config)
        assert "\\'" in result
        assert "\\:" in result


# ---------------------------------------------------------------------------
# build_word_block_filters
# ---------------------------------------------------------------------------

class TestBuildWordBlockFilters:
    @pytest.fixture
    def config(self):
        return {
            "timing": {
                "en_display_secs": 2.0,
                "countdown_secs": 3.0,
                "reveal_hold_secs": 3.0,
            },
            "style": {
                "source_font_size": 64,
                "target_font_size": 64,
                "countdown_font_size": 120,
                "phonetic_font_size": 36,
                "countdown_color": "yellow",
                "progress_dots": True,
                "fontfile": None,
            },
            "difficulty": "beginner",
        }

    def test_returns_list_of_strings(self, config):
        result = build_word_block_filters(
            word_index=0, total_words=3, start_time=3.0,
            source_text="Hello", target_text="Ciao",
            phonetic_text="CHOW", config=config,
        )
        assert isinstance(result, list)
        assert all(isinstance(f, str) for f in result)

    def test_contains_source_text(self, config):
        result = build_word_block_filters(
            word_index=0, total_words=5, start_time=3.0,
            source_text="Good morning", target_text="Buongiorno",
            phonetic_text="bwon-JOR-no", config=config,
        )
        combined = " ".join(result)
        assert "Good morning" in combined

    def test_contains_target_text(self, config):
        result = build_word_block_filters(
            word_index=0, total_words=5, start_time=3.0,
            source_text="Hi", target_text="Ciao",
            phonetic_text="", config=config,
        )
        combined = " ".join(result)
        assert "Ciao" in combined

    def test_phonetic_shown_for_beginner(self, config):
        result = build_word_block_filters(
            word_index=0, total_words=5, start_time=3.0,
            source_text="Hi", target_text="Ciao",
            phonetic_text="CHOW", config=config,
        )
        combined = " ".join(result)
        assert "[chow]" in combined

    def test_phonetic_hidden_for_advanced(self, config):
        config["difficulty"] = "advanced"
        result = build_word_block_filters(
            word_index=0, total_words=5, start_time=3.0,
            source_text="Hi", target_text="Ciao",
            phonetic_text="CHOW", config=config,
        )
        combined = " ".join(result)
        assert "[chow]" not in combined

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


# ---------------------------------------------------------------------------
# _resolve_font_path
# ---------------------------------------------------------------------------

class TestResolveFontPath:
    def test_returns_string(self):
        result = _resolve_font_path({"style": {}})
        assert isinstance(result, str)

    def test_explicit_override_used(self, tmp_path):
        font = tmp_path / "custom.ttf"
        font.write_bytes(b"fake font")
        result = _resolve_font_path({"style": {"fontfile": str(font)}})
        assert "custom" in result

    def test_missing_override_falls_through(self):
        result = _resolve_font_path({"style": {"fontfile": "/nonexistent/font.ttf"}})
        # Should fall through to platform detection, not crash
        assert isinstance(result, str)
