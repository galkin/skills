"""A Twin that answers `200` with a not-found page is no Version (v1.3 ticket 04).

Every test runs under the default `docs.nvidia.com/nemo/guardrails/` rule (`md-suffix`, Fern),
with NVIDIA's move of the NeMo Guardrails pages out of `…/latest/` found live on 2026-10-17.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from lorekeep.cascade import Fallthrough, Fetched, TwinStep
from lorekeep.project import HostRule, load_project
from lorekeep.store import latest
from tests.support import (
    FIXTURES,
    FakeTransport,
    age_version,
    edges_over,
    get,
    lorekeep,
    make_store,
    rows,
    write_version,
)
from tests.test_helpers import read_version

OLD = "https://docs.nvidia.com/nemo/guardrails/latest/about-nemo-guardrails/library/rail-types"
NEW = "https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types"
REASON = f"no Twin: {OLD}.md answered 200 with a not-found page"


def requested(transport: FakeTransport) -> list[str]:
    return [str(request.url) for request in transport.requests]


def test_a_not_found_twin_is_not_stored_and_the_page_is_asked_next(tmp_path: Path) -> None:
    """`guardrails-rail-types.notfound.twin` (the body of the first Store's Version, byte for
    byte), then `guardrails-rail-types.notfound.404`: the page itself answers `404`."""
    store = make_store(tmp_path)
    edges, transport = edges_over(
        "guardrails-rail-types.notfound.twin", "guardrails-rail-types.notfound.404"
    )

    result = get(store, edges, OLD, tag="nvidia")

    assert result.exit_code == 1
    assert requested(transport) == [f"{OLD}.md", OLD]
    assert f"lorekeep: error: nothing stored for {OLD}: {REASON}; {OLD} answered 404" in (
        result.stderr
    )
    assert not list(store.glob("*.md"))
    assert rows(store, "tags.csv") == []


def test_a_page_that_moved_is_stored_from_the_twin_at_its_new_address(tmp_path: Path) -> None:
    """`guardrails-rail-types.notfound.twin`, `guardrails-rail-types.notfound.301` (the page
    redirects to the new address), `guardrails-rail-types.moved.html` (the new page's HTML) and
    `guardrails-rail-types.moved.twin` (its Twin, the real page): the Twin wins over the HTML."""
    store = make_store(tmp_path)
    edges, transport = edges_over(
        "guardrails-rail-types.notfound.twin",
        "guardrails-rail-types.notfound.301",
        "guardrails-rail-types.moved.html",
        "guardrails-rail-types.moved.twin",
    )

    first = get(store, edges, OLD, "--json", tag="nvidia")

    assert first.exit_code == 0, first.stderr
    assert requested(transport) == [f"{OLD}.md", OLD, NEW, f"{NEW}.md"]
    printed = json.loads(first.stdout)
    assert printed["outcome"] == "stored"
    assert printed["url"] == NEW
    assert printed["requested_url"] == OLD
    assert printed["converter"] == "md-twin"
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["original"]["url"] == f"{NEW}.md"
    assert head["title"] == "Guardrail Types"
    assert body == (FIXTURES / "guardrails-rail-types.moved.twin" / "body.md").read_bytes()
    assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [(OLD, NEW)]

    again = get(store, edges_over()[0], OLD, "--json", tag="nvidia")

    assert again.exit_code == 0, again.stderr
    assert json.loads(again.stdout)["outcome"] == "fresh"
    assert json.loads(again.stdout)["path"] == str(version)


def test_a_moved_page_whose_new_twin_is_missing_is_converted_from_its_html(
    tmp_path: Path,
) -> None:
    """`guardrails-rail-types.notfound.twin`, `.notfound.301` and `.moved.html` without
    `.moved.twin`: the new address's Twin answers `404`, so the HTML fetched is converted."""
    store = make_store(tmp_path)
    edges, transport = edges_over(
        "guardrails-rail-types.notfound.twin",
        "guardrails-rail-types.notfound.301",
        "guardrails-rail-types.moved.html",
    )

    result = get(store, edges, OLD, "--json", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert requested(transport) == [f"{OLD}.md", OLD, NEW, f"{NEW}.md"]
    printed = json.loads(result.stdout)
    assert printed["url"] == NEW
    assert printed["converter"].startswith("trafilatura ")


def test_recheck_of_a_version_whose_twin_now_says_not_found_keeps_it(tmp_path: Path) -> None:
    """A Version under the old address (the body of `guardrails-rail-types.twin`), rechecked
    while its Twin answers `guardrails-rail-types.notfound.twin`."""
    store = make_store(tmp_path)
    good = FIXTURES / "guardrails-rail-types.twin"
    path = write_version(
        store,
        good,
        fetched_at="2026-10-01T08:00:00Z",
        url=OLD,
        publisher="nvidia",
        authority="primary",
        converter="md-twin",
        original={
            "url": f"{OLD}.md",
            "mediatype": "text/markdown",
            "sha256": hashlib.sha256((good / "body.md").read_bytes()).hexdigest(),
            "stored": False,
        },
    )
    head, _ = read_version(path)
    age_version(path, days=40)
    edges, transport = edges_over("guardrails-rail-types.notfound.twin")

    result = lorekeep(store, edges, "recheck")

    assert result.exit_code == 0, result.stderr
    assert requested(transport) == [f"{OLD}.md"]
    assert f"error {OLD}" in result.stdout.splitlines()
    assert f"lorekeep: warning: {REASON}; returning the stored Version" in result.stderr
    assert [
        (row["url"], row["result"], row["status"], row["sha256"])
        for row in rows(store, "checks.csv")
    ] == [(OLD, "error", "200", head["sha256"])]
    assert list(store.glob("*.md")) == [path]
    found = latest(store, OLD, load_project(store).hosts)
    assert found is not None
    assert found.path == path


FERN = HostRule("docs.nvidia.com/nemo/guardrails/", "nvidia", "primary", twin="md-suffix")
RAW = HostRule("github.com/", "github", "third-party", twin="github-raw")


@pytest.mark.parametrize(
    ("rule", "address", "body", "taken"),
    [
        (FERN, f"{NEW}.md", b"# 404\n\nNothing here.\n", False),
        (FERN, f"{NEW}.md", b"---\ntitle: x\n---\n\n# page not found\n", False),
        (FERN, f"{NEW}.md", b"# Page Not Found\n" + b"line\n" * 39, True),
        (FERN, f"{NEW}.md", b"# Not Found Errors\n\nHow to handle them.\n", True),
        (RAW, "https://raw.githubusercontent.com/o/r/main/404.md", b"# 404\n", True),
    ],
    ids=["404", "after-frontmatter", "forty-lines", "other-heading", "github-raw"],
)
def test_the_not_found_marker(rule: HostRule, address: str, body: bytes, taken: bool) -> None:
    """The marker `cascade/twin.py` names, pinned on `guardrails-rail-types.notfound.twin`: a
    first `# ` heading `Page Not Found` or `404` in any case, under 40 lines, never `github-raw`."""
    response = httpx.Response(
        200,
        headers={"content-type": "text/markdown"},
        content=body,
        request=httpx.Request("GET", address),
    )

    found = TwinStep().reread(response, rule)

    assert isinstance(found, Fetched) is taken
    if not taken:
        assert isinstance(found, Fallthrough)
        assert found.reason == f"no Twin: {address} answered 200 with a not-found page"
