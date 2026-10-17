"""Readings: the Markdown of a Version after the Project's reading rules, the file a Run reads.

A Reading is `.cache/readings/<stem>.md` beside the Store's Versions: frontmatter (`url`,
`version` the Version's file name, `sha256` of the Reading's body, `rules` the hash of the rules
applied, `title`, and `warnings` when the over-removal guard held a rule back), then the body. It
is built from its Version whenever it is missing or its `rules` hash is not the hash of the rules
that apply now, inside the Store lock, and never backed up: the Versions are the record.

A rule can only drop whole lines of the Version, cut a suffix from its first heading or insert a
heading line, so every other line of a Reading is byte-equal to a line of the Version. A rule
never removes a line inside a code fence (its fences included) or a pipe-table line (one that
starts with `|`): `drop_lines` passes over them, and a leading or trailing block that holds one
is not dropped at all. A Version no rule changes has no Reading, and a stale Reading of it is
removed.

Which rules apply to a Version: for each operation, the rule whose `prefix` is the longest the
Version's `host/path` starts with, else the first `engine` rule whose engine made the Version.
An engine is recognised from the Version itself:

- `fern` — a Twin (`md-twin`) with a line before its first heading starting
  `> For clean Markdown` (the llms.txt banner, worded two ways on `docs.nvidia.com`);
- `mintlify` — a Twin whose first line is `> ## Documentation Index`;
- `sphinx` — an HTML conversion (`trafilatura …`) whose stored Original loads
  `_static/documentation_options.js`, as every Sphinx theme does;
- `eur-lex` — an HTML conversion with the line `This document is an excerpt from the EUR-Lex
  website`;
- `pdf` — a PDF conversion (`markitdown …`).

The operations run in a fixed order — `drop_leading`, `drop_trailing`, `drop_lines`,
`strip_title_suffix`, `heading_before` — each on what the ones before left. A rule with `removes`
that would remove more than twice that share of the Version's lines is not applied to that
Version, and the Reading says so in `warnings`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lorekeep import frontmatter, sections
from lorekeep.project import OPERATIONS, ReadingRule
from lorekeep.store import OWNER_SCHEME, lock, parse_version, stem

READINGS_DIR = Path(".cache") / "readings"
READER = "1"
"""The meaning of the operations: part of every `rules` hash, so a change rebuilds every Reading."""

FERN_BANNER = "> For clean Markdown"
MINTLIFY_BANNER = "> ## Documentation Index"
EUR_LEX_MARKER = "This document is an excerpt from the EUR-Lex website"
SPHINX_MARKER = b"_static/documentation_options.js"


@dataclass(frozen=True)
class Reading:
    """What `ensure` found: the Reading's path (`None` when no rule changes the Version), whether
    it was built now, and the guard's warnings (`rule <name> removed N% (accepted at M%)`)."""

    path: Path | None
    built: bool
    warnings: tuple[str, ...] = ()


def reading_path(store: Path, version: Path) -> Path:
    """Where the Reading of the Version at `version` lives: `.cache/readings/<stem>.md`."""
    return store / READINGS_DIR / f"{stem(version.name)}.md"


def ensure(
    store: Path, version: Path, rules: Sequence[ReadingRule], *, force: bool = False
) -> Reading:
    """The Reading of the Version at `version`, built when missing or stale (always with
    `force`), inside the Store lock; never called with the lock held."""
    head, body = parse_version(version.read_bytes())
    target = reading_path(store, version)
    url = str(head["url"])
    applying = [] if url.startswith(OWNER_SCHEME) else rules_for(store, version, head, body, rules)
    digest = rules_hash(applying)
    if not force:
        current = _current(target, digest)
        if current is not None:
            return Reading(target, False, current)
    if not applying and not target.exists():
        return Reading(None, False)
    made = apply(head, body, applying)
    with lock(store):
        if not force:
            current = _current(target, digest)
            if current is not None:
                return Reading(target, False, current)
        if not made.touched:
            target.unlink(missing_ok=True)
            return Reading(None, False, made.warnings)
        fields: dict[str, Any] = {
            "url": url,
            "version": version.name,
            "sha256": hashlib.sha256(made.body).hexdigest(),
            "rules": digest,
            "title": made.title,
            "warnings": list(made.warnings),
        }
        _write(target, frontmatter.render(fields) + made.body)
    return Reading(target, True, made.warnings)


