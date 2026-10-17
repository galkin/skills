"""Step 1: the publisher's Twin, accepted only when the response really is Markdown."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

import httpx
import yaml

from lorekeep import twins
from lorekeep.cascade.step import Fallthrough, Fetched, Request
from lorekeep.http import media_type
from lorekeep.project import HostRule

CONVERTER = "md-twin"
MODIFIED_KEYS = ("ms.date", "updated_at", "lastmod", "date")
_FRONTMATTER = re.compile(rb"\A---[ \t]*\r?\n(.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_LEADING_BLANK_LINES = re.compile(rb"\A(?:[ \t]*\r?\n)+")
_DATE = re.compile(r"\A\s*(\d{4}-\d{2}-\d{2})")


def twin_url(url: str, rule: HostRule) -> str:
    """The Twin's address built from the address as given (no fragment goes on the wire); a Twin
    address is returned as is."""
    parts = urlsplit(url)
    pieces = [piece for piece in parts.query.split("&") if piece]
    path, pieces = twins.to_twin(parts.path, pieces, rule)
    return urlunsplit((parts.scheme, parts.netloc, path, "&".join(pieces), ""))


def page_url(url: str, rule: HostRule | None) -> str:
    """The page's address from a Twin address as given (the reverse of `twin_url`); any other
    address is returned as is."""
    if rule is None:
        return url
    parts = urlsplit(url)
    pieces = [piece for piece in parts.query.split("&") if piece]
    path, kept = twins.to_page(parts.path, pieces, rule)
    if (path, kept) == (parts.path, pieces):
        return url
    return urlunsplit((parts.scheme, parts.netloc, path, "&".join(kept), parts.fragment))


def accepts(mediatype: str, rule: HostRule | None) -> bool:
    """Whether a Twin may answer `mediatype`: Markdown, or plain text from a raw file host."""
    return mediatype in twins.media_types(rule)


class TwinStep:
    def attempt(self, request: Request) -> Fetched | Fallthrough:
        rule = request.rule
        if rule is None or rule.twin is None:
            return Fallthrough("the host rule names no Twin")
        address = twin_url(request.url, rule)
        try:
            response = request.client.get(address)
        except httpx.HTTPError as error:
            return Fallthrough(f"no Twin: {address} failed ({type(error).__name__})")
        if response.status_code != 200:
            return Fallthrough(f"no Twin: {address} answered {response.status_code}")
        return read_twin(response, rule)


def read_twin(response: httpx.Response, rule: HostRule | None) -> Fetched | Fallthrough:
    """What a `200` to a Twin address holds, once its media type passes the Twin's gate."""
    address = str(response.url)
    mediatype = media_type(response)
    if not accepts(mediatype, rule):
        return Fallthrough(f"no Twin: {address} answered {mediatype or 'no media type'}")
    received = response.content
    fields, body = split_frontmatter(received)
    canonical = _text(fields.get("canonicalUrl"))
    return Fetched(
        markdown=_LEADING_BLANK_LINES.sub(b"", body),
        converter=CONVERTER,
        final_url=canonical or address,
        original_url=decoded(address),
        mediatype=mediatype,
        original_sha256=hashlib.sha256(received).hexdigest(),
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
        title=_text(fields.get("title")),
        modified=first_date(fields),
    )


def split_frontmatter(data: bytes) -> tuple[dict[str, Any], bytes]:
    """The publisher's own frontmatter (strings only) and the body after it.

    A leading `---` block that is not a YAML mapping is left in the body: it is text, not
    frontmatter.
    """
    match = _FRONTMATTER.match(data)
    if match is None:
        return {}, data
    try:
        fields = yaml.load((match.group(1) or b"").decode("utf-8"), Loader=yaml.BaseLoader)
    except (yaml.YAMLError, UnicodeDecodeError):
        return {}, data
    if fields is None:
        fields = {}
    if not isinstance(fields, dict):
        return {}, data
    return fields, data[match.end() :]


def first_date(fields: dict[str, Any]) -> str | None:
    """`YYYY-MM-DD` from the first of `ms.date`, `updated_at`, `lastmod`, `date` that holds one."""
    for key in MODIFIED_KEYS:
        found = _DATE.match(_text(fields.get(key)) or "")
        if found:
            return found.group(1)
    return None


def decoded(url: str) -> str:
    """`url` with its query percent-decoded, as `original.url` records it."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, unquote(parts.query), ""))


def _text(value: Any) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None
