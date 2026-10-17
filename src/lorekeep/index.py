"""The Index: `sources.db`, derived from the Store's files.

Ticket 08 builds it and answers lookups from it; ticket 14 fills the commit notification. Until
then the Store module's lookup falls back to its scan and a commit changes no Index.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lorekeep.store import AliasRow, CheckRow, TagRow, VersionInfo

INDEX_FILE = "sources.db"


def lookup(store: Path, url: str) -> VersionInfo | None:
    """The latest Version of `url` from a current Index; `None` when the Index cannot answer.

    Takes no lock and never rebuilds (ticket 08 fills this in).
    """
    return None


def notify(
    store: Path,
    *,
    version: Path | None,
    tags: Sequence[TagRow],
    checks: Sequence[CheckRow],
    aliases: Sequence[AliasRow],
) -> None:
    """Tell the Index what a commit wrote; called under the Store lock (ticket 14 fills this in)."""
