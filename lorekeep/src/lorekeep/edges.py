"""The three edges the command layer receives: HTTP, the browser, and external commands.

Production wires `httpx`'s own transport, Crawl4AI and `subprocess`; tests wire fakes.
"""

from __future__ import annotations

import asyncio
import importlib
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from importlib import metadata
from typing import Any, Protocol

import httpx

BROWSER_EXTRA = "lorekeep[browser]"


@dataclass(frozen=True)
class RenderedPage:
    """What the browser saw: the rendered document, untouched, and the address it ended at."""

    html: str
    final_url: str


@dataclass(frozen=True)
class Wait:
    """How long the browser waits for a page before it returns the document: the `CrawlerRunConfig`
    parameters of these names (Crawl4AI's Page Navigation & Timing), Crawl4AI's default where
    `None`. `wait_for` is a `js:` condition, given up after `wait_for_timeout` milliseconds."""

    wait_until: str = "domcontentloaded"
    delay_before_return_html: float | None = None
    wait_for: str | None = None
    wait_for_timeout: int | None = None

    def config(self) -> dict[str, Any]:
        """The keywords `CrawlerRunConfig` receives: the parameters that are set."""
        return {name: value for name, value in asdict(self).items() if value is not None}


class FetcherNotInstalled(Exception):
    """The browser step was needed and Crawl4AI is not installed."""

    def __init__(self) -> None:
        super().__init__(
            f"this page needs a browser and Crawl4AI is not installed: "
            f"install the extra {BROWSER_EXTRA} (uv sync --extra browser)"
        )


class PageFetchError(Exception):
    """The browser could not render the page."""


class PageFetcher(Protocol):
    def fetch(self, url: str, wait: Wait) -> RenderedPage:
        """Render `url`, waiting as `wait` says; raise `FetcherNotInstalled` or `PageFetchError`
        when that is impossible."""
        ...

    def version(self) -> str:
        """The browser tool's version string, for the `converter` field."""
        ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, argv: Sequence[str]) -> CommandResult:
        """Run an external command (`gcloud`) to completion and return what it printed."""
        ...


class Crawl4AIFetcher:
    """The browser in production. Crawl4AI is the optional extra, imported only when needed.

    Crawl4AI keeps its state under a base directory (`~/.crawl4ai` by default) and logs through
    `rich` to stderr; a throw-away directory per call and `verbose=False` keep the machine and
    stderr as they were. A missing Chromium is reported with the command for the owner to run,
    never installed.
    """

    def fetch(self, url: str, wait: Wait) -> RenderedPage:
        try:
            crawl4ai: Any = importlib.import_module("crawl4ai")
        except ImportError as error:
            raise FetcherNotInstalled() from error

        async def crawl(workdir: str) -> Any:
            browser = crawl4ai.BrowserConfig(headless=True, verbose=False)
            run = crawl4ai.CrawlerRunConfig(
                cache_mode=crawl4ai.CacheMode.BYPASS, verbose=False, **wait.config()
            )
            async with crawl4ai.AsyncWebCrawler(config=browser, base_directory=workdir) as crawler:
                return await crawler.arun(url=url, config=run)

        with tempfile.TemporaryDirectory(prefix="lorekeep-crawl4ai-") as workdir:
            result = asyncio.run(crawl(workdir))
        if not result.success:
            message = str(result.error_message or "")
            if "Executable doesn't exist" in message:
                raise PageFetchError(
                    f"the browser could not render {url}: Chromium is not installed for "
                    f"Crawl4AI; to install it, run: uv run playwright install chromium"
                )
            raise PageFetchError(f"the browser could not render {url}: {message}")
        return RenderedPage(html=result.html, final_url=result.redirected_url or result.url or url)

    def version(self) -> str:
        """Crawl4AI's version string (`crawl4ai.__version__` is a module that holds it)."""
        try:
            return importlib.import_module("crawl4ai.__version__").__version__
        except ImportError:
            try:
                return metadata.version("crawl4ai")
            except metadata.PackageNotFoundError as error:
                raise FetcherNotInstalled() from error


class SubprocessRunner:
    """External commands in production."""

    def run(self, argv: Sequence[str]) -> CommandResult:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
        return CommandResult(returncode=done.returncode, stdout=done.stdout, stderr=done.stderr)


@dataclass(frozen=True)
class Edges:
    transport: httpx.BaseTransport
    fetcher: PageFetcher
    runner: CommandRunner

    @classmethod
    def production(cls) -> Edges:
        return cls(
            transport=httpx.HTTPTransport(),
            fetcher=Crawl4AIFetcher(),
            runner=SubprocessRunner(),
        )
