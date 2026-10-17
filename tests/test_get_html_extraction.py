"""Static HTML keeps code, tables, lists, headings and titles, and says what it lost (v1.1 #03).

The fixtures are pages of the first migration, cut to the part that showed the defect; each test
counts what the page holds and what the Markdown kept.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import lxml.html
import pytest
import trafilatura

from lorekeep.edges import Edges
from tests.support import FIXTURES, FakeFetcher, FakeRunner, FakeTransport, get, make_store
from tests.test_helpers import read_version

JAILBREAK = (
    "https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/"
    "jailbreak-protection"
)
SELF_CHECK = (
    "https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/self-check"
)
MIDDLEWARE = "https://docs.langchain.com/oss/python/langchain/middleware/built-in"
SQL_AGENT = "https://docs.langchain.com/oss/python/langchain/sql-agent"
DEPLOYMENT = "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"
SIGNALS = "https://opentelemetry.io/docs/concepts/signals/"
KVCACHE = "https://nvidia.github.io/TensorRT-LLM/features/kvcache.html"
TOOL_CALLING = (
    "https://docs.nvidia.com/nim/large-language-models/latest/advanced-use-cases/"
    "tool-calling-and-mcp.html"
)
MODEL_CARD = "https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard"

PAGES = {
    "guardrails-jailbreak-protection.html": JAILBREAK,
    "guardrails-self-check.html": SELF_CHECK,
    "langchain-middleware-built-in.html": MIDDLEWARE,
    "langchain-sql-agent.html": SQL_AGENT,
    "kubernetes-deployment.html": DEPLOYMENT,
    "opentelemetry-signals.html": SIGNALS,
    "trtllm-kvcache.html": KVCACHE,
    "nim-tool-calling.html": TOOL_CALLING,
}


def page(fixture: str) -> lxml.html.HtmlElement:
    return lxml.html.parse(str(FIXTURES / fixture / "body.html")).getroot()


def code_blocks(fixture: str) -> int:
    return len(page(fixture).xpath("//body//pre[not(ancestor::pre)]"))


def tables(fixture: str) -> int:
    return len(page(fixture).xpath("//body//table[not(ancestor::table)]"))


def fences(body: str) -> list[str]:
    """The text of each fenced block of a Markdown body."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def pipe_tables(body: str) -> int:
    return len(re.findall(r"(?m)^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", body))


def headings(body: str) -> list[str]:
    outside = re.sub(r"(?ms)^```.*?^```", "", body)
    return re.findall(r"(?m)^#{1,6} .*$", outside)


def fetch(tmp_path: Path, fixture: str, tag: str = "nvidia") -> tuple[Any, dict[str, Any], str]:
    """`get` of a fixture's page: the command's result, the Version's frontmatter and body."""
    store = make_store(tmp_path)
    transport = FakeTransport.from_fixtures(fixture)
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())
    result = get(store, edges, PAGES[fixture], tag=tag)
    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    return result, head, body.decode("utf-8")


def test_a_fern_page_keeps_every_code_block_and_table(tmp_path: Path) -> None:
    fixture = "guardrails-jailbreak-protection.html"
    assert (code_blocks(fixture), tables(fixture)) == (3, 4)

    result, head, body = fetch(tmp_path, fixture)

    assert len(fences(body)) == 3
    assert pipe_tables(body) == 4
    assert "length_per_perplexity_threshold: 89.79" in "\n".join(fences(body))
    assert "| `length_per_perplexity_threshold` | Must be greater than 0 |" in body
    assert head["title"] == "Jailbreak Protection | NVIDIA NeMo Guardrails Library Developer Guide"
    assert result.stderr == ""


def test_a_fern_page_with_sixteen_code_blocks_has_sixteen_fences(tmp_path: Path) -> None:
    fixture = "guardrails-self-check.html"
    assert code_blocks(fixture) == 16

    _, _, body = fetch(tmp_path, fixture)

    assert len(fences(body)) == 16
    # one line per line of the highlighter, indentation kept
    assert "rails:\n  input:\n    flows:\n      - self check input" in fences(body)


def test_a_mintlify_page_keeps_its_parameter_names_and_fences_its_code(tmp_path: Path) -> None:
    fixture = "langchain-middleware-built-in.html"
    names = [
        " ".join(name.text_content().split())
        for name in page(fixture).xpath("//*[@data-component-part='field-name']")
    ]
    assert len(names) == 29

    result, _, body = fetch(tmp_path, fixture, tag="langchain")

    assert [name for name in names if f"`{name}`" not in body] == []
    # one block sits in a callout Trafilatura drops whole; the warning names it
    assert len(fences(body)) == code_blocks(fixture) - 1 == 9
    assert (
        f"lorekeep: warning: {MIDDLEWARE}: 1 code blocks / 0 tables of the page are missing "
        "from the Markdown"
    ) in result.stderr.splitlines()


def test_kubernetes_keeps_its_title_headings_and_the_list_of_use_cases(tmp_path: Path) -> None:
    _, head, body = fetch(tmp_path, "kubernetes-deployment.html", tag="kubernetes")

    assert head["title"] == "Deployments"
    assert body.splitlines()[0] == "# Deployments"
    assert "## Use Case" in headings(body)
    assert "## Creating a Deployment" in headings(body)
    after = body.split("typical use cases for Deployments:\n\n", 1)[1]
    items = after.split("\n\n", 1)[0].splitlines()
    assert len(items) == 7
    assert all(item.startswith("- ") for item in items)
    assert items[0].startswith("- [Create a Deployment to rollout a ReplicaSet](")


