"""`get <url>`: return the path of a Version of the page, fetching it through the cascade when
the Store has none."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from lorekeep import cascade, recheck
from lorekeep.commands import version_json
from lorekeep.http import make_client
from lorekeep.provenance import build as provenance
from lorekeep.provenance import now
from lorekeep.store import AliasRow, NewVersion, TagRow, VersionInfo, commit, latest
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
        return return_stored(args, ctx, stored)

    with make_client(ctx.edges.transport) as client:
        outcome = cascade.run_cascade(
            cascade.Request(url=args.url, rule=asked.rule, client=client, fetcher=ctx.edges.fetcher)
        )
    if not isinstance(outcome, cascade.Fetched):
        if outcome[-1].final:
            print(f"lorekeep: error: {outcome[-1].reason}", file=sys.stderr)
            return 1
        reasons = "; ".join(fallthrough.reason for fallthrough in outcome)
        print(f"lorekeep: error: nothing stored for {args.url}: {reasons}", file=sys.stderr)
        return 1
    for warning in outcome.warnings:
        print(f"lorekeep: warning: {warning}", file=sys.stderr)

    url = normalise(outcome.final_url, rules)
    found = trust(url, rules)
    if found.warning and found.warning != asked.warning:
        print(found.warning, file=sys.stderr)
    head = provenance(outcome, url, found.publisher, found.authority)
    version = NewVersion(
        frontmatter=head,
        body=outcome.markdown,
        original=outcome.original,
        original_ext=outcome.original_ext,
    )
    alias = normalise(args.url, rules)
    added_at = now()
    tags = [TagRow(url=url, tag=ctx.tag, added_at=added_at)]
    aliases = [AliasRow(alias=alias, url=url, added_at=added_at)] if alias != url else []
    # The address was new, but the Source may not be: a page reached through an alias not yet
    # known, or a canonical address. Then this fetch is a Recheck of its latest Version.
    current = latest(ctx.store, url, rules)
    if current is not None:
        answer = recheck.compare(ctx.store, current, version, tags=tags, aliases=aliases)
        return report(args, ctx, answer.path, answer.result)
    path = commit(ctx.store, version, tags=tags, aliases=aliases)
    assert path is not None
    return report(args, ctx, path, "stored")


def return_stored(args: argparse.Namespace, ctx: Context, stored: VersionInfo) -> int:
    """A stored Version: returned as is inside the freshness window, rechecked outside it."""
    assert ctx.tag is not None
    tag = TagRow(url=stored.url, tag=ctx.tag, added_at=now())
    window = 0 if args.fresh else ctx.project.freshness_days
    if args.max_age is not None:
        window = args.max_age
    match recheck.plan(ctx.store, stored, window_days=window):
        case recheck.Fresh(path):
            commit(ctx.store, tags=[tag])
            return report(args, ctx, path, "fresh")
        case recheck.Skipped(path, reason):
            print(f"lorekeep: warning: {reason}; returning the stored Version", file=sys.stderr)
            commit(ctx.store, tags=[tag])
            return report(args, ctx, path, "skipped")
        case recheck.Ask():
            with make_client(ctx.edges.transport) as client:
                answer = recheck.perform(ctx.store, stored, client, ctx.project.hosts, tags=[tag])
            if answer.warning:
                print(f"lorekeep: warning: {answer.warning}", file=sys.stderr)
            return report(args, ctx, answer.path, answer.result)


def report(args: argparse.Namespace, ctx: Context, path: Path, outcome: str) -> int:
    """The path on the last line, or one JSON object with `--json`, read from the file itself."""
    if not args.json:
        print(path)
        return 0
    print(json.dumps(version_json(ctx.store, path, outcome)))
    return 0
