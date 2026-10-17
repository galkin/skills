# 05: The skill a Run can follow

**What to build:** `SKILL.md` rewritten around what a Run does (`get`, `search`, `add`, `status`), under 250 lines, with the owner's commands moved to `references/owner.md` and `references/store.md` completed (Twin kinds, `canonical`, `requested_url`, `citations.csv` in full). Every sentence the v1.1 spec lists under "The skill" is present. Decisions: `spec.md` › The skill. Read the three worker reports in `reports/` first: their Friction sections are the bar.

**Blocked by:** 01, 02, 03, 04

**Status:** ready-for-agent

- [ ] `SKILL.md` is under 250 lines and documents only `get`, `search`, `add`, `status`; `references/owner.md` documents `recheck`, `tag add`, `backup`, `restore`, `index`, `skill`; the flag-vs-`--help` test covers both files and passes
- [ ] `SKILL.md` says, each in its own sentence or bullet: the returned `url` may differ from the address asked and is the one to cite; `requested_url` is in the JSON; fragments are dropped and the caller keeps them; `.md` and `?accept=` are Twins only under a host rule; parallel `get`s against one Store are safe; on exit 1 retry once only for `ReadTimeout`, `ConnectError` or a `5xx`, otherwise report the URL and the error line to the owner, never fetch another way, never `add` a page; the Tag is per guide, keep your own log of `get --json` lines; a `third-party` page the guide treats as primary is reported to the owner; the `authority` of a law or standard published by its issuer is `primary`; `search` takes `-- '<query>'` for a query starting with `-`; `file:line` is the matching line; a `thin content` error means the page needs the browser
- [ ] `references/store.md` documents `citations.csv`: header `work_id,url[,as_of]` required, one row per `(work_id, url)`, `as_of` an ISO date (read as the end of that day, UTC) or timestamp, `url` normalised, Twin-reduced and taken through `aliases.csv`, a cited `url` with no Version is a warning of `recheck --citations`; and the `canonical` field, the `requested_url` JSON field, the `raw-twin` and `verbatim` converters
- [ ] the JSON examples in `SKILL.md` are produced by running the commands against the fixtures (not typed), so the fields match the parser
- [ ] `README.md`'s "For agents" section links `references/owner.md`
