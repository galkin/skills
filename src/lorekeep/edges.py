"""The three edges the command layer receives: HTTP, the browser, and external commands.

Production wires `httpx`'s own transport, Crawl4AI and `subprocess`; tests wire fakes.
"""

from __future__ import annotations

import asyncio
import importlib
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

BROWSER_EXTRA = "lorekeep[browser]"


@dataclass(frozen=True)
class RenderedPage:
    """What the browser saw: the rendered document, untouched, and the address it ended at."""

    html: str
    final_url: str


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
    def fetch(self, url: str) -> RenderedPage:
        """Render `url`; raise `FetcherNotInstalled` or `PageFetchError` when that is impossible."""
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
    """The browser in production. Crawl4AI is the optional extra, imported only when needed."""

    def fetch(self, url: str) -> RenderedPage:
        try:
            crawl4ai: Any = importlib.import_module("crawl4ai")
        except ImportError as error:
            raise FetcherNotInstalled() from error

        async def crawl() -> Any:
            async with crawl4ai.AsyncWebCrawler() as crawler:
                return await crawler.arun(url=url)

        result = asyncio.run(crawl())
        if not result.success:
            raise PageFetchError(f"the browser could not render {url}: {result.error_message}")
        return RenderedPage(html=result.html, final_url=result.redirected_url or result.url or url)

    @staticmethod
    def version() -> str:
        """Crawl4AI's version string (`crawl4ai.__version__` is a module that holds it)."""
        return importlib.import_module("crawl4ai.__version__").__version__


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
