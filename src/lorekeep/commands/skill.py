"""`skill`: print the lorekeep skill shipped in the package, or install its folder into a repo.

Installing writes only under `<repo>/.agents/skills/lorekeep/`; a repository's skill lock is left
for the owner to update, because only the tool that keeps it knows how it hashes a skill.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

SKILL_PATH = Path(".agents") / "skills" / "lorekeep"


def skill_folder() -> Traversable:
    """The skill folder inside the installed package: `SKILL.md` and its reference files."""
    return resources.files("lorekeep") / "skill"


def run(args: argparse.Namespace) -> int:
    if args.force and not args.install:
        print("lorekeep: error: --force only applies to --install", file=sys.stderr)
        return 2
    if args.install:
        return install(Path(args.install).expanduser(), force=args.force)
    print((skill_folder() / "SKILL.md").read_text(encoding="utf-8"), end="")
    return 0


def install(repo: Path, *, force: bool) -> int:
    if not repo.is_dir():
        print(f"lorekeep: error: the repository {repo} does not exist", file=sys.stderr)
        return 2
    target = repo / SKILL_PATH
    if target.exists() and not force:
        print(f"lorekeep: error: {target} exists; pass --force to replace it", file=sys.stderr)
        return 1
    # Copy beside the target first, so a failed copy never leaves half a skill installed.
    staging = target.with_name(f"{target.name}.tmp-{os.getpid()}")
    with resources.as_file(skill_folder()) as source:
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns("__pycache__"))
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    print(f"Installed the lorekeep skill in {target}")
    print(_lock_reminder(repo))
    return 0


def _lock_reminder(repo: Path) -> str:
    locks = sorted(path.name for path in repo.glob("*skill*lock*") if path.is_file())
    if locks:
        return (
            f"Reminder: {', '.join(locks)} is this repository's skill lock; "
            f"record the new hash of {SKILL_PATH} there."
        )
    return (
        "Reminder: if this repository keeps a skill lock, "
        f"record the new hash of {SKILL_PATH} there."
    )
