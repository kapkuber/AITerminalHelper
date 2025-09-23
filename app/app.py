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
    #ai_body { height: 1fr; overflow: auto; text-wrap: wrap; }
    #term_output { height: 1fr; overflow: auto; text-wrap: wrap; }
    """

    BINDINGS = [
        Binding("ctrl+c", "cancel_running", "Cancel Running"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
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
        input_widget = self.term.query_one("#cmd_input")
        input_widget.can_focus = True

    def update_status(self):
        self.sub_title = f"Model: {settings.ollama_model}"

    def action_cancel_running(self):
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self.term.write("\nCancelled current command.\n")

    async def on_input_submitted(self, event):
        """Textual Input submitted handler: event has .value"""
        value = event.value if hasattr(event, "value") else ""
        await self.on_submit(value)

    async def on_submit(self, value: str):
        cmd = value.strip()
        if not cmd:
            return
        input_widget = self.term.query_one("#cmd_input")
        input_widget.value = ""
        self.term.history.append(cmd)
        self.term.write(f"\n> {cmd}\n")
        self.ai.update_text("Analyzing...\n")
        self._current_task = asyncio.create_task(self._run_and_analyze(cmd))

    async def _run_and_analyze(self, cmd: str):
        stdout_buf: list[str] = []
        stderr_buf: list[str] = []
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
        }

        # Stream AI analysis to right pane (throttled flush for speed)
        self.ai.update_text("")
        got_any = False
        try:
            flush_buf: list[str] = []
            loop = asyncio.get_running_loop()
            last_flush = loop.time()
            FLUSH_INTERVAL = 0.08  # seconds
            FLUSH_BYTES = 600      # flush when buffer gets large

            async for delta in stream_analysis(payload):
                got_any = True
                flush_buf.append(delta)
                now = loop.time()
                if sum(len(x) for x in flush_buf) >= FLUSH_BYTES or (now - last_flush) >= FLUSH_INTERVAL:
                    self.ai.update_text("".join(flush_buf), append=True)
                    flush_buf.clear()
                    last_flush = now

            if flush_buf:
                self.ai.update_text("".join(flush_buf), append=True)
        except Exception as e:
            self.ai.update_text(f"\nAI error: {e}\n", append=True)
        finally:
            if not got_any:
                self.ai.update_text(
                    "\n(no AI tokens received — check OLLAMA_HOST/OLLAMA_MODEL or set AI_DEBUG=1)\n",
                    append=True,
                )
            self.ai.update_text("\n", append=True)


if __name__ == "__main__":
    app = TextualAITerminal()
    app.run()

