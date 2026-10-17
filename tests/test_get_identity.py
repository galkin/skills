"""`url` is where the page was served, never its canonical link (v1.1 ticket 02)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from lorekeep import package
from tests.support import (
    age_version,
    comparable_url,
    edges_over,
    get,
    make_store,
    rows,
    run_cli,
)
from tests.test_helpers import read_version

OWASP_ASKED = "https://genai.owasp.org/llmrisk/llm062025-excessive-agency/"
OWASP_PAGE = "https://genai.owasp.org/llmrisk/llm062025-excessive-agency"
OWASP_CANONICAL = "https://genai.owasp.org/llmrisk/llm06-sensitive-information-disclosure"

RETRIEVER_ASKED = "https://docs.nvidia.com/nemo/retriever/latest/extraction/concepts/"
RETRIEVER_PAGE = "https://docs.nvidia.com/nemo/retriever/latest/extraction/concepts"
RETRIEVER_CANONICAL = "https://docs.nvidia.com/nemo/retriever/26.8.1/extraction/concepts"

HELM_V3 = "https://v3.helm.sh/docs/helm/helm_rollback/"
HELM = "https://helm.sh/docs/helm/helm_rollback"
HELM_WARNING = (
    "lorekeep: warning: helm.sh is in no host table; stored as third-party — tell the owner, "
    "who may add a [[hosts]] rule"
)


def canonical_warnings(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if "declares another page as canonical" in line]


def host_warnings(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if "is in no host table" in line]


def test_a_canonical_naming_another_page_is_recorded_but_never_the_url(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("owasp-excessive-agency.html")

    result = get(store, edges, OWASP_ASKED, tag="owasp")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == OWASP_PAGE
    assert head["canonical"] == OWASP_CANONICAL
    assert head["original"]["url"] == OWASP_ASKED
    assert version.name.startswith("genai.owasp.org--llmrisk-llm062025-excessive-agency--")
    assert b"Excessive Agency is the vulnerability" in body
    [warning] = canonical_warnings(result.stderr)
    assert warning.startswith("lorekeep: warning: ")
    assert OWASP_PAGE in warning and OWASP_CANONICAL in warning
    assert not (store / "aliases.csv").exists()


def test_the_canonical_address_is_fetched_on_its_own_and_its_redirect_decides(
    tmp_path: Path,
) -> None:
    """Live, OWASP's canonical address answers `301` back to the Excessive Agency page: asking for
    it fetches it (the Store never answers it from the `canonical` field), and the redirect makes
    it an alias of the page it lands on."""
    store = make_store(tmp_path)
    edges, transport = edges_over(
        "owasp-excessive-agency.html", "owasp-sensitive-information-disclosure.301"
    )
    first = get(store, edges, OWASP_ASKED, tag="owasp")
    assert first.exit_code == 0, first.stderr
    [version] = store.glob("*.md")

    second = get(store, edges, f"{OWASP_CANONICAL}/", tag="owasp")

    assert second.exit_code == 0, second.stderr
    assert comparable_url(str(transport.requests[-2].url)) == f"{OWASP_CANONICAL}/"
    assert second.stdout.splitlines()[-1] == str(version)
    assert list(store.glob("*.md")) == [version]
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        (OWASP_CANONICAL, OWASP_PAGE)
    ]


def test_a_versioned_canonical_leaves_the_latest_address_as_url_and_the_recheck_asks_it(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("nvidia-retriever-concepts.html")

    result = get(store, edges, RETRIEVER_ASKED, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert (head["url"], head["canonical"]) == (RETRIEVER_PAGE, RETRIEVER_CANONICAL)
    assert (head["publisher"], head["authority"]) == ("nvidia", "primary")
    assert head["original"]["url"] == RETRIEVER_ASKED
    assert len(canonical_warnings(result.stderr)) == 1
    assert host_warnings(result.stderr) == []

    age_version(version, days=40)
    asked = len(transport.requests)
    again = get(store, edges, RETRIEVER_ASKED, "--json", tag="nvidia")

    assert again.exit_code == 0, again.stderr
    assert json.loads(again.stdout)["outcome"] == "unchanged"
    [recheck] = transport.requests[asked:]
    assert comparable_url(str(recheck.url)) == RETRIEVER_ASKED
    assert recheck.headers["if-none-match"] == head["etag"]
    assert [row["url"] for row in rows(store, "checks.csv")] == [RETRIEVER_PAGE]


def test_a_redirect_to_another_host_warns_of_the_final_host_only(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.v3-redirect", "helm-rollback.html")

    result = get(store, edges, HELM_V3, tag="kubernetes")

    assert result.exit_code == 0, result.stderr
    assert host_warnings(result.stderr) == [HELM_WARNING]
    assert "v3.helm.sh" not in result.stderr
    assert canonical_warnings(result.stderr) == []
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert head["url"] == HELM
    assert "canonical" not in head
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
        ("https://v3.helm.sh/docs/helm/helm_rollback", HELM)
    ]
    status = run_cli(["status", "--json", "--store", str(store)])
    assert json.loads(status.stdout)["unknown_hosts"] == ["helm.sh"]


def test_v3_helm_served_in_place_keeps_its_host_and_its_canonical_is_its_own_source(
    tmp_path: Path,
) -> None:
    """As measured on 2026-10-17, `v3.helm.sh` answers `200` itself and names `helm.sh` only as
    its canonical: the page is stored where it was served, and `helm.sh` is fetched on its own."""
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.v3", "helm-rollback.html")

    first = get(store, edges, HELM_V3, tag="kubernetes")

    assert first.exit_code == 0, first.stderr
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert (head["url"], head["canonical"]) == ("https://v3.helm.sh/docs/helm/helm_rollback", HELM)
    assert [line.split(" is in")[0] for line in host_warnings(first.stderr)] == [
        "lorekeep: warning: v3.helm.sh"
    ]
    assert len(canonical_warnings(first.stderr)) == 1

    second = get(store, edges, f"{HELM}/", tag="kubernetes")

    assert second.exit_code == 0, second.stderr
    assert host_warnings(second.stderr) == [HELM_WARNING]
    other = Path(second.stdout.splitlines()[-1])
    assert other != version
    other_head, _ = read_version(other)
    assert other_head["url"] == HELM and "canonical" not in other_head
    assert not (store / "aliases.csv").exists()


def test_get_json_carries_the_normalised_address_asked(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("owasp-excessive-agency.html")

    stored = get(store, edges, f"{OWASP_ASKED}#top", "--json", tag="owasp")
    fresh = get(store, edges, OWASP_ASKED, "--json", tag="owasp")

    first = json.loads(stored.stdout)
    assert (first["url"], first["requested_url"]) == (OWASP_PAGE, OWASP_PAGE)
    assert list(first)[:3] == ["path", "url", "requested_url"]
    assert json.loads(fresh.stdout)["requested_url"] == OWASP_PAGE


def test_the_index_has_a_canonical_column_and_the_package_rows_do_not(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("owasp-excessive-agency.html")
    assert get(store, edges, OWASP_ASKED, tag="owasp").exit_code == 0

    assert run_cli(["index", "--store", str(store)]).exit_code == 0

    with sqlite3.connect(store / "sources.db") as con:
        found = con.execute("SELECT url, canonical FROM versions").fetchall()
    assert found == [(OWASP_PAGE, OWASP_CANONICAL)]
    [row] = next(r for r in package.describe(store)["resources"] if r["name"] == "sources")["data"]
    assert "canonical" not in row


def test_an_index_built_before_the_canonical_column_is_rebuilt(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("owasp-excessive-agency.html")
    assert get(store, edges, OWASP_ASKED, tag="owasp").exit_code == 0
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    with sqlite3.connect(store / "sources.db") as con:
        con.execute("ALTER TABLE versions DROP COLUMN canonical")
        con.execute("DELETE FROM meta WHERE key = 'schema'")

    result = run_cli(["search", "agency", "--all", "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert "rebuilt" in result.stderr
    with sqlite3.connect(store / "sources.db") as con:
        assert con.execute("SELECT canonical FROM versions").fetchall() == [(OWASP_CANONICAL,)]
