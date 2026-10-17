"""The Index follows every commit, and a reader notices when it is stale (ticket 14)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from lorekeep import frontmatter
from lorekeep.edges import Edges
from lorekeep.store import AliasRow, CheckRow, NewVersion, TagRow, commit
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    Result,
    run_cli,
    write_version,
)
from tests.test_index import (
    ANTHROPIC,
    AWS,
    FOUNDRY,
    add_text,
    files_of,
    result_lines,
    store_lock_held,
    three_twins,
)


def search_while_locked(store: Path, *argv: str, timeout: float = 5.0) -> tuple[bool, Result]:
    """Run `search` while another worker holds the Store lock: whether it finished before the
    lock was released, and its result once the lock was released."""
    outcome: list[Result] = []
    worker = threading.Thread(
        target=lambda: outcome.append(run_cli(["search", *argv, "--store", str(store)]))
    )
    with store_lock_held(store):
        worker.start()
        worker.join(timeout=timeout)
        finished = not worker.is_alive()
    worker.join(timeout=30)
    return finished, outcome[0]


def test_after_add_the_version_is_searchable_and_the_next_search_rebuilds_nothing(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    three_twins(store)
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    path = add_text(tmp_path, store, "notes", "# Zebra\n\nThe zebra paragraph is new.\n")

    finished, result = search_while_locked(store, "zebra")

    assert finished, "search waited for the lock: it rebuilt a current Index"
    assert result.exit_code == 0, result.stderr
    lines = result_lines(result.stdout)
    assert len(lines) == 1
    assert lines[0].startswith(f"{path}:")
    assert " | Zebra | " in lines[0]


def test_a_file_copied_in_by_hand_is_searchable_after_the_next_search_which_rebuilds_under_the_lock(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    assert run_cli(["index", "--store", str(tmp_path)]).exit_code == 0
    by_hand = write_version(
        tmp_path,
        FIXTURES / "aws-prompt-caching.twin",
        fetched_at="2026-10-05T00:00:00Z",
        url="https://docs.aws.amazon.com/bedrock/latest/userguide/copied-by-hand.html",
    )

    finished, rebuilt = search_while_locked(
        tmp_path, "caching", "--all", "--limit", "100", timeout=0.5
    )
    assert not finished, "search on a stale Index answered without taking the lock"
    finished, again = search_while_locked(tmp_path, "caching", "--all", "--limit", "100")

    assert rebuilt.exit_code == 0, rebuilt.stderr
    assert by_hand.name in files_of(rebuilt.stdout.splitlines())
    assert finished, "a second search rebuilt an Index that was current"
    assert again.stdout == rebuilt.stdout


def citations(store: Path) -> list[tuple[str, str, str | None]]:
    with sqlite3.connect(store / "sources.db") as con:
        return con.execute("SELECT work_id, url, as_of FROM citations ORDER BY work_id").fetchall()


def cited_works_with_a_version(store: Path) -> set[str]:
    with sqlite3.connect(store / "sources.db") as con:
        rows = con.execute(
            "SELECT DISTINCT c.work_id FROM citations c JOIN versions v ON v.url = c.url"
        ).fetchall()
    return {work for (work,) in rows}


def test_rewriting_citations_makes_the_next_search_rebuild_and_see_the_new_rows(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    assert run_cli(["index", "--store", str(tmp_path)]).exit_code == 0
    (tmp_path / "citations.csv").write_text(
        "work_id,url,as_of\n"
        f"lesson-1,{ANTHROPIC}.md,2026-10-02\n"
        f"lesson-2,{AWS},2026-10-02T12:00:00Z\n"
        f"lesson-3,{FOUNDRY},\n"
        "lesson-4\n"
        f"lesson-5,{AWS},yesterday\n",
        encoding="utf-8",
    )

    first = run_cli(["search", "caching", "--all", "--store", str(tmp_path)])

    assert first.exit_code == 0, first.stderr
    assert citations(tmp_path) == [
        ("lesson-1", ANTHROPIC, "2026-10-02T23:59:59Z"),
        ("lesson-2", AWS, "2026-10-02T12:00:00Z"),
        ("lesson-3", FOUNDRY, None),
    ]
    assert cited_works_with_a_version(tmp_path) == {"lesson-1", "lesson-2", "lesson-3"}
    warnings = [line for line in first.stderr.splitlines() if "citations.csv" in line]
    assert len(warnings) == 2
    assert "line 5" in warnings[0] and "line 6" in warnings[1]

    (tmp_path / "citations.csv").write_text(f"work_id,url\nlesson-9,{FOUNDRY}\n", encoding="utf-8")
    second = run_cli(["search", "caching", "--all", "--store", str(tmp_path)])

    assert second.exit_code == 0, second.stderr
    assert citations(tmp_path) == [("lesson-9", FOUNDRY, None)]
    assert "citations.csv" not in second.stderr


def test_a_version_copied_in_by_hand_is_found_by_get_without_any_request(tmp_path: Path) -> None:
    three_twins(tmp_path)
    assert run_cli(["index", "--store", str(tmp_path)]).exit_code == 0
    page = "https://platform.claude.com/docs/en/build-with-claude/copied-by-hand"
    by_hand = write_version(
        tmp_path, FIXTURES / "aws-prompt-caching.twin", fetched_at="2026-10-05T00:00:00Z", url=page
    )
    transport = FakeTransport.from_fixtures()
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = run_cli(
        ["get", page],
        env={"LOREKEEP_STORE": str(tmp_path), "LOREKEEP_TAG": "anthropic"},
        edges=edges,
    )

    assert result.exit_code == 0, result.stderr
    assert result.stdout.rstrip("\n").splitlines()[-1] == str(by_hand)
    assert transport.requests == []
    # The Tag row that `get` committed did not make the stale Index look current.
    finished, found = search_while_locked(
        tmp_path, "caching", "--all", "--limit", "100", timeout=0.5
    )
    assert not finished and by_hand.name in files_of(found.stdout.splitlines())


ALL_TABLES = ("versions", "tags", "checks", "aliases", "citations", "sections", "sections_fts")


def all_counts(store: Path) -> dict[str, int]:
    with sqlite3.connect(store / "sources.db") as con:
        return {
            table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ALL_TABLES
        }


def test_index_rebuilt_from_the_files_reports_the_same_counts_as_the_incremental_index(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    env = {"LOREKEEP_STORE": str(store), "LOREKEEP_TAG": "anthropic"}
    first = run_cli(["get", ANTHROPIC], env=env)
    assert first.exit_code == 0, first.stderr
    assert not (store / "sources.db").exists(), "get built an Index"
    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    add_text(
        tmp_path, store, "notes", "# Notes\n\nA quokka note.\n\n## More\n\nAnother quokka note.\n"
    )
    # What `tag add` commits: Tag rows, one of them already present.
    at = "2026-10-06T00:00:00Z"
    commit(store, tags=[TagRow(ANTHROPIC, "anthropic", at), TagRow(ANTHROPIC, "nvidia", at)])
    # What an aged `get` commits: a Recheck row, and on a change a new Version beside the old.
    changed = write_version(
        store, FIXTURES / "aws-prompt-caching.twin", fetched_at="2026-10-07T00:00:00Z", url=AWS
    )
    head, body = frontmatter.parse(changed.read_bytes())
    changed.unlink()
    commit(
        store,
        NewVersion(frontmatter=head, body=body),
        tags=[TagRow(AWS, "aws", at)],
        checks=[CheckRow(AWS, "2026-10-07T00:00:00Z", "changed", "200", str(head["sha256"]))],
        aliases=[AliasRow(AWS + "?view=old", AWS, at)],
    )
    commit(store, checks=[CheckRow(ANTHROPIC, "2026-10-08T00:00:00Z", "unchanged", "304", "")])
    again = run_cli(["get", ANTHROPIC], env=env | {"LOREKEEP_TAG": "aws"})
    assert again.exit_code == 0, again.stderr

    incremental = all_counts(store)
    finished, result = search_while_locked(store, "quokka", "--all")
    assert finished and result.exit_code == 0, "the incremental Index was not current"
    assert len(result_lines(result.stdout)) == 2
    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    assert all_counts(store) == incremental
    assert incremental["versions"] == 3
    assert incremental["tags"] == 5
    assert incremental["checks"] == 2
    assert incremental["aliases"] == 1
