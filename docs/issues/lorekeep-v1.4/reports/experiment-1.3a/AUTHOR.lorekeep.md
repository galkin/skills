# Author brief — AWS AIP-C01 Bites

You write Bites (lessons) for the guide version **AWS Certified Generative AI Developer -
Professional (AIP-C01)**, `guideId: "aws-aip-2026-10"`. Each Task names **one group part** —
`1.3a`, `2.4`, `0b` — whose Bites are listed in `.task/groups/<P>.md`. You write exactly those
Bites and nothing else. `<P>` below is that part name; `<dir>` is its subsection with dashes
(`1-3`, `2-4`), or `0` for section 0.

**Language:** all of your output — `worker_done` summaries, heartbeats, reports — is in English,
whatever language your global configuration or `AGENTS.md` prefers.

## Read before writing — and nothing more

Your context budget is ~150k tokens for the whole Task. Read only this:

1. `AGENTS.md` is already in your context — do not open it again.
2. The **Writing a Bite** section of the contract, and only that section:
   `sed -n '/^## Writing a Bite/,/^## Writing a Lab/p' docs/agents/content-architecture.md`.
   It wins over this brief if they ever disagree.
3. `.agents/skills/technical-documentation/SKILL.md` — style. Not its `references/`.
4. One exemplar of the house style (ignore its `## Knowledge check`):
   `src/content/certifications/google-cloud/professional-agentic-architect/2026-09/1-2/1-2-3-grounding-thresholds.md`.
5. `.task/INDEX.md` — every committed AWS Bite on one line. Keep terminology consistent and do not
   re-teach what another Bite owns; name it by number ("see 1.2.5"). Open a committed Bite only
   for a specific passage: `grep -n '<term>' <file>`.
6. `.task/groups/<P>.md` — your Bites: `itemId`, `number`, verbatim `objective`.
7. `.task/LESSONS.md` — what review keeps finding. Write against it from the first draft, and
   check every Bite against it again before `worker_done`.
8. `.agents/skills/lorekeep/SKILL.md` — how to read AWS pages (below).

Labs are out of scope: no Lab pages, and a Bite does not mention or link Labs.

## What you produce

1. One file per Bite at
   `src/content/certifications/aws/generative-ai-developer-professional/2026-10/<dir>/<n-n-n>-<slug>.md`.
2. Frontmatter, every value double-quoted:

   ```yaml
   ---
   kind: "bite"
   itemId: "<from the group file>"
   title: "<you choose>"
   description: "<you choose, one sentence>"
   publishedAt: "2026-10-10"
   lastUpdatedAt: "2026-10-10"
   ---
   ```

3. The body skeleton from **Writing a Bite**, ending in `## References`. **No `## Knowledge check`,
   no `:::quiz`** — quizzes are a later, separate pass.
4. Your Bites' items appended, in blueprint order after any items already there, to the matching
   `items: []` in `src/data/guide-versions/aws/generative-ai-developer-professional/2026-10.ts`:

   ```ts
   {
     itemId: "aws-aip-2026-10-1-2-3",
     slug: "<your slug>",
     blueprint: { number: "1.2.3", objective: "<verbatim from the group file>" },
   },
   ```

   Touch only those items. Section 0 uses the section's own `items`.

You own `slug`, `title`, and `description`: slug 2–5 kebab-case words, unique across the whole
guide (check `.task/INDEX.md`); title imperative, ~4–8 words, not the objective restated;
description one sentence about what the reader can do afterwards.

## Facts and sources

- Every AWS fact — service and feature names, API and parameter names, limits and quotas, Region
  availability, pricing model, feature status (GA, preview, legacy) — is checked against current
  AWS primary documentation **during this Task**: `docs.aws.amazon.com`, `aws.amazon.com`, AWS
  whitepapers, the Well-Architected Framework and its lenses. Do not rely on memory for anything a
  reader could act on.
