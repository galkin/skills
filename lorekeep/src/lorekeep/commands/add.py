"""`add <file> --title <t>`: a file the owner provides becomes a Version with `origin: owner`."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from lorekeep.commands import version_json
from lorekeep.provenance import TIME_FORMAT, now, parse_time
from lorekeep.store import OWNER_SCHEME, NewVersion, TagRow, commit, version_name

if TYPE_CHECKING:
    from lorekeep.cli import Context


def slug(title: str) -> str:
    """The title as a file-name-safe word: lower-case, runs of anything else as one `-`."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def run(args: argparse.Namespace, ctx: Context) -> int:
    file = Path(args.file)
    if not file.is_file():
        print(f"lorekeep: error: {file} is not a file", file=sys.stderr)
        return 2
    if args.fetched_at is not None:
        try:
            fetched_at = parse_time(args.fetched_at).strftime(TIME_FORMAT)
        except ValueError:
            print(
                f"lorekeep: error: --fetched-at {args.fetched_at} is not ISO 8601", file=sys.stderr
            )
            return 2
    else:
        fetched_at = datetime.fromtimestamp(file.stat().st_mtime, UTC).strftime(TIME_FORMAT)
    name = slug(args.title)
    if not name:
        print(
            "lorekeep: error: --title has no letters or digits to name the Source", file=sys.stderr
        )
        return 2
    body = file.read_bytes()
    assert ctx.tag is not None
    head = {
        "url": f"{OWNER_SCHEME}{name}",
        "fetched_at": fetched_at,
        "sha256": hashlib.sha256(body).hexdigest(),
        "publisher": args.publisher or "owner",
        "authority": args.authority or "generated",
        "converter": "owner",
        "title": args.title,
        "origin": "owner",
    }
    already = (ctx.store / version_name(head["url"], head["sha256"])).exists()
    path = commit(
        ctx.store,
        NewVersion(frontmatter=head, body=body),
        tags=[TagRow(url=head["url"], tag=ctx.tag, added_at=now())],
    )
    assert path is not None
    if args.json:
        # The file is what the Store has: an earlier `add` of the same text keeps its fields.
        outcome = "unchanged" if already else "stored"
        print(json.dumps(version_json(ctx.store, path, outcome, asked=args.file)))
    else:
        print(path)
    return 0