def rules_for(
    store: Path,
    version: Path,
    head: dict[str, Any],
    body: bytes,
    rules: Sequence[ReadingRule],
) -> list[ReadingRule]:
    """The rules that apply to a Version, one per operation at most, in the order they run."""
    parts = urlsplit(str(head["url"]))
    host_path = f"{(parts.hostname or '').lower()}{parts.path}"
    engines: dict[str, bool] = {}

    def made_by(engine: str) -> bool:
        if engine not in engines:
            engines[engine] = _made_by(engine, store, version, head, body)
        return engines[engine]

    chosen: list[ReadingRule] = []
    for operation in OPERATIONS:
        of_operation = [rule for rule in rules if rule.operation == operation]
        by_prefix = [
            rule
            for rule in of_operation
            if rule.prefix is not None and host_path.startswith(rule.prefix)
        ]
        rule = max(by_prefix, key=lambda rule: len(rule.prefix or ""), default=None)
        if rule is None:
            rule = next(
                (r for r in of_operation if r.engine is not None and made_by(r.engine)), None
            )
        if rule is not None:
            chosen.append(rule)
    return chosen


def _made_by(engine: str, store: Path, version: Path, head: dict[str, Any], body: bytes) -> bool:
    converter = str(head.get("converter", ""))
    text = body.decode("utf-8", errors="replace")
    if engine == "pdf":
        return converter.startswith("markitdown")
    if engine == "fern":
        if converter != "md-twin":
            return False
        for line in text.split("\n"):
            if sections.heading_text(line) is not None:
                return False
            if line.startswith(FERN_BANNER):
                return True
        return False
    if engine == "mintlify":
        return converter == "md-twin" and text.split("\n", 1)[0].rstrip() == MINTLIFY_BANNER
    if engine == "eur-lex":
        return converter.startswith("trafilatura") and any(
            line.strip() == EUR_LEX_MARKER for line in text.split("\n")
        )
    if engine == "sphinx":
        original = store / f"{stem(version.name)}.orig.html"
        return (
            converter.startswith("trafilatura")
            and original.is_file()
            and SPHINX_MARKER in original.read_bytes()
        )
    return False


def rules_hash(rules: Sequence[ReadingRule]) -> str:
    """The hash a Reading records as `rules`: of what the rules do, not where they were written."""
    described = [
        [rule.operation, rule.pattern, rule.prefix, rule.engine, rule.level, rule.removes]
        for rule in rules
    ]
    return hashlib.sha256(json.dumps([READER, described]).encode()).hexdigest()


@dataclass
class Made:
    """A Reading's body and title, whether any rule changed the Version, and the guard's
    warnings."""

    body: bytes
    title: str | None
    touched: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)


