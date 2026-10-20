"""Six workers call lorekeep against one Store at once (ticket 12).

Every worker is a child process (`spawn`, as on macOS) that builds its own fakes from the fixture
paths and runs commands through the command layer, exactly as six pipeline workers would from
their worktrees.
"""

from __future__ import annotations

import csv
import multiprocessing
import random
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from lorekeep import frontmatter
from lorekeep.edges import Edges
from tests.support import FakeFetcher, FakeRunner, FakeTransport, Result, run_cli
from tests.test_staleness import all_counts, search_while_locked

WORKERS = 6

# Pages every worker may ask for: Twins, a redirect chain into a Twin, static HTML, a meta-refresh
# stub and a page with relative links; none needs the browser or a PDF conversion.
PAGES = (
    "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
    "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html",
    "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry",
    "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents/",
    "https://claude.termidy.com/learn/ccao-f/prompting-task-execution/effective-prompts/",
    "https://claude.termidy.com/learn/ccar-p/governance-safety-risk/ethical-ai/",
    "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html",
    "https://example.test/guide/sub/page.html",
)
# One response per address: the `.noisy` and `.changed` variants of one lesson are left out, so
# every repeated fetch of a page receives the same bytes.
FIXTURES_USED = (
    "anthropic-prompt-caching.twin",
    "anthropic-prompt-caching.304",
    "aws-prompt-caching.twin",
    "ms-foundry.redirect-1",
    "ms-foundry.redirect-2",
    "ms-foundry.twin",
    "termidy-coordinator-and-subagents.html",
    "termidy-effective-prompts.html",
    "termidy-ethical-ai.html",
    "nim-introduction.stub",
    "nim-overview.html",
    "relative-links.html",
)
SHARED_NOTE = "# Shared notes\n\nEvery worker adds this same file.\n"


def worker_edges() -> Edges:
    """The fakes one worker builds for itself, from paths alone."""
    return Edges(
        transport=FakeTransport.from_fixtures(*FIXTURES_USED),
        fetcher=FakeFetcher(),
        runner=FakeRunner(),
    )


def worker_gets_and_adds(store: str, scratch: str, worker: int) -> list[Result]:
    """One worker's Run: every page twice in its own order, some forced through a Recheck, and
    two `add`s — a note of its own and the note every worker adds. Three workers share a Tag."""
    env = {"LOREKEEP_STORE": store, "LOREKEEP_TAG": f"run-{worker % 2}"}
    edges = worker_edges()
    order = list(PAGES) * 2
    random.Random(worker).shuffle(order)
    results: list[Result] = []
    for number, page in enumerate(order):
        argv = ["get", page]
        if (number + worker) % 3 == 0:
            argv += ["--max-age", "0"]
        results.append(run_cli(argv, env=env, edges=edges))
    own = Path(scratch) / f"notes-{worker}.md"
    own.write_text(f"# Notes {worker}\n\nWhat worker {worker} found.\n", encoding="utf-8")
    shared = Path(scratch) / f"shared-{worker}.md"
    shared.write_text(SHARED_NOTE, encoding="utf-8")
    for file, title in ((own, f"Notes {worker}"), (shared, "Shared notes")):
        argv = ["add", str(file), "--title", title, "--fetched-at", "2026-10-01T00:00:00Z"]
        results.append(run_cli(argv, env=env, edges=edges))
    return results


def worker_searches(store: str, worker: int) -> Result:
    return run_cli(["search", "caching", "--all", "--store", store], edges=worker_edges())


def worker_get_without_an_index(store: str, worker: int) -> Result:
    env = {"LOREKEEP_STORE": store, "LOREKEEP_TAG": f"run-{worker % 2}"}
    return run_cli(["get", PAGES[worker % len(PAGES)]], env=env, edges=worker_edges())


def pool() -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn"))


def csv_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def rebuild_notes(results: list[Result]) -> list[str]:
    return [line for result in results for line in result.stderr.splitlines() if "rebuilt" in line]


def test_six_workers_get_and_add_against_one_store(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    with pool() as workers:
        outcomes = list(
            workers.map(
                worker_gets_and_adds, [str(store)] * WORKERS, [str(scratch)] * WORKERS, range(6)
            )
        )

    results = [result for worker in outcomes for result in worker]
    assert all(result.exit_code == 0 for result in results), [
        result.stderr for result in results if result.exit_code != 0
    ]
    # One file per Version: eight pages, six notes of their own and the one shared note.
    versions = sorted(store.glob("*.md"))
    assert len(versions) == len(PAGES) + WORKERS + 1
    assert [path.name for path in store.glob("*.tmp-*")] == []
    for path in versions:
        head, _ = frontmatter.parse(path.read_bytes())
        assert head["url"] and head["sha256"]
    # Every path a worker printed is one of those files.
    printed = {result.stdout.rstrip("\n").splitlines()[-1] for result in results}
    assert printed == {str(path) for path in versions}

    tags = csv_rows(store / "tags.csv")
    assert tags[0] == ["url", "tag", "added_at"]
    assert tags.count(tags[0]) == 1
    assert all(len(row) == 3 for row in tags)
    pairs = [(url, tag) for url, tag, _ in tags[1:]]
    assert len(pairs) == len(set(pairs))
    assert len(pairs) == 2 * (len(PAGES) + 1) + WORKERS

    checks = csv_rows(store / "checks.csv")
    assert checks[0] == ["url", "checked_at", "result", "status", "sha256"]
    assert checks.count(checks[0]) == 1
    assert all(len(row) == 5 for row in checks)
    assert {row[2] for row in checks[1:]} == {"unchanged"}

    aliases = csv_rows(store / "aliases.csv")
    assert aliases[0] == ["alias", "url", "added_at"]
    assert all(len(row) == 3 for row in aliases)

    incremental = all_counts(store)
    finished, result = search_while_locked(store, "caching", "--all")
    assert finished and result.exit_code == 0, "the incremental Index was not current"
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    assert all_counts(store) == incremental
    assert incremental["versions"] == len(versions)


def test_six_searches_against_a_deleted_index_rebuild_it_once(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    env = {"LOREKEEP_STORE": str(store), "LOREKEEP_TAG": "anthropic"}
    for page in PAGES[:2]:
        assert run_cli(["get", page], env=env, edges=worker_edges()).exit_code == 0
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    for name in ("sources.db", "sources.db-wal", "sources.db-shm"):
        (store / name).unlink(missing_ok=True)

    with pool() as workers:
        results = list(workers.map(worker_searches, [str(store)] * WORKERS, range(WORKERS)))

    assert all(result.exit_code == 0 for result in results), [r.stderr for r in results]
    assert len({result.stdout for result in results}) == 1
    assert len(rebuild_notes(results)) == 1, [r.stderr for r in results]
    with sqlite3.connect(store / "sources.db") as con:
        assert con.execute("SELECT count(*) FROM versions").fetchone()[0] == 2


def test_six_gets_against_a_missing_index_rebuild_nothing(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()

    with pool() as workers:
        results = list(
            workers.map(worker_get_without_an_index, [str(store)] * WORKERS, range(WORKERS))
        )

    assert all(result.exit_code == 0 for result in results), [r.stderr for r in results]
    assert rebuild_notes(results) == []
    assert not (store / "sources.db").exists()
    assert len(list(store.glob("*.md"))) == len({PAGES[n % len(PAGES)] for n in range(WORKERS)})
