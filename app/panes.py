from __future__ import annotations
from textual.widgets import Static, Input, Footer
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Vertical

class TerminalPane(Widget):
    """A minimalist terminal-like widget that accepts commands and streams output."""
    history: list[str] = []
    _output_text: str = ""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Input(placeholder="Enter command and press Enter…", id="cmd_input"),
            Static("", id="term_output"),
        )

    def on_mount(self):
        self._output_text = "[b]Ready.[/b]\n"
        self.query_one("#term_output", Static).update(self._output_text)
        self.focus_input()

    def focus_input(self):
        self.query_one("#cmd_input", Input).focus()

    def write(self, text: str):
        out = self.query_one("#term_output", Static)
        # Maintain our own buffer instead of reading widget internals
        self._output_text += text
        out.update(self._output_text)

class AIPane(Widget):
    buffer = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("AI Assistant Output", id="ai_header")
        yield Static("", id="ai_body")

    def on_mount(self):
        self.update_text("(no analysis yet)\n")

    def update_text(self, text: str, append: bool = False):
        body = self.query_one("#ai_body", Static)
        if append:
            self.buffer += text
        else:
            self.buffer = text
        body.update(self.buffer)

class StatusBar(Footer):
    pass
