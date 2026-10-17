# lorekeep v1.2: what the second NVIDIA migration taught

## Problem Statement

Three Opus workers rebuilt the first Store on v1.1 through the rewritten skill (reports in
`../lorekeep-v1.1/reports/migration-v11-{aa,ab,ac}.md`): 379 URLs, 373 Versions, 0 unknown hosts,
0 lock trouble with three writers, 1.2 s per page. The flow works. What it still costs a Run, in
tokens and in trust, is in the three Friction sections, and the same items came back from all
three workers independently:

1. **A question gets `no matches`.** `search` requires every word of the query in one Section
   (an implicit FTS5 AND); the skill says "ranked by BM25", which a reader takes for ranking.
   Every worker lost a round-trip rephrasing a question into keywords.
2. **A Run cannot see what the tool knows.** A `third-party` verdict from the `github.com/`
   catch-all prints nothing, so the rule "report a third-party page the guide treats as primary"
   needs a scan of every JSON line. The missing-code warning prints only on the `get` that stores;
   a second worker hitting the same page (`fresh`) never sees it. The fragment of the asked address
   is dropped from `requested_url`, so a JSON-only log cannot tell `page#a` from `page#b`.
3. **Content loss without a warning.** A Sphinx toctree list dropped from a 1.3 KB page
   (Model-Optimizer `1_quantization.html`) passed the thin-content check because the check has an
   absolute floor (600 characters) before the ratio applies.
4. **The browser renders a shell.** `build.nvidia.com` pages and the Redoc `api-rag.html` load
   their content after the page is rendered; the browser step returns the document as soon as it
   loads, converts the menu, and the thin check does not run on browser output. The three such
   Versions were removed from the Store by hand before the first backup; the two model pages are
   still cited and not stored.
5. **Noise that reaches every Run.** NVIDIA's Fern Twins open with a 12-line llms.txt banner
   before the H1 (a `(top)` Section of boilerplate on 83 pages); Microsoft Learn's H1 is the whole
   `<title>`; PDFs (`markitdown`) have no `title` and keep ligatures (`proﬁle`, 249 times in NIST
   AI 600-1), so `--exact profile` misses them.
6. **A Project rule loses the default's Twin** (found in v1.1 acceptance, documented in
   `owner.md`, not fixed): the owner had to repeat `twin = "github-raw"` on four new GitHub rules
   this round.

## Solution

`search` answers a question in one call; `get` tells a Run everything it would otherwise have to
scan for; the converters stop leaking chrome and boilerplate; the browser waits for the page; host
rules inherit. Every change is in the tool or the skill; the Store's files, the Index schema (one
column) and the commands' flags do not change.

## Implementation Decisions

### Search (ticket 01)

- A plain query is run as today (every word, FTS5 AND). When that finds nothing, it is run again
  as an OR of its content words (stopwords of a fixed English list dropped), ranked by BM25, and
  the results are printed after one line `lorekeep: note: no Section has every word; these have
  most of them` on stderr. `no matches` means no word matched anywhere.
- `--json` adds `"relaxed": true` in that case.
- `--exact` is unchanged.

### What `get` tells a Run (ticket 02)

- `get --json` and `add --json` carry `asked`: the argument exactly as given (fragment included).
  `requested_url` stays the normalised one.
- A Version stored with a missing-code/table warning records it in frontmatter as `warnings`
  (a list of strings, written once with the Version), and `get` prints the Version's `warnings`
  on every return (`stored`, `fresh`, `unchanged`), prefixed `lorekeep: warning:`. The Index's
  `versions` table gains `warnings` (JSON text), `SCHEMA_VERSION` bumps.
- When the matched rule is a catch-all whose `authority` is `third-party` (`github.com/`, or no
  rule), `get` prints `lorekeep: note: <url> is third-party under the <prefix> rule (or: under no
  rule)`; once per `get`, on every return.
- The thin check drops its absolute floor for the ratio: a page whose Markdown text is under a
  fifth of the text of its `<main>`/`[role=main]`/`<article>` (not of the whole document) prints
  `lorekeep: warning: <url>: the Markdown holds N% of the page's main text` and the Version is
  stored with that warning. The existing `thin content` error (under 600 characters and under a
  fifth of the whole document) is unchanged.

### Browser (ticket 03)

