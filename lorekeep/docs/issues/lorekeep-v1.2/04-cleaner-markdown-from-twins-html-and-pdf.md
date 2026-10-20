# 04: a true `title`, a search that finds ligatured text, and a warning for pages without structure

**What to build:** Three things the tool owns, with no edit to the Markdown it stores (owner's decision 2026-10-17: stripping a publisher's banner is post-processing, not the tool's job, so the Fern llms.txt banner stays). (1) `title`: when an HTML page's `<title>` begins with an `<h1>` (`ParentDocumentRetriever | langchain_classic | LangChain Reference`, `<h1>` `ParentDocumentRetriever`), that `<h1>` wins over `<title>` for `title` and for the heading inserted when the Markdown has none; a Twin keeps the publisher's own title and H1 (Microsoft Learn's Twin heads itself `# Retry pattern - Azure Architecture Center | Microsoft Learn`); a PDF's `title` comes from the PDF's metadata, else its first non-empty line. (2) Search: the Index and `--exact` compare text with the ligature code points `ﬁ ﬂ ﬀ ﬃ ﬄ` read as their letters, the way `\_` is already unescaped at Index time, so `--exact profile` hits a line the PDF spells `proﬁle`; the stored Markdown is unchanged. (3) A Version over 20,000 characters with no heading below its title prints `lorekeep: warning: <url>: no headings; search answers with the whole page as one Section` on the `get` that stores it. Decisions: `spec.md` › Converters (amended by this ticket).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] a fixture cut from the Store's Original of `reference.langchain.com/…/ParentDocumentRetriever` (rewritten 2026-10-17: the Microsoft Learn Versions are Twins with no Original, see Comments) stores `title: ParentDocumentRetriever`, and its headings' paths in `search` start `ParentDocumentRetriever`; an `<h1>` the `<title>` does not begin with (the AI Act Service Desk banner `AI Act Explorer`) is not the title; a page with `<title>` and no `<h1>` keeps today's behaviour
- [x] the first pages of `nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf` (fixture cut from the Store's Original) store `title` from the PDF's metadata; a PDF without metadata title takes its first non-empty line
- [x] over that fixture, `search --exact profile` hits a line the Markdown spells `proﬁle`, the snippet shows the line as stored, and the Markdown file still contains `ﬁ`; a plain `search profile` finds it too; an Index built by v1.1 is rebuilt by the next reader (bump `SCHEMA_VERSION`)
- [x] the EUR-Lex AI Act Original (`eur-lex.europa.eu/eli/reg/2024/1689/oj`, cut to under 100 KB but over 20,000 characters of Markdown) stores with the no-headings warning; the kubernetes.io Deployment fixture and a short headingless page print none
- [x] `references/store.md` says `title` comes from `<h1>`, else `<title>`, else the first heading, and from a PDF's metadata; `SKILL.md`'s PDF sentence says `--exact` reads ligatures as letters; the flag test passes

## Comments

**2026-10-17** — done on `galkin/lorekeep-v12-04`; tests in `tests/test_titles_ligatures_structure.py`
(one per criterion clause, each naming its fixture). New fixtures, cut from the first Store's
Originals: `langchain-parent-document-retriever.html`, `ai-act-service-desk-article-26.html`,
`nist-ai-600-1.pdf` (page 5 only, 303 KB: its fonts are most of it), `eur-lex-ai-act.html` (60 KB,
28,167 characters of Markdown). Reused: `owasp-excessive-agency.html` (a `<title>`, no `<h1>`),
`exam-guide.pdf` (no information dictionary), `kubernetes-deployment.html`. No stored Markdown
changes anywhere: the three features read the files, they never rewrite them.

- **`title`, HTML** (`cascade/html.py` › `page_title`). The first `<h1>` (permalinks already
  dropped) whose text begins the `<title>` and is followed there by a non-letter (`ParentDocument
  Retriever` of `ParentDocumentRetriever | langchain_classic | LangChain Reference`) is the title,
  and so the heading `finish` inserts when the Markdown kept none; otherwise today's chain
  (Trafilatura's title, `<title>`, first `<h1>`). Over the Store's 224 static HTML Originals this
  changes 25 titles and regresses none: 15 Milvus, 3 Grafana, 3 Prometheus, helm, the LangChain
  reference (`… | site` suffixes dropped) and Riva (`NVIDIA Riva` → `ASR Overview`).
- **Where the ticket was wrong: Microsoft Learn.** All four `learn.microsoft.com` Versions in the
  Store, `patterns/retry` among them, are `md-twin` Versions with `original.stored: false`: there
  is no HTML Original to cut, and `# Retry pattern - Azure Architecture Center | Microsoft Learn` is
  the publisher's own first line of the Twin (its frontmatter `title` is the same string), so no
  heading path can start `Retry pattern` without editing the stored Markdown, which the owner ruled
  out. The Twin keeps the publisher's title and H1 (coordinator's decision A); criterion 1 now names
  the LangChain reference page, the Store's one HTML Original with the same defect (the whole
  `<title>` as the inserted heading). The spec's problem item 5 ("Microsoft Learn's H1 is the whole
  `<title>`") describes the Twin, not the HTML.
