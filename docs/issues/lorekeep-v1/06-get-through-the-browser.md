# 06: `get` falls back to the browser

**What to build:** On a first fetch, when the plain client gets `403`/`429`, when extraction yields no text, or when the host rule says `browser = true`, `get` asks the page-fetcher edge (Crawl4AI in production, the optional extra `lorekeep[browser]`; it returns `result.html` untouched, not `cleaned_html`) for the rendered document and the final URL, removes the rule's `cut` selectors itself with `lxml`, then hands that HTML to ticket 04's extraction: the Original is the rendered HTML and `converter` is `trafilatura <version> via crawl4ai <version>`. If Crawl4AI is not installed, `get` says so, names the extra, and stores nothing.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] the `milvus-403` fixture triggers the fetcher fake exactly once and stores what it returns with `converter: trafilatura … via crawl4ai …` and the rendered HTML as the Original
- [ ] a host given `browser = true` in the test's `lorekeep.toml` skips the plain client entirely (zero transport calls)
- [ ] the `js-only.html` fixture now triggers the fetcher instead of "no content"
- [ ] the rule's `cut` selectors are removed from the fetcher's HTML before extraction (a fake returning a page with a `<nav>` and `cut = ["nav"]` yields a body without the nav text) and the Original is the document before the cut
- [ ] with the fetcher absent (fake in "not installed" mode), `get` exits non-zero with the extra's name and stores nothing
