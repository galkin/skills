"""A Twin under `page_suffix` keeps the address the page was asked at (v1.2 ticket 07)."""

from __future__ import annotations

from pathlib import Path

from tests.support import age_version, edges_over, get, lorekeep, make_store, rows
from tests.test_helpers import read_version

BUILD_RULE = (
    '[[hosts]]\nprefix = "build.nvidia.com/"\npublisher = "nvidia"\nauthority = "primary"\n'
    'twin = "md-suffix"\npage_suffix = "/modelcard"\n'
)
SAFETY = "https://build.nvidia.com/nvidia/safety-for-agentic-ai"
NANO = "https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2"
MOVED = "https://build.nvidia.com/nvidia/agentic-ai-safety"


def build_store(tmp_path: Path) -> Path:
    """A Store whose `lorekeep.toml` holds the first Store's rule for `build.nvidia.com/`."""
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(BUILD_RULE, encoding="utf-8")
    return store


def test_a_page_asked_without_page_suffix_is_stored_under_that_address(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    edges, transport = edges_over("build-safety-for-agentic-ai.twin")

    result = get(store, edges, SAFETY, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [f"{SAFETY}.md"]
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["url"] == SAFETY
    assert head["original"]["url"] == f"{SAFETY}.md"
    assert head["original"]["stored"] == "false"
    assert head["converter"] == "md-twin"
    assert head["title"] == "Safety for Agentic AI"
    assert body.startswith(b"As large language models (LLMs)")
    assert version.name.startswith("build.nvidia.com--nvidia-safety-for-agentic-ai--")
    assert not (store / "aliases.csv").exists()


def test_a_page_asked_with_page_suffix_keeps_it(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    edges, transport = edges_over("build-nemotron-nano.twin")

    result = get(store, edges, f"{NANO}/modelcard", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [f"{NANO}.md"]
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    assert head["url"] == f"{NANO}/modelcard"
    assert head["original"]["url"] == f"{NANO}.md"
    assert head["converter"] == "md-twin"
    assert not (store / "aliases.csv").exists()


def test_a_twin_reached_through_a_redirect_is_stored_under_the_page_it_redirected_to(
    tmp_path: Path,
) -> None:
    fixtures = ("build-safety-for-agentic-ai.301", "build-safety-for-agentic-ai.twin")
    bare = build_store(tmp_path / "bare")
    suffixed = build_store(tmp_path / "suffixed")

    asked_bare = get(bare, edges_over(*fixtures)[0], MOVED, tag="nvidia")
    asked_suffixed = get(suffixed, edges_over(*fixtures)[0], f"{MOVED}/modelcard", tag="nvidia")

    assert asked_bare.exit_code == 0, asked_bare.stderr
    assert asked_suffixed.exit_code == 0, asked_suffixed.stderr
    for store, suffix in ((bare, ""), (suffixed, "/modelcard")):
        [version] = store.glob("*.md")
        head, _ = read_version(version)
        assert head["url"] == f"{SAFETY}{suffix}"
        assert head["original"]["url"] == f"{SAFETY}.md"
        assert [(row["alias"], row["url"]) for row in rows(store, "aliases.csv")] == [
            (f"{MOVED}{suffix}", f"{SAFETY}{suffix}")
        ]


def test_recheck_asks_the_twin_and_records_the_check_under_the_page(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    stored = get(store, edges_over("build-safety-for-agentic-ai.twin")[0], SAFETY, tag="nvidia")
    assert stored.exit_code == 0, stored.stderr
    path = Path(stored.stdout.splitlines()[-1])
    age_version(path, days=40)
    edges, transport = edges_over("build-safety-for-agentic-ai.twin")

    result = lorekeep(store, edges, "recheck")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [f"{SAFETY}.md"]
    assert f"unchanged {SAFETY}" in result.stdout.splitlines()
    head, _ = read_version(path)
    assert [(row["url"], row["result"], row["sha256"]) for row in rows(store, "checks.csv")] == [
        (SAFETY, "unchanged", head["sha256"])
    ]
    assert list(store.glob("*.md")) == [path]
