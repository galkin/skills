"""`recheck` asks publishers what changed; `--citations` names the works to revisit (ticket 09)."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from lorekeep.edges import Edges
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    Result,
    age_version,
    run_cli,
    write_version,
)

ANTHROPIC_PAGE = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
ANTHROPIC_TWIN = f"{ANTHROPIC_PAGE}.md"
LESSONS = "https://claude.termidy.com/learn"
ETHICAL_AI = f"{LESSONS}/ccar-p/governance-safety-risk/ethical-ai"
COORDINATOR = f"{LESSONS}/ccar-f/agentic-architecture/coordinator-and-subagents"
EFFECTIVE_PROMPTS = f"{LESSONS}/ccao-f/prompting-task-execution/effective-prompts"
BROWSER_PAGE = "https://example.test/app"


def make_store(tmp_path: Path) -> Path:
    path = tmp_path / "store"
    path.mkdir()
    return path


def edges_over(*fixtures: str) -> tuple[Edges, FakeTransport]:
    transport = FakeTransport.from_fixtures(*fixtures)
    return Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner()), transport


def lorekeep(store: Path, edges: Edges, *argv: str, tag: str | None = None) -> Result:
    env = {"LOREKEEP_STORE": str(store)}
    if tag is not None:
        env["LOREKEEP_TAG"] = tag
    return run_cli(list(argv), env=env, edges=edges)


def get(store: Path, url: str, fixture: str, *, tag: str) -> None:
    """A real `get` of `url`, aged by the helper so any window would have it rechecked."""
    edges, _ = edges_over(fixture)
    before = set(store.glob("*.md"))
    result = lorekeep(store, edges, "get", url, tag=tag)
    assert result.exit_code == 0, result.stderr
    [version] = set(store.glob("*.md")) - before
    age_version(version, days=40)


def checks_rows(store: Path) -> list[dict[str, str]]:
    path = store / "checks.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mixed_store(tmp_path: Path) -> Path:
    """Four real `get`s under two Tags, one owner's Source and one Version read by a browser."""
    store = make_store(tmp_path)
    get(store, ANTHROPIC_PAGE, "anthropic-prompt-caching.twin", tag="anthropic")
    get(store, f"{ETHICAL_AI}/", "termidy-ethical-ai.html", tag="termidy")
    get(store, f"{COORDINATOR}/", "termidy-coordinator-and-subagents.html", tag="termidy")
    get(store, f"{EFFECTIVE_PROMPTS}/", "termidy-effective-prompts.html", tag="termidy")
    research = tmp_path / "research.md"
    research.write_text("# Research\n\nPasted from a chat.\n", encoding="utf-8")
    edges, _ = edges_over()
    added = lorekeep(store, edges, "add", str(research), "--title", "Research", tag="anthropic")
    assert added.exit_code == 0, added.stderr
    write_version(
        store,
        FIXTURES / "js-only.html",
        fetched_at="2026-08-01T00:00:00Z",
        converter="trafilatura 2.0.0 via crawl4ai 0.9.5",
    )
    return store


# The publishers' answers now: a `304` for the Twin, the same bytes for `ethical-ai`, a changed
# `<h1>` for `coordinator-and-subagents`; `effective-prompts` has no fixture, so it is a `404`.
NOW = (
    "anthropic-prompt-caching.304",
    "anthropic-prompt-caching.twin",
    "termidy-ethical-ai.html",
    "termidy-coordinator-and-subagents.changed",
)


