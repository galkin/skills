"""A Project's settings: `lorekeep.toml` in the Store over the package's default host table and
its default reading rules."""

from __future__ import annotations

import datetime
import re
import tomllib
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path
from typing import Any, Literal, cast

AUTHORITIES = ("primary", "official", "third-party", "generated")
TWIN_KINDS = ("md-suffix", "accept-header", "raw", "github-raw")
DEFAULT_FRESHNESS_DAYS = 30
PROJECT_FILE = "lorekeep.toml"

TwinKind = Literal["md-suffix", "accept-header", "raw", "github-raw"]
ENGINES = ("fern", "mintlify", "sphinx", "eur-lex", "pdf")
OPERATIONS = ("drop_leading", "drop_trailing", "drop_lines", "strip_title_suffix", "heading_before")

Operation = Literal[
    "drop_leading", "drop_trailing", "drop_lines", "strip_title_suffix", "heading_before"
]


class ProjectError(Exception):
    """`lorekeep.toml` cannot be used; the message names the key that failed."""


@dataclass(frozen=True)
class HostRule:
    """One row of the host table: what is true of every page under `prefix` (`host/path`);
    `inherited` when `twin` and `page_suffix` came from a shorter prefix's rule."""

    prefix: str
    publisher: str
    authority: str
    twin: TwinKind | None = None
    page_suffix: str | None = None
    browser: bool = False
    cut: tuple[str, ...] = ()
    source: Literal["default", "lorekeep.toml"] = "default"
    inherited: bool = False


@dataclass(frozen=True)
class ReadingRule:
    """One `[[readings]]` rule: one operation (`pattern`, a regular expression; `level` for
    `heading_before`) on every Version under `prefix` (`host/path`) or made by `engine`, with the
    date it was `accepted` and the share of lines in percent it `removes` as accepted."""

    operation: Operation
    pattern: str
    prefix: str | None = None
    engine: str | None = None
    level: int | None = None
    accepted: str | None = None
    removes: float | None = None
    source: Literal["default", "lorekeep.toml"] = "default"

    @property
    def scope(self) -> str:
        """What the rule applies to: its prefix, or `engine:<name>`."""
        return self.prefix if self.prefix is not None else f"engine:{self.engine}"

    @property
    def name(self) -> str:
        """The rule as a warning names it: `<prefix> <operation>` (`engine:fern drop_leading`)."""
        return f"{self.scope} {self.operation}"


@dataclass(frozen=True)
class Project:
    """The settings of the Project a Store serves."""

    bucket: str | None
    freshness_days: int
    hosts: tuple[HostRule, ...]
    readings: tuple[ReadingRule, ...] = ()


def load_project(store: Path) -> Project:
    """Read `lorekeep.toml` from the Store (absent means every default) over the default table."""
    defaults = _parse_hosts(_read_default_table(), "default", "the package's host table")
    default_readings = _parse_readings(
        _read_package_toml("readings.toml"), "default", "the package's reading rules"
    )
    path = store / PROJECT_FILE
    data: dict[str, Any] = _read_toml(path) if path.is_file() else {}
    unknown = sorted(set(data) - {"bucket", "freshness_days", "hosts", "readings"})
    if unknown:
        raise ProjectError(f"{PROJECT_FILE}: unknown key {unknown[0]}")
    bucket = data.get("bucket")
    if bucket is not None and (not isinstance(bucket, str) or not bucket):
        raise ProjectError(f"{PROJECT_FILE}: bucket must be a bucket name")
    freshness = data.get("freshness_days", DEFAULT_FRESHNESS_DAYS)
    if isinstance(freshness, bool) or not isinstance(freshness, int) or freshness < 0:
        raise ProjectError(f"{PROJECT_FILE}: freshness_days must be a whole number of days >= 0")
    own = _parse_hosts(data, "lorekeep.toml", PROJECT_FILE)
    own_readings = _parse_readings(data, "lorekeep.toml", PROJECT_FILE)
    return Project(
        bucket=bucket,
        freshness_days=freshness,
        hosts=merge_rules(defaults, own),
        readings=merge_readings(default_readings, own_readings),
    )


def merge_rules(defaults: list[HostRule], own: list[HostRule]) -> tuple[HostRule, ...]:
    """The default rules in order, each replaced by the Project's rule with the same prefix, then
    the Project's other rules in their order; a rule naming neither `twin` nor `page_suffix`
    inherits both from the merged table (`inherit`)."""
    by_prefix = {rule.prefix: rule for rule in own}
    merged = [by_prefix.pop(rule.prefix, rule) for rule in defaults]
    return inherit([*merged, *(rule for rule in own if rule.prefix in by_prefix)])


def inherit(rules: list[HostRule]) -> tuple[HostRule, ...]:
    """Each rule that names neither `twin` nor `page_suffix` with both taken from the rule with the
    longest shorter prefix that names a `twin`, if any; `browser` and `cut` are never inherited."""

    def resolved(rule: HostRule) -> HostRule:
        if rule.twin is not None or rule.page_suffix is not None:
            return rule
        donors = [
            other
            for other in rules
            if other.twin is not None
            and len(other.prefix) < len(rule.prefix)
            and rule.prefix.startswith(other.prefix)
        ]
        donor = max(donors, key=lambda other: len(other.prefix), default=None)
        if donor is None:
            return rule
        return replace(rule, twin=donor.twin, page_suffix=donor.page_suffix, inherited=True)

    return tuple(resolved(rule) for rule in rules)


def merge_readings(defaults: list[ReadingRule], own: list[ReadingRule]) -> tuple[ReadingRule, ...]:
    """The default reading rules in order, each replaced by the Project's rule with the same
    prefix or engine and operation, then the Project's other rules in their order."""
    by_key = {(rule.scope, rule.operation): rule for rule in own}
    merged = [by_key.pop((rule.scope, rule.operation), rule) for rule in defaults]
    return (*merged, *(rule for rule in own if (rule.scope, rule.operation) in by_key))


