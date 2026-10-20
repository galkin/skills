"""`get` reads a PDF (ticket 05)."""

from __future__ import annotations

import hashlib
from importlib import metadata
from pathlib import Path

from tests.support import FIXTURES, edges_over, get, make_store
from tests.test_helpers import read_version

EXAM_GUIDE = "https://example.test/exam/guide"


def test_a_pdf_served_under_a_url_without_pdf_is_converted_by_markitdown(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, transport = edges_over("exam-guide.pdf")

    result = get(store, edges, EXAM_GUIDE)

    assert result.exit_code == 0, result.stderr
    versions = list(store.glob("*.md"))
    assert len(versions) == 1
    assert result.stdout.rstrip("\n").splitlines()[-1] == str(versions[0])
    head, body = read_version(versions[0])
    assert head["converter"] == f"markitdown {metadata.version('markitdown')}"
    assert b"Prompt caching reduces cost and latency" in body
    assert head["sha256"] == hashlib.sha256(body).hexdigest()
    assert head["url"] == EXAM_GUIDE
    received = (FIXTURES / "exam-guide.pdf" / "body.pdf").read_bytes()
    original = versions[0].with_name(versions[0].name.removesuffix(".md") + ".orig.pdf")
    assert original.read_bytes() == received
    assert head["original"] == {
        "url": EXAM_GUIDE,
        "mediatype": "application/pdf",
        "sha256": hashlib.sha256(received).hexdigest(),
        "stored": "true",
    }
    assert [str(request.url) for request in transport.requests] == [EXAM_GUIDE]


def test_a_media_type_no_step_takes_is_reported_as_unsupported_and_stores_nothing(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("exam-guide.zip")

    result = get(store, edges, "https://example.test/exam/guide.zip")

    assert result.exit_code != 0
    assert "unsupported media type application/zip" in result.stderr
    assert result.stdout == ""
    assert list(store.iterdir()) == []


def test_html_under_a_pdf_url_is_never_handed_to_markitdown(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("exam-guide.html-as-pdf")

    get(store, edges, "https://example.test/exam/guide.pdf")

    assert not list(store.glob("*.orig.pdf"))
    for version in store.glob("*.md"):
        head, _ = read_version(version)
        assert not head["converter"].startswith("markitdown")
        assert head["original"]["mediatype"] == "text/html"


def test_bytes_served_as_pdf_that_are_not_a_pdf_store_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("exam-guide.not-a-pdf")

    result = get(store, edges, "https://example.test/exam/broken")

    assert result.exit_code != 0
    assert "not a PDF" in result.stderr
    assert list(store.iterdir()) == []


def test_a_pdf_behind_a_host_whose_twin_is_missing_is_read_by_the_pdf_step(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    (store / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "example.test/"\npublisher = "example"\n'
        'authority = "official"\ntwin = "md-suffix"\n',
        encoding="utf-8",
    )
    edges, transport = edges_over("exam-guide.pdf")

    result = get(store, edges, EXAM_GUIDE)

    assert result.exit_code == 0, result.stderr
    assert [str(request.url) for request in transport.requests] == [
        f"{EXAM_GUIDE}.md",
        EXAM_GUIDE,
    ]
    (version,) = store.glob("*.md")
    head, _ = read_version(version)
    assert head["converter"].startswith("markitdown ")
    assert head["publisher"] == "example"
    assert head["authority"] == "official"
    assert "warning" not in result.stderr
