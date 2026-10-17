"""`status`: the shape of a Store, read from its Index (built first when missing or stale)."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from lorekeep import index
from lorekeep.commands import plural

if TYPE_CHECKING:
    from lorekeep.cli import Context


def size_on_disk(store: Path) -> int:
    """The bytes of every file in the Store's flat folder, the Index included."""
    return sum(path.stat().st_size for path in store.iterdir() if path.is_file())


def run(args: argparse.Namespace, ctx: Context) -> int:
    with index.ensured(ctx.store, ctx.project.hosts) as reader:
        found = reader.summary()
    size = size_on_disk(ctx.store)
    if args.json:
        print(json.dumps({**asdict(found), "bytes": size}, ensure_ascii=False))
        return 0
    print(f"Store: {ctx.store}")
    print(f"{plural(found.versions, 'Version')} of {plural(found.sources, 'Source')}")
    tags = ", ".join(f"{tag} {count}" for tag, count in found.tags.items())
    print(f"Tags: {tags or 'none'}")
    print(f"Oldest fetched_at: {found.oldest_fetched_at or 'none'}")
    print(f"Newest fetched_at: {found.newest_fetched_at or 'none'}")
    checks = ", ".join(f"{count} {result}" for result, count in found.checks.items())
    print(f"Rechecks: {checks}")
    print(f"Unknown hosts: {', '.join(found.unknown_hosts) or 'none'}")
    print(f"Size on disk: {size} bytes")
    print(f"Bucket: {ctx.project.bucket or 'none'}")
    print(f"Freshness window: {ctx.project.freshness_days} days")
    if not args.rules:
        return 0
    print(f"Host rules ({len(ctx.project.hosts)}):")
    for rule in ctx.project.hosts:
        words = [rule.prefix, rule.publisher, rule.authority]
        mark = " (inherited)" if rule.inherited else ""
        words += [f"twin={rule.twin}{mark}"] if rule.twin else []
        words += [f"page_suffix={rule.page_suffix}{mark}"] if rule.page_suffix else []
        words += ["browser"] if rule.browser else []
        words += [f"cut={','.join(rule.cut)}"] if rule.cut else []
        words += ["(lorekeep.toml)"] if rule.source == "lorekeep.toml" else []
        print("  " + "  ".join(words))
    return 0
