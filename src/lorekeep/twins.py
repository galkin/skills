"""The Twin kinds a host rule may name, in one place: how a page address becomes its Twin's
address and back, and what media types a Twin may answer.

`md-suffix`: the page's path with `page_suffix` (when any) replaced by `.md`; it may answer plain
text that is not HTML (Fern serves some Twins so). `accept-header`: the page's address with
`accept=text/markdown` in the query. `raw`: the address as given is its own Twin and answers plain
text. `github-raw`: a `github.com/<owner>/<repo>/blob/<ref>/<path>` page's Twin is
`raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>`, which answers plain text. The path and
the raw query pieces are handled as given, so what goes on the wire keeps its encoding.
"""

from __future__ import annotations

from urllib.parse import unquote

from lorekeep.project import HostRule

MARKDOWN = "text/markdown"
PLAIN_TEXT = "text/plain"
ACCEPT_PIECE = "accept=text/markdown"
MD = ".md"
GITHUB = "github.com"
GITHUB_RAW = "raw.githubusercontent.com"


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


def to_raw(host: str, path: str) -> tuple[str, str] | None:
    """The raw file's host and path for a GitHub `blob` page's; `None` for any other address."""
    pieces = path.split("/")
    if host.lower() != GITHUB or len(pieces) < 6 or pieces[3] != "blob" or not all(pieces[1:6]):
        return None
    _, owner, repo, _, ref, *rest = pieces
    return GITHUB_RAW, "/".join(("", owner, repo, ref, *rest))


def to_blob(host: str, path: str) -> tuple[str, str] | None:
    """The GitHub `blob` page's host and path for a raw file's (the reverse of `to_raw`)."""
    pieces = path.split("/")
    if host.lower() != GITHUB_RAW or len(pieces) < 5 or not all(pieces[1:5]):
        return None
    _, owner, repo, ref, *rest = pieces
    return GITHUB, "/".join(("", owner, repo, "blob", ref, *rest))


def accepts(mediatype: str, body: bytes, rule: HostRule | None) -> bool:
    """Whether a Twin may answer `mediatype` with `body`: Markdown always; plain text from a raw
    file host, or under `md-suffix` when the body is not HTML."""
    if mediatype == MARKDOWN:
        return True
    if mediatype != PLAIN_TEXT or rule is None:
        return False
    if rule.twin in ("raw", "github-raw"):
        return True
    return rule.twin == "md-suffix" and not body.lstrip().startswith(b"<")
