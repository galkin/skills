"""`backup` and `restore`: the Store to and from the Project's bucket through `gcloud storage`.

Nothing here deletes, locally or in the bucket.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from lorekeep import package
from lorekeep.edges import CommandRunner
from lorekeep.project import PROJECT_FILE
from lorekeep.readings import CACHE_DIR
from lorekeep.store import INDEX_FILE, LOCK_FILE, WATCHED_FILES

if TYPE_CHECKING:
    from lorekeep.cli import Context


GCLOUD = ("gcloud", "storage")

# Every upload is gzipped on the wire only: the Store's HTML and Markdown shrink about fivefold, the
# upload is what a backup waits on, and the objects in the bucket stay byte for byte the files.
GZIP_IN_FLIGHT = "--gzip-in-flight-all"

# The files that grow, in the order they are copied: the bucket's versioning keeps their history.
GROWING_FILES = (*WATCHED_FILES, package.PACKAGE_FILE, PROJECT_FILE)

# What `rsync` leaves out (a regular expression over a path in the Store): the growing files, which
# `cp` copies, the Index with its journals, the lock file, a temporary file still being written,
# and everything under `.cache/` (the Readings), which is rebuilt from the Versions.
EXCLUDE = (
    "^("
    + "|".join(re.escape(name) for name in GROWING_FILES)
    + f"|{re.escape(INDEX_FILE)}(-wal|-shm)?"
    + f"|{re.escape(LOCK_FILE)}"
    + r"|.*\.tmp-[0-9]+"
    + f"|{re.escape(CACHE_DIR)}/.*"
    + ")$"
)


def _bucket(ctx: Context) -> str | None:
    if ctx.project.bucket is None:
        print(
            f"lorekeep: error: no bucket: set `bucket` in {ctx.store / PROJECT_FILE}",
            file=sys.stderr,
        )
    return ctx.project.bucket


def _call(runner: CommandRunner, argv: Sequence[str]) -> bool:
    """Run one `gcloud` command, pass on what it printed, and say whether it succeeded."""
    try:
        done = runner.run(argv)
    except OSError as error:
        print(f"lorekeep: error: could not run {argv[0]}: {error}", file=sys.stderr)
        return False
    if done.stdout:
        print(done.stdout, end="")
    if done.stderr:
        print(done.stderr, end="", file=sys.stderr)
    if done.returncode != 0:
        print(
            f"lorekeep: error: {' '.join(argv[:3])} exited with {done.returncode}",
            file=sys.stderr,
        )
    return done.returncode == 0


def run_backup(args: argparse.Namespace, ctx: Context) -> int:
    bucket = _bucket(ctx)
    if bucket is None:
        return 2
    package.regenerate(ctx.store)
    rsync = [*GCLOUD, "rsync", "--recursive", "--no-clobber", GZIP_IN_FLIGHT]
    rsync += [f"--exclude={EXCLUDE}"]
    rsync += ["--dry-run"] if args.dry_run else []
    if not _call(ctx.edges.runner, [*rsync, str(ctx.store), f"gs://{bucket}"]):
        return 1
    growing = [str(ctx.store / name) for name in GROWING_FILES if (ctx.store / name).is_file()]
    if args.dry_run:
        # `gcloud storage cp` has no dry run: say what it would copy instead of running it.
        for path in growing:
            print(f"Would copy {path} to gs://{bucket}/ (replacing; the bucket keeps the old one)")
        return 0
    if not _call(ctx.edges.runner, [*GCLOUD, "cp", GZIP_IN_FLIGHT, *growing, f"gs://{bucket}/"]):
        return 1
    return 0


def run_restore(args: argparse.Namespace, ctx: Context) -> int:
    name: str = args.name
    if "/" in name or name in {"", ".", ".."}:
        print(f"lorekeep: error: {name!r} is not a file name in the Store", file=sys.stderr)
        return 2
    if args.generation is not None and not args.generation.isdigit():
        print(f"lorekeep: error: --generation {args.generation} is not a number", file=sys.stderr)
        return 2
    target = ctx.store / name
    if target.exists():
        print(f"lorekeep: error: {target} exists; restore never overwrites", file=sys.stderr)
        return 1
    bucket = _bucket(ctx)
    if bucket is None:
        return 2
    # `#N` names one generation of an object in a versioned bucket (Google's documented form).
    source = f"gs://{bucket}/{name}" + (f"#{args.generation}" if args.generation else "")
    if not _call(ctx.edges.runner, [*GCLOUD, "cp", source, f"{ctx.store}/"]):
        return 1
    print(target)
    return 0
