"""HTTP helpers with bounded retry/backoff."""

from __future__ import annotations

import time
from typing import Any

import requests

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "confluence-scanner/0.1"})


def _request_json(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
    headers: dict | None = None,
    retries: int = 3,
    timeout: float = 20.0,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = SESSION.request(
                method,
                url,
                params=params,
                json=body,
                headers=headers,
                timeout=timeout,
            )
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", "2"))
                time.sleep(min(wait, 30.0))
                continue
            if 500 <= response.status_code < 600 and attempt < retries - 1:
                time.sleep(1.5**attempt)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.5**attempt)
    raise RuntimeError(f"{method} {url} failed after {retries} retries: {last_exc}")


def get_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    *,
    retries: int = 3,
    timeout: float = 20.0,
):
    return _request_json(
        "GET",
        url,
        params=params,
        headers=headers,
        retries=retries,
        timeout=timeout,
    )


def post_json(
    url: str,
    body: dict,
    headers: dict | None = None,
    *,
    retries: int = 3,
    timeout: float = 20.0,
):
    return _request_json(
        "POST",
        url,
        body=body,
        headers=headers,
        retries=retries,
        timeout=timeout,
    )
