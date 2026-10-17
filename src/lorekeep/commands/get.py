"""`get <url>`: return the path of a Version of the page, fetching it through the cascade when
the Store has none."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lorekeep import cascade
from lorekeep.commands.add import now
from lorekeep.http import make_client
from lorekeep.store import (
    AliasRow,
    CheckRow,
    NewVersion,
    TagRow,
    commit,
    latest,
    read_head,
    read_rows,
    version_name,
)
from lorekeep.urls import normalise, trust

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    rules = ctx.project.hosts
    assert ctx.tag is not None
    asked = trust(args.url, rules)
    if asked.warning:
        print(asked.warning, file=sys.stderr)

    stored = latest(ctx.store, args.url, rules)
    if stored is not None:
        commit(ctx.store, tags=[TagRow(url=stored.url, tag=ctx.tag, added_at=now())])
        return report(args, ctx, stored.path, "fresh")

    with make_client(ctx.edges.transport) as client:
        outcome = cascade.run_cascade(
            cascade.Request(url=args.url, rule=asked.rule, client=client), cascade.STEPS
        )
    if not isinstance(outcome, cascade.Fetched):
        reasons = "; ".join(fallthrough.reason for fallthrough in outcome)
        print(f"lorekeep: error: nothing stored for {args.url}: {reasons}", file=sys.stderr)
        return 1

    url = normalise(outcome.final_url, rules)
    found = trust(url, rules)
    if found.warning and found.warning != asked.warning:
        print(found.warning, file=sys.stderr)
    head = provenance(outcome, url, found.publisher, found.authority)
    already = (ctx.store / version_name(url, str(head["sha256"]))).exists()
    alias = normalise(args.url, rules)
    added_at = now()
    path = commit(
        ctx.store,
        NewVersion(
            frontmatter=head,
            body=outcome.markdown,
            original=outcome.original,
            original_ext=outcome.original_ext,
        ),
        tags=[TagRow(url=url, tag=ctx.tag, added_at=added_at)],
        aliases=[AliasRow(alias=alias, url=url, added_at=added_at)] if alias != url else [],
    )
    assert path is not None
    return report(args, ctx, path, "unchanged" if already else "stored")


def provenance(fetched: cascade.Fetched, url: str, publisher: str, authority: str) -> dict:
    """The Version's frontmatter, in the order a reader expects; absent values are left out."""
    return {
        "url": url,
        "fetched_at": now(),
        "sha256": hashlib.sha256(fetched.markdown).hexdigest(),
        "publisher": publisher,
        "authority": authority,
        "converter": fetched.converter,
        "etag": fetched.etag,
        "last_modified": fetched.last_modified,
        "title": fetched.title,
        "modified": fetched.modified,
        "original": {
            "url": fetched.original_url,
            "mediatype": fetched.mediatype,
            "sha256": fetched.original_sha256,
            "stored": fetched.original is not None,
        },
        "origin": "web",
    }


def report(args: argparse.Namespace, ctx: Context, path: Path, outcome: str) -> int:
    """The path on the last line, or one JSON object with `--json`, read from the file itself."""
    if not args.json:
        print(path)
        return 0
    head: dict[str, Any] = read_head(path)
    unchanged = [
        row.checked_at
        for row in read_rows(ctx.store, CheckRow)
        if row.url == head["url"] and row.result == "unchanged"
    ]
    print(
        json.dumps(
            {
                "path": str(path),
                "url": head["url"],
                "sha256": head["sha256"],
                "fetched_at": head["fetched_at"],
                "converter": head["converter"],
                "publisher": head["publisher"],
                "authority": head["authority"],
                "verified_at": max(unchanged) if unchanged else head["fetched_at"],
                "outcome": outcome,
            }
        )
    )
    return 0
