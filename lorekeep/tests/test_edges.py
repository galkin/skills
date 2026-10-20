"""The production browser's readiness check, with Crawl4AI faked: no browser starts here."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from lorekeep import edges
from lorekeep.edges import BROWSER_INSTALL, Crawl4AIFetcher, chromium_install_command


def test_the_chromium_command_runs_the_playwright_of_the_interpreter_running_lorekeep() -> None:
    assert chromium_install_command() == f"{sys.executable} -m playwright install chromium"


def crawl4ai(started: list[dict[str, Any]], error: Exception | None = None) -> ModuleType:
    """A `crawl4ai` whose `AsyncWebCrawler` records the config it was started with, or raises
    `error` on start as Playwright does when Chromium is missing."""

    class BrowserConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class AsyncWebCrawler:
        def __init__(self, *, config: BrowserConfig, base_directory: str) -> None:
            self.config = config

        async def __aenter__(self) -> AsyncWebCrawler:
            if error is not None:
                raise error
            started.append(self.config.kwargs)
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    module = ModuleType("crawl4ai")
    module.BrowserConfig = BrowserConfig  # type: ignore[attr-defined]
    module.AsyncWebCrawler = AsyncWebCrawler  # type: ignore[attr-defined]
    return module


def imports(monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any]) -> None:
    """`importlib.import_module` answers from `modules`; any other name is not installed."""

    def fake(name: str) -> Any:
        if name in modules:
            return modules[name]
        raise ImportError(name)

    monkeypatch.setattr(edges.importlib, "import_module", fake)


def version_module() -> ModuleType:
    module = ModuleType("crawl4ai.__version__")
    module.__version__ = "0.9.5"  # type: ignore[attr-defined]
    return module


def test_without_crawl4ai_the_browser_is_not_ready_and_says_how_to_get_the_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports(monkeypatch, {})

    found = Crawl4AIFetcher().readiness()

    assert (found.ready, found.crawl4ai, found.fix) == (False, None, BROWSER_INSTALL)


def test_a_chromium_that_cannot_start_is_not_ready_with_the_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = RuntimeError("BrowserType.launch: Executable doesn't exist at /x/chrome\nmore")
    imports(
        monkeypatch,
        {"crawl4ai": crawl4ai([], missing), "crawl4ai.__version__": version_module()},
    )

    found = Crawl4AIFetcher().readiness()

    assert (found.ready, found.crawl4ai) == (False, "0.9.5")
    assert found.detail == (
        "Chromium cannot start: BrowserType.launch: Executable doesn't exist at /x/chrome"
    )
    assert found.fix == chromium_install_command()


def test_the_browser_starts_as_fetch_starts_it_and_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[dict[str, Any]] = []
    imports(
        monkeypatch,
        {"crawl4ai": crawl4ai(started), "crawl4ai.__version__": version_module()},
    )

    found = Crawl4AIFetcher().readiness()

    assert (found.ready, found.crawl4ai, found.fix) == (True, "0.9.5", None)
    assert started == [{"headless": True, "verbose": False}]
