# Reviewer brief — AWS AIP-C01 Bites

Guide version `aws-aip-2026-10`. A Task names one group part (`1.3a`, `2.4`, `0b`) and a review
round; `<P>` below is that part name. Your review goes to `.task/reviews/<P>.r<n>.md`.

## What to read

1. The **Writing a Bite** section of the contract, and only that section:
   `sed -n '/^## Writing a Bite/,/^## Writing a Lab/p' docs/agents/content-architecture.md`.
2. `.agents/skills/technical-documentation/SKILL.md`, **Quick Diagnostic** and **Scoring** only.
3. `docs/pipeline/briefs/aws-aip-lorekeep/author.md` — what the author was asked to do.
4. `.task/groups/<P>.md` — the Bites under review, with verbatim objectives.
5. `.task/reports/<P>.md` — the author's report, including declared discrepancies.
6. `.task/INDEX.md` — committed AWS Bites, one line each, for overlap and terminology.

## Sources

- Primary documentation is `docs.aws.amazon.com`, `aws.amazon.com`, AWS whitepapers, the
  Well-Architected Framework and its lenses. Every reference in a Bite must be one of these and
  must resolve. Exception: an open standard's own specification (e.g. MCP) for that standard's
  semantics only; any AWS claim still needs an AWS page.
- Pages come from the source store through lorekeep, never from the web. `get` returns the
  store's copy (the Markdown twin for `docs.aws.amazon.com`) and fetches only what it lacks; ask
  for the `.html` address:

  ```sh
  ~/Projects/lorekeep/.venv/bin/lorekeep get --json --store ~/orca/sources/agentic-system.design --tag aws https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html
  grep -n -i -A4 'custom model' <path from the JSON>
  ```

- To find a page or a fact the store already holds, search it first with 2–4 of the page's own
  words: `~/Projects/lorekeep/.venv/bin/lorekeep search --store ~/orca/sources/agentic-system.design --tag aws 'provisioned throughput custom'`; it prints `file:line`.
  Web search only to find the address of a page the store lacks, then `get` it.
- Never `curl` a page, never read the lorekeep skill or any other skill; these commands are all
  you need. Exit 1 from `get`: retry once on a timeout or a 5xx, otherwise record the URL and the
  error line in your report and do without the page.
- Cite the `url` from the JSON (it may differ from the address you asked), never a store path.

## Contract (any miss is blocking)

- Frontmatter: the six fields only, every value double-quoted, both dates `"2026-10-10"`, `itemId`
  matching `.task/groups/<P>.md`.
- Manifest entry: right group, blueprint order, `objective` byte-identical to the group file.
- Filename `<n-n-n>-<slug>.md` in the right directory; slug 2–5 kebab-case words, unique in the
  guide.
- Headings in the contract's order; `How it works` may be renamed. **No `## Knowledge check`, no
  `:::quiz`.**
- No link to another Curriculum item, to a Lab, or to the Google Cloud guide.
- Teaching prose roughly 900–1,400 words (references excluded). Outside 800–1,600 is blocking;
  inside but off-target is should-fix.

## Teaching, guide-specific

- Exam traps are plausible distractors for a Professional-level AWS exam, not straw men.
- Names the concrete AWS mechanism behind each recommended practice (feature, API, metric, quota,
  constraint) where AWS documents one. Abstract methodology where a mechanism exists is
  should-fix; name the missing mechanism and its AWS page.

## Checks

`pnpm validate:content 2>&1 | tail -3` and `pnpm check 2>&1 | tail -5`; both are read-only.
