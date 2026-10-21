"""`rules`: the material for a proposer of reading rules (`sample`), the measure of its candidates
against the limits (`check`), and the passing ones written into `lorekeep.toml` (`accept`).

lorekeep calls no model: the proposer is a subagent the orchestrator launches, and these commands
only hand it Versions and judge what it returns (references/curating.md has the brief). A candidate
is measured on its own, on every Version it reaches, before any other rule; `removes` is the most
it changed there, in lines for a block operation and in percent for `drop_lines`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import statistics
import sys
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lorekeep import readings
from lorekeep.commands import plural
from lorekeep.project import (
    BLOCK_OPERATIONS,
    ENGINES,
    PROJECT_FILE,
    ProjectError,
    ReadingRule,
    load_project,
    parse_reading,
    removes_text,
    with_readings,
)
from lorekeep.store import OWNER_SCHEME, lock, parse_version, scan
from lorekeep.urls import host_path

if TYPE_CHECKING:
    from lorekeep.cli import Context

DEFAULT_SAMPLE = 5
OTHER = "other"
"""The `rules sample` group of the Versions no engine made."""
EXAMPLES = 3
EXAMPLE_WIDTH = 100


def run(args: argparse.Namespace, ctx: Context) -> int:
    if args.rules_command == "sample":
        return sample(args, ctx)
    try:
        candidates = load_candidates(Path(args.file))
    except ProjectError as error:
        print(f"lorekeep: error: {error}", file=sys.stderr)
        return 2
    stored = versions(ctx.store)
    verdicts = [judge(candidate, ctx.store, stored) for candidate in candidates]
    for verdict in verdicts:
        print(verdict.report())
    failed = sum(1 for verdict in verdicts if not verdict.passed)
    if args.rules_command == "check":
        passed = len(verdicts) - failed
        print(f"Checked {plural(len(verdicts), 'candidate')}: {passed} pass, {failed} fail")
        return 0
    return accept(ctx, stored, verdicts, failed, everything=args.all)


@dataclass(frozen=True)
class _Version:
    path: Path
    head: dict[str, Any]
    body: bytes
    offset: int

    @property
    def lines(self) -> int:
        """The body's lines, a last line without its newline counted."""
        return self.body.count(b"\n") + (1 if self.body and not self.body.endswith(b"\n") else 0)


def versions(store: Path) -> list[_Version]:
    """Every Version in the Store that may have a Reading (`owner:` Sources never do)."""
    found: list[_Version] = []
    for info in scan(store):
        if info.url.startswith(OWNER_SCHEME):
            continue
        data = info.path.read_bytes()
        head, body = parse_version(data)
        offset = data[: len(data) - len(body)].count(b"\n")
        found.append(_Version(info.path, head, body, offset))
    return found


def sample(args: argparse.Namespace, ctx: Context) -> int:
    """Print the paths of Versions under the prefix, the newest of each Source, by the engine that
    made them: per engine (`other` for none) a `# engine: NAME` line, then up to `--sample` of its
    Versions — the shortest, the longest, then the rest spread evenly between them by length.
    `--engine` prints that group alone."""
    wanted = args.sample
    if wanted < 1:
        print("lorekeep: error: --sample must be at least 1", file=sys.stderr)
        return 2
    groups = (*ENGINES, OTHER)
    if args.engine is not None and args.engine not in groups:
        print(f"lorekeep: error: --engine must be one of {', '.join(groups)}", file=sys.stderr)
        return 2
    prefix = args.prefix.split("://", 1)[-1]
    newest: dict[str, _Version] = {}
    for version in versions(ctx.store):
        if not host_path(str(version.head["url"])).startswith(prefix):
            continue
        url = str(version.head["url"])
        held = newest.get(url)
        if held is None or str(version.head["fetched_at"]) > str(held.head["fetched_at"]):
            newest[url] = version
    if not newest:
        print(f"lorekeep: error: no Version under {prefix}", file=sys.stderr)
        return 1
    by_engine: dict[str, list[_Version]] = {group: [] for group in groups}
    for version in newest.values():
        made = readings.engine_of(ctx.store, version.path, version.head, version.body)
        by_engine[made or OTHER].append(version)
    if args.engine is not None:
        by_engine = {args.engine: by_engine[args.engine]}
        if not by_engine[args.engine]:
            made = "no engine made" if args.engine == OTHER else f"{args.engine} made"
            print(f"lorekeep: error: no Version under {prefix} that {made}", file=sys.stderr)
            return 1
    for engine, group in by_engine.items():
        if not group:
            continue
        print(f"# engine: {engine}")
        by_length = sorted(group, key=lambda version: (version.lines, version.path.name))
        for version in spread(by_length, wanted):
            print(version.path)
    return 0


