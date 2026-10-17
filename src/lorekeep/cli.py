"""The command layer: one parser and one `run`, which the console script and the tests call."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lorekeep.commands import add as add_command
from lorekeep.commands import backup as backup_command
from lorekeep.commands import get as get_command
from lorekeep.commands import index as index_command
from lorekeep.commands import search as search_command
from lorekeep.edges import Edges
from lorekeep.project import AUTHORITIES, Project, ProjectError, load_project


class UsageError(Exception):
    """A setting the command needs is missing or wrong; the message is one line."""


class _Once(argparse.Action):
    """Store a flag that may be given at most once (`--tag` on `get` and `add`)."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        if getattr(namespace, self.dest) is not None:
            parser.error(f"{option_string} may be given once")
        setattr(namespace, self.dest, values)


def _store_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--store", metavar="DIR", help="the Store folder (default: $LOREKEEP_STORE)"
    )


def _json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print one JSON object")


def _single_tag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tag",
        action=_Once,
        metavar="TAG",
        help="the Run's Tag, exactly one (default: $LOREKEEP_TAG)",
    )


def _scope_tags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tag",
        action="append",
        metavar="TAG",
        help="limit the scope to this Tag; repeatable (default: $LOREKEEP_TAG, else everything)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lorekeep",
        description="Keep the Sources a Project's Runs read, with their Provenance, in one Store.",
    )
    commands = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    def command(name: str, help_text: str) -> argparse.ArgumentParser:
        return commands.add_parser(name, help=help_text, description=help_text)

    get = command("get", "store a Version of a page and print its path")
    get.add_argument("url", help="the page's address (or its Twin's)")
    _single_tag(get)
    age = get.add_mutually_exclusive_group()
    age.add_argument(
        "--max-age",
        type=int,
        metavar="DAYS",
        help="recheck a Version older than this (default: freshness_days)",
    )
    age.add_argument("--fresh", action="store_true", help="ask the publisher now (--max-age 0)")
    _json_flag(get)
    _store_flag(get)

    add = command("add", "store a file the owner provides as a Version")
    add.add_argument("file", help="a Markdown or text file")
    add.add_argument("--title", required=True, help="the Source's title; its slug names it")
    add.add_argument("--publisher", help="who produced it (default: owner)")
    add.add_argument("--authority", choices=AUTHORITIES, help="(default: generated)")
    add.add_argument("--fetched-at", metavar="WHEN", help="ISO 8601 time (default: file's mtime)")
    _single_tag(add)
    _json_flag(add)
    _store_flag(add)

    search = command("search", "search the Sections of the Store's latest Versions")
    search.add_argument("query", help="words to search for, or a string with --exact")
    _scope_tags(search)
    search.add_argument("--all", action="store_true", help="search every Tag")
    search.add_argument("--publisher", help="only Sources of this publisher")
    search.add_argument("--authority", choices=AUTHORITIES, help="only Sources of this authority")
    search.add_argument("--exact", action="store_true", help="match the text as written")
    search.add_argument("--limit", type=int, default=5, metavar="N", help="results (default: 5)")
    _json_flag(search)
    _store_flag(search)

    index = command("index", "rebuild the Index from the Store's files")
    _store_flag(index)

    recheck = command("recheck", "ask publishers whether their Sources changed")
    _scope_tags(recheck)
    recheck.add_argument("--publisher", help="only Sources of this publisher")
    recheck.add_argument("--prefix", metavar="URL", help="only Sources whose url starts so")
    recheck.add_argument(
        "--citations", action="store_true", help="list works whose cited Sources changed"
    )
    recheck.add_argument("--dry-run", action="store_true", help="list what would be asked")
    _store_flag(recheck)

    backup = command("backup", "copy the Store to the Project's bucket")
    backup.add_argument("--dry-run", action="store_true", help="show what would be copied")
    _store_flag(backup)

    restore = command("restore", "fetch one object back from the bucket")
    restore.add_argument("name", help="the object's name in the Store")
    restore.add_argument("--generation", metavar="N", help="an older generation of the object")
    _store_flag(restore)

    tag = command("tag", "add a Tag to stored Sources")
    tag_commands = tag.add_subparsers(dest="tag_command", metavar="<tag command>", required=True)
    tag_add = tag_commands.add_parser(
        "add", help="tag one Source, or every Source under a prefix", description="tag Sources"
    )
    tag_add.add_argument("tag", help="the Tag to add")
    tag_add.add_argument("url", nargs="?", help="the Source's url")
    tag_add.add_argument("--prefix", metavar="URL", help="every Source whose url starts so")
    _store_flag(tag_add)

    status = command("status", "summarise the Store")
    _json_flag(status)
    _store_flag(status)

    skill = command("skill", "print or install the lorekeep skill")
    skill.add_argument("--install", metavar="REPO", help="copy the skill into REPO/.agents/skills/")
    skill.add_argument("--force", action="store_true", help="replace an installed copy")

    return parser


