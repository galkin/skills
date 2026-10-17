# 09: `recheck` asks publishers what changed

**What to build:** `recheck` walks the latest Version of every Source in scope (`--tag`, `--publisher`, a URL prefix, default the Run's Tag), performs the same conditional request or hash comparison as `get`, appends to `checks.csv`, stores changed pages as new Versions, updates the Index, and prints a summary. `recheck --citations` prints `work_id, url, old sha8 → new sha8` for every work whose cited Source has a Version newer than the one the work was written from (`as_of` in `citations.csv`, else the oldest Version).

**Blocked by:** 06, 08

**Status:** ready-for-agent

- [ ] over a Store with three Sources (fixtures: `304`, same hash, changed), `recheck` appends three rows, creates one new Version and prints 1 changed / 2 unchanged
- [ ] scope flags limit which Sources are asked; the fake transport records exactly those requests
- [ ] `--citations` lists only works whose cited Source changed after `as_of`; without `as_of` it measures against the oldest Version
- [ ] `--dry-run` asks nothing and lists what would be asked
