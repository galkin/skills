# 08: `index` builds the Index and `search` answers from it

**What to build:** `index` rebuilds `sources.db` (WAL mode, busy timeout) from the Store: `versions` from every frontmatter, `tags`, `checks` and `aliases` from their CSVs (empty when absent), a `meta` table recording the file count and each CSV's size and mtime at build time, `sections` cut at headings and again at 4 KB on paragraph boundaries without splitting code fences, each with its heading path and the line its heading sits on, and an FTS5 external-content table with `porter unicode61`. `search <query>` prints up to 5 (`--limit`) lines `file:line | heading path | snippet`, ranked by `bm25`, scoped to the Run's Tag (everything when no Tag is set), and ends with `+N matches under other tags (--all)` — N distinct Versions — unless the scope is already everything; `--all`, `--tag` repeated, `--publisher`, `--authority`, `--json` in the spec's shape; `--exact` is a case-sensitive substring match over the Sections' text. Ticket 02's lookup uses the Index when the file exists, without taking the lock. In this ticket the Index is built only by `index` (and by `search` when the file is missing, under the Store module's lock context manager); incremental updates, staleness and `citations.csv` ingest are ticket 14.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `index` on a Store of Versions written by ticket 01's fixture helper (Twin bodies as they are) builds `sources.db`; deleting it and running `index` again gives identical row counts
- [ ] a page without headings is split into Sections of at most ~4 KB; a code fence is never cut; every Section's `line` points at its heading (or the first line of its slice) in the file
- [ ] `search 'prompt caching'` returns ranked lines with `file:line`, heading path and a snippet; `caching` matches `cached`
- [ ] default scope is the Run's Tag; the final line counts Versions, not Sections, under other Tags (a page with three matching Sections counts once); `--all` includes them and drops the line; without `LOREKEEP_TAG` the scope is everything and no line is printed; `--tag`, `--publisher`, `--authority` filter
- [ ] `--exact 'cache_control'` matches only Sections containing that exact string and not a Section containing "cache control"
- [ ] `--json` prints `{results: [...], other_tags: N}` with the spec's fields
- [ ] `search` on a Store without `sources.db` builds it under `.lorekeep.lock` and answers; the `meta` table holds the file count and the CSV sizes and mtimes
