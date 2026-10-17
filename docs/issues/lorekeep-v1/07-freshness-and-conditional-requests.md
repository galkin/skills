# 07: Freshness window and conditional requests

**What to build:** A stored Version whose age — counted from the later of its `fetched_at` and its last `unchanged` row in `checks.csv` — is under the freshness window is returned without a request. Older, `get` sends a conditional request (`If-None-Match` / `If-Modified-Since` from the latest Version's frontmatter) to `original.url` and records one of four outcomes in `checks.csv` (`url, checked_at, result, status, sha256`): `304`, or `200` with the same received bytes, or `200` with different bytes but the same Markdown after conversion by the Version's step → `unchanged`, latest Version returned; different bytes and different Markdown → `changed`, a new Version beside the old, new path returned; `404`/`410` on a Twin address → the cascade goes on with the page URL and stores what it finds as `changed`, or `gone` when the page is gone too; `404`/`410` on a page address → `gone`, a warning, latest Version returned; any other status → `error` with that status code; a transport exception → `error` with the exception's class name; both with a warning and the latest Version returned. Without any stored Version, `gone` and `error` exit non-zero. The window is `freshness_days` from `lorekeep.toml`, overridden per call by `--max-age <days>`; `--fresh` means `--max-age 0`. The `checks.csv` append goes through the commit point.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] with a Version 10 days old (written by the helper) and the default window, `get` makes no request; with `--max-age 5` it makes one request carrying `If-None-Match` from the frontmatter
- [ ] a Version 40 days old with an `unchanged` row 10 days old: no request
- [ ] the `anthropic-prompt-caching.304` fixture: no new file, one `unchanged` row with status `304`, latest path printed
- [ ] `200` with the same bytes: no conversion, no new file, one `unchanged` row
- [ ] the `termidy-coordinator-and-subagents.noisy` fixture served after the plain one: different bytes, identical Markdown, no new file, one `unchanged` row
- [ ] `200` with different bytes and different Markdown: a second Version with the same `<host>--<path>` prefix and a new sha8, its own Original, one `changed` row, new path printed; the old files untouched
- [ ] `404` with a stored Version: one `gone` row, a warning, the old path printed, exit 0; `404` without a stored Version: exit non-zero
- [ ] a Twin Version whose `.md` address now answers `404` while the page answers HTML: a new Version by Trafilatura, one `changed` row; when the page answers `404` too, one `gone` row and the old path
- [ ] a `403` or `503` on a stored Version: one `error` row with that status, the old path printed, exit 0
- [ ] the `timeout` fixture with a stored Version: one `error` row with status `ReadTimeout`, the old path printed, exit 0
- [ ] `--fresh` behaves as `--max-age 0`; `checks.csv` keeps one header after concurrent appends
