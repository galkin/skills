"""The commit point and the lock: what a commit leaves in the Store."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from lorekeep.store import (
    AliasRow,
    LockError,
    NewVersion,
    RecheckRow,
    TagRow,
    commit,
    lock,
    read_head,
)

SRC = Path(__file__).parent.parent / "src" / "lorekeep"
URL = "https://docs.example.test/guide"


def rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_a_commit_of_rows_alone_appends_them_and_writes_no_version_and_every_recheck_is_kept(
    tmp_path: Path,
) -> None:
    tag = TagRow(URL, "anthropic", "2026-10-01T00:00:00Z")
    check = RecheckRow(URL, "2026-10-02T00:00:00Z", "unchanged", "304", "ab" * 32)
    alias = AliasRow("https://docs.example.test/old", URL, "2026-10-03T00:00:00Z")

    assert commit(tmp_path, tags=[tag]) is None
    assert commit(tmp_path, checks=[check]) is None
    assert commit(tmp_path, aliases=[alias]) is None
    commit(tmp_path, tags=[tag, TagRow(URL, "anthropic", "2026-10-09T00:00:00Z")])
    commit(tmp_path, aliases=[alias, AliasRow(alias.alias, URL, "2026-10-09T00:00:00Z")])
    commit(tmp_path, checks=[check])

    assert list(tmp_path.glob("*.md")) == []
    assert rows(tmp_path / "tags.csv") == [
        ["url", "tag", "added_at"],
        [URL, "anthropic", "2026-10-01T00:00:00Z"],
    ]
    assert rows(tmp_path / "aliases.csv") == [
        ["alias", "url", "added_at"],
        ["https://docs.example.test/old", URL, "2026-10-03T00:00:00Z"],
    ]
    # Two Rechecks with one answer in one second are two Rechecks: the row is never deduplicated.
    assert rows(tmp_path / "checks.csv") == [
        ["url", "checked_at", "result", "status", "sha256"],
        [URL, "2026-10-02T00:00:00Z", "unchanged", "304", "ab" * 32],
        [URL, "2026-10-02T00:00:00Z", "unchanged", "304", "ab" * 32],
    ]


def test_the_lock_context_manager_is_the_only_place_the_lock_file_is_opened() -> None:
    hits = [
        (path, line)
        for path in SRC.rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if ".lorekeep.lock" in line
    ]

    assert len(hits) == 1, hits
    assert hits[0][0].name == "store.py"
    assert "fcntl" not in {
        name
        for path in SRC.rglob("*.py")
        if path.name != "store.py"
        for name in path.read_text().split()
    }


def test_a_commit_leaves_the_lock_file_and_no_temporary_file_and_cuts_a_long_name(
    tmp_path: Path,
) -> None:
    long_url = "https://docs.example.test/" + "/".join(f"segment-{n:03d}" for n in range(40))
    body = b"# Deep page\n"
    head = {
        "url": long_url,
        "fetched_at": "2026-10-01T00:00:00Z",
        "sha256": "0123456789abcdef" * 4,
        "publisher": "docs.example.test",
        "authority": "third-party",
        "converter": "trafilatura 2.3.1",
    }

    path = commit(tmp_path, NewVersion(head, body, original=b"<html>x</html>", original_ext="html"))

    assert path is not None and path.parent == tmp_path
    assert len(path.name.encode()) < 200
    assert path.name.startswith("docs.example.test--segment-000-")
    assert path.name.endswith("--01234567.md")
    assert read_head(path)["url"] == long_url
    original = tmp_path / f"{path.name.removesuffix('.md')}.orig.html"
    assert original.read_bytes() == b"<html>x</html>"
    names = sorted(p.name for p in tmp_path.iterdir())
    assert ".lorekeep.lock" in names
    assert not [name for name in names if ".tmp-" in name]


def test_an_existing_version_is_left_alone_and_the_lock_is_never_nested(tmp_path: Path) -> None:
    head = {
        "url": URL,
        "fetched_at": "2026-10-01T00:00:00Z",
        "sha256": "ff" * 32,
        "publisher": "docs.example.test",
        "authority": "third-party",
        "converter": "md-twin",
    }
    first = commit(tmp_path, NewVersion(head, b"# One\n"))
    assert first is not None
    before = first.stat().st_mtime_ns

    second = commit(
        tmp_path, NewVersion({**head, "fetched_at": "2026-10-09T00:00:00Z"}, b"# Two\n")
    )

    assert second == first
    assert first.read_bytes().endswith(b"# One\n")
    assert first.stat().st_mtime_ns == before
    with lock(tmp_path), pytest.raises(LockError), lock(tmp_path):
        pass
