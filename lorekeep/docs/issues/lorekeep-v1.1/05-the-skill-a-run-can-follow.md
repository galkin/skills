# 05: The skill a Run can follow

**What to build:** `SKILL.md` rewritten around what a Run does (`get`, `search`, `add`, `status`), under 250 lines, with the owner's commands moved to `references/owner.md` and `references/store.md` completed (Twin kinds, `canonical`, `requested_url`, `citations.csv` in full). Every sentence the v1.1 spec lists under "The skill" is present. Decisions: `spec.md` › The skill. Read the three worker reports in `reports/` first: their Friction sections are the bar.

**Blocked by:** 01, 02, 03, 04

**Status:** done

- [x] `SKILL.md` is under 250 lines and documents only `get`, `search`, `add`, `status`; `references/owner.md` documents `recheck`, `tag add`, `backup`, `restore`, `index`, `skill`; the flag-vs-`--help` test covers both files and passes
- [x] `SKILL.md` says, each in its own sentence or bullet: the returned `url` may differ from the address asked and is the one to cite; `requested_url` is in the JSON; fragments are dropped and the caller keeps them; `.md` and `?accept=` are Twins only under a host rule; parallel `get`s against one Store are safe; on exit 1 retry once only for `ReadTimeout`, `ConnectError` or a `5xx`, otherwise report the URL and the error line to the owner, never fetch another way, never `add` a page; the Tag is per guide, keep your own log of `get --json` lines; a `third-party` page the guide treats as primary is reported to the owner; the `authority` of a law or standard published by its issuer is `primary`; `search` takes `-- '<query>'` for a query starting with `-`; `file:line` is the matching line; a `thin content` error means the page needs the browser
- [x] `references/store.md` documents `citations.csv`: header `work_id,url[,as_of]` required, one row per `(work_id, url)`, `as_of` an ISO date (read as the end of that day, UTC) or timestamp, `url` normalised, Twin-reduced and taken through `aliases.csv`, a cited `url` with no Version is a warning of `recheck --citations`; and the `canonical` field, the `requested_url` JSON field, the `raw-twin` and `verbatim` converters
- [x] the JSON examples in `SKILL.md` are produced by running the commands against the fixtures (not typed), so the fields match the parser
- [x] `README.md`'s "For agents" section links `references/owner.md`

## Comments

**2026-10-17** — done on `galkin/lorekeep-v11-05`.

- **Files.** `SKILL.md` (214 lines) covers `get`, `add`, `search`, `status` and a Run's rules: what to
  cite, a table of the stderr lines with what to do, the exit-1 rule, the log. `references/owner.md`
  (new) covers `recheck`, `tag add`, `backup`, `restore`, `index`, `skill` and the `[[hosts]]` keys,
  with both findings of ticket 06. `references/store.md` is rewritten: `url` as the served address,
  `canonical`, the converters, the Twin kinds, what `--json` adds (`requested_url`), and a
  `citations.csv` section. README's "For agents" links both references.
- **Examples.** Every JSON and output block in `SKILL.md` was printed by the real commands, run
  in-process against `tests/fixtures/` with the fakes of `tests/support.py` (Tag `nvidia`, no
  browser installed), and pasted. The search examples use `--limit 1` so nothing had to be cut.
  `test_the_json_examples_have_the_fields_the_commands_print` keeps the four JSON examples' fields
  equal to what `get`, `add`, `search` and `status` print.
- **Tests.** The flag test now reads both `SKILL.md` and `references/owner.md`: each command has one
  section in one of them, each `--help` flag is a bullet there, and any flag named in a code span
  must exist (in its command's `--help` inside a section, in some `--help` outside one). New: the
  Run/owner split of the sections, `SKILL.md` under 250 lines, a flag named in prose alone is drift.
- **Friction answered** (reports aa, ab, ac): the address to cite and `requested_url`; fragments;
  `.md` only under a rule; parallel `get`s; retry only on `ReadTimeout`/`ConnectError`/`5xx`;
  report, never fetch another way, never `add`; the Tag per guide and the Run's own log, which goes
  in the final message when the harness blocks files; unknown host → tell the owner; third-party
  repository the guide treats as primary; laws and standards; `-- '<query>'` with flags on either
  side; `file:line` the matching line; `no matches` and `+N`; `thin content` → `lorekeep[browser]`;
  the missing-code warning (Version partial, Original whole); PDF Versions to be read, not searched;
  `lorekeep --version`; `status --rules`; the skill's length.

**Where the ticket, the spec or the brief was wrong.**

- **"Wait for a new Version"** (the brief, on adopting a new Twin rule): a Recheck rereads with the
  converter that stored the Version, and a changed page's new Version is made by that converter
  too. Only a Source first fetched after the rule gets the Twin, so `owner.md` says "fetch into a
  new Store". The README said `get --fresh` "stores a new one" after a rule change; corrected the
  same way (a new Version does take the new `publisher`/`authority`).
- **`crawl4ai` is not a converter**: a browser-rendered Version's `converter` is
  `trafilatura <version> via crawl4ai <version>`. The converters are `md-twin`, `raw-twin`,
  `verbatim`, `trafilatura <version>`, `markitdown <version>`, that browser form, and `owner`.
- **`.md` without a host rule** is not quietly a page: measured with a fixture served as
  `text/markdown` on an unknown host, `get` exits 1 with `unsupported media type text/markdown`.
  The skill tells a Run to ask for the page's address.
- **"`authority` of laws and standards is `primary`"** is a rule for the Run, not the tool: a host
  rule decides `authority` (the first Store recorded its two `eu` pages as `official`). The skill
  says to treat such a Source as `primary` and report a different value.
- **"One row per `(work_id, url)`"** is a rule for whoever writes `citations.csv`; lorekeep does
  not deduplicate, and a repeated row is listed twice by `recheck --citations`.
- **"The Tag is per guide"**: the glossary names a Tag for the ecosystem a Run serves. Both hold —
  one Tag per guide's ecosystem, shared by every worker — and the examples use `nvidia`.

**Seen, not changed** (behaviour is out of scope here): `recheck --citations` takes "the oldest
Version" by `fetched_at`, ties broken by file name, so two Versions of one page fetched in the same
second can hide a change (met while capturing the `owner.md` example; a real Store hardly ever has
them).
