# 14: The Index follows every commit, and notices when it is stale

**What to build:** The Index notification at the commit point (ticket 02) is filled in: a committed Version, Tag row or check row is inserted into `sources.db` in one small transaction while the commit holds the lock, so `get`, `add`, `recheck` and `tag` leave the Index current without `index`. Every command that reads the Index first compares, without the lock, the `.md` file count and the size and mtime of `tags.csv`, `checks.csv` and `citations.csv` with the `meta` table; only on a mismatch or a missing file does it take the lock, compare again and rebuild. `citations.csv` is ingested at build (`work_id, url[, as_of]`; `url` normalised and Twin-reduced; `as_of` an ISO 8601 date or timestamp; a malformed row reported with its line number).

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] after `add`, the new Version is searchable without running `index`; the commit function's only change is the notification
- [ ] a file copied into the Store by hand is searchable after the next `search`; the rebuild takes `.lorekeep.lock`; a `search` on a current Index takes no lock (a test holds the lock and runs `search`)
- [ ] rewriting `citations.csv` makes the next `search` or `recheck --citations` rebuild and see the new rows; a row citing the `.md` Twin address joins the Version stored under the page URL; `as_of` with and without a time part is accepted; a malformed row is reported with its line number
- [ ] `index` rebuilt from the files reports the same counts as the incrementally updated Index after a sequence of `add`, `tag add` and aged `get`s
