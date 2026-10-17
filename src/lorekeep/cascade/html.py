"""Static HTML converted by Trafilatura, and the `<meta http-equiv="refresh">` stubs before it.

Trafilatura decides what the page's content is; lorekeep prepares the tree first so that the
structure a documentation site wraps around code, tables and headings cannot hide them, then
checks the Markdown against the tree and says what is still missing. Trafilatura is imported on
first use, like MarkItDown, so `lorekeep --help` stays fast.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
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

HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
PERMALINK_CLASSES = frozenset({"headerlink", "anchor"})
PERMALINK_TEXTS = frozenset({"", "#", "¶", "🔗"})
"""What a heading's permalink anchor reads; any other text in a heading's `<a>` is content."""
GUTTER_CLASSES = frozenset({"linenos", "lineno", "line-number", "line-numbers", "gutter"})
"""Line numbers drawn beside code: not part of it."""
LINE_BLOCKS = frozenset({"div", "p", "li", "tr", "table", "ul", "ol", *HEADINGS})
"""Elements that end a line inside a `<pre>` (syntax highlighters draw one line per `<div>`)."""
WRAPPERS = frozenset({"div", "span"})
FIELD_NAMES = "//button[@data-component-part='field-name']"
"""Mintlify draws a parameter's name as a `<button>` (it copies a link), which Trafilatura drops
with every other button; it is the name of the parameter the paragraphs below it describe."""
MAIN_SUBTREE = ("//main", "//*[@role='main']", "//article")
"""Where the content is when Trafilatura's own choice lost part of it, in order of trust."""

THIN_CHARACTERS = 600
THIN_WORDS = 40
THIN_RATIO = 5
"""A page is thin when its Markdown has fewer than 600 characters or 40 words of text and the
Original's text content (scripts included: a client-rendered page carries its content there) is
at least five times longer. Whatever its size, a Markdown whose text is under a fifth of the text
a reader sees in the page's main element is stored with a warning."""
UNSEEN = (
    ".//script | .//style | .//noscript | .//template | .//nav | .//aside | .//header"
    " | .//footer | .//*[@role='navigation']"
)
"""What a reader of the main element does not read as its text: code that is not shown, and the
site's own navigation, which some themes put inside `<main>` (Docker, Grafana)."""

_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_HEADING = re.compile(r"^#{1,6}\s")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_GLUED_FENCE = re.compile(r"^(?P<text>\s*\S.*?)\s*(?P<fence>```)$")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_MARKUP = re.compile(r"[\\`*\[\]]")
NAVIGATION = "ancestor::nav | ancestor::aside | ancestor::header | ancestor::footer"


def convert_html(received: bytes, url: str, charset: str | None) -> Converted | Fallthrough:
    """The page's main content as Markdown with absolute links, and its canonical address; a
    page whose Markdown is a sliver of its text is left to the browser (`thin content`)."""
    document = parse(received, charset)
    if document is None:
        return Fallthrough(f"no content: {url} is empty", needs_browser=True)
    page_text = len(" ".join(document.text_content().split()))
    converted = extract(document, url)
    if isinstance(converted, Fallthrough):
        return converted
    text = _LINK_TARGET.sub("]", converted.markdown.decode("utf-8"))
    characters, words = len(" ".join(text.split())), len(text.split())
    if (characters < THIN_CHARACTERS or words < THIN_WORDS) and page_text >= THIN_RATIO * max(
        characters, 1
    ):
        return Fallthrough(
            f"thin content: {url} converted to {characters} characters of a page of {page_text}",
            needs_browser=True,
        )
    return converted


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


@dataclass(frozen=True)
class Shape:
    """What a conversion should keep, or kept: the text of each code block, the number of
    tables and of headings, and the items of each list in running text. A page's code blocks
    are its distinct `<pre>` texts (Trafilatura writes a block repeated verbatim once); the
    Markdown's are its fences, `fences` many. `text` is the Markdown's text without its
    markup."""

    code: frozenset[str]
    tables: int
    headings: int
    lists: tuple[tuple[str, ...], ...] = ()
    fences: int = 0
    text: str = ""

    def covers(self, other: Shape) -> bool:
        """Whether this Markdown keeps at least as many fences, tables and headings."""
        return (
            self.fences >= other.fences
            and self.tables >= other.tables
            and self.headings >= other.headings
        )