- The browser step needs no per-host setting (owner's decision: no configuration, the tool
  escalates on its own). It renders in up to three attempts with Crawl4AI's documented
  `CrawlerRunConfig` parameters (`docs.crawl4ai.com/api/parameters/` › Page Navigation & Timing):
  1. `wait_until="networkidle"` (today: the default `domcontentloaded`, which snaps the page
     before its scripts have loaded the content);
  2. if the Markdown is thin, `delay_before_return_html=3.0` as well;
  3. if still thin, a `wait_for` `js:` condition that the main element's text has grown past the
     thin threshold, `wait_for_timeout=15000`.
- A page thin after the last attempt is an error `lorekeep: error: nothing stored for <url>: the
  browser rendered a shell (N characters after 3 attempts)`, not a Version.
- `scripts/smoke.py` stops expecting `milvus.io` to need the browser (it answers a plain client
  now); it proves the browser with a temporary `browser = true` rule instead.

### Converters (ticket 04)

- `md-twin`: a leading blockquote before the first heading that contains `llms.txt` or `For clean
  Markdown` is dropped (Fern's banner); nothing else of the publisher's Markdown changes.
- `trafilatura`: when the `<title>` is `<h1> - <site> | <site>`, the title and the inserted first
  heading use the `<h1>`'s text (Microsoft Learn); the rule is "the `<h1>` wins over `<title>`
  when both exist".
- `markitdown`: `title` from the PDF's metadata, else the first non-empty line; the Markdown has
  Unicode ligatures (`ﬁ ﬂ ﬀ ﬃ ﬄ`) normalised to their letters (NFKC on those code points only).
- A Version with no heading below the title and more than 20,000 characters prints
  `lorekeep: warning: <url>: no headings; search answers with the whole page as one Section`
  (EUR-Lex, OWASP). Recovering structure from such pages is out of scope.

### Host rules inherit (ticket 06)

- A rule that omits `twin` and `page_suffix` inherits both from the longest shorter-prefix rule
  of either layer that has them; a rule that names `twin` keeps its own. `browser` and `cut` are
  not inherited. `status --rules` prints inherited values marked `(inherited)`.
- The four GitHub rules in the first Store's `lorekeep.toml` keep their explicit `twin`; the
  README and `owner.md` paragraphs on repetition become one sentence on inheritance.

### The skill (ticket 05, documentation only, dispatched first)

`SKILL.md`: `search` needs 2–4 content words from the page's own wording, not a question, and
how a relaxed answer looks (after 01: the note line); an example of the exit-1 log line
(`{"url": …, "error": …}`); check `authority` in every JSON line (there is no warning for a
third-party verdict until 02); a Twin has no Original file (`original.stored: false`), its Markdown
is the text received; the `get --json` example is captured from a fixture that really has no host
rule (not the synthesised helm redirect); "the Original is `<stem>.orig.<ext>` beside the Version".
`store.md`: the `asked` field, the `warnings` field, `relaxed` (after 01–02). `owner.md`: `browser` on a rule; the issuer rule for laws — a law's text on its official journal
(EUR-Lex, the Federal Register, nist.gov for NIST) is `primary`; an institution's reproduction
(the Commission's AI Act Service Desk) is `official`, and a Run cites the journal.

## Testing Decisions

As v1.1: fixtures cut from the Store's Originals (`build.nvidia.com` model card rendered by the
browser and its loaded content; Model-Optimizer `1_quantization.html` with its toctree; a Fern
Twin with the banner; the NIST PDF's first pages; a Microsoft Learn page), one test per bullet
naming its fixture; `pytest`, `ruff`, `pyright` the gate; the skill tests of ticket 05 of v1.1
keep every flag honest.

## Out of Scope

- Recovering headings from EUR-Lex and OWASP pages.
- Near-duplicate Sources the guide cites under two addresses (`TensorRT-LLM/features/…` with and
  without `latest/`): a guide-side choice.
- The `tags.csv` rows left behind when a Version is removed by hand (three in the first Store):
  `status` counts rows, not Versions; a `tag` cleanup command is not planned.
- A `wait_for` host-rule key: the browser escalates on its own (owner, 2026-10-17).

## Further Notes

Decisions pending the owner, written into ticket 05 as above unless overruled: the issuer rule for
laws; whether `asked` is worth a JSON field against "log the raw address yourself". Ticket 05 is
dispatched at once; 01–04 and 06 wait for the owner's yes.
