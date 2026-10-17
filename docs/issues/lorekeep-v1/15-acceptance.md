# 15: Acceptance of v1 and the live smoke test

**What to build:** Nothing. This ticket records the acceptance pass over `main` at `14d89bf`: the spec and tickets 01–14 compared with the code and the tests, the gate rerun, the smoke script run against the live network and the real bucket, and the owner's working scenario run in a throw-away Store. The open items at the end are small and listed for the owner to decide.

**Blocked by:** 01–14 (all done)

**Status:** done

- [x] gate on a fresh `uv sync`: `pytest` 214 passed, `ruff check`, `ruff format --check`, `pyright` 0 errors
- [x] every Implementation Decision of the spec was read against the module that owns it (`store`, `urls`, `twins`, `history`, `project`, `cascade/*`, `recheck`, `index`, `sections`, `package`, `commands/*`, `cli`, `edges`, `http`, `provenance`, `frontmatter`, `skill/SKILL.md`); no decision is missing or contradicted — the deviations found are the three notes below
- [x] `scripts/smoke.py --bucket agentic-system-design-sources` with `uv sync --extra browser`: Twin `ok` (`md-twin`), static page `ok` (`trafilatura 2.3.1`); the browser step and the restore step did not run, for reasons outside lorekeep (see the comments)
- [x] the browser step exercised live through a `lorekeep.toml` rule `browser = true` with `cut`: `converter: trafilatura 2.3.1 via crawl4ai 0.9.5`, `.orig.html` stored, `~/.crawl4ai` unchanged before and after
- [x] the working scenario in an empty Store: `get` (`stored`), `get` of the `.md` address (`fresh`, same file, no alias row since the Twin address reduces to the page), `get --fresh` (`unchanged`, status `200`, one `checks.csv` row), `search 'cache_control' --exact` (5 `file:line` hits, `+0` line), `search` by words, `status`, `recheck --dry-run`, `backup --dry-run` against the real bucket (rsync lists only the Version; the six growing files, the Index, the lock are excluded as the real `gcloud` reads the regex), `recheck` and `get --fresh` of a browser Version (`skipped`, warning)

## Comments

2026-10-17 — Acceptance by the spec's author (a review agent in the owner's session), after the coordinator handed over `14d89bf`.

**Verdict:** accepted. The code implements the spec as written, the tickets' Comments document every decision taken under it, and the two document changes made on top of the spec (ADR 0007 on the age of a Version, `requires-python >=3.12,<3.14`) match what the spec already said.

**Smoke test, what did not run and why.**

1. *Browser page.* The script expects `https://milvus.io/docs/overview.md` to answer `403` to a plain client and so reach the browser. Today it answers `200` with HTML, so `get` stores a `trafilatura` Version and the script prints `FAIL browser page`. That is the live world moving, not lorekeep. Suggested fix, not applied: let the script write a `[[hosts]]` rule with `browser = true` for one host into its temporary `lorekeep.toml`, so the browser step is exercised whatever the host answers that day (done by hand here, see the fourth checkbox).
2. *Restore.* `gs://agentic-system-design-sources` holds no object yet — no `backup` has run against the real Store — so `restore --generation` had nothing to restore and the `#N` form stays unproven live. It will be proven by the first `lorekeep backup` from `~/orca/sources/agentic-system.design/` followed by the smoke script; writing to the bucket is the owner's call.

**Notes for the owner (small; none blocks acceptance).**

- `add --json` of a text already stored prints `outcome: unchanged` (the Version's own fields, `verified_at` from `checks.csv`); the spec and `SKILL.md` say `add --json` prints `outcome: stored`. Either the one sentence in `SKILL.md` (and the spec's) says "`stored`, or `unchanged` when the same text was added before", or `add` always says `stored`. The test `test_add_json_of_a_version_already_stored_is_unchanged_with_its_verified_at` pins the current behaviour.
- A host rule with `browser = true` sends `get` straight to the browser and skips the Twin step as well as the page step. The spec lists the Twin first "for a host whose rule names one" and the browser "when the host rule says `browser = true`" without saying which wins when a rule has both. The code's reading (browser wins) is sensible; one sentence in the spec's cascade would close it.
- Ticket 09's Comment says `--dry-run` prints `ask  <address>` / `skip <url>`; the code and `SKILL.md` print `would ask <address>` / `skipped <url>: <reason>`. The comment is stale; the code and the skill agree.
- A Recheck sends `original.url`, which `get` stored with its query percent-decoded (`?accept=text/markdown`), while the first fetch sent the address as given. Both name the same resource and Microsoft Learn answered the decoded form in the measurements; recorded here only because the spec's "what goes on the wire is the address as given" is read slightly more loosely on a Recheck.
- `platform.claude.com` serves its Twin without `ETag` or `Last-Modified`, so every Recheck of an Anthropic page is a full download compared by bytes (`unchanged` with status `200`, never `304`). Expected under ADR 0007; worth knowing when reading `checks.csv`.

**Next for the owner:** create `~/orca/sources/agentic-system.design/` with its `lorekeep.toml` as the README says, run the first `lorekeep backup`, then `scripts/smoke.py` again to prove `restore --generation`; install the skill into the pipeline repository with `lorekeep skill --install` and update `skills-lock.json`.
