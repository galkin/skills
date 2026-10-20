# 02: `search` over Readings, `status` counts them, `backup` leaves the cache

**What to build:** The Index's `sections` rows come from the Reading where one exists (else the Version) and name the file they came from, so `file:line` points into the file `get` returns; the Index is rebuilt lazily when Readings change (`SCHEMA_VERSION` bump, and the Index fingerprint covers `.cache/readings/`); `status` prints `Readings: N of M Versions, K rules`; `backup` never copies `.cache/`; `recheck` and `citations` keep working on Versions. Decisions: `spec.md` › Readings.

**Blocked by:** 01

**Status:** done

- [x] over the Fern Twin fixture with the banner rule, `search 'llms.txt'` prints `no matches` and `search 'execution rails'` prints the Reading's path and a line number that holds the match in the Reading
- [x] a Version without a Reading is searched as today, same path and line
- [x] after a rule is added, the next `search` rebuilds the Index (note line) and its hits point into the new Readings
- [x] `status` prints the Readings line; `status --json` has `readings` and `rules`
- [x] `backup --dry-run` lists no path under `.cache/`; the fake `gcloud` receives an exclude for it
- [x] `recheck --citations` matches a cited `url` to the Version as before; a changed page gets a new Version and its Reading is built on the next read
- [x] `references/owner.md` says `.cache/` is never backed up and is rebuilt from the Versions; the flag test passes

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v13-02`).** Tests in
`tests/test_readings_index.py`, one per criterion (two for the third), each naming its fixture.

- **The Index over Readings** (`index.py`, `SCHEMA_VERSION` 6). `sections.source` is the file a
  Section was read from, relative to the Store (`.cache/readings/<stem>.md` or `<stem>.md`), and
  `search` prints and returns it as `file`; `sections.file` stays the Version, which the `latest`
  view joins on. `versions.reading` names the Reading (`NULL` without one), which `status`
  counts. A rebuild (`index.rebuild`/`ensure`, now taking the `Project`) first builds every
  missing or stale Reading inside the Store lock it already holds (`readings.ensure_held`, the
  lock-free twin of `ensure`), then indexes; guard warnings of Readings built then go out with the
  rebuild's warnings, as `read` prints them.
- **Staleness.** `meta` records `reading_rules`, the hash of the Project's whole rule set
  (`readings.rules_hash`), and the fingerprint gains `readings:files` and `readings:mtime` (the
  count of `.cache/readings/*.md` and the folder's mtime, which every rename into it or removal
  changes). `index.ensure` compares the rule hash; `index.current` (lookups that never touch
  Sections) does not, so a rules change costs a lookup nothing.
- **Where the ticket was loose.** It said the Index is rebuilt "when Readings change"; taken
  literally that is a full rebuild after every `get` of a page under a rule, because `get` builds
  the Reading after its commit notified the Index. So a Reading `readings.ensure` writes or removes
  is told to the Index (`index.notify_reading`, inside the same lock): the Version's Sections are
  re-read from the file it is now searched in and `meta` brought up to date when nothing else
  moved; `test_a_reading_built_by_get_reaches_a_current_index_without_a_rebuild` holds it. For the
  same reason `recheck` builds the Reading of a changed page right after storing it: a commit
  indexes the new Version from its own text, and with a current Index nothing else would replace
  that before the next `get`. The sixth criterion's "built on the next read" is therefore already
  true when `recheck` returns.
- **Backup.** `EXCLUDE` gains `\.cache/.*` (`readings.CACHE_DIR`); the dry-run test uses a fake
  `gcloud` that lists every file under the Store at any depth not matched by the exclude, so
  "lists nothing under `.cache/`" is measured on a listing, not on canned output. The data package
  and `status`'s size never saw `.cache/` (both read the flat folder only).
- **Tests, where they had to bend.** A hit's `line` is the Section's line holding the most query
  words as written; for `execution rails` the second hit is a table row with `Execution` alone, so
  the test asks that every hit's line holds `execution` and the first both words. Two Versions of a
  Source fetched in the same second tie on `fetched_at`, and `recheck --citations` then measures
  from whichever sorts first; the citations test ages the first Version, as `test_recheck.py` does.
- **Docs.** `references/owner.md`: `.cache/` is never backed up and is rebuilt from the Versions
  (`backup`), the rebuild builds Readings first (`index`), who builds Readings (`read`);
  `references/store.md`: `.cache/readings/` never backed up, the Index searches Readings and a
  rules change makes it stale. `SKILL.md`: the `status` text and JSON examples gain the Readings
  line and `readings`/`rules` (249 lines); "no rules" in `status --json` became "no host rules".
  Also kept true: `GLOSSARY.md` › Section (of the Reading, where there is one) and ADR 0004's
  exclusions (`.cache/`, amended in v1.3).