def _read_default_table() -> dict[str, Any]:
    return _read_package_toml("hosts.toml")


def _read_package_toml(name: str) -> dict[str, Any]:
    text = resources.files("lorekeep").joinpath(name).read_text(encoding="utf-8")
    return tomllib.loads(text)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ProjectError(f"{path.name} is not valid TOML: {error}") from error


RULE_KEYS = ("prefix", "publisher", "authority", "twin", "page_suffix", "browser", "cut")


def _parse_hosts(
    data: dict[str, Any], source: Literal["default", "lorekeep.toml"], where: str
) -> list[HostRule]:
    rows = data.get("hosts", [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ProjectError(f"{where}: hosts must be [[hosts]] tables")
    rules: list[HostRule] = []
    seen: set[str] = set()
    for number, row in enumerate(cast(list[dict[str, Any]], rows), start=1):
        key = f"hosts[{number}]"
        unknown = sorted(set(row) - set(RULE_KEYS))
        if unknown:
            raise ProjectError(f"{where}: unknown key {key}.{unknown[0]}")
        for required in ("prefix", "publisher", "authority"):
            if not isinstance(row.get(required), str) or not row[required]:
                raise ProjectError(f"{where}: {key}.{required} is required and must be a string")
        if row["authority"] not in AUTHORITIES:
            raise ProjectError(f"{where}: {key}.authority must be one of {', '.join(AUTHORITIES)}")
        twin = row.get("twin")
        if twin is not None and twin not in TWIN_KINDS:
            raise ProjectError(f"{where}: {key}.twin must be one of {', '.join(TWIN_KINDS)}")
        page_suffix = row.get("page_suffix")
        if page_suffix is not None and not isinstance(page_suffix, str):
            raise ProjectError(f"{where}: {key}.page_suffix must be a string")
        browser = row.get("browser", False)
        if not isinstance(browser, bool):
            raise ProjectError(f"{where}: {key}.browser must be true or false")
        cut = row.get("cut", [])
        if not isinstance(cut, list) or not all(isinstance(item, str) for item in cut):
            raise ProjectError(f"{where}: {key}.cut must be a list of CSS selectors")
        if row["prefix"] in seen:
            raise ProjectError(f"{where}: {key}.prefix {row['prefix']} is given twice")
        seen.add(row["prefix"])
        rules.append(
            HostRule(
                prefix=row["prefix"],
                publisher=row["publisher"],
                authority=row["authority"],
                twin=twin,
                page_suffix=page_suffix,
                browser=browser,
                cut=tuple(cast(list[str], cut)),
                source=source,
            )
        )
    return rules


READING_KEYS = ("prefix", "engine", *OPERATIONS, "level", "accepted", "removes")


def _parse_readings(
    data: dict[str, Any], source: Literal["default", "lorekeep.toml"], where: str
) -> list[ReadingRule]:
    rows = data.get("readings", [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ProjectError(f"{where}: readings must be [[readings]] tables")
    rules: list[ReadingRule] = []
    seen: set[tuple[str, str]] = set()
    for number, row in enumerate(cast(list[dict[str, Any]], rows), start=1):
        key = f"readings[{number}]"
        unknown = sorted(set(row) - set(READING_KEYS))
        if unknown:
            raise ProjectError(f"{where}: unknown key {key}.{unknown[0]}")
        if ("prefix" in row) == ("engine" in row):
            raise ProjectError(f"{where}: {key} needs exactly one of prefix and engine")
        prefix, engine = row.get("prefix"), row.get("engine")
        if prefix is not None and (not isinstance(prefix, str) or not prefix):
            raise ProjectError(f"{where}: {key}.prefix must be a host/path string")
        if engine is not None and engine not in ENGINES:
            raise ProjectError(f"{where}: {key}.engine must be one of {', '.join(ENGINES)}")
        named = [operation for operation in OPERATIONS if operation in row]
        if len(named) != 1:
            raise ProjectError(f"{where}: {key} needs exactly one of {', '.join(OPERATIONS)}")
        operation = cast(Operation, named[0])
        pattern = row[operation]
        if not isinstance(pattern, str) or not pattern:
            raise ProjectError(f"{where}: {key}.{operation} must be a regular expression")
        try:
            re.compile(pattern)
        except re.error as error:
            raise ProjectError(
                f"{where}: {key}.{operation} is not a regular expression: {error}"
            ) from error
        level = row.get("level")
        if operation == "heading_before":
            if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 6:
                raise ProjectError(f"{where}: {key}.level must be a heading level from 1 to 6")
        elif level is not None:
            raise ProjectError(f"{where}: {key}.level belongs to heading_before only")
        accepted = row.get("accepted")
        if isinstance(accepted, datetime.date):
            accepted = accepted.isoformat()
        if accepted is not None and not isinstance(accepted, str):
            raise ProjectError(f"{where}: {key}.accepted must be a date")
        removes = row.get("removes")
        if removes is not None and (
            isinstance(removes, bool) or not isinstance(removes, int | float) or removes < 0
        ):
            raise ProjectError(f"{where}: {key}.removes must be a percentage >= 0")
        rule = ReadingRule(
            operation=operation,
            pattern=pattern,
            prefix=prefix,
            engine=engine,
            level=level,
            accepted=accepted,
            removes=None if removes is None else float(removes),
            source=source,
        )
        if (rule.scope, operation) in seen:
            raise ProjectError(f"{where}: {key} repeats {operation} for {rule.scope}")
        seen.add((rule.scope, operation))
        rules.append(rule)
    return rules
