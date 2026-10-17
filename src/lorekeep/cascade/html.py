"""Static HTML converted by Trafilatura, and the `<meta http-equiv="refresh">` stubs before it.

Trafilatura is imported on first use, like MarkItDown, so `lorekeep --help` stays fast.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from importlib import metadata
from urllib.parse import urljoin

import lxml.etree
import lxml.html
from cssselect import SelectorError

from lorekeep.cascade.step import Converted, Fallthrough

NAME = "trafilatura"
"""The first word of the `converter` this step writes: `trafilatura <version>`."""

_REFRESH = re.compile(
    r"^\s*\d*(?:\.\d+)?\s*[;,]?\s*(?:url\s*=\s*)?(['\"]?)(?P<url>.*?)\1\s*$", re.IGNORECASE
)


def convert_html(received: bytes, url: str, charset: str | None) -> Converted | Fallthrough:
    """The page's main content as Markdown with absolute links, and its canonical address."""
    document = parse(received, charset)
    if document is None:
        return Fallthrough(f"no content: {url} is empty", needs_browser=True)
    return extract(document, url)


def convert_rendered(html: str, url: str, cut: Sequence[str]) -> Converted | Fallthrough:
    """A document the browser rendered, without the elements the host rule's `cut` selectors
    name, converted as static HTML is."""
    document = parse(html.encode("utf-8"), "utf-8")
    if document is None:
        return Fallthrough(f"no content: the browser rendered {url} empty")
    for selector in cut:
        try:
            found = document.cssselect(selector)
        except SelectorError:
            return Fallthrough(f"cut selector {selector!r} is not valid CSS")
        for element in found:
            element.drop_tree()
    return extract(document, url)


def extract(document: lxml.html.HtmlElement, url: str) -> Converted | Fallthrough:
    """Trafilatura over the parsed document.

    Trafilatura's own `url=` resolves links against scheme and host only, so the links are made
    absolute in the tree the browser way (`<base>` honoured) and the tree is handed to it.
    """
    import trafilatura

    canonical = canonical_link(document, url)
    document.make_links_absolute(url, resolve_base_href=True)
    markdown = trafilatura.extract(
        document,
        url=url,
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=True,
        include_images=False,
        include_comments=False,
        with_metadata=False,
    )
    if markdown is None or not markdown.strip():
        return Fallthrough(f"no content: {url} yielded no text", needs_browser=True)
    return Converted(
        markdown=(markdown.strip() + "\n").encode("utf-8"),
        converter=f"{NAME} {metadata.version(NAME)}",
        original_ext="html",
        canonical=canonical,
    )


def refresh_target(received: bytes, url: str, charset: str | None) -> str | None:
    """The absolute target of a `<meta http-equiv="refresh">` stub; `None` for a page or a
    plain reload."""
    document = parse(received, charset)
    if document is None:
        return None
    for element in document.xpath("//meta[@http-equiv]"):
        if element.get("http-equiv", "").strip().lower() != "refresh":
            continue
        found = _REFRESH.match(element.get("content") or "")
        if found and found.group("url").strip():
            return urljoin(url, found.group("url").strip())
    return None


def parse(received: bytes, charset: str | None) -> lxml.html.HtmlElement | None:
    """The document, or `None` for a body with nothing to parse."""
    if not received.strip():
        return None
    parser = lxml.html.HTMLParser(encoding=charset) if charset else None
    try:
        return lxml.html.document_fromstring(received, parser=parser)
    except (lxml.etree.ParserError, LookupError):
        return None


def canonical_link(document: lxml.html.HtmlElement, base: str) -> str | None:
    """The absolute address of `<link rel="canonical">`, read before links are rewritten."""
    for element in document.xpath("//link[@href]"):
        if "canonical" in (element.get("rel") or "").lower().split():
            return urljoin(base, element.get("href", "").strip()) or None
    return None