def spread[T](ordered: list[T], wanted: int) -> list[T]:
    """Up to `wanted` items of `ordered`: the first, the last, then the others evenly spaced
    between them, in order."""
    if len(ordered) <= wanted:
        picked = list(range(len(ordered)))
    elif wanted == 1:
        picked = [0]
    else:
        last = len(ordered) - 1
        picked = [round(step * last / (wanted - 1)) for step in range(wanted)]
    ends = [picked[0], picked[-1]] if len(picked) > 1 else picked[:1]
    return [ordered[at] for at in [*ends, *picked[1:-1]]]


@dataclass(frozen=True)
class Candidate:
    """One `[[readings]]` table of a candidates file: its rule, or why it is not one."""

    number: int
    row: dict[str, Any]
    rule: ReadingRule | None
    problem: str | None = None

    @property
    def label(self) -> str:
        if self.rule is not None:
            shown = f"{self.rule.name} = {json.dumps(self.rule.pattern, ensure_ascii=False)}"
            return shown + (f", level {self.rule.level}" if self.rule.level else "")
        return json.dumps(self.row, ensure_ascii=False, default=str)


def load_candidates(path: Path) -> list[Candidate]:
    """The candidates in the TOML file at `path`: `[[readings]]` tables and nothing else. A table
    that is not the rule grammar is a candidate that fails, not an error."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ProjectError(f"cannot read {path}: {error.strerror}") from error
    except tomllib.TOMLDecodeError as error:
        raise ProjectError(f"{path} is not valid TOML: {error}") from error
    rows = data.get("readings")
    if set(data) != {"readings"} or not isinstance(rows, list):
        raise ProjectError(f"{path} must hold [[readings]] tables and nothing else")
    candidates: list[Candidate] = []
    for number, row in enumerate(cast(list[Any], rows), start=1):
        if not isinstance(row, dict):
            raise ProjectError(f"{path} must hold [[readings]] tables and nothing else")
        row = cast(dict[str, Any], row)
        try:
            candidates.append(Candidate(number, row, parse_reading(row, number, candidate=True)))
        except ProjectError as error:
            candidates.append(Candidate(number, row, None, str(error)))
    return candidates


@dataclass
class Verdict:
    """What `rules check` found for one candidate."""

    candidate: Candidate
    reached: int = 0
    counts: list[int] = field(default_factory=list[int])
    shares: list[float] = field(default_factory=list[float])
    examples: list[str] = field(default_factory=list[str])
    reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.reason is None

    @property
    def removes(self) -> str | None:
        """What `rules accept` writes as `removes`: the most it changed in one Version."""
        rule = self.candidate.rule
        if rule is None or rule.operation not in (*BLOCK_OPERATIONS, "drop_lines"):
            return None
        if rule.operation == "drop_lines":
            return removes_text(rule.operation, math.ceil(max(self.shares, default=0.0)))
        return removes_text(rule.operation, max(self.counts, default=0))

    def report(self) -> str:
        rule = self.candidate.rule
        lines = [f"[{self.candidate.number}] {self.candidate.label}"]
        if rule is not None and self.reached:
            what = {
                "heading_before": "headings inserted",
                "strip_title_suffix": "titles cut",
            }.get(rule.operation, "lines removed")
            low, mid, high = min(self.counts), statistics.median(self.counts), max(self.counts)
            line = (
                f"    over {plural(self.reached, 'Version')}: {sum(self.counts)} {what} "
                f"(per Version min {low}, median {mid:g}, max {high})"
            )
            if rule.operation == "drop_lines":
                line += f", at most {max(self.shares):.0f}% of a Version"
            lines.append(line)
            lines += [f"    | {example}" for example in self.examples]
        lines.append(f"    {'pass' if self.passed else f'fail: {self.reason}'}")
        return "\n".join(lines)


def judge(candidate: Candidate, store: Path, stored: list[_Version]) -> Verdict:
    """Measure `candidate` on every Version of `stored` it reaches and give its verdict against
    the limits."""
    verdict = Verdict(candidate)
    rule = candidate.rule
    if rule is None:
        verdict.reason = candidate.problem
        return verdict
    changed: dict[str, None] = {}
    breaches: list[tuple[float, str]] = []
    for version in stored:
        if not readings.covers(rule, store, version.path, version.head, version.body):
            continue
        made = readings.measure(rule, version.body, version.offset)
        verdict.reached += 1
        verdict.counts.append(len(made.changed))
        verdict.shares.append(made.share)
        changed |= dict.fromkeys(line for line in made.changed if line.strip())
        if made.breach is not None:
            line, reason = made.breach
            at = version.path.name if line == 0 else f"{version.path.name}:{line}"
            # A Version where the share is over the limit is reported by its share, highest
            # first; any other breach is reported before it.
            breaches.append((made.share if line == 0 else math.inf, reason.format(at=at)))
    verdict.examples = [_short(line) for line in _spread_examples(list(changed))]
    if not verdict.reached:
        verdict.reason = f"no Version under {rule.scope}"
    elif breaches:
        verdict.reason = max(breaches, key=lambda breach: breach[0])[1]
    elif not sum(verdict.counts):
        verdict.reason = f"changes no Version under {rule.scope}"
    return verdict


def _spread_examples(changed: list[str]) -> list[str]:
    """Up to `EXAMPLES` of the lines a rule changed, blank ones aside: the first, the last, one
    between."""
    if len(changed) <= EXAMPLES:
        return changed
    return [changed[0], changed[len(changed) // 2], changed[-1]]


def _short(line: str) -> str:
    return line if len(line) <= EXAMPLE_WIDTH else line[: EXAMPLE_WIDTH - 1] + "…"


def accept(
    ctx: Context, stored: list[_Version], verdicts: list[Verdict], failed: int, *, everything: bool
) -> int:
    """Write the passing candidates (every one that is a rule, with `--all`) into the Store's
    `lorekeep.toml` with `accepted` and `removes`, then build the Readings they reach."""
    today = datetime.date.today().isoformat()
    by_key: dict[tuple[str, ...], tuple[int, ReadingRule]] = {}
    for verdict in verdicts:
        rule = verdict.candidate.rule
        if rule is None or not (verdict.passed or everything):
            continue
        key = rule.key
        if key in by_key:
            # As in lorekeep.toml, a later rule that is the same rule (the same prefix and
            # operation, and pattern for heading_before) replaces it.
            same = "the same operation" if len(key) == 2 else "the same heading_before"
            print(
                f"lorekeep: note: readings[{by_key[key][0]}] is replaced by "
                f"readings[{verdict.candidate.number}], {same} on {rule.scope}",
                file=sys.stderr,
            )
        accepted = replace(rule, accepted=today, removes=verdict.removes)
        by_key[key] = (verdict.candidate.number, accepted)
    chosen = [rule for _, rule in by_key.values()]
    if chosen:
        path = ctx.store / PROJECT_FILE
        try:
            with lock(ctx.store):
                text = path.read_text(encoding="utf-8") if path.is_file() else ""
                written = with_readings(text, chosen)
                tmp = path.with_name(f"{path.name}.tmp")
                tmp.write_text(written, encoding="utf-8")
                tmp.replace(path)
        except ProjectError as error:
            print(f"lorekeep: error: {error}", file=sys.stderr)
            return 2
    print(f"Accepted {plural(len(chosen), 'rule')}, {failed} failed")
    if not chosen:
        return 0
    rules = load_project(ctx.store).readings
    built = current = 0
    for version in stored:
        if not any(
            readings.covers(rule, ctx.store, version.path, version.head, version.body)
            for rule in chosen
        ):
            continue
        reading = readings.ensure(ctx.store, version.path, rules)
        if reading.path is None or reading.built:
            for warning in reading.warnings:
                print(f"lorekeep: warning: {version.head['url']}: {warning}", file=sys.stderr)
        if reading.built:
            built += 1
        elif reading.path is not None:
            current += 1
    print(f"Built {plural(built, 'Reading')}, {current} current")
    return 0
