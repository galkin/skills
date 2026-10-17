"""A `.md` file in the Store that is not a Version is ignored with one warning (ticket 08)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tests.support import FIXTURES, edges_over, lorekeep, make_store, write_version
from tests.test_index import ANTHROPIC, result_lines

WARNING = "lorekeep: warning: note.md: not a Version (no frontmatter), ignored"


def stray_note(store: Path) -> Path:
    """A note the owner dropped into the Store root, and then added as an owner's Source."""
    note = store / "note.md"
    note.write_text("# Zebra notes\n\nThe zebra paragraph the owner wrote.\n", encoding="utf-8")
    edges, _ = edges_over()
    added = lorekeep(store, edges, "add", str(note), "--title", "zebra", tag="t")
    assert added.exit_code == 0, added.stderr
    return Path(added.stdout.strip())


def test_search_ignores_a_stray_md_file_with_one_warning_and_finds_the_added_version(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    version = stray_note(store)
    edges, _ = edges_over()

    result = lorekeep(store, edges, "search", "zebra", tag="t")

    assert result.exit_code == 0, result.stderr
    assert result.stderr.count(WARNING) == 1, result.stderr
    assert "Traceback" not in result.stderr
    lines = result_lines(result.stdout)
    assert len(lines) == 1
    assert lines[0].startswith(f"{version}:")


REBUILT = "the Index was missing or stale and was rebuilt"


def test_a_stray_md_file_rebuilds_the_index_at_most_once_even_across_commits(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    stray_note(store)
    edges, _ = edges_over()
    first = lorekeep(store, edges, "search", "zebra", tag="t")
    assert REBUILT in first.stderr
    other = tmp_path / "other.md"
    other.write_text("# Okapi\n\nThe okapi paragraph.\n", encoding="utf-8")
    added = lorekeep(store, edges, "add", str(other), "--title", "okapi", tag="t")
    assert added.exit_code == 0, added.stderr

    second = lorekeep(store, edges, "search", "okapi", tag="t")

    assert second.exit_code == 0, second.stderr
    assert REBUILT not in second.stderr, "a commit left the Index stale because of note.md"
    assert len(result_lines(second.stdout)) == 1


def test_index_counts_only_versions_and_names_the_stray_file_once(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    stray_note(store)
    edges, _ = edges_over()

    result = lorekeep(store, edges, "index")

    assert result.exit_code == 0, result.stderr
    assert result.stderr.count(WARNING) == 1, result.stderr
    assert "Indexed 1 Version," in result.stdout


def test_status_counts_neither_a_version_nor_a_host_for_the_stray_file(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    write_version(store, FIXTURES / "aws-prompt-caching.twin", fetched_at="2026-10-02T00:00:00Z")
    (store / "note.md").write_text("# A note\n\nNot a Version.\n", encoding="utf-8")
    edges, _ = edges_over()

    result = lorekeep(store, edges, "status", "--json")

    assert result.exit_code == 0, result.stderr
    assert result.stderr.count(WARNING) == 1, result.stderr
    found = json.loads(result.stdout)
    assert (found["versions"], found["sources"]) == (1, 1)
    assert found["unknown_hosts"] == ["docs.aws.amazon.com"]


def test_get_without_an_index_finds_the_stored_version_past_the_stray_file(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    stored = write_version(
        store, FIXTURES / "anthropic-prompt-caching.twin", fetched_at=now(), url=ANTHROPIC
    )
    (store / "note.md").write_text("# A note\n\nNot a Version.\n", encoding="utf-8")
    edges, transport = edges_over()

    result = lorekeep(store, edges, "get", ANTHROPIC, tag="t")

    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == str(stored)
    assert result.stderr.count(WARNING) == 1, result.stderr
    assert transport.requests == []


def test_a_md_file_whose_frontmatter_is_not_a_version_s_is_ignored_too(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    write_version(store, FIXTURES / "aws-prompt-caching.twin", fetched_at="2026-10-02T00:00:00Z")
    (store / "jekyll.md").write_text("---\ntitle: My page\n---\n# Hello\n", encoding="utf-8")
    edges, _ = edges_over()

    result = lorekeep(store, edges, "status", "--json")

    assert result.exit_code == 0, result.stderr
    warning = "lorekeep: warning: jekyll.md: not a Version (no url in the frontmatter), ignored"
    assert warning in result.stderr
    assert json.loads(result.stdout)["versions"] == 1


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
