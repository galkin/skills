# 05: `get` falls back to the browser

**What to build:** When the plain client gets `403`/`429`, an empty or JavaScript-only body, or the host rule says `browser = true`, `get` fetches the page through the page-fetcher edge (Crawl4AI in production, the optional extra `lorekeep[browser]`), applies the rule's `cut` selector list, converts the result and records `converter: crawl4ai <version>`. If Crawl4AI is not installed, `get` says so, names the extra, and stores nothing.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] the `milvus-403` fixture triggers the fetcher fake exactly once and stores what it returns with `converter: crawl4ai …` and the rendered HTML as the Original
- [ ] a host with `browser = true` skips the plain client entirely (zero transport calls)
- [ ] the `js-only.html` fixture (no text after extraction) triggers the fetcher
- [ ] the rule's `cut` selectors are passed to the fetcher
- [ ] with the fetcher absent (fake reports "not installed"), `get` exits non-zero with the extra's name and stores nothing