@dataclass(frozen=True)
class Missing:
    """What the Markdown lacks of the page."""

    code: int
    tables: int
    headings: bool
    lists: int

    @classmethod
    def of(cls, page: Shape, markdown: Shape) -> Missing:
        fenced = "\n".join(markdown.code)
        return cls(
            code=sum(1 for text in page.code if text not in fenced),
            tables=max(page.tables - markdown.tables, 0),
            headings=bool(page.headings) and not markdown.headings,
            lists=sum(
                1 for items in page.lists if any(item not in markdown.text for item in items)
            ),
        )

    @property
    def loss(self) -> int:
        return self.code + self.tables + int(self.headings) + self.lists


def extract(document: lxml.html.HtmlElement, url: str) -> Converted | Fallthrough:
    """Trafilatura over the prepared document, retried on the main subtree when it lost code,
    tables, every heading or a list of links in running text. The retry is taken when it loses
    less and keeps at least as many fences, tables and headings; a loss of code or tables that
    remains is a warning, not a refusal.

    Trafilatura's own `url=` resolves links against scheme and host only, so the links are made
    absolute in the tree the browser way (`<base>` honoured) and the tree is handed to it.
    """
    canonical = canonical_link(document, url)
    prepare(document)
    document.make_links_absolute(url, resolve_base_href=True)
    title = page_title(document, url)
    expected = tree_shape(document)
    markdown = trafilatura_markdown(copy.deepcopy(document), url, favor_recall=False)
    if markdown is None:
        return Fallthrough(f"no content: {url} yielded no text", needs_browser=True)
    kept = markdown_shape(markdown)
    missing = Missing.of(expected, kept)
    if missing.loss:
        main = main_subtree(document)
        retried = trafilatura_markdown(main, url, favor_recall=True) if main is not None else None
        if retried is not None:
            kept_on_retry = markdown_shape(retried)
            retried_missing = Missing.of(expected, kept_on_retry)
            if retried_missing.loss < missing.loss and kept_on_retry.covers(kept):
                markdown, missing = retried, retried_missing
    warnings: list[str] = []
    if missing.code or missing.tables:
        warnings.append(
            f"{missing.code} code blocks / {missing.tables} tables of the page are "
            "missing from the Markdown"
        )
    markdown = finish(markdown, title)
    main = main_text(document)
    kept_text = len(markdown_shape(markdown).text)
    if main is not None and THIN_RATIO * kept_text < main:
        warnings.append(f"the Markdown holds {100 * kept_text // main}% of the page's main text")
    return Converted(
        markdown=markdown.encode("utf-8"),
        converter=f"{NAME} {metadata.version(NAME)}",
        original_ext="html",
        title=title,
        canonical=canonical,
        warnings=tuple(warnings),
    )


def main_text(document: lxml.html.HtmlElement) -> int | None:
    """How many characters of text a reader sees in the page's `<main>`, `role=main` or
    `<article>` (the first found, without its scripts and navigation); `None` when it has none."""
    for path in MAIN_SUBTREE:
        found = document.xpath(path)
        if found:
            main = copy.deepcopy(found[0])
            for element in main.xpath(UNSEEN):
                element.drop_tree()
            return len(squeeze(main.text_content()))
    return None


def trafilatura_markdown(
    document: lxml.html.HtmlElement, url: str, *, favor_recall: bool
) -> str | None:
    """Trafilatura's Markdown of `document`, `None` when it found no text."""
    import trafilatura

    markdown = trafilatura.extract(
        document,
        url=url,
        output_format="markdown",
        favor_recall=favor_recall,
        include_formatting=True,
        include_links=True,
        include_tables=True,
        include_images=False,
        include_comments=False,
        with_metadata=False,
    )
    if markdown is None or not markdown.strip():
        return None
    return unglue_fences(markdown)


