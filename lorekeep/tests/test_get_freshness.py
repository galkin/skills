"""`get` returns a fresh Version without a request and rechecks an old one (ticket 07)."""

from __future__ import annotations

import csv
import hashlib
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import trafilatura

from lorekeep.edges import Edges
from lorekeep.store import RecheckRow, commit
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    Result,
    age_version,
    edges_over,
    get,
    make_store,
    rows,
    write_version,
)
from tests.test_helpers import read_version

ANTHROPIC_PAGE = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
ANTHROPIC_TWIN = f"{ANTHROPIC_PAGE}.md"


def edges_over_nothing() -> tuple[Edges, FakeTransport]:
    """A transport that answers every URL with `404` (no fixture at all)."""
    transport = FakeTransport([])
    return Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner()), transport


def stored_anthropic_twin(store: Path, *, days: float) -> Path:
    """A real `get` of the Anthropic Twin, aged by the helper."""
    edges, _ = edges_over("anthropic-prompt-caching.twin")
    result = get(store, edges, ANTHROPIC_PAGE)
    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    age_version(version, days=days)
    return version


def test_a_version_inside_the_window_is_returned_without_a_request(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_anthropic_twin(store, days=10)
    edges, transport = edges_over("anthropic-prompt-caching.twin", "anthropic-prompt-caching.304")

    result = get(store, edges, ANTHROPIC_PAGE, "--json")

    assert result.exit_code == 0, result.stderr
    assert transport.requests == []
    assert json.loads(result.stdout)["path"] == str(version)
    assert json.loads(result.stdout)["outcome"] == "fresh"
    assert rows(store, "checks.csv") == []


def test_max_age_below_the_age_sends_one_conditional_request(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_anthropic_twin(store, days=10)
    edges, transport = edges_over("anthropic-prompt-caching.twin", "anthropic-prompt-caching.304")

    result = get(store, edges, ANTHROPIC_PAGE, "--max-age", "5", "--json")

    assert result.exit_code == 0, result.stderr
    [request] = transport.requests
    assert str(request.url) == ANTHROPIC_TWIN
    assert request.headers["if-none-match"] == '"a1-twin"'
    assert [path.name for path in store.glob("*.md")] == [version.name]
    checks = rows(store, "checks.csv")
    head, _ = read_version(version)
    assert [(row["url"], row["result"], row["status"], row["sha256"]) for row in checks] == [
        (ANTHROPIC_PAGE, "unchanged", "304", head["sha256"])
    ]
    printed = json.loads(result.stdout)
    assert printed["path"] == str(version)
    assert printed["outcome"] == "unchanged"
    assert printed["verified_at"] == checks[0]["checked_at"]
    assert result.stderr == ""


def days_ago(days: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_verified_at_is_an_unchanged_recheck_of_this_version_after_it_was_fetched_else_fetched_at(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    version = stored_anthropic_twin(store, days=2)
    head, _ = read_version(version)
    other = "ab" * 32
    commit(
        store,
        checks=[
            RecheckRow(ANTHROPIC_PAGE, days_ago(5), "unchanged", "304", head["sha256"]),
            RecheckRow(ANTHROPIC_PAGE, days_ago(1), "unchanged", "304", other),
            RecheckRow(ANTHROPIC_PAGE, days_ago(1), "changed", "200", head["sha256"]),
        ],
    )

    before = get(store, edges_over_nothing()[0], ANTHROPIC_PAGE, "--json")

    assert before.exit_code == 0, before.stderr
    assert json.loads(before.stdout)["outcome"] == "fresh"
    assert json.loads(before.stdout)["verified_at"] == head["fetched_at"]

    confirmed = days_ago(0.5)
    commit(
        store, checks=[RecheckRow(ANTHROPIC_PAGE, confirmed, "unchanged", "304", head["sha256"])]
    )
    after = get(store, edges_over_nothing()[0], ANTHROPIC_PAGE, "--json")

    assert json.loads(after.stdout)["verified_at"] == confirmed


def test_a_recent_recheck_row_of_any_result_keeps_an_old_version_fresh(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_anthropic_twin(store, days=40)
    edges, transport = edges_over("anthropic-prompt-caching.twin", "anthropic-prompt-caching.304")
    unchanged = get(store, edges, ANTHROPIC_PAGE, "--max-age", "35")
    assert unchanged.exit_code == 0, unchanged.stderr
    assert len(transport.requests) == 1
    age_version(version, days=40)
    # Make the row look 10 days old: rewrite checked_at in place (the test's own file).
    _age_rows(store, days=10)

    again = get(store, edges, ANTHROPIC_PAGE, "--json")

    assert again.exit_code == 0, again.stderr
    assert len(transport.requests) == 1
    assert json.loads(again.stdout)["outcome"] == "fresh"

    gone_edges, gone_transport = edges_over_nothing()
    _rewrite_rows(store, result="gone", status="404")

    after_gone = get(store, gone_edges, ANTHROPIC_PAGE, "--json")

    assert after_gone.exit_code == 0, after_gone.stderr
    assert gone_transport.requests == []
    assert json.loads(after_gone.stdout)["outcome"] == "fresh"
    assert json.loads(after_gone.stdout)["path"] == str(version)


def _age_rows(store: Path, *, days: float) -> None:
    when = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _rewrite_rows(store, checked_at=when)


def _rewrite_rows(store: Path, **fields: str) -> None:
    checks = rows(store, "checks.csv")
    for row in checks:
        row.update(fields)
    with (store / "checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(checks)


LESSON = "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents"


def stored_lesson(store: Path, *, days: float, fixture: str) -> Path:
    """A real `get` of the termidy lesson from `fixture`, aged by the helper."""
    edges, _ = edges_over(fixture)
    result = get(store, edges, f"{LESSON}/")
    assert result.exit_code == 0, result.stderr
    version = max(store.glob("*.md"), key=lambda path: path.stat().st_mtime)
    age_version(version, days=days)
    return version


def test_the_same_bytes_again_are_unchanged_without_a_conversion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = make_store(tmp_path)
    version = stored_lesson(store, days=40, fixture="termidy-coordinator-and-subagents.html")
    edges, transport = edges_over("termidy-coordinator-and-subagents.html")
    monkeypatch.setattr(
        trafilatura, "extract", lambda *a, **k: pytest.fail("the page was converted again")
    )

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code == 0, result.stderr
    assert len(transport.requests) == 1
    assert result.stdout.splitlines()[-1] == str(version)
    assert [path.name for path in store.glob("*.md")] == [version.name]
    head, _ = read_version(version)
    assert [(row["result"], row["status"], row["sha256"]) for row in rows(store, "checks.csv")] == [
        ("unchanged", "200", head["sha256"])
    ]


def test_noisy_html_with_the_same_markdown_is_unchanged(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_lesson(store, days=40, fixture="termidy-coordinator-and-subagents.html")
    edges, _ = edges_over("termidy-coordinator-and-subagents.noisy")

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code == 0, result.stderr
    assert result.stdout.splitlines()[-1] == str(version)
    assert [path.name for path in store.glob("*.md")] == [version.name]
    assert len(list(store.glob("*.orig.html"))) == 1
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("unchanged", "200")
    ]


def test_different_markdown_is_a_second_version_beside_the_old(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old = stored_lesson(store, days=40, fixture="termidy-coordinator-and-subagents.html")
    old_bytes = old.read_bytes()
    [old_original] = store.glob("*.orig.html")
    old_original_bytes = old_original.read_bytes()
    edges, _ = edges_over("termidy-coordinator-and-subagents.changed")

    result = get(store, edges, f"{LESSON}/", "--json")

    assert result.exit_code == 0, result.stderr
    versions = sorted(store.glob("*.md"))
    assert len(versions) == 2
    [new] = [path for path in versions if path != old]
    prefix = old.name.rsplit("--", 1)[0]
    assert new.name.startswith(prefix + "--")
    assert new.name != old.name
    new_head, new_body = read_version(new)
    old_head, _ = read_version(old)
    assert new_head["sha256"] != old_head["sha256"]
    assert new_head["url"] == LESSON
    assert new_head["original"]["stored"] == "true"
    originals = sorted(store.glob("*.orig.html"))
    assert len(originals) == 2
    assert old.read_bytes() == old_bytes
    assert old_original.read_bytes() == old_original_bytes
    assert [(row["result"], row["status"], row["sha256"]) for row in rows(store, "checks.csv")] == [
        ("changed", "200", new_head["sha256"])
    ]
    printed = json.loads(result.stdout)
    assert printed["path"] == str(new)
    assert printed["outcome"] == "changed"
    assert printed["sha256"] == new_head["sha256"]
    assert b"coordinator" in new_body.lower()


def test_a_gone_page_keeps_the_stored_version_with_a_warning(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_lesson(store, days=40, fixture="termidy-coordinator-and-subagents.html")
    edges, transport = edges_over_nothing()

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code == 0
    assert [str(request.url) for request in transport.requests] == [f"{LESSON}/"]
    assert "gone" in result.stderr and "404" in result.stderr
    assert result.stdout.splitlines()[-1] == str(version)
    head, _ = read_version(version)
    assert [(row["result"], row["status"], row["sha256"]) for row in rows(store, "checks.csv")] == [
        ("gone", "404", head["sha256"])
    ]


def test_a_gone_page_without_a_stored_version_fails(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over_nothing()

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code != 0
    assert "404" in result.stderr
    assert list(store.iterdir()) == []


def test_a_twin_whose_md_address_is_gone_asks_nothing_else(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = stored_anthropic_twin(store, days=40)
    edges, transport = edges_over("anthropic-prompt-caching.html")

    result = get(store, edges, ANTHROPIC_PAGE)

    assert result.exit_code == 0
    assert [str(request.url) for request in transport.requests] == [ANTHROPIC_TWIN]
    assert result.stdout.splitlines()[-1] == str(version)
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("gone", "404")
    ]


GOOGLE_PAGE = "https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview"
GOOGLE_TWIN_RULE = (
    '[[hosts]]\nprefix = "cloud.google.com/"\npublisher = "google"\n'
    'authority = "primary"\ntwin = "md-suffix"\n'
)


def test_a_twin_address_now_answering_html_is_an_error_and_nothing_is_stored(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(GOOGLE_TWIN_RULE, encoding="utf-8")
    twin_body = (FIXTURES / "anthropic-prompt-caching.twin" / "body.md").read_bytes()
    version = write_version(
        store,
        FIXTURES / "anthropic-prompt-caching.twin",
        fetched_at="2026-01-01T00:00:00Z",
        url=GOOGLE_PAGE,
        converter="md-twin",
        original={
            "url": f"{GOOGLE_PAGE}.md",
            "mediatype": "text/markdown",
            "sha256": hashlib.sha256(twin_body).hexdigest(),
            "stored": False,
        },
    )
    edges, transport = edges_over("google-md-answers-html", "google-overview.html")

    result = get(store, edges, GOOGLE_PAGE, tag="google")

    assert result.exit_code == 0
    assert [str(request.url) for request in transport.requests] == [f"{GOOGLE_PAGE}.md"]
    assert result.stdout.splitlines()[-1] == str(version)
    assert "text/html" in result.stderr
    assert [path.name for path in store.glob("*.md")] == [version.name]
    assert not list(store.glob("*.orig.*"))
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("error", "200")
    ]


def test_an_html_version_whose_address_now_answers_a_pdf_is_an_error_and_nothing_is_stored(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    page = "https://example.test/exam/guide"
    html = (FIXTURES / "termidy-ethical-ai.html" / "body.html").read_bytes()
    version = write_version(
        store,
        FIXTURES / "termidy-ethical-ai.html",
        fetched_at="2026-01-01T00:00:00Z",
        url=page,
        converter="trafilatura 2.0.0",
        original={
            "url": page,
            "mediatype": "text/html",
            "sha256": hashlib.sha256(html).hexdigest(),
            "stored": True,
        },
    )
    edges, transport = edges_over("exam-guide.pdf")

    result = get(store, edges, page, "--json")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [page]
    assert "application/pdf" in result.stderr
    assert json.loads(result.stdout)["path"] == str(version)
    assert json.loads(result.stdout)["outcome"] == "error"
    assert [path.name for path in store.glob("*.md")] == [version.name]
    assert not list(store.glob("*.orig.*"))
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("error", "200")
    ]


def test_a_page_served_a_then_changed_then_a_again_has_two_files_and_a_current(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    plain, _ = edges_over("termidy-coordinator-and-subagents.html")
    changed, _ = edges_over("termidy-coordinator-and-subagents.changed")

    first = get(store, plain, f"{LESSON}/", "--max-age", "0")
    second = get(store, changed, f"{LESSON}/", "--max-age", "0")
    third = get(store, plain, f"{LESSON}/", "--max-age", "0", "--json")

    assert first.exit_code == second.exit_code == third.exit_code == 0, third.stderr
    a_path = first.stdout.splitlines()[-1]
    b_path = second.stdout.splitlines()[-1]
    assert a_path != b_path
    assert len(list(store.glob("*.md"))) == 2
    assert len(list(store.glob("*.orig.html"))) == 2
    a_head, _ = read_version(Path(a_path))
    b_head, _ = read_version(Path(b_path))
    assert [(row["result"], row["sha256"]) for row in rows(store, "checks.csv")] == [
        ("changed", b_head["sha256"]),
        ("changed", a_head["sha256"]),
    ]
    assert json.loads(third.stdout)["path"] == a_path
    assert json.loads(third.stdout)["outcome"] == "changed"
    fresh_again = get(store, edges_over_nothing()[0], f"{LESSON}/")
    assert fresh_again.stdout.splitlines()[-1] == a_path


@pytest.mark.parametrize("status", [503, 403])
def test_a_refusal_on_a_stored_version_is_an_error_without_the_browser(
    tmp_path: Path, status: int
) -> None:
    store = make_store(tmp_path)
    version = stored_lesson(store, days=40, fixture="termidy-coordinator-and-subagents.html")
    transport = FakeTransport.from_fixtures("termidy-coordinator-and-subagents.html")
    transport.fixtures = [replace(f, status=status) for f in transport.fixtures]
    fetcher = FakeFetcher()
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, f"{LESSON}/")

    assert result.exit_code == 0
    assert fetcher.calls == []
    assert str(status) in result.stderr
    assert result.stdout.splitlines()[-1] == str(version)
    assert [path.name for path in store.glob("*.md")] == [version.name]
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("error", str(status))
    ]


def test_a_browser_version_is_never_rechecked(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = "https://claude.termidy.com/learn/ccar-p/governance-safety-risk/ethical-ai"
    version = write_version(
        store,
        FIXTURES / "termidy-ethical-ai.html",
        fetched_at="2026-01-01T00:00:00Z",
        url=page,
        converter="trafilatura 2.0 via crawl4ai 0.9",
    )
    edges, transport = edges_over("termidy-ethical-ai.html")

    result = get(store, edges, page, "--json")

    assert result.exit_code == 0
    assert transport.requests == []
    assert "browser" in result.stderr
    assert json.loads(result.stdout)["path"] == str(version)
    assert json.loads(result.stdout)["outcome"] == "skipped"
    assert rows(store, "checks.csv") == []


def test_a_timeout_on_a_stored_version_is_an_error_named_by_its_class(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    version = write_version(
        store, FIXTURES / "timeout", fetched_at="2026-01-01T00:00:00Z", converter="md-twin"
    )
    edges, transport = edges_over("timeout")

    result = get(store, edges, "https://example.test/slow")

    assert result.exit_code == 0
    assert len(transport.requests) == 1
    assert "ReadTimeout" in result.stderr
    assert result.stdout.splitlines()[-1] == str(version)
    assert [(row["result"], row["status"]) for row in rows(store, "checks.csv")] == [
        ("error", "ReadTimeout")
    ]


def test_fresh_asks_now_like_max_age_zero(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    stored_anthropic_twin(store, days=0)
    edges, transport = edges_over("anthropic-prompt-caching.twin", "anthropic-prompt-caching.304")

    by_flag = get(store, edges, ANTHROPIC_PAGE, "--fresh")
    by_age = get(store, edges, ANTHROPIC_PAGE, "--max-age", "0")

    assert by_flag.exit_code == by_age.exit_code == 0
    assert [request.headers["if-none-match"] for request in transport.requests] == [
        '"a1-twin"',
        '"a1-twin"',
    ]
    checks = rows(store, "checks.csv")
    # Two Rechecks, two rows, even within one second with the same answer.
    assert [row["result"] for row in checks] == ["unchanged", "unchanged"]


def recheck_in_child(store: str, worker: int) -> Result:
    """One `get --fresh` in a child process, with fakes built there from paths."""
    edges, _ = edges_over("anthropic-prompt-caching.twin", "anthropic-prompt-caching.304")
    return get(Path(store), edges, ANTHROPIC_PAGE, "--fresh", tag=f"worker-{worker}")


def test_concurrent_rechecks_keep_one_header_in_checks_csv(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    stored_anthropic_twin(store, days=40)
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=6, mp_context=context) as pool:
        results = list(pool.map(recheck_in_child, [str(store)] * 6, range(6)))

    assert all(result.exit_code == 0 for result in results), [r.stderr for r in results]
    lines = (store / "checks.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "url,checked_at,result,status,sha256"
    assert lines.count(lines[0]) == 1
    checks = rows(store, "checks.csv")
    assert [row["result"] for row in checks] == ["unchanged"] * 6
