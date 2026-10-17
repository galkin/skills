"""`search` over Readings, `status` counts them, `backup` leaves the cache (v1.3 ticket 02): the
Index's Sections come from a Version's Reading where it has one and name that file, so `file:line`
points into what `get` returns; a rules change rebuilds the Index; `.cache/` never reaches the
bucket; Rechecks and Citations still work on Versions.

Each test names its fixture: the Fern Twin with the llms.txt banner, the Microsoft Learn Twin of
the Retry pattern, the synthesised page with a fence and a table, and a termidy lesson that changes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from lorekeep.commands.skill import skill_folder
from lorekeep.edges import CommandResult, Edges
from lorekeep.readings import reading_path
from tests.support import (
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    Result,
    age_version,
    edges_over,
    get,
    lorekeep,
    make_store,
)
from tests.test_readings import (
    FERN_RULE,
    LEARN_RULE,
    RAIL_TYPES,
    RETRY,
    readings_of,
    set_rules,
    store_with,
    stored,
)

REBUILT = "lorekeep: note: the Index was missing or stale and was rebuilt"
COORDINATOR = (
    "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents"
)
# The breadcrumb and the course line a termidy lesson carries before its H1.
TERMIDY_RULE = (
    '[[readings]]\nprefix = "claude.termidy.com/"\ndrop_leading = "^\\\\[Home\\\\]|^CCAR-F · "\n'
)


def search(store: Path, *argv: str) -> Result:
    result = lorekeep(store, edges_over()[0], "search", *argv)
    assert result.exit_code == 0, result.stderr
    return result


def hits(result: Result) -> list[tuple[Path, int]]:
    """The `file:line` of every line `search` printed."""
    found: list[tuple[Path, int]] = []
    for line in result.stdout.splitlines():
        path, number = line.split(" | ", 1)[0].rsplit(":", 1)
        found.append((Path(path), int(number)))
    return found


def holds(path: Path, number: int, text: str) -> bool:
    """Whether line `number` of the file at `path` holds `text`, ignoring case."""
    return text.casefold() in path.read_text(encoding="utf-8").splitlines()[number - 1].casefold()


def rail_types(store: Path) -> Path:
    return stored(store, "guardrails-rail-types.twin", url=RAIL_TYPES, converter="md-twin")


def test_search_over_a_fern_reading_skips_the_banner_and_points_into_the_reading(
    tmp_path: Path,
) -> None:
    """`guardrails-rail-types.twin` under the banner rule; no `read` before the search."""
    store = store_with(tmp_path, FERN_RULE)
    version = rail_types(store)

    banner = search(store, "llms.txt")
    found = search(store, "execution rails")

    [reading] = readings_of(store)
    assert reading == reading_path(store, version)
    assert REBUILT in banner.stderr
    assert banner.stdout == "no matches\n"
    [(_, top), *_] = hits(found)
    assert holds(reading, top, "execution") and holds(reading, top, "rails")
    for path, number in hits(found):
        assert path == reading
        assert holds(reading, number, "execution")
    assert "llms.txt" in version.read_text(encoding="utf-8")


def test_a_version_without_a_reading_is_searched_as_before(tmp_path: Path) -> None:
    """`ms-retry-pattern.twin` in a Store without rules and in one whose Fern rule names another
    host, beside `guardrails-rail-types.twin`, which gets a Reading there."""
    plain = make_store(tmp_path / "plain")
    ruled = store_with(tmp_path / "ruled", FERN_RULE)
    for store in (plain, ruled):
        stored(store, "ms-retry-pattern.twin", url=RETRY, converter="md-twin")
    rail_types(ruled)

    before = json.loads(search(plain, "--json", "--exact", "transient failures").stdout)
    after = json.loads(search(ruled, "--json", "--exact", "transient failures").stdout)

    assert len(readings_of(ruled)) == 1
    [old], [new] = before["results"], after["results"]
    assert Path(old["file"]).relative_to(plain) == Path(new["file"]).relative_to(ruled)
    assert Path(new["file"]).parent == ruled
    assert (old["line"], old["heading_line"]) == (new["line"], new["heading_line"])
    assert holds(Path(new["file"]), new["line"], "transient failures")


def test_a_rule_added_rebuilds_the_index_and_the_hits_point_into_the_new_readings(
    tmp_path: Path,
) -> None:
    """`guardrails-rail-types.twin`, searched before and after the banner rule is added; stored
    as a conversion, so the package's Fern rule, which reaches Twins only, does not."""
    store = make_store(tmp_path)
    version = stored(
        store, "guardrails-rail-types.twin", url=RAIL_TYPES, converter="trafilatura 2.3.1"
    )

    first = search(store, "execution rails")
    second = search(store, "execution rails")
    set_rules(store, FERN_RULE)
    third = search(store, "execution rails")
    banner = search(store, "llms.txt")

    assert {path for path, _ in hits(first)} == {version}
    assert REBUILT in first.stderr
    assert second.stderr == ""
    assert REBUILT in third.stderr
    [reading] = readings_of(store)
    assert hits(third)
    for path, number in hits(third):
        assert path == reading
        assert holds(reading, number, "execution")
    assert banner.stderr == ""
    assert banner.stdout == "no matches\n"


def test_a_reading_built_by_get_reaches_a_current_index_without_a_rebuild(
    tmp_path: Path,
) -> None:
    """`guardrails-rail-types.twin` fetched by `get` into a Store whose Index is current."""
    store = store_with(tmp_path, FERN_RULE)
    stored(store, "ms-retry-pattern.twin", url=RETRY, converter="md-twin")
    search(store, "transient failures")
    edges, _ = edges_over("guardrails-rail-types.twin")

    fetched = get(store, edges, RAIL_TYPES, tag="nvidia")
    found = search(store, "execution rails")

    [reading] = readings_of(store)
    assert fetched.stdout == f"{reading}\n"
    assert found.stderr == ""
    assert hits(found)
    for path, number in hits(found):
        assert path == reading
        assert holds(reading, number, "execution")


