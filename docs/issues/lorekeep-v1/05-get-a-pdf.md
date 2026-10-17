# 05: `get` reads a PDF

**What to build:** When the response's media type is `application/pdf` — whatever the URL ends in — `get` converts the file to Markdown with MarkItDown (installed with its `pdf` extra), stores the file as `<stem>.orig.pdf`, and records `converter: markitdown <version>`.

**Blocked by:** 03

**Status:** done

- [x] the `exam-guide.pdf` fixture (served under a URL without `.pdf`) produces a Version with `converter: markitdown <version>`, a body containing "Prompt caching reduces cost and latency", and an `.orig.pdf` Original with `original.mediatype: application/pdf`
- [x] a `text/html` response is never handed to MarkItDown; a media type this step does not take is left to the other steps, and when no step takes it `get` reports it as unsupported, exits non-zero, stores nothing

## Comments

2026-10-17 — Decisions made while building this ticket. (1) The page URL is fetched once, by one
`PageStep` (`cascade/page.py`) placed after the Twin step: it sends the address as given, and the
response's media type picks a converter from `CONVERTERS` (here only `application/pdf` →
`cascade/pdf.py`); a media type with no converter is a `Fallthrough("unsupported media type …")`,
so `get` exits 1 with `nothing stored for <url>: … unsupported media type …`. Ticket 04 is meant to
add `text/html` to `CONVERTERS` (and its meta-refresh and canonical handling to the page fetch)
rather than add a second step that fetches the page again. `Converted` lives in `cascade/step.py`.
(2) MarkItDown falls back to its HTML or plain-text converter when a stream labelled PDF is not
one, so bytes that do not start with `%PDF-` are refused ("not a PDF") and nothing is stored; a
PDF that yields no text is "no content". The Markdown is MarkItDown's output stripped, with one
trailing newline; `title` is MarkItDown's when it gives one. (3) Two ticket 03 tests asserted that
nothing followed a Twin answered with HTML; they now expect the page URL requested next (a `404`
miss in those fixture sets), which holds after ticket 04 too.
