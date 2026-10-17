# 04: `get` reads documents

**What to build:** When the response's media type is PDF or an Office type — whatever the URL ends in — `get` converts the file to Markdown with MarkItDown (installed with its `pdf` extra), stores the file as the Original with its media type's extension, and records `converter: markitdown <version>`. `--layout` routes a PDF through Docling instead, which is the optional extra `lorekeep[layout]`: when it is absent, `get --layout` exits non-zero naming the extra and stores nothing.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] the `exam-guide.pdf` fixture (served under a URL without `.pdf`) produces a Version with `converter: markitdown <version>`, a body containing "Prompt caching reduces cost and latency", and an `.orig.pdf` Original
- [ ] `--layout` on the same fixture routes through Docling behind the seam (the fake records the call) and records `converter: docling <version>`
- [ ] with Docling absent (fake reports "not installed"), `get --layout` exits non-zero with the extra's name and stores nothing
- [ ] a `text/html` response is never handed to MarkItDown
