# 11: `tag add` and a full `status`

**What to build:** `tag add <tag> <url>` appends a Tag row for that Source, and `tag add <tag> --prefix <url-prefix>` for every Source whose URL starts with the prefix, skipping rows that exist, through the Store's commit point so the Index follows. `status` reports from the Index: Versions, Sources, Tags with counts, oldest and newest `fetched_at`, Rechecks logged by outcome, unknown hosts seen (publisher equal to the host), and the Store's size on disk.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `tag add nvidia --prefix https://docs.nvidia.com/` tags every Source under that prefix once; rerunning adds nothing; without `--prefix` only the exact URL is tagged
- [ ] `status` on the fixture Store prints every figure above; `--json` returns them as an object
- [ ] `status` on a Store without an Index builds it first
