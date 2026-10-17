# aws-b: second half of the AWS AIP guide's Sources

Worker task `task_331daf1820b5`, dispatch `ctx_1728f65f5f33`. lorekeep as installed at
`~/Projects/lorekeep/.venv/bin` (`lorekeep --version` → `lorekeep 0.1.1`), Store
`~/orca/sources/agentic-system.design`, Tag `aws` (passed as `LOREKEEP_TAG=aws`; see Friction › the brief).

Files here: `log.jsonl` (331 lines, one per URL, no retry lines because nothing failed),
`exits.txt` (`<n> <exit> <url>`), `err/<n>.txt` (stderr per URL, empty for 329 of 331), `time.txt`.

## Numbers

| What | Count |
| --- | --- |
| URLs in the batch | 331 |
| Exit 0 | 331 — `outcome` `stored` 331 (no `fresh`, `unchanged`, `changed`, `gone`, `error`, `skipped`) |
| Exit 1 | 0 |
| Exit 2 | 0 (the loop's; one manual probe with the brief's environment exited 2, see Friction) |
| Retries | 0 — nothing named `ReadTimeout`, `ConnectError` or a `5xx` |
| Converters | `md-twin` 329, `trafilatura 2.3.1` 2; no `raw-twin`, `markitdown`, `verbatim`, browser |
| Authorities | `primary` 330, `third-party` 1 |
| Publishers | `aws` 329, `mcp` 1, `ui.docs.amplify.aws` 1 |
| Readings (`version` in the JSON) | 1 (`modelcontextprotocol.io/specification/2025-11-25/server/tools`) |
| `url` ≠ `requested_url` | 0; `asked` ≠ `url` once (trailing slash dropped: `https://docs.aws.amazon.com/solutions/multi-agent-orchestration-on-aws/`) |
| Versions under 2 KB (file size, frontmatter included) | 8, all genuine short AWS pages (see Spot checks) |
| Wall time | 294 s (2026-10-17T21:02:51Z → 21:07:45Z), ≈0.9 s per URL, sequential, five other workers on the same Store |

## To report to the owner

1. **Unknown host** — `ui.docs.amplify.aws`, stored as `third-party`:
   - `https://ui.docs.amplify.aws/react/getting-started/accessibility` —
     `lorekeep: warning: ui.docs.amplify.aws is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule`
     and `lorekeep: note: https://ui.docs.amplify.aws/react/getting-started/accessibility is third-party under no rule`.
   - **The guide treats it as primary**: Amplify UI is AWS's own component library documenting its
     own product (`aws-amplify/amplify-ui`), so by the skill's definition it is `primary` under a
     host rule (publisher `aws`). Until the owner adds `ui.docs.amplify.aws/`, it is context only.
2. **Error lines** — none.
3. **`third-party` pages the guide treats as primary** — the Amplify UI page above; nothing else.
4. **Missing code/tables warnings** — none printed.
5. **`thin content`** — none.
6. **Main-text warnings (`the Markdown holds N%`)** — none printed, **but one page lost most of its
   text silently** (not a warning the skill names; reported because it changes what the guide may cite):
   `https://docs.aws.amazon.com/solutions/multi-agent-orchestration-on-aws` (trafilatura). The
   Version keeps ≈22% of the words of the Original's `<main>` (453 of ≈2047, my count with scripts
   and `nav` stripped), just above the 20% threshold. Lost: every step of the four "How it works"
   architecture tabs (≈40 paragraphs, `Step 1` … `Step 7`, `4a`–`4d`, `5a`–`5d`; only the literal
   `Step 1` survives, glued to a link), the "Go to sample code" link, and the body of "Accelerate
   customer support resolution", which moved above `## Overview` and left its heading empty. Any fact
   about the guidance's architecture must be read from the `.orig.html`.
7. **Reading-rule warnings (`rule <name> removed N …`)** — none printed. One Reading was made
   (MCP tools page) without any stderr line.
8. **Other warning printed** — `https://docs.aws.amazon.com/sagemaker/latest/dg/inference-recommender-prerequisites.html`:
   `no headings; search answers with the whole page as one Section` (24.9 KB, one `#` title and a
   numbered list of steps with code; content is complete).

## Spot checks

No `raw-twin`, `markitdown` or `verbatim` Version in this batch, so six checks over the two
converters present, smallest and warned first.

