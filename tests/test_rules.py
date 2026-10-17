"""Reading rules a proposer suggests (v1.3 ticket 03): `rules sample` prints the Versions a
proposer reads, `rules check` measures its candidates against the limits and writes nothing,
`rules accept` writes the passing ones into `lorekeep.toml` with `accepted` and `removes` and
builds their Readings; `removes` carries its unit and the guard compares in it.

Each test names its fixture: five Fern Twins of `docs.nvidia.com` (NeMo Gym's Build Verifiers,
Guardrails' Rail Types and Jailbreak Protection, Dynamo's Router Guide and Fast Model Loading),
each with the llms.txt banner before its H1, and `readings-candidates-fern.toml`, the candidates a
proposer returns for `docs.nvidia.com/`.
"""

from __future__ import annotations

import datetime
import json
import tomllib
from pathlib import Path

from lorekeep.provenance import now
from tests.support import FIXTURES, Result, edges_over, lorekeep, make_store, write_version
from tests.test_helpers import read_version
from tests.test_readings import readings_of, set_rules

CANDIDATES = FIXTURES / "readings-candidates-fern.toml"
# The five Fern Twins by the lines of their body: 39, 42, 63, 159 and 240.
GYM = "nemo-gym-build-verifiers.twin"
RAIL_TYPES = "guardrails-rail-types.twin"
ROUTER = "dynamo-router-guide.twin"
JAILBREAK = "guardrails-jailbreak-protection.twin"
LOADING = "dynamo-fast-model-loading.twin"
FERN = (GYM, RAIL_TYPES, ROUTER, JAILBREAK, LOADING)
BANNER = "llms\\\\.txt|For clean Markdown|/_mcp/server"
OWNER_TOML = """\
# The owner's settings, which rules accept leaves as written.
bucket = "a-bucket"
freshness_days = 14

[[hosts]]
prefix = "docs.example.test/"  # a host of the owner's
publisher = "example"
authority = "primary"
"""


