"""`withdraw`: the owner takes a Source stored by mistake out of every Run's view (ADR 0010)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from frictionless import validate

from lorekeep.edges import Edges
from lorekeep.store import (
    WITHDRAW,
    TagRow,
    WithdrawalRow,
    WithdrawnError,
    change_withdrawal,
    commit,
)
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    edges_over,
    get,
    lorekeep,
    make_store,
    rows,
    run_cli,
    write_version,
)
from tests.test_index import store_lock_held

NIM = "https://docs.nvidia.com/nim/large-language-models/latest/about-nim-llm/overview.html"
AWS = "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"
REASON = "a namesake, not the page the brief asked for"
BUILD_RULE = (
    '[[hosts]]\nprefix = "build.nvidia.com/"\npublisher = "nvidia"\nauthority = "primary"\n'
    'twin = "md-suffix"\npage_suffix = "/modelcard"\n'
)
AWS_RULE = '[[readings]]\nprefix = "docs.aws.amazon.com/"\ndrop_lines = "^\\\\s*<"\n'


def two_sources(tmp_path: Path) -> Path:
    """An NVIDIA Source and an AWS Source in two Versions (the HTML one latest), each tagged, the
    AWS one also asked once under an alias."""
    store = make_store(tmp_path)
    write_version(store, FIXTURES / "nim-overview.html", fetched_at="2026-08-01T00:00:00Z")
    write_version(store, FIXTURES / "aws-prompt-caching.html", fetched_at="2026-08-02T00:00:00Z")
    write_version(
        store,
        FIXTURES / "nim-introduction.stub",
        fetched_at="2026-07-30T00:00:00Z",
        url=AWS,
    )
    (store / "tags.csv").write_text(
        f"url,tag,added_at\n{NIM},nvidia,2026-08-01T00:00:00Z\n{AWS},aws,2026-08-02T00:00:00Z\n",
        encoding="utf-8",
    )
    (store / "aliases.csv").write_text(
        f"alias,url,added_at\nhttps://aws.test/caching,{AWS},2026-08-02T00:00:00Z\n",
        encoding="utf-8",
    )
    return store


def withdraw(store: Path, *argv: str, reason: str = REASON) -> tuple[int, str, str]:
    result = run_cli(["withdraw", *argv, "--reason", reason, "--store", str(store)])
    return result.exit_code, result.stdout, result.stderr


def search_urls(store: Path, query: str) -> list[str]:
    result = run_cli(["search", query, "--json", "--all", "--store", str(store)])
    assert result.exit_code == 0, result.stderr
    return [hit["url"] for hit in json.loads(result.stdout)["results"]]


def test_withdraw_appends_one_row_naming_the_source(tmp_path: Path) -> None:
    store = two_sources(tmp_path)

    code, out, err = withdraw(store, AWS)

    assert code == 0, err
    assert out == f"Withdrew {AWS}: {REASON}\n"
    [row] = rows(store, "withdrawals.csv")
    assert row["url"] == AWS
    assert row["action"] == "withdraw"
    assert row["reason"] == REASON
    assert row["recorded_at"].endswith("Z")


def test_an_alias_or_an_address_as_a_request_gives_it_withdraws_the_same_source(
    tmp_path: Path,
) -> None:
    for asked in ("https://aws.test/caching", AWS.replace("docs.aws", "DOCS.AWS") + "#top"):
        store = two_sources(tmp_path / asked.split("/")[2])

        code, _, err = withdraw(store, asked)

        assert code == 0, err
        assert [row["url"] for row in rows(store, "withdrawals.csv")] == [AWS]


def test_a_url_with_no_source_exits_2_and_writes_nothing(tmp_path: Path) -> None:
    store = two_sources(tmp_path)

    code, _, err = withdraw(store, "https://ans.dev/")

    assert code == 2
    assert "https://ans.dev/" in err
    assert not (store / "withdrawals.csv").exists()


def test_withdraw_needs_a_reason(tmp_path: Path) -> None:
    store = two_sources(tmp_path)

    assert run_cli(["withdraw", AWS, "--store", str(store)]).exit_code == 2
    assert withdraw(store, AWS, reason="  ")[0] == 2
    assert not (store / "withdrawals.csv").exists()


def test_a_second_withdraw_writes_nothing_and_says_when_and_why(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)
    before = (store / "withdrawals.csv").read_bytes()

    code, out, _ = withdraw(store, AWS, reason="again")

    assert code == 0
    assert "already withdrawn" in out
    assert REASON in out
    assert (store / "withdrawals.csv").read_bytes() == before


def test_undo_appends_the_row_that_takes_it_back_and_only_when_withdrawn(tmp_path: Path) -> None:
    store = two_sources(tmp_path)

    code, out, _ = withdraw(store, "--undo", AWS, reason="nothing to undo")
    assert code == 0
    assert "not withdrawn" in out
    assert not (store / "withdrawals.csv").exists()

    withdraw(store, AWS)
    code, out, err = withdraw(store, "--undo", AWS, reason="the owner was wrong")

    assert code == 0, err
    assert out.startswith(f"Brought back {AWS}")
    actions = [(row["action"], row["reason"]) for row in rows(store, "withdrawals.csv")]
    assert actions == [("withdraw", REASON), ("undo", "the owner was wrong")]
    assert withdraw(store, "--undo", AWS, reason="twice")[0] == 0
    assert len(rows(store, "withdrawals.csv")) == 2


def test_search_leaves_a_withdrawn_source_out_and_finds_it_again_after_undo(
    tmp_path: Path,
) -> None:
    store = two_sources(tmp_path)
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    assert AWS in search_urls(store, "caching")

    withdraw(store, AWS)
    assert AWS not in search_urls(store, "caching")
    assert NIM in search_urls(store, "NIM")

    withdraw(store, "--undo", AWS, reason="taken back")
    assert AWS in search_urls(store, "caching")


def test_status_counts_a_withdrawn_source_on_its_own_line(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)

    text = run_cli(["status", "--store", str(store)])
    found = json.loads(run_cli(["status", "--json", "--store", str(store)]).stdout)

    assert text.exit_code == 0, text.stderr
    assert "1 Version of 1 Source\n" in text.stdout
    assert "Withdrawn: 1 Source (2 Versions)\n" in text.stdout
    assert (found["versions"], found["sources"]) == (1, 1)
    assert (found["withdrawn_sources"], found["withdrawn_versions"]) == (1, 2)
    assert found["tags"] == {"nvidia": 1}


def test_get_of_a_withdrawn_url_refuses_naming_the_withdrawal(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)
    tags = (store / "tags.csv").read_bytes()
    edges, transport = edges_over("aws-prompt-caching.html")

    for asked in (AWS, "https://aws.test/caching"):
        result = get(store, edges, asked, "--fresh", tag="aws")

        assert result.exit_code == 1
        assert result.stdout == ""
        assert f"{AWS} was withdrawn by the owner" in result.stderr
        assert REASON in result.stderr
    assert transport.requests == []
    assert (store / "tags.csv").read_bytes() == tags


def test_add_of_a_withdrawn_owner_source_refuses(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    note = tmp_path / "note.md"
    note.write_text("# Research\n\nPasted from a chat.\n", encoding="utf-8")
    argv = ["add", str(note), "--title", "Research", "--tag", "anthropic", "--store", str(store)]
    assert run_cli(argv).exit_code == 0
    withdraw(store, "owner:research")

    result = run_cli(argv)

    assert result.exit_code == 1
    assert "owner:research was withdrawn" in result.stderr


def test_read_and_the_index_build_no_reading_of_a_withdrawn_version(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    (store / "lorekeep.toml").write_text(AWS_RULE, encoding="utf-8")
    withdraw(store, AWS)

    result = run_cli(["read", "--store", str(store)])
    indexed = run_cli(["index", "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert indexed.exit_code == 0, indexed.stderr
    assert not list((store / ".cache" / "readings").glob("docs.aws*"))

    withdraw(store, "--undo", AWS, reason="taken back")
    assert run_cli(["read", "--store", str(store)]).stdout.startswith("Built 2 Readings")


def test_recheck_asks_nothing_about_a_withdrawn_source(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)

    result = run_cli(["recheck", "--dry-run", "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert AWS not in result.stdout
    assert "Would ask 0 Sources; 1 skipped" in result.stdout


def test_a_citation_of_a_withdrawn_source_fails_recheck_citations(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    (store / "citations.csv").write_text(
        f"work_id,url\nlesson-1,https://aws.test/caching\nlesson-2,{NIM}\n", encoding="utf-8"
    )
    assert run_cli(["recheck", "--citations", "--store", str(store)]).exit_code == 0
    withdraw(store, AWS)

    result = run_cli(["recheck", "--citations", "--store", str(store)])

    assert result.exit_code == 1
    assert f"lorekeep: error: lesson-1 cites {AWS}, withdrawn at " in result.stderr
    assert REASON in result.stderr
    assert "lesson-2" not in result.stderr


def test_backup_copies_withdrawals_and_the_package_describes_them(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    (store / "lorekeep.toml").write_text('bucket = "test-sources"\n', encoding="utf-8")
    withdraw(store, AWS)
    runner = FakeRunner()
    edges = Edges(transport=FakeTransport([]), fetcher=FakeFetcher(), runner=runner)

    result = lorekeep(store, edges, "backup")

    assert result.exit_code == 0, result.stderr
    _, cp = runner.calls
    assert str(store / "withdrawals.csv") in cp
    report = validate(str(store / "datapackage.json"))
    assert report.valid, report.flatten(["rowNumber", "fieldName", "type", "note"])
    package = json.loads((store / "datapackage.json").read_text(encoding="utf-8"))
    [described] = [r for r in package["resources"] if r["name"] == "withdrawals"]
    assert [field["name"] for field in described["schema"]["fields"]] == [
        "url",
        "recorded_at",
        "action",
        "reason",
    ]


def test_get_of_a_new_address_that_redirects_to_a_withdrawn_source_stores_nothing(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(BUILD_RULE, encoding="utf-8")
    safety = "https://build.nvidia.com/nvidia/safety-for-agentic-ai"
    fixtures = ("build-safety-for-agentic-ai.301", "build-safety-for-agentic-ai.twin")
    assert get(store, edges_over(*fixtures)[0], safety, tag="nvidia").exit_code == 0
    withdraw(store, safety)
    files = sorted(path.name for path in store.iterdir())

    result = get(
        store, edges_over(*fixtures)[0], "https://build.nvidia.com/nvidia/agentic-ai-safety"
    )

    assert result.exit_code == 1
    assert f"{safety} was withdrawn by the owner" in result.stderr
    assert sorted(path.name for path in store.iterdir()) == files
    assert [row["tag"] for row in rows(store, "tags.csv")] == ["nvidia"]


def test_a_twin_address_withdraws_the_page_it_is_the_twin_of(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = (
        "https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/"
        "jailbreak-protection"
    )
    edges, _ = edges_over("guardrails-jailbreak-protection.twin")
    assert get(store, edges, page, tag="nvidia").exit_code == 0

    code, _, err = withdraw(store, f"{page}.md")

    assert code == 0, err
    assert [row["url"] for row in rows(store, "withdrawals.csv")] == [page]


def test_whether_a_row_changes_anything_is_decided_under_the_lock(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    mine = WithdrawalRow(AWS, "2026-10-22T10:00:01Z", WITHDRAW, "mine")
    returned: list[WithdrawalRow | None] = []

    with store_lock_held(store):
        worker = threading.Thread(target=lambda: returned.append(change_withdrawal(store, mine)))
        worker.start()
        worker.join(timeout=0.5)
        assert worker.is_alive(), "change_withdrawal did not wait for the lock"
        # Another worker's withdrawal lands while this one waits.
        (store / "withdrawals.csv").write_text(
            f"url,recorded_at,action,reason\n{AWS},2026-10-22T10:00:00Z,withdraw,theirs\n",
            encoding="utf-8",
        )
    worker.join(timeout=30)

    [before] = returned
    assert before is not None and before.reason == "theirs"
    assert [row["reason"] for row in rows(store, "withdrawals.csv")] == ["theirs"]


def test_a_commit_naming_a_withdrawn_source_writes_nothing(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)
    tags = (store / "tags.csv").read_bytes()
    rows_of = [
        TagRow(NIM, "late", "2026-10-22T10:00:00Z"),
        TagRow(AWS, "late", "2026-10-22T10:00:00Z"),
    ]

    with pytest.raises(WithdrawnError, match=f"{AWS} was withdrawn by the owner"):
        commit(store, tags=rows_of)

    assert (store / "tags.csv").read_bytes() == tags


def test_tag_add_of_a_withdrawn_url_says_so_and_tags_nothing(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)
    tags = (store / "tags.csv").read_bytes()

    result = run_cli(["tag", "add", "specifications", AWS, "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert f"{AWS} was withdrawn by the owner" in result.stderr
    assert "not tagged" in result.stderr
    assert "Tagged 0 Sources" in result.stdout
    assert (store / "tags.csv").read_bytes() == tags


def test_tag_add_under_a_prefix_leaves_a_withdrawn_source_out(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)

    result = run_cli(["tag", "add", "docs", "--prefix", "https://docs.", "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert [row["url"] for row in rows(store, "tags.csv") if row["tag"] == "docs"] == [NIM]


def test_rules_sample_leaves_withdrawn_versions_out(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    withdraw(store, AWS)

    result = run_cli(["rules", "sample", "docs.aws.amazon.com/", "--store", str(store)])

    assert result.exit_code == 1
    assert "no Version under docs.aws.amazon.com/" in result.stderr


def test_a_cited_withdrawn_source_is_an_error_and_not_also_a_revisit(tmp_path: Path) -> None:
    store = two_sources(tmp_path)
    # Written from the older AWS Version: without the withdrawal it is a revisit.
    (store / "citations.csv").write_text(
        f"work_id,url,as_of\nlesson-1,{AWS},2026-07-31\n", encoding="utf-8"
    )
    before = run_cli(["recheck", "--citations", "--store", str(store)])
    assert before.stdout.startswith(f"lesson-1, {AWS}, ")
    withdraw(store, AWS)

    result = run_cli(["recheck", "--citations", "--store", str(store)])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert f"lesson-1 cites {AWS}, withdrawn at " in result.stderr
