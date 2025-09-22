from __future__ import annotations
import asyncio
import os
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.binding import Binding
from .panes import TerminalPane, AIPane, StatusBar
from .pty_runner import run_command_stream
from .parsers.nmap_xml import parse_nmap_xml_text
from .ai.ollama_client import stream_analysis
from .config import settings

class TextualAITerminal(App):
    CSS = """
    Screen { layout: vertical; }
    Horizontal { height: 1fr; }
    #left { width: 1fr; }
    #right { width: 1fr; border-left: solid #555555; }
    #ai_body { height: 1fr; overflow: auto; }
    #term_output { height: 1fr; overflow: auto; }
    """

    BINDINGS = [
        Binding("f2", "toggle_safe_mode", "Toggle Safe Mode"),
        Binding("ctrl+c", "cancel_running", "Cancel Running"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.safe_mode = settings.safe_mode
        self._current_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            self.term = TerminalPane(id="left")
            self.ai = AIPane(id="right")
            yield self.term
            yield self.ai
        yield StatusBar()

    def on_mount(self):
        self.update_status()
        # Hook input submit by watching Input (Textual's Input widget fires events)
        input_widget = self.term.query_one("#cmd_input")
        input_widget.can_focus = True

    def update_status(self):
        mode = "SAFE" if self.safe_mode else "AGGRESSIVE"
        self.sub_title = f"Model: {settings.ollama_model} • Mode: {mode}"

    def action_toggle_safe_mode(self):
        self.safe_mode = not self.safe_mode
        self.update_status()
        self.ai.update_text(f"Safe mode set to {self.safe_mode}\n")

    def action_cancel_running(self):
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self.term.write("\n[red]Cancelled current command.[/red]\n")

    async def on_input_submitted(self, event):
        """Textual Input submitted handler — input event object contains value."""
        value = event.value if hasattr(event, "value") else ""
        await self.on_submit(value)

    async def on_submit(self, value: str):
        cmd = value.strip()
        if not cmd:
            return
        # clear input for next command
        input_widget = self.term.query_one("#cmd_input")
        input_widget.value = ""
        self.term.history.append(cmd)
        self.term.write(f"\n[b]> {cmd}[/b]\n")
        self.ai.update_text("Analyzing…\n")
        # Start run in background
        self._current_task = asyncio.create_task(self._run_and_analyze(cmd))

    async def _run_and_analyze(self, cmd: str):
        stdout_buf = []
        stderr_buf = []
        try:
            async for stream, chunk in run_command_stream(cmd):
                if stream == "stdout":
                    stdout_buf.append(chunk)
                else:
                    stderr_buf.append(chunk)
                self.term.write(chunk)
        except asyncio.CancelledError:
            return

        stdout_text = "".join(stdout_buf)
        stderr_text = "".join(stderr_buf)

        structured = None
        if "<nmaprun" in stdout_text:
            structured = parse_nmap_xml_text(stdout_text).model_dump()
        else:
            # naive: if command contains -oX <file>, try to open it
            try:
                parts = cmd.split()
                if "-oX" in parts:
                    idx = parts.index("-oX")
                    xml_path = parts[idx + 1]
                    if os.path.exists(xml_path):
                        with open(xml_path, "r", encoding="utf-8") as f:
                            structured = parse_nmap_xml_text(f.read()).model_dump()
            except Exception:
                structured = None

        payload = {
            "command": cmd,
            "structured_output": structured or {},
            "policy": {"safe_mode": self.safe_mode},
        }

        # 3) Stream AI analysis to right pane
        self.ai.update_text("")
        try:
            async for delta in stream_analysis(payload):
                self.ai.update_text(delta, append=True)
        except Exception as e:
            self.ai.update_text(f"\n[red]AI error: {e}[/red]\n")
        self.ai.update_text("\n")

if __name__ == "__main__":
    app = TextualAITerminal()
    app.run()
