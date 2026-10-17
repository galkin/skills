# 05: `get` falls back to the browser

**What to build:** When the plain client gets `403`/`429`, an empty or JavaScript-only body, or the host table marks the host `browser = true`, `get` fetches the page through the page-fetcher edge (Crawl4AI in production, an optional dependency), applies the host's selector list of what to cut, converts the result and records `converter: crawl4ai <version>`. If Crawl4AI is not installed, `get` says so and names the extra to install.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] the Milvus `403` fixture triggers the fetcher fake exactly once and stores what it returns with `converter: crawl4ai …`
- [ ] a host with `browser = true` skips the plain client entirely
- [ ] a JavaScript-only body (no text after extraction) triggers the fetcher
- [ ] the host's `cut` selectors are passed to the fetcher
- [ ] with the fetcher absent (fake returns "not installed"), `get` exits non-zero with the install hint and stores nothing
