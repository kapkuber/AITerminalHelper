from __future__ import annotations
from textual.widgets import Static, Input, Footer
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
            Static("", id="term_output"),
        )

    def on_mount(self):
        self.query_one("#term_output", Static).update("[b]Ready.[/b]\n")
        self.focus_input()

    def focus_input(self):
        self.query_one("#cmd_input", Input).focus()

    def write(self, text: str):
        out = self.query_one("#term_output", Static)
        # append text (Static.renderable holds a Renderable; using str concatenation is fine for this skeleton)
        current = out.renderable if out.renderable is not None else ""
        out.update(current + text)

class AIPane(Widget):
    buffer = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("AI Assistant Output", id="ai_header")
        yield Static("", id="ai_body")

    def on_mount(self):
        self.update_text("(no analysis yet)\n")

    def update_text(self, text: str, append: bool = False):
        body = self.query_one("#ai_body", Static)
        current = body.renderable if body.renderable is not None else ""
        if append:
            body.update(current + text)
        else:
            body.update(text)

class StatusBar(Footer):
    pass
