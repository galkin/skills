# 07: Freshness window and conditional requests

**What to build:** A stored Version whose age — counted from the later of its `fetched_at` and its last `checks.csv` row of any result — is under the freshness window is returned without a request. Older, `get` sends a conditional request (`If-None-Match` / `If-Modified-Since` from the latest Version's frontmatter) to `original.url` and records one of four outcomes in `checks.csv` (`url, checked_at, result, status, sha256`): `304`, or `200` with the same received bytes, or `200` with different bytes but the same Markdown after conversion by the Version's step → `unchanged`, latest Version returned; different bytes and different Markdown → `changed`, a new Version beside the old, new path returned; `404`/`410` → `gone`, a warning, latest Version returned; a `200` whose media type fails the Version's step (a Twin address answering HTML) → `error` with status `200`, nothing stored; any other status, `403` and `429` included (the browser is never used for a comparison) → `error` with that status code; a transport exception → `error` with the exception's class name; both with a warning and the latest Version returned. Without any stored Version, `gone` and `error` exit non-zero. The window is `freshness_days` from `lorekeep.toml`, overridden per call by `--max-age <days>`; `--fresh` means `--max-age 0`. A Version whose `converter` says `via crawl4ai` is never rechecked by `get`: it is returned with a warning and `outcome: skipped`. The `checks.csv` append goes through the commit point. Old Versions in tests come from a real `get` aged by ticket 01's helper.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] with a Version 10 days old (a real `get`, then aged by the helper) and the default window, `get` makes no request; with `--max-age 5` it makes one request carrying `If-None-Match` from the frontmatter
- [ ] a Version 40 days old with an `unchanged` row 10 days old: no request; the same with a `gone` row 10 days old: no request
- [ ] the `anthropic-prompt-caching.304` fixture: no new file, one `unchanged` row with status `304`, latest path printed
- [ ] `200` with the same bytes: no conversion, no new file, one `unchanged` row
- [ ] the `termidy-coordinator-and-subagents.noisy` fixture served after the plain one: different bytes, identical Markdown, no new file, one `unchanged` row
- [ ] `200` with different bytes and different Markdown: a second Version with the same `<host>--<path>` prefix and a new sha8, its own Original, one `changed` row, new path printed; the old files untouched
- [ ] `404` with a stored Version: one `gone` row, a warning, the old path printed, exit 0; `404` without a stored Version: exit non-zero
- [ ] a Twin Version whose `.md` address now answers `404`: one `gone` row and the old path, no request to the page URL
- [ ] a Twin Version whose `.md` address now answers `200 text/html` (the `google-md-answers-html` fixture against a helper-written Twin Version): one `error` row with status `200`, nothing stored, old path
- [ ] a page served A, then `.changed`, then A again with `--max-age 0` each time: two files, three rows (`stored`-less: `changed`, `changed`), and the lookup returns A's file after the third call
- [ ] a `503` or a `403` on a stored Version: one `error` row with that status, no fetcher call, the old path printed, exit 0
- [ ] a Version written by the fixture helper with `converter: trafilatura 2.0 via crawl4ai 0.9`, aged past the window: no request, old path, a warning, `--json` says `skipped`
- [ ] the `timeout` fixture with a stored Version: one `error` row with status `ReadTimeout`, the old path printed, exit 0
- [ ] `--fresh` behaves as `--max-age 0`; `checks.csv` keeps one header after concurrent appends
