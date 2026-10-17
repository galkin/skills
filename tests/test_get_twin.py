"""`get` stores the publisher's Twin as a Version (ticket 03)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from lorekeep.edges import Edges
from lorekeep.project import load_project
from lorekeep.store import RecheckRow, commit, latest
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    comparable_url,
    edges_over,
    get,
    make_store,
    rows,
    run_cli,
)
from tests.test_helpers import read_version

ANTHROPIC_PAGE = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
ANTHROPIC_TWIN = f"{ANTHROPIC_PAGE}.md"


def fixture_bytes(name: str, body: str = "body.md") -> bytes:
    return (FIXTURES / name / body).read_bytes()


def test_get_of_the_anthropic_twin_stores_one_version_with_its_provenance(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("anthropic-prompt-caching.twin")

    result = get(store, edges, ANTHROPIC_PAGE)

    assert result.exit_code == 0, result.stderr
    versions = list(store.glob("*.md"))
    assert len(versions) == 1
    assert result.stdout.rstrip("\n").splitlines()[-1] == str(versions[0])
    assert not list(store.glob("*.orig.*"))
    head, body = read_version(versions[0])
    received = fixture_bytes("anthropic-prompt-caching.twin")
    assert body.startswith(b"Prompt caching optimizes")
    assert b"title: Prompt caching" not in body
    assert head["url"] == ANTHROPIC_PAGE
    assert head["sha256"] == hashlib.sha256(body).hexdigest()
    assert versions[0].name.endswith(f"--{head['sha256'][:8]}.md")
    assert versions[0].name.startswith("platform.claude.com--docs-en-build-with-claude-")
    assert head["publisher"] == "anthropic"
    assert head["authority"] == "primary"
    assert head["converter"] == "md-twin"
    assert head["fetched_at"].endswith("Z")
    assert head["etag"] == '"a1-twin"'
    assert head["title"] == "Prompt caching"
    assert head["original"] == {
        "url": ANTHROPIC_TWIN,
        "mediatype": "text/markdown",
        "sha256": hashlib.sha256(received).hexdigest(),
        "stored": "false",
    }


def test_get_json_prints_one_object_with_the_path(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("anthropic-prompt-caching.twin")

    result = get(store, edges, ANTHROPIC_PAGE, "--json")

    assert result.exit_code == 0, result.stderr
    printed = json.loads(result.stdout)
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert printed == {
        "path": str(version),
        "url": ANTHROPIC_PAGE,
        "sha256": head["sha256"],
        "fetched_at": head["fetched_at"],
        "converter": "md-twin",
        "publisher": "anthropic",
        "authority": "primary",
        "verified_at": head["fetched_at"],
        "outcome": "stored",
    }


MS_ASKED = "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry"
MS_CANONICAL = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
MS_CHAIN = ("ms-foundry.redirect-1", "ms-foundry.redirect-2", "ms-foundry.twin")


def test_the_microsoft_chain_is_stored_once_under_its_canonical_url(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over(*MS_CHAIN)

    result = get(store, edges, MS_ASKED, tag="microsoft")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == MS_CANONICAL
    assert version.name.startswith("learn.microsoft.com--en-us-azure-foundry-what-is-foundry--")
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (MS_ASKED, MS_CANONICAL)
    ]
    assert head["original"]["url"] == f"{MS_CANONICAL}?accept=text/markdown"
    assert body.startswith(b"# What is Microsoft Foundry? - Microsoft Foundry | Microsoft Learn")
    assert b"canonicalUrl" not in body
    assert head["title"] == "What is Microsoft Foundry? - Microsoft Foundry | Microsoft Learn"
    assert head["modified"] == "2026-08-13"
    assert head["etag"] == '"RYzzG3LLzfqUX6b79i4xKDnTE/w="'
    assert head["last_modified"] == "Tue, 13 Oct 2026 16:17:35 GMT"
    assert head["publisher"] == "microsoft"
    received = fixture_bytes("ms-foundry.twin")
    assert head["original"]["sha256"] == hashlib.sha256(received).hexdigest()
    assert head["sha256"] == hashlib.sha256(body).hexdigest()


def test_the_aws_twin_is_stored_under_the_page_address_with_its_suffix(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("aws-prompt-caching.twin")
    page = "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"

    result = get(store, edges, page, tag="aws")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == page
    assert head["original"]["url"].endswith("/userguide/prompt-caching.md")
    assert [str(request.url) for request in transport.requests] == [
        "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.md"
    ]
    assert body.startswith(b"# Prompt caching for faster model inference")
    assert "modified" not in head
    assert "last_modified" not in head


def test_the_twin_address_and_the_page_address_find_one_version(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("anthropic-prompt-caching.twin")

    by_twin = get(store, edges, ANTHROPIC_TWIN)
    by_page = get(store, edges, ANTHROPIC_PAGE)

    assert by_twin.exit_code == 0, by_twin.stderr
    assert by_page.exit_code == 0, by_page.stderr
    [version] = store.glob("*.md")
    assert by_twin.stdout.splitlines()[-1] == by_page.stdout.splitlines()[-1] == str(version)
    assert len(transport.requests) == 1
    assert not (store / "aliases.csv").exists()


def test_a_twin_address_that_answers_html_is_not_stored(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "cloud.google.com/"\npublisher = "google"\n'
        'authority = "primary"\ntwin = "md-suffix"\n',
        encoding="utf-8",
    )
    edges, transport = edges_over("google-md-answers-html")
    page = "https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview"

    result = get(store, edges, page, tag="google")

    assert result.exit_code != 0
    assert "no Twin" in result.stderr
    assert [str(request.url) for request in transport.requests] == [f"{page}.md", page]
    assert transport.misses == [page]
    assert sorted(path.name for path in store.iterdir()) == ["lorekeep.toml"]


def test_a_second_get_and_a_get_by_an_alias_make_no_request(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over(*MS_CHAIN)
    first = get(store, edges, MS_ASKED, tag="microsoft")
    assert first.exit_code == 0, first.stderr
    calls = len(transport.requests)
    [version] = store.glob("*.md")

    again = get(store, edges, MS_CANONICAL, tag="microsoft")
    by_alias = get(store, edges, MS_ASKED, tag="microsoft")
    other_run = get(store, edges, f"{MS_ASKED}?accept=text%2Fmarkdown", "--json", tag="azure")

    assert len(transport.requests) == calls
    assert again.stdout.splitlines()[-1] == by_alias.stdout.splitlines()[-1] == str(version)
    assert json.loads(other_run.stdout)["path"] == str(version)
    assert json.loads(other_run.stdout)["outcome"] == "fresh"
    assert [(row["url"], row["tag"]) for row in rows(store, "tags.csv")] == [
        (MS_CANONICAL, "microsoft"),
        (MS_CANONICAL, "azure"),
    ]
    assert len(list(store.glob("*.md"))) == 1


def test_the_old_address_first_used_after_the_page_is_stored_adds_its_alias(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over(*MS_CHAIN)
    canonical = get(store, edges, MS_CANONICAL, tag="microsoft")
    assert canonical.exit_code == 0, canonical.stderr
    assert not (store / "aliases.csv").exists()
    [version] = store.glob("*.md")
    before = len(transport.requests)

    second = get(store, edges, MS_ASKED, tag="microsoft")

    assert second.exit_code == 0, second.stderr
    # One fetch: the Twin address built from the old one, its two redirects, the Twin once.
    assert [comparable_url(str(request.url)) for request in transport.requests[before:]] == [
        f"{MS_ASKED}?accept=text/markdown",
        "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-foundry?accept=text/markdown",
        f"{MS_CANONICAL}?accept=text/markdown",
    ]
    assert second.stdout.splitlines()[-1] == str(version)
    assert list(store.glob("*.md")) == [version]
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (MS_ASKED, MS_CANONICAL)
    ]
    after_second = len(transport.requests)

    third = get(store, edges, MS_ASKED, tag="microsoft")

    assert third.stdout.splitlines()[-1] == str(version)
    assert len(transport.requests) == after_second
    assert len(rows(store, "aliases.csv")) == 1
    # The second call found the Markdown already stored: that is a Recheck, recorded as one.
    head, _ = read_version(version)
    assert [
        (row["url"], row["result"], row["status"], row["sha256"])
        for row in rows(store, "checks.csv")
    ] == [(MS_CANONICAL, "unchanged", "200", head["sha256"])]


def test_an_alias_first_used_when_the_page_changed_makes_the_new_version_current(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    first = get(store, edges_over(*MS_CHAIN)[0], MS_CANONICAL, tag="microsoft")
    assert first.exit_code == 0, first.stderr
    old = Path(first.stdout.splitlines()[-1])
    old_head, _ = read_version(old)
    commit(
        store,
        checks=[
            RecheckRow(MS_CANONICAL, "2026-10-10T00:00:00Z", "unchanged", "304", old_head["sha256"])
        ],
    )
    rewritten = tmp_path / "rewritten.md"
    rewritten.write_text(
        "# What is Microsoft Foundry?\n\nRewritten since the brief.\n", encoding="utf-8"
    )
    transport = FakeTransport.from_fixtures(*MS_CHAIN)
    transport.fixtures = [
        replace(fixture, body=rewritten) if fixture.folder.name == "ms-foundry.twin" else fixture
        for fixture in transport.fixtures
    ]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    by_alias = get(store, edges, MS_ASKED, "--json", tag="microsoft")

    assert by_alias.exit_code == 0, by_alias.stderr
    printed = json.loads(by_alias.stdout)
    new = Path(printed["path"])
    assert new != old and new.parent == store
    assert printed["outcome"] == "changed"
    assert printed["url"] == MS_CANONICAL
    new_head, _ = read_version(new)
    assert [(row["result"], row["status"], row["sha256"]) for row in rows(store, "checks.csv")][
        -1
    ] == (
        "changed",
        "200",
        new_head["sha256"],
    )
    found = latest(store, MS_CANONICAL, load_project(store).hosts)
    assert found is not None and found.path == new
    again = get(store, edges_over()[0], MS_CANONICAL, "--json", tag="microsoft")
    assert json.loads(again.stdout)["path"] == str(new)
    assert json.loads(again.stdout)["outcome"] == "fresh"


def test_get_without_a_tag_exits_before_any_request(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("anthropic-prompt-caching.twin")

    result = run_cli(["get", ANTHROPIC_PAGE], env={"LOREKEEP_STORE": str(store)}, edges=edges)

    assert result.exit_code != 0
    assert "Tag" in result.stderr
    assert transport.requests == []
    assert list(store.iterdir()) == []


def test_an_unknown_host_warns_on_stderr(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over()

    result = get(store, edges, "https://unknown.example/docs/page")

    assert "unknown.example" in result.stderr
    assert "neither host table" in result.stderr
    assert result.stderr.startswith("lorekeep: warning: ")


def test_every_request_names_lorekeep_as_its_user_agent(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over(*MS_CHAIN, "google-md-answers-html")
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "cloud.google.com/"\npublisher = "google"\n'
        'authority = "primary"\ntwin = "md-suffix"\n',
        encoding="utf-8",
    )

    get(store, edges, MS_ASKED)
    get(store, edges, "https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview")

    assert len(transport.requests) == 5
    assert all(
        request.headers["user-agent"].startswith("lorekeep/") for request in transport.requests
    )
