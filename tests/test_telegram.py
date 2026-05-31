from __future__ import annotations

from confscan.alert.telegram import TelegramAlerter, _split


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.ok = status_code < 400

    def json(self):
        return {"parameters": {"retry_after": 0}}


def test_split_chunks_long_text() -> None:
    chunks = _split("a\n" * 4000, max_len=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_telegram_send_retries_429(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_post(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse(429 if calls["n"] == 1 else 200)

    monkeypatch.setattr("confscan.alert.telegram.requests.post", fake_post)
    monkeypatch.setattr("confscan.alert.telegram.time.sleep", lambda _: None)
    assert TelegramAlerter("token", "chat").send("hello") is True
    assert calls["n"] == 2


def test_telegram_missing_creds_returns_false() -> None:
    assert TelegramAlerter("", "").send("hello") is False
