"""Twins of Fern, Mintlify and GitHub, and Rechecks through them (v1.1 ticket 01)."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from lorekeep.edges import Edges
from tests.support import (
    FIXTURES,
    FakeFetcher,
    FakeRunner,
    FakeTransport,
    age_version,
    edges_over,
    get,
    make_store,
    rows,
)
from tests.test_helpers import read_version

LANGCHAIN_SQL = "https://docs.langchain.com/oss/python/langchain/sql-agent"
LANGCHAIN_TOOLS = "https://docs.langchain.com/oss/python/langchain/tools"
GUARDRAILS = (
    "https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/"
    "jailbreak-protection"
)
DYNAMO = (
    "https://docs.nvidia.com/dynamo/latest/kubernetes/model-deployment/model-loading/"
    "fast-model-loading"
)
BLOB_YAML = (
    "https://github.com/NVIDIA-AI-Blueprints/deep-researcher-agent/blob/main/deploy/compose/"
    "docker-compose.yaml"
)
RAW_YAML = (
    "https://raw.githubusercontent.com/NVIDIA-AI-Blueprints/deep-researcher-agent/main/deploy/"
    "compose/docker-compose.yaml"
)
BLOB_README = "https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/README.md"
RAW_README = "https://raw.githubusercontent.com/NVIDIA-AI-Blueprints/rag/main/README.md"

FENCE = re.compile(rb"^ *```", re.MULTILINE)
PIPE_TABLE = re.compile(rb"^ *\|.*\|\s*\n *\|[ :|-]+\|", re.MULTILINE)


def the_version(store: Path) -> tuple[dict[str, Any], bytes]:
    [version] = store.glob("*.md")
    return read_version(version)


def test_a_mintlify_page_is_stored_as_its_twin_with_code(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("langchain-sql-agent.twin")

    result = get(store, edges, LANGCHAIN_SQL, tag="langchain")

    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""
    head, body = the_version(store)
    assert head["url"] == LANGCHAIN_SQL
    assert head["converter"] == "md-twin"
    assert head["publisher"] == "langchain"
    assert head["authority"] == "primary"
    assert head["title"] == "Build a SQL agent"
    assert FENCE.search(body)
    assert [str(request.url) for request in transport.requests] == [f"{LANGCHAIN_SQL}.md"]


def test_a_mintlify_page_keeps_its_pipe_tables(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("langchain-tools.twin")

    result = get(store, edges, LANGCHAIN_TOOLS, tag="langchain")

    assert result.exit_code == 0, result.stderr
    head, body = the_version(store)
    assert head["converter"] == "md-twin"
    assert FENCE.search(body)
    assert PIPE_TABLE.search(body)


def test_a_fern_guardrails_page_is_stored_as_its_twin_with_code_and_tables(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("guardrails-jailbreak-protection.twin")

    result = get(store, edges, GUARDRAILS, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    head, body = the_version(store)
    assert head["url"] == GUARDRAILS
    assert head["converter"] == "md-twin"
    assert head["publisher"] == "nvidia"
    assert head["title"] == "Jailbreak Protection"
    assert head["original"]["url"] == f"{GUARDRAILS}.md"
    assert FENCE.search(body)
    assert PIPE_TABLE.search(body)
    assert [str(request.url) for request in transport.requests] == [f"{GUARDRAILS}.md"]


def test_a_fern_twin_served_as_plain_text_is_accepted(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("dynamo-fast-model-loading.plain")

    result = get(store, edges, DYNAMO, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    head, body = the_version(store)
    assert head["url"] == DYNAMO
    assert head["converter"] == "md-twin"
    assert head["original"]["mediatype"] == "text/plain"
    assert FENCE.search(body)
    assert PIPE_TABLE.search(body)


def test_plain_text_that_is_html_is_not_a_twin(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    page = tmp_path / "page.html"
    page.write_bytes(b"<!doctype html><html><body><p>A page, not Markdown.</p></body></html>")
    transport = FakeTransport.from_fixtures("dynamo-fast-model-loading.plain")
    transport.fixtures = [replace(fixture, body=page) for fixture in transport.fixtures]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, DYNAMO, tag="nvidia")

    assert result.exit_code == 1
    assert f"no Twin: {DYNAMO}.md answered text/plain" in result.stderr
    assert not list(store.glob("*.md"))


def test_a_sphinx_section_of_docs_nvidia_com_asks_for_no_twin(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("nim-introduction.stub", "nim-overview.html")
    page = "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html"

    result = get(store, edges, page, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert not any(str(request.url).endswith(".md") for request in transport.requests)


def test_a_twin_404_under_a_fern_rule_falls_through_to_the_page(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("guardrails-no-twin.html")
    page = "https://docs.nvidia.com/nemo/guardrails/latest/about/release-notes"

    result = get(store, edges, page, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [f"{page}.md", page]
    head, body = the_version(store)
    assert head["url"] == page
    assert str(head["converter"]).startswith("trafilatura ")
    assert b"streaming output rails" in body


def test_a_github_blob_is_stored_as_the_raw_file_fenced_by_its_extension(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("github-docker-compose.raw")

    result = get(store, edges, BLOB_YAML, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert (
        result.stderr == f"lorekeep: note: {BLOB_YAML} is third-party under the github.com/ rule\n"
    )
    assert [str(request.url) for request in transport.requests] == [RAW_YAML]
    head, body = the_version(store)
    assert head["url"] == BLOB_YAML
    assert head["converter"] == "raw-twin"
    assert head["publisher"] == "github"
    assert head["authority"] == "third-party"
    assert head["title"] == "deploy/compose/docker-compose.yaml"
    assert head["original"]["url"] == RAW_YAML
    assert head["original"]["mediatype"] == "text/plain"
    assert not list(store.glob("*.orig.*"))
    received = (FIXTURES / "github-docker-compose.raw" / "body.yaml").read_bytes()
    assert body == b"# deploy/compose/docker-compose.yaml\n\n```yaml\n" + received + b"```\n"


def test_a_raw_file_holding_a_fence_gets_a_longer_one(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    script = tmp_path / "script.py"
    script.write_bytes(b'DOC = """\n```python\nprint(1)\n```\n"""')
    transport = FakeTransport.from_fixtures("github-docker-compose.raw")
    transport.fixtures = [
        replace(fixture, url=fixture.url.replace("docker-compose.yaml", "doc.py"), body=script)
        for fixture in transport.fixtures
    ]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, BLOB_YAML.replace("docker-compose.yaml", "doc.py"), tag="nvidia")

    assert result.exit_code == 0, result.stderr
    _, body = the_version(store)
    assert body.startswith(b"# deploy/compose/doc.py\n\n````py\n")
    assert body.endswith(b'"""\n````\n')


