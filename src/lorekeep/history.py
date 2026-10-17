"""The Latest Version rule: which of a Source's Versions answers for it, now or at a moment.

Among a Source's Versions the one its latest `checks.csv` row names is the Latest Version, and
the newest `fetched_at` when no row names a stored one (ADR 0007: a page served A, then B, then A
again has two files and A is latest). The rule is written here once; the Store's scan and the
Index's Citations call it, and the Index's SQL view `latest` is tested equal to it.
"""

from __future__ import annotations

from collections.abc import Sequence
from operator import itemgetter

type Stamped = tuple[str, str]
"""A timestamp (`YYYY-MM-DDTHH:MM:SSZ`, so text order is time order) and a `sha256`."""


def latest(
    versions: Sequence[Stamped], checks: Sequence[Stamped], as_of: str | None = None
) -> str | None:
    """The `sha256` of the Latest Version at `as_of` (now when `None`): the one named by the
    latest `checks.csv` row up to then whose `sha256` is a Version fetched by then, else the
    newest `fetched_at` up to then.

    `versions` are `(fetched_at, sha256)` in file-name order and `checks` are
    `(checked_at, sha256)` in `checks.csv` order: the later row wins a tie on `checked_at` (two
    Rechecks in one second append in order) and the first file a tie on `fetched_at`. `None`
    when no Version was fetched by `as_of`.
    """
    if as_of is not None:
        versions = [version for version in versions if version[0] <= as_of]
        checks = [check for check in checks if check[0] <= as_of]
    if not versions:
        return None
    stored = {sha256 for _, sha256 in versions}
    named = [check for check in checks if check[1]]
    if named:
        # `max` keeps the first of equals: over the reversed rows that is the later row.
        last = max(reversed(named), key=itemgetter(0))[1]
        if last in stored:
            return last
    return max(versions, key=itemgetter(0))[1]
