"""URL normalisation: what is stored, looked up and compared — never what goes on the wire."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from lorekeep.project import HostRule

TRACKING = ("ref", "source", "fbclid", "gclid")
ACCEPT_MARKDOWN = ("accept", "text/markdown")
QUERY_SAFE = "/:@!$'()*,;~"


def normalise(url: str, rules: Sequence[HostRule]) -> str:
    """Lower-case scheme and host, decode query values, drop fragment and tracking parameters,
    sort the query, drop a trailing slash, collapse duplicate slashes; then reduce a Twin address
    to its page address under the host rule that matches."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    netloc = f"{host}:{parts.port}" if parts.port else host
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    query = [
        (unquote(key), unquote(value))
        for key, _, value in (piece.partition("=") for piece in parts.query.split("&") if piece)
        if not (key.startswith("utm_") or key in TRACKING)
    ]
    rule = rule_for(f"{host}{path}", rules)
    if rule is not None:
        path, query = _reduce_twin(path, query, rule)
    path = path.rstrip("/")
    query_text = "&".join(
        f"{quote(key, safe=QUERY_SAFE)}={quote(value, safe=QUERY_SAFE)}"
        if value
        else quote(key, safe=QUERY_SAFE)
        for key, value in sorted(query)
    )
    return urlunsplit((scheme, netloc, path, query_text, ""))


def rule_for(host_path: str, rules: Sequence[HostRule]) -> HostRule | None:
    """The rule with the longest `prefix` that `host/path` starts with, or `None`."""
    matching = [rule for rule in rules if host_path.startswith(rule.prefix)]
    return max(matching, key=lambda rule: len(rule.prefix), default=None)


def _reduce_twin(
    path: str, query: list[tuple[str, str]], rule: HostRule
) -> tuple[str, list[tuple[str, str]]]:
    if rule.twin == "md-suffix" and path.endswith(".md"):
        return path.removesuffix(".md") + (rule.page_suffix or ""), query
    if rule.twin == "accept-header":
        return path, [pair for pair in query if pair != ACCEPT_MARKDOWN]
    return path, query


@dataclass(frozen=True)
class Trust:
    """What the host table says of a URL; `warning` is set when no rule matched."""

    publisher: str
    authority: str
    rule: HostRule | None
    warning: str | None


def trust(url: str, rules: Sequence[HostRule]) -> Trust:
    """`publisher` and `authority` for `url` by longest prefix; an unknown host is `third-party`
    under its own name, with a warning for stderr so the owner extends the table."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    rule = rule_for(f"{host}{parts.path}", rules)
    if rule is not None:
        return Trust(rule.publisher, rule.authority, rule, None)
    warning = (
        f"warning: {host} is in neither host table; recorded as third-party — "
        f"add a [[hosts]] rule to lorekeep.toml before citing it"
    )
    return Trust(host, "third-party", None, warning)
