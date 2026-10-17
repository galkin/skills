"""The seam's edge for tests: run a command in-process with fakes, and build Store files.

Every fake is built from paths and plain values, so a child process can construct its own. The
spec's two Store helpers (`write_version`, `age_version`) live here with the harness every test
file shares: `make_store`, `edges_over`, `lorekeep`, `get` and `rows`.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from lorekeep import frontmatter
from lorekeep.cli import run
from lorekeep.edges import (
    CommandResult,
    Edges,
    FetcherNotInstalled,
    PageFetchError,
    RenderedPage,
    Wait,
)
from lorekeep.store import version_name

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_folders() -> list[Path]:
    """Every recorded response under `tests/fixtures/`."""
    return sorted(path.parent for path in FIXTURES.glob("*/response.json"))


def comparable_url(url: str) -> str:
    """A URL as the fake transport compares it: host lower-cased, path and query percent-decoded.

    `httpx.URL` equality is not used because it keeps `%2F` and `/` apart.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    netloc = f"{host}:{parts.port}" if parts.port else host
    query = f"?{unquote(parts.query)}" if parts.query else ""
    return f"{parts.scheme.lower()}://{netloc}{unquote(parts.path)}{query}"


@dataclass(frozen=True)
class Fixture:
    folder: Path
    url: str
    status: int
    headers: dict[str, str]
    body: Path | None
    match_headers: dict[str, str]
    error: str | None

    @classmethod
    def load(cls, folder: Path) -> Fixture:
        data: dict[str, Any] = json.loads((folder / "response.json").read_text())
        body = data.get("body")
        return cls(
            folder=folder,
            url=data["url"],
            status=data.get("status", 0),
            headers=dict(data.get("headers", {})),
            body=folder / body if body else None,
            match_headers={k.lower(): v for k, v in data.get("match_headers", {}).items()},
            error=data.get("error"),
        )

    def matches_headers(self, request: httpx.Request) -> bool:
        return all(request.headers.get(k) == v for k, v in self.match_headers.items())


class FakeTransport(httpx.BaseTransport):
    """Serves recorded responses; any other URL is a `404` and a recorded miss."""

    def __init__(self, folders: Sequence[Path | str]) -> None:
        self.fixtures = [Fixture.load(Path(folder)) for folder in folders]
        self.requests: list[httpx.Request] = []
        self.misses: list[str] = []

    @classmethod
    def from_fixtures(cls, *names: str) -> FakeTransport:
        """A transport over the named fixture folders, or over all of them when none is named."""
        return cls([FIXTURES / name for name in names] if names else fixture_folders())

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        wanted = comparable_url(str(request.url))
        candidates = [
            fixture
            for fixture in self.fixtures
            if comparable_url(fixture.url) == wanted and fixture.matches_headers(request)
        ]
        if not candidates:
            self.misses.append(str(request.url))
            return httpx.Response(404, request=request)
        fixture = max(candidates, key=lambda f: len(f.match_headers))
        if fixture.error:
            error_class: type[httpx.TransportError] = getattr(httpx, fixture.error)
            raise error_class(f"{fixture.error} (fixture {fixture.folder.name})", request=request)
        content = fixture.body.read_bytes() if fixture.body else b""
        return httpx.Response(
            fixture.status, headers=fixture.headers, content=content, request=request
        )


class FakeFetcher:
    """The browser: renders the pages it was given (`url → (html file, final url)`). A page given
    as a sequence of files renders as the next one on each call, the last one ever after; each
    call's `CrawlerRunConfig` keywords are recorded in `configs`."""

    def __init__(
        self,
        pages: Mapping[str, tuple[Path | str | Sequence[Path | str], str]] | None = None,
        *,
        installed: bool = True,
        version: str = "0.9.5",
    ) -> None:
        self.pages = {
            url: (
                [Path(paths)] if isinstance(paths, (Path, str)) else [Path(p) for p in paths],
                final,
            )
            for url, (paths, final) in (pages or {}).items()
        }
        self.installed = installed
        self._version = version
        self.calls: list[str] = []
        self.configs: list[dict[str, Any]] = []

    def version(self) -> str:
        if not self.installed:
            raise FetcherNotInstalled()
        return self._version

    def fetch(self, url: str, wait: Wait) -> RenderedPage:
        if not self.installed:
            raise FetcherNotInstalled()
        rendered = sum(1 for call in self.calls if call == url)
        self.calls.append(url)
        self.configs.append(wait.config())
        if url not in self.pages:
            raise PageFetchError(f"the fake browser has no page for {url}")
        paths, final_url = self.pages[url]
        path = paths[min(rendered, len(paths) - 1)]
        return RenderedPage(html=path.read_text(encoding="utf-8"), final_url=final_url)


