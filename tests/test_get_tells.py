"""`get` tells a Run what the tool knows (v1.2 #02): the address as asked, a Version's warnings on
every return, a `third-party` verdict no rule made for the publisher, and a Markdown that holds
little of the page's main text.

Each test names its fixture; the main-text ones are pages of the first migration's Store and one
synthesised catalog page whose link lists Trafilatura drops.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from lorekeep.commands.skill import skill_folder
from tests.support import edges_over, get, lorekeep, make_store
from tests.test_helpers import read_version

MIDDLEWARE = "https://docs.langchain.com/oss/python/langchain/middleware/built-in"
MISSING_CODE = "1 code blocks / 0 tables of the page are missing from the Markdown"
BLOB_README = "https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/README.md"
BLOB_YAML = (
    "https://github.com/NVIDIA-AI-Blueprints/deep-researcher-agent/blob/main/deploy/compose/"
    "docker-compose.yaml"
)
HELM = "https://helm.sh/docs/helm/helm_rollback"
QUANTIZATION = "https://nvidia.github.io/Model-Optimizer/guides/1_quantization.html"
TOCTREE = (
    "Basic Concepts",
    "Best practices to choose the right quantization methods",
    "PyTorch Quantization",
    "Quantization Configuration (quant_cfg)",
    "Guides to quantize a customized model from Hugging Face for TensorRT-LLM deployment",
    "Compress quantized models",
    "ONNX Quantization - Linux (Beta)",
    "ONNX Quantization - Windows",
)
CATALOG = "https://docs.example.test/guides"
DEPLOYMENT = "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"
MAIN_TEXT = "of the page's main text"


def the_version(store: Path) -> tuple[dict[str, Any], str]:
    [path] = store.glob("*.md")
    head, body = read_version(path)
    return head, body.decode("utf-8")


def test_get_json_keeps_the_fragment_asked_in_asked_alone(tmp_path: Path) -> None:
    """Fixture `langchain-middleware-built-in.html`."""
    store = make_store(tmp_path)
    edges, _ = edges_over("langchain-middleware-built-in.html")
    asked = f"{MIDDLEWARE}#model-fallback"

    result = get(store, edges, "--json", asked, tag="langchain")

    printed = json.loads(result.stdout)
    assert printed["asked"] == asked
    assert printed["requested_url"] == printed["url"] == MIDDLEWARE


def test_a_missing_code_warning_is_kept_and_printed_again_on_a_fresh_get(tmp_path: Path) -> None:
    """Fixture `langchain-middleware-built-in.html`: the warning of the `get` that stored the
    Version, from its frontmatter, on a later `get` that returns it without a request."""
    store = make_store(tmp_path)
    edges, transport = edges_over("langchain-middleware-built-in.html")
    line = f"lorekeep: warning: {MIDDLEWARE}: {MISSING_CODE}"

    first = get(store, edges, "--json", MIDDLEWARE, tag="langchain")
    asked = len(transport.requests)
    second = get(store, edges, "--json", MIDDLEWARE, tag="langchain")

    assert json.loads(first.stdout)["outcome"] == "stored"
    assert json.loads(second.stdout)["outcome"] == "fresh"
    assert len(transport.requests) == asked
    assert line in first.stderr.splitlines()
    assert second.stderr.splitlines() == [line]
    head, _ = the_version(store)
    assert head["warnings"] == [MISSING_CODE]


def test_a_github_page_under_the_catch_all_is_named_third_party(tmp_path: Path) -> None:
    """Fixture `github-readme.raw` under the default table's `github.com/` rule, on the `get`
    that stores the Version and on the one that returns it."""
    store = make_store(tmp_path)
    edges, _ = edges_over("github-readme.raw")
    note = f"lorekeep: note: {BLOB_README} is third-party under the github.com/ rule"

    first = get(store, edges, BLOB_README, tag="nvidia")
    second = get(store, edges, BLOB_README, tag="nvidia")

    assert first.stderr.splitlines() == [note]
    assert second.stderr.splitlines() == [note]


def test_a_page_under_no_rule_is_named_beside_the_unknown_host_warning(tmp_path: Path) -> None:
    """Fixture `helm-rollback.html`: `helm.sh` is in no host table."""
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.html")

    first = get(store, edges, f"{HELM}/", tag="helm")
    second = get(store, edges, f"{HELM}/", tag="helm")

    lines = [
        "lorekeep: warning: helm.sh is in no host table; stored as third-party — "
        "tell the owner, who may add a [[hosts]] rule",
        f"lorekeep: note: {HELM} is third-party under no rule",
    ]
    assert first.stderr.splitlines() == lines
    assert second.stderr.splitlines() == lines


def test_a_page_under_a_vendors_own_github_rule_prints_neither(tmp_path: Path) -> None:
    """Fixture `github-docker-compose.raw` under the first Store's rule for
    `github.com/NVIDIA-AI-Blueprints/` (the default table's catch-all no longer decides it)."""
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "github.com/NVIDIA-AI-Blueprints/"\npublisher = "nvidia"\n'
        'authority = "official"\ntwin = "github-raw"\n'
    )
    edges, _ = edges_over("github-docker-compose.raw")

    result = get(store, edges, "--json", BLOB_YAML, tag="nvidia")

    assert result.exit_code == 0
    assert json.loads(result.stdout)["authority"] == "official"
    assert result.stderr == ""


