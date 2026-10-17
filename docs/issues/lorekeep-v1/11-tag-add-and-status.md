# 11: `tag add` and a full `status`

**What to build:** `tag add <tag> <url>` appends a Tag row for that Source, and `tag add <tag> --prefix <url-prefix>` for every Source whose URL starts with the prefix, skipping rows that exist, through the commit point so the Index follows. `status` reports from the Index, in text and as the spec's `--json` object: Versions, Sources, Tags with counts, oldest and newest `fetched_at`, Rechecks logged by outcome, unknown hosts seen (publisher equal to the host), and the Store's size on disk.

**Blocked by:** 14

**Status:** done

- [x] `tag add nvidia --prefix https://docs.nvidia.com/` tags every Source under that prefix once; rerunning adds nothing; without `--prefix` only the exact URL is tagged; a URL no Source has exits non-zero
- [x] `status` on a Store written by the helper with a `checks.csv` of mixed outcomes prints every figure above; `--json` returns them as one object in the spec's shape
- [x] `status` on a Store without an Index builds it first

## Comments

2026-10-17 — Decisions made while building this ticket. (1) `tag add <tag> <url>` resolves the url the way `get` would (normalised, Twin-reduced, through `aliases.csv`) and tags the Source's stored `url`; `--prefix` is compared verbatim with stored `url`s (so `--prefix owner:` reaches owner's Sources). A prefix no Source has also exits 1 and writes nothing, like an unknown url, so a mistyped prefix is not a silent success; giving both a url and `--prefix`, or neither, is a usage error (exit 2). Both first read the Index after `index.ensure`; revised 2026-10-17 (review fix A8): they read a current Index without any lock and scan the Store's files otherwise, never rebuilding, so the only lock `tag add` takes is its commit's (the spec: the lock is never taken twice by one command). The rows go through `commit`, which drops rows already present and notifies the Index. (2) `status` calls `index.ensure` and reads `index.summary`: `tags` counts distinct Sources per Tag; `checks` counts `checks.csv` rows per `result`, always with all four keys; `unknown_hosts` are the hosts of Versions whose `publisher` equals their url's host (owner's Sources have none); `oldest_fetched_at`/`newest_fetched_at` are `null` on an empty Store; `bytes` is the sum of the sizes of every file in the Store folder, `sources.db` included, measured after the Index is built. The text output keeps ticket 01's bucket, freshness window and host-rule lines after the new figures; `cmd_status` moved from `cli.py` to `commands/status.py`.
