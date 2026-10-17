"""The Twin kinds a host rule may name, in one place: how a page address becomes its Twin's
address and back, and what media types a Twin may answer.

`md-suffix`: the page's path with `page_suffix` (when any) replaced by `.md`. `accept-header`:
the page's address with `accept=text/markdown` in the query. `raw`: the address as given is its
own Twin and answers plain text. The path and the raw query pieces are handled as given, so what
goes on the wire keeps its encoding.
"""

from __future__ import annotations

from urllib.parse import unquote

from lorekeep.project import HostRule

MARKDOWN = "text/markdown"
PLAIN_TEXT = "text/plain"
ACCEPT_PIECE = "accept=text/markdown"
MD = ".md"


def is_accept_piece(piece: str) -> bool:
    return unquote(piece) == ACCEPT_PIECE


def to_twin(path: str, pieces: list[str], rule: HostRule) -> tuple[str, list[str]]:
    """The Twin's path and query pieces built from the page's; a Twin address is returned as is."""
    if rule.twin == "md-suffix":
        if path.endswith(MD):
            return path, pieces
        page = path.rstrip("/")
        if rule.page_suffix and page.endswith(rule.page_suffix):
            page = page.removesuffix(rule.page_suffix)
        return page + MD, pieces
    if rule.twin == "accept-header" and not any(is_accept_piece(piece) for piece in pieces):
        return path, [*pieces, ACCEPT_PIECE]
    return path, pieces


def to_page(path: str, pieces: list[str], rule: HostRule) -> tuple[str, list[str]]:
    """The page's path and query pieces from a Twin's (the reverse of `to_twin`); any other
    address is returned as is."""
    if rule.twin == "md-suffix" and path.endswith(MD):
        return path.removesuffix(MD) + (rule.page_suffix or ""), pieces
    if rule.twin == "accept-header":
        return path, [piece for piece in pieces if not is_accept_piece(piece)]
    return path, pieces


def media_types(rule: HostRule | None) -> tuple[str, ...]:
    """What a Twin may answer: Markdown, or plain text too from a raw file host."""
    if rule is not None and rule.twin == "raw":
        return (MARKDOWN, PLAIN_TEXT)
    return (MARKDOWN,)
