"""What a cascade step receives and returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from lorekeep.edges import PageFetcher
from lorekeep.project import HostRule


@dataclass(frozen=True)
class Request:
    """What a step is asked for: the address as given (sent untouched) and its host rule, with
    the plain client and the browser to ask it with."""

    url: str
    rule: HostRule | None
    client: httpx.Client
    fetcher: PageFetcher | None = None


@dataclass(frozen=True)
class Fetched:
    """A step's result: the Markdown and the Provenance it learned on the way.

    `final_url` is where the page says it lives (after redirects and any canonical address),
    not yet normalised; `original_url` is the address the bytes came from. `original` is
    `None` when the Original is not stored (a Twin), but `original_sha256` always hashes the
    bytes received.
    """

    markdown: bytes
    converter: str
    final_url: str
    original_url: str
    mediatype: str
    original_sha256: str
    original: bytes | None = None
    original_ext: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    title: str | None = None
    modified: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Converted:
    """What a converter of the page step made of the received bytes; `canonical` is the address
    the document names as its own (`<link rel="canonical">`), absolute, when it names one;
    `warnings` say what the conversion knowingly lost, one line each, without `lorekeep:`."""

    markdown: bytes
    converter: str
    original_ext: str
    title: str | None = None
    canonical: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Same:
    """A reread's answer when the received bytes are the Version's own: nothing to convert."""


@dataclass(frozen=True)
class Fallthrough:
    """Why a step declined; the next step runs. `needs_browser` says the page may still be read
    by the browser: the plain client was refused (`403`/`429`) or the HTML yielded no text or
    too little of it. `final` stops the cascade: the page was received and its converter failed,
    so no other step may stand in for it, and `reason` is the whole error line."""

    reason: str
    needs_browser: bool = False
    final: bool = False


class Step(Protocol):
    def attempt(self, request: Request) -> Fetched | Fallthrough: ...

    def reread(
        self, response: httpx.Response, rule: HostRule | None, *, unchanged: str | None = None
    ) -> Fetched | Fallthrough | Same:
        """What a `200` to this step's own address holds, for a Recheck of a Version this step
        wrote: the response passes the step's media-type gate first, then bytes whose sha256 is
        `unchanged` are `Same` without a conversion, then the step converts. A `Fallthrough`
        names the address and the reason."""
        ...
