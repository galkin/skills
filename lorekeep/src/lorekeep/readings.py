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
`heading_before` alone stacks: every `heading_before` rule of that winning scope (the longest
prefix that has one, else the first engine that made the Version and has one) applies, in the
order the rules are merged (the package's, then the Store's, each in file order), and a heading an
earlier one inserted counts as a heading for the next. An engine is recognised from the Version
itself, the first of these that holds (`engine_of`):

- `fern` — a Twin (`md-twin`) with a line before its first heading starting
  `> For clean Markdown` (the llms.txt banner, worded two ways on `docs.nvidia.com`);
- `mintlify` — a Twin whose first line is `> ## Documentation Index`;
- `sphinx` — an HTML conversion (`trafilatura …`) whose stored Original loads
  `_static/documentation_options.js`, as every Sphinx theme does;
- `eur-lex` — an HTML conversion with the line `This document is an excerpt from the EUR-Lex
  website`;
- `pdf` — a PDF conversion (`markitdown …`).

The operations run in a fixed order — `drop_leading`, `drop_trailing`, `drop_lines`,
`strip_title_suffix`, `heading_before` — each on what the ones before left. A `drop_leading`
whose pattern matches the first heading line removes the block up to and including that heading.
The Reading's `title` is the Version's, unless the Version has none or a rule removed its first
heading: then it is the Reading's first heading, an inserted one included. A rule with `removes`
that would remove more than twice that from a Version — lines for a block operation (`"26 lines"`),
the share of the Version's lines for `drop_lines` (`"4%"`) — is not applied to that Version, and
the Reading says so in `warnings`.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lorekeep import frontmatter, sections
from lorekeep.project import (
    BLOCK_OPERATIONS,
    ENGINES,
    OPERATIONS,
    STACKED,
    ReadingRule,
    removes_text,
)
from lorekeep.store import OWNER_SCHEME, lock, parse_version, stem
from lorekeep.urls import host_path

CACHE_DIR = ".cache"
"""The Store's folder of what is rebuilt from the Versions: never indexed as a Version, never
backed up."""
READINGS_DIR = Path(CACHE_DIR) / "readings"
READER = "3"
"""The meaning of the operations: part of every `rules` hash, so a change rebuilds every Reading."""

FERN_BANNER = "> For clean Markdown"
MINTLIFY_BANNER = "> ## Documentation Index"
EUR_LEX_MARKER = "This document is an excerpt from the EUR-Lex website"
SPHINX_MARKER = b"_static/documentation_options.js"