class FakeRunner:
    """External commands: records each `argv` and answers with the next canned result."""

    def __init__(self, results: Sequence[tuple[int, str, str]] = ()) -> None:
        self.results = [CommandResult(*result) for result in results]
        self.calls: list[list[str]] = []

    def run(self, argv: Sequence[str]) -> CommandResult:
        self.calls.append(list(argv))
        return self.results.pop(0) if self.results else CommandResult(0, "", "")


def fake_edges() -> Edges:
    """All fixtures over HTTP, a browser with no pages, a runner that succeeds."""
    return Edges(
        transport=FakeTransport.from_fixtures(), fetcher=FakeFetcher(), runner=FakeRunner()
    )


@dataclass(frozen=True)
class Result:
    exit_code: int
    stdout: str
    stderr: str


def run_cli(
    argv: Sequence[str], *, env: Mapping[str, str] | None = None, edges: Edges | None = None
) -> Result:
    """Run one lorekeep command in-process with fake edges and capture what it printed."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run(list(argv), env=dict(env or {}), edges=edges or fake_edges())
    return Result(code, out.getvalue(), err.getvalue())


def make_store(tmp_path: Path) -> Path:
    """An empty Store under `tmp_path`, folders above it made on the way."""
    path = tmp_path / "store"
    path.mkdir(parents=True)
    return path


def edges_over(*fixtures: str) -> tuple[Edges, FakeTransport]:
    """Fakes whose transport serves the named fixture folders (every folder when none is named),
    and that transport, for its `requests` and `misses`."""
    transport = FakeTransport.from_fixtures(*fixtures)
    return Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner()), transport


def lorekeep(store: Path, edges: Edges, *argv: str, tag: str | None = None) -> Result:
    """Run one command against `store` with `edges`, under the Run's Tag when one is given."""
    env = {"LOREKEEP_STORE": str(store)}
    if tag is not None:
        env["LOREKEEP_TAG"] = tag
    return run_cli(list(argv), env=env, edges=edges)


def get(store: Path, edges: Edges, *argv: str, tag: str = "anthropic") -> Result:
    """`get` under a Tag: the command most tests drive."""
    return lorekeep(store, edges, "get", *argv, tag=tag)


def rows(store: Path, name: str) -> list[dict[str, str]]:
    """The rows of one of the Store's growing CSV files, `[]` when it was never written."""
    path = store / name
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def status_in_child(store: str) -> Result:
    """Run `status` in whatever process calls this, with fakes built there from paths."""
    return run_cli(["status", "--store", store])


def write_version(store: Path, fixture: Path | str, *, fetched_at: str, **fields: Any) -> Path:
    """Write a Version straight from a fixture folder, converting nothing.

    The body is the response body verbatim, whatever its type; `original.url` and
    `original.sha256` are those of the response; `fields` override any frontmatter field.
    """
    recorded = Fixture.load(Path(fixture))
    body = recorded.body.read_bytes() if recorded.body else b""
    digest = hashlib.sha256(body).hexdigest()
    url = fields.pop("url", recorded.url)
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    head: dict[str, Any] = {
        "url": url,
        "fetched_at": fetched_at,
        "sha256": digest,
        "publisher": host,
        "authority": "third-party",
        "converter": "fixture",
        "etag": recorded.headers.get("etag"),
        "last_modified": recorded.headers.get("last-modified"),
        "original": {
            "url": recorded.url,
            "mediatype": recorded.headers.get("content-type", "").split(";")[0].strip(),
            "sha256": digest,
            "stored": False,
        },
    }
    head.update(fields)
    path = store / version_name(url, digest)
    path.write_bytes(frontmatter.render(head) + body)
    return path


def age_version(path: Path, *, days: float) -> None:
    """Make a stored Version `days` old by rewriting `fetched_at` in its frontmatter.

    The file name stays valid: `sha256` covers only the body.
    """
    head, body = frontmatter.parse(path.read_bytes())
    head["fetched_at"] = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_bytes(frontmatter.render(head) + body)
