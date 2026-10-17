# lorekeep v1.3: Readings — the canonical Markdown a Run reads

## Problem Statement

After v1.2 a Version is faithful to the publisher and `search` finds what it holds, but the file
a Run opens still carries what no converter can remove without editing the publisher's text: the
12-line llms.txt banner Fern puts before the H1 of every NVIDIA Twin (83 pages in the first
Store), a site suffix in the H1 of Microsoft Learn's Twins, 113 articles of the AI Act as one
headingless block, a Redoc shell's menu. Every Run pays those tokens on every read, and `search`
reports a `(top)` Section of boilerplate. The owner's decisions (2026-10-17): the tool never
edits a Version; post-processing is a legitimate part of making the canonical Markdown for this
project and belongs in the tool, deterministic; the rules are not written by hand — an LLM
analysis proposes them and the tool verifies and applies them; everything a Run or the owner needs
to know is in the skill.

## Solution

A **Reading** is the Markdown of a Version after the Project's **reading rules**, built by the
tool, kept in the Store's `.cache/`, rebuilt whenever the rules change, never backed up. A Run
reads the Reading (`get` returns its path), `search` indexes Readings, the Version stays the
evidence and the object of Recheck and Citation. Rules are data in two layers (package defaults
per engine, the Store's `lorekeep.toml`), limited to operations that cannot alter a line: drop a
leading or trailing block, drop lines by pattern, drop a heading's suffix, insert a heading before
lines by pattern. `lorekeep rules propose <prefix>` asks an LLM for candidate rules over a sample
of the host's Versions, then measures each candidate over every Version of the host and prints
what it would remove; `--accept` writes the rules that pass the limits into `lorekeep.toml`. `get`
and `search` never call a model.

## User Stories

1. As a Run, I want `get` to hand me the page without the publisher's banner and chrome, so that
   I spend tokens on content.
2. As a Run, I want `search` hits and `file:line` to point into the file I open, so that a hit is
   one `Read` away.
3. As a Run, I want the law I cite to have one heading per article, so that a hit names the
   article.
4. As a Run, I want to know when the file I read is a Reading and where its Version is, so that I
   cite the Version's `url` and can compare when in doubt.
5. As the owner, I want rules proposed from the Store's own pages and shown with what they remove
   before they apply, so that no rule silently eats content.
6. As the owner, I want a rule that starts removing much more than when it was accepted to be
   reported, so that a site redesign cannot hollow out my Readings unnoticed.
7. As the owner, I want engine rules (Fern, Sphinx, EUR-Lex) shipped with the tool, so that a new
   Project starts clean.
8. As the owner, I want `backup` to copy Versions and never the cache, so that the bucket holds
   evidence only and Readings are rebuilt from it.
9. As the orchestrator, I want the skill to say how a Run reads, how the owner proposes rules and
   what to report, so that nothing here lives in my head.

## Implementation Decisions

### Rules

- A rule is a TOML table under `[[readings]]` with `prefix` (host/path, longest wins, as host
  rules) or `engine` (`fern`, `mintlify`, `sphinx`, `eur-lex`, `pdf`, matched on `converter` and
  the Version's own markers, decided by the implementer and written down), and one operation:
  - `drop_leading = "<regex>"`: the leading lines up to and including the last line matching the
    regex before the first heading; `drop_trailing` the same from the end;
  - `drop_lines = "<regex>"`: every line matching, outside fences;
  - `strip_title_suffix = "<regex>"`: the match removed from the end of the first heading and
    from `title` in the Reading's frontmatter;
  - `heading_before = "<regex>"`, `level = N`: a heading of that level whose text is the matched
    line, inserted before each matching line outside fences, unless the previous line is already a
    heading.
- Every kept line of a Reading is byte-equal to a line of the Version; a rule cannot touch a
  fence or a pipe-table line. A rule carries `accepted` (date) and `removes` (the share of lines
  it removed over the Store's Versions when accepted, as `rules propose` measured it).
- Two layers, as host rules: `src/lorekeep/readings.toml` (engines) and the Store's
  `lorekeep.toml`; a Store rule with the same `prefix`/`engine` and operation replaces the default.

### Readings

- `.cache/readings/<stem>.md` beside the Store, frontmatter: `url`, `version` (the Version's
  file name), `sha256` (of the Reading's body), `rules` (the hash of the rule set applied),
  `title`. No Reading for a Version no rule touches: `get` returns the Version.
- `lorekeep read [--prefix URL] [--force]` builds missing or stale Readings (stale = `rules` hash
  differs); every reader (`get`, `search`) builds the Readings it needs lazily, inside the Store
  lock, so a Run never sees a stale one. `backup` skips `.cache/`; `restore` needs nothing.
- `get` returns the Reading's path when one exists (text and `path` in JSON) and adds `version`
  (the Version's path) to the JSON; `url`, `sha256` and the rest stay the Version's.
- `search` indexes Readings where they exist (`sections` rows name the file searched, so
  `file:line` points into it); `SCHEMA_VERSION` bumps. `status` prints `Readings: N of M Versions,
  K rules`.
- When rebuilding a Reading, a rule that removes more than twice its `removes` share on a
  Version prints `lorekeep: warning: <url>: rule <name> removed N% (accepted at M%)` and is NOT
  applied to that Version.

### `rules propose` (the one place a model is called)

- `lorekeep rules propose PREFIX [--sample N] [--accept] [--store DIR]`: takes up to N (default
  5) Versions under the prefix (the shortest and the longest among them), sends them with the
  rule grammar to the model (Anthropic API, `claude-haiku-4-5-20251001`, key from
  `ANTHROPIC_API_KEY`; the `anthropic` SDK as the extra `lorekeep[rules]` — a new runtime
  dependency, named here because the task cannot be done without it), and receives candidate
  rules as TOML. The tool then applies each candidate to every Version under the prefix and
  prints, per candidate: lines removed or headings inserted in total and per Version (min, median,
  max), three removed lines as examples, and whether it passes the limits: at most 30% of a
  Version's lines, never a fence or table line, `drop_leading` only before the first heading.
- `--accept` appends the passing candidates to the Store's `lorekeep.toml` with `accepted` and
  `removes`, and rebuilds the Readings under the prefix. Without it nothing is written.
- Without the extra or the key, the command exits 2 naming what is missing.

### The skill

- `SKILL.md`: what a Reading is (one sentence), that `path` is the file to read and `version`
  the evidence, that `url` is still what to cite, that a `rule … removed N%` warning means the
  Reading fell back to the Version; the stderr table gains that row.
- `references/owner.md`: `read`, `rules propose`, the `[[readings]]` keys with one example, the
  limits, the cycle (a worker's friction → `rules propose` on that host → `--accept` → rebuilt
  Readings), and that `.cache/` is never backed up.
- `references/store.md`: `.cache/readings/`, the Reading's frontmatter, `version` in JSON.
- `GLOSSARY.md`: Reading, reading rule.

## Testing Decisions

As before: fixtures from the first Store (a Fern Twin with the banner, the EUR-Lex AI Act cut,
a Microsoft Learn Twin, a Redoc shell), one test per criterion; the model is faked at the seam
(`Edges` gains a `proposer`), with recorded candidate TOML as the fixture; `pytest`, `ruff`,
`pyright` the gate.

## Out of Scope

- Any operation that rewrites a line (paraphrase, number or code changes).
- Digests (LLM summaries as `generated` Sources): a later spec.
- Readings for `owner:` Sources.
- Running `rules propose` inside `get` or on a schedule.

## Further Notes

The first Store's rule set is produced by the implementer of ticket 03 by running
`rules propose` live on `docs.nvidia.com/`, `eur-lex.europa.eu/`, `learn.microsoft.com/` and
`docs.nvidia.com/rag/latest/`, with the owner's key; what it proposed and what passed is recorded
in the ticket, and the engine-level rules among them go into `readings.toml`.
