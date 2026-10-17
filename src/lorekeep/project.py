"""A Project's settings: `lorekeep.toml` in the Store over the package's default host table."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Literal, cast

AUTHORITIES = ("primary", "official", "third-party", "generated")
TWIN_KINDS = ("md-suffix", "accept-header", "raw", "github-raw")
DEFAULT_FRESHNESS_DAYS = 30
PROJECT_FILE = "lorekeep.toml"

TwinKind = Literal["md-suffix", "accept-header", "raw", "github-raw"]


class ProjectError(Exception):
    """`lorekeep.toml` cannot be used; the message names the key that failed."""


@dataclass(frozen=True)
class HostRule:
    """One row of the host table: what is true of every page under `prefix` (`host/path`)."""

    prefix: str
    publisher: str
    authority: str
    twin: TwinKind | None = None
    page_suffix: str | None = None
    browser: bool = False
    cut: tuple[str, ...] = ()
    source: Literal["default", "lorekeep.toml"] = "default"


@dataclass(frozen=True)
class Project:
    """The settings of the Project a Store serves."""

    bucket: str | None
    freshness_days: int
    hosts: tuple[HostRule, ...]


def load_project(store: Path) -> Project:
    """Read `lorekeep.toml` from the Store (absent means every default) over the default table."""
    defaults = _parse_hosts(_read_default_table(), "default", "the package's host table")
    path = store / PROJECT_FILE
    data: dict[str, Any] = _read_toml(path) if path.is_file() else {}
    unknown = sorted(set(data) - {"bucket", "freshness_days", "hosts"})
    if unknown:
        raise ProjectError(f"{PROJECT_FILE}: unknown key {unknown[0]}")
    bucket = data.get("bucket")
    if bucket is not None and (not isinstance(bucket, str) or not bucket):
        raise ProjectError(f"{PROJECT_FILE}: bucket must be a bucket name")
    freshness = data.get("freshness_days", DEFAULT_FRESHNESS_DAYS)
    if isinstance(freshness, bool) or not isinstance(freshness, int) or freshness < 0:
        raise ProjectError(f"{PROJECT_FILE}: freshness_days must be a whole number of days >= 0")
    own = _parse_hosts(data, "lorekeep.toml", PROJECT_FILE)
    return Project(bucket=bucket, freshness_days=freshness, hosts=merge_rules(defaults, own))


def merge_rules(defaults: list[HostRule], own: list[HostRule]) -> tuple[HostRule, ...]:
    """The default rules in order, each replaced by the Project's rule with the same prefix, then
    the Project's other rules in their order."""
    by_prefix = {rule.prefix: rule for rule in own}
    merged = [by_prefix.pop(rule.prefix, rule) for rule in defaults]
    return (*merged, *(rule for rule in own if rule.prefix in by_prefix))


def _read_default_table() -> dict[str, Any]:
    text = resources.files("lorekeep").joinpath("hosts.toml").read_text(encoding="utf-8")
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