- **Where the ticket was wrong: "an `<h1>` wins over `<title>`".** Taken literally it regresses real
  pages: OWASP's three `genai.owasp.org` pages open with a banner `<h1>` (`Join us in Orlando, FL
  10/11 – 10/15 @ InfoSec World 2026`), the AI Act Service Desk's with `AI Act Explorer`, Creative
  Commons' with its logo `Creative Commons`. Hence the rule "an `<h1>` that the `<title>` begins
  with"; `ai-act-service-desk-article-26.html` proves a banner `<h1>` is not taken. The spec's
  › Converters bullet is amended to say so.
- **`title`, PDF** (`cascade/pdf.py`). The `Title` of the information dictionary, read with
  pdfminer.six (`metadata_title`), else MarkItDown's own title (always `None` for a PDF today), else
  the first non-empty line, whitespace squeezed. pdfminer.six is no new dependency: it is the parser
  MarkItDown's `pdf` extra installs, which `markitdown[pdf]` already requires; an Info that cannot
  be read yields no title rather than an error. XMP-only titles are not read.
- **Ligatures** (`index.py`). `as_letters` reads `ﬀ ﬁ ﬂ ﬃ ﬄ` as their letters. The FTS rows are
  written through it; `sections.body` keeps the text as stored, and the FTS table stays external
  content over it, so `snippet()` shows `[proﬁle]` as the file writes it: a ligature is a letter to
  the `unicode61` tokenizer, so its tokens line up with the letters'. `--exact` compares
  `as_letters(unescape(…))` of both sides in SQL and in Python and maps the match back to the stored
  text for its snippet; the query is read the same way, so `--exact proﬁle` hits too.
  `SCHEMA_VERSION` 3 → 4 (no column changes; what `sections_fts` holds does), so an Index built by
  v1.1 is rebuilt by the next reader. Ticket 02 also bumps it: one of the two bumps goes in the
  merge.
- **The no-headings warning** (`cascade/__init__.py` › `structure_warned`, `sections.headings`).
  Any step's `Fetched` whose Markdown is over 20,000 characters with at most one heading outside
  code gets `<final url>: no headings; search answers with the whole page as one Section` in its
  `warnings`, which `get` prints as `lorekeep: warning: …` on the fetch that stores it (and which
  ticket 02 will record with the Version). "No heading below its title" is read as "at most one
  heading": EUR-Lex's only heading is the footer's `Need help?`, which Trafilatura took for the
  title. Two wrong details in the ticket and spec: the OWASP pages are under 20,000 characters
  (9 KB), so they never warn; and the page is not literally one Section (a Section is still cut
  at 4 KB), it is Sections that all share one heading path. Over the Store, 15 Versions would warn:
  both EUR-Lex regulations, both NIST PDFs, kubernetes.io `service`, TensorRT-LLM `LLM`, W3C Trace
  Context, and 8 raw files kept in one fence (`raw-twin`, `verbatim`: code, OpenAPI schemas, an
  `.rst` page), where the warning is true but expected; the owner may want those exempt (count only text outside fences).
- **The skill.** `references/store.md`'s `title` line says where the title comes from (HTML,
  Twin, PDF); `SKILL.md`'s PDF sentence says PDFs keep ligatures that `search`, exact or not, reads as
  letters and that `get` warns on a long page without headings, in the same three lines (249
  lines). It does not spell `--exact`: the flag test reads a flag named in the `get` section as a
  flag of `get`.
