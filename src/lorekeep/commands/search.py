"""`search <query>`: ranked Sections of the latest Versions in the Run's scope."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from lorekeep import index
from lorekeep.commands import scope_tags

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    if not args.query.strip():
        print("lorekeep: error: the search query is empty", file=sys.stderr)
        return 2
    scope = index.Scope(
        tags=scope_tags(args.tag, ctx.tag, everything=args.all),
        publisher=args.publisher,
        authority=args.authority,
    )
    with index.ensured(ctx.store, ctx.project.hosts) as reader:
        hits, other = reader.search(args.query, scope, limit=args.limit, exact=args.exact)
    if args.json:
        results = [
            {
                "file": str(ctx.store / hit.file),
                "line": hit.line,
                "heading": hit.heading,
                "snippet": hit.snippet,
                "url": hit.url,
                "tag": hit.tags,
            }
            for hit in hits
        ]
        print(json.dumps({"results": results, "other_tags": other or 0}, ensure_ascii=False))
        return 0
    for hit in hits:
        print(f"{ctx.store / hit.file}:{hit.line} | {hit.heading} | {hit.snippet}")
    if other is not None:
        print(f"+{other} matches under other tags (--all)")
    return 0