def test_status_counts_the_readings_and_the_rules(tmp_path: Path) -> None:
    """`guardrails-rail-types.twin` and `ms-retry-pattern.twin` get a Reading under the Fern and
    Learn rules; the synthesised `readings-fence-table.v1` matches no rule. The count of rules adds
    the package's three engine rules to the Store's two."""
    store = store_with(tmp_path, FERN_RULE, LEARN_RULE)
    rail_types(store)
    stored(store, "ms-retry-pattern.twin", url=RETRY, converter="md-twin")
    stored(store, "readings-fence-table.v1")

    text = lorekeep(store, edges_over()[0], "status")
    printed = lorekeep(store, edges_over()[0], "status", "--json")

    assert text.exit_code == printed.exit_code == 0, text.stderr
    assert "Readings: 2 of 3 Versions, 5 rules" in text.stdout.splitlines()
    found = json.loads(printed.stdout)
    assert (found["readings"], found["rules"], found["versions"]) == (2, 5, 3)
    assert len(readings_of(store)) == 2


class ListingRunner(FakeRunner):
    """`gcloud storage rsync --dry-run` as it lists: every file under the source folder, at any
    depth, whose path relative to it the `--exclude` pattern does not match."""

    def run(self, argv: Sequence[str]) -> CommandResult:
        self.calls.append(list(argv))
        if argv[2] != "rsync":
            return CommandResult(0, "", "")
        [exclude] = [arg.removeprefix("--exclude=") for arg in argv if arg.startswith("--exclude=")]
        pattern = re.compile(exclude)
        source, bucket = Path(argv[-2]), argv[-1]
        listed = [
            f"Would copy file://{path} to {bucket}/{relative}\n"
            for path in sorted(source.rglob("*"))
            if path.is_file()
            and not pattern.search(relative := path.relative_to(source).as_posix())
        ]
        return CommandResult(0, "".join(listed), "")


def test_backup_never_copies_the_cache(tmp_path: Path) -> None:
    """`guardrails-rail-types.twin` with its Reading built by `read`."""
    store = store_with(tmp_path, 'bucket = "test-sources"\n', FERN_RULE)
    version = rail_types(store)
    assert lorekeep(store, edges_over()[0], "read").exit_code == 0
    [reading] = readings_of(store)
    runner = ListingRunner()
    edges = Edges(transport=FakeTransport([]), fetcher=FakeFetcher(), runner=runner)

    result = lorekeep(store, edges, "backup", "--dry-run")

    assert result.exit_code == 0, result.stderr
    assert f"file://{version} " in result.stdout
    assert ".cache" not in result.stdout
    [rsync] = runner.calls
    [exclude] = [arg.removeprefix("--exclude=") for arg in rsync if arg.startswith("--exclude=")]
    assert re.search(exclude, reading.relative_to(store).as_posix())
    assert re.search(exclude, ".cache/anything/else.bin")
    assert not re.search(exclude, version.name)
    package = json.loads((store / "datapackage.json").read_text(encoding="utf-8"))
    [sources] = [r for r in package["resources"] if r["name"] == "sources"]
    assert [row["file"] for row in sources["data"]] == [version.name]


def test_recheck_and_citations_work_on_versions_and_a_changed_page_gets_its_reading(
    tmp_path: Path,
) -> None:
    """`termidy-coordinator-and-subagents.html` under a rule dropping its breadcrumb, then
    `termidy-coordinator-and-subagents.changed` (a new H1) at the Recheck."""
    store = store_with(tmp_path, TERMIDY_RULE)
    first_edges, _ = edges_over("termidy-coordinator-and-subagents.html")
    assert get(store, first_edges, f"{COORDINATOR}/", tag="termidy").exit_code == 0
    [first] = store.glob("*.md")
    age_version(first, days=40)  # fetched in the same second, the two would tie on `fetched_at`
    (store / "citations.csv").write_text(
        f"work_id,url\nlesson-1,{COORDINATOR}/\n", encoding="utf-8"
    )
    changed_edges, _ = edges_over("termidy-coordinator-and-subagents.changed")

    rechecked = lorekeep(store, changed_edges, "recheck", tag="termidy")
    cited = lorekeep(store, edges_over()[0], "recheck", "--citations")
    then = get(store, edges_over()[0], COORDINATOR, tag="termidy")
    printed = json.loads(get(store, edges_over()[0], "--json", COORDINATOR, tag="t").stdout)

    assert rechecked.exit_code == 0, rechecked.stderr
    assert f"changed {COORDINATOR}" in rechecked.stdout
    [second] = set(store.glob("*.md")) - {first}
    old, new = first.name.removesuffix(".md")[-8:], second.name.removesuffix(".md")[-8:]
    assert cited.exit_code == 0, cited.stderr
    assert cited.stdout.splitlines() == [f"lesson-1, {COORDINATOR}, {old} → {new}"]
    reading = reading_path(store, second)
    assert then.stdout == f"{reading}\n"
    assert printed["path"] == str(reading)
    assert printed["version"] == str(second)
    assert sorted(readings_of(store)) == sorted([reading_path(store, first), reading])
    body = reading.read_text(encoding="utf-8").split("---\n", 2)[2]
    assert body.startswith("# ")


def test_the_owner_reference_says_the_cache_is_never_backed_up() -> None:
    """No fixture: `references/owner.md`."""
    owner = skill_folder().joinpath("references", "owner.md").read_text(encoding="utf-8")

    assert "`.cache/` is never backed up" in owner
    assert "rebuilt from the Versions" in owner
