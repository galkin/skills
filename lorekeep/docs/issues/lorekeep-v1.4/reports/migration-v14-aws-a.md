# aws-a — lorekeep fetch report

Batch `batch-aws-a`, 331 URLs (first half of the AWS Certified Generative AI Developer – Professional
guide's Sources). lorekeep 0.1.1, Store `~/orca/sources/agentic-system.design`, Tag `aws`.
Log: `log.jsonl` (331 lines, no retry lines — nothing qualified for a retry). Per-URL stderr:
`err/<n>.txt`, `n` = line number in the batch file; `rc.txt` holds `n exit url`.

## Numbers

- **URLs:** 331, each attempted once.
- **Exit 0 — 330:** `stored` 330. No `fresh`, `unchanged`, `changed`, `gone`, `error` or `skipped`.
  Every page was new to the Store.
- **Exit 1 — 1:** browser rendered a shell (1). No `ReadTimeout`, `ConnectError`, 5xx,
  `thin content`, `unsupported media type` or `could not convert`.
- **Exit 2:** 0.
- **Retries:** 0. The one error names no `ReadTimeout`/`ConnectError`/5xx, so the skill's rule
  says to report it and not retry it.
- **Converters:** `md-twin` 320 (every `docs.aws.amazon.com` page); `trafilatura 2.3.1` 10
  (9 `aws.amazon.com` + 1 `docs.amplify.aws`). No `raw-twin`, `markitdown …` or `verbatim`.
- **Authorities:** `primary` 320, `official` 9, `third-party` 1.
- **Publishers:** `aws` 329, `docs.amplify.aws` 1.
- **Size:** 3.77 MB of Markdown in total; 18 Versions under 2 KB (all `md-twin`).
- **Wall time:** 327 s (21:02:37Z → 21:08:04Z), about 1 s per URL, with five other workers on the
  same Store.
- **Warnings:** only the two lines for `docs.amplify.aws`, listed below. No missing code/tables
  warnings, no main-text % warnings, no canonical notes, no reading-rule warnings.

## To report to the owner

1. **Unknown host** — `docs.amplify.aws`, stored as `third-party`:
   `lorekeep: warning: docs.amplify.aws is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule`
   — https://docs.amplify.aws/react/frontend/ai/conversation/ai-conversation/
2. **`third-party` page the guide treats as primary** — the same page. AWS publishes Amplify
   Gen 2 documentation, and the guide cites it as AWS documentation, so a `[[hosts]]` rule
   (`docs.amplify.aws/` → publisher `aws`, `primary` or `official`) looks right. Until then it is context.
   `lorekeep: note: https://docs.amplify.aws/react/frontend/ai/conversation/ai-conversation is third-party under no rule`
3. **Error, not retried (no retry allowed for this error)** — https://aws.amazon.com/bedrock/pricing/
   `lorekeep: error: nothing stored for https://aws.amazon.com/bedrock/pricing/: the host rule names no Twin; no content: https://aws.amazon.com/bedrock/pricing/ yielded no text; the browser rendered a shell (0 characters after 3 attempts)`
   The browser already ran (three attempts) and still got a shell. The pricing page fills its
   tables client-side, so the guide's pricing claims have no stored Source.
4. Missing code/tables warnings: none. `thin content`: none. Reading-rule warnings: none.

## Spot checks

There were no `raw-twin`, `markitdown` or `verbatim` Versions in the batch, so I checked three
`md-twin` and two `trafilatura` Versions. No JSON line had a `version` field, and `path` was the
Version `<stem>.md` in all 330 lines, so for these pages the Reading and the Version are the same
file. A Twin has no Original to compare against (`original.stored: false`).

1. **md-twin, smallest (1482 B)** — `docs.aws.amazon.com--bedrock-latest-APIReference-API_RoutingCriteria.html--c38bc759.md`.
   Real content: `# RoutingCriteria`, `## Contents` with the one member, its type, range and
   whether it is required, then `## See Also` with the SDK links. It is small because the API shape
   has one member, not because something is missing. Noise: `<a name="…">` tags after every
   heading, and `C\+\+` escaped.
2. **md-twin, 1506 B** — `…bedrock-agentcore-latest-devguide-how-it-works-evaluations.html--87219a4e.md`
   and **1681 B** `…gateway-targets-mcp.html--f21fcfb4.md`. Both are hub pages: a short intro
   paragraph, then a `**Topics**` list. The Markdown is complete, but the topic links are
   relative `.md` paths (`evaluations-terminology.md`) that point at no stored file and no web URL.
   Across the batch, 263 of 320 Twins have relative `.md` links and all 320 have `<a name>` tags.
3. **md-twin with code + table + inline HTML (3825 B)** — `…bedrock-latest-userguide-latency-optimized-inference.html--b7a60e7a.md`.
   Clean: the note, the prose, a `performanceConfig` code fence and the provider/model/region table
   are all there. The table cells hold `<br />` for the region lists. Fences have no language
   (` ``` ` rather than ` ```json `).
4. **trafilatura, smallest (3665 B), `official`** — `aws.amazon.com--documentation-overview-kiro--8dce6cfe.md`
   against its 306 KB Original. The Original has 14 h1–h3. The Version keeps the 10 content
   headings (Kiro Documentation … Additional Information) with their paragraphs and drops the 4
   footer headings (Learn, Resources, Developers, Help). The Version is cleaner and loses no
   content. The Original has no `<pre>` and no `<table>`.
5. **trafilatura, the `third-party` warned page** — `docs.amplify.aws--react-frontend-ai-conversation-ai-conversation--314991cb.md`.
   It is the page's content: 11 `<pre>` blocks in the Original and 11 fences in the Version. It
   dropped the site banner ("Introducing AWS Blocks …"). Two problems: the headings carry their
   self-links (`## [Introduction](https://docs.amplify.aws/…/#introduction)`), so the search
   heading path shows link markup, and the fences have no language even though the code is TSX.
   It keeps a stray `[See Build a Backend →]` line above the H1.
6. **Also looked at, trafilatura, largest (63 KB)** — `aws.amazon.com--bedrock-faqs--7c5bac5d.md`.
   All 13 FAQ sections are present (General … Amazon Bedrock in SageMaker Unified Studio). The
   footer "Did you find what you were looking for today?" is still there as an `##` heading.
   The strands blog post has 5 `<pre>` in its Original and 5 fences in its Version, and its headings
   are complete (45 in the Version against 42 h1–h3 in the Original).

## Search

All with `LOREKEEP_TAG=aws`.

1. **Plain** — `lorekeep search 'latency optimized usage quota' --limit 3` → the right file
   (`…latency-optimized-inference.html--b7a60e7a.md`) and the right section, with the snippet
   showing the answer ("Once you reach the [usage] [quota] for [latency] …"). **But `:19` is the
   wrong line:** line 19 is `<a name="latency-optimized-inference"></a>`, which matches `latency`
   and `optimized` inside the anchor id. The sentence that answers the query is on line 34. So
   `file:line` pointed at the section, not the answer. The query also printed
   `+3 matches under other tags (--all)`.
2. **`--exact` identifier** — `lorekeep search --exact performanceConfig --limit 3` → InvokeAgent:51,
   InvokeFlow:45, RetrieveAndGenerate:55, each a correct line inside the Request Syntax fence. Good.
   **Trap:** `--exact 'model-id+latency-optimized'` → `no matches`, because the Twin stores
   `model-id\+latency-optimized`. Only `--exact 'model-id\+latency-optimized'` finds it (line 34,
   correct). The skill documents `\_` and `\*` but not `\+`.
3. **Needs `--all`** — `lorekeep search 'jailbreak detection perplexity' --limit 2` → `no matches`
   / `+4 matches under other tags (--all)`. With `--all`, both hits were NVIDIA guardrails pages
   and the lines were right (`…jailbreak-protection…:16`, `…configuration-reference…:378`). The
   files are under `.cache/readings/`, not at Store root: search answers from the Reading, a path
   that no `get` in this batch returned.

## Friction

### The brief

- `export LOREKEEP_aws=aws` is presumably a typo for `LOREKEEP_TAG=aws`. As written, `get` would
  exit 2 with no Tag. I used `LOREKEEP_TAG=aws` because `aws` is the only Tag the brief hints at;
  the brief should state the Tag in so many words.
- "open the file at `path` (the Reading) and, where `version` differs from `path`, the Version
  too" — lorekeep 0.1.1 printed no `version` field, and `path` was the Version for every page. The
  brief describes a JSON shape this tool does not emit, or one that appears only for pages with a
  Reading; it should say which.
- "a `raw-twin`, a `markitdown …`, a `verbatim` if your batch has them" was fine. Saying ahead of
  time that the AWS half is about 97% `md-twin` would have saved a look.
- It did not say whether `err/<n>` counts from 0 or 1, or whether every URL gets a file. I used
  the 1-based batch line and wrote all 331, empty ones included.
- "Record the wall time" — 331 fetches took 5.5 min, not "a while". The expected scale would help
  me pick between waiting and polling.

### The skill

- **Readings are not in the skill at all.** `status` prints `Readings: 85 of 377 Versions, 8 rules`,
  search `--all` returns paths under `.cache/readings/`, and the brief speaks of "the Reading", but
  neither `SKILL.md` nor `references/store.md` says what a Reading is, whether `get` returns it in
  `path`, or how to cite a `file:line` that lies in a Reading. (It is cited by the `url` field of
  the `--json` result, I assume.)
- "`\_` and `\*` in the text match `_` and `*`" — incomplete. AWS Twins escape `+` (`C\+\+`,
  `model-id\+latency-optimized`), and `--exact` with a plain `+` finds nothing. The skill should
  say that `--exact` matches the Markdown as stored, escapes included, or list every escape.
- "`file:line` is the matching line: open the file there" — in practice it is the first line of
  the Section that holds any query word, and in a Twin that is often the `<a name="…">` anchor
  line. It can sit 15 lines above the answer.
- "Exit `0` can still be a menu … open a Version under 2 KB, compare it with its Original" — a Twin
  has no Original (`original.stored: false`), and every one of my 18 sub-2 KB Versions was a Twin.
  The skill does not say what to compare a small Twin with; I judged it from the text alone.
- On "`the browser rendered a shell`" the skill says only that `thin content` "needs the browser
  … which waits longer before `rendered a shell`". It does not say what to do when the browser
  itself already rendered a shell (my one error). I inferred: not retryable, report it.
- `LOREKEEP_TAG` "set by the brief and never chosen by you" — with the brief's typo I had to choose
  anyway. A line on what to do when the brief's Tag is missing or malformed (ask through the
  coordinator, or stop) would remove the guess.
