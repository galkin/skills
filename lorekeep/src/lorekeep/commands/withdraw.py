"""`withdraw <url> --reason <text>` and `withdraw --undo <url> --reason <text>`: the owner takes a
Source stored by mistake out of every Run's view, or brings it back (ADR 0010).

The url resolves as `get` resolves it (normalised, Twin-reduced, through `aliases.csv`), and the
row names the Source, so every Version of it is withdrawn. A row is appended only when it changes
what holds: a second `withdraw`, or an `--undo` of a Source not withdrawn, writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from lorekeep.provenance import now
from lorekeep.store import UNDO, WITHDRAW, WithdrawalRow, commit, latest, withdrawn

if TYPE_CHECKING:
    from lorekeep.cli import Context


def run(args: argparse.Namespace, ctx: Context) -> int:
    reason = " ".join(args.reason.split())
    if not reason:
        print("lorekeep: error: --reason is empty", file=sys.stderr)
        return 2
    found = latest(ctx.store, args.url, ctx.project.hosts)
    if found is None:
        print(f"lorekeep: error: no Source has the url {args.url}", file=sys.stderr)
        return 2
    url = found.url
    held = withdrawn(ctx.store).get(url)
    if args.undo:
        if held is None:
            print(f"{url} is not withdrawn; nothing written")
            return 0
        commit(ctx.store, withdrawals=[WithdrawalRow(url, now(), UNDO, reason)])
        print(f"Brought back {url} (withdrawn at {held.recorded_at}: {held.reason})")
        return 0
    if held is not None:
        print(f"{url} was already withdrawn at {held.recorded_at}: {held.reason}; nothing written")
        return 0
    commit(ctx.store, withdrawals=[WithdrawalRow(url, now(), WITHDRAW, reason)])
    print(f"Withdrew {url}: {reason}")
    return 0