def fern_store(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    """A Store holding the five Fern Twins as Versions of their pages."""
    store = make_store(tmp_path)
    stored: dict[str, Path] = {}
    for fixture in FERN:
        twin = json.loads((FIXTURES / fixture / "response.json").read_text())["url"]
        stored[fixture] = write_version(
            store,
            FIXTURES / fixture,
            fetched_at=now(),
            url=twin.removesuffix(".md"),
            converter="md-twin",
        )
    return store, stored


def rules(store: Path, *argv: str) -> Result:
    return lorekeep(store, edges_over()[0], "rules", *argv)


def files(store: Path) -> dict[str, bytes]:
    """Every file under the Store, at any depth, with its bytes."""
    return {
        str(path.relative_to(store)): path.read_bytes()
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }


def verdicts(output: str) -> list[str]:
    """The verdict line of every candidate `rules check` reported, in order."""
    return [
        line.strip() for line in output.splitlines() if line.startswith(("    pass", "    fail"))
    ]


def test_rules_sample_prints_the_shortest_and_the_longest_first(tmp_path: Path) -> None:
    """The five Fern Twins; a Microsoft Learn Twin outside the prefix is never printed."""
    store, stored = fern_store(tmp_path)
    write_version(store, FIXTURES / "ms-retry-pattern.twin", fetched_at=now())

    five = rules(store, "sample", "docs.nvidia.com/")
    two = rules(store, "sample", "docs.nvidia.com/", "--sample", "2")

    assert five.exit_code == 0, five.stderr
    assert five.stdout.splitlines() == [
        str(stored[name]) for name in (GYM, LOADING, RAIL_TYPES, ROUTER, JAILBREAK)
    ]
    assert two.stdout.splitlines() == [str(stored[GYM]), str(stored[LOADING])]


def test_rules_check_measures_each_candidate_and_writes_nothing(tmp_path: Path) -> None:
    """`readings-candidates-fern.toml` over the five Fern Twins: the banner rule passes; 41% of
    the Router Guide, a fence line of Fast Model Loading, and a leading block whose last match
    is after Fast Model Loading's first heading fail."""
    store, stored = fern_store(tmp_path)
    before = files(store)

    result = rules(store, "check", str(CANDIDATES))

    assert result.exit_code == 0, result.stderr
    assert files(store) == before
    reports = result.stdout.split("\n[")
    assert reports[0].startswith(f'[1] docs.nvidia.com/ drop_leading = "{BANNER}"\n')
    assert (
        "    over 5 Versions: 91 lines removed (per Version min 12, median 15, max 26)\n"
        in reports[0]
    )
    assert "    | > This page is for version Latest (v1.5.1) (default).\n" in reports[0]
    assert reports[0].endswith("    pass")
    assert "at most 41% of a Version" in reports[1]
    loading = stored[LOADING].name
    assert verdicts(result.stdout) == [
        "pass",
        f"fail: removes 41% of {stored[ROUTER].name}, more than 30%",
        f"fail: matches a fence line, {loading}:134",
        f"fail: matches {loading}:171, after the first heading (line 41)",
    ]
    assert result.stdout.endswith("Checked 4 candidates: 1 pass, 3 fail\n")
    lines = stored[LOADING].read_text().splitlines()
    assert (
        lines[133]
        == "# -1 = stripe across all OSTs; 4 MiB stripe chunk suits large sequential shards"
    )
    assert lines[40].startswith("# ")
    assert lines[170].startswith("> ")


def test_a_candidate_that_is_not_the_grammar_fails_with_the_reason(tmp_path: Path) -> None:
    """The five Fern Twins and candidates written here: a pattern that is no regular expression,
    an unknown key, a `removes` the proposer may not give, and one that matches nothing."""
    store, _ = fern_store(tmp_path)
    candidates = tmp_path / "candidates.toml"
    candidates.write_text(
        '[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_lines = "("\n\n'
        '[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_lines = "x"\nname = "chrome"\n\n'
        '[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_trailing = "x"\nremoves = "3 lines"\n\n'
        '[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_lines = "^Was this page helpful"\n',
        encoding="utf-8",
    )

    result = rules(store, "check", str(candidates))

    assert result.exit_code == 0, result.stderr
    assert verdicts(result.stdout) == [
        "fail: readings[1].drop_lines is not a regular expression: missing ), unterminated "
        "subpattern at position 0",
        "fail: unknown key readings[2].name",
        "fail: readings[3].removes is written by rules accept, not by a candidate",
        "fail: changes no Version under docs.nvidia.com/",
    ]


def test_removes_carries_its_unit_and_the_guard_compares_lines(tmp_path: Path) -> None:
    """The five Fern Twins under the banner rule: the two Dynamo banners are blocks of 26 lines
    (41% of the Router Guide's 63), the others' 12 to 16. Accepted at 26 lines every one gets a
    Reading; accepted at 12, the Dynamo blocks are more than twice that and are held back."""
    store, stored = fern_store(tmp_path)
    rule = f'[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_leading = "{BANNER}"\n'

    set_rules(store, rule + 'removes = "26 lines"\n')
    every = lorekeep(store, edges_over()[0], "read")
    set_rules(store, rule + 'removes = "12 lines"\n')
    held = lorekeep(store, edges_over()[0], "read")

    assert every.stdout == "Built 5 Readings, 0 current\n"
    assert every.stderr == ""
    assert sorted(held.stderr.splitlines()) == [
        f"lorekeep: warning: {read_version(stored[name])[0]['url']}: rule docs.nvidia.com/ "
        "drop_leading removed 26 lines (accepted at 12 lines)"
        for name in (ROUTER, LOADING)
    ]
    assert held.stdout == "Built 3 Readings, 0 current\n"
    readings = {reading.name: reading for reading in readings_of(store)}
    assert sorted(readings) == sorted(stored[name].name for name in (GYM, RAIL_TYPES, JAILBREAK))
    for name in (GYM, RAIL_TYPES, JAILBREAK):
        assert read_version(readings[stored[name].name])[1].startswith(b"# ")


def test_rules_accept_appends_the_passing_rules_and_builds_their_readings(
    tmp_path: Path,
) -> None:
    """`readings-candidates-fern.toml` over the five Fern Twins, in a Store whose `lorekeep.toml`
    holds the owner's settings and comments; accepted twice."""
    store, stored = fern_store(tmp_path)
    (store / "lorekeep.toml").write_text(OWNER_TOML, encoding="utf-8")

    first = rules(store, "accept", str(CANDIDATES))
    text = (store / "lorekeep.toml").read_text(encoding="utf-8")
    again = rules(store, "accept", str(CANDIDATES))
    read = lorekeep(store, edges_over()[0], "read")

    assert first.exit_code == 0, first.stderr
    assert first.stdout.endswith("Accepted 1 rule, 3 failed\nBuilt 5 Readings, 0 current\n")
    today = datetime.date.today().isoformat()
    assert text == (
        f'{OWNER_TOML}\n[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_leading = "{BANNER}"\n'
        f'accepted = {today}\nremoves = "26 lines"\n'
    )
    assert (store / "lorekeep.toml").read_text(encoding="utf-8") == text
    assert again.stdout.endswith("Accepted 1 rule, 3 failed\nBuilt 0 Readings, 5 current\n")
    assert read.stdout == "Built 0 Readings, 5 current\n"
    reading = {path.name: path for path in readings_of(store)}[stored[ROUTER].name]
    assert read_version(reading)[1].startswith(b"# Router Guide\n")


def test_rules_accept_all_appends_the_failing_rules_too(tmp_path: Path) -> None:
    """`readings-candidates-fern.toml` over the five Fern Twins with `--all`: of two candidates
    with the same operation the later replaces the earlier, as in `lorekeep.toml`."""
    store, _ = fern_store(tmp_path)

    result = rules(store, "accept", "--all", str(CANDIDATES))

    assert result.exit_code == 0, result.stderr
    assert "Accepted 2 rules, 3 failed\n" in result.stdout
    assert "readings[1] is replaced by readings[4]" in result.stderr
    assert "readings[2] is replaced by readings[3]" in result.stderr
    written = tomllib.loads((store / "lorekeep.toml").read_text(encoding="utf-8"))["readings"]
    assert [
        {key: value for key, value in rule.items() if key != "accepted"} for rule in written
    ] == [
        {"prefix": "docs.nvidia.com/", "drop_leading": "^> ", "removes": "26 lines"},
        {"prefix": "docs.nvidia.com/", "drop_lines": "^# ", "removes": "3%"},
    ]


def test_rules_accept_replaces_a_rule_with_the_same_prefix_and_operation(tmp_path: Path) -> None:
    """The five Fern Twins; `lorekeep.toml` already holds an older banner rule between two of
    the owner's tables, and a Microsoft Learn rule after it."""
    store, _ = fern_store(tmp_path)
    older = (
        '[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_leading = "llms\\\\.txt"\n'
        'accepted = 2026-10-01\nremoves = "20 lines"\n'
    )
    learn = (
        '[[readings]]\nprefix = "learn.microsoft.com/"\n'
        'strip_title_suffix = " \\\\| Microsoft Learn$"\naccepted = 2026-10-01\n'
    )
    (store / "lorekeep.toml").write_text(
        f"{OWNER_TOML}\n{older}\n# Microsoft Learn's titles.\n{learn}", encoding="utf-8"
    )

    result = rules(store, "accept", str(CANDIDATES))

    assert result.exit_code == 0, result.stderr
    today = datetime.date.today().isoformat()
    banner = (
        f'[[readings]]\nprefix = "docs.nvidia.com/"\ndrop_leading = "{BANNER}"\n'
        f'accepted = {today}\nremoves = "26 lines"\n'
    )
    assert (store / "lorekeep.toml").read_text(encoding="utf-8") == (
        f"{OWNER_TOML}\n{banner}\n# Microsoft Learn's titles.\n{learn}"
    )