def unglue_fences(markdown: str) -> str:
    """Trafilatura's Markdown with each fence it wrote at the end of a line of text moved to a
    line of its own, where a Markdown reader sees it: a `<pre>` after a paragraph inside a list
    item comes out as "The output is similar to this:" and the fence on one line."""
    lines: list[str] = []
    fenced = False
    for line in markdown.splitlines():
        glued = None if fenced else _GLUED_FENCE.match(line)
        if glued:
            lines += [glued.group("text"), glued.group("fence")]
            fenced = True
            continue
        if _FENCE.match(line):
            fenced = not fenced
        lines.append(line)
    return "\n".join(lines)


def prepare(document: lxml.html.HtmlElement) -> None:
    """Drop heading permalinks, flatten every `<pre>` to its text in one `<pre><code>`, and lift
    each `<pre>` and `<table>` out of the wrappers that hold nothing else, so no class a site's
    theme puts on them reads as boilerplate."""
    for anchor in document.xpath("//a"):
        if permalink(anchor):
            anchor.drop_tree()
    for name in document.xpath(FIELD_NAMES):
        name.tag = "code"
        name.attrib.clear()
    for pre in document.xpath("//pre[not(ancestor::pre)]"):
        text = code_text(pre)
        tail = pre.tail
        pre.clear()
        pre.tail = tail
        code = lxml.html.Element("code")
        code.text = text
        pre.append(code)
    for element in document.xpath(
        "//pre[not(ancestor::pre)] | //table[not(ancestor::table) and not(ancestor::pre)]"
    ):
        lift(element)


def permalink(anchor: lxml.html.HtmlElement) -> bool:
    """Whether an `<a>` only links to the place it stands: a `headerlink`/`anchor`, a heading's
    `#`/`¶`/`🔗`/empty link, or a textless link to a fragment of the page."""
    text = anchor.text_content().replace("\u200b", "").strip()
    if set((anchor.get("class") or "").split()) & PERMALINK_CLASSES:
        return True
    if not text and (anchor.get("href") or "").startswith("#"):
        return True
    in_heading = any(parent.tag in HEADINGS for parent in anchor.iterancestors())
    return in_heading and text in PERMALINK_TEXTS


def code_text(pre: lxml.html.HtmlElement) -> str:
    """A `<pre>`'s code as a reader sees it: one line per line block, no line-number gutter."""
    parts: list[str] = []

    def ends_line() -> bool:
        return not parts or parts[-1].endswith("\n")

    def walk(element: lxml.html.HtmlElement) -> None:
        if element.tag == "br":
            parts.append("\n")
        if element.text:
            parts.append(element.text)
        for child in element:
            if isinstance(child.tag, str) and not (
                child.tag == "button" or set((child.get("class") or "").split()) & GUTTER_CLASSES
            ):
                walk(child)
            if child.tail:
                parts.append(child.tail)
        if element is not pre and element.tag in LINE_BLOCKS and not ends_line():
            parts.append("\n")

    walk(pre)
    return "".join(parts).rstrip("\n") + "\n"


def lift(element: lxml.html.HtmlElement) -> None:
    """Put `element` in the place of the outermost `<div>`/`<span>` around it whose text is its
    own and that holds no other code block or table."""
    own = " ".join(element.text_content().split())
    top = None
    for ancestor in element.iterancestors():
        if (
            ancestor.tag not in WRAPPERS
            or " ".join(ancestor.text_content().split()) != own
            or len(ancestor.xpath(".//pre | .//table")) != 1 + len(element.xpath(".//table"))
        ):
            break
        top = ancestor
    if top is None:
        return
    parent = top.getparent()
    if parent is None:
        return
    element.tail = top.tail
    parent.replace(top, element)


def tree_shape(document: lxml.html.HtmlElement) -> Shape:
    """The code blocks, tables and headings the prepared page holds."""
    code = frozenset(
        squeezed
        for pre in document.xpath("//body//pre[not(ancestor::pre)]")
        if (squeezed := squeeze(pre.text_content()))
    )
    tables = sum(
        1
        for table in document.xpath("//body//table[not(ancestor::table) and not(ancestor::pre)]")
        if len(table.xpath(".//tr")) >= 2
    )
    headings = len(document.xpath("//body//*[self::h2 or self::h3 or self::h4]"))
    lists = tuple(items for _, items in prose_lists(document))
    return Shape(code=code, tables=tables, headings=headings, lists=lists)


