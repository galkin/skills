"""`index` builds the Index from the Store's files, and `search` answers from it."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path

from lorekeep.project import load_project
from lorekeep.store import AliasRow, RecheckRow, TagRow, VersionInfo, commit, latest
from tests.support import FIXTURES, Result, edges_over, get, run_cli, write_version

ANTHROPIC = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
AWS = "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"
FOUNDRY = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
TABLES = ("versions", "tags", "checks", "aliases", "sections", "sections_fts")


def counts(store: Path) -> dict[str, int]:
    with sqlite3.connect(store / "sources.db") as con:
        return {
            table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES
        }


def three_twins(store: Path) -> None:
    """The Anthropic and AWS Twins tagged `anthropic` and `aws`, the Foundry Twin `microsoft`."""
    write_version(
        store,
        FIXTURES / "anthropic-prompt-caching.twin",
        fetched_at="2026-10-01T00:00:00Z",
        url=ANTHROPIC,
        publisher="anthropic",
        authority="primary",
    )
    write_version(
        store,
        FIXTURES / "aws-prompt-caching.twin",
        fetched_at="2026-10-02T00:00:00Z",
        url=AWS,
        publisher="aws",
        authority="primary",
    )
    write_version(
        store,
        FIXTURES / "ms-foundry.twin",
        fetched_at="2026-10-03T00:00:00Z",
        url=FOUNDRY,
        publisher="microsoft",
        authority="official",
    )
    at = "2026-10-03T00:00:00Z"
    commit(
        store,
        tags=[
            TagRow(ANTHROPIC, "anthropic", at),
            TagRow(AWS, "aws", at),
            TagRow(FOUNDRY, "microsoft", at),
        ],
        checks=[RecheckRow(AWS, "2026-10-04T00:00:00Z", "unchanged", "304", "")],
        aliases=[AliasRow(FOUNDRY + "-old", FOUNDRY, at)],
    )


def test_index_builds_sources_db_and_a_rebuild_from_the_files_gives_the_same_counts(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)

    first = run_cli(["index", "--store", str(tmp_path)])

    assert first.exit_code == 0, first.stderr
    built = counts(tmp_path)
    assert built["versions"] == 3
    assert built["tags"] == 3
    assert built["checks"] == 1
    assert built["aliases"] == 1
    assert built["sections"] > 3
    assert built["sections_fts"] == built["sections"]
    assert "3 Versions" in first.stdout

    for name in ("sources.db", "sources.db-wal", "sources.db-shm"):
        (tmp_path / name).unlink(missing_ok=True)
    second = run_cli(["index", "--store", str(tmp_path)])

    assert second.exit_code == 0, second.stderr
    assert counts(tmp_path) == built
    assert second.stdout == first.stdout


def test_index_runs_in_wal_mode(tmp_path: Path) -> None:
    three_twins(tmp_path)

    run_cli(["index", "--store", str(tmp_path)])

    with sqlite3.connect(tmp_path / "sources.db") as con:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def sections(store: Path) -> list[tuple[str, str, int, str]]:
    with sqlite3.connect(store / "sources.db") as con:
        return con.execute(
            "SELECT file, heading, line, body FROM sections ORDER BY file, ord"
        ).fetchall()


def add_text(tmp_path: Path, store: Path, title: str, text: str) -> Path:
    source = tmp_path / f"{title}.md"
    source.write_text(text, encoding="utf-8")
    result = run_cli(
        ["add", str(source), "--title", title, "--store", str(store), "--tag", "owner"]
    )
    assert result.exit_code == 0, result.stderr
    return Path(result.stdout.strip())


def test_a_page_without_headings_is_cut_into_sections_of_about_4_kb_and_never_inside_a_fence(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    paragraph = "Prompt caching stores a prefix of the prompt so later calls reuse it. " * 4
    fence = "```python\n" + "\n\n".join(f"call_{n} = client.messages.create()" for n in range(80))
    fence += "\n```"
    text = "\n\n".join([paragraph] * 25 + [fence] + [paragraph] * 25) + "\n"
    path = add_text(tmp_path, store, "no headings", text)

    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    file_lines = path.read_text(encoding="utf-8").splitlines()
    found = sections(store)
    assert len(found) >= 4
    assert sum(body.count("reuse it.") for *_, body in found) == 50 * 4
    for _, heading, line, body in found:
        assert heading == ""
        assert len(body.encode()) <= 4096 or body.startswith("```"), len(body.encode())
        assert file_lines[line - 1] == body.splitlines()[0]
        assert body.count("```") in (0, 2)
    fenced = [body for *_, body in found if "```" in body]
    assert len(fenced) == 1 and "call_0 " in fenced[0] and "call_79 " in fenced[0]


def test_a_fence_over_4_kb_after_two_blank_lines_is_kept_whole_and_its_line_is_the_fence(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    paragraph = "Prompt caching stores a prefix of the prompt so later calls reuse it. " * 4
    fence = "```python\n" + "\n\n".join(f"call_{n} = client.messages.create()" for n in range(150))
    fence += "\n```"
    assert len(fence.encode()) > 4096
    text = "# Calls\n\n" + paragraph + "\n\n\n" + fence + "\n\n\n" + paragraph + "\n"
    path = add_text(tmp_path, store, "blank lines before a fence", text)

    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    file_lines = path.read_text(encoding="utf-8").splitlines()
    found = sections(store)
    fenced = [(line, body) for _, _, line, body in found if "```" in body]
    assert len(fenced) == 1, [body[:40] for *_, body in found]
    line, body = fenced[0]
    assert body.count("```") == 2 and "call_0 " in body and "call_149 " in body
    assert file_lines[line - 1] == body.splitlines()[0]
    for _, _, line, body in found:
        assert file_lines[line - 1].strip(), (line, body[:40])


def test_every_section_knows_its_heading_line_its_first_text_line_and_its_heading_path(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    text = (
        "Intro before any heading.\n\n# Prompt caching\n\nCaching cuts cost.\n\n"
        "```bash\n# not a heading\necho cached\n```\n\n## Pricing\n\nCache writes cost more.\n\n"
        "### Reads\n\nCache reads cost less.\n\n## Limits\n\nFive minutes.\n"
    )
    path = add_text(tmp_path, store, "with headings", text)

    run_cli(["index", "--store", str(store)])

    file_lines = path.read_text(encoding="utf-8").splitlines()
    with sqlite3.connect(store / "sources.db") as con:
        found = con.execute(
            "SELECT heading, heading_line, line, body FROM sections ORDER BY ord"
        ).fetchall()
    assert [heading for heading, *_ in found] == [
        "",
        "Prompt caching",
        "Prompt caching > Pricing",
        "Prompt caching > Pricing > Reads",
        "Prompt caching > Limits",
    ]
    assert found[0][1] is None
    assert file_lines[found[0][2] - 1] == "Intro before any heading."
    for heading, heading_line, line, body in found[1:]:
        assert file_lines[heading_line - 1].lstrip("#").strip() == heading.split(" > ")[-1]
        assert file_lines[line - 1] == body.splitlines()[0]
    assert "# not a heading" in found[1][3]


def result_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if " | " in line]


def test_search_returns_ranked_lines_with_file_line_heading_path_and_snippet(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    result = run_cli(["search", "prompt caching", "--store", str(tmp_path)])

    assert result.exit_code == 0, result.stderr
    lines = result_lines(result.stdout)
    assert 1 <= len(lines) <= 5
    for line in lines:
        location, heading, snippet = line.split(" | ", 2)
        file, number = location.rsplit(":", 1)
        text = Path(file).read_text(encoding="utf-8").splitlines()
        assert Path(file).parent == tmp_path
        # The line holds a query word, or is the first text line of a Section under the heading.
        assert text[int(number) - 1].strip()
        assert any(
            heading.split(" > ")[-1] in above
            for above in text[: int(number)]
            if above.startswith("#")
        )
        assert "[" in snippet and "]" in snippet
    assert any("prompt-caching" in line for line in lines)
    assert "foundry" not in "".join(lines)


def test_search_understands_word_forms(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    add_text(tmp_path, store, "forms", "# Reuse\n\nThe prefix was cached by the server.\n")
    run_cli(["index", "--store", str(store)])

    result = run_cli(["search", "caching", "--store", str(store)])

    lines = result_lines(result.stdout)
    assert len(lines) == 1
    assert "[cached]" in lines[0]
    location, heading, _ = lines[0].split(" | ", 2)
    file, number = location.rsplit(":", 1)
    assert heading == "Reuse"
    # No line holds "caching" as written, so the line is the Section's first text line.
    assert Path(file).read_text(encoding="utf-8").splitlines()[int(number) - 1] == (
        "The prefix was cached by the server."
    )


def test_search_limit_caps_the_number_of_results(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    default = run_cli(["search", "cache", "--store", str(tmp_path)])
    two = run_cli(["search", "cache", "--limit", "2", "--store", str(tmp_path)])

    assert len(result_lines(default.stdout)) == 5
    assert len(result_lines(two.stdout)) == 2
    assert result_lines(two.stdout) == result_lines(default.stdout)[:2]


def search(store: Path, *argv: str, tag: str | None = None) -> list[str]:
    env = {"LOREKEEP_STORE": str(store)} | ({"LOREKEEP_TAG": tag} if tag else {})
    result = run_cli(["search", *argv], env=env)
    assert result.exit_code == 0, result.stderr
    return result.stdout.splitlines()


def files_of(lines: list[str]) -> set[str]:
    return {Path(line.split(" | ")[0].rsplit(":", 1)[0]).name for line in result_lines_of(lines)}


def result_lines_of(lines: list[str]) -> list[str]:
    return [line for line in lines if " | " in line]


def test_only_the_latest_version_of_a_source_is_searched(tmp_path: Path) -> None:
    three_twins(tmp_path)
    newer = write_version(
        tmp_path,
        FIXTURES / "aws-prompt-caching.twin",
        fetched_at="2026-10-05T00:00:00Z",
        url=ANTHROPIC,
        publisher="anthropic",
        authority="primary",
    )
    run_cli(["index", "--store", str(tmp_path)])

    lines = search(tmp_path, "prompt caching", "--all", "--limit", "100")

    anthropic_files = {name for name in files_of(lines) if name.startswith("platform.claude.com")}
    assert anthropic_files == {newer.name}


def test_a_scoped_search_counts_other_sources_not_sections_and_all_drops_the_line(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    scoped = search(tmp_path, "caching", tag="microsoft")
    everything = search(tmp_path, "caching", "--all", tag="microsoft")

    assert result_lines_of(scoped) == []
    assert scoped[-1] == "+2 matches under other tags (--all)"
    assert len(result_lines_of(everything)) == 5
    assert not any(line.startswith("+") for line in everything)
    assert {name.split("--")[0] for name in files_of(everything)} <= {
        "platform.claude.com",
        "docs.aws.amazon.com",
    }


def test_the_run_tag_scopes_the_search_and_the_line_ends_it(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    lines = search(tmp_path, "caching", "--limit", "100", tag="anthropic")

    assert {name.split("--")[0] for name in files_of(lines)} == {"platform.claude.com"}
    assert lines[-1] == "+1 matches under other tags (--all)"


def test_without_a_tag_the_scope_is_everything_and_no_line_is_printed(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    lines = search(tmp_path, "caching", "--limit", "100")

    assert {name.split("--")[0] for name in files_of(lines)} == {
        "platform.claude.com",
        "docs.aws.amazon.com",
    }
    assert not any(line.startswith("+") for line in lines)


def test_tag_publisher_and_authority_filter_the_scope(tmp_path: Path) -> None:
    three_twins(tmp_path)
    # The filters read the host rules, not the frontmatter: Foundry is `official` by this rule.
    (tmp_path / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "learn.microsoft.com/"\npublisher = "microsoft"\n'
        'authority = "official"\ntwin = "accept-header"\n',
        encoding="utf-8",
    )
    run_cli(["index", "--store", str(tmp_path)])

    def hosts(*argv: str) -> set[str]:
        found = set()
        for query in ("agents", "caching"):
            lines = search(tmp_path, query, "--limit", "100", *argv)
            found |= {name.split("--")[0] for name in files_of(lines)}
        return found

    assert hosts("--tag", "aws", "--tag", "microsoft") == {
        "docs.aws.amazon.com",
        "learn.microsoft.com",
    }
    assert hosts("--publisher", "aws", "--all") == {"docs.aws.amazon.com"}
    assert hosts("--authority", "official", "--all") == {"learn.microsoft.com"}
    scoped = search(tmp_path, "caching", "--tag", "aws", "--publisher", "aws")
    assert result_lines_of(scoped)
    assert not any(line.startswith("+") for line in scoped)


def test_exact_matches_the_identifier_as_written_and_not_its_words_apart(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    add_text(
        tmp_path,
        store,
        "identifiers",
        "# Breakpoints\n\nSet cache_control on a block.\n\n"
        "# Prose\n\nThe cache control header is unrelated.\n\n"
        "# Capitals\n\nCache_Control is not the field.\n",
    )
    run_cli(["index", "--store", str(store)])

    exact = run_cli(["search", "--exact", "cache_control", "--store", str(store)])
    words = run_cli(["search", "cache_control", "--store", str(store)])

    lines = result_lines(exact.stdout)
    assert len(lines) == 1
    assert " | Breakpoints | " in lines[0]
    assert "[cache_control]" in lines[0]
    assert len(result_lines(words.stdout)) == 3


def test_json_prints_results_and_the_other_tags_count(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])

    result = run_cli(
        ["search", "caching", "--json", "--limit", "3"],
        env={"LOREKEEP_STORE": str(tmp_path), "LOREKEEP_TAG": "aws"},
    )

    data = json.loads(result.stdout)
    assert set(data) == {"results", "other_tags"}
    assert data["other_tags"] == 1
    assert len(data["results"]) == 3
    for hit in data["results"]:
        assert set(hit) == {
            "file",
            "line",
            "heading_line",
            "heading",
            "snippet",
            "url",
            "tag",
            "publisher",
            "authority",
        }
        assert Path(hit["file"]).parent == tmp_path
        assert isinstance(hit["line"], int)
        assert hit["url"] == AWS
        assert hit["tag"] == ["aws"]
        assert "[" in hit["snippet"]
    assert len(result.stdout.strip().splitlines()) == 1


@contextlib.contextmanager
def store_lock_held(store: Path) -> Iterator[None]:
    """Hold `.lorekeep.lock` the way another worker would, through a descriptor of its own."""
    fd = os.open(store / ".lorekeep.lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_search_without_an_index_builds_it_under_the_store_lock_and_answers(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    assert not (tmp_path / "sources.db").exists()
    outcome: list[Result] = []

    with store_lock_held(tmp_path):
        worker = threading.Thread(
            target=lambda: outcome.append(
                run_cli(["search", "caching", "--all", "--store", str(tmp_path)])
            )
        )
        worker.start()
        worker.join(timeout=0.5)
        assert worker.is_alive(), "search built the Index without waiting for the lock"
        assert not (tmp_path / "sources.db").exists()
    worker.join(timeout=30)

    assert outcome and outcome[0].exit_code == 0, outcome
    assert len(result_lines(outcome[0].stdout)) == 5
    with sqlite3.connect(tmp_path / "sources.db") as con:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    assert meta["md_files"] == "3"
    for name in ("tags.csv", "checks.csv", "aliases.csv"):
        stat = (tmp_path / name).stat()
        assert meta[f"{name}:size"] == str(stat.st_size)
        assert meta[f"{name}:mtime"] == str(stat.st_mtime_ns)
    assert meta["citations.csv:size"] == "missing"


@contextlib.contextmanager
def only_readable(store: Path, *keep: Path) -> Iterator[None]:
    """Every Version file but `keep` stripped of its permission bits: a scan of the Store opens
    them all and fails on the first, a current Index opens only the file it names."""
    others = [path for path in store.glob("*.md") if path not in keep]
    for path in others:
        path.chmod(0)
    try:
        yield
    finally:
        for path in others:
            path.chmod(0o644)


def test_the_lookup_answers_from_a_current_index_without_scanning_or_locking(
    tmp_path: Path,
) -> None:
    three_twins(tmp_path)
    newer = write_version(
        tmp_path,
        FIXTURES / "aws-prompt-caching.twin",
        fetched_at="2026-10-05T00:00:00Z",
        url=ANTHROPIC,
    )
    run_cli(["index", "--store", str(tmp_path)])
    rules = load_project(tmp_path).hosts
    [foundry] = [path for path in tmp_path.glob("*.md") if path.name.startswith("learn.microsoft")]

    found: list[VersionInfo | None] = []
    with only_readable(tmp_path, newer, foundry), store_lock_held(tmp_path):
        worker = threading.Thread(
            target=lambda: found.append(latest(tmp_path, ANTHROPIC + ".md", rules))
        )
        worker.start()
        worker.join(timeout=5)
        by_alias = latest(tmp_path, FOUNDRY + "-old", rules)

    assert found and found[0] is not None and found[0].path == newer
    assert found[0].url == ANTHROPIC
    assert by_alias is not None and by_alias.url == FOUNDRY


def test_the_lookup_scans_when_the_index_is_stale(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])
    by_hand = write_version(
        tmp_path,
        FIXTURES / "aws-prompt-caching.twin",
        fetched_at="2026-10-05T00:00:00Z",
        url=ANTHROPIC,
    )

    found = latest(tmp_path, ANTHROPIC, load_project(tmp_path).hosts)

    assert found is not None and found.path == by_hand


def test_an_unknown_url_on_a_current_index_is_not_found_without_scanning(tmp_path: Path) -> None:
    three_twins(tmp_path)
    run_cli(["index", "--store", str(tmp_path)])
    edges, transport = edges_over()

    with only_readable(tmp_path):
        result = get(tmp_path, edges, "https://example.test/nowhere")

    assert result.exit_code == 1
    assert "nothing stored for https://example.test/nowhere" in result.stderr
    assert transport.misses == ["https://example.test/nowhere"]
    assert len(list(tmp_path.glob("*.md"))) == 3


def test_an_empty_query_is_a_one_line_error(tmp_path: Path) -> None:
    three_twins(tmp_path)

    result = run_cli(["search", "  ", "--store", str(tmp_path)])

    assert result.exit_code == 2
    assert result.stderr.count("\n") == 1 and "query" in result.stderr


def test_index_counts_aliases_in_plain_english(tmp_path: Path) -> None:
    result = run_cli(["index", "--store", str(tmp_path)])

    assert result.exit_code == 0
    assert "0 aliases" in result.stdout
