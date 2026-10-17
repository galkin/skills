"""`index`: rebuild `sources.db` from the Store's files."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from lorekeep import index
from lorekeep.commands import plural
from lorekeep.store import INDEX_FILE

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    counts = index.rebuild(ctx.store, ctx.project.hosts)
    index.report(counts, note=False)
    print(
        f"Indexed {plural(counts.versions, 'Version')}, {plural(counts.sections, 'Section')}, "
        f"{plural(counts.tags, 'Tag row')}, {plural(counts.checks, 'Recheck')}, "
        f"{plural(counts.aliases, 'alias', 'aliases')}, {plural(counts.citations, 'Citation')} "
        f"into {ctx.store / INDEX_FILE}"
    )
    return 0
