"""A Recheck: one conditional request to a Version's `original.url`, compared as ADR 0001 says.

`get` runs it on a Version older than the freshness window and `recheck` (ticket 09) on every
Source in scope. The plain client only: the browser is for a first fetch, never for a comparison.
A `304`, equal received bytes, or equal Markdown after conversion by the Version's step is
`unchanged`; different bytes and different Markdown is `changed` and a new Version; `404`/`410` is
`gone`; anything else is `error` with the status code or the exception's class name. Every answer
is one `checks.csv` row through the commit point, and the Version latest after the check is named
in that row.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from lorekeep import provenance
from lorekeep.cascade.page import CONVERTERS, convert_response
from lorekeep.cascade.step import Fallthrough
from lorekeep.cascade.twin import CONVERTER as TWIN_CONVERTER
from lorekeep.cascade.twin import accepts, read_twin
from lorekeep.http import media_type
from lorekeep.project import HostRule
from lorekeep.store import CheckRow, NewVersion, TagRow, VersionInfo, commit
from lorekeep.urls import trust

BROWSER_MARK = "via crawl4ai"
OWNER_SCHEME = "owner:"


@dataclass(frozen=True)
class Recheck:
    """What one Recheck found: its `checks.csv` result, the status it records, the Version that
    is latest afterwards, and a warning for stderr when the stored text is returned regardless."""

    result: str
    status: str
    path: Path
    warning: str | None = None


def skipped_reason(stored: VersionInfo) -> str | None:
    """Why a Version is never asked: an owner's Source has no publisher, and a browser's bytes
    differ on every visit."""
    if stored.url.startswith(OWNER_SCHEME):
        return f"{stored.url} is an owner's Source and has no publisher to ask"
    if BROWSER_MARK in str(stored.frontmatter.get("converter", "")):
        return f"{stored.url} was read through the browser and cannot be compared"
    return None


def asked_address(stored: VersionInfo) -> str:
    """Where a Recheck sends its request: `original.url`, the address the bytes came from."""
    original: dict[str, Any] = stored.frontmatter.get("original") or {}
    return str(original.get("url") or stored.url)


def perform(
    store: Path,
    stored: VersionInfo,
    client: httpx.Client,
    rules: Sequence[HostRule],
    *,
    tags: Sequence[TagRow] = (),
) -> Recheck:
    """Ask the publisher of `stored` whether it changed and record the answer."""
    head = stored.frontmatter
    original: dict[str, Any] = head.get("original") or {}
    address = asked_address(stored)
    headers = {
        name: str(head[key])
        for name, key in (("If-None-Match", "etag"), ("If-Modified-Since", "last_modified"))
        if head.get(key)
    }
    try:
        response = client.get(address, headers=headers)
    except httpx.HTTPError as error:
        name = type(error).__name__
        return _record(store, stored, "error", name, tags, f"{address} failed ({name})")
    status = response.status_code
    if status == 304:
        return _record(store, stored, "unchanged", str(status), tags)
    if status in (404, 410):
        return _record(store, stored, "gone", str(status), tags, f"{address} is gone ({status})")
    if status != 200:
        return _record(store, stored, "error", str(status), tags, f"{address} answered {status}")

    rule = trust(stored.url, rules).rule
    mediatype = media_type(response)
    twin = str(head.get("converter")) == TWIN_CONVERTER
    gate = accepts(mediatype, rule) if twin else mediatype in CONVERTERS
    if not gate:
        what = "no Twin" if twin else "unsupported media type"
        reason = f"{what}: {address} answered {mediatype or 'no media type'}"
        return _record(store, stored, "error", "200", tags, reason)
    if hashlib.sha256(response.content).hexdigest() == str(original.get("sha256")):
        return _record(store, stored, "unchanged", "200", tags)
    fetched = read_twin(response, rule) if twin else convert_response(response, mediatype)
    if isinstance(fetched, Fallthrough):
        return _record(store, stored, "error", "200", tags, f"{address}: {fetched.reason}")
    sha256 = hashlib.sha256(fetched.markdown).hexdigest()
    if sha256 == stored.sha256:
        return _record(store, stored, "unchanged", "200", tags)
    found = trust(stored.url, rules)
    version = NewVersion(
        frontmatter=provenance.build(fetched, stored.url, found.publisher, found.authority),
        body=fetched.markdown,
        original=fetched.original,
        original_ext=fetched.original_ext,
    )
    row = CheckRow(stored.url, provenance.now(), "changed", "200", sha256)
    path = commit(store, version, tags=tags, checks=[row])
    assert path is not None
    return Recheck("changed", "200", path)


def _record(
    store: Path,
    stored: VersionInfo,
    result: str,
    status: str,
    tags: Sequence[TagRow],
    warning: str | None = None,
) -> Recheck:
    row = CheckRow(stored.url, provenance.now(), result, status, stored.sha256)
    commit(store, tags=tags, checks=[row])
    message = None if warning is None else f"{warning}; returning the stored Version"
    return Recheck(result, status, stored.path, message)


def is_fresh(stored: VersionInfo, checks: Sequence[CheckRow], window_days: int) -> bool:
    """Whether the Version's age, counted from the later of its `fetched_at` and its last
    `checks.csv` row of any result, is under the window."""
    last = max([stored.fetched_at, *(row.checked_at for row in checks if row.url == stored.url)])
    try:
        since = provenance.parse_time(last)
    except ValueError:
        return False
    return datetime.now(UTC) - since < timedelta(days=window_days)
