# 01: `search` answers a question in one call

**What to build:** A plain query that no Section matches whole is rerun as an OR of its content words (a fixed English stopword list dropped), ranked by BM25, printed after one stderr line `lorekeep: note: no Section has every word; these have most of them`; `--json` carries `"relaxed": true`. `no matches` is printed only when no word matches anywhere. `--exact` is unchanged. Decisions: `spec.md` › Search.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] over the three fixtures of `tests/test_search_lines.py`, `search 'which rail type validates tool call arguments'` prints the note and then the `rail-types` Section whose line holds "Execution rails control and validate tool/function calls, their arguments" as the first result, at that line
- [ ] a query every word of which matches one Section prints no note and the same results as before; `--json` has no `relaxed` key, or `false`
- [ ] a query of stopwords only, or of words that match nothing, prints `no matches`, exit 0
- [ ] `--exact` with a phrase that is not in the text prints `no matches` and never relaxes
- [ ] `SKILL.md`'s search paragraph says one sentence on the note line; the flag test passes