| Version | Converter | Verdict |
| --- | --- | --- |
| `docs.aws.amazon.com--wellarchitected-latest-framework-the-pillars-of-the-framework.html--9cc1eaea.md` (1648 B, smallest) | md-twin | The page's content: `#` title, one paragraph, a **Topics** list of six pillars. Short because the page is an index page, not a menu. No Original to compare (Twin). Links are relative to the Twin (`operational-excellence.md`), not to citable pages. |
| `…secretsmanager-latest-userguide-rotating-secrets.html--c716ab1f.md` (1660 B), `…eventbridge-latest-userguide-eb-rule-retry-policy.html--ed94e37a.md` (1807 B), `…bedrock…model-evaluation-report…`, `…prompt-management-deploy…`, `…codedeploy…API_AutoRollbackConfiguration…` | md-twin | All the page's content: titles, prose, lists, the API reference's `Type`/`Valid Values`/`Required` fields. Every AWS Twin keeps the publisher's `<a name="…"></a>` anchor lines under each heading. |
| `…sagemaker-latest-dg-inference-recommender-prerequisites.html--3f35e881.md` (24.9 KB, warned `no headings`) | md-twin | Complete: title, note, numbered steps with fenced Python. The warning is accurate in effect (one Section) but its wording is not: the page has an `#` heading, just no `##`. |
| `modelcontextprotocol.io--specification-2025-11-25-server-tools--b372c48e.md` (Version) vs `.cache/readings/…--b372c48e.md` (Reading) | md-twin + Reading | The Reading is cleaner: it drops only the Mintlify banner (`> ## Documentation Index` / `Fetch the complete documentation index at: …llms.txt`); every other line is the Version's. It keeps the MDX tags (`<div id="enable-section-numbers" />`, `<Warning>`). Its frontmatter drops `publisher`, `authority`, `converter`, `fetched_at`, `original` and adds `version`, `sha256` (of the Reading), `rules`. |
| `docs.aws.amazon.com--solutions-multi-agent-orchestration-on-aws--bb4ccc50.md` (4.9 KB) vs `.orig.html` (86 KB) | trafilatura 2.3.1 | **Lost most of the page** (see To report, item 6): headings and benefits survive, the architecture steps and the sample-code link do not, one heading is left empty. No warning. |
| `ui.docs.amplify.aws--react-getting-started-accessibility--b0b7d60d.md` (5 KB) vs `.orig.html` (369 KB) | trafilatura 2.3.1 | The page's content: intro, `##`/`###` headings, three code fences (unlabelled, the page's are `jsx`), the "related" cards flattened into one-line links (`[Accessible input labelsLearn about …](…)`, title and blurb run together). Nothing missing that I could see. |

## Search

All with `LOREKEEP_TAG=aws`, each ≈0.2 s.

1. Plain — `lorekeep search 'EventBridge retry policy dead-letter queue' --limit 3`: two results, the
   right two pages and the right Sections (`Subscribing to events on a Custom Event Bus > Retries and
   dead-letter queues`, `How EventBridge retries delivering events`). **`file:line` did not point at the
   answer**: `eb-rule-retry-policy…:19` is the `<a name="eb-rule-retry-policy"></a>` line under the
   title; the dead-letter sentence is line 29, the retry defaults line 25. Probing further:
   `'retries 24 hours 185 times'` printed `:21` with a snippet from line 25 (`…By default, EventBridge
   [retries] sending the event for [24] [hours] and up to [185] [times]…`), and `'avoid losing events
   dead-letter'` printed `:21` with a snippet from line 29. The snippet is right, the line is the
   Section's first lines. On `eb-custom-bus-subscribers` the line was right once (`RetryPolicy default
   attempts` → `:70`) and off once (`:68`, the anchor, for a match on line 70).
2. Exact — `lorekeep search --exact DEPLOYMENT_STOP_ON_ALARM`: one result,
   `…API_AutoRollbackConfiguration.html--7fbc08db.md:34`, exactly the `Valid Values` line. Correct.
   `--exact '185 times'` → `:25`, also exact.
3. Needing `--all` — `lorekeep search 'NeMo Guardrails jailbreak detection'`: `no matches` and
   `+8 matches under other tags (--all)`; with `--all`, a NeMo Agent Toolkit README `:359` and two
   NeMo Guardrails Readings (`.cache/readings/…jailbreak-protection…:124`, the support-matrix row
   `` `jailbreak detection model` ``, correct line). The hint line worked as described.

## Friction

### The brief

- `export LOREKEEP_aws=aws` is not a variable lorekeep reads. With it, `get` exits 2:
  `lorekeep: error: get needs the Run's Tag: set LOREKEEP_TAG or pass --tag`. I read the intent as
  `LOREKEEP_TAG=aws` and used that; the brief should say `export LOREKEEP_TAG=aws`.
