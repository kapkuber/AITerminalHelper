from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Settings:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    safe_mode: bool = os.getenv("SAFE_MODE", "1") not in {"0", "false", "False"}
    read_timeout_secs: int = int(os.getenv("READ_TIMEOUT_SECS", "60"))

settings = Settings()
