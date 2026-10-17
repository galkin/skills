"""A Version's Provenance frontmatter built from what the cascade fetched, and the clock."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from lorekeep.cascade.step import Fetched

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def now() -> str:
    return datetime.now(UTC).strftime(TIME_FORMAT)


def parse_time(value: str) -> datetime:
    """A `fetched_at` or `checked_at` as an aware UTC time; a naive value is taken as UTC."""
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def build(
    fetched: Fetched, url: str, publisher: str, authority: str, *, canonical: str | None = None
) -> dict[str, Any]:
    """The Version's frontmatter, in the order a reader expects; absent values are left out.
    `canonical` is the address the page declares as its own when it is not `url`."""
    return {
        "url": url,
        "fetched_at": now(),
        "sha256": hashlib.sha256(fetched.markdown).hexdigest(),
        "publisher": publisher,
        "authority": authority,
        "converter": fetched.converter,
        "etag": fetched.etag,
        "last_modified": fetched.last_modified,
        "title": fetched.title,
        "modified": fetched.modified,
        "canonical": canonical,
        "original": {
            "url": fetched.original_url,
            "mediatype": fetched.mediatype,
            "sha256": fetched.original_sha256,
            "stored": fetched.original is not None,
        },
        "origin": "web",
    }
