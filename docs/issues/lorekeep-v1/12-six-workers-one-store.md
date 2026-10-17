# 12: Six workers on one Store

**What to build:** A test drives a process pool of six workers calling `get` (fresh and repeated URLs, some forcing `--max-age 0`) and `add` against one Store with the fake edges, then asserts: one file per Version, no temporary files left, `tags.csv` and `checks.csv` intact with one header and no interleaved rows, and an Index whose counts equal a fresh `index` rebuild. Whatever the test exposes in the locking, atomic writes or SQLite busy handling is fixed here.

**Blocked by:** 06, 08

**Status:** ready-for-agent

- [ ] the pool test passes 20 runs in a row
- [ ] no `.tmp-*` file remains; every Version file parses
- [ ] CSV files have exactly one header and every row has the right number of columns
- [ ] `index` rebuilt from the files reports the same counts as the incrementally updated Index
