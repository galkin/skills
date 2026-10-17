# 09: `recheck` asks publishers what changed

**What to build:** `recheck` walks the latest Version of every Source in scope (`--tag` repeated, `--publisher`, `--prefix <url-prefix>`; default the Run's Tag, everything when no Tag is set; `owner:` Sources skipped), performs the same conditional request and two-step comparison as `get` through the same cascade, browser step included (a Version whose `converter` says `via crawl4ai` is asked through the fetcher), with the same outcomes, appends to `checks.csv`, stores changed pages as new Versions, and prints counts per outcome. `recheck --citations` prints `work_id, url, old sha8 → new sha8` for every work whose cited Source has a Version newer than the one the work was written from (`as_of` in `citations.csv`, else the oldest Version). `--dry-run` lists what would be asked and asks nothing.

**Blocked by:** 06, 07, 08

**Status:** ready-for-agent

- [ ] over a Store written by the helper from four fixtures and one `owner:` Source — the Anthropic Twin (served `304`), a termidy lesson served again unchanged, the same lesson served as `.changed`, and one whose URL now answers `404` — `recheck` appends four rows, creates one new Version and prints 1 changed / 2 unchanged / 1 gone; the `owner:` Source is skipped and not counted
- [ ] a Source whose latest Version came through the browser is asked through the fetcher fake, not the transport
- [ ] scope flags limit which Sources are asked; the fake transport records exactly those requests; without `LOREKEEP_TAG` every web Source is asked
- [ ] `--citations` lists only works whose cited Source changed after `as_of`; without `as_of` it measures against the oldest Version
- [ ] `--dry-run` asks nothing and lists what would be asked
