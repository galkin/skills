"""Step 1: the publisher's Twin, accepted only when the response really is Markdown.

Under a `github-raw` rule the Twin is the raw file behind a `blob` page: kept as published when it
is Markdown or text, else in one fence named by its extension under a `# <path>` heading, and
filed under the `blob` page (`converter: raw-twin`).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

import httpx
import yaml

from lorekeep import twins
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Same
from lorekeep.cascade.verbatim import fence
from lorekeep.http import media_type
from lorekeep.project import HostRule

CONVERTER = "md-twin"
RAW_CONVERTER = "raw-twin"
TEXT_EXTENSIONS = (".md", ".markdown", ".txt")
MARKDOWN_EXTENSIONS = (".md", ".markdown")
MODIFIED_KEYS = ("ms.date", "updated_at", "lastmod", "date")
_FRONTMATTER = re.compile(rb"\A---[ \t]*\r?\n(.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_LEADING_BLANK_LINES = re.compile(rb"\A(?:[ \t]*\r?\n)+")
_DATE = re.compile(r"\A\s*(\d{4}-\d{2}-\d{2})")
_HEADING = re.compile(r"^# +(.+?)[ #]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def twin_url(url: str, rule: HostRule) -> str | None:
    """The Twin's address built from the address as given (no fragment goes on the wire); a Twin
    address is returned as is; `None` when the rule gives this address no Twin (a GitHub page
    that is not a `blob`)."""
    parts = urlsplit(url)
    if rule.twin == "github-raw":
        raw = twins.to_raw(parts.hostname or "", parts.path)
        if raw is None:
            return None
        return urlunsplit((parts.scheme, raw[0], raw[1], parts.query, ""))
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


def blob_url(url: str) -> str:
    """The GitHub `blob` page of a raw file's address; any other address is returned as is."""
    parts = urlsplit(url)
    blob = twins.to_blob(parts.hostname or "", parts.path)
    if blob is None:
        return url
    return urlunsplit((parts.scheme, blob[0], blob[1], parts.query, ""))


class TwinStep:
    def attempt(self, request: Request) -> Fetched | Fallthrough:
        rule = request.rule
        if rule is None or rule.twin is None:
            return Fallthrough("the host rule names no Twin")
        address = twin_url(request.url, rule)
        if address is None:
            return Fallthrough(f"no Twin: {request.url} is not a file the {rule.twin} rule maps")
        try:
            response = request.client.get(address)
        except httpx.HTTPError as error:
            return Fallthrough(f"no Twin: {address} failed ({type(error).__name__})")
        if response.status_code != 200:
            return Fallthrough(f"no Twin: {address} answered {response.status_code}")
        found = self.reread(response, rule)
        assert not isinstance(found, Same)  # nothing was `unchanged`
        return found

    def reread(
        self, response: httpx.Response, rule: HostRule | None, *, unchanged: str | None = None
    ) -> Fetched | Fallthrough | Same:
        """What a `200` to a Twin address holds, once its media type passes the Twin's gate
        under the host's current rule (`text/markdown` is taken even when the rule no longer
        names a Twin; plain text only from a raw file host, or under `md-suffix` when it is not
        HTML). Under `github-raw` the file is filed under its `blob` page."""
        address = str(response.url)
        mediatype = media_type(response)
        received = response.content
        if not twins.accepts(mediatype, received, rule):
            return Fallthrough(f"no Twin: {address} answered {mediatype or 'no media type'}")
        sha256 = hashlib.sha256(received).hexdigest()
        if sha256 == unchanged:
            return Same()
        if rule is not None and rule.twin == "github-raw":
            markdown, fields, title = raw_file(urlsplit(address).path, received)
            converter, final_url = RAW_CONVERTER, blob_url(address)
        else:
            fields, body = split_frontmatter(received)
            markdown = _LEADING_BLANK_LINES.sub(b"", body)
            title = _text(fields.get("title")) or first_heading(markdown)
            converter = CONVERTER
            final_url = _text(fields.get("canonicalUrl")) or address
        return Fetched(
            markdown=markdown,
            converter=converter,
            final_url=final_url,
            original_url=decoded(address),
            mediatype=mediatype,
            original_sha256=sha256,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            title=title,
            modified=first_date(fields),
        )


def raw_file(raw_path: str, received: bytes) -> tuple[bytes, dict[str, Any], str]:
    """A raw GitHub file as Markdown, with the frontmatter it carried and its title.

    Markdown is kept as published (its frontmatter mined like any Twin's) and text as is; any
    other file becomes `# <path>` and one fence named by its extension, the file verbatim inside.
    The path is the file's within its repository; the title is the Markdown's own, else the path.
    """
    path = unquote(raw_path).split("/", 4)[-1]
    name = path.rsplit("/", 1)[-1]
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suffix in MARKDOWN_EXTENSIONS:
        fields, body = split_frontmatter(received)
        markdown = _LEADING_BLANK_LINES.sub(b"", body)
        return markdown, fields, _text(fields.get("title")) or first_heading(markdown) or path
    if suffix in TEXT_EXTENSIONS:
        return received, {}, path
    text = received.decode("utf-8", errors="replace")
    return f"# {path}\n\n{fence(text, suffix[1:])}".encode(), {}, path


def first_heading(markdown: bytes) -> str | None:
    """The text of the first `# ` heading outside a fence, when there is one."""
    inside: str | None = None
    for line in markdown.decode("utf-8", errors="replace").splitlines():
        opener = _FENCE.match(line)
        if opener is not None:
            marker = opener.group(1)
            if inside is None:
                inside = marker
            elif marker[0] == inside[0] and len(marker) >= len(inside):
                inside = None
            continue
        if inside is None and (heading := _HEADING.match(line)):
            return heading.group(1).strip() or None
    return None


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
