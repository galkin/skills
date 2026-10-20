# 01: `search` answers a question in one call

**What to build:** A plain query that no Section matches whole is rerun as an OR of its content words (a fixed English stopword list dropped), ranked by BM25, printed after one stderr line `lorekeep: note: no Section has every word; these have most of them`; `--json` carries `"relaxed": true`. `no matches` is printed only when no word matches anywhere. `--exact` is unchanged. Decisions: `spec.md` › Search.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] over the three fixtures of `tests/test_search_lines.py`, `search 'which rail type validates tool call arguments'` prints the note and then the `rail-types` Section whose line holds "Execution rails control and validate tool/function calls, their arguments" as the first result, at that line
- [x] a query every word of which matches one Section prints no note and the same results as before; `--json` has no `relaxed` key, or `false`
- [x] a query of stopwords only, or of words that match nothing, prints `no matches`, exit 0
- [x] `--exact` with a phrase that is not in the text prints `no matches` and never relaxes
- [x] `SKILL.md`'s search paragraph says one sentence on the note line; the flag test passes

## Comments

**2026-10-17** — implemented on `galkin/lorekeep-v12-01`.

- **The tool.** `search` runs a plain query as before (every word, FTS5 AND). When that finds no
  Section in scope and dropping the stopwords leaves content words other than the query's own,
  it runs again as an `OR` of those words (`Reader.search(..., any_word=True)`, the same BM25
  order and snippet) and, if that finds anything, prints `lorekeep: note: no Section has every
  word; these have most of them` on stderr (text and `--json` alike) before the results; `--json`
  then carries `"relaxed": true` and has no `relaxed` key otherwise. A relaxed hit's `line` is the
  Section's first line holding the most distinct content words, not the first holding any: the
  `rail-types` Section's first such line is the `> Apply input, … output rails` blurb above the
  answer. The stopword list is fixed: 127 English function words (pronouns, articles,
  prepositions, auxiliaries, question words) in `src/lorekeep/stopwords.py`; no new dependency. `--exact` is untouched.
- **Tests** (`tests/test_search_lines.py`), one per criterion: the question over the three
  pages; a query one Section matches whole (no note, no key, the hits of the AND query); a query
  of stopwords and one of words found nowhere (`no matches`, exit 0, empty stderr); `--exact`
  with the question as a phrase.
- **`SKILL.md`** (249 lines, under the 250 of its test): one sentence on the note line in the
  `search` paragraph; the question example now shows the note and the relaxed answer
  (`--limit 1`; line 37, the same Section as the keyword example); the `--json` paragraph says
  `"relaxed": true` comes with the note. `test_the_search_examples_are_what_search_prints` now
  takes an example's `lorekeep: note:` lines as stderr (each must be printed there) and the rest
  as stdout. No room left for a row in the stderr table; the paragraph names the line instead.
- **Where the ticket was wrong.** `tests/test_search_lines.py` had two fixtures, not three
  (`trtllm-kv-cache.v1`, `vllm-cli-serve.v1`), and neither holds the `rail-types` Section. Added
  `tests/fixtures/guardrails-rail-types.twin`: the Store's Version of that page is a Fern Twin
  (`original.stored: false`), so its body, whose `sha256` is the Version's `c0162b5b…`, is the
  response received; it is recorded whole (3.5 KB) with its `etag`. The test indexes it beside the
  other two.
- **Decisions the ticket and spec left open.** "When that finds nothing" is read as nothing *in
  scope*: a Run's Tag with no whole match is relaxed even when other Tags have one, and the
  `+N matches under other tags` line then counts the relaxed query (the query whose results are
  printed). When the relaxed query finds nothing either, the output is the AND query's (`no
  matches`, its own other-Tags count, no note). A query with no stopword and one word is not
  rerun, since its `OR` is the same query.
