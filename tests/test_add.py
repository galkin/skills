"""`add`: a file the owner provides becomes a Version with `origin: owner`."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lorekeep.store import RecheckRow, commit
from tests.support import rows, run_cli
from tests.test_helpers import read_version

BODY = "# Research on prompt caching\n\nPasted from a chat.\n"


def note(tmp_path: Path) -> Path:
    path = tmp_path / "outside" / "note.md"
    path.parent.mkdir()
    path.write_text(BODY, encoding="utf-8")
    return path


def store(tmp_path: Path) -> Path:
    path = tmp_path / "store"
    path.mkdir()
    return path


def test_add_of_a_text_file_creates_an_owner_version_with_one_tag_row(tmp_path: Path) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    digest = hashlib.sha256(BODY.encode()).hexdigest()

    result = run_cli(
        ["add", str(file), "--title", "Research on Prompt Caching!", "--tag", "anthropic"],
        env={"LOREKEEP_STORE": str(store_dir)},
    )

    assert result.exit_code == 0, result.stderr
    expected = store_dir / f"owner--research-on-prompt-caching--{digest[:8]}.md"
    assert result.stdout.rstrip("\n").splitlines()[-1] == str(expected)
    head, body = read_version(expected)
    assert body.decode() == BODY
    assert head["sha256"] == digest
    assert head["url"] == "owner:research-on-prompt-caching"
    assert head["origin"] == "owner"
    assert head["authority"] == "generated"
    assert head["publisher"] == "owner"
    assert head["converter"] == "owner"
    assert head["title"] == "Research on Prompt Caching!"
    mtime = datetime.fromtimestamp(file.stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert head["fetched_at"] == mtime
    assert "original" not in head
    tags = rows(store_dir, "tags.csv")
    assert [(row["url"], row["tag"]) for row in tags] == [
        ("owner:research-on-prompt-caching", "anthropic")
    ]
    datetime.fromisoformat(tags[0]["added_at"])


def test_add_json_prints_one_object_with_the_path(tmp_path: Path) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    digest = hashlib.sha256(BODY.encode()).hexdigest()

    result = run_cli(
        ["add", str(file), "--title", "Research", "--json"],
        env={"LOREKEEP_STORE": str(store_dir), "LOREKEEP_TAG": "nvidia"},
    )

    assert result.exit_code == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["path"] == str(store_dir / f"owner--research--{digest[:8]}.md")
    assert data["url"] == "owner:research"
    assert data["requested_url"] == data["url"]
    assert data["sha256"] == digest
    assert data["converter"] == "owner"
    assert data["publisher"] == "owner"
    assert data["authority"] == "generated"
    assert data["outcome"] == "stored"
    assert data["verified_at"] == data["fetched_at"]
    assert set(data) == {
        "path",
        "url",
        "requested_url",
        "sha256",
        "fetched_at",
        "converter",
        "publisher",
        "authority",
        "verified_at",
        "outcome",
    }


def test_add_of_the_same_content_twice_creates_one_file_and_tags_once_per_tag(
    tmp_path: Path,
) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    env = {"LOREKEEP_STORE": str(store_dir)}

    first = run_cli(["add", str(file), "--title", "Research", "--tag", "anthropic"], env=env)
    second = run_cli(["add", str(file), "--title", "Research", "--tag", "anthropic"], env=env)
    third = run_cli(["add", str(file), "--title", "Research", "--tag", "nvidia"], env=env)

    assert (first.exit_code, second.exit_code, third.exit_code) == (0, 0, 0)
    assert first.stdout == second.stdout == third.stdout
    assert sorted(p.name for p in store_dir.glob("*.md")) == [Path(first.stdout.strip()).name]
    assert [(row["url"], row["tag"]) for row in rows(store_dir, "tags.csv")] == [
        ("owner:research", "anthropic"),
        ("owner:research", "nvidia"),
    ]


def test_add_json_of_a_version_already_stored_is_unchanged_with_its_verified_at(
    tmp_path: Path,
) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    env = {"LOREKEEP_STORE": str(store_dir), "LOREKEEP_TAG": "anthropic"}
    argv = [
        "add",
        str(file),
        "--title",
        "Research",
        "--fetched-at",
        "2026-09-01T00:00:00Z",
        "--json",
    ]
    first = json.loads(run_cli(argv, env=env).stdout)
    assert first["outcome"] == "stored"
    commit(
        store_dir,
        checks=[
            RecheckRow(
                "owner:research", "2026-09-05T00:00:00Z", "unchanged", "304", first["sha256"]
            )
        ],
    )

    second = json.loads(run_cli(argv, env=env).stdout)

    assert second["path"] == first["path"]
    assert second["outcome"] == "unchanged"
    assert second["fetched_at"] == "2026-09-01T00:00:00Z"
    assert second["verified_at"] == "2026-09-05T00:00:00Z"


def test_add_honours_authority_publisher_and_fetched_at(tmp_path: Path) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)

    result = run_cli(
        [
            "add",
            str(file),
            "--title",
            "Research",
            "--authority",
            "primary",
            "--publisher",
            "claude",
            "--fetched-at",
            "2026-09-01T12:30:00+02:00",
            "--tag",
            "anthropic",
        ],
        env={"LOREKEEP_STORE": str(store_dir)},
    )

    assert result.exit_code == 0, result.stderr
    head, _ = read_version(Path(result.stdout.strip()))
    assert head["authority"] == "primary"
    assert head["publisher"] == "claude"
    assert head["fetched_at"] == "2026-09-01T10:30:00Z"


def test_a_fetched_at_without_a_timezone_is_utc_whatever_the_local_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    time.tzset()
    try:
        result = run_cli(
            ["add", str(file), "--title", "Research", "--fetched-at", "2026-09-01T12:30:00"],
            env={"LOREKEEP_STORE": str(store_dir), "LOREKEEP_TAG": "anthropic"},
        )
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()

    assert result.exit_code == 0, result.stderr
    head, _ = read_version(Path(result.stdout.strip()))
    assert head["fetched_at"] == "2026-09-01T12:30:00Z"


def test_add_without_a_tag_with_two_tags_or_without_a_title_writes_nothing(
    tmp_path: Path,
) -> None:
    store_dir = store(tmp_path)
    file = note(tmp_path)
    env = {"LOREKEEP_STORE": str(store_dir)}

    for argv in (
        ["add", str(file), "--title", "Research"],
        ["add", str(file), "--title", "Research", "--tag", "a", "--tag", "b"],
        ["add", str(file), "--tag", "a"],
    ):
        result = run_cli(argv, env=env)

        assert result.exit_code != 0, argv
        assert result.stderr, argv
    assert list(store_dir.iterdir()) == []
