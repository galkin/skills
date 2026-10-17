# 11: `tag add` and a full `status`

**What to build:** `tag add <tag> <url-or-prefix>` appends Tag rows for every Source whose URL matches (exact or prefix), skipping rows that exist, and updates the Index. `status` reports from the Index: Versions, Sources, Tags with counts, oldest and newest `fetched_at`, Rechecks logged, unknown hosts seen (publisher equal to the host), and the Store's size on disk.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `tag add nvidia https://docs.nvidia.com/` tags every Source under that prefix once; rerunning adds nothing
- [ ] `status` on the fixture Store prints every figure above; `--json` returns them as an object
- [ ] `status` on a Store without an Index builds it first
