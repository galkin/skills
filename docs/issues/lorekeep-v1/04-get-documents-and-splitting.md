# 04: `get` reads documents and splits long texts

**What to build:** `get` converts PDF and Office files to Markdown with MarkItDown (`--layout` switches a PDF to Docling), stores the file as the Original with its media type's extension, and cuts any Markdown body over the configured size (default 150 KB) into parts at `Article N` / `Статья N` / `ANNEX` / top-level headings, each part a Version with `part_of` and `part`, plus an index part listing them.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] a PDF fixture produces a Version with `converter: markitdown <version>` and an `.orig.pdf` Original
- [ ] `--layout` on the same PDF routes through Docling (behind the seam; the fake records the call)
- [ ] the long legal-text fixture yields one Version per Article plus an index Version; every part's frontmatter has `part_of` = the document's URL and `part` = its heading
- [ ] `get` of a part's parent URL returns the index part's path
- [ ] a body under the size limit is never split
