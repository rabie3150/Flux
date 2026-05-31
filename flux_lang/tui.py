"""Textual TUI for Flux Language Shorts — keyboard + mouse navigation."""

from __future__ import annotations

import os
import platform
import random
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    RichLog,
    Select,
    Static,
    Switch,
)

from flux_lang.assets import fetch_backgrounds
from flux_lang.config import AppConfig, load_config, save_config, LANG_NAMES
from flux_lang.generator import GeminiGenerator
from flux_lang.renderer import render_video
from flux_lang.tts import voices_for_language, VoiceInfo
from flux_lang.utils import get_logger, get_log_buffer, clear_log_buffer

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------

CSS = """
Screen { align: center middle; }

/* Root container fills the entire terminal */
Screen > Container {
    width: 100%;
    height: 100%;
    padding: 0 1;
}

#main-menu {
    width: auto;
    height: auto;
    border: thick $background 80%;
    padding: 1 2;
}

#main-menu OptionList { height: auto; min-width: 30; }

.title {
    text-align: center;
    text-style: bold;
    color: #0EA5E9;
    height: auto;
    padding: 1 0;
}

.form-row {
    height: auto;
    margin: 1 0;
}

.form-row Input, .form-row Select, .form-row Button { width: 1fr; min-width: 10; }
.form-row Label { width: auto; }
.form-row Switch { width: auto; }

/* Generation Dashboard */
.mission-card {
    border: panel $primary;
    padding: 1;
    height: auto;
}

.mission-card Static { height: auto; }

#generate_btn { width: auto; margin: 1 0; }

.dashboard-mid {
    height: 1fr;
    min-height: 10;
}

.pipeline-panel {
    width: 100%;
    border: panel $success;
    padding: 1;
    height: 100%;
}

.pipeline-panel Static { height: auto; margin: 1 0; }

#pipeline_scroll { height: 1fr; }

.step-words {
    color: $text-muted;
    margin-left: 2;
}

.result-panel {
    border: panel $primary;
    padding: 1;
    height: auto;
}

.result-actions { height: auto; }
.result-actions Button { width: auto; margin-right: 2; }

.logs-panel {
    border: panel $surface-lighten-1;
    padding: 1;
    height: 1fr;
    min-height: 5;
    max-height: 12;
}

.logs-panel RichLog { height: 1fr; }

.voice-picker {
    width: 100%;
    height: auto;
    border: thick $background 80%;
    padding: 1;
}

.voice-picker DataTable {
    width: 100%;
    height: 1fr;
    min-height: 5;
}
"""


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------

class MainScreen(Screen):
    """Landing screen with navigation menu."""

    def compose(self) -> ComposeResult:
        with Container(id="main-menu"):
            yield Static("Flux Language Shorts Generator", classes="title")
            yield OptionList(
                "Generate Video",
                "Settings",
                "Open Output Folder",
                "Quit",
                id="menu",
            )
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if idx == 0:
            self.app.push_screen(GenerateScreen())
        elif idx == 1:
            self.app.push_screen(SettingsScreen())
        elif idx == 2:
            self._open_folder()
        elif idx == 3:
            self.app.exit()

    def _open_folder(self) -> None:
        cfg: AppConfig = self.app.cfg
        path = Path(cfg.output_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(path))
            elif system == "Darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            logger.error("Could not open folder: %s", e)


# ---------------------------------------------------------------------------
# Generate Video
# ---------------------------------------------------------------------------

