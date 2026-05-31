from __future__ import annotations

import requests

from confscan.data import http


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"ok": True}
        self.ok = status_code < 400
        self.headers = {"Retry-After": "0"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("bad")

    def json(self):
        return self._payload


def test_get_json_retries_429(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse(429 if calls["n"] == 1 else 200)

    monkeypatch.setattr(http.SESSION, "request", fake_request)
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    assert http.get_json("https://example.test") == {"ok": True}
    assert calls["n"] == 2


def test_post_json_raises_after_failure(monkeypatch) -> None:
    def fake_request(*args, **kwargs):
        raise requests.RequestException("down")

    monkeypatch.setattr(http.SESSION, "request", fake_request)
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    try:
        http.post_json("https://example.test", {"x": 1}, retries=1)
    except RuntimeError as exc:
        assert "failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
