"""JSON, YAML, plain text, CSV and XML are stored verbatim in one fence (v1.1 ticket 01)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

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

SCHEMA = "https://docs.nvidia.com/rag/latest/_static/api_reference/openapi_schema_rag_server.json"
EXAMPLES = "https://docs.nvidia.com/rag/latest/_static/examples"


def test_a_json_file_is_stored_verbatim_in_one_json_fence(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("rag-openapi-schema.json")

    result = get(store, edges, SCHEMA, tag="nvidia")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    received = (FIXTURES / "rag-openapi-schema.json" / "body.json").read_bytes()
    assert head["url"] == SCHEMA
    assert head["converter"] == "verbatim"
    assert head["title"] == "openapi_schema_rag_server.json"
    assert head["publisher"] == "nvidia"
    assert head["original"]["mediatype"] == "application/json"
    assert head["original"]["stored"] == "true"
    assert body == b"```json\n" + received + b"```\n"
    [original] = store.glob("*.orig.*")
    assert original.name.endswith(".orig.json")
    assert original.read_bytes() == received


@pytest.mark.parametrize(
    ("fixture", "name", "language", "mediatype"),
    [
        ("verbatim-notes.text", "notes.txt", "text", "text/plain"),
        ("verbatim-values.yaml", "values.yaml", "yaml", "application/yaml"),
        ("verbatim-models.csv", "models.csv", "csv", "text/csv"),
        ("verbatim-feed.xml", "feed.xml", "xml", "application/xml"),
    ],
)
def test_text_formats_are_stored_verbatim_in_one_fence(
    tmp_path: Path, fixture: str, name: str, language: str, mediatype: str
) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over(fixture)

    result = get(store, edges, f"{EXAMPLES}/{name}", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    [version] = store.glob("*.md")
    head, body = read_version(version)
    received = next((FIXTURES / fixture).glob("body.*")).read_bytes()
    assert head["converter"] == "verbatim"
    assert head["title"] == name
    assert head["original"]["mediatype"] == mediatype
    assert body == f"```{language}\n".encode() + received + b"```\n"


def test_an_empty_verbatim_file_is_not_stored(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"  \n")
    transport = FakeTransport.from_fixtures("verbatim-notes.text")
    transport.fixtures = [replace(fixture, body=empty) for fixture in transport.fixtures]
    edges = Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())

    result = get(store, edges, f"{EXAMPLES}/notes.txt", tag="nvidia")

    assert result.exit_code == 1
    assert "no content" in result.stderr
    assert not list(store.glob("*.md"))


def answering(fixture: str, body: bytes, tmp_path: Path, **headers: str) -> Edges:
    path = tmp_path / "answer"
    path.write_bytes(body)
    transport = FakeTransport.from_fixtures(fixture)
    transport.fixtures = [
        replace(fixture_, body=path, headers={**fixture_.headers, **headers})
        for fixture_ in transport.fixtures
    ]
    return Edges(transport=transport, fetcher=FakeFetcher(), runner=FakeRunner())


def stored_then_aged(store: Path) -> Path:
    edges, _ = edges_over("rag-openapi-schema.json")
    result = get(store, edges, SCHEMA, tag="nvidia")
    assert result.exit_code == 0, result.stderr
    path = Path(result.stdout.splitlines()[-1])
    age_version(path, days=40)
    return path


def test_a_verbatim_version_is_rechecked_through_the_page_step(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old = stored_then_aged(store)
    edges = answering("rag-openapi-schema.json", b'{"openapi": "3.1.0"}\n', tmp_path)

    result = get(store, edges, SCHEMA, "--json", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    printed = json.loads(result.stdout)
    assert printed["outcome"] == "changed"
    assert printed["converter"] == "verbatim"
    assert Path(printed["path"]) != old
    _, body = read_version(Path(printed["path"]))
    assert body == b'```json\n{"openapi": "3.1.0"}\n```\n'


def test_a_verbatim_version_now_answering_html_is_an_error(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old = stored_then_aged(store)
    edges = answering(
        "rag-openapi-schema.json",
        b"<html><body><p>Moved.</p></body></html>",
        tmp_path,
        **{"content-type": "text/html"},
    )

    result = get(store, edges, SCHEMA, "--json", tag="nvidia")

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["path"] == str(old)
    assert "not what verbatim reads" in result.stderr
    assert [row["result"] for row in rows(store, "checks.csv")] == ["error"]
    assert len(list(store.glob("*.md"))) == 1
