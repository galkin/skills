"""URL normalisation: what is stored, looked up and compared — never what goes on the wire."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from lorekeep import twins
from lorekeep.project import HostRule

TRACKING = ("ref", "source", "fbclid", "gclid")
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
    pieces = [piece for piece in parts.query.split("&") if piece]
    rule = rule_for(host_path(url), rules)
    if rule is not None:
        path, pieces = twins.to_page(path, pieces, rule)
    query = [
        (unquote(key), unquote(value))
        for key, _, value in (piece.partition("=") for piece in pieces)
        if not (key.startswith("utm_") or key in TRACKING)
    ]
    path = path.rstrip("/")
    query_text = "&".join(
        f"{quote(key, safe=QUERY_SAFE)}={quote(value, safe=QUERY_SAFE)}"
        if value
        else quote(key, safe=QUERY_SAFE)
        for key, value in sorted(query)
    )
    return urlunsplit((scheme, netloc, path, query_text, ""))


def other_canonical(canonical: str | None, url: str, rules: Sequence[HostRule]) -> str | None:
    """The page's declared canonical address, normalised, when it names another address than
    `url` (itself normalised); `None` when there is none or it is `url`. It is recorded, never
    used as `url`: publishers declare the wrong page (ADR 0003)."""
    if not canonical:
        return None
    found = normalise(canonical, rules)
    return found if found != url else None


def went_home(asked: str, final: str) -> bool:
    """Whether a request for a page below a site's root ended at a site's root page: a publisher
    that dropped a page often redirects to its home page instead of answering `404`. A root's own
    `index.*` is the root, so `/index.html` landing on `/` is the same page. A locale root
    (`/en/`) is not recognised."""
    landed = urlsplit(final)
    return not _root(urlsplit(asked).path) and _root(landed.path) and not landed.query


def home_reason(asked: str, final: str) -> str:
    """The reason a page that `went_home` is gone, for `get`'s error and `recheck`'s row."""
    return f"{asked} is gone: it ended at the site's home page {final}"


def _root(path: str) -> bool:
    """Whether `path` is a site's root: empty, `/`, or the root's `index.*` page."""
    rest = path.strip("/")
    return rest == "" or ("/" not in rest and rest.startswith("index."))


def host_path(url: str) -> str:
    """What a rule's `prefix` is matched against: the url's host, lower-cased, and its path,
    duplicate slashes collapsed, with `/` for a root's empty one, so `https://agents.md` is under
    `agents.md/`."""
    parts = urlsplit(url.strip())
    return f"{(parts.hostname or '').lower()}{re.sub(r'/{2,}', '/', parts.path) or '/'}"


def rule_for(host_path: str, rules: Sequence[HostRule]) -> HostRule | None:
    """The rule with the longest `prefix` that `host/path` starts with, or `None`."""
    matching = [rule for rule in rules if host_path.startswith(rule.prefix)]
    return max(matching, key=lambda rule: len(rule.prefix), default=None)


def under(url: str, prefix: str) -> bool:
    """Whether a stored `url` is under a `--prefix` URL: it starts with it, or it is the root
    `prefix` names, which `normalise` stores without its slash (`https://agents.md`)."""
    return url.startswith(prefix) or url == bare_root(prefix)


def bare_root(prefix: str) -> str | None:
    """`prefix` without its slash when it is a site's root (`https://agents.md/`), else `None`."""
    parts = urlsplit(prefix)
    if parts.scheme and parts.netloc and parts.path == "/" and not parts.query:
        return prefix[:-1]
    return None


# A user's contribution on GitHub — an issue, a discussion, a pull request — under its repository
# or its organisation: third-party whoever the repository's rule makes primary, as Wikipedia's
# WP:USERG rules user-generated content out as a source.
CONTRIBUTION = re.compile(
    r"github\.com/(?:orgs/(?P<org>[^/]+)|[^/]+/[^/]+)/"
    r"(?P<kind>issues|discussions|pulls?)(?:/|$)"
)


def unknown_host(url: str, publisher: str) -> str | None:
    """The host of `url` when `publisher` is the fallback `trust` gives an unknown host (its own
    host name), else `None`: what `status` lists under unknown hosts."""
    host = (urlsplit(url).hostname or "").lower()
    return host if host and publisher == host else None


@dataclass(frozen=True)
class Trust:
    """What the host table says of a URL; `warning` is set when no rule matched, and `note` when
    the verdict is `third-party` from no rule or from a catch-all rule."""

    publisher: str
    authority: str
    rule: HostRule | None
    warning: str | None
    note: str | None = None


def trust(url: str, rules: Sequence[HostRule]) -> Trust:
    """`publisher` and `authority` for `url` by longest prefix; an unknown host is `third-party`
    under its own name, with a warning for stderr that a Run passes on to the owner. A
    `third-party` verdict no rule made for this page's publisher — no rule, or a catch-all — is
    named in a note, so a Run sees it without reading `authority`."""
    host = (urlsplit(url).hostname or "").lower()
    rule = rule_for(host_path(url), rules)
    if rule is not None:
        contribution = _contribution(url, rule, rules)
        if contribution is not None:
            return contribution
        note = None
        if rule.authority == "third-party" and catch_all(rule):
            note = f"lorekeep: note: {url} is third-party under the {rule.prefix} rule"
        return Trust(rule.publisher, rule.authority, rule, None, note)
    warning = (
        f"lorekeep: warning: {host} is in no host table; stored as third-party — "
        f"tell the owner, who may add a [[hosts]] rule"
    )
    return Trust(
        host, "third-party", None, warning, f"lorekeep: note: {url} is third-party under no rule"
    )


def _contribution(url: str, rule: HostRule, rules: Sequence[HostRule]) -> Trust | None:
    """The trust of a GitHub contribution `rule` would make primary: `third-party` under the
    publisher of its repository's rule (of the organisation's, for `orgs/<org>/discussions`),
    with a note. `None` when `url` is no contribution, when `rule` already says so, or when
    `rule` names the contribution's own prefix or a longer one."""
    found = CONTRIBUTION.match(host_path(url))
    if found is None or len(rule.prefix) >= found.end("kind"):
        return None
    repository = rule
    if found["org"] is not None and catch_all(rule):
        repository = rule_for(f"github.com/{found['org']}/", rules) or rule
    if repository is rule and rule.authority == "third-party":
        return None
    kind = {"issues": "issue", "discussions": "discussion"}.get(found["kind"], "pull request")
    note = f"lorekeep: note: {url} is third-party: a GitHub {kind} is a user's contribution"
    return Trust(repository.publisher, "third-party", rule, None, note)


def effective_trust(head: Mapping[str, object], rules: Sequence[HostRule]) -> tuple[str, str]:
    """`publisher` and `authority` of a Version as the current host rules judge its `url`; the
    frontmatter's own (captured at fetch, never rewritten) for an owner's Source (`lorekeep add`),
    which no host rule describes."""
    if head.get("origin") == "owner":
        return str(head["publisher"]), str(head["authority"])
    found = trust(str(head["url"]), rules)
    return found.publisher, found.authority


def catch_all(rule: HostRule) -> bool:
    """Whether `rule` covers a whole host (`github.com/`), whoever wrote the pages under it."""
    return "/" not in rule.prefix.rstrip("/")