@dataclass(frozen=True)
class Context:
    """What every command receives: its Store, the Project's settings, the Run's Tag, the edges."""

    store: Path
    project: Project
    tag: str | None
    edges: Edges


def resolve_store(args: argparse.Namespace, env: Mapping[str, str]) -> Path:
    value = args.store or env.get("LOREKEEP_STORE")
    if not value:
        raise UsageError("no Store: set LOREKEEP_STORE or pass --store")
    store = Path(value).expanduser()
    if not store.is_dir():
        raise UsageError(f"the Store {store} does not exist (lorekeep never creates it)")
    return store


def resolve_tag(args: argparse.Namespace, env: Mapping[str, str]) -> str:
    value = args.tag or env.get("LOREKEEP_TAG")
    if not value:
        raise UsageError(f"{args.command} needs the Run's Tag: set LOREKEEP_TAG or pass --tag")
    return value


def cmd_status(args: argparse.Namespace, ctx: Context) -> int:
    versions = sum(1 for _ in ctx.store.glob("*.md"))
    print(f"Store: {ctx.store}")
    print(f"{versions} Version{'' if versions == 1 else 's'}")
    print(f"Bucket: {ctx.project.bucket or 'none'}")
    print(f"Freshness window: {ctx.project.freshness_days} days")
    print(f"Host rules ({len(ctx.project.hosts)}):")
    for rule in ctx.project.hosts:
        words = [rule.prefix, rule.publisher, rule.authority]
        words += [f"twin={rule.twin}"] if rule.twin else []
        words += [f"page_suffix={rule.page_suffix}"] if rule.page_suffix else []
        words += ["browser"] if rule.browser else []
        words += [f"cut={','.join(rule.cut)}"] if rule.cut else []
        words += ["(lorekeep.toml)"] if rule.source == "lorekeep.toml" else []
        print("  " + "  ".join(words))
    return 0


def _not_yet(args: argparse.Namespace, ctx: Context) -> int:
    print(f"lorekeep {args.command}: not implemented yet", file=sys.stderr)
    return 1


HANDLERS: dict[str, Callable[[argparse.Namespace, Context], int]] = {
    "get": get_command.run,
    "add": add_command.run,
    "search": search_command.run,
    "index": index_command.run,
    "recheck": _not_yet,
    "backup": backup_command.run_backup,
    "restore": backup_command.run_restore,
    "tag": _not_yet,
    "status": cmd_status,
}

NEEDS_TAG = {"get", "add"}


def run(
    argv: Sequence[str], *, env: Mapping[str, str] | None = None, edges: Edges | None = None
) -> int:
    """Run one command; return its exit code. Output goes to `sys.stdout` and `sys.stderr`."""
    env = os.environ if env is None else env
    try:
        args = build_parser().parse_args(list(argv))
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 1
    if args.command == "skill":
        print("lorekeep skill: not implemented yet", file=sys.stderr)
        return 1
    try:
        store = resolve_store(args, env)
        if args.command in NEEDS_TAG:
            tag = resolve_tag(args, env)
        else:
            # A scoped command's default scope is the Run's Tag, when the Run has one.
            tag = env.get("LOREKEEP_TAG") or None
        project = load_project(store)
    except (UsageError, ProjectError) as error:
        print(f"lorekeep: error: {error}", file=sys.stderr)
        return 2
    ctx = Context(store=store, project=project, tag=tag, edges=edges or Edges.production())
    return HANDLERS[args.command](args, ctx)


def main() -> int:
    return run(sys.argv[1:], env=os.environ)