def test_recheck_records_every_answer_stores_the_change_and_counts_the_skipped(
    tmp_path: Path,
) -> None:
    store = mixed_store(tmp_path)
    versions_before = set(store.glob("*.md"))
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck")

    assert result.exit_code == 0, result.stderr
    rows = checks_rows(store)
    assert sorted((row["url"], row["result"], row["status"]) for row in rows) == [
        (EFFECTIVE_PROMPTS, "gone", "404"),
        (COORDINATOR, "changed", "200"),
        (ETHICAL_AI, "unchanged", "200"),
        (ANTHROPIC_PAGE, "unchanged", "304"),
    ]
    [new] = set(store.glob("*.md")) - versions_before
    assert new.name.startswith("claude.termidy.com--learn-ccar-f-agentic-architecture-")
    assert [row["sha256"][:8] for row in rows if row["result"] == "changed"] == [
        new.name.removesuffix(".md")[-8:]
    ]
    assert len(transport.requests) == 4
    assert result.stdout.splitlines()[-1] == (
        "Rechecked 6 Sources: 2 unchanged, 1 changed, 1 gone, 0 error, 2 skipped"
    )
    assert f"{EFFECTIVE_PROMPTS}" in result.stderr


def changed_store(tmp_path: Path) -> tuple[Path, str, str]:
    """`coordinator-and-subagents` fetched, then rechecked as changed; `ethical-ai` rechecked
    unchanged. Returns the Store and the old and new sha256 of the lesson that changed."""
    store = mixed_store(tmp_path)
    edges, _ = edges_over(*NOW)
    assert lorekeep(store, edges, "recheck").exit_code == 0
    [changed] = [row for row in checks_rows(store) if row["result"] == "changed"]
    [old] = [
        path
        for path in store.glob("claude.termidy.com--learn-ccar-f-*.md")
        if not path.name.endswith(f"{changed['sha256'][:8]}.md")
    ]
    return store, old.name.removesuffix(".md")[-8:], changed["sha256"][:8]


def write_citations(store: Path, text: str) -> None:
    (store / "citations.csv").write_text(text, encoding="utf-8")


def test_citations_makes_no_request_and_needs_no_tag(tmp_path: Path) -> None:
    store, old, new = changed_store(tmp_path)
    write_citations(store, f"work_id,url\nlesson-1,{COORDINATOR}/\n")
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", "--citations")

    assert result.exit_code == 0, result.stderr
    assert transport.requests == []
    assert result.stdout.splitlines() == [f"lesson-1, {COORDINATOR}, {old} → {new}"]


def test_citations_lists_only_works_whose_source_changed_after_as_of(tmp_path: Path) -> None:
    store, old, new = changed_store(tmp_path)
    write_citations(
        store,
        "work_id,url,as_of\n"
        f"written-before,{COORDINATOR},2026-09-01\n"
        f"written-after,{COORDINATOR},2099-01-01T00:00:00Z\n"
        f"no-as-of,{COORDINATOR},\n"
        f"unchanged-source,{ETHICAL_AI},2026-09-01\n"
        f"gone-source,{EFFECTIVE_PROMPTS}\n",
    )
    edges, transport = edges_over()

    result = lorekeep(store, edges, "recheck", "--citations", tag="termidy")

    assert result.exit_code == 0, result.stderr
    assert transport.requests == []
    assert result.stdout.splitlines() == [
        f"no-as-of, {COORDINATOR}, {old} → {new}",
        f"written-before, {COORDINATOR}, {old} → {new}",
    ]


def test_citations_against_a_page_that_went_a_b_a_lists_nothing(tmp_path: Path) -> None:
    store, _, _ = changed_store(tmp_path)
    back, _ = edges_over("termidy-coordinator-and-subagents.html")
    reverted = lorekeep(store, back, "get", f"{COORDINATOR}/", "--fresh", tag="termidy")
    assert reverted.exit_code == 0, reverted.stderr
    write_citations(store, f"work_id,url\nlesson-1,{COORDINATOR}\n")

    result = lorekeep(store, back, "recheck", "--citations")

    assert result.exit_code == 0, result.stderr
    assert result.stdout == ""


MS_ASKED = "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry"
MS_CANONICAL = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
MS_CHAIN = ("ms-foundry.redirect-1", "ms-foundry.redirect-2", "ms-foundry.twin")


