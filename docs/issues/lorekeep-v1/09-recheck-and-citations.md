# 09: `recheck` asks publishers what changed

**What to build:** `recheck` walks the latest Version of every Source in scope (`--tag` repeated, `--publisher`, `--prefix <url-prefix>`; default the Run's Tag, everything when no Tag is set), performs the same conditional request and two-step comparison as `get` through the same cascade with the same outcomes, appends to `checks.csv`, stores changed pages as new Versions, and prints counts per outcome; `owner:` Sources and Versions whose `converter` says `via crawl4ai` are counted as `skipped` and asked nothing. `recheck --citations` is a pure report that makes no request and needs no Tag: it prints `work_id, url, old sha8 → new sha8` for every work whose cited Source has a Version newer than the one the work was written from (`as_of` in `citations.csv`, else the oldest Version). `--dry-run` lists what would be asked and asks nothing.

**Blocked by:** 07, 14

**Status:** ready-for-agent

- [ ] over a Store of real `get`s aged by the helper — the Anthropic Twin (served `304`), the `ethical-ai` lesson served again unchanged, the `coordinator-and-subagents` lesson served as `.changed`, the `effective-prompts` lesson now answering `404` — plus one `owner:` Source and one Version written by the fixture helper with `via crawl4ai` in its `converter`: `recheck` appends four rows, creates one new Version and prints 1 changed / 2 unchanged / 1 gone / 2 skipped
- [ ] `--citations` makes no request and works without `LOREKEEP_TAG`
- [ ] scope flags limit which Sources are asked; the fake transport records exactly those requests; without `LOREKEEP_TAG` every web Source is asked
- [ ] `--citations` lists only works whose cited Source changed after `as_of`; without `as_of` it measures against the oldest Version
- [ ] `--dry-run` asks nothing and lists what would be asked
