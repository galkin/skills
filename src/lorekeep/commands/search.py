"""`search <query>`: ranked Sections of the latest Versions in the Run's scope."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from lorekeep import index
from lorekeep.commands import scope_tags
from lorekeep.stopwords import content_words

if TYPE_CHECKING:
    from lorekeep.cli import Context


TOP = "(top)"
"""The heading path printed for text before a Version's first heading."""

RELAXED = "lorekeep: note: no Section has every word; these have most of them"
"""Printed on stderr before the results of a plain query no Section matched whole."""


def run(args: argparse.Namespace, ctx: Context) -> int:
    if args.query is None or not args.query.strip():
        print("lorekeep: error: the search query is empty", file=sys.stderr)
        return 2
    scope = index.Scope(
        tags=scope_tags(args.tag, ctx.tag, everything=args.all),
        publisher=args.publisher,
        authority=args.authority,
    )
    with index.ensured(ctx.store, ctx.project) as reader:
        hits, other = reader.search(args.query, scope, limit=args.limit, exact=args.exact)
        relaxed = False
        words = content_words(args.query)
        if not hits and not args.exact and words and words != args.query.split():
            some, some_other = reader.search(
                " ".join(words), scope, limit=args.limit, exact=False, any_word=True
            )
            if some:
                hits, other, relaxed = some, some_other, True
    if relaxed:
        print(RELAXED, file=sys.stderr)
    if args.json:
        results = [
            {
                "file": str(ctx.store / hit.file),
                "line": hit.line,
                "heading_line": hit.heading_line,
                "heading": hit.heading,
                "snippet": hit.snippet,
                "url": hit.url,
                "tag": hit.tags,
            }
            for hit in hits
        ]
        found = {"results": results, "other_tags": other or 0} | (
            {"relaxed": True} if relaxed else {}
        )
        print(json.dumps(found, ensure_ascii=False))
        return 0
    for hit in hits:
        print(f"{ctx.store / hit.file}:{hit.line} | {hit.heading or TOP} | {hit.snippet}")
    if not hits:
        print("no matches")
    if other:
        print(f"+{other} matches under other tags (--all)")
    return 0
