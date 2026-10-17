"""`get` falls back to the browser (ticket 06)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import trafilatura

from lorekeep.edges import Edges
from tests.support import FakeFetcher, FakeRunner, FakeTransport, run_cli
from tests.test_helpers import read_version

MILVUS = "https://milvus.io/docs/overview.md"
CRAWL4AI_VERSION = "0.9.5"

RENDERED = """<!doctype html>
<html><head><title>What is Milvus</title></head>
<body>
<nav>Docs Home Blog Community Navigation menu entry</nav>
<main><article>
<h1>Introduction to Milvus</h1>
<p>Milvus is a high-performance vector database built for scale. It powers AI applications
by efficiently organizing and searching vast amounts of unstructured data, such as text,
images, and multi-modal information.</p>
<h2>What makes Milvus so fast</h2>
<p>Milvus was designed from day one to be a highly efficient vector database system. In most
cases, Milvus outperforms other vector databases by two to five times. See the
<a href="/docs/benchmark.md">benchmark</a> for the measurements behind that claim.</p>
<p>Hardware-aware optimization, advanced search algorithms and a search engine written in C++
are what keep its latency low and its throughput high.</p>
</article></main>
</body></html>
"""


def make_store(tmp_path: Path) -> Path:
    path = tmp_path / "store"
    path.mkdir(parents=True)
    return path


def rendered_page(tmp_path: Path, html: str = RENDERED) -> Path:
    path = tmp_path / "rendered.html"
    path.write_text(html, encoding="utf-8")
    return path


def get(store: Path, edges: Edges, *argv: str, tag: str = "milvus"):
    return run_cli(
        ["get", *argv], env={"LOREKEEP_STORE": str(store), "LOREKEEP_TAG": tag}, edges=edges
    )


def test_a_403_to_the_plain_client_is_fetched_once_through_the_browser(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    transport = FakeTransport.from_fixtures("milvus-403")
    fetcher = FakeFetcher({MILVUS: (rendered_page(tmp_path), MILVUS)}, version=CRAWL4AI_VERSION)
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, MILVUS)

    assert result.exit_code == 0, result.stderr
    assert fetcher.calls == [MILVUS]
    [version] = store.glob("*.md")
    assert result.stdout.splitlines()[-1] == str(version)
    head, body = read_version(version)
    assert head["converter"] == (
        f"trafilatura {trafilatura.__version__} via crawl4ai {CRAWL4AI_VERSION}"
    )
    assert head["url"] == MILVUS
    assert head["publisher"] == "milvus"
    assert b"Milvus is a high-performance vector database" in body
    assert b"(https://milvus.io/docs/benchmark.md)" in body
    original = version.with_name(f"{version.name.removesuffix('.md')}.orig.html")
    assert original.read_text(encoding="utf-8") == RENDERED
    assert head["original"] == {
        "url": MILVUS,
        "mediatype": "text/html",
        "sha256": hashlib.sha256(RENDERED.encode("utf-8")).hexdigest(),
        "stored": "true",
    }


def test_a_host_marked_browser_skips_the_plain_client_entirely(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    browser_rule(store)
    page = "https://example.test/app/dashboard"
    transport = FakeTransport.from_fixtures()
    fetcher = FakeFetcher({page: (rendered_page(tmp_path), page)})
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, page, tag="example")

    assert result.exit_code == 0, result.stderr
    assert transport.requests == []
    assert fetcher.calls == [page]
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert head["url"] == page
    assert head["publisher"] == "example"
    assert " via crawl4ai " in head["converter"]


def test_a_page_without_text_goes_to_the_browser_instead_of_no_content(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = "https://example.test/app"
    transport = FakeTransport.from_fixtures("js-only.html")
    fetcher = FakeFetcher({page: (rendered_page(tmp_path), page)})
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, page, tag="example")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [page]
    assert fetcher.calls == [page]
    [version] = store.glob("*.md")
    _, body = read_version(version)
    assert b"Introduction to Milvus" in body


def browser_rule(store: Path, cut: str = "") -> None:
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "example.test/app/"\npublisher = "example"\n'
        f'authority = "third-party"\nbrowser = true\n{cut}',
        encoding="utf-8",
    )


def test_the_rule_s_cut_selectors_are_removed_before_extraction_but_not_from_the_original(
    tmp_path: Path,
) -> None:
    page = "https://example.test/app/dashboard"
    html = RENDERED.replace(
        "<p>Hardware-aware",
        '<p class="promo">Try Zilliz Cloud, the managed Milvus, free for thirty days and '
        "skip the setup.</p><p>Hardware-aware",
    )
    rendered = rendered_page(tmp_path, html)
    uncut, cut = make_store(tmp_path / "uncut"), make_store(tmp_path / "cut")
    browser_rule(uncut)
    browser_rule(cut, 'cut = ["nav", ".promo"]\n')

    for store in (uncut, cut):
        fetcher = FakeFetcher({page: (rendered, page)})
        edges = Edges(transport=FakeTransport([]), fetcher=fetcher, runner=FakeRunner())
        result = get(store, edges, page, tag="example")
        assert result.exit_code == 0, result.stderr

    [kept] = uncut.glob("*.md")
    [version] = cut.glob("*.md")
    assert b"Try Zilliz Cloud" in read_version(kept)[1]
    _, body = read_version(version)
    assert b"Try Zilliz Cloud" not in body
    assert b"Navigation menu entry" not in body
    assert b"Hardware-aware optimization" in body
    original = version.with_name(f"{version.name.removesuffix('.md')}.orig.html")
    assert original.read_text(encoding="utf-8") == html


def test_without_crawl4ai_get_names_the_extra_and_stores_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    transport = FakeTransport.from_fixtures("milvus-403")
    fetcher = FakeFetcher({MILVUS: (rendered_page(tmp_path), MILVUS)}, installed=False)
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, MILVUS)

    assert result.exit_code != 0
    assert "lorekeep[browser]" in result.stderr
    assert "Crawl4AI is not installed" in result.stderr
    assert fetcher.calls == []
    assert list(store.iterdir()) == []


def test_a_page_the_browser_cannot_render_stores_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = "https://example.test/app"
    transport = FakeTransport.from_fixtures("js-only.html")
    fetcher = FakeFetcher({})
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, page, tag="example")

    assert result.exit_code != 0
    assert "no content" in result.stderr
    assert "the fake browser has no page" in result.stderr
    assert fetcher.calls == [page]
    assert list(store.iterdir()) == []


def test_a_404_does_not_send_get_to_the_browser(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = "https://example.test/missing"
    fetcher = FakeFetcher({page: (rendered_page(tmp_path), page)})
    edges = Edges(transport=FakeTransport([]), fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, page, tag="example")

    assert result.exit_code != 0
    assert fetcher.calls == []
    assert list(store.iterdir()) == []
