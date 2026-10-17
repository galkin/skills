"""The Latest Version rule is one rule: the Store's scan and the Index's view give one answer."""

from __future__ import annotations

from pathlib import Path

import pytest

from lorekeep.store import RecheckRow, commit
from tests.support import FIXTURES, run_cli, write_version
from tests.test_helpers import read_version

PAGE = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
A = FIXTURES / "ms-foundry.twin"
B = FIXTURES / "anthropic-prompt-caching.twin"
C = FIXTURES / "aws-prompt-caching.twin"
FOREVER = ("--max-age", "36500")
"""A window no Version is older than: `get` returns the Latest Version without a request."""


def sha256_of(version: Path) -> str:
    return str(read_version(version)[0]["sha256"])


def latest_without_and_with_an_index(store: Path) -> tuple[str, str]:
    """What `get` answers from the files, then from a freshly built Index."""
    env = {"LOREKEEP_STORE": str(store), "LOREKEEP_TAG": "microsoft"}
    assert not (store / "sources.db").exists()
    scanned = run_cli(["get", PAGE, *FOREVER], env=env)
    assert scanned.exit_code == 0, scanned.stderr
    built = run_cli(["index", "--store", str(store)])
    assert built.exit_code == 0, built.stderr
    viewed = run_cli(["get", PAGE, *FOREVER], env=env)
    assert viewed.exit_code == 0, viewed.stderr
    return scanned.stdout.splitlines()[-1], viewed.stdout.splitlines()[-1]


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        pytest.param([], "b", id="no Recheck: the newest fetched_at"),
        pytest.param(
            [("2026-10-02T00:00:00Z", "b"), ("2026-10-09T00:00:00Z", "a")],
            "a",
            id="A then B then A again: the latest row names an older file",
        ),
        pytest.param(
            [("2026-10-09T00:00:00Z", "b"), ("2026-10-09T00:00:00Z", "a")],
            "a",
            id="two rows in one second: the later row wins",
        ),
        pytest.param(
            [("2026-10-02T00:00:00Z", "a"), ("2026-10-09T00:00:00Z", "0" * 64)],
            "b",
            id="the latest row names no stored Version: the newest fetched_at",
        ),
        pytest.param(
            [("2026-10-09T00:00:00Z", "gone"), ("2026-10-10T00:00:00Z", "")],
            "b",
            id="a row without a sha256 names nothing",
        ),
    ],
)
def test_the_scan_and_the_index_view_agree_on_the_latest_version(
    tmp_path: Path, checks: list[tuple[str, str]], expected: str
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    files = {
        "a": write_version(store, A, fetched_at="2026-09-01T00:00:00Z", url=PAGE),
        "b": write_version(store, B, fetched_at="2026-10-01T00:00:00Z", url=PAGE),
    }
    sha = {name: sha256_of(path) for name, path in files.items()}
    rows = [RecheckRow(PAGE, at, "changed", "200", sha.get(named, named)) for at, named in checks]
    commit(store, checks=rows)

    scanned, viewed = latest_without_and_with_an_index(store)

    assert scanned == viewed == str(files[expected])


def test_versions_fetched_in_the_same_second_tie_to_the_first_file_name(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    at = "2026-10-01T00:00:00Z"
    files = [write_version(store, fixture, fetched_at=at, url=PAGE) for fixture in (A, B, C)]

    scanned, viewed = latest_without_and_with_an_index(store)

    assert scanned == viewed == str(min(files))
