# 06: Freshness window and conditional requests

**What to build:** A stored Version younger than the freshness window is returned without a request. Older, `get` sends a conditional request (`If-None-Match` / `If-Modified-Since` from the latest Version's frontmatter) and records one of four outcomes in `checks.csv`: `304`, or `200` with the same received bytes, or `200` with different bytes but the same Markdown after conversion → `unchanged`, latest Version returned; different bytes and different Markdown → `changed`, a new Version beside the old, new path returned; `404`/`410` → `gone`, a warning on stderr, latest Version returned; connection failure or timeout → `error`, a warning, latest Version returned. Without any stored Version, `gone` and `error` exit non-zero. The window is `freshness_days` from `lorekeep.toml`, overridden per call by `--max-age <days>`; `--fresh` means `--max-age 0`. There is no HTTP cache library: the conditional requests are lorekeep's own.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] with a Version 10 days old and the default window, `get` makes no request; with `--max-age 5` it makes one request carrying `If-None-Match` from the frontmatter
- [ ] the `anthropic-prompt-caching.304` fixture: no new file, one `checks.csv` row `unchanged` with status `304`, latest path printed
- [ ] `200` with the same bytes: no conversion, no new file, one `unchanged` row
- [ ] `200` with different bytes whose Markdown is identical (a fixture with a changed per-request id in a `<script>` tag): no new file, one `unchanged` row
- [ ] `200` with different bytes and different Markdown: a second Version file with the same stem and a new sha8, one `changed` row, new path printed; the old file is untouched
- [ ] `404` with a stored Version: one `gone` row, a warning, the old path printed, exit 0; `404` without a stored Version: exit non-zero
- [ ] a transport error with a stored Version: one `error` row with its label, the old path printed, exit 0
- [ ] `--fresh` behaves as `--max-age 0`
- [ ] `checks.csv` rows have `url, checked_at, result, status, sha256` and the file keeps its header after concurrent appends
