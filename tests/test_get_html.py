"""`get` extracts static HTML when there is no Twin (ticket 04)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from pathlib import Path

import pytest
import trafilatura

from lorekeep.edges import Edges
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    edges_over,
    get,
    make_store,
    rows,
)
from tests.test_helpers import read_version

LESSON = "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name / "body.html").read_bytes()


def link_targets(body: bytes) -> list[str]:
    return re.findall(r"\]\(([^)\s]*)", body.decode("utf-8"))


@pytest.mark.parametrize(
    ("fixture", "page"),
    [
        ("termidy-coordinator-and-subagents.html", f"{LESSON}/"),
        (
            "termidy-effective-prompts.html",
            "https://claude.termidy.com/learn/ccao-f/prompting-task-execution/effective-prompts/",
        ),
        (
            "termidy-ethical-ai.html",
            "https://claude.termidy.com/learn/ccar-p/governance-safety-risk/ethical-ai/",
        ),
        (
            "anthropic-prompt-caching.html",
            "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
        ),
        (
            "aws-prompt-caching.html",
            "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html",
        ),
    ],
)
def test_a_static_html_page_is_stored_as_clean_markdown_with_absolute_links(
    tmp_path: Path, fixture: str, page: str
) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over(fixture)

    result = get(store, edges, page)

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    assert result.stdout.splitlines()[-1] == str(version)
    head, body = read_version(version)
    assert head["converter"] == f"trafilatura {trafilatura.__version__}"
    assert head["sha256"] == hashlib.sha256(body).hexdigest()
    assert len(body) > 5000
    assert b"<div" not in body
    assert b"cookie" not in body.lower()
    links = link_targets(body)
    assert links
    assert all(link.startswith(("https://", "http://")) for link in links), links


def test_the_original_html_is_stored_beside_the_version_with_its_own_hash(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("termidy-coordinator-and-subagents.html")

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    original = version.with_name(f"{version.name.removesuffix('.md')}.orig.html")
    received = fixture_bytes("termidy-coordinator-and-subagents.html")
    assert original.read_bytes() == received
    head, _ = read_version(version)
    assert head["url"] == LESSON
    assert head["original"] == {
        "url": f"{LESSON}/",
        "mediatype": "text/html",
        "sha256": hashlib.sha256(received).hexdigest(),
        "stored": "true",
    }
    assert sorted(path.name for path in store.iterdir()) == sorted(
        [".lorekeep.lock", "tags.csv", version.name, original.name]
    )


NIM_STUB = "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html"
NIM_TARGET = "https://docs.nvidia.com/nim/large-language-models/latest/about-nim-llm/overview.html"


def test_a_meta_refresh_stub_is_followed_and_never_stored(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("nim-introduction.stub", "nim-overview.html")

    result = get(store, edges, NIM_STUB, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [NIM_STUB, NIM_TARGET]
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == NIM_TARGET
    assert head["original"]["url"] == NIM_TARGET
    assert head["etag"] == '"05e0903d68b11fdf4da3d162a0b700ce"'
    assert head["publisher"] == "nvidia"
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (NIM_STUB, NIM_TARGET)
    ]
    assert b"redirect file" not in body
    [original] = store.glob("*.orig.html")
    assert original.read_bytes() == fixture_bytes("nim-overview.html")


LESSON_ALIAS = f"{LESSON}/index.html"


def test_a_page_with_a_canonical_link_is_stored_under_the_canonical_url(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("termidy-coordinator-and-subagents.alias")

    result = get(store, edges, LESSON_ALIAS)

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert head["url"] == LESSON
    assert head["original"]["url"] == LESSON_ALIAS
    assert version.name.startswith("claude.termidy.com--learn-ccar-f-agentic-architecture-")
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (LESSON_ALIAS, LESSON)
    ]


def test_the_alias_fetched_after_the_lesson_adds_its_row_and_no_second_file(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over(
        "termidy-coordinator-and-subagents.html", "termidy-coordinator-and-subagents.alias"
    )
    lesson = get(store, edges, f"{LESSON}/")
    assert lesson.exit_code == 0, lesson.stderr
    [version] = store.glob("*.md")
    assert not (store / "aliases.csv").exists()

    by_alias = get(store, edges, LESSON_ALIAS)

    assert by_alias.exit_code == 0, by_alias.stderr
    assert by_alias.stdout.splitlines()[-1] == str(version)
    assert list(store.glob("*.md")) == [version]
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (LESSON_ALIAS, LESSON)
    ]
    calls = len(transport.requests)

    again = get(store, edges, LESSON_ALIAS)

    assert again.stdout.splitlines()[-1] == str(version)
    assert len(transport.requests) == calls
    assert len(rows(store, "aliases.csv")) == 1


def test_tracking_parameters_and_a_trailing_slash_are_sent_as_given_and_add_no_alias(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    page = "https://claude.termidy.com/learn/ccao-f/prompting-task-execution/effective-prompts"
    asked = f"{page}/?utm_source=newsletter"
    transport = FakeTransport.from_fixtures("termidy-effective-prompts.html")
    transport.fixtures = [replace(f, url=asked) for f in transport.fixtures]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, asked)

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [asked]
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert head["url"] == page
    assert not (store / "aliases.csv").exists()


GOOGLE_PAGE = "https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview"
GOOGLE_TWIN_RULE = (
    '[[hosts]]\nprefix = "cloud.google.com/"\npublisher = "google"\n'
    'authority = "primary"\ntwin = "md-suffix"\n'
)


@pytest.mark.parametrize("asked", [GOOGLE_PAGE, f"{GOOGLE_PAGE}.md"])
def test_a_twin_address_answering_html_is_discarded_and_the_page_is_stored(
    tmp_path: Path, asked: str
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(GOOGLE_TWIN_RULE, encoding="utf-8")
    edges, transport = edges_over("google-md-answers-html", "google-overview.html")

    result = get(store, edges, asked, tag="google")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [
        f"{GOOGLE_PAGE}.md",
        GOOGLE_PAGE,
    ]
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == GOOGLE_PAGE
    assert head["original"]["url"] == GOOGLE_PAGE
    assert head["converter"].startswith("trafilatura ")
    assert b"Vertex AI" in body
    [original] = store.glob("*.orig.html")
    assert original.read_bytes() == fixture_bytes("google-overview.html")
    assert not (store / "aliases.csv").exists()


def test_relative_links_are_resolved_against_the_page_address(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("relative-links.html")

    result = get(store, edges, "https://example.test/guide/sub/page.html")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    _, body = read_version(version)
    assert link_targets(body) == [
        "https://example.test/guide/sub/rel.html",
        "https://example.test/guide/up.html",
        "https://example.test/abs.html",
        "https://cdn.example.test/asset",
    ]


def test_the_media_type_decides_the_step_not_the_url(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = "https://example.test/guide/sub/page.html"
    transport = FakeTransport.from_fixtures("relative-links.html")
    transport.fixtures = [
        replace(f, headers={"content-type": "application/octet-stream"}) for f in transport.fixtures
    ]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, page)

    assert result.exit_code != 0
    assert "application/octet-stream" in result.stderr
    assert list(store.iterdir()) == []
