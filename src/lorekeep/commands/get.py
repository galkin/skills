"""`get <url>`: return the path of a Version of the page, fetching it through the cascade when
the Store has none."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lorekeep import cascade, recheck
from lorekeep.http import make_client
from lorekeep.provenance import build as provenance
from lorekeep.provenance import now
from lorekeep.store import (
    AliasRow,
    NewVersion,
    RecheckRow,
    TagRow,
    VersionInfo,
    commit,
    latest,
    read_head,
    read_rows,
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
        return return_stored(args, ctx, stored)

    with make_client(ctx.edges.transport) as client:
        outcome = cascade.run_cascade(
            cascade.Request(url=args.url, rule=asked.rule, client=client, fetcher=ctx.edges.fetcher)
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
    alias = normalise(args.url, rules)
    added_at = now()
    # The address was new, but the Source may not be: a page reached through an alias not yet
    # known, or a canonical address. Then this fetch is a Recheck of its latest Version and is
    # recorded as one, so the lookup names the Version that is current now.
    current = latest(ctx.store, url, rules)
    if current is None:
        result = "stored"
        checks: list[RecheckRow] = []
    else:
        result = "unchanged" if current.sha256 == head["sha256"] else "changed"
        checks = [RecheckRow(url, added_at, result, "200", str(head["sha256"]))]
    path = commit(
        ctx.store,
        NewVersion(
            frontmatter=head,
            body=outcome.markdown,
            original=outcome.original,
            original_ext=outcome.original_ext,
        ),
        tags=[TagRow(url=url, tag=ctx.tag, added_at=added_at)],
        checks=checks,
        aliases=[AliasRow(alias=alias, url=url, added_at=added_at)] if alias != url else [],
    )
    assert path is not None
    return report(args, ctx, path, result)


def return_stored(args: argparse.Namespace, ctx: Context, stored: VersionInfo) -> int:
    """A stored Version: returned as is inside the freshness window, rechecked outside it."""
    assert ctx.tag is not None
    tag = TagRow(url=stored.url, tag=ctx.tag, added_at=now())
    window = 0 if args.fresh else ctx.project.freshness_days
    if args.max_age is not None:
        window = args.max_age
    if recheck.is_fresh(stored, read_rows(ctx.store, RecheckRow), window):
        commit(ctx.store, tags=[tag])
        return report(args, ctx, stored.path, "fresh")
    skipped = recheck.skipped_reason(stored)
    if skipped is not None:
        print(f"lorekeep: warning: {skipped}; returning the stored Version", file=sys.stderr)
        commit(ctx.store, tags=[tag])
        return report(args, ctx, stored.path, "skipped")
    with make_client(ctx.edges.transport) as client:
        asked = recheck.perform(ctx.store, stored, client, ctx.project.hosts, tags=[tag])
    if asked.warning:
        print(f"lorekeep: warning: {asked.warning}", file=sys.stderr)
    return report(args, ctx, asked.path, asked.result)


def report(args: argparse.Namespace, ctx: Context, path: Path, outcome: str) -> int:
    """The path on the last line, or one JSON object with `--json`, read from the file itself."""
    if not args.json:
        print(path)
        return 0
    head: dict[str, Any] = read_head(path)
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
                "verified_at": recheck.verified_at(ctx.store, head),
                "outcome": outcome,
            }
        )
    )
    return 0