@dataclass(frozen=True)
class Reading:
    """What `ensure` found: the Reading's path (`None` when no rule changes the Version), whether
    it was built now, and the guard's warnings (`rule <name> removed N lines (accepted at M
    lines)`)."""

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
    `force`), inside the Store lock; never called with the lock held. A Reading built or removed
    is told to the Index (`index.notify_reading`), so its Sections come from the file `get`
    returns."""
    return _ensure(store, version, rules, force=force, held=False)


def ensure_held(store: Path, version: Path, rules: Sequence[ReadingRule]) -> Reading:
    """`ensure` for an Index rebuild, which holds the Store lock and indexes every file after:
    nothing is locked or told to the Index here."""
    return _ensure(store, version, rules, force=False, held=True)


def _ensure(
    store: Path, version: Path, rules: Sequence[ReadingRule], *, force: bool, held: bool
) -> Reading:
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
    with contextlib.nullcontext() if held else lock(store):
        if not force:
            current = _current(target, digest)
            if current is not None:
                return Reading(target, False, current)
        if not made.touched:
            if target.exists():
                target.unlink()
                _notify(store, version, held)
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
        _notify(store, version, held)
    return Reading(target, True, made.warnings)


def _notify(store: Path, version: Path, held: bool) -> None:
    if held:
        return
    from lorekeep import index  # the Index indexes Readings, so it imports this module

    index.notify_reading(store, version)


def rules_for(
    store: Path,
    version: Path,
    head: dict[str, Any],
    body: bytes,
    rules: Sequence[ReadingRule],
) -> list[ReadingRule]:
    """The rules that apply to a Version, in the order they run: one per operation at most, but
    every `heading_before` rule of the scope that wins for it, in their order."""
    under = host_path(str(head["url"]))
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
            if rule.prefix is not None and under.startswith(rule.prefix)
        ]
        rule = max(by_prefix, key=lambda rule: len(rule.prefix or ""), default=None)
        if rule is None:
            rule = next(
                (r for r in of_operation if r.engine is not None and made_by(r.engine)), None
            )
        if rule is None:
            continue
        if operation == STACKED:
            chosen += [other for other in of_operation if other.scope == rule.scope]
        else:
            chosen.append(rule)
    return chosen


def covers(
    rule: ReadingRule, store: Path, version: Path, head: dict[str, Any], body: bytes
) -> bool:
    """Whether `rule` reaches a Version: its `prefix` starts the Version's `host/path`, or its
    `engine` made the Version. Another rule of the same operation may still win (`rules_for`)."""
    if rule.prefix is not None:
        return host_path(str(head["url"])).startswith(rule.prefix)
    return rule.engine is not None and _made_by(rule.engine, store, version, head, body)


def engine_of(store: Path, version: Path, head: dict[str, Any], body: bytes) -> str | None:
    """The engine that made a Version, the first of `ENGINES` whose markers it carries; `None`
    when none does."""
    return next(
        (engine for engine in ENGINES if _made_by(engine, store, version, head, body)), None
    )


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
    page = _Page.of(body)
    lines, bare, heading, protected = page.lines, page.bare, page.heading, page.protected
    kept = list(range(len(lines)))
    inserted: dict[int, str] = {}
    edited: dict[int, str] = {}
    title = head.get("title")
    title = str(title) if title is not None else None
    retitled = False
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
                cut = _cut_heading(bare[first], pattern)
                if cut is not None:
                    edited[first] = cut + lines[first][len(bare[first]) :]
            if title is not None:
                title = _strip_suffix(title, pattern) or title
            continue
        else:
            assert rule.level is not None
            inserted |= _headings_before(
                kept, bare, heading, protected, pattern, rule.level, inserted
            )
            continue
        warning = _held_back(rule, len(kept) - len(after), len(lines))
        if warning is not None:
            warnings.append(warning)
            continue
        first = next((n for n in kept if heading[n]), None)
        # A rule that took the first heading took the line the title was read from.
        retitled = retitled or (first is not None and first not in after)
        kept = after

    out: list[str] = []
    for n in kept:
        if n in inserted:
            out.append(inserted[n])
        out.append(edited.get(n, lines[n]))
    touched = len(kept) != len(lines) or bool(inserted) or bool(edited)
    if title is None or retitled:
        texts = [line.removesuffix("\n") for line in out]
        found = (
            sections.heading_text(text)
            for text, code in zip(texts, sections.code_lines(texts), strict=True)
            if not code
        )
        title = next((text for text in found if text), None)
    return Made(
        body="".join(out).encode("utf-8", errors="surrogateescape"),
        title=title,
        touched=touched,
        warnings=tuple(warnings),
    )


def _held_back(rule: ReadingRule, removed: int, total: int) -> str | None:
    """The guard's warning when `rule` removed more than twice what it was accepted at, in the
    unit of its `removes`: lines for a block operation, the share of the Version's `total` lines
    for `drop_lines`; `None` when it may apply."""
    allowed = rule.allowed
    if allowed is None:
        return None
    if rule.unit == "lines":
        if removed <= 2 * allowed:
            return None
        return f"rule {rule.name} removed {removes_text(rule.operation, removed)} " + (
            f"(accepted at {rule.removes})"
        )
    share = 100 * removed / total if total else 0.0
    if share <= 2 * allowed:
        return None
    return f"rule {rule.name} removed {share:.0f}% (accepted at {rule.removes})"


@dataclass(frozen=True)
class _Page:
    """A Version's body as the operations see it: its lines (each with its `\\n`), the same
    without it, which are headings, and which no rule may remove (fence and table lines)."""

    lines: list[str]
    bare: list[str]
    fenced: list[bool]
    table: list[bool]
    heading: list[bool]

    @classmethod
    def of(cls, body: bytes) -> _Page:
        lines = _lines(body.decode("utf-8", errors="surrogateescape"))
        bare = [line.removesuffix("\n") for line in lines]
        fenced = sections.code_lines(bare)
        table = [
            not code and line.lstrip().startswith("|")
            for line, code in zip(bare, fenced, strict=True)
        ]
        heading = [
            not code and sections.heading_text(line) is not None
            for line, code in zip(bare, fenced, strict=True)
        ]
        return cls(lines, bare, fenced, table, heading)

    @property
    def protected(self) -> list[bool]:
        return [code or row for code, row in zip(self.fenced, self.table, strict=True)]


@dataclass(frozen=True)
class Measure:
    """What one rule does to one Version on its own (`rules check`): the lines it removes, the
    headings it inserts or the first heading as it cuts it (`changed`), and the first line where
    it breaks a limit (`breach`: the file's line number, `0` for the whole file, and the reason
    with `{at}` for where)."""

    lines: int
    changed: tuple[str, ...]
    breach: tuple[int, str] | None = None

    @property
    def share(self) -> float:
        """The share of the Version's lines in percent the rule changes."""
        return 100 * len(self.changed) / self.lines if self.lines else 0.0


DROP_LINES_LIMIT = 30
"""The most a `drop_lines` rule may remove from any Version, in percent of its lines."""


