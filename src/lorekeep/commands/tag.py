"""`tag add <tag> <url>` and `tag add <tag> --prefix <url-prefix>`: tag stored Sources."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from lorekeep import index
from lorekeep.commands.add import now
from lorekeep.store import TagRow, commit, latest

if TYPE_CHECKING:
    from lorekeep.cli import Context


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def run(args: argparse.Namespace, ctx: Context) -> int:
    if (args.url is None) == (args.prefix is None):
        print("lorekeep: error: tag add takes a url or --prefix, not both", file=sys.stderr)
        return 2
    index.report(index.ensure(ctx.store))
    if args.prefix is not None:
        urls = index.source_urls(ctx.store, args.prefix)
        if not urls:
            print(f"lorekeep: error: no Source's url starts with {args.prefix}", file=sys.stderr)
            return 1
    else:
        found = latest(ctx.store, args.url, ctx.project.hosts)
        if found is None:
            print(f"lorekeep: error: no Source has the url {args.url}", file=sys.stderr)
            return 1
        urls = [found.url]
    present = index.tagged_urls(ctx.store, args.tag)
    new = [url for url in urls if url not in present]
    added_at = now()
    commit(ctx.store, tags=[TagRow(url=url, tag=args.tag, added_at=added_at) for url in new])
    for url in new:
        print(f"tagged {url}")
    print(
        f"Tagged {_plural(len(new), 'Source')} {args.tag}; "
        f"{len(urls) - len(new)} already carried it"
    )
    return 0
