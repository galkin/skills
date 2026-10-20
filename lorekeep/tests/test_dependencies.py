"""What `uv sync` installs: the spec's runtime list; Crawl4AI only under the `browser` extra."""

from importlib.metadata import requires

import lxml.html
from packaging.requirements import Requirement


def requirements() -> list[Requirement]:
    return [Requirement(line) for line in requires("lorekeep") or []]


def test_runtime_dependencies_are_the_specs_list() -> None:
    runtime = {(r.name.lower(), frozenset(r.extras)) for r in requirements() if r.marker is None}

    assert runtime == {
        ("httpx", frozenset()),
        ("trafilatura", frozenset()),
        ("markitdown", frozenset({"pdf"})),
        ("cssselect", frozenset()),
        ("pyyaml", frozenset()),
    }


def test_crawl4ai_is_only_the_browser_extra_and_frictionless_is_not_runtime() -> None:
    by_name = {r.name.lower(): r for r in requirements()}

    crawl4ai = by_name["crawl4ai"]
    assert crawl4ai.marker is not None
    assert not crawl4ai.marker.evaluate({"extra": ""})
    assert crawl4ai.marker.evaluate({"extra": "browser"})
    assert "frictionless" not in by_name


def test_lxml_css_selectors_work_without_extras() -> None:
    page = lxml.html.fromstring("<html><body><nav>menu</nav><p>text</p></body></html>")

    assert [node.text for node in page.cssselect("nav")] == ["menu"]
