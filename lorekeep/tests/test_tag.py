"""`tag add`: the owner tags stored Sources, one by url or every one under a prefix (ticket 11)."""

from __future__ import annotations

import csv
from pathlib import Path

from tests.support import FIXTURES, run_cli, write_version
from tests.test_staleness import search_while_locked

NIM_OVERVIEW = (
    "https://docs.nvidia.com/nim/large-language-models/latest/about-nim-llm/overview.html"
)
NIM_INTRODUCTION = "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html"
AWS = "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"


def tag_rows(store: Path) -> list[tuple[str, str]]:
    path = store / "tags.csv"
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [(row["url"], row["tag"]) for row in csv.DictReader(handle)]


def three_sources(store: Path) -> None:
    """Two NVIDIA Sources (one of them in two Versions) and one AWS Source, untagged."""
    write_version(store, FIXTURES / "nim-overview.html", fetched_at="2026-08-01T00:00:00Z")
    write_version(
        store,
        FIXTURES / "nim-introduction.stub",
        fetched_at="2026-08-02T00:00:00Z",
        url=NIM_OVERVIEW,
    )
    write_version(store, FIXTURES / "nim-introduction.stub", fetched_at="2026-08-03T00:00:00Z")
    write_version(store, FIXTURES / "aws-prompt-caching.html", fetched_at="2026-08-04T00:00:00Z")


def test_tag_add_with_a_prefix_tags_every_source_under_it_once(tmp_path: Path) -> None:
    three_sources(tmp_path)

    result = run_cli(
        ["tag", "add", "nvidia", "--prefix", "https://docs.nvidia.com/"],
        env={"LOREKEEP_STORE": str(tmp_path)},
    )

    assert result.exit_code == 0, result.stderr
    assert sorted(tag_rows(tmp_path)) == [
        (NIM_OVERVIEW, "nvidia"),
        (NIM_INTRODUCTION, "nvidia"),
    ]
    assert "Tagged 2 Sources" in result.stdout


def test_tag_add_run_again_adds_nothing(tmp_path: Path) -> None:
    three_sources(tmp_path)
    argv = [
        "tag",
        "add",
        "nvidia",
        "--prefix",
        "https://docs.nvidia.com/",
        "--store",
        str(tmp_path),
    ]
    run_cli(argv)
    before = (tmp_path / "tags.csv").read_bytes()

    result = run_cli(argv)

    assert result.exit_code == 0, result.stderr
    assert (tmp_path / "tags.csv").read_bytes() == before
    assert "Tagged 0 Sources nvidia; 2 already carried it" in result.stdout


def test_tag_add_without_a_prefix_tags_only_the_exact_url(tmp_path: Path) -> None:
    three_sources(tmp_path)

    result = run_cli(["tag", "add", "nvidia", NIM_INTRODUCTION, "--store", str(tmp_path)])

    assert result.exit_code == 0, result.stderr
    assert tag_rows(tmp_path) == [(NIM_INTRODUCTION, "nvidia")]


def test_tag_add_finds_a_source_by_its_url_as_a_request_would_give_it(tmp_path: Path) -> None:
    three_sources(tmp_path)

    result = run_cli(
        [
            "tag",
            "add",
            "aws",
            AWS.replace("docs.aws", "DOCS.AWS") + "#top",
            "--store",
            str(tmp_path),
        ]
    )

    assert result.exit_code == 0, result.stderr
    assert tag_rows(tmp_path) == [(AWS, "aws")]


def test_tag_add_of_a_url_no_source_has_fails_and_writes_nothing(tmp_path: Path) -> None:
    three_sources(tmp_path)

    result = run_cli(
        ["tag", "add", "nvidia", "https://docs.nvidia.com/nope", "--store", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "https://docs.nvidia.com/nope" in result.stderr
    assert not (tmp_path / "tags.csv").exists()


def test_tag_add_of_a_prefix_no_source_has_fails(tmp_path: Path) -> None:
    three_sources(tmp_path)

    result = run_cli(
        ["tag", "add", "x", "--prefix", "https://nowhere.test/", "--store", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "https://nowhere.test/" in result.stderr
    assert not (tmp_path / "tags.csv").exists()


def test_tag_add_takes_a_url_or_a_prefix_but_not_both_or_neither(tmp_path: Path) -> None:
    three_sources(tmp_path)
    store = ["--store", str(tmp_path)]

    for argv in (
        ["tag", "add", "nvidia", *store],
        ["tag", "add", "nvidia", NIM_INTRODUCTION, "--prefix", "https://docs.nvidia.com/", *store],
    ):
        result = run_cli(argv)
        assert result.exit_code == 2, argv
        assert len(result.stderr.strip().splitlines()) == 1, argv
    assert not (tmp_path / "tags.csv").exists()


def test_tag_add_without_an_index_reads_the_store_and_builds_none(tmp_path: Path) -> None:
    three_sources(tmp_path)
    assert not (tmp_path / "sources.db").exists()

    by_prefix = run_cli(
        ["tag", "add", "nvidia", "--prefix", "https://docs.nvidia.com/", "--store", str(tmp_path)]
    )
    by_url = run_cli(["tag", "add", "aws", AWS, "--store", str(tmp_path)])

    assert by_prefix.exit_code == 0, by_prefix.stderr
    assert by_url.exit_code == 0, by_url.stderr
    assert "rebuilt" not in by_prefix.stderr + by_url.stderr
    assert not (tmp_path / "sources.db").exists(), "tag add built an Index: a second lock take"
    assert sorted(tag_rows(tmp_path)) == [
        (AWS, "aws"),
        (NIM_OVERVIEW, "nvidia"),
        (NIM_INTRODUCTION, "nvidia"),
    ]


def test_a_tag_added_is_in_the_search_scope_without_a_rebuild(tmp_path: Path) -> None:
    three_sources(tmp_path)
    assert run_cli(["index", "--store", str(tmp_path)]).exit_code == 0
    assert run_cli(["tag", "add", "aws", AWS, "--store", str(tmp_path)]).exit_code == 0

    finished, result = search_while_locked(tmp_path, "caching", "--tag", "aws", "--json")

    assert finished, "search waited for the lock: tag add left the Index stale"
    assert result.exit_code == 0, result.stderr
    assert '"url": "' + AWS + '"' in result.stdout
