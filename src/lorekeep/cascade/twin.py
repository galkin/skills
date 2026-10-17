"""Step 1: the publisher's Twin, accepted only when the response really is Markdown."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

import httpx
import yaml

from lorekeep.cascade.step import Fallthrough, Fetched, Request
from lorekeep.http import media_type
from lorekeep.project import HostRule

CONVERTER = "md-twin"
MODIFIED_KEYS = ("ms.date", "updated_at", "lastmod", "date")
_FRONTMATTER = re.compile(rb"\A---[ \t]*\r?\n(.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_LEADING_BLANK_LINES = re.compile(rb"\A(?:[ \t]*\r?\n)+")
_DATE = re.compile(r"\A\s*(\d{4}-\d{2}-\d{2})")


def twin_url(url: str, rule: HostRule) -> str:
    """The Twin's address built from the address as given; a Twin address is returned as is."""
    parts = urlsplit(url)
    if rule.twin == "md-suffix":
        path = parts.path
        if not path.endswith(".md"):
            path = path.rstrip("/")
            if rule.page_suffix and path.endswith(rule.page_suffix):
                path = path.removesuffix(rule.page_suffix)
            path += ".md"
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))
    if rule.twin == "accept-header":
        pairs = [unquote(piece) for piece in parts.query.split("&") if piece]
        if "accept=text/markdown" in pairs:
            return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        query = f"{parts.query}&accept=text/markdown" if parts.query else "accept=text/markdown"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def page_url(url: str, rule: HostRule | None) -> str:
    """The page's address from a Twin address as given (the reverse of `twin_url`); any other
    address is returned as is."""
    if rule is None:
        return url
    parts = urlsplit(url)
    if rule.twin == "md-suffix" and parts.path.endswith(".md"):
        path = parts.path.removesuffix(".md") + (rule.page_suffix or "")
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    if rule.twin == "accept-header":
        pieces = [piece for piece in parts.query.split("&") if piece]
        kept = [piece for piece in pieces if unquote(piece) != "accept=text/markdown"]
        if len(kept) != len(pieces):
            query = "&".join(kept)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    return url


def accepts(mediatype: str, rule: HostRule) -> bool:
    """A Twin is `text/markdown`, or plain text from a raw file host."""
    return mediatype == "text/markdown" or (rule.twin == "raw" and mediatype == "text/plain")


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
        mediatype = media_type(response)
        if response.status_code != 200:
            return Fallthrough(f"no Twin: {address} answered {response.status_code}")
        if not accepts(mediatype, rule):
            return Fallthrough(f"no Twin: {address} answered {mediatype or 'no media type'}")
        received = response.content
        fields, body = split_frontmatter(received)
        canonical = _text(fields.get("canonicalUrl"))
        return Fetched(
            markdown=_LEADING_BLANK_LINES.sub(b"", body),
            converter=CONVERTER,
            final_url=canonical or str(response.url),
            original_url=decoded(str(response.url)),
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
