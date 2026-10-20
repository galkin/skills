"""A page that ends at its site's home page is gone: `get` stores nothing and `recheck` records
`gone`, so a dropped page never becomes a Version of the home page under its address."""

from __future__ import annotations

from pathlib import Path

from lorekeep.urls import went_home
from tests.support import age_version, edges_over, lorekeep, make_store, rows

ROLLBACK = "https://helm.sh/docs/helm/helm_rollback/"


def test_only_a_page_below_the_root_that_lands_on_a_root_page_went_home() -> None:
    assert went_home(
        "https://www.skills.google/focuses/1?parent=catalog", "https://www.skills.google"
    )
    assert went_home("https://docs.example.test/a/b", "https://example.test/")
    assert not went_home("https://helm.sh/", "https://helm.sh/")
    assert not went_home("https://helm.sh/docs/a", "https://helm.sh/docs/b")
    assert not went_home("https://example.test/a", "https://example.test/?page=a")
    assert not went_home("https://example.test/index.html", "https://example.test/")
    assert went_home("https://example.test/a/index.html", "https://example.test/index.php")


def test_get_of_a_page_redirected_to_the_home_page_stores_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.home-redirect", "helm-home.html")

    result = lorekeep(store, edges, "get", ROLLBACK, tag="helm")

    assert result.exit_code == 1
    assert result.stderr.endswith(
        f"lorekeep: error: {ROLLBACK} is gone: it ended at the site's home page https://helm.sh/\n"
    ), result.stderr
    assert list(store.glob("*.md")) == []


def test_recheck_of_a_page_now_redirected_to_the_home_page_records_it_gone(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = lorekeep(store, edges_over("helm-rollback.html")[0], "get", ROLLBACK, tag="helm")
    assert first.exit_code == 0, first.stderr
    [version] = store.glob("*.md")
    age_version(version, days=40)
    edges, _ = edges_over("helm-rollback.home-redirect", "helm-home.html")

    result = lorekeep(store, edges, "recheck")

    assert result.exit_code == 0, result.stderr
    assert [row["result"] for row in rows(store, "checks.csv")] == ["gone"]
    assert list(store.glob("*.md")) == [version]