- What worked well: the stderr table, the retry rule, and the JSON-line log format were clear and
  enough on their own.

### The tool

- **Search line pointers land on HTML anchors.** Every Twin keeps `<a name="…">` after each
  heading (320/320). The anchor ids hold the page's words (`latency-optimized-inference`), so plain
  search matches them and reports that line. Either strip `<a name>` from Twins at store time or
  skip anchor-only lines when choosing `line`.
- **Twin escapes break `--exact`.** `\+` (and likely `\-`, `\.`, `\(`) stay in the stored Markdown.
  Normalise Markdown escapes on both sides of `--exact`, or index an unescaped text column.
- **Relative `.md` links in Twins** (263/320) such as `[Evaluators](evaluators.md)` resolve to
  nothing. Resolving them against `original.url` would make them citable URLs.
- **Code fences lose their language** in both trafilatura and the AWS Twins (` ``` `). This is
  harmless for search, but a guide writer copying a snippet has to guess the language.
- **trafilatura keeps self-link headings** (`## [Introduction](…#introduction)`) on
  docs.amplify.aws, so the search heading path carries the URL. Unwrap a heading's sole link.
- The `bedrock/pricing` error line is long and repeats the URL three times
  (`nothing stored for <url>: … no content: <url> yielded no text; …`). The URL once plus a short
  kind (`kind=shell`) would be easier to tally; I had to regex it out to count errors by kind.
- `get --json` printed no `version`/Reading field, while search returns Reading paths. A run cannot
  tell from its own log which file search will point at.
- What worked well: 330/331 on the first pass in 5.5 min with six concurrent workers and no lock
  contention I could see; empty stderr for 329 URLs; one JSON line per call.
