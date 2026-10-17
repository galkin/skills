"""The page itself over plain HTTP, fetched once and converted by the step its media type names.

The response's media type — never the URL's extension — picks the converter; a media type no
converter takes is reported as unsupported and nothing is stored.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

import httpx

from lorekeep.cascade.pdf import convert_pdf
from lorekeep.cascade.step import Converted, Fallthrough, Fetched, Request
from lorekeep.cascade.twin import decoded
from lorekeep.http import media_type

Converter = Callable[[bytes], Converted | Fallthrough]

CONVERTERS: Mapping[str, Converter] = {"application/pdf": convert_pdf}


class PageStep:
    def __init__(self, converters: Mapping[str, Converter] = CONVERTERS) -> None:
        self.converters = converters

    def attempt(self, request: Request) -> Fetched | Fallthrough:
        try:
            response = request.client.get(request.url)
        except httpx.HTTPError as error:
            return Fallthrough(f"{request.url} failed ({type(error).__name__})")
        if response.status_code != 200:
            return Fallthrough(f"{request.url} answered {response.status_code}")
        mediatype = media_type(response)
        convert = self.converters.get(mediatype)
        if convert is None:
            return Fallthrough(f"unsupported media type {mediatype or '(none)'}")
        received = response.content
        converted = convert(received)
        if isinstance(converted, Fallthrough):
            return converted
        return Fetched(
            markdown=converted.markdown,
            converter=converted.converter,
            final_url=str(response.url),
            original_url=decoded(str(response.url)),
            mediatype=mediatype,
            original_sha256=hashlib.sha256(received).hexdigest(),
            original=received,
            original_ext=converted.original_ext,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            title=converted.title,
        )
