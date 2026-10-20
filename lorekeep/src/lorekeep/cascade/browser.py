"""Step 4: the browser, for a page a plain client cannot read.

The page fetcher (Crawl4AI in production) returns the rendered document untouched; lorekeep cuts
the host rule's `cut` selectors itself and converts what is left as static HTML. The Original is
the rendered document before the cut.

A page whose scripts load its content after the document has loaded renders as a shell: a menu
and a payload `<script>`. The step judges each render as the static step judges a page (thin
Markdown against the document's text) and renders again, waiting longer, up to three attempts;
no host rule tunes it. A shell after the last attempt stores nothing.
"""

from __future__ import annotations

import hashlib

import httpx

from lorekeep.cascade.html import THIN_CHARACTERS, THIN_WORDS, Shell, convert_rendered
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Same
from lorekeep.cascade.twin import decoded, page_url
from lorekeep.edges import FetcherNotInstalled, PageFetchError, Wait
from lorekeep.project import HostRule

BROWSER_MARK = "via crawl4ai"


NEVER_REREAD = "was read through the browser and cannot be compared"
"""Why a browser's Version is never rechecked: rendered bytes differ on every visit."""


GROWN = (
    "js:() => {"
    " const root = document.querySelector('main') || document.querySelector('[role=main]')"
    " || document.querySelector('article') || document.body;"
    " const words = root ? root.innerText.split(/\\s+/).filter(Boolean) : [];"
    f" return words.join(' ').length >= {THIN_CHARACTERS} && words.length >= {THIN_WORDS}; }}"
)
"""The `wait_for` condition: the page's main text (`innerText`, which leaves scripts out) has
grown past the thin threshold."""

ATTEMPTS = (
    Wait(wait_until="networkidle"),
    Wait(wait_until="networkidle", delay_before_return_html=3.0),
    Wait(
        wait_until="networkidle",
        delay_before_return_html=3.0,
        wait_for=GROWN,
        wait_for_timeout=15000,
    ),
)
"""Each render waits longer than the one before; the next runs only when this one was a shell.
A `wait_for` that times out returns the document as it is, judged like the others."""


def via_browser(converter: str) -> bool:
    """Whether a Version's `converter` says the browser rendered it."""
    return BROWSER_MARK in converter


class BrowserStep:
    def attempt(self, request: Request) -> Fetched | Fallthrough:
        if request.fetcher is None:
            return Fallthrough("no browser was given")
        address = page_url(request.url, request.rule)
        cut = request.rule.cut if request.rule is not None else ()
        characters = 0
        for wait in ATTEMPTS:
            try:
                rendered = request.fetcher.fetch(address, wait)
                version = request.fetcher.version()
            except (FetcherNotInstalled, PageFetchError) as error:
                return Fallthrough(str(error))
            converted = convert_rendered(rendered.html, rendered.final_url, cut)
            if isinstance(converted, Shell):
                characters = converted.characters
                continue
            if isinstance(converted, Fallthrough):
                return Fallthrough(converted.reason)
            original = rendered.html.encode("utf-8")
            return Fetched(
                markdown=converted.markdown,
                converter=f"{converted.converter} {BROWSER_MARK} {version}",
                final_url=rendered.final_url,
                original_url=decoded(rendered.final_url),
                mediatype="text/html",
                original_sha256=hashlib.sha256(original).hexdigest(),
                original=original,
                original_ext="html",
                canonical=converted.canonical,
                title=converted.title,
                warnings=converted.warnings,
            )
        return Fallthrough(
            f"the browser rendered a shell ({characters} characters after {len(ATTEMPTS)} attempts)"
        )

    def reread(
        self, response: httpx.Response, rule: HostRule | None, *, unchanged: str | None = None
    ) -> Fetched | Fallthrough | Same:
        return Fallthrough(f"{response.url} {NEVER_REREAD}")