def test_the_sphinx_toctree_after_its_paragraph_is_kept(tmp_path: Path) -> None:
    """Fixture `model-optimizer-quantization.html`, under the first Store's `nvidia.github.io/`
    rule: the list sits in a `toctree-wrapper` `<div>` after the paragraph that introduces it;
    v1.1 dropped it and said nothing."""
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "nvidia.github.io/"\npublisher = "nvidia"\nauthority = "primary"\n'
    )
    edges, _ = edges_over("model-optimizer-quantization.html")

    result = get(store, edges, QUANTIZATION, tag="nvidia")

    assert result.exit_code == 0
    assert result.stderr == ""
    head, body = the_version(store)
    after = body.split("documentation for the quantization toolkit in ModelOpt:\n\n", 1)[1]
    assert after.splitlines()[: len(TOCTREE)] == [f"- {entry}" for entry in TOCTREE]
    assert "warnings" not in head


def test_a_markdown_with_a_sliver_of_the_main_text_is_stored_with_a_warning(
    tmp_path: Path,
) -> None:
    """Fixture `guides-catalog.html` (synthesised): three paragraphs Trafilatura keeps above
    sixteen headed lists of links it drops, inside `<main>`; more than 600 characters are kept,
    so it is no `thin content` error."""
    store = make_store(tmp_path)
    edges, _ = edges_over("guides-catalog.html")

    first = get(store, edges, CATALOG, tag="example")
    second = get(store, edges, CATALOG, tag="example")

    head, _ = the_version(store)
    [warning] = head["warnings"]
    assert isinstance(warning, str)
    percent = int(warning.removeprefix("the Markdown holds ").removesuffix(f"% {MAIN_TEXT}"))
    assert percent < 20
    line = f"lorekeep: warning: {CATALOG}: {warning}"
    assert line in first.stderr.splitlines()
    assert line in second.stderr.splitlines()


def test_a_page_whose_markdown_holds_its_main_text_has_no_such_warning(tmp_path: Path) -> None:
    """Fixture `kubernetes-deployment.html`."""
    store = make_store(tmp_path)
    edges, _ = edges_over("kubernetes-deployment.html")

    result = get(store, edges, DEPLOYMENT, tag="kubernetes")

    assert result.exit_code == 0
    assert MAIN_TEXT not in result.stderr
    head, _ = the_version(store)
    assert "warnings" not in head


def test_an_index_built_by_v1_1_is_rebuilt_and_search_answers_as_before(tmp_path: Path) -> None:
    """Fixture `langchain-middleware-built-in.html`: an Index of schema 3, without
    `versions.warnings`, is rebuilt by the next reader."""
    store = make_store(tmp_path)
    edges, _ = edges_over("langchain-middleware-built-in.html")
    get(store, edges, MIDDLEWARE, tag="langchain")
    before = lorekeep(store, edges, "search", "--json", "fallback model")
    with sqlite3.connect(store / "sources.db") as con:
        [row] = con.execute("SELECT warnings FROM versions").fetchall()
        assert json.loads(row[0]) == [MISSING_CODE]
        con.execute("UPDATE meta SET value = '3' WHERE key = 'schema'")
        con.execute("DROP VIEW latest")
        con.execute("ALTER TABLE versions DROP COLUMN warnings")

    after = lorekeep(store, edges, "search", "--json", "fallback model")

    assert "rebuilt" in after.stderr
    assert after.stdout == before.stdout
    assert json.loads(after.stdout)["results"]
    with sqlite3.connect(store / "sources.db") as con:
        assert con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone() == ("5",)


def test_the_store_reference_documents_asked_and_warnings() -> None:
    store_md = skill_folder().joinpath("references", "store.md").read_text(encoding="utf-8")

    assert "\n- `asked` — " in store_md
    assert "\n- `warnings` — " in store_md
