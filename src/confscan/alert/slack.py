"""Slack webhook alert sender with chunking and bounded retry."""

from __future__ import annotations

import time
from typing import Any, cast

import requests

from confscan.score.confluence import ConfluenceResult


def _split(text: str, max_len: int = 3000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(line) > max_len:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(line), max_len):
                chunks.append(line[start : start + max_len])
            continue
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


class SlackAlerter:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, text: str) -> bool:
        if not self.webhook_url:
            return False
        for chunk in _split(text, 3000):
            payload = {"text": chunk}
            try:
                response = requests.post(
                    self.webhook_url,
                    json=cast(Any, payload),
                    timeout=20,
                )
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "3")
                    time.sleep(min(float(retry) + 1.0, 30.0))
                    response = requests.post(
                        self.webhook_url,
                        json=cast(Any, payload),
                        timeout=20,
                    )
                if not response.ok:
                    return False
            except requests.RequestException:
                return False
        return True

    def send_confluence(self, result: ConfluenceResult) -> bool:
        marker = {"STRONG": "green", "MODERATE": "yellow"}.get(result.label, "neutral")
        lines = [
            f"*{result.symbol}* confluence: {result.total:.1f}/100 ({result.label}, {marker})",
            f"weight mode: {result.weight_mode}",
        ]
        for layer in result.layers:
            lines.append(
                f"{layer.name}: raw={layer.raw:.1f}, weight={layer.weight:.2f}, "
                f"contribution={layer.contribution:.1f}"
            )
        return self.send("\n".join(lines))
