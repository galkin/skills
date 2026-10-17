# 01: Readings and the rule language

**What to build:** `[[readings]]` rules in two layers (`src/lorekeep/readings.toml`, the Store's `lorekeep.toml`) with the five operations (`drop_leading`, `drop_trailing`, `drop_lines`, `strip_title_suffix`, `heading_before`+`level`), applied to a Version to make a Reading in `.cache/readings/<stem>.md` with its frontmatter (`url`, `version`, `sha256`, `rules`, `title`); `lorekeep read [--prefix URL] [--force]`; `get` returns the Reading's path and `version` in JSON; the over-removal guard. Every kept line byte-equal to a Version line, fences and table lines untouchable. Decisions: `spec.md` › Rules, Readings.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] with a Store rule `prefix = "docs.nvidia.com/"`, `drop_leading = "llms\\.txt|For clean Markdown"`, the Fern Guardrails Twin fixture gets a Reading whose first line is `# Guardrail Types` and whose every line is a line of the Version; `get` prints the Reading's path, `--json` has `path` (the Reading) and `version` (the Version), `url` and `sha256` the Version's
- [x] with `prefix = "eur-lex.europa.eu/"`, `heading_before = "^Article \\d+$"`, `level = 2`, the EUR-Lex AI Act fixture's Reading has one `## Article N` before each article line and none where a heading already precedes; a `drop_lines` rule never removes a line inside a fence or a pipe-table line (fixture with both)
- [x] `strip_title_suffix = " - Azure Architecture Center \\| Microsoft Learn$"` on the Microsoft Learn Twin fixture gives a Reading headed `# Retry pattern` with `title: Retry pattern`; the Version is unchanged
- [x] a Version no rule touches gets no Reading and `get` returns the Version with no `version` key
- [x] `lorekeep read` builds the missing Readings and prints `Built N Readings, M current`; a rules change makes them stale and the next `get` rebuilds the one it returns; `--force` rebuilds all
- [x] a rule with `removes = 5` applied to a Version where it would remove 12% of lines prints `lorekeep: warning: <url>: rule <name> removed 12% (accepted at 5%)` and the Reading is built without that rule
- [x] `GLOSSARY.md` defines Reading and reading rule; `references/store.md` documents `.cache/readings/`, the Reading's frontmatter and `version` in JSON; `SKILL.md` says in one sentence what a Reading is, that `path` is the file to read and `version` the evidence, and gains the stderr row for the guard; the flag test covers `read`; under 250 lines

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v13-01`).** Tests in
`tests/test_readings.py`, one per criterion (two for the second), each naming its fixture.

- **Rules.** `project.ReadingRule`, parsed from `[[readings]]` in the package's
  `src/lorekeep/readings.toml` and the Store's `lorekeep.toml` and merged as host rules are: a Store
  rule with the same `prefix`/`engine` and operation replaces a default. `readings.toml` ships with
  no rule, only a comment that the engine rules come from ticket 03's live run. Keys: `prefix` or
  `engine` (exactly one), exactly one operation, `level` (only and always with `heading_before`,
  1–6), `accepted` (a TOML date or a string), `removes` (percent, ≥ 0); anything else is a usage
  error naming `readings[N].<key>`. Which rules apply to a Version (`readings.rules_for`): per
  operation, the longest matching `prefix`, else the first `engine` rule whose engine made the
  Version; a prefix rule therefore beats an engine rule of the same operation. The operations run
  in a fixed order (`drop_leading`, `drop_trailing`, `drop_lines`, `strip_title_suffix`,
  `heading_before`).
- **Engines** (the spec left the markers to the implementer; written in `readings.py`'s
  docstring): `fern` — `md-twin` with a line before the first heading starting
  `> For clean Markdown` (NeMo Guardrails says `… of any page`, Dynamo `… content of this page`;
  a smoke run on 20 Fern Versions of the first Store missed the Dynamo ones with the narrower
  marker); `mintlify` — `md-twin` whose first line is `> ## Documentation Index`; `sphinx` —
  `trafilatura …` whose stored Original loads `_static/documentation_options.js` (133 of the first
  Store's 225 HTML Originals; Sphinx's `generator` meta is absent from NVIDIA's pages); `eur-lex` —
  `trafilatura …` with the line `This document is an excerpt from the EUR-Lex website`; `pdf` —
  `markitdown …`. Only the `fern` marker is tested (`engine = "fern"` over the Fern Twin and a
  non-Fern Twin).
- **Operations, where the spec was loose.** A pipe-table line is one whose first non-blank
  character is `|`; fence lines are those `sections` already treats as code (opener, body,
  closer), now exposed as `sections.code_lines`. `drop_leading` with no heading in the Version does
  nothing, and it also drops the blank lines after the block, so the Reading starts at its first
  text (the criterion's `# Guardrail Types` needs that); `drop_trailing` mirrors it after the last
  heading. A leading or trailing block that holds a fence or table line is not dropped at all
  (silently: `rules check` in ticket 03 is where that shows). `strip_title_suffix` takes the match
  that ends the first heading line (trailing blanks aside) and never empties it; that edited
  heading and the inserted headings are the only lines of a Reading that are not lines of the
  Version. `heading_before` inserts one line, `#`×`level` + the matched line stripped, with no
  blank line after it, and none when the previous non-blank line is a heading (the synthesised
  fixture has `Article 9` right under `## Article 9`).
- **Readings.** `readings.ensure` builds `.cache/readings/<stem>.md` when it is missing or its
  `rules` hash (sha256 of the applying rules' operation, pattern, prefix, engine, level and
  `removes`, plus a `READER` version of the operations' meaning) differs, writes it through a
  temporary file renamed into place inside the Store lock, and re-checks inside the lock so two
  workers build it once. A Version the rules leave unchanged gets no Reading, and a stale Reading
  of it is removed; `owner:` Sources never get one (out of scope). `get` calls it in `report`,
  after the commit released the lock; `--json` then has `path` (the Reading) and `version` (the
  Version) and everything else from the Version; `add --json` is unchanged. `lorekeep read
  [--prefix URL] [--force]` (`commands/read.py`) goes over every Version, not only the Latest,
  since `status` will count `N of M Versions`; `--prefix` is a full-URL prefix like `recheck`'s.
  The Index is untouched: it globs `*.md` in the Store's root, so `.cache/` never reaches it.
- **The guard.** A rule's share is lines it removed over the Version's lines, measured on what the
  earlier operations left; above twice `removes` the rule is skipped for that Version and the
  Reading records `warnings: ["rule <name> removed N% (accepted at M%)"]`, which `get` prints on
  every return, like a Version's own warnings (the spec said only "when rebuilding"; a Run that
  `get`s a Reading another worker built would otherwise never see it). `<name>` is
  `<prefix or engine:NAME> <operation>` (`docs.example.test/ drop_lines`); the spec named no rule
  name and the grammar has no `name` key. `N` is rounded to a whole percent.
- **Where the ticket was wrong.** The Fern rule `llms\.txt|For clean Markdown` leaves the banner's
  last line (`> For AI client integration …, connect to the MCP server at …/_mcp/server.`), because
  `drop_leading` stops at the last matching line; the test uses
  `llms\.txt|For clean Markdown|/_mcp/server`. The EUR-Lex fixture `eur-lex-ai-act.html` holds no
  article (it stops after recital 30), so the article test uses `eur-lex-ai-act.v1`, cut from the
  first Store's Version (the head, recitals 1–2, Articles 1–3). No Version in the first Store has
  an article line under a heading, so "none where a heading already precedes" is tested on the
  synthesised `readings-fence-table.v1`, which also carries the fence and the table.
- **Docs.** `GLOSSARY.md` gains Reading and reading rule; `references/store.md` the
  `.cache/readings/` row, a Readings section with the frontmatter and `path`/`version` in JSON;
  `references/owner.md` a `lorekeep read` section and the `[[readings]]` keys with one example
  (ticket 03 owns the full brief); `SKILL.md` one sentence in "How a Run works" and the stderr row,
  kept at 248 lines by dropping the exit-`1` example, which repeated the log example. That
  `.cache/` is never backed up is not written yet: `backup` still copies it until ticket 02.
