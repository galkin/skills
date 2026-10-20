# Author brief — AWS AIP-C01 Bites

Guide version **AWS Certified Generative AI Developer - Professional (AIP-C01)**,
`guideId: "aws-aip-2026-10"`. A Task names one group part — `1.3a`, `2.4`, `0b` — whose Bites
are listed in `.task/groups/<P>.md`. `<P>` below is that part name; `<dir>` is its subsection
with dashes (`1-3`, `2-4`), or `0` for section 0.

## What to read

1. The **Writing a Bite** section of the contract, and only that section:
   `sed -n '/^## Writing a Bite/,/^## Writing a Lab/p' docs/agents/content-architecture.md`.
2. `.agents/skills/technical-documentation/SKILL.md` — style. Not its `references/`.
3. One exemplar of the house style (ignore its `## Knowledge check`):
   `src/content/certifications/google-cloud/professional-agentic-architect/2026-09/1-2/1-2-3-grounding-thresholds.md`.
4. `.task/INDEX.md` — every committed AWS Bite on one line. Keep terminology consistent and do not
   re-teach what another Bite owns; name it by number ("see 1.2.5").
5. `.task/groups/<P>.md` — your Bites: `itemId`, `number`, verbatim `objective`.
6. `docs/pipeline/LESSONS.md` — what review keeps finding. Write against it from the first draft, and
   check every Bite against it again before you finish.

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
4. Your Bites' items inserted, in blueprint order among any items already there, into the matching
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

## Sources

- Primary documentation is `docs.aws.amazon.com`, `aws.amazon.com`, AWS whitepapers, the
  Well-Architected Framework and its lenses.
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

- Cite under `## References` as `- AWS, [Page title](https://…html)` — the `.html` URL, never the
  `.md` one. An open standard cites as `- Model Context Protocol, [Title](https://…)`.

## Checks

- Formatter: `pnpm exec oxfmt <your .md files> src/data/guide-versions/aws/generative-ai-developer-professional/2026-10.ts`
- Checks: `pnpm validate:content 2>&1 | tail -3` and `pnpm check 2>&1 | tail -5`. Do not run
  `pnpm test` or `pnpm build`; the coordinator runs them before committing.