class GenerateScreen(Screen):
    """Mission Control dashboard for video generation."""

    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Static("Generate Video", classes="title")

            # Mission Card
            with Container(classes="mission-card"):
                cfg = self.app.cfg
                yield Static(
                    f"[bold]Mission:[/] {cfg.words_per_video} {cfg.target_lang_name} Words",
                    id="mission_title",
                )
                yield Static(
                    f"{cfg.source_lang_name} → {cfg.target_lang_name}  |  "
                    f"Difficulty: {cfg.difficulty.title()}  |  "
                    f"TTS: {cfg.tts.provider}",
                    id="mission_meta",
                )
                yield Static(
                    f"Source Voice: {cfg.tts.source_voice}  |  "
                    f"Target Voice: {cfg.tts.target_voice}",
                    id="mission_voices",
                )
                yield Button("GENERATE", variant="primary", id="generate_btn")

            # Pipeline timeline (scrollable)
            with Container(classes="dashboard-mid"):
                with Container(classes="pipeline-panel"):
                    yield Static("[bold]Pipeline[/]")
                    with VerticalScroll(id="pipeline_scroll"):
                        yield Static("○  Vocabulary", id="step_1")
                        yield Static("", id="step_1_words", classes="step-words")
                        yield Static("○  Backgrounds", id="step_2")
                        yield Static("○  TTS Audio", id="step_3")
                        yield Static("○  Cards", id="step_4")
                        yield Static("○  FFmpeg Render", id="step_5")

            # Logs panel
            with Container(classes="logs-panel", id="logs_container"):
                yield Static("[bold]Logs[/]")
                yield RichLog(id="log_view", wrap=True)

            # Result panel (hidden until done)
            with Container(classes="result-panel", id="result_container"):
                yield Static("", id="result_path")
                with Horizontal(classes="result-actions"):
                    yield Button("Open Folder", id="open_folder_btn")
                    yield Button("Generate Another", variant="primary", id="again_btn")

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#result_container", Container).display = False
        self.query_one("#logs_container", Container).display = self.app.cfg.show_logs
        self._log_timer = self.set_interval(0.2, self._poll_logs)
        clear_log_buffer()

    def _poll_logs(self) -> None:
        buf = get_log_buffer()
        if not buf:
            return
        log_view = self.query_one("#log_view", RichLog)
        # Drain buffer
        while buf:
            try:
                line = buf.popleft()
                log_view.write(line)
            except IndexError:
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "generate_btn":
            self._start_generation()
        elif bid == "open_folder_btn":
            self._open_result_folder()
        elif bid == "again_btn":
            self._reset()

    def action_back(self) -> None:
        self.app.pop_screen()

    def _reset(self) -> None:
        """Reset UI for another generation."""
        self._set_step(1, "○  Vocabulary")
        self.query_one("#step_1_words", Static).update("")
        self._set_step(2, "○  Backgrounds")
        self._set_step(3, "○  TTS Audio")
        self._set_step(4, "○  Cards")
        self._set_step(5, "○  FFmpeg Render")
        self.query_one("#result_container", Container).display = False
        self.query_one("#generate_btn", Button).disabled = False
        clear_log_buffer()
        self.query_one("#log_view", RichLog).clear()

    def _set_step(self, n: int, text: str) -> None:
        self.query_one(f"#step_{n}", Static).update(text)

    def _start_generation(self) -> None:
        cfg = self.app.cfg
        theme = random.choice(cfg.themes)
        self.query_one("#generate_btn", Button).disabled = True
        self.run_worker(self._generate(cfg, theme), exclusive=True)

    def _open_result_folder(self) -> None:
        path = Path(self.app.cfg.output_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(path))
            elif system == "Darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            logger.error("Could not open folder: %s", e)

    async def _generate(self, cfg: AppConfig, theme: str) -> None:
        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _on_render_progress(step: str, detail: str) -> None:
            if step == "tts_word":
                self._set_step(3, f"⏳  TTS  — {detail}")
            elif step in ("tts_intro", "tts_outro", "tts_ding"):
                self._set_step(3, f"⏳  TTS  — {detail}")
            elif step == "tts":
                self._set_step(3, f"⏳  TTS  — {detail}")
            elif step == "cards":
                self._set_step(4, f"⏳  Cards  — {detail}")
            elif step == "ffmpeg":
                self._set_step(5, f"⏳  FFmpeg  — {detail}")

        # Step 1: vocabulary
        self._set_step(1, "⏳  Vocabulary  — calling Gemini...")
        gen = GeminiGenerator(cfg.gemini_api_keys)
        words = await gen.generate(
            source_lang=cfg.source_lang,
            target_lang=cfg.target_lang,
            theme=theme,
            count=cfg.words_per_video,
            difficulty=cfg.difficulty,
        )
        if not words:
            self._set_step(1, "✗  Vocabulary  — failed (check API keys)")
            self.query_one("#generate_btn", Button).disabled = False
            return
        self._set_step(1, f"✓  Vocabulary  — {len(words)} words")
        word_lines = [
            f"  {i}. {w['source_text']} → {w['target_text']}"
            for i, w in enumerate(words, 1)
        ]
        self.query_one("#step_1_words", Static).update("\n".join(word_lines))

        # Step 2: backgrounds
        self._set_step(2, "⏳  Backgrounds  — fetching...")
        bg_paths = await fetch_backgrounds(cfg)
        self._set_step(2, f"✓  Backgrounds  — {len(bg_paths)} image(s)")

        # Step 3-5: render (TTS → Cards → FFmpeg)
        import time
        ts = int(time.time())
        safe_theme = "".join(c if c.isalnum() else "_" for c in theme)
        output_video = str(output_dir / f"lang_{safe_theme}_{ts}.mp4")

        try:
            rendered = await render_video(words, bg_paths, output_video, cfg, on_progress=_on_render_progress)
        except Exception as e:
            logger.exception("Render failed")
            self._set_step(5, f"✗  FFmpeg  — {e}")
            self.query_one("#generate_btn", Button).disabled = False
            return

        self._set_step(3, "✓  TTS  — complete")
        self._set_step(4, "✓  Cards  — complete")
        self._set_step(5, "✓  FFmpeg  — complete")

        # Show result
        result = self.query_one("#result_path", Static)
        result.update(f"[bold green]Saved:[/] {rendered}")
        self.query_one("#result_container", Container).display = True
        self.query_one("#generate_btn", Button).disabled = False


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    """Settings editor."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Static("Settings", classes="title")
            cfg = self.app.cfg

            with Vertical():
                with Horizontal(classes="form-row"):
                    yield Select(
                        [(v, k) for k, v in LANG_NAMES.items()],
                        value=cfg.source_lang,
                        id="s_source_lang",
                    )
                    yield Select(
                        [(v, k) for k, v in LANG_NAMES.items()],
                        value=cfg.target_lang,
                        id="s_target_lang",
                    )

                with Horizontal(classes="form-row"):
                    yield Select(
                        [(d.title(), d) for d in ["beginner", "intermediate", "advanced"]],
                        value=cfg.difficulty,
                        id="s_difficulty",
                    )
                    yield Select(
                        [("Edge TTS", "edge_tts"), ("Inworld", "inworld")],
                        value=cfg.tts.provider,
                        id="s_provider",
                    )

                with Horizontal(classes="form-row"):
                    yield Input(value=str(cfg.words_per_video), id="s_words", type="integer", placeholder="Words")
                    yield Input(value=cfg.output_dir, id="s_output", placeholder="Output dir")

                with Horizontal(classes="form-row"):
                    yield Input(value=",".join(cfg.gemini_api_keys), id="s_keys", placeholder="Gemini API keys")

                with Horizontal(classes="form-row"):
                    yield Button("Source Voice", id="btn_src_voice")
                    yield Button("Target Voice", id="btn_tgt_voice")

                with Horizontal(classes="form-row"):
                    yield Label("Show Logs")
                    yield Switch(value=cfg.show_logs, id="s_show_logs")

                with Horizontal(classes="form-row"):
                    yield Label("GPU Encoding")
                    yield Switch(value=cfg.use_gpu, id="s_use_gpu")

                with Horizontal(classes="form-row"):
                    yield Button("Save", variant="success", id="save")
                    yield Button("Back", variant="error", id="cancel")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "save":
            self._save()
        elif bid == "cancel":
            self.app.pop_screen()
        elif bid == "btn_src_voice":
            self.app.push_screen(VoicePickerScreen(self.app.cfg.source_lang, "source"))
        elif bid == "btn_tgt_voice":
            self.app.push_screen(VoicePickerScreen(self.app.cfg.target_lang, "target"))

    def _save(self) -> None:
        cfg = self.app.cfg
        cfg.source_lang = str(self.query_one("#s_source_lang", Select).value)
        cfg.target_lang = str(self.query_one("#s_target_lang", Select).value)
        try:
            cfg.words_per_video = int(self.query_one("#s_words", Input).value or "5")
        except ValueError:
            cfg.words_per_video = 5
        cfg.difficulty = str(self.query_one("#s_difficulty", Select).value)
        cfg.tts.provider = str(self.query_one("#s_provider", Select).value)
        cfg.output_dir = self.query_one("#s_output", Input).value or "./output"
        keys = self.query_one("#s_keys", Input).value
        cfg.gemini_api_keys = [k.strip() for k in keys.split(",") if k.strip()]
        cfg.show_logs = self.query_one("#s_show_logs", Switch).value
        cfg.use_gpu = self.query_one("#s_use_gpu", Switch).value
        save_config(cfg)
        self.app.pop_screen()


# ---------------------------------------------------------------------------
# Voice Picker
# ---------------------------------------------------------------------------

class VoicePickerScreen(Screen):
    """Pick a voice from a filtered list."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, lang_code: str, target: str) -> None:
        super().__init__()
        self.lang_code = lang_code
        self.target = target  # "source" or "target"
        self.voices: list[VoiceInfo] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="voice-picker"):
            yield Static(f"Pick {self.target.title()} Voice ({self.lang_code.upper()})", classes="title")
            yield DataTable(id="voice_table")
            with Horizontal(classes="form-row"):
                yield Button("Select", variant="success", id="vp_select")
                yield Button("Cancel", variant="error", id="vp_cancel")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#voice_table", DataTable)
        table.add_columns("#", "Name", "Voice ID", "Description")
        table.cursor_type = "row"
        table.zebra_stripes = True

        cfg = self.app.cfg
        try:
            self.voices = await voices_for_language(cfg.tts.provider, self.lang_code)
        except Exception as e:
            logger.error("Voice fetch failed: %s", e)
            self.voices = []

        if not self.voices:
            table.add_row("—", "No voices found", "Enter manually in settings", "")
            return

        for i, v in enumerate(self.voices, 1):
            name = v.name
            if len(name) > 14:
                name = name[:11] + "..."
            vid = v.voice_id
            if len(vid) > 22:
                vid = vid[:19] + "..."
            desc = v.description
            if len(desc) > 28:
                desc = desc[:25] + "..."
            table.add_row(str(i), name, vid, desc)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "vp_select":
            self._select()
        elif event.button.id == "vp_cancel":
            self.app.pop_screen()

    def _select(self) -> None:
        table = self.query_one("#voice_table", DataTable)
        if not self.voices:
            self.app.pop_screen()
            return

        cursor = table.cursor_row
        if cursor is None or cursor < 0 or cursor >= len(self.voices):
            self.app.pop_screen()
            return

        voice_id = self.voices[cursor].voice_id
        if self.target == "source":
            self.app.cfg.tts.source_voice = voice_id
        else:
            self.app.cfg.tts.target_voice = voice_id
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class FluxApp(App):
    """Main Textual application."""

    CSS = CSS
    SCREENS = {
        "main": MainScreen,
        "generate": GenerateScreen,
        "settings": SettingsScreen,
    }

    def __init__(self) -> None:
        super().__init__()
        self.cfg = load_config()

    def on_mount(self) -> None:
        self.push_screen("main")


def run() -> None:
    app = FluxApp()
    app.run()
