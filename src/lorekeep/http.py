"""The one HTTP client: plain `httpx`, no cache library, the same in tests and production."""

from __future__ import annotations

from importlib import metadata

import httpx

TIMEOUT_SECONDS = 30.0


def user_agent() -> str:
    """`lorekeep/<version>`, so a publisher can tell who asked."""
    return f"lorekeep/{metadata.version('lorekeep')}"


def make_client(transport: httpx.BaseTransport) -> httpx.Client:
    """A client over the edge's transport that follows redirects and names lorekeep."""
    return httpx.Client(
        transport=transport,
        follow_redirects=True,
        headers={"User-Agent": user_agent()},
        timeout=TIMEOUT_SECONDS,
    )


def media_type(response: httpx.Response) -> str:
    """The response's media type without parameters, lower-cased (`text/markdown`)."""
    return response.headers.get("content-type", "").split(";")[0].strip().lower()
