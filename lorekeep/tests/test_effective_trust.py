"""Effective trust: `get`, `search` and `status` judge a stored Version by the current host
rules, while its frontmatter keeps what the rules said when it was fetched."""

from __future__ import annotations

import json
from pathlib import Path

from lorekeep import index
from lorekeep.project import load_project
from lorekeep.provenance import now
from tests.support import FIXTURES, Result, edges_over, get, lorekeep, make_store, write_version

HELM = "https://helm.sh/docs/helm/helm_rollback"
RULE = '[[hosts]]\nprefix = "helm.sh/"\npublisher = "helm"\nauthority = "primary"\n'
WARNING = "helm.sh is in no host table"
NOTE = f"{HELM} is third-party under no rule"


def unknown_helm(tmp_path: Path) -> tuple[Path, Path]:
    """A Store holding one Version of a page under a host no rule knows, stored as such, and
    tagged; the Store and the Version."""
    store = make_store(tmp_path)
    version = write_version(
        store, FIXTURES / "helm-rollback.html", fetched_at=now(), url=HELM, origin="web"
    )
    (store / "tags.csv").write_text(f"url,tag,added_at\n{HELM},specs,{now()}\n", encoding="utf-8")
    return store, version


def add_rule(store: Path, rule: str = RULE) -> None:
    (store / "lorekeep.toml").write_text(rule, encoding="utf-8")


def get_json(store: Path) -> tuple[dict[str, str], Result]:
    edges, _ = edges_over()
    result = get(store, edges, "--json", "--max-age", "9999", HELM, tag="specs")
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout), result


def search_urls(store: Path, *argv: str) -> list[dict[str, str]]:
    edges, _ = edges_over()
    result = lorekeep(store, edges, "search", "--json", "rollback", *argv)
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)["results"]


def test_get_json_shows_a_rule_added_after_the_fetch_and_the_captured_trust_beside_it(
    tmp_path: Path,
) -> None:
    store, version = unknown_helm(tmp_path)
    before, _ = get_json(store)
    stored = version.read_bytes()

    add_rule(store)
    after, _ = get_json(store)

    assert (before["publisher"], before["authority"]) == ("helm.sh", "third-party")
    assert "captured_authority" not in before and "captured_publisher" not in before
    assert (after["publisher"], after["authority"]) == ("helm", "primary")
    assert (after["captured_publisher"], after["captured_authority"]) == (
        "helm.sh",
        "third-party",
    )
    assert version.read_bytes() == stored


def test_get_json_adds_only_the_captured_field_that_differs(tmp_path: Path) -> None:
    store, _ = unknown_helm(tmp_path)
    add_rule(store, RULE.replace('"helm"', '"helm.sh"'))

    found, _ = get_json(store)

    assert (found["publisher"], found["authority"]) == ("helm.sh", "primary")
    assert found["captured_authority"] == "third-party"
    assert "captured_publisher" not in found


def test_get_stops_warning_and_noting_once_a_rule_covers_the_host(tmp_path: Path) -> None:
    store, _ = unknown_helm(tmp_path)
    _, before = get_json(store)

    add_rule(store)
    _, after = get_json(store)

    assert WARNING in before.stderr and NOTE in before.stderr
    assert WARNING not in after.stderr and NOTE not in after.stderr


def test_search_filters_on_and_prints_the_effective_trust(tmp_path: Path) -> None:
    store, _ = unknown_helm(tmp_path)
    assert search_urls(store, "--authority", "primary") == []
    assert [hit["url"] for hit in search_urls(store, "--authority", "third-party")] == [HELM]

    add_rule(store)

    primary = search_urls(store, "--authority", "primary")
    assert [(hit["url"], hit["publisher"], hit["authority"]) for hit in primary] == [
        (HELM, "helm", "primary")
    ]
    assert [hit["url"] for hit in search_urls(store, "--publisher", "helm")] == [HELM]
    assert search_urls(store, "--authority", "third-party") == []
    assert search_urls(store, "--publisher", "helm.sh") == []


def test_a_change_of_the_host_rules_makes_the_index_stale(tmp_path: Path) -> None:
    store, _ = unknown_helm(tmp_path)
    search_urls(store)
    with index.current(store, load_project(store)) as reader:
        assert reader is not None

    add_rule(store)

    with index.current(store, load_project(store)) as reader:
        assert reader is None
    edges, _ = edges_over()
    result = lorekeep(store, edges, "search", "rollback")
    assert "the Index was missing or stale and was rebuilt" in result.stderr


def test_status_lists_a_host_as_unknown_only_while_no_rule_covers_it(tmp_path: Path) -> None:
    store, _ = unknown_helm(tmp_path)
    edges, _ = edges_over()
    before = json.loads(lorekeep(store, edges, "status", "--json").stdout)

    add_rule(store)
    after = json.loads(lorekeep(store, edges, "status", "--json").stdout)

    assert before["unknown_hosts"] == ["helm.sh"]
    assert after["unknown_hosts"] == []


def test_an_owner_source_keeps_the_trust_it_was_added_with(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    note = tmp_path / "note.md"
    note.write_text("# Rollback research\n\nHelm rollback notes.\n", encoding="utf-8")
    edges, _ = edges_over()
    added = lorekeep(store, edges, "add", str(note), "--title", "Rollback", "--json", tag="specs")
    found = json.loads(added.stdout)

    assert (found["publisher"], found["authority"]) == ("owner", "generated")
    assert "captured_authority" not in found
    hits = search_urls(store, "--authority", "generated")
    assert [(hit["url"], hit["authority"]) for hit in hits] == [("owner:rollback", "generated")]


def test_a_twin_rule_added_after_the_fetch_reaches_no_stored_version(tmp_path: Path) -> None:
    store, version = unknown_helm(tmp_path)
    add_rule(store, RULE + 'twin = "md-suffix"\n')
    edges, transport = edges_over()

    result = get(store, edges, "--json", "--max-age", "9999", HELM, tag="specs")

    assert result.exit_code == 0, result.stderr
    found = json.loads(result.stdout)
    assert (found["path"], found["outcome"], found["converter"]) == (
        str(version),
        "fresh",
        "fixture",
    )
    assert transport.requests == []


def test_a_version_committed_into_a_current_index_carries_its_trust(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.html")
    search_urls(store)  # an Index exists before the fetch, so the commit notifies it
    add_rule(store)
    search_urls(store)

    assert get(store, edges, f"{HELM}/", tag="specs").exit_code == 0

    with index.current(store, load_project(store)) as reader:
        assert reader is not None
    hits = search_urls(store, "--authority", "primary")
    assert {(hit["url"], hit["publisher"]) for hit in hits} == {(HELM, "helm")}
