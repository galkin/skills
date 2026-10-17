"""Step 4: the browser, for a page a plain client cannot read.

The page fetcher (Crawl4AI in production) returns the rendered document untouched; lorekeep cuts
the host rule's `cut` selectors itself and converts what is left as static HTML. The Original is
the rendered document before the cut.
"""

from __future__ import annotations

import hashlib

import httpx

from lorekeep.cascade.html import convert_rendered
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Same
from lorekeep.cascade.twin import decoded, page_url
from lorekeep.edges import FetcherNotInstalled, PageFetchError
from lorekeep.project import HostRule

BROWSER_MARK = "via crawl4ai"


NEVER_REREAD = "was read through the browser and cannot be compared"
"""Why a browser's Version is never rechecked: rendered bytes differ on every visit."""


def via_browser(converter: str) -> bool:
    """Whether a Version's `converter` says the browser rendered it."""
    return BROWSER_MARK in converter


class BrowserStep:
    def attempt(self, request: Request) -> Fetched | Fallthrough:
        if request.fetcher is None:
            return Fallthrough("no browser was given")
        address = page_url(request.url, request.rule)
        try:
            rendered = request.fetcher.fetch(address)
            version = request.fetcher.version()
        except (FetcherNotInstalled, PageFetchError) as error:
            return Fallthrough(str(error))
        cut = request.rule.cut if request.rule is not None else ()
        converted = convert_rendered(rendered.html, rendered.final_url, cut)
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
        )

    def reread(
        self, response: httpx.Response, rule: HostRule | None, *, unchanged: str | None = None
    ) -> Fetched | Fallthrough | Same:
        return Fallthrough(f"{response.url} {NEVER_REREAD}")