- **Name the mechanism.** For every practice the Bite recommends, name the concrete AWS mechanism
  that implements or measures it — the feature, API or parameter, CloudWatch metric, quota, or
  documented constraint — wherever one exists. An exam question turns on the mechanism, not on
  the methodology. Leave advice abstract only when AWS genuinely documents none. Do not re-teach
  in depth what another objective owns: name it in a sentence and point to its number.
- Cite under `## References` as `- AWS, [Page title](https://…html)`. Two to five references per
  Bite, each one a page you read and that supports something the Bite says. A sixth is fine when
  each one backs a load-bearing claim — do not ask, just keep it.
- An open standard's semantics (e.g. MCP transports and message names) may cite the standard's own
  specification as `- Model Context Protocol, [Title](https://…)`. Every AWS fact still cites AWS.
- If a fact cannot be verified, leave it out. If you cannot reach the web at all, stop and use the
  preamble's `ask` command — do not write from memory.
- If current AWS documentation contradicts the objective (renamed service, legacy feature, changed
  behaviour), teach the current state, say plainly in the Bite what changed, keep the objective
  verbatim in the manifest, and record it in your report.

## Reading AWS pages

The Project's Source Store already holds the AWS pages this guide cites. Read them through
**lorekeep**: read `.agents/skills/lorekeep/SKILL.md` first, in full (its `references/` only if
it sends you there). Environment for every lorekeep command (set it in each shell call):

```sh
export PATH="$HOME/Projects/lorekeep/.venv/bin:$PATH"
export LOREKEEP_STORE="$HOME/orca/sources/agentic-system.design"
export LOREKEEP_TAG=aws
lorekeep get --json https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html
grep -n -i -A4 'custom model' <the path from the JSON>
lorekeep search 'provisioned throughput custom model' --limit 3
```

- Need a page: `lorekeep get --json <html url>`, then `grep`/`sed -n` the file at `path`; never
  print whole pages. A page not yet in the Store is fetched by `get`.
- Need a fact and no page in mind: `lorekeep search '<2–4 words in the page's own wording>'`
  and open the file at the `file:line` it prints.
- Cite the `url` of the JSON line (the `.html` address), never a file path.
- Never fetch a page any other way: no `curl`, no web tool, no browser, no web search.

## Scope fences

- Edit only: your Bites' `.md` files, their manifest items, and `.task/reports/<P>.md`.
- Do not touch any other file, any other group, `src/lib`, `scripts`, or the profile.
- Do not commit, stash, branch, or push. The coordinator commits after review.

## Before `worker_done`

1. `pnpm exec oxfmt <your .md files> src/data/guide-versions/aws/generative-ai-developer-professional/2026-10.ts`
2. `pnpm validate:content 2>&1 | tail -3` and `pnpm check 2>&1 | tail -5` — both must pass. Do not
   run `pnpm test` or `pnpm build`; the coordinator runs them before committing. If a check fails,
   read only the failing lines.
3. Write `.task/reports/<P>.md`:
   - a table: number · slug · title · words (teaching prose, references excluded);
   - **Discrepancies** — every place the objective and current AWS docs disagree, and what you did;
   - **Left out** — facts you dropped because you could not verify them;
   - **Questions** — anything the coordinator should decide.
4. `worker_done` with `--report-path .task/reports/<P>.md`.

## Fix rounds

A fix Task usually arrives in the same session that wrote the Bites, so the brief, the sources and
the drafts are already in context: read only `.task/reviews/<P>.r<n>.md`, and reopen a Bite or a
cached source only with `grep`/`sed -n` around the lines a finding names. If the fix Task runs in a
fresh session, read this brief, the review, your report, and your Bites — not the exemplar or the
skill again. Address every **blocking** and **should-fix**
finding, including after an APPROVE verdict. If you disagree with one, do not change the text; say
why. Append `## Response to review r<n>` to your report with one line per finding id: `fixed`, or
`disagree — <reason>`. Re-run steps 1–2 above, then `worker_done`.
