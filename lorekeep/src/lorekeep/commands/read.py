"""`read`: build the Readings that are missing or stale, under a prefix or in the whole Store."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from lorekeep import readings
from lorekeep.commands import plural
from lorekeep.store import OWNER_SCHEME, scan
from lorekeep.urls import under

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    built = current = 0
    for info in scan(ctx.store):
        if info.url.startswith(OWNER_SCHEME):
            continue
        if args.prefix and not under(info.url, args.prefix):
            continue
        reading = readings.ensure(ctx.store, info.path, ctx.project.readings, force=args.force)
        if reading.path is None or reading.built:
            for warning in reading.warnings:
                print(f"lorekeep: warning: {info.url}: {warning}", file=sys.stderr)
        if reading.built:
            built += 1
        elif reading.path is not None:
            current += 1
    print(f"Built {plural(built, 'Reading')}, {current} current")
    return 0
