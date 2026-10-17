# 01: Readings and the rule language

**What to build:** `[[readings]]` rules in two layers (`src/lorekeep/readings.toml`, the Store's `lorekeep.toml`) with the five operations (`drop_leading`, `drop_trailing`, `drop_lines`, `strip_title_suffix`, `heading_before`+`level`), applied to a Version to make a Reading in `.cache/readings/<stem>.md` with its frontmatter (`url`, `version`, `sha256`, `rules`, `title`); `lorekeep read [--prefix URL] [--force]`; `get` returns the Reading's path and `version` in JSON; the over-removal guard. Every kept line byte-equal to a Version line, fences and table lines untouchable. Decisions: `spec.md` › Rules, Readings.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] with a Store rule `prefix = "docs.nvidia.com/"`, `drop_leading = "llms\\.txt|For clean Markdown"`, the Fern Guardrails Twin fixture gets a Reading whose first line is `# Guardrail Types` and whose every line is a line of the Version; `get` prints the Reading's path, `--json` has `path` (the Reading) and `version` (the Version), `url` and `sha256` the Version's
- [ ] with `prefix = "eur-lex.europa.eu/"`, `heading_before = "^Article \\d+$"`, `level = 2`, the EUR-Lex AI Act fixture's Reading has one `## Article N` before each article line and none where a heading already precedes; a `drop_lines` rule never removes a line inside a fence or a pipe-table line (fixture with both)
- [ ] `strip_title_suffix = " - Azure Architecture Center \\| Microsoft Learn$"` on the Microsoft Learn Twin fixture gives a Reading headed `# Retry pattern` with `title: Retry pattern`; the Version is unchanged
- [ ] a Version no rule touches gets no Reading and `get` returns the Version with no `version` key
- [ ] `lorekeep read` builds the missing Readings and prints `Built N Readings, M current`; a rules change makes them stale and the next `get` rebuilds the one it returns; `--force` rebuilds all
- [ ] a rule with `removes = 5` applied to a Version where it would remove 12% of lines prints `lorekeep: warning: <url>: rule <name> removed 12% (accepted at 5%)` and the Reading is built without that rule
- [ ] `GLOSSARY.md` defines Reading and reading rule; `references/store.md` documents `.cache/readings/`, the Reading's frontmatter and `version` in JSON; `SKILL.md` says in one sentence what a Reading is, that `path` is the file to read and `version` the evidence, and gains the stderr row for the guard; the flag test covers `read`; under 250 lines
