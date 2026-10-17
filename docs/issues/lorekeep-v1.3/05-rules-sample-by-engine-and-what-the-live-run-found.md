# 05: `rules sample` by engine, and what the first live run found

**What to build:** Three things the live run of ticket 03 (2026-10-17) showed. (1) `rules sample PREFIX` samples by length alone, so on a host that mixes engines (`docs.nvidia.com/`: 55 Fern Twins among 174 Versions, the rest Sphinx HTML and one verbatim JSON) the five paths are mostly one engine and the proposer never sees the other; the sample takes `--engine NAME` (the engines `readings.py` recognises) and, without it, is stratified: up to `--sample` Versions per engine present under the prefix, each group headed by a `# engine: NAME` comment line, so the proposer knows which pages share a banner. (2) One `[[readings]]` rule per operation and scope: the proposer offered `heading_before` for both `^CHAPTER` (level 1) and `^Article \d+$` (level 2) on EUR-Lex, and the second replaced the first; `heading_before` rules on one scope stack in file order (each inserted heading counts as a heading for the next rule's "unless the previous line is a heading"), while the four other operations stay one per scope — `rules check` and `rules accept` follow (two `heading_before` candidates on one scope are both accepted, not replaced). (3) A wrong first heading: the EUR-Lex Versions' first heading is `# Need help?` (the site's help box, which Trafilatura kept and v1.2's title rule took as the title), so every Reading of a law is titled `Need help?` and `search` breadcrumbs read `Need help? > Article 9`; `drop_leading` cannot remove it (it stops before the first heading) and no operation retitles. A `drop_leading` that is allowed to remove the first heading itself when the pattern matches that heading line (`drop_leading = "^# Need help\?$"`) — the Reading's `title` then comes from its first remaining heading, as ticket 01 already does when the Version has no title — is the smallest change; the implementer measures it on the two EUR-Lex Versions and says in the Comment what the Reading's first heading and title became. Decisions: `spec.md` › Rules, › Rules proposed by a subagent.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `rules sample docs.nvidia.com/` over a fixture Store holding Fern Twins and Sphinx conversions prints a `# engine: fern` group and a `# engine: sphinx` group, each with the shortest and longest of its engine; `--engine fern` prints the Fern group alone; `--sample 2` gives two per group
- [x] two `heading_before` rules on `eur-lex.europa.eu/` (`^CHAPTER`, level 1; `^Article \d+$`, level 2) both apply to the EUR-Lex fixture, in file order, and `search` breadcrumbs read `CHAPTER III > Article 9`; `rules accept` with both candidates accepts both and `lorekeep.toml` holds both tables
- [x] a `drop_leading` whose pattern matches the first heading line removes that heading too, and the Reading's `title` is its first remaining heading; measured on the first Store's two EUR-Lex Versions (the Comment records the title each Reading got)
- [x] `references/owner.md` documents `--engine`, the stratified sample, stacked `heading_before` rules and the first-heading case of `drop_leading`; `SKILL.md` unchanged unless a sentence became false; under 250 lines

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v13-05`).** One test per criterion (three for
the second, two for the third), each naming its fixture: `tests/test_rules.py` (the sample, the
accept) and `tests/test_readings.py` (the stack, the Store layer, the first heading, its limit).

- **`rules sample PREFIX [--sample N] [--engine NAME]`.** Each Version (the newest of each
  Source) goes to the first engine of `fern`, `mintlify`, `sphinx`, `eur-lex`, `pdf` whose markers
  it carries (`readings.engine_of`, the markers ticket 01 wrote down), else to `other`; the groups
  print in that order, each as a `# engine: NAME` line then up to `--sample` paths chosen as
  before (shortest, longest, spread), an empty group not at all. `--engine NAME` prints that
  group alone, header included; `other` is a valid name; an unknown name exits `2`, a group with
  no Version under the prefix exits `1` (`no Version under docs.nvidia.com/ that pdf made`).
  The test's Store: the five Fern Twins, two Sphinx pages converted by `get` (`nim-overview.html`
  and the new `nim-legal.html`, the first Store's Original whole: Sphinx is recognised from the
  stored Original, and the only other kept one had its scripts cut) and RAG's OpenAPI schema
  stored verbatim, which no engine made.
