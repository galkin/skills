# 03: HTML extraction keeps code, tables, lists and titles, and reports what it lost

**What to build:** The static-HTML step keeps `<pre>` blocks as fences, tables as pipe tables, link-only lists as lists and the page's title as `title` (and as the first `# ` when the Markdown has no heading); strips permalink anchors from headings; writes `_` unescaped; sends a page that converts to almost nothing to the browser (`thin content`); turns a converter exception into one `lorekeep: error:` line; and warns when code blocks or tables of the page are missing from the Markdown. Decisions: `spec.md` › HTML extraction. Fixtures are cut from the Originals the first migration stored (`docs/issues/lorekeep-v1.1/reports/` names the pages; the files are in `~/orca/sources/agentic-system.design/*.orig.html` on the owner's machine — ask the orchestrator for the ones you need, they are copied into the ticket's worktree under `tests/fixtures/`).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] a Fern Guardrails page (`<pre class="code-block-root">` with nested `<div>`s, 3 code blocks, 1 table) converts with 3 fences and 1 pipe table, and `length_per_perplexity_threshold` is in the Markdown; a Sphinx NeMo page with 16 `<pre>` blocks converts with 16 fences
- [x] a Mintlify LangChain page (`middleware/built-in`) converts with its parameter tables keeping the parameter names and its code samples fenced
- [x] `kubernetes.io/docs/concepts/workloads/controllers/deployment/` converts with `title: Deployments`, a first line `# Deployments`, headings under it, and the seven-item use-case list after "typical use cases for Deployments:"; `opentelemetry.io/docs/concepts/signals` keeps the signal names
- [x] a Sphinx page with `a.headerlink` converts without `[#](…)` in any heading; `nvidia.github.io` headings read `# KV Cache System`
- [x] the Markdown of every fixture above contains no `\_`
- [x] the LangChain `sql-agent` page (the one that raised `lxml.etree._Comment`) converts without an exception; a converter that still raises makes `get` print one `lorekeep: error: <url>: could not convert text/html (ValueError: …); report it to the owner` line, exit 1, store nothing
- [x] `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` (233-byte menu after conversion) is declined with `thin content` and `needs_browser`; with the fake fetcher it is stored `via crawl4ai`; with the fetcher "not installed" `get` exits 1 naming `lorekeep[browser]`
- [x] a page whose code blocks Trafilatura still drops after the retry with the main subtree stores the Version and prints `lorekeep: warning: <url>: N code blocks / M tables of the page are missing from the Markdown`
- [x] the v1 fixtures (`termidy-*`, `nim-*`, `aws-*.html`, `google-*`, `relative-links`) still produce content Markdown; their asserted strings still hold

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v11-03`).**

What `src/lorekeep/cascade/html.py` does now, in order:

- **Parse** with `remove_comments=True, remove_pis=True`: the `lxml.etree._Comment` crash cannot
  reach Trafilatura.
- **Prepare the tree.** Permalinks are dropped: `a.headerlink`, `a.anchor`, a heading's `<a>`
  reading `#`/`¶`/`🔗`/nothing, and also any textless `<a href="#…">` (Mintlify's parameter
  anchors, which made each parameter head a link farm). Every outermost `<pre>` becomes one
  `<pre><code>` holding its text, one line per line block (Fern draws a `<div>` per line, so
  `text_content()` alone would join the lines), no gutter or button, ending in one newline (without
  it Trafilatura writes a `<pre>` inside a list item as inline code: 72 → 30 fences on
  kubernetes.io). Every `<pre>` and `<table>` is then **lifted** out of the `<div>`/`<span>`
  wrappers that hold nothing else: Fern's tables were dropped for their wrappers' classes, not for
  themselves. Mintlify's parameter names are `<button data-component-part="field-name">`, which
  Trafilatura drops with every button; they become `<code>` (a Mintlify-specific rule, the one
  place the converter knows a site's markup).
- **Check and retry.** The Markdown is compared with the tree: distinct `<pre>` texts against the
  fences' texts (by content, because Trafilatura writes a repeated block once — kubernetes.io has
  96 `<pre>`, 75 distinct), `<table>`s with two rows or more against pipe tables, whether
  `<h2>`–`<h4>` exist against Markdown headings, and lists a `<p>` introduces (outside
  `nav`/`aside`/`header`/`footer`) against the Markdown's text. Any loss retries Trafilatura on a
  copy of the first `<main>`, `[role=main]` or `<article>` with `favor_recall`, in which a list item
  that is nothing but a link keeps its text and loses the link (Trafilatura deletes every short
  run of links as navigation; neither `favor_recall` nor the subtree alone kept OpenTelemetry's
  signal names). The retry is taken only when it loses less **and** keeps at least as many fences,
  tables and headings — without that guard it traded 22 tables or 7 headings for one list on two
  Store pages. Code blocks or tables still missing print the warning; the Version is stored.
