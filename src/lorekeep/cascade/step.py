"""What a cascade step receives and returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from lorekeep.project import HostRule


@dataclass(frozen=True)
class Request:
    """What a step is asked for: the address as given (sent untouched) and its host rule."""

    url: str
    rule: HostRule | None
    client: httpx.Client


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


@dataclass(frozen=True)
class Converted:
    """What a converter of the page step made of the received bytes."""

    markdown: bytes
    converter: str
    original_ext: str
    title: str | None = None


@dataclass(frozen=True)
class Fallthrough:
    """Why a step declined; the next step runs."""

    reason: str


class Step(Protocol):
    def attempt(self, request: Request) -> Fetched | Fallthrough: ...
