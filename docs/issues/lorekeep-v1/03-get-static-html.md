# 03: `get` extracts static HTML

**What to build:** When no Twin exists, `get` fetches the page over plain HTTP, follows HTTP redirects and `<meta http-equiv="refresh">` stubs, extracts the main content with Trafilatura (formatting, links, tables on), rewrites relative links to absolute against the final URL, stores the received HTML as the Original (`<stem>.orig.html`, `original.stored` pointing at it, `original.sha256` of the bytes) and records `converter: trafilatura <version>`. The step is chosen by the response's media type (`text/html`), never by the URL. The client sends a `User-Agent` naming lorekeep and its version.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] the three termidy lesson fixtures and the Anthropic/AWS HTML fixtures each produce a Version whose body has no `<div`, no cookie-banner text and absolute links only
- [ ] the NVIDIA NIM meta-refresh stub fixture is followed and the target page is what gets stored under the target URL, the stub's URL in `original.url`; the stub is never stored
- [ ] the Original is stored beside the Version with its own sha256 in the frontmatter
- [ ] `converter` carries the Trafilatura version string
- [ ] a page whose extraction yields an empty body is reported as "no content" and not stored (ticket 05 turns this into the browser step)
- [ ] every request the fake transport records carries a `User-Agent` that starts with `lorekeep/`
