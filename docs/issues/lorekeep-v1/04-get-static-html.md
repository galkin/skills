# 04: `get` extracts static HTML

**What to build:** When no Twin exists, `get` fetches the page over plain HTTP, follows HTTP redirects and `<meta http-equiv="refresh">` stubs, and for a `text/html` response extracts the main content with Trafilatura (formatting, links, tables on), rewrites relative links to absolute against the final URL, stores the received HTML as the Original (`<stem>.orig.html`, `original.stored: true`, `original.sha256` of the bytes) and records `converter: trafilatura <version>`. The step is chosen by the response's media type, never by the URL. An extraction that yields no text is reported as "no content" and stores nothing; ticket 06 turns that into the browser step.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] the three termidy lesson fixtures and the Anthropic/AWS HTML fixtures each produce a Version whose body has no `<div`, no cookie-banner text and absolute links only
- [ ] the NVIDIA NIM meta-refresh stub fixture is followed and the target page is stored under the target URL with the stub's URL in `original.url`; the stub is never stored
- [ ] the Original is stored beside the Version with its own sha256 in the frontmatter and `original.stored: true`
- [ ] `converter` carries the Trafilatura version string
- [ ] the `js-only.html` fixture is reported as "no content", exits non-zero, stores nothing
