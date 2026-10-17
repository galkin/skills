"""A true `title`, a search that reads ligatures as letters, and a warning for a long page with no
headings; the stored Markdown is never edited for any of them (v1.2 ticket 04)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from lorekeep import sections
from tests.support import Result, edges_over, get, make_store, run_cli
from tests.test_helpers import read_version

PARENT_RETRIEVER = (
    "https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/"
    "ParentDocumentRetriever"
)
ARTICLE_26 = "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-26"
OWASP = "https://genai.owasp.org/llmrisk/llm062025-excessive-agency/"
NIST = "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf"
NIST_TITLE = (
    "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile"
)
EXAM_GUIDE = "https://example.test/exam/guide"
AI_ACT = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
DEPLOYMENT = "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"
NO_HEADINGS = "no headings; search answers with the whole page as one Section"


def stored(tmp_path: Path, fixture: str, url: str) -> tuple[Path, Result]:
    """The Store after `get url` over `fixture` alone, and what `get` printed."""
    store = make_store(tmp_path)
    edges, _ = edges_over(fixture)
    result = get(store, edges, url, tag="t")
    assert result.exit_code == 0, result.stderr
    return store, result


def version_of(store: Path) -> Path:
    [path] = store.glob("*.md")
    return path


def search(store: Path, *argv: str) -> dict[str, object]:
    result = run_cli(["search", *argv, "--all", "--json", "--store", str(store)])
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)


def hits(found: dict[str, object]) -> list[dict[str, object]]:
    results = found["results"]
    assert isinstance(results, list)
    return results


# title --------------------------------------------------------------------------------------------


def test_an_h1_the_title_begins_with_is_the_title_and_heads_every_heading_path(
    tmp_path: Path,
) -> None:
    """`langchain-parent-document-retriever.html`: `<title>ParentDocumentRetriever |
    langchain_classic | LangChain Reference`, `<h1>ParentDocumentRetriever`, and a Markdown with
    no heading of its own, so the title is also the heading the converter writes."""
    store, _ = stored(tmp_path, "langchain-parent-document-retriever.html", PARENT_RETRIEVER)

    head, body = read_version(version_of(store))

    assert head["title"] == "ParentDocumentRetriever"
    assert body.startswith(b"# ParentDocumentRetriever\n")
    found = hits(search(store, "parent documents"))
    assert found
    assert all(str(hit["heading"]).startswith("ParentDocumentRetriever") for hit in found)


def test_an_h1_the_title_does_not_begin_with_is_not_the_title(tmp_path: Path) -> None:
    """`ai-act-service-desk-article-26.html`: its only `<h1>` is the site's banner `AI Act
    Explorer`, which the `<title>` (`Article 26: …`) does not begin with."""
    store, _ = stored(tmp_path, "ai-act-service-desk-article-26.html", ARTICLE_26)

    head, _ = read_version(version_of(store))

    assert head["title"] == (
        "AI Act Service Desk - Article 26: Obligations of deployers of high-risk AI systems"
    )


def test_a_page_with_a_title_and_no_h1_keeps_todays_title(tmp_path: Path) -> None:
    """`owasp-excessive-agency.html`: a `<title>` and no `<h1>`."""
    store, _ = stored(tmp_path, "owasp-excessive-agency.html", OWASP)

    head, _ = read_version(version_of(store))

    assert head["title"] == "LLM06:2025 Excessive Agency"


def test_a_pdf_takes_its_title_from_its_metadata(tmp_path: Path) -> None:
    """`nist-ai-600-1.pdf`: page 5 of NIST AI 600-1 with the document's information dictionary,
    whose text starts `1.`, so the title can only come from the metadata."""
    store, _ = stored(tmp_path, "nist-ai-600-1.pdf", NIST)

    head, body = read_version(version_of(store))

    assert head["title"] == NIST_TITLE
    assert body.startswith(b"1.\n")


def test_a_pdf_without_a_metadata_title_takes_its_first_non_empty_line(tmp_path: Path) -> None:
    """`exam-guide.pdf`: a PDF with no information dictionary."""
    store, _ = stored(tmp_path, "exam-guide.pdf", EXAM_GUIDE)

    head, _ = read_version(version_of(store))

    assert head["title"] == "Exam Guide"


# ligatures ----------------------------------------------------------------------------------------


def test_exact_search_reads_a_ligature_as_its_letters_and_shows_the_line_as_stored(
    tmp_path: Path,
) -> None:
    """`nist-ai-600-1.pdf`: MarkItDown keeps `proﬁle` with U+FB01, and so does the Version."""
    store, _ = stored(tmp_path, "nist-ai-600-1.pdf", NIST)
    path = version_of(store)
    text = path.read_text(encoding="utf-8")

    [hit] = hits(search(store, "--exact", "profile", "--limit", "1"))

    assert "proﬁle" in text
    assert "profile" not in text
    line = text.splitlines()[int(str(hit["line"])) - 1]
    assert "proﬁle" in line
    assert "[proﬁle]" in str(hit["snippet"])
    assert hits(search(store, "--exact", "proﬁle", "--limit", "1")) == [hit]


def test_a_plain_search_finds_a_word_the_pdf_spells_with_a_ligature(tmp_path: Path) -> None:
    """`nist-ai-600-1.pdf`: every `profile` of the page is spelled `proﬁle`."""
    store, _ = stored(tmp_path, "nist-ai-600-1.pdf", NIST)
    text = version_of(store).read_text(encoding="utf-8")

    [hit] = hits(search(store, "profile", "--limit", "1"))

    assert "[proﬁle]" in str(hit["snippet"])
    assert "proﬁle" in text.splitlines()[int(str(hit["line"])) - 1]


def test_an_index_built_before_ligatures_were_read_as_letters_is_rebuilt(tmp_path: Path) -> None:
    """`nist-ai-600-1.pdf`: an Index as v1.1 built it (schema 3, FTS rows as stored) misses
    `profile`; the next reader rebuilds it and finds it."""
    store, _ = stored(tmp_path, "nist-ai-600-1.pdf", NIST)
    assert run_cli(["index", "--store", str(store)]).exit_code == 0
    with sqlite3.connect(store / "sources.db") as con:
        con.execute("INSERT INTO sections_fts(sections_fts) VALUES('delete-all')")
        con.execute(
            "INSERT INTO sections_fts(rowid, heading, body) SELECT id, heading, body FROM sections"
        )
        con.execute("UPDATE meta SET value = '3' WHERE key = 'schema'")

    result = run_cli(["search", "profile", "--all", "--store", str(store)])

    assert result.exit_code == 0, result.stderr
    assert "rebuilt" in result.stderr
    assert "[proﬁle]" in result.stdout


# structure ----------------------------------------------------------------------------------------


def test_a_long_page_with_no_heading_below_its_title_is_stored_with_a_warning(
    tmp_path: Path,
) -> None:
    """`eur-lex-ai-act.html`: the AI Act's head and first 30 recitals, 60 KB of HTML, 28,000
    characters of Markdown whose one heading is the footer's `Need help?`."""
    store, result = stored(tmp_path, "eur-lex-ai-act.html", AI_ACT)

    body = read_version(version_of(store))[1].decode("utf-8")

    assert len(body) > 20_000
    assert sections.headings(body) == 1
    assert f"lorekeep: warning: {AI_ACT}: {NO_HEADINGS}\n" in result.stderr


def test_a_page_with_headings_and_a_short_page_without_any_print_no_such_warning(
    tmp_path: Path,
) -> None:
    """`kubernetes-deployment.html` (headings) and `exam-guide.pdf` (no heading, one line)."""
    _, deployment = stored(tmp_path / "k8s", "kubernetes-deployment.html", DEPLOYMENT)
    _, exam_guide = stored(tmp_path / "pdf", "exam-guide.pdf", EXAM_GUIDE)

    assert NO_HEADINGS not in deployment.stderr
    assert NO_HEADINGS not in exam_guide.stderr