- **Finish the Markdown.** A fence Trafilatura glued to the end of a line of text (`The output is
  similar to this: ` followed by the fence, from a `<pre>` after a `<p>` in a list item) is moved
  to its own line before measuring — not in the spec's list of post-processing, but without it 30
  of kubernetes.io's code blocks read as prose and the retry could not win. Then `\_` becomes `_`
  outside fences (inside them Trafilatura writes code verbatim, so a `\_` there is the
  author's), and the title becomes the first `# ` line when no heading is left.
- **Title**: `extract_metadata(...).title` on the prepared tree (so `KV Cache System`, not
  `KV Cache System#`), else `<title>`, else the first `<h1>`; written by the page and browser steps.
- **Thin content** (static step only): fewer than 600 characters or 40 words of Markdown text (link
  targets removed) and an Original whose `text_content()` — scripts included, since a
  client-rendered page carries its content there — is at least five times longer. Measured: the
  model card's visible text is 309 characters against 233 of Markdown, so the ratio only holds with
  the script text (58,636 characters); the spec does not say which text content, this is the one
  that works.
- **Converter exception** (`page.py`): any exception from a converter is
  `Fallthrough(final=True)` with the spec's line; `run_cascade` stops on it (no browser) and `get`
  prints it as is, exit 1, nothing stored. A Recheck's reread passes the same line through
  unprefixed.

Measured over all 365 HTML Originals of the first migration (old → new): pages with `<pre>` and no
fence 80 → 1; with `<table>` and no pipe table 66 → 13; with no heading 53 → 0; fences 2,288 →
3,941 (of 4,005 `<pre>`); Versions with `\_` → 0; warnings on 37 pages; thin content on 2
(the model card and `docs.nvidia.com/rag/latest/api-rag.html`, a client-rendered API page). Five
pages count fewer pipe tables or fences than before; checked, each is a Sphinx `<caption>` with a
headerlink that Trafilatura used to write as a bogus one-row `| # |` table, or a glued fence the old
count misread.

Fixtures (README updated): nine new folders cut from the Originals, all failing on the old code.
Ticket corrections: the Fern Guardrails page has **4** tables, not 1 (`3 fences and 4 pipe tables`
is asserted); the 16-`<pre>` NeMo page is Fern (`guardrails/…/self-check`), not Sphinx; the
Mintlify page keeps all 29 parameter names of the cut and fences 9 of its 10 code blocks — the
10th sits in a Tip callout that Trafilatura drops whole (text too), and the page prints `1 code
blocks / 0 tables … missing`; that page and `nim-tool-calling.html` (a table inside a list item,
`0 code blocks / 1 tables`) are the warning's real-world fixtures.

Not done: the warning is printed by `get` on a first fetch only — a Recheck that stores a new
Version through `recheck.perform` does not print it. OpenTelemetry's second list (`Events, a
specific type of log`, items mixing text and links) is still dropped; the page's own `<h1>` is
still dropped (its section-index `<h5>` survives, so no title heading is inserted).