def apply(head: dict[str, Any], body: bytes, rules: Sequence[ReadingRule]) -> Made:
    """The rules applied to a Version's body and `title`, in the order of `rules_for`."""
    text = body.decode("utf-8", errors="surrogateescape")
    lines = _lines(text)
    bare = [line.removesuffix("\n") for line in lines]
    code = sections.code_lines(bare)
    protected = [
        fenced or line.lstrip().startswith("|") for line, fenced in zip(bare, code, strict=True)
    ]
    heading = [
        not fenced and sections.heading_text(line) is not None
        for line, fenced in zip(bare, code, strict=True)
    ]
    kept = list(range(len(lines)))
    inserted: dict[int, str] = {}
    edited: dict[int, str] = {}
    title = head.get("title")
    title = str(title) if title is not None else None
    warnings: list[str] = []

    for rule in rules:
        pattern = re.compile(rule.pattern)
        if rule.operation == "drop_leading":
            after = _drop_leading(kept, bare, heading, protected, pattern)
        elif rule.operation == "drop_trailing":
            after = _drop_trailing(kept, bare, heading, protected, pattern)
        elif rule.operation == "drop_lines":
            after = [n for n in kept if protected[n] or not pattern.search(bare[n])]
        elif rule.operation == "strip_title_suffix":
            first = next((n for n in kept if heading[n]), None)
            if first is not None:
                cut = _strip_suffix(bare[first], pattern)
                if cut is not None and sections.heading_text(cut):
                    edited[first] = cut + lines[first][len(bare[first]) :]
            if title is not None:
                title = _strip_suffix(title, pattern) or title
            continue
        else:
            assert rule.level is not None
            previous_is_heading = False
            for n in kept:
                if not bare[n].strip():
                    continue
                if (
                    not protected[n]
                    and not heading[n]
                    and not previous_is_heading
                    and pattern.search(bare[n])
                ):
                    inserted[n] = f"{'#' * rule.level} {bare[n].strip()}\n"
                previous_is_heading = heading[n]
            continue
        removed = len(kept) - len(after)
        share = 100 * removed / len(lines) if lines else 0.0
        if rule.removes is not None and share > 2 * rule.removes:
            warnings.append(
                f"rule {rule.name} removed {share:.0f}% (accepted at {rule.removes:g}%)"
            )
            continue
        kept = after

    out: list[str] = []
    for n in kept:
        if n in inserted:
            out.append(inserted[n])
        out.append(edited.get(n, lines[n]))
    touched = len(kept) != len(lines) or bool(inserted) or bool(edited)
    if title is None:
        found = (sections.heading_text(line.removesuffix("\n")) for line in out)
        title = next((text for text in found if text), None)
    return Made(
        body="".join(out).encode("utf-8", errors="surrogateescape"),
        title=title,
        touched=touched,
        warnings=tuple(warnings),
    )


def _lines(text: str) -> list[str]:
    """`text` as lines, each with its `\\n` (the last without one when the text has none)."""
    parts = text.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _drop_leading(
    kept: list[int],
    bare: list[str],
    heading: list[bool],
    protected: list[bool],
    pattern: re.Pattern[str],
) -> list[int]:
    """`kept` without its lines up to the last one before the first heading that matches, and the
    blank lines after them; unchanged when there is no heading, no match, or the block holds a
    fence or table line."""
    first = next((at for at, n in enumerate(kept) if heading[n]), None)
    if first is None:
        return kept
    last = next((at for at in range(first - 1, -1, -1) if pattern.search(bare[kept[at]])), None)
    if last is None:
        return kept
    end = last + 1
    while end < first and not bare[kept[end]].strip():
        end += 1
    if any(protected[n] for n in kept[:end]):
        return kept
    return kept[end:]


def _drop_trailing(
    kept: list[int],
    bare: list[str],
    heading: list[bool],
    protected: list[bool],
    pattern: re.Pattern[str],
) -> list[int]:
    """`kept` without its lines from the first one after the last heading that matches, and the
    blank lines before them; unchanged when there is no heading, no match, or the block holds a
    fence or table line."""
    last_heading = next((at for at in range(len(kept) - 1, -1, -1) if heading[kept[at]]), None)
    if last_heading is None:
        return kept
    start = next(
        (at for at in range(last_heading + 1, len(kept)) if pattern.search(bare[kept[at]])), None
    )
    if start is None:
        return kept
    while start > last_heading + 1 and not bare[kept[start - 1]].strip():
        start -= 1
    if any(protected[n] for n in kept[start:]):
        return kept
    return kept[:start]


def _strip_suffix(text: str, pattern: re.Pattern[str]) -> str | None:
    """`text` without the match of `pattern` that ends it (trailing blanks aside), else `None`."""
    end = len(text.rstrip())
    for match in pattern.finditer(text):
        if match.end() == end and match.start() > 0:
            return text[: match.start()]
    return None


def _current(target: Path, digest: str) -> tuple[str, ...] | None:
    """The guard's warnings of the Reading at `target` when it was built with the rules hashed
    `digest`; `None` when it is missing or stale."""
    if not target.is_file():
        return None
    try:
        head, _ = frontmatter.parse(target.read_bytes())
    except frontmatter.FrontmatterError:
        return None
    if head.get("rules") != digest:
        return None
    return tuple(str(warning) for warning in head.get("warnings") or ())


def _write(target: Path, data: bytes) -> None:
    """Write `data` to `target` through a temporary file renamed into place."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
