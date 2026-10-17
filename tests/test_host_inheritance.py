"""A host rule that names no `twin` inherits it from the longest shorter prefix (v1.2 ticket 06)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from lorekeep.edges import Edges
from tests.support import FakeFetcher, FakeRunner, FakeTransport, edges_over, get, make_store
from tests.test_helpers import read_version
from tests.test_project import host_rules, status

NVIDIA_ORG = """\
[[hosts]]
prefix = "github.com/NVIDIA/"
publisher = "nvidia"
authority = "official"
"""
# The shape of the four GitHub rules of the first Store's `lorekeep.toml`: `twin` named.
BLUEPRINTS_ORG = """\
[[hosts]]
prefix = "github.com/NVIDIA-AI-Blueprints/"
publisher = "nvidia"
authority = "primary"
twin = "github-raw"
"""
LANGCHAIN_WITHOUT_TWIN = """\
[[hosts]]
prefix = "docs.langchain.com/"
publisher = "langchain"
authority = "official"
"""
EXAMPLE_TREE = """\
[[hosts]]
prefix = "example.test/"
publisher = "example"
authority = "primary"
twin = "md-suffix"
page_suffix = ".html"
browser = true
cut = ["nav"]

[[hosts]]
prefix = "example.test/app/"
publisher = "example"
authority = "official"
"""

BLOB_README = "https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/README.md"
RAW_README = "https://raw.githubusercontent.com/NVIDIA-AI-Blueprints/rag/main/README.md"
NVIDIA_BLOB = "https://github.com/NVIDIA/TensorRT-LLM/blob/main/README.md"
NVIDIA_RAW = "https://raw.githubusercontent.com/NVIDIA/TensorRT-LLM/main/README.md"
LANGCHAIN_SQL = "https://docs.langchain.com/oss/python/langchain/sql-agent"


def the_version(store: Path) -> dict[str, Any]:
    [version] = store.glob("*.md")
    head, _ = read_version(version)
    return head


def test_an_org_rule_without_twin_stores_its_blob_pages_through_the_github_twin(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(NVIDIA_ORG)
    transport = FakeTransport.from_fixtures("github-readme.raw")
    transport.fixtures = [replace(fixture, url=NVIDIA_RAW) for fixture in transport.fixtures]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, NVIDIA_BLOB, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [NVIDIA_RAW]
    head = the_version(store)
    assert head["url"] == NVIDIA_BLOB
    assert head["converter"] == "raw-twin"
    assert head["publisher"] == "nvidia"
    assert head["authority"] == "official"
    assert head["original"]["url"] == NVIDIA_RAW


def test_a_rule_replacing_a_default_inherits_only_from_a_shorter_prefix(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(LANGCHAIN_WITHOUT_TWIN)
    edges, transport = edges_over("langchain-sql-agent.html")

    result = get(store, edges, LANGCHAIN_SQL, tag="langchain")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [LANGCHAIN_SQL]
    head = the_version(store)
    assert head["converter"] != "md-twin"
    assert head["authority"] == "official"


def test_status_marks_inherited_values_and_inherits_neither_browser_nor_cut(
    tmp_path: Path,
) -> None:
    (tmp_path / "lorekeep.toml").write_text(
        "\n".join([NVIDIA_ORG, BLUEPRINTS_ORG, LANGCHAIN_WITHOUT_TWIN, EXAMPLE_TREE])
    )

    rows = {row[0]: row for row in host_rules(status(tmp_path))}

    own = "(lorekeep.toml)"
    marked = "(inherited)"
    assert rows["github.com/NVIDIA/"] == [
        "github.com/NVIDIA/", "nvidia", "official", "twin=github-raw", marked, own
    ]  # fmt: skip
    assert rows["github.com/NVIDIA-AI-Blueprints/"] == [
        "github.com/NVIDIA-AI-Blueprints/", "nvidia", "primary", "twin=github-raw", own
    ]  # fmt: skip
    assert rows["docs.langchain.com/"] == ["docs.langchain.com/", "langchain", "official", own]
    assert rows["example.test/app/"] == [
        "example.test/app/", "example", "official",
        "twin=md-suffix", marked, "page_suffix=.html", marked, own,
    ]  # fmt: skip


def test_an_org_rule_naming_its_twin_works_unchanged(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(BLUEPRINTS_ORG)
    edges, transport = edges_over("github-readme.raw")

    result = get(store, edges, BLOB_README, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [RAW_README]
    head = the_version(store)
    assert head["converter"] == "raw-twin"
    assert head["publisher"] == "nvidia"
    assert head["authority"] == "primary"
