"""`status`: the shape of a Store from its Index, in text and as one JSON object (ticket 11)."""

from __future__ import annotations

import json
from pathlib import Path

from lorekeep.edges import BROWSER_INSTALL, Edges
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    run_cli,
    write_version,
)

NIM_OVERVIEW = (
    "https://docs.nvidia.com/nim/large-language-models/latest/about-nim-llm/overview.html"
)
NIM_INTRODUCTION = "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html"
AWS = "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"
GOOGLE = "https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview"


def mixed_store(store: Path) -> None:
    """Six Versions of five Sources: two hosts no rule knows (publisher equal to the host), one
    known publisher, one owner's note; three Tags; a `checks.csv` of every outcome."""
    write_version(store, FIXTURES / "nim-overview.html", fetched_at="2026-08-01T00:00:00Z")
    write_version(
        store,
        FIXTURES / "nim-introduction.stub",
        fetched_at="2026-08-02T00:00:00Z",
        url=NIM_OVERVIEW,
    )
    write_version(store, FIXTURES / "nim-introduction.stub", fetched_at="2026-08-03T00:00:00Z")
    write_version(
        store,
        FIXTURES / "aws-prompt-caching.html",
        fetched_at="2026-08-04T09:30:00Z",
        publisher="aws",
        authority="primary",
    )
    write_version(store, FIXTURES / "google-overview.html", fetched_at="2026-08-03T12:00:00Z")
    write_version(
        store,
        FIXTURES / "termidy-effective-prompts.html",
        fetched_at="2026-07-15T08:00:00Z",
        url="owner:research-notes",
        publisher="claude",
        authority="generated",
        origin="owner",
    )
    (store / "tags.csv").write_text(
        "url,tag,added_at\n"
        f"{NIM_OVERVIEW},nvidia,2026-08-01T00:00:00Z\n"
        f"{NIM_INTRODUCTION},nvidia,2026-08-03T00:00:00Z\n"
        f"{AWS},aws,2026-08-04T09:30:00Z\n"
        f"{GOOGLE},google,2026-08-03T12:00:00Z\n"
        "owner:research-notes,anthropic,2026-07-15T08:00:00Z\n"
        f"{AWS},anthropic,2026-08-05T00:00:00Z\n"
    )
    (store / "checks.csv").write_text(
        "url,checked_at,result,status,sha256\n"
        f"{NIM_OVERVIEW},2026-08-10T00:00:00Z,unchanged,304,\n"
        f"{AWS},2026-08-10T00:00:00Z,unchanged,304,\n"
        f"{NIM_OVERVIEW},2026-08-11T00:00:00Z,changed,200,\n"
        f"{NIM_INTRODUCTION},2026-08-11T00:00:00Z,gone,404,\n"
        f"{GOOGLE},2026-08-11T00:00:00Z,error,ReadTimeout,\n"
        f"{AWS},2026-08-12T00:00:00Z,unchanged,304,\n"
    )


def store_bytes(store: Path) -> int:
    return sum(path.stat().st_size for path in store.iterdir() if path.is_file())


def test_status_json_is_one_object_in_the_spec_shape(tmp_path: Path) -> None:
    mixed_store(tmp_path)

    result = run_cli(["status", "--json", "--store", str(tmp_path)])

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout) == {
        "versions": 6,
        "sources": 5,
        "tags": {"anthropic": 2, "aws": 1, "google": 1, "nvidia": 2},
        "oldest_fetched_at": "2026-07-15T08:00:00Z",
        "newest_fetched_at": "2026-08-04T09:30:00Z",
        "checks": {"unchanged": 3, "changed": 1, "gone": 1, "error": 1},
        "unknown_hosts": ["cloud.google.com", "docs.nvidia.com"],
        "readings": 0,
        "rules": 6,
        "bytes": store_bytes(tmp_path),
        "browser": {"ready": True, "crawl4ai": "0.9.5", "detail": "Chromium starts", "fix": None},
    }


