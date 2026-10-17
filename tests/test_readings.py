"""Readings and the rule language (v1.3 ticket 01): `[[readings]]` rules in the Store's
`lorekeep.toml` make a Reading of a Version in `.cache/readings/`, which `get` returns and
`read` builds; a rule never touches a fence or a table line, and the over-removal guard holds back
a rule that removes far more than when it was accepted.

Each test names its fixture: the Fern Twin with the llms.txt banner, the Microsoft Learn Twin of
the Retry pattern, the AI Act cut from the first Store's Version, and one synthesised page with a
fence and a table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lorekeep.provenance import now
from lorekeep.readings import READINGS_DIR
from tests.support import FIXTURES, edges_over, get, lorekeep, make_store, write_version
from tests.test_helpers import read_version

RAIL_TYPES = (
    "https://docs.nvidia.com/nemo/guardrails/latest/about-nemo-guardrails-library/rail-types"
)
RETRY = "https://learn.microsoft.com/en-us/azure/architecture/patterns/retry"
AI_ACT = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
FENCES = "https://docs.example.test/guide/fences-and-tables"

# The ticket's rule was `llms\.txt|For clean Markdown`; the banner's last line names neither (it
# points at `…/_mcp/server`), and `drop_leading` stops at the last line that matches.
FERN_RULE = (
    '[[readings]]\nprefix = "docs.nvidia.com/"\n'
    'drop_leading = "llms\\\\.txt|For clean Markdown|/_mcp/server"\n'
)
LEARN_RULE = (
    '[[readings]]\nprefix = "learn.microsoft.com/"\n'
    'strip_title_suffix = " - Azure Architecture Center \\\\| Microsoft Learn$"\n'
)
ARTICLE_RULE = (
    '[[readings]]\nprefix = "eur-lex.europa.eu/"\nheading_before = "^Article \\\\d+$"\nlevel = 2\n'
)
CHROME = "Edit this page on GitHub"


def store_with(tmp_path: Path, *rules: str) -> Path:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text("\n".join(rules), encoding="utf-8")
    return store


def set_rules(store: Path, *rules: str) -> None:
    (store / "lorekeep.toml").write_text("\n".join(rules), encoding="utf-8")


def stored(store: Path, fixture: str, **fields: Any) -> Path:
    """A Version written straight from a fixture folder, fetched now so `get` asks nothing."""
    return write_version(store, FIXTURES / fixture, fetched_at=now(), **fields)


def readings_of(store: Path) -> list[Path]:
    return sorted((store / READINGS_DIR).glob("*.md"))


def lines_of(data: bytes) -> list[bytes]:
    return data.splitlines(keepends=True)


def get_json(store: Path, url: str, fixtures: tuple[str, ...] = ()) -> dict[str, Any]:
    result = get(store, edges_over(*fixtures)[0], "--json", url, tag="test")
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)


def test_a_fern_banner_rule_gives_a_reading_that_starts_at_the_title(tmp_path: Path) -> None:
    """`guardrails-rail-types.twin`: the 12-line llms.txt banner before `# Guardrail Types`."""
    store = store_with(tmp_path, FERN_RULE)
    edges, _ = edges_over("guardrails-rail-types.twin")

    text = get(store, edges, RAIL_TYPES, tag="nvidia")
    printed = get_json(store, RAIL_TYPES)

    assert text.exit_code == 0, text.stderr
    [version] = store.glob("*.md")
    [reading] = readings_of(store)
    assert reading.name == version.name
    assert text.stdout == f"{reading}\n"
    assert printed["path"] == str(reading)
    assert printed["version"] == str(version)
    head, body = read_version(version)
    assert printed["url"] == head["url"] == RAIL_TYPES
    assert printed["sha256"] == head["sha256"]
    reading_head, reading_body = read_version(reading)
    assert reading_body.startswith(b"# Guardrail Types\n")
    assert set(lines_of(reading_body)) <= set(lines_of(body))
    assert b"llms.txt" not in reading_body
    assert reading_head["url"] == RAIL_TYPES
    assert reading_head["version"] == version.name
    assert reading_head["title"] == "Guardrail Types"
    assert len(reading_head["rules"]) == 64
    assert reading_head["sha256"] != head["sha256"]
    assert "warnings" not in reading_head


def test_an_article_rule_puts_a_heading_before_each_article_of_the_ai_act(tmp_path: Path) -> None:
    """`eur-lex-ai-act.v1`: the AI Act's head, recitals 1 and 2 and Articles 1 to 3, with no
    heading but the footer's `Need help?`."""
    store = store_with(tmp_path, ARTICLE_RULE)
    version = stored(store, "eur-lex-ai-act.v1", converter="trafilatura 2.3.1")

    printed = get_json(store, AI_ACT)

    [reading] = readings_of(store)
    assert printed["path"] == str(reading)
    _, body = read_version(version)
    _, reading_body = read_version(reading)
    lines = lines_of(reading_body)
    added = [line for line in lines if line not in set(lines_of(body))]
    assert added == [b"## Article 1\n", b"## Article 2\n", b"## Article 3\n"]
    for heading in added:
        article = heading.removeprefix(b"## ")
        assert lines[lines.index(heading) + 1] == article