def test_a_github_blob_of_markdown_is_stored_as_is(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("github-readme.raw")

    result = get(store, edges, BLOB_README, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    head, body = the_version(store)
    received = (FIXTURES / "github-readme.raw" / "body.md").read_bytes()
    assert head["url"] == BLOB_README
    assert head["converter"] == "raw-twin"
    assert head["original"]["url"] == RAW_README
    assert body == received.lstrip(b"\n")
    assert head["title"]


def test_a_raw_address_given_directly_still_works_under_its_own_rule(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("github-readme.raw")

    result = get(store, edges, RAW_README, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [RAW_README]
    head, _ = the_version(store)
    assert head["url"] == RAW_README
    assert head["converter"] == "md-twin"


def changed(fixture: str, body: bytes, tmp_path: Path, **headers: str) -> Edges:
    """The fixture's address now answering `body` (and `headers`, when given)."""
    path = tmp_path / f"changed-{fixture}"
    path.write_bytes(body)
    transport = FakeTransport.from_fixtures(fixture)
    transport.fixtures = [
        replace(fixture_, body=path, headers={**fixture_.headers, **headers})
        for fixture_ in transport.fixtures
    ]
    return Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())


def stored_then_aged(store: Path, url: str, fixture: str) -> Path:
    edges, _ = edges_over(fixture)
    result = get(store, edges, url, tag="nvidia")
    assert result.exit_code == 0, result.stderr
    path = Path(result.stdout.splitlines()[-1])
    age_version(path, days=40)
    return path


def test_a_raw_twin_is_rechecked_through_the_github_rule(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old = stored_then_aged(store, BLOB_YAML, "github-docker-compose.raw")
    edges = changed("github-docker-compose.raw", b"services: {}\n", tmp_path)

    result = get(store, edges, BLOB_YAML, "--json", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    printed = json.loads(result.stdout)
    assert printed["outcome"] == "changed"
    new = Path(printed["path"])
    assert new != old
    head, body = read_version(new)
    assert head["url"] == BLOB_YAML
    assert head["converter"] == "raw-twin"
    assert body == b"# deploy/compose/docker-compose.yaml\n\n```yaml\nservices: {}\n```\n"
    assert [row["result"] for row in rows(store, "checks.csv")] == ["changed"]


def test_a_fern_twin_is_rechecked_through_the_twin_step(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    stored_then_aged(store, DYNAMO, "dynamo-fast-model-loading.twin")
    edges = changed(
        "dynamo-fast-model-loading.twin",
        b"# Fast Model Weight Loading\n\nRewritten.\n",
        tmp_path,
        **{"content-type": "text/plain; charset=utf-8"},
    )

    result = get(store, edges, DYNAMO, "--json", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    printed = json.loads(result.stdout)
    assert printed["outcome"] == "changed"
    assert printed["converter"] == "md-twin"


def test_a_github_page_that_is_not_a_blob_asks_for_no_raw_file(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over()
    repo = "https://github.com/NVIDIA-AI-Blueprints/rag/tree/main/docs"

    result = get(store, edges, repo, tag="nvidia")

    assert result.exit_code == 1
    assert [str(request.url) for request in transport.requests] == [repo]
    assert "is not a file the github-raw rule maps" in result.stderr
