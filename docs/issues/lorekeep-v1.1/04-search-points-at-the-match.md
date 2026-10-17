# 04: `search` points at the matching line, survives escapes and broken fences, and says "no matches"

**What to build:** `search` prints the line of the first matched term inside the Section (`heading_line` beside it in JSON), compares `--exact` after unescaping `\_` and `\*` on both sides, strips permalink links from heading paths at Index time, prints `(top)` for an empty heading path, accepts a query after `--`, prints `no matches` on zero results and the `+N` line only when N > 0. The sectioniser opens a fence only on a line that is nothing but the fence (plus an info string) and closes an unclosed fence at the next heading. `lorekeep --version` prints the version; `status` prints host rules only with `--rules`. Decisions: `spec.md` › Search and Sections.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] a Version whose Section heading is on line 64 and whose body has `free_gpu_memory_fraction: 0.7` on line 77: `search --exact free_gpu_memory_fraction` prints `…:77`, `--json` gives `line: 77, heading_line: 64`; a stemmed FTS match with no literal word in the Section prints the Section's first content line
- [x] a Version written by v1 with `free\_gpu\_memory\_fraction` matches `--exact free_gpu_memory_fraction`
- [x] a Version whose heading is `## Enable Tool Calling[#](https://…#enable-tool-calling)` shows the heading path `Enable Tool Calling` in text and JSON after `index`; a hit before any heading shows `(top)`
- [x] the vLLM `cli/serve` page (fixture: its Markdown as v1 stored it, with `Example (new format): ```` followed by a JSON block) yields Sections for every heading after that line; a fence left open ends at the next heading
- [x] `lorekeep search -- '--enable-auto-tool-choice' --exact` works, and `SKILL.md`'s search section shows the `--` form (one sentence; the rewrite is ticket 05)
- [x] a query with no hit prints `no matches` and exits 0; in a scoped search with 0 outside matches the `+0` line is absent; with 3 it is `+3 matches under other tags (--all)`; `--json` keeps `other_tags`
- [x] `lorekeep --version` prints `lorekeep 0.1.1` (bump `pyproject.toml`); `status` without `--rules` ends at `Freshness window`; `status --rules` prints the rules as today
- [x] the flag-vs-`--help` test in `tests/test_skill.py` passes with the new flags documented

## Comments

**2026-10-17** — done on `galkin/lorekeep-v11-04`; tests in `tests/test_search_lines.py`, fixtures
`tests/fixtures/vllm-cli-serve.v1` (cut from the first migration's Version) and
`tests/fixtures/trtllm-kv-cache.v1` (hand-written, v1 escapes).

- **The vLLM defect is not what the spec says.** `format): ```` never opened a fence in v1 (the
  opener regex is anchored at the line start); the bare ```` ``` ```` three lines later did, and it
  *was* closed — by the next bare fence 467 lines on, after the next inline `… ```` paragraph. So
  "an unclosed fence ends at the next heading" alone does not fix the page. Implemented as well: a
  text line ending in an unpaired backtick fence opens a fence whose code starts on the next line
  (the text line stays text) and closes at the next bare fence. Both kinds, when never closed, end
  at the next heading. Openers are bare per the spec; closers must be bare too (CommonMark).
- **Index:** `sections.heading_line` added (`NULL` before the first heading); `sections.line` is
  now the Section's first text line, and `search` adds the offset of the first line holding the
  match. `meta` records `schema = 2`; an Index without it is stale, and the rebuild drops and
  recreates `sections`/`sections_fts`, so a v1 `sources.db` is rebuilt by the next reader and a
  commit never marks it current.
- **JSON for text before any heading:** `heading` stays `""` and `heading_line` is `null`; only the
  text output prints `(top)`.
- **`--`:** `cli.run` takes the one argument after `--` on `search` as the query and parses the
  rest as flags (argparse alone would make every later word a positional); a query both before and
  after `--` is a usage error. `query` is `nargs="?"` so an empty one still gets the one-line error.
- Snippets are unescaped (`\_`, `\*`) in both modes; FTS matching is unchanged (unicode61 already
  splits on `\` and `_`).
- `SKILL.md`: besides the `--` sentence, the search output paragraph (match line, `(top)`,
  `no matches`, `+N` only above zero), `heading_line` in the JSON example, and `status --rules`
  had to change because the old sentences became false; README and `references/store.md` say
  `status --rules`. The rewrite stays with ticket 05.
