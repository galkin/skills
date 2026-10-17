"""The browser waits for the page: it renders again, waiting longer, while the Markdown is thin,
and a shell after the last attempt stores nothing (v1.2 ticket 03)."""

from __future__ import annotations

import re
from pathlib import Path

import trafilatura

from lorekeep.edges import Edges
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    Result,
    get,
    make_store,
)
from tests.test_helpers import read_version

MODEL_CARD = "https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard"
SHELL = FIXTURES / "build-nemotron-modelcard.rendered-shell.html"
"""What Crawl4AI 0.9.5 rendered of the model card with its default wait: the menu and the
Next.js payload, an empty `<main>`."""
CARD = FIXTURES / "build-nemotron-modelcard.rendered-card.html"
"""The same document with the card's content in `<main>` (synthesised: see the README)."""
SHORT = FIXTURES / "browser-short-page.html"
NETWORKIDLE = {"wait_until": "networkidle"}
DELAYED = {"wait_until": "networkidle", "delay_before_return_html": 3.0}


def browser_rule(store: Path) -> None:
    """The first Store's rule for `build.nvidia.com/`: straight to the browser."""
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "build.nvidia.com/"\npublisher = "nvidia"\n'
        'authority = "primary"\nbrowser = true\n',
        encoding="utf-8",
    )


def get_card(
    tmp_path: Path, renders: list[Path], url: str = MODEL_CARD
) -> tuple[Path, FakeFetcher, Result]:
    store = make_store(tmp_path)
    browser_rule(store)
    fetcher = FakeFetcher({url: (renders, url)})
    edges = Edges(transport=FakeTransport([]), fetcher=fetcher, runner=FakeRunner())
    return store, fetcher, get(store, edges, url, tag="nvidia")


def test_a_shell_then_a_full_render_is_stored_after_two_calls_and_a_full_one_after_one(
    tmp_path: Path,
) -> None:
    store, fetcher, result = get_card(tmp_path / "two", [SHELL, CARD])

    assert result.exit_code == 0, result.stderr
    assert fetcher.configs == [NETWORKIDLE, DELAYED]
    assert "wait_for" not in fetcher.configs[0]
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert " via crawl4ai " in head["converter"]
    assert (
        version.with_name(f"{version.name.removesuffix('.md')}.orig.html").read_bytes()
        == CARD.read_bytes()
    )

    _, once, result = get_card(tmp_path / "one", [CARD])

    assert result.exit_code == 0, result.stderr
    assert once.configs == [NETWORKIDLE]


def test_a_shell_on_every_render_is_an_error_and_stores_nothing(tmp_path: Path) -> None:
    store, fetcher, result = get_card(tmp_path, [SHELL])

    assert result.exit_code == 1
    assert re.fullmatch(
        rf"lorekeep: error: nothing stored for {re.escape(MODEL_CARD)}: "
        r"the browser rendered a shell \(\d+ characters after 3 attempts\)\n",
        result.stderr,
    ), result.stderr
    assert list(store.glob("*.md")) == [] and list(store.glob("*.orig.*")) == []
    assert fetcher.calls == [MODEL_CARD] * 3
    first, second, third = fetcher.configs
    assert (first, second) == (NETWORKIDLE, DELAYED)
    assert third["wait_for"].startswith("js:")
    assert third["wait_for_timeout"] == 15000
    assert third["delay_before_return_html"] == 3.0


def test_the_model_card_with_its_content_loaded_is_stored_with_its_description(
    tmp_path: Path,
) -> None:
    store, fetcher, result = get_card(tmp_path, [CARD])

    assert result.exit_code == 0, result.stderr
    assert fetcher.calls == [MODEL_CARD]
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["converter"] == f"trafilatura {trafilatura.__version__} via crawl4ai 0.9.5"
    assert b"Transformer\xe2\x80\x91Mamba design" in body
    assert b"unified model for both reasoning and non-reasoning tasks" in body
    assert b"Skip to main content" not in body


def test_a_page_short_for_real_is_stored_on_the_first_render(tmp_path: Path) -> None:
    page = "https://build.nvidia.com/nvidia/release-notes"
    store, fetcher, result = get_card(tmp_path, [SHORT], url=page)

    assert result.exit_code == 0, result.stderr
    assert fetcher.configs == [NETWORKIDLE]
    [version] = store.glob("*.md")
    _, body = read_version(version)
    assert b"fixes the login timeout" in body
