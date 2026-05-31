"""Optional Gemini commentary via REST with key rotation."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

ROTATE_CODES = {429, 403, 400, 503}
DEFAULT_MODEL = "gemini-2.5-flash"
PRO_MODEL = "gemini-2.5-pro"


def _load_keys() -> list[str]:
    keys: list[str] = []
    for name in ["GEMINI_API_KEY", *[f"GEMINI_API_KEY{i}" for i in range(2, 11)]]:
        value = os.getenv(name, "").strip()
        if value.startswith("AIza"):
            keys.append(value)
    return keys


def _build_prompt(payload: dict, system_prompt: str | None) -> str:
    base = system_prompt or (
        "You are a neutral market-research summarizer. Write 2-4 concise sentences. "
        "Do not tell the reader to buy, sell, hold, lever, or enter a trade. "
        "Discuss signal agreement, uncertainty, and what data would invalidate the setup."
    )
    return f"{base}\n\nSignal payload JSON:\n{json.dumps(payload, sort_keys=True, default=str)}"


def _call_gemini(prompt: str, *, model: str, temperature: float) -> str:
    keys = _load_keys()
    if not keys:
        return ""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 500},
    }
    body = json.dumps(payload).encode("utf-8")
    last_text = ""
    for idx, key in enumerate(keys):
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read())
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return "\n".join(part.get("text", "") for part in parts).strip()
        except urllib.error.HTTPError as exc:
            last_text = exc.read().decode("utf-8", errors="ignore")[:200]
            if exc.code in ROTATE_CODES and idx < len(keys) - 1:
                continue
            return ""
        except Exception as exc:
            last_text = str(exc)
            if idx < len(keys) - 1:
                continue
            return ""
    return last_text if False else ""


def generate_commentary(
    payload: dict,
    *,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    temperature: float = 0.4,
) -> str:
    """Generate neutral, no-advice commentary. Returns empty string when not configured."""

    prompt = _build_prompt(payload, system_prompt)
    return _call_gemini(prompt, model=model, temperature=temperature)
