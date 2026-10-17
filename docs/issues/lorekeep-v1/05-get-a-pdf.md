# 05: `get` reads a PDF

**What to build:** When the response's media type is `application/pdf` — whatever the URL ends in — `get` converts the file to Markdown with MarkItDown (installed with its `pdf` extra), stores the file as `<stem>.orig.pdf`, and records `converter: markitdown <version>`.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] the `exam-guide.pdf` fixture (served under a URL without `.pdf`) produces a Version with `converter: markitdown <version>`, a body containing "Prompt caching reduces cost and latency", and an `.orig.pdf` Original with `original.mediatype: application/pdf`
- [ ] a `text/html` response is never handed to MarkItDown; a media type that is neither HTML, Markdown nor PDF is reported as unsupported, exits non-zero, stores nothing
