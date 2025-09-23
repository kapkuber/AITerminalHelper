from __future__ import annotations
from textual.widgets import Static, Input, Footer
import re
try:
    # Newer Textual versions
    from textual.widgets import TextLog as _TextLog
except ImportError:
    try:
        # Older Textual fallback
        from textual.widgets import Log as _TextLog
    except ImportError:  # pragma: no cover
        try:
            from textual.widgets import RichLog as _TextLog
        except Exception:
            _TextLog = None  # Last resort; will raise at runtime if missing
TextLog = _TextLog

_TAG_RE = re.compile(r"\[(?:/?[a-zA-Z]+)(?:=[^\]]+)?\]")
def _strip_markup(text: str) -> str:
    try:
        return _TAG_RE.sub("", text)
    except Exception:
        return text
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Vertical

class TerminalPane(Widget):
    """A minimalist terminal-like widget that accepts commands and streams output."""
    history: list[str] = []

    def compose(self) -> ComposeResult:
        yield Vertical(
            Input(placeholder="Enter command and press Enter…", id="cmd_input"),
            TextLog(id="term_output"),
        )

    def on_mount(self):
        term = self.query_one("#term_output", TextLog)
        try:
            term.clear()
        except Exception:
            pass
        self.focus_input()

    def focus_input(self):
        self.query_one("#cmd_input", Input).focus()

    def write(self, text: str):
        out = self.query_one("#term_output", TextLog)
        text = _strip_markup(text)
        try:
            out.write(text)
        except Exception:
            for line in text.splitlines(True):
                out.write(line)

class AIPane(Widget):
    buffer = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("AI Assistant Output", id="ai_header")
        yield TextLog(id="ai_body")

    def on_mount(self):
        self.update_text("(no analysis yet)\n")

    def update_text(self, text: str, append: bool = False):
        body = self.query_one("#ai_body", TextLog)
        if not append:
            try:
                body.clear()
            except Exception:
                pass
        body.write(_strip_markup(text))

class StatusBar(Footer):
    pass