def prose_lists(
    root: lxml.html.HtmlElement,
) -> Iterator[tuple[lxml.html.HtmlElement, tuple[str, ...]]]:
    """Each list a paragraph introduces ("The following are typical use cases:"), alone or in a
    `<div>` that holds nothing else (Sphinx's `toctree-wrapper`), outside navigation, with the
    text of its items: the lists Trafilatura must not take for a menu."""
    for found in root.xpath("//body//*[self::ul or self::ol]"):
        before = wrapper(found).getprevious()
        if before is None or before.tag != "p" or found.xpath(NAVIGATION):
            continue
        items = tuple(squeeze(item.text_content()) for item in found.findall("li"))
        if len(items) >= 2 and all(items):
            yield found, items


def wrapper(element: lxml.html.HtmlElement) -> lxml.html.HtmlElement:
    """The outermost `<div>` around `element` whose text is its own, else `element`."""
    own = squeeze(element.text_content())
    top = element
    for ancestor in element.iterancestors():
        if ancestor.tag != "div" or squeeze(ancestor.text_content()) != own:
            break
        top = ancestor
    return top


def markdown_shape(markdown: str) -> Shape:
    """The fences, pipe tables and headings a Markdown text holds."""
    blocks: list[list[str]] = []
    tables = 0
    headings = 0
    fenced = False
    for line in markdown.splitlines():
        if _FENCE.match(line):
            if not fenced:
                blocks.append([])
            fenced = not fenced
        elif fenced:
            blocks[-1].append(line)
        else:
            tables += bool(_TABLE_RULE.match(line))
            headings += bool(_HEADING.match(line))
    code = frozenset(squeeze("\n".join(block)) for block in blocks)
    text = squeeze(_MARKUP.sub("", _LINK_TARGET.sub("]", markdown)))
    return Shape(code=code, tables=tables, headings=headings, fences=len(blocks), text=text)


def squeeze(text: str) -> str:
    """`text` with every run of whitespace one space, for comparing code across renderings."""
    return " ".join(text.split())


def main_subtree(document: lxml.html.HtmlElement) -> lxml.html.HtmlElement | None:
    """A copy of the page's `<main>`, `role=main` or `<article>` as a document of its own, in
    which an item of a list in running text that is nothing but a link keeps its text and loses
    the link: Trafilatura drops every short run of links as navigation, and a list of a page's
    subjects is no navigation."""
    for path in MAIN_SUBTREE:
        found = document.xpath(path)
        if found:
            root = lxml.html.document_fromstring("<html><body></body></html>")
            body = root.find("body")
            assert body is not None
            body.append(copy.deepcopy(found[0]))
            for listed, _ in prose_lists(root):
                for item in listed.findall("li"):
                    links = item.findall(".//a")
                    if links and squeeze(item.text_content()) == squeeze(
                        " ".join(link.text_content() for link in links)
                    ):
                        for link in links:
                            link.drop_tag()
            return root
    return None


def finish(markdown: str, title: str | None) -> str:
    """Trafilatura's Markdown with `\\_` written as `_` outside code, and the title as the first
    heading when the page kept none."""
    lines: list[str] = []
    fenced = False
    headings = False
    for line in markdown.strip().splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            line = line.replace("\\_", "_")
            headings = headings or bool(_HEADING.match(line))
        lines.append(line)
    if not headings and title:
        lines[:0] = [f"# {title}", ""]
    return "\n".join(lines) + "\n"


def page_title(document: lxml.html.HtmlElement, url: str) -> str | None:
    """Trafilatura's title of the page, else its `<title>`, else its first `<h1>`."""
    import trafilatura

    found = trafilatura.extract_metadata(copy.deepcopy(document), default_url=url).title
    if not found:
        found = document.findtext(".//title")
    if not found:
        heading = document.find(".//h1")
        found = heading.text_content() if heading is not None else None
    found = " ".join((found or "").split())
    return found or None


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
    """The document without comments or processing instructions, or `None` for a body with
    nothing to parse."""
    if not received.strip():
        return None
    parser = lxml.html.HTMLParser(encoding=charset, remove_comments=True, remove_pis=True)
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