def test_opentelemetry_keeps_the_signal_names(tmp_path: Path) -> None:
    _, head, body = fetch(tmp_path, "opentelemetry-signals.html", tag="otel")

    assert head["title"] == "Signals"
    after = body.split("OpenTelemetry currently supports:\n\n", 1)[1]
    assert after.startswith("- Traces\n- Metrics\n- Logs\n- Baggage\n")


def test_sphinx_headings_lose_their_permalinks(tmp_path: Path) -> None:
    fixture = "trtllm-kvcache.html"
    assert page(fixture).xpath("//h1//a[@class='headerlink']")

    _, head, body = fetch(tmp_path, fixture)

    assert head["title"] == "KV Cache System"
    assert body.splitlines()[0] == "# KV Cache System"
    assert [line for line in headings(body) if "](" in line] == []
    assert len(fences(body)) == code_blocks(fixture) == 5
    assert pipe_tables(body) == tables(fixture) == 1


def test_a_sphinx_page_fences_its_code_and_warns_about_the_table_it_lost(
    tmp_path: Path,
) -> None:
    fixture = "nim-tool-calling.html"
    assert (code_blocks(fixture), tables(fixture)) == (4, 1)

    result, _, body = fetch(tmp_path, fixture)

    assert len(fences(body)) == 4
    assert "--tool-call-parser llama3_json" in "\n".join(fences(body))
    assert "NIM_MODEL_PATH=hf://" in "\n".join(fences(body))
    assert result.stderr == (
        f"lorekeep: warning: {TOOL_CALLING}: 0 code blocks / 1 tables of the page are missing "
        "from the Markdown\n"
    )


@pytest.mark.parametrize("fixture", sorted(PAGES))
def test_no_underscore_is_escaped(tmp_path: Path, fixture: str) -> None:
    _, head, body = fetch(tmp_path, fixture)

    assert "\\_" not in body
    assert head["converter"] == f"trafilatura {trafilatura.__version__}"
    assert head["title"]


def test_the_page_whose_comments_crashed_trafilatura_converts(tmp_path: Path) -> None:
    fixture = "langchain-sql-agent.html"
    assert b"<!-- -->" in (FIXTURES / fixture / "body.html").read_bytes()

    _, head, body = fetch(tmp_path, fixture, tag="langchain")

    assert head["title"] == "Build a SQL agent - Docs by LangChain"
    assert len(fences(body)) == code_blocks(fixture) == 4


def test_a_converter_that_raises_is_one_error_line_and_stores_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: object, **__: object) -> str:
        raise ValueError("Input object is not an XML element: lxml.etree._Comment")

    monkeypatch.setattr(trafilatura, "extract", broken)
    store = make_store(tmp_path)
    transport = FakeTransport.from_fixtures("langchain-sql-agent.html")
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, SQL_AGENT, tag="langchain")

    assert result.exit_code == 1
    errors = [line for line in result.stderr.splitlines() if not line.startswith("lorekeep: w")]
    assert errors == [
        f"lorekeep: error: {SQL_AGENT}: could not convert text/html (ValueError: Input object "
        "is not an XML element: lxml.etree._Comment); report it to the owner"
    ]
    assert result.stdout == ""
    assert list(store.glob("*.md")) == []
    assert list(store.glob("*.html")) == []
    assert edges.fetcher is not None
    assert isinstance(edges.fetcher, FakeFetcher) and edges.fetcher.calls == []


RENDERED_CARD = """<!doctype html>
<html><head><title>nvidia-nemotron-nano-9b-v2 Model by NVIDIA | NVIDIA NIM</title></head>
<body><main><article>
<h1>NVIDIA-Nemotron-Nano-9B-v2</h1>
<h2>Model Overview</h2>
<p>NVIDIA-Nemotron-Nano-9B-v2 is a large language model trained from scratch by NVIDIA and
designed as a unified model for both reasoning and non-reasoning tasks. It responds to user
queries and tasks by first generating a reasoning trace and then concluding with a final
response.</p>
<p>The model's reasoning capabilities can be controlled via a system prompt. If the user prefers
the model to provide its final answer without intermediate reasoning traces, it can be
configured to do so, albeit with a slight decrease in accuracy for harder prompts.</p>
</article></main></body></html>
"""


def test_a_client_rendered_page_is_thin_content_and_goes_to_the_browser(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    rendered = tmp_path / "rendered.html"
    rendered.write_text(RENDERED_CARD, encoding="utf-8")
    fetcher = FakeFetcher({MODEL_CARD: (rendered, MODEL_CARD)}, version="0.9.5")
    transport = FakeTransport.from_fixtures("build-nemotron-modelcard.html")
    edges = Edges(transport=transport, fetcher=fetcher, runner=FakeRunner())

    result = get(store, edges, MODEL_CARD, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert fetcher.calls == [MODEL_CARD]
    [version] = store.glob("*.md")
    head, body = read_version(version)
    assert head["converter"] == f"trafilatura {trafilatura.__version__} via crawl4ai 0.9.5"
    assert head["title"] == "NVIDIA-Nemotron-Nano-9B-v2"
    assert b"unified model for both reasoning" in body


def test_a_thin_page_without_the_browser_is_an_error_naming_the_extra(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    transport = FakeTransport.from_fixtures("build-nemotron-modelcard.html")
    edges = Edges(transport=transport, fetcher=FakeFetcher(installed=False), runner=FakeRunner())

    result = get(store, edges, MODEL_CARD, tag="nvidia")

    assert result.exit_code == 1
    assert f"thin content: {MODEL_CARD} converted to " in result.stderr
    assert "lorekeep[browser]" in result.stderr
    assert list(store.glob("*.md")) == []
