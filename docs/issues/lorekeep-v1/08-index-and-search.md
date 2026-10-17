# 08: `index` builds the Index and `search` answers from it

**What to build:** `index` rebuilds `sources.db` (WAL mode, busy timeout) from the Store: `versions` from every frontmatter, `tags`, `checks` and `citations` from their CSVs (empty when absent), `sections` cut at headings and again at 4 KB on paragraph boundaries without splitting code fences, each with its heading path and the line its heading sits on, and an FTS5 external-content table with `porter unicode61`. `search <query>` prints up to 5 (`--limit`) lines `file:line | heading path | snippet`, ranked by `bm25`, scoped to the Run's Tag (everything when no Tag is set), and ends with `+N matches under other tags (--all)` unless the scope is already everything; `--all`, `--tag` repeated, `--publisher`, `--authority`, `--json`; `--exact` is a case-sensitive substring match over the Sections' text. The Index notification at the commit point (ticket 02) is filled in here, so every command that commits updates the Index incrementally, and ticket 02's lookup uses the Index when it exists; any command that reads the Index compares the count of `.md` files with the `versions` rows first and rebuilds under the Store lock on a mismatch or a missing file.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `index` on a Store of Versions written by the helper from the fixture bodies builds `sources.db`; deleting it and running `index` again gives identical row counts
- [ ] a page without headings is split into Sections of at most ~4 KB; a code fence is never cut; every Section's `line` points at its heading (or the first line of its slice) in the file
- [ ] `search 'prompt caching'` returns ranked lines with `file:line`, heading path and a snippet; `caching` matches `cached`
- [ ] default scope is the Run's Tag; the final line reports the count under other Tags; `--all` includes them and drops the line; without `LOREKEEP_TAG` the scope is everything and no line is printed; `--tag`, `--publisher`, `--authority` filter
- [ ] `--exact 'cache_control'` matches only Sections containing that exact string and not a Section containing "cache control"
- [ ] `--json` returns the same results as objects plus `other_tags`
- [ ] after `add`, the new Version is searchable without running `index`; the commit function's only change is the notification
- [ ] a file copied into the Store by hand is searchable after the next `search`; the rebuild happens under `.lorekeep.lock`
- [ ] `citations.csv` with and without `as_of` is ingested; a malformed row is reported with its line number
