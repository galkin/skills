# 12: Six workers on one Store

**What to build:** A test drives a process pool of six workers calling `get` (fresh and repeated URLs, some forcing `--max-age 0`) and `add` against one Store, each worker building its own fake edges from the fixture paths, then asserts: one file per Version, no temporary files left, `tags.csv` and `checks.csv` intact with one header and no interleaved rows, and an Index whose counts equal a fresh `index` rebuild. Six workers each running `search` against a Store with no Index produce one rebuild; `get` and `add` never rebuild. Whatever the test exposes in the locking, atomic writes or SQLite busy handling is fixed here.

**Blocked by:** 07, 14

**Status:** done

- [x] the pool test passes 20 runs in a row
- [x] no `.tmp-*` file remains; every Version file parses
- [x] CSV files have exactly one header and every row has the right number of columns; `tags.csv` has no duplicate `(url, tag)` pair although every worker tags every URL it gets
- [x] `index` rebuilt from the files reports the same counts as the incrementally updated Index
- [x] with the Index deleted before a pool of six `search` calls starts, exactly one rebuild is logged; a pool of `get`s against a missing Index logs none

## Comments

2026-10-17 — Decisions made while building this ticket. (1) The pool test is `tests/test_workers.py`: six `spawn` children, each building its own `FakeTransport`/`FakeFetcher`/`FakeRunner` from fixture paths, run eight pages twice in a seeded order (Twins, the Foundry redirect chain, three termidy lessons, the NIM stub, a page with relative links; the `.noisy`/`.changed` variants are left out so repeated fetches receive the same bytes), every third call with `--max-age 0`, then `add` a note of their own and one note shared by all; three workers share a Tag so `(url, tag)` deduplication is exercised across processes. The test passed 20 runs in a row (and a loop of 20 full `pytest` runs of the file) without a change to the locking, the atomic writes or the SQLite busy handling: nothing was exposed. (2) "A rebuild is logged" is one line on stderr, `lorekeep: note: the Index was missing or stale and was rebuilt (N Versions, M Sections)`, printed by `index.report` when `ensure()` rebuilt; the `index` command passes `note=False` because it prints its own count on stdout. Six concurrent `search`es against a deleted Index produce exactly one such line between them; six `get`s against a missing Index produce none and leave no `sources.db`. (3) Ticket 01's seam test (`status` on an empty Store with the three fakes) asserted an empty stderr; it now allows that one note, since `status` builds the missing Index like every reader.
