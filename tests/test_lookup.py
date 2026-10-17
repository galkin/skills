"""The lookup of a URL's latest Version without an Index: a scan of every frontmatter."""

from __future__ import annotations

from pathlib import Path

from lorekeep.project import load_project
from lorekeep.store import AliasRow, CheckRow, commit, latest
from tests.support import FIXTURES, write_version

PAGE = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
OLD_ADDRESS = "https://learn.microsoft.com/en-us/azure/ai-studio/what-is-ai-studio"


def test_the_newest_version_is_found_by_url_and_by_alias_and_nothing_for_an_unknown_url(
    tmp_path: Path,
) -> None:
    rules = load_project(tmp_path).hosts
    older = write_version(
        tmp_path, FIXTURES / "ms-foundry.twin", fetched_at="2026-09-01T00:00:00Z", url=PAGE
    )
    newer = write_version(
        tmp_path,
        FIXTURES / "anthropic-prompt-caching.twin",
        fetched_at="2026-10-01T00:00:00Z",
        url=PAGE,
    )
    write_version(tmp_path, FIXTURES / "aws-prompt-caching.twin", fetched_at="2026-10-05T00:00:00Z")
    commit(
        tmp_path, aliases=[AliasRow(alias=OLD_ADDRESS, url=PAGE, added_at="2026-10-01T00:00:00Z")]
    )
    assert older != newer

    by_url = latest(tmp_path, PAGE + "?accept=text/markdown#top", rules)
    by_alias = latest(tmp_path, OLD_ADDRESS + "/", rules)
    unknown = latest(tmp_path, "https://learn.microsoft.com/en-us/nowhere", rules)

    assert by_url is not None and by_url.path == newer
    assert by_url.url == PAGE
    assert by_url.fetched_at == "2026-10-01T00:00:00Z"
    assert by_alias is not None and by_alias.path == newer
    assert unknown is None


def test_the_version_named_by_the_latest_check_row_wins_over_the_newest_fetched_at(
    tmp_path: Path,
) -> None:
    rules = load_project(tmp_path).hosts
    a = write_version(
        tmp_path, FIXTURES / "ms-foundry.twin", fetched_at="2026-09-01T00:00:00Z", url=PAGE
    )
    b = write_version(
        tmp_path,
        FIXTURES / "anthropic-prompt-caching.twin",
        fetched_at="2026-10-01T00:00:00Z",
        url=PAGE,
    )
    a_hash = a.name.rsplit("--", 1)[1].removesuffix(".md")
    assert latest(tmp_path, PAGE, rules) is not None
    assert latest(tmp_path, PAGE, rules).path == b  # type: ignore[union-attr]

    commit(
        tmp_path,
        checks=[
            CheckRow(PAGE, "2026-10-02T00:00:00Z", "unchanged", "304", full_hash(b)),
            CheckRow(PAGE, "2026-10-09T00:00:00Z", "changed", "200", full_hash(a)),
        ],
    )

    found = latest(tmp_path, PAGE, rules)
    assert found is not None
    assert found.path == a
    assert found.sha256.startswith(a_hash)


def full_hash(version: Path) -> str:
    import yaml

    head = version.read_bytes()[4:].split(b"\n---\n", 1)[0]
    return yaml.load(head.decode(), Loader=yaml.BaseLoader)["sha256"]