def measure(rule: ReadingRule, body: bytes, offset: int = 0) -> Measure:
    """`rule` applied alone to a Version's `body` (whose first line is line `offset + 1` of its
    file), against the limits: `drop_lines` removes at most `DROP_LINES_LIMIT`% of the lines and
    never matches a fence or table line; a leading block ends at the first heading at most (it
    takes that heading when the pattern matches it), holds no fence or table line, and no line
    after that heading matches (a trailing block mirrors it, never taking the last heading)."""
    page = _Page.of(body)
    bare = page.bare
    pattern = re.compile(rule.pattern)
    every = list(range(len(bare)))
    matches = [n for n in every if pattern.search(bare[n])]

    def at(n: int) -> int:
        return offset + n + 1

    def kind(n: int) -> str:
        return "fence" if page.fenced[n] else "table"

    if rule.operation == "drop_lines":
        removed = [n for n in matches if not page.protected[n]]
        changed = tuple(bare[n] for n in removed)
        touched = next((n for n in matches if page.protected[n]), None)
        if touched is not None:
            return Measure(
                len(bare), changed, (at(touched), f"matches a {kind(touched)} line, {{at}}")
            )
        made = Measure(len(bare), changed)
        if made.share > DROP_LINES_LIMIT:
            return Measure(
                len(bare),
                changed,
                (0, f"removes {made.share:.0f}% of {{at}}, more than {DROP_LINES_LIMIT}%"),
            )
        return made
    if rule.operation in BLOCK_OPERATIONS:
        leading = rule.operation == "drop_leading"
        headings = [n for n in every if page.heading[n]]
        if not headings or not matches:
            return Measure(len(bare), ())
        unguarded = [False] * len(bare)
        if leading:
            rest = _drop_leading(every, bare, page.heading, unguarded, pattern)
            block = every[: len(every) - len(rest)]
        else:
            block = every[len(_drop_trailing(every, bare, page.heading, unguarded, pattern)) :]
        changed = tuple(bare[n] for n in block)
        bound = headings[0] if leading else headings[-1]
        outside = matches[-1] if leading else matches[0]
        if outside > bound if leading else outside < bound:
            where = "after the first" if leading else "before the last"
            reason = f"matches {{at}}, {where} heading (line {at(bound)})"
            return Measure(len(bare), changed, (at(outside), reason))
        touched = next((n for n in block if page.protected[n]), None)
        if touched is not None:
            reason = f"its block holds a {kind(touched)} line, {{at}}"
            return Measure(len(bare), changed, (at(touched), reason))
        return Measure(len(bare), changed)
    if rule.operation == "strip_title_suffix":
        first = next((n for n in every if page.heading[n]), None)
        cut = None if first is None else _cut_heading(bare[first], pattern)
        return Measure(len(bare), () if cut is None else (cut,))
    assert rule.level is not None
    inserted = _headings_before(every, bare, page.heading, page.protected, pattern, rule.level, {})
    return Measure(
        len(bare), tuple(line.removesuffix("\n") for _, line in sorted(inserted.items()))
    )


def _cut_heading(line: str, pattern: re.Pattern[str]) -> str | None:
    """The heading `line` without the suffix `pattern` matches, unless that empties it."""
    cut = _strip_suffix(line, pattern)
    return cut if cut is not None and sections.heading_text(cut) else None


def _headings_before(
    kept: list[int],
    bare: list[str],
    heading: list[bool],
    protected: list[bool],
    pattern: re.Pattern[str],
    level: int,
    earlier: dict[int, str],
) -> dict[int, str]:
    """The heading line to insert before each kept line that matches, by its index: not before a
    fence or table line, a heading, or a line right under a heading — one of the Version's, or
    one an `earlier` rule inserts before that line."""
    inserted: dict[int, str] = {}
    previous_is_heading = False
    for n in kept:
        if not bare[n].strip():
            continue
        if (
            not protected[n]
            and not heading[n]
            and not previous_is_heading
            and n not in earlier
            and pattern.search(bare[n])
        ):
            inserted[n] = f"{'#' * level} {bare[n].strip()}\n"
        previous_is_heading = heading[n]
    return inserted


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
    """`kept` without its lines up to the last one before the first heading that matches — the
    first heading itself when it matches — and the blank lines after them; unchanged when there is
    no heading, no match, or the block holds a fence or table line."""
    first = next((at for at, n in enumerate(kept) if heading[n]), None)
    if first is None:
        return kept
    if pattern.search(bare[kept[first]]):
        last, bound = first, len(kept)
    else:
        found = (at for at in range(first - 1, -1, -1) if pattern.search(bare[kept[at]]))
        last, bound = next(found, None), first
    if last is None:
        return kept
    end = last + 1
    while end < bound and not bare[kept[end]].strip():
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
