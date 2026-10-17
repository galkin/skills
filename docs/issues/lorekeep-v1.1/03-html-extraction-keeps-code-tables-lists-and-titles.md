# 03: HTML extraction keeps code, tables, lists and titles, and reports what it lost

**What to build:** The static-HTML step keeps `<pre>` blocks as fences, tables as pipe tables, link-only lists as lists and the page's title as `title` (and as the first `# ` when the Markdown has no heading); strips permalink anchors from headings; writes `_` unescaped; sends a page that converts to almost nothing to the browser (`thin content`); turns a converter exception into one `lorekeep: error:` line; and warns when code blocks or tables of the page are missing from the Markdown. Decisions: `spec.md` › HTML extraction. Fixtures are cut from the Originals the first migration stored (`docs/issues/lorekeep-v1.1/reports/` names the pages; the files are in `~/orca/sources/agentic-system.design/*.orig.html` on the owner's machine — ask the orchestrator for the ones you need, they are copied into the ticket's worktree under `tests/fixtures/`).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] a Fern Guardrails page (`<pre class="code-block-root">` with nested `<div>`s, 3 code blocks, 1 table) converts with 3 fences and 1 pipe table, and `length_per_perplexity_threshold` is in the Markdown; a Sphinx NeMo page with 16 `<pre>` blocks converts with 16 fences
- [ ] a Mintlify LangChain page (`middleware/built-in`) converts with its parameter tables keeping the parameter names and its code samples fenced
- [ ] `kubernetes.io/docs/concepts/workloads/controllers/deployment/` converts with `title: Deployments`, a first line `# Deployments`, headings under it, and the seven-item use-case list after "typical use cases for Deployments:"; `opentelemetry.io/docs/concepts/signals` keeps the signal names
- [ ] a Sphinx page with `a.headerlink` converts without `[#](…)` in any heading; `nvidia.github.io` headings read `# KV Cache System`
- [ ] the Markdown of every fixture above contains no `\_`
- [ ] the LangChain `sql-agent` page (the one that raised `lxml.etree._Comment`) converts without an exception; a converter that still raises makes `get` print one `lorekeep: error: <url>: could not convert text/html (ValueError: …); report it to the owner` line, exit 1, store nothing
- [ ] `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` (233-byte menu after conversion) is declined with `thin content` and `needs_browser`; with the fake fetcher it is stored `via crawl4ai`; with the fetcher "not installed" `get` exits 1 naming `lorekeep[browser]`
- [ ] a page whose code blocks Trafilatura still drops after the retry with the main subtree stores the Version and prints `lorekeep: warning: <url>: N code blocks / M tables of the page are missing from the Markdown`
- [ ] the v1 fixtures (`termidy-*`, `nim-*`, `aws-*.html`, `google-*`, `relative-links`) still produce content Markdown; their asserted strings still hold
