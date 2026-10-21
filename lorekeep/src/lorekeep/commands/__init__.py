"""One module per subcommand; each exposes `run(args, ctx) -> int`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from lorekeep.project import HostRule
from lorekeep.recheck import verified_at
from lorekeep.store import read_head
from lorekeep.urls import effective_trust


def scope_tags(
    given: Sequence[str] | None, run_tag: str | None, *, everything: bool = False
) -> list[str] | None:
    """The Tags a scoped command covers: every Tag with `--all`; `--tag` repeated; else the
    Run's Tag; with none, every Tag (`None`)."""
    if everything:
        return None
    if given:
        return list(given)
    return [run_tag] if run_tag else None


def plural(count: int, word: str, plural_word: str | None = None) -> str:
    """`1 Version`, `2 Versions`, `0 aliases`: the count and the word it takes."""
    return f"{count} {word if count == 1 else plural_word or word + 's'}"


def version_json(
    store: Path,
    path: Path,
    outcome: str,
    *,
    asked: str,
    rules: Sequence[HostRule],
    requested_url: str | None = None,
    reading: Path | None = None,
) -> dict[str, Any]:
    """The one JSON object `get --json` and `add --json` print: the Version as its file says,
    the command's argument exactly as given (`asked`, a fragment kept), the normalised address
    the caller asked for (`requested_url`, the Version's `url` when not given), when its
    publisher last confirmed it, and what the call did (`outcome`). With a `reading`, `path` is
    the Reading's and `version` the Version's; every other field stays the Version's.
    `publisher` and `authority` are the effective ones, what the current host `rules` say of its
    `url`; the frontmatter's, captured at fetch, follow as `captured_publisher` and
    `captured_authority` when they differ."""
    head = read_head(path)
    publisher, authority = effective_trust(head, rules)
    captured = {
        f"captured_{key}": head[key]
        for key, value in (("publisher", publisher), ("authority", authority))
        if head[key] != value
    }
    paths = {"path": str(reading), "version": str(path)} if reading else {"path": str(path)}
    return {
        **paths,
        "url": head["url"],
        "asked": asked,
        "requested_url": requested_url or head["url"],
        "sha256": head["sha256"],
        "fetched_at": head["fetched_at"],
        "converter": head["converter"],
        "publisher": publisher,
        "authority": authority,
        **captured,
        "verified_at": verified_at(store, head),
        "outcome": outcome,
    }