def test_status_prints_every_figure_as_text(tmp_path: Path) -> None:
    mixed_store(tmp_path)

    result = run_cli(["status", "--store", str(tmp_path)])

    assert result.exit_code == 0, result.stderr
    lines = result.stdout.splitlines()
    assert "6 Versions of 5 Sources" in lines
    assert "Tags: anthropic 2, aws 1, google 1, nvidia 2" in lines
    assert "Oldest fetched_at: 2026-07-15T08:00:00Z" in lines
    assert "Newest fetched_at: 2026-08-04T09:30:00Z" in lines
    assert "Rechecks: 3 unchanged, 1 changed, 1 gone, 1 error" in lines
    assert "Unknown hosts: cloud.google.com, docs.nvidia.com" in lines
    assert f"Size on disk: {store_bytes(tmp_path)} bytes" in lines
    assert "Browser: ready (Crawl4AI 0.9.5)" in lines


def test_status_on_a_store_without_an_index_builds_it_first(tmp_path: Path) -> None:
    mixed_store(tmp_path)
    assert not (tmp_path / "sources.db").exists()

    result = run_cli(["status", "--json", "--store", str(tmp_path)])

    assert result.exit_code == 0, result.stderr
    assert (tmp_path / "sources.db").is_file()
    assert json.loads(result.stdout)["versions"] == 6
    assert (tmp_path / ".lorekeep.lock").exists()


def test_status_sees_a_version_copied_in_after_the_index_was_built(tmp_path: Path) -> None:
    mixed_store(tmp_path)
    assert run_cli(["index", "--store", str(tmp_path)]).exit_code == 0
    write_version(tmp_path, FIXTURES / "termidy-ethical-ai.html", fetched_at="2026-09-01T00:00:00Z")

    result = run_cli(["status", "--json", "--store", str(tmp_path)])

    found = json.loads(result.stdout)
    assert (found["versions"], found["sources"]) == (7, 6)
    assert found["newest_fetched_at"] == "2026-09-01T00:00:00Z"
    assert "claude.termidy.com" in found["unknown_hosts"]


def test_status_of_an_empty_store_has_no_fetch_times(tmp_path: Path) -> None:
    result = run_cli(["status", "--json", "--store", str(tmp_path)])

    found = json.loads(result.stdout)
    assert found["versions"] == 0
    assert found["oldest_fetched_at"] is None
    assert found["checks"] == {"unchanged": 0, "changed": 0, "gone": 0, "error": 0}
    assert found["tags"] == {}


def browser_of(tmp_path: Path, fetcher: FakeFetcher) -> tuple[str, dict[str, object]]:
    """The `Browser:` line and the JSON `browser` object `status` prints with this browser."""
    edges = Edges(transport=FakeTransport.from_fixtures(), fetcher=fetcher, runner=FakeRunner())
    text = run_cli(["status", "--store", str(tmp_path)], edges=edges).stdout.splitlines()
    found = json.loads(run_cli(["status", "--json", "--store", str(tmp_path)], edges=edges).stdout)
    return next(line for line in text if line.startswith("Browser: ")), found["browser"]


def test_status_names_the_extra_when_crawl4ai_is_not_installed(tmp_path: Path) -> None:
    line, browser = browser_of(tmp_path, FakeFetcher(installed=False))

    assert line == f"Browser: not ready: Crawl4AI is not installed; fix: {BROWSER_INSTALL}"
    assert browser["ready"] is False
    assert browser["crawl4ai"] is None


def test_status_gives_the_command_that_installs_chromium_when_it_cannot_start(
    tmp_path: Path,
) -> None:
    line, browser = browser_of(tmp_path, FakeFetcher(chromium=False))

    assert line.startswith("Browser: not ready: Chromium cannot start: ")
    assert line.endswith("; fix: python -m playwright install chromium")
    assert (browser["ready"], browser["crawl4ai"]) == (False, "0.9.5")
    assert browser["fix"] == "python -m playwright install chromium"
