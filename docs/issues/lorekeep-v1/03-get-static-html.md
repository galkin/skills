# 03: `get` extracts static HTML

**What to build:** When no Twin exists, `get` fetches the page over plain HTTP, follows HTTP redirects and `<meta http-equiv="refresh">` stubs, extracts the main content with Trafilatura (formatting, links, tables on), rewrites relative links to absolute against the final URL, stores the received HTML as the Original (`<stem>.orig.html`, `original.stored` pointing at it) and records `converter: trafilatura <version>`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] the three termidy lesson fixtures and the Anthropic/AWS HTML fixtures each produce a Version whose body has no `<div`, no cookie-banner text and absolute links only
- [ ] the NVIDIA NIM meta-refresh stub fixture is followed and the target page is what gets stored; the stub is never stored
- [ ] the Original is stored beside the Version with its own sha256 in the frontmatter
- [ ] `converter` carries the Trafilatura version string
- [ ] a page whose extraction yields an empty body is reported as "no content" and not stored
