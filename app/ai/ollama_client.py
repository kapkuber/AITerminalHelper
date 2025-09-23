from __future__ import annotations
import json
from pathlib import Path
import os
from typing import AsyncIterator, Dict, Any

import httpx

from ..config import settings

SYSTEM_PROMPT = None

async def _load_system_prompt() -> str:
    global SYSTEM_PROMPT
    if SYSTEM_PROMPT is None:
        try:
            # Resolve repo root and prompts path robustly across OSes
            here = Path(__file__).resolve()
            repo_root = here.parents[2]  # .../TerminalHelper
            prompt_path = repo_root / "prompts" / "system_prompt.txt"
            SYSTEM_PROMPT = prompt_path.read_text(encoding="utf-8")
        except Exception:
            SYSTEM_PROMPT = (
                "You are a security analysis assistant. Given a command and parsed output, "
                "identify device types and propose SAFE next-step enumeration commands. "
                "If safe_mode is true, refuse exploit payloads. Return concise, actionable text."
            )
    return SYSTEM_PROMPT

async def stream_analysis(payload: Dict[str, Any]) -> AsyncIterator[str]:
    """Stream tokens from Ollama /api/chat endpoint.

    payload example:
    {
      "command": "nmap -sn ... -oX sweep.xml",
      "structured_output": { ... },
      "policy": {"safe_mode": true}
    }
    """
    system_prompt = await _load_system_prompt()

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False)
        },
    ]

    url = f"{settings.ollama_host}/api/chat"
    req = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=settings.read_timeout_secs) as client:
        # Keep initial debug quiet unless explicitly asked
        if os.getenv("AI_DEBUG_VERBOSE"):
            yield f"(debug) POST {url} model={settings.ollama_model} stream=True\n"
        yielded_any = False
        async with client.stream("POST", url, json=req) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                raw = line.strip()
                if raw.startswith("data:"):
                    raw = raw[5:].strip()
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    # Optional debug of raw line
                    if os.getenv("AI_DEBUG_VERBOSE"):
                        yield f"(debug) non-json line: {raw}\n"
                    continue

                if isinstance(obj, dict) and obj.get("error"):
                    yield f"LLM error: {obj.get('error')}\n"
                    break

                delta: str | None = None
                if isinstance(obj.get("message"), dict):
                    content = obj["message"].get("content")
                    if isinstance(content, str):
                        delta = content
                    elif isinstance(content, list):
                        delta = "".join(
                            [c.get("text", "") for c in content if isinstance(c, dict)]
                        )
                if delta is None and isinstance(obj.get("response"), str):
                    delta = obj.get("response")
                if delta is None and isinstance(obj.get("content"), str):
                    delta = obj.get("content")
                if delta is None and isinstance(obj.get("delta"), str):
                    delta = obj.get("delta")

                if delta:
                    yielded_any = True
                    yield delta

                if obj.get("done") is True:
                    break

        # Fallback: if nothing yielded (some servers send only a final object), do non-stream
        if not yielded_any:
            if os.getenv("AI_DEBUG_VERBOSE"):
                yield "(debug) no streamed chunks; trying non-stream fallback\n"
            r = await client.post(url, json={**req, "stream": False})
            r.raise_for_status()
            data = r.json()
            text = None
            if isinstance(data, dict):
                if isinstance(data.get("message"), dict) and isinstance(data["message"].get("content"), str):
                    text = data["message"]["content"]
                elif isinstance(data.get("response"), str):
                    text = data.get("response")
                elif isinstance(data.get("content"), str):
                    text = data.get("content")
            if text:
                yield text
            elif os.getenv("AI_DEBUG_VERBOSE"):
                try:
                    yield f"(debug) final object keys: {list(data.keys())}\n"
                except Exception:
                    yield "(debug) unable to read final JSON object\n"
