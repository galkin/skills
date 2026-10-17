# 06: Freshness window and conditional requests

**What to build:** A stored Version younger than the freshness window is returned without a request. Older, `get` sends a conditional request (`If-None-Match` / `If-Modified-Since` from the latest Version); `304` or an unchanged Original hash appends an `unchanged` row to `checks.csv` and returns the latest Version; a changed Original stores a new Version beside the old and appends a `changed` row. The window is `freshness_days` from `lorekeep.toml`, overridden per call by `--max-age <days>`; `--fresh` means `--max-age 0`. The HTTP cache (`hishel`) lives in the user's cache directory, never in the Store.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] with a Version 10 days old and the default window, `get` makes no request; with `--max-age 5` it makes one conditional request
- [ ] `304` fixture: no new file, one `checks.csv` row `unchanged`, latest path printed
- [ ] `200` with the same Original hash: no new file, one `unchanged` row
- [ ] `200` with a different Original: a second Version file with the same stem and a new sha8, one `changed` row, new path printed
- [ ] `--fresh` behaves as `--max-age 0`
- [ ] for a Twin the comparison uses the Markdown hash (Original not stored)
- [ ] `checks.csv` rows have `url, checked_at, result, status, sha256` and the file keeps its header after concurrent appends
- [ ] the Store never contains an `hishel` cache
