"""`tag add <tag> <url>` and `tag add <tag> --prefix <url-prefix>`: tag stored Sources.

The Sources are found the way a lookup finds them (a current Index, else the Store's files) and
`tags.csv` is read directly, so the only lock this command takes is its commit's. A withdrawn
Source is never tagged: one asked by url is named on stderr, those under a prefix are left out.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from lorekeep.commands import plural
from lorekeep.provenance import now
from lorekeep.store import TagRow, commit, latest, read_rows, source_urls, withdrawn

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    if (args.url is None) == (args.prefix is None):
        print("lorekeep: error: tag add takes a url or --prefix, not both", file=sys.stderr)
        return 2
    out = withdrawn(ctx.store)
    if args.prefix is not None:
        urls = [url for url in source_urls(ctx.store, args.prefix) if url not in out]
        if not urls:
            print(f"lorekeep: error: no Source's url is under {args.prefix}", file=sys.stderr)
            return 1
    else:
        found = latest(ctx.store, args.url, ctx.project.hosts)
        if found is None:
            print(f"lorekeep: error: no Source has the url {args.url}", file=sys.stderr)
            return 1
        if found.url in out:
            row = out[found.url]
            print(
                f"lorekeep: warning: {found.url} was withdrawn by the owner at "
                f"{row.recorded_at}: {row.reason}; not tagged",
                file=sys.stderr,
            )
        urls = [found.url] if found.url not in out else []
    present = {row.url for row in read_rows(ctx.store, TagRow) if row.tag == args.tag}
    new = [url for url in urls if url not in present]
    added_at = now()
    commit(ctx.store, tags=[TagRow(url=url, tag=args.tag, added_at=added_at) for url in new])
    for url in new:
        print(f"tagged {url}")
    print(
        f"Tagged {plural(len(new), 'Source')} {args.tag}; {len(urls) - len(new)} already carried it"
    )
    return 0
