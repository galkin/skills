# 03: a subagent proposes rules, `lorekeep rules check` measures, `rules accept` writes

**What to build:** No model inside lorekeep and no API key (owner, 2026-10-17: the tool already runs in an agentic flow). Three parts. (1) `lorekeep rules sample PREFIX [--sample N]` prints the paths of up to N Versions under the prefix (default 5: the shortest, the longest, three between) — the material for a proposer. (2) `lorekeep rules check FILE [--store DIR]` reads candidate `[[readings]]` rules from a TOML file, applies each to every Version under its prefix, and prints per candidate: lines removed or headings inserted (total; min, median, max per Version), three removed lines as examples, and `pass` or `fail` with the reason against the limits (`drop_lines` at most 30% of any Version's lines; a block operation is bounded by the first or last heading and has no share limit; never a fence or a pipe-table line); writes nothing. (3) `lorekeep rules accept FILE` runs the same check and appends the passing rules to the Store's `lorekeep.toml` with `accepted` (today) and `removes` (the most it removed, with its unit: `"31 lines"` for a block operation, `"4%"` for `drop_lines`, none for the other two; ticket 01 wrote `removes` as a percent for every operation and its guard must change with it — spec.md › Rules, amended 2026-10-17), then rebuilds the Readings under their prefixes; `--all` also accepts the failing ones (owner's override). (4) `references/owner.md` gives the orchestrator the brief for the proposer: launch a subagent on the cheapest model available (the Haiku tier, through Orca orchestration as any worker), hand it the sampled paths and the rule grammar, and require the answer as one TOML file of `[[readings]]` candidates, nothing else; then `rules check`, read the report, `rules accept`. The engine defaults in `src/lorekeep/readings.toml` come from running that cycle live on the first Store. Decisions: `spec.md` › Rules proposed by a subagent.

**Blocked by:** 01, 02

**Status:** done, but the fifth criterion: the live run is the orchestrator's

- [x] `rules sample docs.nvidia.com/` over five Fern Twin fixtures prints five paths, shortest and longest first; `--sample 2` prints two
- [x] `rules check` with a fixture file of candidates (the TOML a proposer returned for `docs.nvidia.com/` on the first live run, kept as `tests/fixtures/readings-candidates-fern.toml`) prints each candidate with its measurements and verdict and writes nothing; a candidate that removes 40% of one Version, or a fence line, or a leading block after the first heading, is `fail` with the reason
- [x] `removes` is written with its unit (`"31 lines"` for `drop_leading`/`drop_trailing`, `"4%"` for `drop_lines`, absent for the other two) and the guard of ticket 01 compares in that unit: on the first Store's rule `drop_leading = "llms\\.txt|For clean Markdown|/_mcp/server"` for `docs.nvidia.com/` every one of the 55 banner Versions gets a Reading (the 79-line Dynamo router guide with its 31-line banner included), and a Version where the block is more than twice the accepted count is held back with `rule <name> removed N lines (accepted at M lines)`
- [x] `rules accept` with that file appends only the passing rules to `lorekeep.toml`, with `accepted` and `removes`, prints `Accepted N rules, M failed`, and `lorekeep read` has then built the Readings under the prefix; `--all` appends the failing ones too; a rule already present (same prefix and operation) is replaced, not duplicated
- [ ] run live by the orchestrator on the first Store with a Haiku-tier subagent for `docs.nvidia.com/`, `eur-lex.europa.eu/`, `learn.microsoft.com/` and `docs.nvidia.com/rag/latest/`: the ticket Comment records every candidate, its measurements and the verdict; the accepted engine-level rules (Fern banner, EUR-Lex articles, Microsoft Learn suffix) go into `src/lorekeep/readings.toml` with a test each; the Store's `lorekeep.toml` holds the rest
- [x] `references/owner.md` documents `rules sample`, `rules check`, `rules accept`, the `[[readings]]` keys with one example, the limits, and the proposer brief (model tier, input, the exact output format, what the orchestrator does with it) in under 30 lines; the flag test covers the three commands and passes

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v13-03`).** Tests in `tests/test_rules.py`,
one per criterion (two for the second and three for the fourth), each naming its fixture; the
fifth criterion, the live run, is left to the orchestrator and unticked.

- **`removes` with its unit** (the spec's amendment). `ReadingRule.removes` is the string as
  written: `"N lines"` (`"1 line"` too) for `drop_leading`/`drop_trailing`, `"N%"` for
  `drop_lines`; a bare number, the wrong unit, or `removes` on `strip_title_suffix` or
  `heading_before` is a usage error naming the key. The guard compares in that unit: a block
  operation's lines against twice the accepted count, `drop_lines`'s share of the Version's lines
  against twice the accepted share; the warning reads `rule <name> removed N lines (accepted at M
  lines)` or `… removed N% (accepted at M%)`. The rules hash changes with it (`removes` is hashed
  as written, and `READER` is `2`, so every Reading of ticket 01 is rebuilt once). Ticket 01's
  guard test, the owner.md example, store.md's `warnings` and SKILL.md's stderr row follow.
- **`rules sample PREFIX [--sample N]`** matches `PREFIX` as a rule's `prefix` (`host/path`; a
  scheme given is dropped), takes the newest Version of each Source (`owner:` ones aside), sorts
  them by body lines and prints the shortest, the longest, then the others evenly spaced by rank.
- **`rules check FILE`** measures each candidate alone on every Version it reaches (its prefix,
  or the Versions its engine made), before any other rule: the guard then measures on what the
  earlier operations left, which is never more. The limits, as `readings.measure` applies them:
  `drop_lines` above 30% of any Version, or matching any fence or table line (the operation would
  skip it, but the candidate meant it), fails; a leading block fails when the pattern's last match
  in a Version is after its first heading, or the block holds a fence or table line (a trailing
  block mirrors both); a candidate that is not the grammar fails with the parser's reason
  (`readings[N].…`), and so does one carrying `accepted` or `removes`. Two verdicts the ticket did
  not name: no Version under the prefix, and a candidate that changes no Version (its `removes`
  would be `0` and hold it back everywhere). A failing `drop_lines` names the Version with the
  highest share; any other failure the first Version where it happens, as `file:line`. Examples
  are three distinct non-blank lines (the first, the middle, the last of all it changed). Exit `0`
  whatever the verdicts; `2` for a file that is not TOML or holds anything but `[[readings]]`.
- **`rules accept FILE [--all]`** prints the same report, then `Accepted N rules, M failed`
  (`M` the failing verdicts, accepted or not), then `Built N Readings, M current` over the
  Versions the accepted rules reach. `removes` is the most one Version lost: lines, or the share
  rounded up to a whole percent. Two candidates with the same prefix and operation: the later
  wins, as a later table does in `lorekeep.toml`, with a note on stderr; `--all` never accepts a
  candidate that is not the grammar.
- **How `lorekeep.toml` is edited** (`project.with_readings`), under the Store lock and written
  through a temporary file renamed into place: the file is read as text; each `[[readings]]`
  header line is paired with the parsed table of the same rank (a count that differs, as with an
  inline `readings = [...]`, is refused with an error); a table's lines run to the next table
  header, less the blank and comment lines before it, which belong to what follows. A rule with
  the same prefix/engine and operation replaces its table's lines where they stand; any other is
  appended at the end after a blank line. Strings are written in TOML basic quotes, `accepted` as
  a TOML date. The result is parsed again and refused unless every other setting is equal and the
  rules read back exactly as written, so the owner's other lines and comments are byte for byte
  what they were.
- **Fixtures.** Two Fern Twins from the first Store, whole: `dynamo-router-guide.twin` and
  `nemo-gym-build-verifiers.twin` (the shortest Fern Twin there), beside the three already kept.
  `readings-candidates-fern.toml` was written for this ticket, before any live run: the banner
  rule (passes, `removes = "26 lines"`), `drop_lines = "^> |^</?Info>$"` (41% of the Router
  Guide), `drop_lines = "^# "` (a shell comment in a fence of Fast Model Loading) and
  `drop_leading = "^> "` (its last match is a quote line after that page's first heading).
- **Where the ticket was wrong or loose.** The Dynamo Router Guide is 79 lines as a file, 63 as a
  body; its banner is 24 quote lines, and the block `drop_leading` removes is 26 with the blank
  lines, not 31. On a copy of the first Store, `rules check` of the banner rule measured 813 lines
  over 174 Versions under `docs.nvidia.com/`, at most 26 per Version, with no match after a first
  heading; `rules accept` wrote `removes = "26 lines"` and built a Reading for every one of the 55
  banner Versions, the Router Guide included (0.98 s), and a second accept replaced the table
  rather than adding one. The candidate fixture's 40% is 41%: no plausible pattern lands on 25 of
  the Router Guide's 63 lines. "A leading block after the first heading" cannot happen as
  `drop_leading` works (it stops at the heading), so the limit is read as the candidate's last
  match being after it, which is what the proposer meant to remove.
- **Docs.** `references/owner.md`: `rules sample`, `rules check` (with a real report), `rules
  accept` (and how it edits the file), `removes` with its unit in the keys and the example, and
  "Proposing reading rules", the brief and the cycle in 22 lines. `SKILL.md`: only the stderr
  row, which had become false (249 lines). `GLOSSARY.md` › Reading rule: what it records.

**2026-10-17 — live run (orchestrator), ticket 03 merged as `82d9547`.** On the first Store
(376 Versions, 0 Readings before). `rules sample` on the ticket's four prefixes gave for
`docs.nvidia.com/` eight Sphinx conversions and one Fern Twin, since it samples by length and the
host mixes engines; the orchestrator sampled seven sub-prefixes by hand instead (`nemo/guardrails/`,
`dynamo/`, `nemo/gym/`, `rag/latest/`, `nemo/agent-toolkit/`, `eur-lex.europa.eu/`,
`learn.microsoft.com/`, four Versions each) — friction filed as ticket 05. A Haiku subagent
(Orca dispatch `ctx_6f2c83f04769`, brief as owner.md › Proposing reading rules, told to read heads,
tails and grep the laws) returned six candidates in one TOML file. `rules check` (0.9 s):

| candidate | result |
| --- | --- |
| `docs.nvidia.com/nemo/guardrails/` `drop_leading = "/_mcp/server"` | pass, 31 Versions, 12 lines each |
| `docs.nvidia.com/dynamo/` `drop_leading = "/_mcp/server"` | fail: changes no Version (Dynamo's banner has no MCP line) |
| `docs.nvidia.com/nemo/gym/` `drop_leading = "/_mcp/server"` | pass, 4 Versions, 15 lines each |
| `learn.microsoft.com/` `strip_title_suffix = " - Azure Architecture Center \\| Microsoft Learn"` | pass, 4 titles |
| `eur-lex.europa.eu/` `heading_before = "^Article \\d+"`, level 2 | pass, 213 headings — one too many: `Article 18 of Regulation (EU) 2019/1020 shall apply…` in a paragraph |
| `eur-lex.europa.eu/` `heading_before = "^CHAPTER"`, level 1 | pass, 24 headings — but a second `heading_before` on the same prefix replaces the first, so only one could be accepted |

What the orchestrator did with the report, as the cycle says: one host-wide Fern rule in place of
the three per-group ones, with the pattern ticket 01 found (`llms\.txt|For clean Markdown|/_mcp/server`,
which also reaches Dynamo and NeMo Curator); the article pattern anchored (`^Article \d+$`); the
chapter rule dropped (one rule per operation and prefix — the limitation is in ticket 05). Second
`rules check`: 3 pass; the Fern rule over 174 Versions, 813 lines, max 26 per Version.
`rules accept`: `Accepted 3 rules, 0 failed`, `Built 61 Readings, 0 current` in 1.3 s (55 Fern,
4 Learn, 2 EUR-Lex); `lorekeep.toml` gained three `[[readings]]` tables (`removes = "26 lines"` on
the Fern rule, none on the other two), every other line as it was. After it: `search "llms.txt"`
finds no Section, `search "risk management system high-risk"` answers with `… > Article 9` in the
breadcrumb and a line in the Reading, `status` prints `Readings: 61 of 376 Versions, 3 rules`.
The engine rules (Fern banner, EUR-Lex articles, Microsoft Learn suffix) go into
`src/lorekeep/readings.toml` with a test each — dispatched as the last step of this ticket.

**2026-10-17 — live run, round 2 (orchestrator).** `search "llms.txt"` still answered from the
Mintlify Twins (`docs.langchain.com/`, 22 Versions; `modelcontextprotocol.io/`, 2), which the
ticket's four prefixes did not cover. A second Haiku subagent (dispatch `ctx_2f103b4a8e6d`) on
those two prefixes returned three candidates: `drop_leading = "^> "` for both hosts and
`drop_trailing = "^<div className=\"source-links\">"` for LangChain. `rules check` failed the
LangChain `drop_leading`: `matches docs.langchain.com--oss-python-deepagents-overview--d3f61289.md:23,
after the first heading (line 21)` — a quote in the page's body, exactly the case the limit is for.
The orchestrator replaced `^> ` by the banner's last line, `before exploring further\.$`, on both
hosts; second check 3 pass; `rules accept`: `Accepted 3 rules, 0 failed`, `Built 24 Readings`
(`removes = "4 lines"`, `"10 lines"`, `"4 lines"`). The Store: `Readings: 85 of 376 Versions,
6 rules`. Engine candidates for `readings.toml`: `fern` (the banner), `mintlify` (the banner and,
if it measures on both hosts, the source-links footer), `eur-lex` (articles), and the Microsoft
Learn suffix, which is a host rule rather than an engine.