def test_an_article_already_under_a_heading_and_one_in_a_fence_get_none(tmp_path: Path) -> None:
    """`readings-fence-table.v1` (synthesised): `Article 7` inside a fence, `Article 9` right
    under `## Article 9`, `Article 10` under nothing."""
    rule = ARTICLE_RULE.replace("eur-lex.europa.eu/", "docs.example.test/")
    store = store_with(tmp_path, rule)
    stored(store, "readings-fence-table.v1")

    get_json(store, FENCES)

    [reading] = readings_of(store)
    _, reading_body = read_version(reading)
    assert reading_body.count(b"## Article") == 2
    assert b"## Article 10\nArticle 10\n" in reading_body
    assert b"## Article 7" not in reading_body


def test_drop_lines_never_removes_a_fence_or_table_line(tmp_path: Path) -> None:
    """`readings-fence-table.v1` (synthesised): the chrome line stands alone, in a fence and in a
    pipe table."""
    rule = (
        f'[[readings]]\nprefix = "docs.example.test/"\ndrop_lines = "^{CHROME}$|\\\\| {CHROME}"\n'
    )
    store = store_with(tmp_path, rule)
    version = stored(store, "readings-fence-table.v1")

    get_json(store, FENCES)

    [reading] = readings_of(store)
    _, body = read_version(version)
    _, reading_body = read_version(reading)
    assert body.count(CHROME.encode()) == 5
    assert reading_body.count(CHROME.encode()) == 2
    assert f"```text\n{CHROME}\nArticle 7\n```\n".encode() in reading_body
    assert f"| table | {CHROME} |\n".encode() in reading_body
    assert set(lines_of(reading_body)) <= set(lines_of(body))


def test_a_title_suffix_rule_cuts_the_heading_and_title_of_microsoft_learn(tmp_path: Path) -> None:
    """`ms-retry-pattern.twin`: the first Store's Twin of the Retry pattern, headed
    `# Retry pattern - Azure Architecture Center | Microsoft Learn`."""
    store = store_with(tmp_path, LEARN_RULE)
    edges, _ = edges_over("ms-retry-pattern.twin")

    result = get(store, edges, "--json", RETRY, tag="azure")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    before = version.read_bytes()
    [reading] = readings_of(store)
    assert json.loads(result.stdout)["path"] == str(reading)
    head, body = read_version(version)
    reading_head, reading_body = read_version(reading)
    assert reading_body.startswith(b"# Retry pattern\n")
    assert reading_head["title"] == "Retry pattern"
    assert head["title"] == "Retry pattern - Azure Architecture Center | Microsoft Learn"
    assert body.startswith(b"# Retry pattern - Azure Architecture Center | Microsoft Learn\n")
    assert lines_of(reading_body)[1:] == lines_of(body)[1:]
    get(store, edges_over()[0], RETRY, tag="azure")
    assert version.read_bytes() == before


def test_a_version_no_rule_touches_has_no_reading(tmp_path: Path) -> None:
    """`ms-retry-pattern.twin` under the Fern rule, which names another host, and under a Learn
    rule whose suffix the page does not carry."""
    store = store_with(tmp_path, FERN_RULE)
    edges, _ = edges_over("ms-retry-pattern.twin")

    text = get(store, edges, RETRY, tag="azure")
    printed = get_json(store, RETRY)
    set_rules(store, LEARN_RULE.replace("Azure Architecture Center", "Azure Updates"))
    again = get_json(store, RETRY)

    [version] = store.glob("*.md")
    assert text.stdout == f"{version}\n"
    assert printed["path"] == again["path"] == str(version)
    assert "version" not in printed
    assert "version" not in again
    assert readings_of(store) == []


def test_read_builds_the_missing_readings_and_a_rules_change_makes_them_stale(
    tmp_path: Path,
) -> None:
    """`eur-lex-ai-act.v1`, `readings-fence-table.v1` and `guardrails-rail-types.twin` under three
    rules; the AI Act's rule then changes level."""
    store = store_with(tmp_path, FERN_RULE, ARTICLE_RULE, LEARN_RULE)
    edges, _ = edges_over()
    stored(store, "eur-lex-ai-act.v1")
    stored(store, "guardrails-rail-types.twin", url=RAIL_TYPES, converter="md-twin")
    stored(store, "readings-fence-table.v1")

    first = lorekeep(store, edges, "read")
    second = lorekeep(store, edges, "read")
    set_rules(store, FERN_RULE, ARTICLE_RULE.replace("level = 2", "level = 3"), LEARN_RULE)
    printed = get_json(store, AI_ACT)
    third = lorekeep(store, edges, "read")
    forced = lorekeep(store, edges, "read", "--force")
    scoped = lorekeep(store, edges, "read", "--force", "--prefix", "https://eur-lex.europa.eu/")

    assert first.exit_code == 0, first.stderr
    assert first.stdout == "Built 2 Readings, 0 current\n"
    assert second.stdout == "Built 0 Readings, 2 current\n"
    assert b"### Article 1\n" in Path(printed["path"]).read_bytes()
    assert third.stdout == "Built 0 Readings, 2 current\n"
    assert forced.stdout == "Built 2 Readings, 0 current\n"
    assert scoped.stdout == "Built 1 Reading, 0 current\n"


