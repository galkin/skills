# 02: `search` over Readings, `status` counts them, `backup` leaves the cache

**What to build:** The Index's `sections` rows come from the Reading where one exists (else the Version) and name the file they came from, so `file:line` points into the file `get` returns; the Index is rebuilt lazily when Readings change (`SCHEMA_VERSION` bump, and the Index fingerprint covers `.cache/readings/`); `status` prints `Readings: N of M Versions, K rules`; `backup` never copies `.cache/`; `recheck` and `citations` keep working on Versions. Decisions: `spec.md` › Readings.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] over the Fern Twin fixture with the banner rule, `search 'llms.txt'` prints `no matches` and `search 'execution rails'` prints the Reading's path and a line number that holds the match in the Reading
- [ ] a Version without a Reading is searched as today, same path and line
- [ ] after a rule is added, the next `search` rebuilds the Index (note line) and its hits point into the new Readings
- [ ] `status` prints the Readings line; `status --json` has `readings` and `rules`
- [ ] `backup --dry-run` lists no path under `.cache/`; the fake `gcloud` receives an exclude for it
- [ ] `recheck --citations` matches a cited `url` to the Version as before; a changed page gets a new Version and its Reading is built on the next read
- [ ] `references/owner.md` says `.cache/` is never backed up and is rebuilt from the Versions; the flag test passes