- **Stacked `heading_before`.** "The same rule" is `ReadingRule.key`: scope (prefix or engine)
  and operation, plus the pattern for `heading_before` only; the four other operations stay one
  per scope, keyed as before. That key drives the package/Store merge (a Store `heading_before`
  with the default's pattern replaces it, so the owner can change its level; another pattern
  stacks after it), the duplicate check of `lorekeep.toml` (the same pattern twice on one scope is
  still an error), `rules accept`'s "the later candidate wins" and `with_readings` (a table is
  replaced in place only by the same key; any other `heading_before` is appended). Which apply to
  a Version: the scope wins as for any operation (the longest prefix that has a
  `heading_before`, else the first engine that made the Version and has one), then every
  `heading_before` of that scope runs, in merged order (the package's, then the Store's, each in
  file order). A line an earlier rule headed counts as under a heading for the later ones.
- **`drop_leading` through the first heading.** When the pattern matches the first heading line,
  the block runs through that heading and the blank lines after it, up to the next text line;
  otherwise, as before, up to the last match before it. `rules check`'s limit is unchanged in
  form: a match after the first heading fails, and one on it does not. The Reading's `title` is
  the Version's unless the Version has none or a rule removed its first heading; then it is the
  Reading's first heading, inserted ones included, now skipping fence lines (before, a `# comment`
  in a fence could title a Version that had no `title`). `READER` is `3`, so every Reading is
  rebuilt once.
- **Measured on the first Store's two EUR-Lex Versions** (`…2024-1689-oj--d5a4ced3.md`,
  `…2016-679-oj--4f2f9df1.md`), copied into a temporary Store; nothing was written to the first
  Store. Both are titled `Need help?` and that box is their only heading. `rules check` of
  `readings-candidates-eur-lex.toml`: `drop_leading = "^# Need help\?$"` passes, 2 lines per
  Version (the heading and the blank after it); `^CHAPTER [IVXLC]+$` (level 1) passes, 24
  headings (13 and 11); `^Article \d+$` (level 2) passes, 212 (113 and 99). `rules accept`:
  `Accepted 3 rules, 0 failed`, `Built 2 Readings`, and `lorekeep.toml` holds the three tables,
  both `heading_before` ones. Each Reading now starts at `This document is an excerpt from the
  EUR-Lex website`; its first heading is `# CHAPTER I` and its `title` is `CHAPTER I`, for both
  laws. `search "risk management system high-risk"` answers with `CHAPTER III > Article 9` (line
  833 of the AI Act's Reading), and `search "lawfulness of processing"` with `CHAPTER II > Article 6`
  in the GDPR's. With the `drop_leading` alone the package's article rule applies, and the first
  heading and title are `## Article 1` and `Article 1`. Neither title is the act's name. A third
  `heading_before`, `^REGULATION \(EU\) \d+/\d+ OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL$` at
  level 1 (one match per act), with chapters at 2 and articles at 3, titles them
  `REGULATION (EU) 2024/1689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL` and `… 2016/679 …`,
  but the breadcrumbs then begin with that line. Which set to accept is the owner's choice.
  Nothing went into `readings.toml`: the help-box `drop_leading` is an `engine = "eur-lex"`
  candidate for it once it is accepted live.
- **Where the ticket was wrong or loose.** (1) `eur-lex-ai-act.v1` holds Chapter I and Articles
  1–3 only, so the test's breadcrumb is `CHAPTER I > Article 2`; `CHAPTER III > Article 9` is the
  measurement above. (2) "stack in file order" says nothing about scopes. As built, a prefix's
  `heading_before` rules shadow an engine's, as for every other operation, so an owner who adds a
  chapter rule on `eur-lex.europa.eu/` lists the article rule there too (the candidate fixture
  does). A Store also cannot turn off a package `heading_before` whose pattern it does not repeat.
  (3) `rules check` still measures each candidate alone, so two `heading_before` candidates that
  would head the same line both count it; applied together, the later one inserts nothing there.
  (4) The ticket's own fix titles a law `CHAPTER I` or `Article 1`, not by its name: see the
  measurement. (5) `drop_trailing` was not mirrored (it never takes the last heading); nothing
  asked for it.
- **Docs.** `references/owner.md`: `--engine`, the groups and a real example in `rules sample`;
  the first-heading case in `rules check`'s limits and in the grammar; same-pattern replacement in
  `rules accept`; the brief tells the proposer what a `# engine:` line means and that several
  `heading_before` rules may share one prefix; the `[[readings]]` section explains the stack and
  the shadowing. `references/store.md`: the Reading's `title` line, which had become false.
  `SKILL.md` (249 lines) and `GLOSSARY.md` are unchanged, since none of their sentences became
  false. `tests/fixtures/README.md` lists `nim-legal.html` and `readings-candidates-eur-lex.toml`.
