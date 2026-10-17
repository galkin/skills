"""`search` points at the matching line, reads escaped identifiers and broken fences, and says
"no matches"; `--version` and `status --rules`."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from tests.support import FIXTURES, Result, run_cli, write_version

KV_CACHE = FIXTURES / "trtllm-kv-cache.v1"
VLLM = FIXTURES / "vllm-cli-serve.v1"
PERMALINK = re.compile(r"\[[#¶]\]\([^)]*\)")


def stored(store: Path, fixture: Path) -> Path:
    path = write_version(store, fixture, fetched_at="2026-10-17T00:00:00Z")
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    return path


def search(store: Path, *argv: str, tag: str | None = None) -> Result:
    env = {"LOREKEEP_STORE": str(store)} | ({"LOREKEEP_TAG": tag} if tag else {})
    result = run_cli(["search", *argv], env=env)
    assert result.exit_code == 0, result.stderr
    return result


def number_of(path: Path, text: str) -> int:
    """The 1-based line of the file that contains `text`; exactly one must."""
    found = [n for n, line in enumerate(path.read_text().splitlines(), 1) if text in line]
    assert len(found) == 1, (text, found)
    return found[0]


def add_text(tmp_path: Path, store: Path, title: str, text: str, tag: str = "owner") -> Path:
    source = tmp_path / f"{title}.md"
    source.write_text(text, encoding="utf-8")
    result = run_cli(["add", str(source), "--title", title, "--store", str(store), "--tag", tag])
    assert result.exit_code == 0, result.stderr
    return Path(result.stdout.strip())


def test_exact_prints_the_line_of_the_match_and_json_gives_the_heading_line_beside_it(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    text = "# Model\n\n" + "".join(f"Line {n} of prose.\n" for n in range(12))
    text += "\nfree_gpu_memory_fraction: 0.7\n"
    path = add_text(tmp_path, store, "plain identifier", text)
    run_cli(["index", "--store", str(store)])
    heading, match = number_of(path, "# Model"), number_of(path, "free_gpu_memory_fraction")
    assert match - heading == 15

    lines = search(store, "--exact", "free_gpu_memory_fraction").stdout.splitlines()
    data = json.loads(search(store, "--exact", "free_gpu_memory_fraction", "--json").stdout)

    assert lines[0].startswith(f"{path}:{match} | Model | ")
    [hit] = data["results"]
    assert (hit["line"], hit["heading_line"]) == (match, heading)


def test_exact_finds_an_identifier_the_converter_escaped_and_points_at_its_line(
    tmp_path: Path,
) -> None:
    path = stored(tmp_path, KV_CACHE)
    match = number_of(path, r"free\_gpu\_memory\_fraction: 0.7")

    result = search(tmp_path, "--exact", "free_gpu_memory_fraction", "--json")
    escaped = search(tmp_path, "--exact", r"free\_gpu\_memory\_fraction", "--json")

    [hit] = json.loads(result.stdout)["results"]
    assert hit["line"] == match
    assert hit["heading_line"] == number_of(path, "### Fields")
    assert hit["heading"] == "KvCacheConfig > Fields"
    assert "[free_gpu_memory_fraction]" in hit["snippet"]
    assert json.loads(escaped.stdout)["results"] == [hit]


def test_a_word_search_points_at_the_first_line_with_a_query_word_after_unescaping(
    tmp_path: Path,
) -> None:
    path = stored(tmp_path, KV_CACHE)

    [hit] = json.loads(search(tmp_path, "GPU MEMORY", "--json").stdout)["results"]

    assert hit["line"] == number_of(path, r"free\_gpu\_memory\_fraction: 0.7")


def test_a_stemmed_match_with_no_literal_word_points_at_the_first_content_line(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    path = add_text(tmp_path, store, "forms", "# Reuse\n\nThe prefix\nwas cached by the server.\n")
    run_cli(["index", "--store", str(store)])

    [hit] = json.loads(search(store, "caching", "--json").stdout)["results"]

    assert hit["line"] == number_of(path, "The prefix")
    assert hit["heading_line"] == number_of(path, "# Reuse")


def test_heading_paths_lose_their_permalinks_and_text_before_any_heading_is_top(
    tmp_path: Path,
) -> None:
    path = stored(tmp_path, KV_CACHE)

    text = search(tmp_path, "parsed by the server").stdout.splitlines()
    [hit] = json.loads(search(tmp_path, "parsed by the server", "--json").stdout)["results"]
    top = search(tmp_path, "--exact", "LLM API reference").stdout.splitlines()
    [top_hit] = json.loads(search(tmp_path, "--exact", "LLM API reference", "--json").stdout)[
        "results"
    ]

    assert text[0].split(" | ")[1] == "Enable Tool Calling"
    assert hit["heading"] == "Enable Tool Calling"
    assert top[0].split(" | ")[:2] == [f"{path}:{number_of(path, 'LLM API reference')}", "(top)"]
    assert (top_hit["heading"], top_hit["heading_line"]) == ("", None)


def section_headings(store: Path) -> list[str]:
    with sqlite3.connect(store / "sources.db") as con:
        return [heading for (heading,) in con.execute("SELECT heading FROM sections ORDER BY ord")]


def test_an_inline_fence_on_the_vllm_page_does_not_swallow_the_headings_after_it(
    tmp_path: Path,
) -> None:
    path = stored(tmp_path, VLLM)
    body = path.read_text().split("---\n", 2)[2]
    written = [
        PERMALINK.sub("", line.lstrip("#").strip()) for line in body.splitlines() if line[:1] == "#"
    ]

    headings = section_headings(tmp_path)

    assert [heading.split(" > ")[-1] for heading in headings] == written
    assert all("[¶]" not in heading for heading in headings)
    assert headings[2] == "Frontend > `--chat-template`"
    json_section = search(tmp_path, "--exact", '"base_model_name": "id"').stdout
    assert " | Frontend > `--lora-modules` | " in json_section


def test_a_fence_left_open_ends_at_the_next_heading_and_a_closed_one_keeps_its_comments(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    add_text(
        tmp_path,
        store,
        "open fence",
        "# Setup\n\n```bash\n# a comment\necho one\n```\n\n## Run\n\n```python\nx = 1\n\n"
        "## Stop\n\nThe end.\n",
    )
    run_cli(["index", "--store", str(store)])

    assert section_headings(store) == ["Setup", "Setup > Run", "Setup > Stop"]


def test_a_query_after_double_dash_may_start_with_a_dash(tmp_path: Path) -> None:
    path = stored(tmp_path, VLLM)

    result = search(tmp_path, "--", "--max-model-len", "--exact")
    words = search(tmp_path, "--json", "--", "--max-model-len")

    [line] = result.stdout.splitlines()
    assert line.startswith(f"{path}:{number_of(path, 'When passing via `--max-model-len`')} | ")
    assert json.loads(words.stdout)["results"]


def test_two_queries_are_a_usage_error(tmp_path: Path) -> None:
    stored(tmp_path, VLLM)

    result = run_cli(["search", "one", "--", "two", "--store", str(tmp_path)])

    assert result.exit_code == 2
    assert result.stderr.startswith("lorekeep: error:")


def test_no_hit_prints_no_matches_and_the_other_tags_line_only_above_zero(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    for n in range(3):
        add_text(tmp_path, store, f"zebra {n}", f"# Stripes\n\nA zebra, number {n}.\n", tag="a")
    add_text(tmp_path, store, "horse", "# Mane\n\nA horse.\n", tag="b")

    nothing = search(store, "unicorn", tag="b")
    nothing_anywhere = search(store, "unicorn")
    elsewhere = search(store, "zebra", tag="b")
    as_json = json.loads(search(store, "zebra", "--json", tag="b").stdout)

    assert nothing.stdout == "no matches\n"
    assert nothing_anywhere.stdout == "no matches\n"
    assert elsewhere.stdout == "no matches\n+3 matches under other tags (--all)\n"
    assert as_json == {"results": [], "other_tags": 3}


def test_version_prints_the_package_version() -> None:
    result = run_cli(["--version"])

    assert result.exit_code == 0
    assert result.stdout == "lorekeep 0.1.1\n"


def test_status_prints_host_rules_only_with_rules(tmp_path: Path) -> None:
    plain = run_cli(["status", "--store", str(tmp_path)])
    with_rules = run_cli(["status", "--rules", "--store", str(tmp_path)])

    assert plain.stdout.splitlines()[-1].startswith("Freshness window: ")
    assert "Host rules" not in plain.stdout
    assert with_rules.stdout.startswith(plain.stdout)
    rules = with_rules.stdout[len(plain.stdout) :].splitlines()
    assert rules[0].startswith("Host rules (")
    assert any(line.startswith("  platform.claude.com/  anthropic  primary") for line in rules)


def test_an_index_built_by_v1_is_rebuilt_before_a_search_reads_it(tmp_path: Path) -> None:
    path = stored(tmp_path, KV_CACHE)
    with sqlite3.connect(tmp_path / "sources.db") as con:
        con.execute("DELETE FROM meta WHERE key = 'schema'")
        con.execute("DROP TABLE sections_fts")
        con.execute("ALTER TABLE sections DROP COLUMN heading_line")
        con.execute(
            "CREATE VIRTUAL TABLE sections_fts USING fts5(heading, body, content='sections', "
            "content_rowid='id', tokenize='porter unicode61')"
        )
        con.execute("INSERT INTO sections_fts(sections_fts) VALUES('rebuild')")

    result = run_cli(
        ["search", "--exact", "free_gpu_memory_fraction", "--json"],
        env={"LOREKEEP_STORE": str(tmp_path)},
    )

    assert result.exit_code == 0, result.stderr
    assert "rebuilt" in result.stderr
    [hit] = json.loads(result.stdout)["results"]
    assert hit["heading_line"] == number_of(path, "### Fields")
