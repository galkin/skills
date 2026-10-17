# Fetching is a cascade, and the browser is the last resort

`get` tries, in order: the publisher's Twin over plain HTTP (`<page>.md`, `?accept=text/markdown`,
`raw.githubusercontent.com`); the page's static HTML over plain HTTP through Trafilatura, with links
made absolute; MarkItDown for PDF and Office files, Docling for PDFs whose layout matters; and
Crawl4AI only for pages that need a browser, with a per-site configuration of what to cut. The
Converter that succeeded is recorded, and the response's media type — never the URL's extension —
decides which step converts. HTTP is plain `httpx` with no cache library: the Store is the cache,
and the conditional requests are lorekeep's own (ADR 0007). The Twin rules and the publisher of
every host probed so far ship inside the package as a default host table; a Project's
`lorekeep.toml` extends or overrides it, so no Project rewrites what is true of `learn.microsoft.com`
everywhere.

Measured on five real pages (2026-10-17): Trafilatura's Markdown was 8–78% smaller than Crawl4AI's
default `fit_markdown`, which kept cookie banners from the live page, and 0.7 s against 5.2 s per
page; pandoc on full HTML left 443 `<div>` lines on one page. A Twin was the most complete of all —
it carries every code-language tab the HTML hides. What an agent reads is what costs tokens, so the
cheapest clean text wins, and the browser is used where nothing else can see the page.

Probing the hosts of three finished Runs (2026-10-17) fixed four rules the cascade must follow:

- **A Twin is accepted only when the response is `text/markdown`** (or plain text from a raw file
  host). `cloud.google.com` answers `<page>.md` with `200` and HTML.
- **The fetcher follows `<meta http-equiv="refresh">`**, which HTTP clients do not: NVIDIA NIM
  pages are 98-byte redirect stubs.
- **A `403` to a plain client is the signal for the browser step**, not a failure: Milvus refuses
  `httpx` with a browser User-Agent, and only Crawl4AI sees it.
- **A page without any Twin is the common case for a whole ecosystem**: NVIDIA, vLLM, Kubernetes,
  A2A and Python's documentation have none, so Trafilatura is the main path there, not a fallback.

## Considered Options

- **Crawl4AI for everything.** Rejected: a browser per page, larger output, per-site tuning to
  remove overlays.
- **LLM-based extraction** (Crawl4AI or Firecrawl strategies). Rejected: it spends tokens on every
  page and paraphrases, and facts are checked against verbatim text.
