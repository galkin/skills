"""The page itself over plain HTTP, fetched once and converted by the step its media type names.

The response's media type — never the URL's extension — picks the converter; a media type no
converter takes is reported as unsupported and nothing is stored. An HTML stub that only says
`<meta http-equiv="refresh">` is followed like a redirect, and never converted.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

import httpx

from lorekeep.cascade.html import convert_html, refresh_target
from lorekeep.cascade.pdf import convert_pdf
from lorekeep.cascade.step import Converted, Fallthrough, Fetched, Request
from lorekeep.cascade.twin import decoded, page_url
from lorekeep.http import media_type

Converter = Callable[[bytes, str, str | None], Converted | Fallthrough]
"""`(received bytes, the address they came from, the charset the response named)`."""

HTML_TYPES = ("text/html", "application/xhtml+xml")
CONVERTERS: Mapping[str, Converter] = {
    "text/html": convert_html,
    "application/xhtml+xml": convert_html,
    "application/pdf": convert_pdf,
}
MAX_REFRESHES = 5
REFUSED = (403, 429)
"""What a host answers a plain client it will not serve: the signal for the browser step."""


class PageStep:
    def __init__(self, converters: Mapping[str, Converter] = CONVERTERS) -> None:
        self.converters = converters

    def attempt(self, request: Request) -> Fetched | Fallthrough:
        address = page_url(request.url, request.rule)
        for _ in range(MAX_REFRESHES + 1):
            try:
                response = request.client.get(address)
            except httpx.HTTPError as error:
                return Fallthrough(f"{address} failed ({type(error).__name__})")
            if response.status_code != 200:
                return Fallthrough(
                    f"{address} answered {response.status_code}",
                    needs_browser=response.status_code in REFUSED,
                )
            mediatype = media_type(response)
            final_url = str(response.url)
            target = (
                refresh_target(response.content, final_url, response.charset_encoding)
                if mediatype in HTML_TYPES
                else None
            )
            if target is None or target == final_url:
                return self._convert(response, mediatype)
            address = target
        return Fallthrough(f"{address}: more than {MAX_REFRESHES} meta refreshes")

    def _convert(self, response: httpx.Response, mediatype: str) -> Fetched | Fallthrough:
        convert = self.converters.get(mediatype)
        if convert is None:
            return Fallthrough(f"unsupported media type {mediatype or '(none)'}")
        received = response.content
        final_url = str(response.url)
        converted = convert(received, final_url, response.charset_encoding)
        if isinstance(converted, Fallthrough):
            return converted
        return Fetched(
            markdown=converted.markdown,
            converter=converted.converter,
            final_url=converted.canonical or final_url,
            original_url=decoded(final_url),
            mediatype=mediatype,
            original_sha256=hashlib.sha256(received).hexdigest(),
            original=received,
            original_ext=converted.original_ext,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            title=converted.title,
        )
