"""`search <query>`: ranked Sections of the latest Versions in the Run's scope."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from lorekeep import index

if TYPE_CHECKING:
    from lorekeep.cli import Context


def scope_tags(args: argparse.Namespace, ctx: Context) -> list[str] | None:
    """`--all` → every Tag; `--tag` repeated; else the Run's Tag; with none, every Tag."""
    if args.all:
        return None
    if args.tag:
        return list(args.tag)
    return [ctx.tag] if ctx.tag else None


def run(args: argparse.Namespace, ctx: Context) -> int:
    if not args.query.strip():
        print("lorekeep: error: the search query is empty", file=sys.stderr)
        return 2
    index.ensure(ctx.store)
    scope = index.Scope(
        tags=scope_tags(args, ctx), publisher=args.publisher, authority=args.authority
    )
    hits, other = index.search(ctx.store, args.query, scope, limit=args.limit, exact=args.exact)
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