def test_a_citation_of_an_alias_is_measured_against_the_source_it_leads_to(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = lorekeep(store, edges_over(*MS_CHAIN)[0], "get", MS_ASKED, tag="microsoft")
    assert first.exit_code == 0, first.stderr
    old = Path(first.stdout.splitlines()[-1]).name.removesuffix(".md")[-8:]
    rewritten = tmp_path / "rewritten.md"
    rewritten.write_text("# What is Microsoft Foundry?\n\nRewritten since.\n", encoding="utf-8")
    transport = FakeTransport.from_fixtures(*MS_CHAIN)
    transport.fixtures = [
        replace(fixture, body=rewritten) if fixture.folder.name == "ms-foundry.twin" else fixture
        for fixture in transport.fixtures
    ]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())
    second = lorekeep(store, edges, "get", MS_CANONICAL, "--fresh", tag="microsoft")
    assert second.exit_code == 0, second.stderr
    new = Path(second.stdout.splitlines()[-1]).name.removesuffix(".md")[-8:]
    assert new != old
    write_citations(store, f"work_id,url\nguide-1,{MS_ASKED}\n")

    result = lorekeep(store, edges_over()[0], "recheck", "--citations")

    assert result.exit_code == 0, result.stderr
    assert "warning" not in result.stderr
    assert result.stdout.splitlines() == [f"guide-1, {MS_CANONICAL}, {old} → {new}"]


def asked(transport: FakeTransport) -> list[str]:
    return sorted(str(request.url) for request in transport.requests)


TERMIDY_ASKED = sorted([f"{EFFECTIVE_PROMPTS}/", f"{COORDINATOR}/", f"{ETHICAL_AI}/"])


def test_without_a_tag_every_web_source_is_asked(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck")

    assert result.exit_code == 0, result.stderr
    assert asked(transport) == sorted([ANTHROPIC_TWIN, *TERMIDY_ASKED])


def test_the_runs_tag_is_the_default_scope(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", tag="anthropic")

    assert result.exit_code == 0, result.stderr
    assert asked(transport) == [ANTHROPIC_TWIN]
    assert result.stdout.splitlines()[-1] == (
        "Rechecked 2 Sources: 1 unchanged, 0 changed, 0 gone, 0 error, 1 skipped"
    )


def test_tag_flags_replace_the_runs_tag_and_repeat(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", "--tag", "termidy", tag="anthropic")

    assert result.exit_code == 0, result.stderr
    assert asked(transport) == TERMIDY_ASKED

    edges, transport = edges_over(*NOW)
    both = lorekeep(store, edges, "recheck", "--tag", "termidy", "--tag", "anthropic")
    assert both.exit_code == 0, both.stderr
    assert asked(transport) == sorted([ANTHROPIC_TWIN, *TERMIDY_ASKED])


def test_publisher_limits_the_sources_asked(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", "--publisher", "anthropic")

    assert result.exit_code == 0, result.stderr
    assert asked(transport) == [ANTHROPIC_TWIN]


def test_prefix_limits_the_sources_asked(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", "--prefix", f"{LESSONS}/ccar-")

    assert result.exit_code == 0, result.stderr
    assert asked(transport) == sorted([f"{COORDINATOR}/", f"{ETHICAL_AI}/"])
    assert sorted(row["url"] for row in checks_rows(store)) == [COORDINATOR, ETHICAL_AI]


def test_dry_run_asks_nothing_and_lists_what_would_be_asked(tmp_path: Path) -> None:
    store = mixed_store(tmp_path)
    versions = sorted(store.glob("*.md"))
    edges, transport = edges_over(*NOW)

    result = lorekeep(store, edges, "recheck", "--dry-run")

    assert result.exit_code == 0, result.stderr
    assert transport.requests == []
    assert checks_rows(store) == []
    assert sorted(store.glob("*.md")) == versions
    assert result.stdout.splitlines() == [
        f"would ask {EFFECTIVE_PROMPTS}/",
        f"would ask {COORDINATOR}/",
        f"would ask {ETHICAL_AI}/",
        f"skipped {BROWSER_PAGE}: {BROWSER_PAGE} was read through the browser and cannot be "
        "compared",
        f"would ask {ANTHROPIC_TWIN}",
        "skipped owner:research: owner:research is an owner's Source and has no publisher to ask",
        "Would ask 4 Sources; 2 skipped",
    ]
