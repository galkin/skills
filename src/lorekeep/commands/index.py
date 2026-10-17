"""`index`: rebuild `sources.db` from the Store's files."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from lorekeep import index

if TYPE_CHECKING:
    from lorekeep.cli import Context


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def run(args: argparse.Namespace, ctx: Context) -> int:
    counts = index.rebuild(ctx.store)
    index.report(counts)
    print(
        f"Indexed {_plural(counts.versions, 'Version')}, {_plural(counts.sections, 'Section')}, "
        f"{_plural(counts.tags, 'Tag row')}, {_plural(counts.checks, 'Recheck')}, "
        f"{_plural(counts.aliases, 'alias')}, {_plural(counts.citations, 'Citation')} "
        f"into {ctx.store / index.INDEX_FILE}"
    )
    return 0
