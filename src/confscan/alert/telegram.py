"""Telegram alert sender with chunking and bounded retry."""

from __future__ import annotations

import time
from typing import Any, cast

import requests

from confscan.score.confluence import ConfluenceResult

API = "https://api.telegram.org/bot{token}/{method}"


def _split(text: str, max_len: int = 3800) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str, *, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        url = API.format(token=self.bot_token, method="sendMessage")
        for chunk in _split(text, 3800):
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            try:
                response = requests.post(url, json=cast(Any, payload), timeout=20)
                if response.status_code == 429:
                    retry = response.json().get("parameters", {}).get("retry_after", 3)
                    time.sleep(min(float(retry) + 1.0, 30.0))
                    response = requests.post(url, json=cast(Any, payload), timeout=20)
                if not response.ok:
                    return False
            except requests.RequestException:
                return False
        return True

    def send_confluence(self, result: ConfluenceResult) -> bool:
        marker = {"STRONG": "green", "MODERATE": "yellow"}.get(result.label, "neutral")
        lines = [
            f"<b>{result.symbol}</b> confluence: {result.total:.1f}/100 ({result.label}, {marker})",
            f"weight mode: {result.weight_mode}",
        ]
        for layer in result.layers:
            lines.append(
                f"{layer.name}: raw={layer.raw:.1f}, weight={layer.weight:.2f}, "
                f"contribution={layer.contribution:.1f}"
            )
        return self.send("\n".join(lines))
