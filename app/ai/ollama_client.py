from __future__ import annotations
import json
import httpx
from typing import AsyncIterator, Dict, Any
from ..config import settings

SYSTEM_PROMPT = None

async def _load_system_prompt() -> str:
    global SYSTEM_PROMPT
    if SYSTEM_PROMPT is None:
        try:
            base = __file__.rsplit("ai/ollama_client.py", 1)[0]
            with open(base + "prompts/system_prompt.txt", "r", encoding="utf-8") as f:
                SYSTEM_PROMPT = f.read()
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
        async with client.stream("POST", url, json=req) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # Ollama streams JSON lines; try to parse each line.
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # ignore non-json lines
                    continue
                # Typical structure: {"id":..., "object":"chat.completion.chunk","message": {"content": "..."}, ...}
                # Adjust depending on your Ollama version.
                if obj.get("done"):
                    break
                delta = None
                if isinstance(obj.get("message"), dict):
                    # message.content may be a string or list; handle common cases
                    content = obj["message"].get("content")
                    if isinstance(content, str):
                        delta = content
                    elif isinstance(content, list):
                        # content may be a list of pieces
                        delta = "".join([c.get("text", "") for c in content if isinstance(c, dict)])
                else:
                    # fallback: check top-level "content"
                    delta = obj.get("content")
                if delta:
                    yield delta
