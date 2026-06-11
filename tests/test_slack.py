from __future__ import annotations

from confscan.alert.slack import SlackAlerter, _split
from confscan.score.confluence import ConfluenceScorer


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.ok = status_code < 400
        self.headers = {"Retry-After": "0"}


def test_slack_split_chunks_long_text() -> None:
    chunks = _split("a\n" * 3000, max_len=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_slack_send_retries_429(monkeypatch) -> None:
    calls = {"n": 0, "payloads": []}

    def fake_post(*args, **kwargs):
        calls["n"] += 1
        calls["payloads"].append(kwargs["json"])
        return FakeResponse(429 if calls["n"] == 1 else 200)

    monkeypatch.setattr("confscan.alert.slack.requests.post", fake_post)
    monkeypatch.setattr("confscan.alert.slack.time.sleep", lambda _: None)

    assert SlackAlerter("https://example.invalid/webhook").send("hello") is True
    assert calls["n"] == 2
    assert calls["payloads"][0]["text"] == "hello"


def test_slack_missing_webhook_returns_false() -> None:
    assert SlackAlerter("").send("hello") is False


def test_slack_confluence_format(monkeypatch) -> None:
    sent = []

    def fake_send(self, text):
        sent.append(text)
        return True

    monkeypatch.setattr(SlackAlerter, "send", fake_send)
    result = ConfluenceScorer().score("BTCUSDT", {"ta": 80, "fa": 60, "cex": 50, "onchain": 40})

    assert SlackAlerter("https://example.invalid/webhook").send_confluence(result) is True
    assert "*BTCUSDT* confluence" in sent[0]