def test_a_rule_removing_more_than_twice_its_share_is_held_back(tmp_path: Path) -> None:
    """`readings-fence-table.v1` (synthesised): 25 lines, 3 of them chrome outside the fence and
    the table, so the rule removes 12% where it was accepted at 5%."""
    rules = (
        f'[[readings]]\nprefix = "docs.example.test/"\ndrop_lines = "^{CHROME}$"\nremoves = "5%"\n',
        ARTICLE_RULE.replace("eur-lex.europa.eu/", "docs.example.test/"),
    )
    store = store_with(tmp_path, *rules)
    version = stored(store, "readings-fence-table.v1")
    warning = (
        f"lorekeep: warning: {FENCES}: rule docs.example.test/ drop_lines removed 12% "
        "(accepted at 5%)\n"
    )

    built = lorekeep(store, edges_over()[0], "read")
    returned = get(store, edges_over()[0], FENCES, tag="test")

    assert warning in built.stderr
    assert warning in returned.stderr
    [reading] = readings_of(store)
    assert returned.stdout == f"{reading}\n"
    _, body = read_version(version)
    reading_head, reading_body = read_version(reading)
    assert reading_body.count(CHROME.encode()) == body.count(CHROME.encode())
    assert b"## Article 10\n" in reading_body
    assert reading_head["warnings"] == [warning.split(": ", 3)[3].strip()]

    set_rules(store, rules[0].replace('removes = "5%"', 'removes = "6%"'), rules[1])
    accepted = lorekeep(store, edges_over()[0], "read")

    assert "removed" not in accepted.stderr
    _, reading_body = read_version(reading)
    assert reading_body.count(CHROME.encode()) == 2


def test_an_engine_rule_applies_to_the_versions_that_engine_made(tmp_path: Path) -> None:
    """`guardrails-rail-types.twin` is a Fern Twin (its banner says so); the synthesised
    `readings-fence-table.v1` is not, though its host would match any prefix rule."""
    rule = '[[readings]]\nengine = "fern"\ndrop_leading = "llms\\\\.txt|/_mcp/server"\n'
    store = store_with(tmp_path, rule)
    stored(store, "guardrails-rail-types.twin", url=RAIL_TYPES, converter="md-twin")
    stored(store, "readings-fence-table.v1", converter="md-twin")

    result = lorekeep(store, edges_over()[0], "read")

    assert result.stdout == "Built 1 Reading, 0 current\n"
    [reading] = readings_of(store)
    assert reading.name.startswith("docs.nvidia.com--")
    assert read_version(reading)[1].startswith(b"# Guardrail Types\n")


def test_a_reading_rule_that_cannot_be_used_is_a_usage_error(tmp_path: Path) -> None:
    """No fixture: `lorekeep.toml` alone."""
    store = make_store(tmp_path)
    cases = {
        '[[readings]]\nprefix = "a.test/"\nengine = "fern"\ndrop_lines = "x"\n': (
            "readings[1] needs exactly one of prefix and engine"
        ),
        '[[readings]]\nprefix = "a.test/"\ndrop_lines = "x"\ndrop_leading = "y"\n': (
            "readings[1] needs exactly one of drop_leading"
        ),
        '[[readings]]\nprefix = "a.test/"\nheading_before = "x"\n': (
            "readings[1].level must be a heading level from 1 to 6"
        ),
        '[[readings]]\nprefix = "a.test/"\ndrop_lines = "("\n': (
            "readings[1].drop_lines is not a regular expression"
        ),
        '[[readings]]\nengine = "hugo"\ndrop_lines = "x"\n': "readings[1].engine must be one of",
        '[[readings]]\nprefix = "a.test/"\ndrop_lines = "x"\nremoves = 4\n': (
            'readings[1].removes must be written with its unit, as "4%"'
        ),
        '[[readings]]\nprefix = "a.test/"\ndrop_leading = "x"\nremoves = "4%"\n': (
            'readings[1].removes must be written with its unit, as "31 lines"'
        ),
        '[[readings]]\nprefix = "a.test/"\nstrip_title_suffix = "x"\nremoves = "0%"\n': (
            "readings[1].removes belongs to drop_leading, drop_trailing, drop_lines"
        ),
    }
    for toml, message in cases.items():
        set_rules(store, toml)

        result = lorekeep(store, edges_over()[0], "read")

        assert result.exit_code == 2
        assert message in result.stderr
