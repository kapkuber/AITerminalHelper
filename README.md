# Textual AI Terminal (Ollama edition)


Two‑pane terminal: left is a real in‑app terminal; right streams AI explanations and safe next‑step suggestions.


- **LLM**: [Ollama](https://github.com/ollama/ollama) (local). Default: `llama3.1`.
- **UI**: [Textual](https://github.com/Textualize/textual).
- **Parsers**: Nmap XML → structured JSON.
- **Safety**: `SAFE_MODE=1` by default (no exploit payloads).


## Quick start


```bash
# 1) Create & activate venv
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate


# 2) Install deps
pip install -r requirements.txt


# 3) Install & start Ollama (separately), then pull a model
# https://ollama.com/download
ollama pull llama3.1


# 4) Run the app
python -m app.app
```


## Usage
- Type commands in the left terminal pane (e.g., `nmap -sn 192.168.1.0/24 -oX sweep.xml`).
- If an nmap XML file is detected, the parser summarizes hosts; the right pane asks the LLM for device IDs and safe next steps.
- Press `F2` to toggle **Safe Mode** on/off (off enables more aggressive enumeration tips, still no exploit payloads by default).
- Press `Ctrl+C` inside the terminal to stop a running command.


## Configuration
Env vars:
- `OLLAMA_HOST` (default `http://127.0.0.1:11434`)
- `OLLAMA_MODEL` (default `llama3.1`)
- `SAFE_MODE` (default `1`)
- `READ_TIMEOUT_SECS` (default `60`)


## Notes
- PTY behavior on Windows may require WSL. If PTY is unavailable, we fall back to a subprocess pipe (still works for most commands).
- Add more parsers under `app/parsers/` and call them from `app.app` after each command finishes.