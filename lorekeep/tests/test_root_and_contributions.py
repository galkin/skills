"""Host rules at a site's root and on GitHub contributions: `https://agents.md` is under its
`agents.md/` rule, and an issue under a primary repository rule is third-party."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lorekeep.project import HostRule, load_project
from lorekeep.provenance import now
from lorekeep.urls import host_path, trust
from tests.support import FIXTURES, edges_over, get, lorekeep, make_store, write_version

AGENTS_MD = '[[hosts]]\nprefix = "agents.md/"\npublisher = "agents.md"\nauthority = "primary"\n'
REPO = (
    '[[hosts]]\nprefix = "github.com/acme/kit/"\npublisher = "acme"\nauthority = "primary"\n'
    '[[hosts]]\nprefix = "github.com/acme/"\npublisher = "acme"\nauthority = "primary"\n'
)
ISSUE = "https://github.com/acme/kit/issues/12"


def rules_of(tmp_path: Path, toml: str) -> tuple[HostRule, ...]:
    (tmp_path / "lorekeep.toml").write_text(toml, encoding="utf-8")
    return load_project(tmp_path).hosts


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://Agents.MD", "agents.md/"),
        ("https://agents.md/", "agents.md/"),
        ("https://agents.md//faq", "agents.md/faq"),
    ],
)
def test_a_root_s_empty_path_is_matched_as_a_slash(url: str, expected: str) -> None:
    assert host_path(url) == expected


def test_a_site_s_home_page_is_under_its_own_host_rule(tmp_path: Path) -> None:
    found = trust("https://agents.md", rules_of(tmp_path, AGENTS_MD))

    assert (found.publisher, found.authority, found.warning) == ("agents.md", "primary", None)


@pytest.mark.parametrize(
    "url",
    [
        ISSUE,
        "https://github.com/acme/kit/issues",
        "https://github.com/acme/kit/discussions/5",
        "https://github.com/acme/kit/pull/7/files",
        "https://github.com/acme/kit/pulls",
        "https://github.com/orgs/acme/discussions/3",
    ],
)
def test_a_github_contribution_is_third_party_under_the_repository_s_publisher(
    tmp_path: Path, url: str
) -> None:
    found = trust(url, rules_of(tmp_path, REPO))

    assert (found.publisher, found.authority) == ("acme", "third-party")
    assert found.note is not None and "GitHub" in found.note


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/acme/kit",
        "https://github.com/acme/kit/blob/main/README.md",
        "https://github.com/acme/kit/issues-guide",
        "https://github.com/acme/kit/wiki/pull",
        "https://github.com/acme/kit/pullsx",
    ],
)
def test_the_repository_s_own_pages_keep_its_rule(tmp_path: Path, url: str) -> None:
    found = trust(url, rules_of(tmp_path, REPO))

    assert (found.publisher, found.authority, found.note) == ("acme", "primary", None)


def test_a_rule_naming_the_contribution_prefix_decides_it(tmp_path: Path) -> None:
    rules = rules_of(
        tmp_path,
        REPO + '[[hosts]]\nprefix = "github.com/acme/kit/issues/"\n'
        'publisher = "acme"\nauthority = "primary"\n',
    )

    assert trust(ISSUE, rules).authority == "primary"
    assert trust("https://github.com/acme/kit/pull/7", rules).authority == "third-party"


def test_a_contribution_under_no_owner_rule_keeps_the_catch_all(tmp_path: Path) -> None:
    found = trust("https://github.com/orgs/other/discussions/3", rules_of(tmp_path, REPO))

    assert (found.publisher, found.authority) == ("github", "third-party")
    assert found.note is not None and "github.com/ rule" in found.note


def test_get_json_stores_a_home_page_under_its_host_rule(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(AGENTS_MD, encoding="utf-8")
    edges, _ = edges_over("agents-md-home.html")

    result = get(store, edges, "--json", "https://agents.md")

    assert result.exit_code == 0, result.stderr
    found = json.loads(result.stdout)
    assert (found["url"], found["publisher"], found["authority"]) == (
        "https://agents.md",
        "agents.md",
        "primary",
    )
    assert "in no host table" not in result.stderr


def test_get_json_judges_a_stored_issue_third_party_under_a_primary_repository_rule(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(REPO, encoding="utf-8")
    write_version(store, FIXTURES / "helm-rollback.html", fetched_at=now(), url=ISSUE, origin="web")
    (store / "tags.csv").write_text(f"url,tag,added_at\n{ISSUE},specs,{now()}\n", encoding="utf-8")
    edges, _ = edges_over()

    result = get(store, edges, "--json", "--max-age", "9999", ISSUE, tag="specs")

    assert result.exit_code == 0, result.stderr
    found = json.loads(result.stdout)
    assert (found["publisher"], found["authority"]) == ("acme", "third-party")


def test_tag_add_prefix_reaches_the_home_page_stored_without_its_slash(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    write_version(
        store,
        FIXTURES / "agents-md-home.html",
        fetched_at=now(),
        url="https://agents.md",
        origin="web",
    )
    edges, _ = edges_over()

    result = lorekeep(store, edges, "tag", "add", "specs", "--prefix", "https://agents.md/")

    assert result.exit_code == 0, result.stderr
    assert "https://agents.md,specs," in (store / "tags.csv").read_text(encoding="utf-8")
