"""`recheck`: ask the publisher of every Source in scope whether it changed, and with
`--citations` list the works whose cited Sources changed since they were written."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from lorekeep import index, readings, recheck
from lorekeep.commands import plural, scope_tags
from lorekeep.http import make_client
from lorekeep.store import RECHECK_RESULTS

if TYPE_CHECKING:
    from lorekeep.cli import Context

RESULTS: tuple[str, ...] = (*RECHECK_RESULTS, "skipped")


def run(args: argparse.Namespace, ctx: Context) -> int:
    with index.ensured(ctx.store, ctx.project) as reader:
        if args.citations:
            return report_citations(reader)
        scope = index.Scope(tags=scope_tags(args.tag, ctx.tag), publisher=args.publisher)
        versions = reader.latest_in_scope(scope, args.prefix)
    counts = dict.fromkeys(RESULTS, 0)
    plans = [(stored, recheck.plan(ctx.store, stored, window_days=0)) for stored in versions]
    if args.dry_run:
        asked = 0
        for stored, planned in plans:
            if isinstance(planned, recheck.Skipped):
                counts["skipped"] += 1
                print(f"skipped {stored.url}: {planned.reason}")
            elif isinstance(planned, recheck.Ask):
                asked += 1
                print(f"would ask {planned.address}")
        print(f"Would ask {plural(asked, 'Source')}; {counts['skipped']} skipped")
        return 0
    with make_client(ctx.edges.transport) as client:
        for stored, planned in plans:
            if not isinstance(planned, recheck.Ask):
                counts["skipped"] += 1
                print(f"skipped {stored.url}")
                continue
            answer = recheck.perform(ctx.store, stored, client, ctx.project.hosts)
            counts[answer.result] += 1
            if answer.warning:
                print(f"lorekeep: warning: {answer.warning}", file=sys.stderr)
            if answer.result == "changed":
                # The new Version's Reading now, so the Index never searches its raw text.
                reading = readings.ensure(ctx.store, answer.path, ctx.project.readings)
                for warning in reading.warnings:
                    print(f"lorekeep: warning: {stored.url}: {warning}", file=sys.stderr)
            print(f"{answer.result} {stored.url}")
    summary = ", ".join(f"{counts[result]} {result}" for result in RESULTS)
    print(f"Rechecked {plural(len(versions), 'Source')}: {summary}")
    return 0


def report_citations(reader: index.Reader) -> int:
    """A pure report: no request, no Tag, nothing written."""
    found, warnings = reader.revisits()
    for warning in warnings:
        print(warning, file=sys.stderr)
    for revisit in found:
        old, new = revisit.old_sha256[:8], revisit.new_sha256[:8]
        print(f"{revisit.work_id}, {revisit.url}, {old} → {new}")
    return 0
