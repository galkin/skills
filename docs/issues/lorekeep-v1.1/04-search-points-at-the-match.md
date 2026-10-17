# 04: `search` points at the matching line, survives escapes and broken fences, and says "no matches"

**What to build:** `search` prints the line of the first matched term inside the Section (`heading_line` beside it in JSON), compares `--exact` after unescaping `\_` and `\*` on both sides, strips permalink links from heading paths at Index time, prints `(top)` for an empty heading path, accepts a query after `--`, prints `no matches` on zero results and the `+N` line only when N > 0. The sectioniser opens a fence only on a line that is nothing but the fence (plus an info string) and closes an unclosed fence at the next heading. `lorekeep --version` prints the version; `status` prints host rules only with `--rules`. Decisions: `spec.md` › Search and Sections.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] a Version whose Section heading is on line 64 and whose body has `free_gpu_memory_fraction: 0.7` on line 77: `search --exact free_gpu_memory_fraction` prints `…:77`, `--json` gives `line: 77, heading_line: 64`; a stemmed FTS match with no literal word in the Section prints the Section's first content line
- [ ] a Version written by v1 with `free\_gpu\_memory\_fraction` matches `--exact free_gpu_memory_fraction`
- [ ] a Version whose heading is `## Enable Tool Calling[#](https://…#enable-tool-calling)` shows the heading path `Enable Tool Calling` in text and JSON after `index`; a hit before any heading shows `(top)`
- [ ] the vLLM `cli/serve` page (fixture: its Markdown as v1 stored it, with `Example (new format): ```` followed by a JSON block) yields Sections for every heading after that line; a fence left open ends at the next heading
- [ ] `lorekeep search -- '--enable-auto-tool-choice' --exact` works, and `SKILL.md`'s search section shows the `--` form (one sentence; the rewrite is ticket 05)
- [ ] a query with no hit prints `no matches` and exits 0; in a scoped search with 0 outside matches the `+0` line is absent; with 3 it is `+3 matches under other tags (--all)`; `--json` keeps `other_tags`
- [ ] `lorekeep --version` prints `lorekeep 0.1.1` (bump `pyproject.toml`); `status` without `--rules` ends at `Freshness window`; `status --rules` prints the rules as today
- [ ] the flag-vs-`--help` test in `tests/test_skill.py` passes with the new flags documented
