# 08: `index` builds the Index and `search` answers from it

**What to build:** `index` rebuilds `sources.db` (WAL mode) from the Store: `versions` from every frontmatter, `tags`, `checks` and `citations` from their CSVs (empty when absent), `sections` cut at headings and again at 4 KB on paragraph boundaries without splitting code fences, and an FTS5 external-content table with `porter unicode61`. `search <query>` prints up to 5 (`--limit`) lines `file | heading path | snippet`, ranked by `bm25`, scoped to the Run's Tag, and always ends with `+N matches under other tags (--all)`; `--all`, `--tag a,b`, `--publisher`, `--authority`, `--exact`, `--json`. `get` and `add` update the Index incrementally after writing a Version or a Tag; a missing or stale Index is rebuilt on first use.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `index` on a Store of the fixture Versions builds `sources.db`; deleting it and running `index` again gives identical row counts
- [ ] a page without headings is split into Sections of at most ~4 KB; a code fence is never cut
- [ ] `search 'prompt caching'` returns ranked lines with file, heading path and a snippet; `caching` matches `cached`
- [ ] default scope is the Run's Tag; the final line reports the count under other Tags; `--all` includes them; `--tag`, `--publisher`, `--authority` filter; `--exact 'cache_control'` matches the phrase
- [ ] `--json` returns the same results as objects plus `other_tags`
- [ ] after `get` or `add`, the new Version is searchable without running `index`
- [ ] `citations.csv` with and without `as_of` is ingested; a malformed row is reported with its line number