- It sends me to `.agents/skills/lorekeep/SKILL.md`, but that copy (untracked in this worktree) is
  older than the installed tool: it has no Readings, no `version` field, no `rule … removed` warning.
  The brief's own words ("open the file at `path` (the Reading) and, where `version` differs from
  `path`") only make sense with `~/Projects/lorekeep/src/lorekeep/skill/SKILL.md`, which I found by
  diffing. Say which skill copy is authoritative, or refresh the vendored one first.
- "331 fetches take a while … run it in the background": it took 294 s. Fine, but a figure
  ("≈1 s per URL") would let a worker pick a foreground timeout and skip a monitor.
- "a `raw-twin`, … a `markitdown …`, a `verbatim` if your batch has them": an AWS docs batch is
  ~99% `md-twin`; saying so up front would have saved a guess at what "five of different converters"
  means when only two exist.
- The `exit 1` log shape is given; the shape of a *retry* line is not (append a second line? replace?).
  Moot here, but I would have had to guess.
- "the counts (stored / fresh-or-unchanged / errors)" for `worker_done`: clear.

### The skill (the vendored copy, read as instructed)

- Stale against the tool (above): `path` silently becomes `.cache/readings/…` for some pages, and
  `search` returns `.cache/readings/…` files, with nothing in this copy explaining either. Its
  `store.md` does not mention `.cache/readings` or the Reading frontmatter (`version`, `rules`) either.
- `lorekeep --version` prints `lorekeep 0.1.1`, so the skill's "names the version" does not let a
  worker tell which skill matches the tool.
- "open a Version under 2 KB, compare it with its Original": a Twin has no Original
  (`original.stored: false`), and 2 KB counts ~600 bytes of frontmatter. For 8 AWS Twins under 2 KB
  I had nothing to compare against; I read them and judged them complete index pages. Say what to do
  for a Twin, and whether 2 KB is the file or the body.
- The stderr table has no row for `no headings; search answers with the whole page as one Section`;
  it is only in the `lorekeep get` prose ("a long page with no headings (`get` warns) is one Section").
  I had to infer it is informational, not reportable.
- No rule covers a page that loses most of its text above the 20% line (solutions page, 22%). The
  only check the skill prescribes for exit-0 losses is "under 2 KB"; a 4.9 KB Version that dropped
  ≈1600 words passes every stated test. A rule like "for a `trafilatura` Version of a page with tabs
  or steps, compare headings with the Original" would have caught it; today it was luck.
- How to cite a page a Twin links to: AWS Twin links are `rotate-secrets_managed.md`, relative to the
  Twin. The skill says `.md` addresses "are Twins only under a host rule" but not how to turn such a
  link into a citable `url`.
- "Put everything this skill says to report in your final report": the list is spread over four
  places (the stderr table, `authority`, the exit-1 list, the 2 KB rule). One checklist would help.
- Worked well: the exit-code contract, `asked`/`url`/`requested_url`, and the `+N matches under
  other tags (--all)` hint.

### The tool

- **`search` `file:line` for plain queries points at the Section's first lines, not the match** (see
  Search 1): `:19`/`:21` for matches on 25 and 29. `--exact` lines were exact. The skill promises
  "`file:line` is the matching line: open the file there"; on AWS Twins with `<a name>` anchors it
  was not. The snippet is right, so a worker can grep for it, but that is an extra call per answer.
- **The 20% main-text warning is too coarse**: `solutions/multi-agent-orchestration-on-aws` kept
  ≈22% and lost every architecture step without a word on stderr. trafilatura drops tab panels
  (`Step 1` … `Step 7` in four tabs); a heading with an empty body (`## Accelerate customer support
  resolution`) could be its own warning.
- `lorekeep --version` → `0.1.1` while the tool has Readings (v1.3 per the owner's notes): the version
  string does not move with features.
- A Reading's frontmatter drops `publisher`, `authority`, `converter`, `fetched_at`; a worker who opens
  `path` (as told) cannot see the authority there and must go back to the JSON or open `version`.
- The Reading for the MCP page was made with no stderr line at all, so a log reader cannot tell from
  stderr which `get`s returned a Reading; only `version` in the JSON says so (fine with `--json`).
- `no headings` warning on a page that has an `#` title: it means "no `##`"; the wording sent me to
  open the file to check.
- AWS Twins keep `<a name="…"></a>` under every heading. Harmless to read, but they occupy the line
  the plain search points at and their ids (`eb-rule-retry-policy`) carry query words.
- Twin bodies end without a final newline (`cat` of two Versions runs `…(sustainability.md)=====`).
- trafilatura code fences lose the page's language (`jsx` on Amplify UI → bare ```` ``` ````), and
  card links run title and blurb together (`[Accessible input labelsLearn about …]`).
- Speed and locking: 331 sequential `get`s in 294 s with five other writers, no lock waits visible,
  no errors. Worked well.
