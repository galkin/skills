"""A Recheck: one conditional request to a Version's `original.url`, compared as ADR 0007 says.

`plan` says what becomes of a stored Version: `Fresh` inside the freshness window (returned, no
request), `Skipped` when it can never be asked (an owner's Source has no publisher; a browser's
bytes differ on every visit), else an `Ask` that `perform` sends. `get` plans with the Project's
window and `recheck` with none, so every Source in scope is asked whatever its age. The plain
client only: the browser is for a first fetch, never for a comparison.
A `200` is reread by the step that wrote the Version (`cascade.step_of`): its media-type gate
first (a Twin takes Markdown, the HTML step HTML, the PDF step a PDF; anything else is `error`,
nothing stored). A `304`, equal received bytes, or equal Markdown after conversion by that step is
`unchanged`; different bytes and different Markdown is `changed` and a new Version; `404`/`410` is
`gone`; anything else is `error` with the status code or the exception's class name. Every answer
is one `checks.csv` row through the commit point, and the Version latest after the check is named
in that row. `compare` records a full fetch that `get` made of a Source it already held (an alias
not yet known: a redirect to it) the same way. Nothing else writes a `checks.csv` row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import astuple, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from lorekeep import cascade, provenance
from lorekeep.project import HostRule
from lorekeep.store import (
    OWNER_SCHEME,
    AliasRow,
    NewVersion,
    RecheckResult,
    RecheckRow,
    TagRow,
    VersionInfo,
    commit,
    read_rows,
)
from lorekeep.urls import other_canonical, trust


@dataclass(frozen=True)
class Recheck:
    """What one Recheck found: its `checks.csv` result, the status it records, the Version that
    is latest afterwards, and a warning for stderr when the stored text is returned regardless."""

    result: RecheckResult
    status: str
    path: Path
    warning: str | None = None


@dataclass(frozen=True)
class Fresh:
    """Inside the window: the stored Version is returned and nothing is asked."""

    path: Path


@dataclass(frozen=True)
class Skipped:
    """Never asked: an owner's Source has no publisher, a browser's bytes differ on every visit."""

    path: Path
    reason: str


@dataclass(frozen=True)
class Ask:
    """Outside the window: one conditional request to `address`, the address the bytes came from
    (`original.url`), with the Version's validators as headers."""

    address: str
    headers: dict[str, str]


def plan(store: Path, stored: VersionInfo, *, window_days: int) -> Fresh | Skipped | Ask:
    """What becomes of `stored`: its age — from the later of `fetched_at` and its last
    `checks.csv` row of any result — under `window_days` is `Fresh`; else `Skipped` with the
    reason, or the `Ask` that `perform` sends. A window of 0 asks whatever the age."""
    if window_days > 0 and _is_fresh(stored, read_rows(store, RecheckRow), window_days):
        return Fresh(stored.path)
    if stored.url.startswith(OWNER_SCHEME):
        return Skipped(
            stored.path, f"{stored.url} is an owner's Source and has no publisher to ask"
        )
    step = cascade.step_of(str(stored.frontmatter.get("converter", "")))
    if isinstance(step, cascade.Fallthrough):
        return Skipped(stored.path, f"{stored.url} {step.reason}")
    return _ask(stored)


def _ask(stored: VersionInfo) -> Ask:
    head = stored.frontmatter
    original: dict[str, Any] = head.get("original") or {}
    headers = {
        name: str(head[key])
        for name, key in (("If-None-Match", "etag"), ("If-Modified-Since", "last_modified"))
        if head.get(key)
    }
    return Ask(str(original.get("url") or stored.url), headers)


def perform(
    store: Path,
    stored: VersionInfo,
    client: httpx.Client,
    rules: Sequence[HostRule],
    *,
    tags: Sequence[TagRow] = (),
) -> Recheck:
    """Send the `Ask` for `stored` to its publisher and record the answer."""
    head = stored.frontmatter
    original: dict[str, Any] = head.get("original") or {}
    address, headers = astuple(_ask(stored))
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

    found = trust(stored.url, rules)
    step = cascade.step_of(str(head.get("converter", "")))
    assert not isinstance(step, cascade.Fallthrough), "a skipped Version is never asked"
    fetched = step.reread(response, found.rule, unchanged=str(original.get("sha256")))
    if isinstance(fetched, cascade.Same):
        return _record(store, stored, "unchanged", "200", tags)
    if isinstance(fetched, cascade.Fallthrough):
        return _record(store, stored, "error", "200", tags, fetched.reason)
    version = NewVersion(
        frontmatter=provenance.build(
            fetched,
            stored.url,
            found.publisher,
            found.authority,
            canonical=other_canonical(fetched.canonical, stored.url, rules),
        ),
        body=fetched.markdown,
        original=fetched.original,
        original_ext=fetched.original_ext,
    )
    return compare(store, stored, version, tags=tags)


def compare(
    store: Path,
    stored: VersionInfo,
    version: NewVersion,
    *,
    tags: Sequence[TagRow] = (),
    aliases: Sequence[AliasRow] = (),
) -> Recheck:
    """A Version just fetched of a Source whose latest Version is `stored`, recorded as a Recheck
    with status `200`: `unchanged` when its Markdown hash is the stored one (the file is already
    there), else `changed` and the new Version beside the old. The one commit of this answer."""
    sha256 = str(version.frontmatter["sha256"])
    result: RecheckResult = "unchanged" if sha256 == stored.sha256 else "changed"
    row = RecheckRow(stored.url, provenance.now(), result, "200", sha256)
    path = commit(store, version, tags=tags, checks=[row], aliases=aliases)
    assert path is not None
    return Recheck(result, "200", path)


def _record(
    store: Path,
    stored: VersionInfo,
    result: RecheckResult,
    status: str,
    tags: Sequence[TagRow],
    warning: str | None = None,
) -> Recheck:
    row = RecheckRow(stored.url, provenance.now(), result, status, stored.sha256)
    commit(store, tags=tags, checks=[row])
    message = None if warning is None else f"{warning}; returning the stored Version"
    return Recheck(result, status, stored.path, message)


def verified_at(store: Path, head: Mapping[str, Any]) -> str:
    """When the publisher last confirmed this very Version: the latest `unchanged` Recheck naming
    its `sha256` and made after it was fetched; else its `fetched_at`."""
    fetched_at = str(head["fetched_at"])
    confirmed = [
        row.checked_at
        for row in read_rows(store, RecheckRow)
        if row.url == head["url"]
        and row.result == "unchanged"
        and row.sha256 == head["sha256"]
        and row.checked_at >= fetched_at
    ]
    return max(confirmed, default=fetched_at)


def _is_fresh(stored: VersionInfo, checks: Sequence[RecheckRow], window_days: int) -> bool:
    """Whether the Version's age, counted from the later of its `fetched_at` and its last
    `checks.csv` row of any result, is under the window."""
    last = max([stored.fetched_at, *(row.checked_at for row in checks if row.url == stored.url)])
    try:
        since = provenance.parse_time(last)
    except ValueError:
        return False
    return datetime.now(UTC) - since < timedelta(days=window_days)
