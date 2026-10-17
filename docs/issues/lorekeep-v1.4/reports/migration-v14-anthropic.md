# Batch `anthropic` — lorekeep fetch report

lorekeep 0.1.1, Store `~/orca/sources/agentic-system.design`, Tag `anthropic` (see Friction › the
brief, item 1). Log: `log.jsonl` (219 lines, no retry lines), stderr per URL: `err/<n>.txt` where
`n` is the line number in `batch-anthropic`; exit codes per URL: `rc.txt`; loop: `run.sh`.

## Numbers

- **URLs:** 219 (one `get --json` each, sequential, while five other workers fetched).
- **Exit 0:** 217 — `stored` 203, `fresh` 14 (13 stored by the NVIDIA run at 17:23–17:25Z and
  now also tagged `anthropic`; 1 is my own duplicate: `…/claude-prompting-best-practices#long-context-prompting`
  after `…/claude-prompting-best-practices`). No `unchanged`, `changed`, `gone`, `error`, `skipped`.
- **Exit 1:** 2, one kind — "Twin answered 404; no text; the browser rendered a shell (358
  characters after 3 attempts)". **Exit 2:** 0.
- **Retries:** 0. Neither error names `ReadTimeout`, `ConnectError` or a `5xx`, so the skill says
  report, not retry.
- **Converters:** `md-twin` 152, `trafilatura 2.3.1` 53, `raw-twin` 6, `markitdown 0.1.8` 4,
  `trafilatura 2.3.1 via crawl4ai 0.9.5` 2 (browser path, both `www.hhs.gov`). No `verbatim`.
- **Readings:** 65 of 217 have `version` ≠ `path` (all `code.claude.com` and
  `modelcontextprotocol.io` Twins, plus EUR-Lex GDPR). `platform.claude.com` Twins have no Reading.
- **Authorities:** `primary` 183 (anthropic 139, nist 12, mcp 10, github 5 = docs.github.com,
  elastic 5, json-schema 3, git 2, microsoft 2, a2a/aws/python/eu/opentelemetry 1 each),
  `official` 17 (anthropic 10 = www.anthropic.com, google 5 = sre.google, owasp 2),
  `third-party` 17 (see below).
- **`url` ≠ `requested_url` (redirects to a different page):** 4 — see To report.
- **Wall time:** 307 s (2026-10-17T21:02:57Z → 21:08:04Z), ≈1.4 s per URL; the lock never showed.

## To report to the owner

**Errors (exit 1, not retried):**

- `https://platform.claude.com/docs/en/administration/usage-cost-api` —
  `lorekeep: error: nothing stored for https://platform.claude.com/docs/en/administration/usage-cost-api: no Twin: https://platform.claude.com/docs/en/administration/usage-cost-api.md answered 404; no content: https://platform.claude.com/docs/en/administration/usage-cost-api yielded no text; the browser rendered a shell (358 characters after 3 attempts)`.
  Probably a moved page: the batch also holds `https://platform.claude.com/docs/en/manage-claude/usage-cost-api`, stored fine (17 KB).
- `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-best-practices` —
  same error line shape (Twin 404, no text, shell of 358 characters after 3 attempts). Probably
  moved to `…/prompt-engineering/claude-prompting-best-practices`, stored fine from the same batch.

**Hosts in no host table (stored as `third-party`):**

- `academy.claude.com` — `https://academy.claude.com/tutorials/claude-enterprise-administrator-guide` (Anthropic's own; the guide treats it as primary)
- `claude.com` — `https://claude.com/solutions/government` (Anthropic's own; primary)
- `everpath-course-content.s3-accelerate.amazonaws.com` — the two exam guides, `…/Claude+Certified+Architect+–+Foundations+Exam+Guide.pdf` and `…/Claude+Certified+Architect+–+Professional+Exam+Guide.pdf` (Anthropic's official exam guides; the guides' primary source)
- `developers.google.com` — `https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall` (Google's own course; `official` like sre.google?)
- `ir-measur.es` — `https://ir-measur.es/en/latest/measures.html` (library docs; context is right)
- `pydantic.dev` — `https://pydantic.dev/docs/validation/latest/concepts/validators/` (vendor docs)
- `www.fedramp.gov` — `https://www.fedramp.gov/2026/agencies/use/`, `https://www.fedramp.gov/2026/agencies/use/initial/ssp/` (US government programme; likely `primary`/`official`)
- `www.hhs.gov` — `https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html`, `https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html` (HHS guidance on HIPAA; the regulator's own reading — `official` at least)

**`third-party` under the `github.com/` rule that the guide treats as primary** (Anthropic's own repositories):

- `https://github.com/anthropics/claude-code-action/blob/main/action.yml`
- `https://github.com/anthropics/claude-code-action/blob/main/docs/security.md`
- `https://github.com/anthropics/claude-code-action/blob/main/README.md`
- `https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/knowledge_graph/guide.ipynb`
- `https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/retrieval_augmented_generation/guide.ipynb`
- `https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/text_to_sql/guide.ipynb`

  A `github.com/anthropics/` rule would cover all six.

**Missing code blocks / tables:**

- `https://docs.github.com/en/rest/pulls/comments` — `0 code blocks / 19 tables of the page are missing from the Markdown` (not opened; REST reference pages put parameters in tables — the largest loss in the batch)
- `https://pydantic.dev/docs/validation/latest/concepts/validators/` — `10 code blocks / 0 tables …` (not opened; a validators page without its code is mostly lost)
- `https://git-scm.com/docs/git-worktree` — `1 code blocks / 0 tables …`
- `https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm` — `1 code blocks / 0 tables …`
- `1 tables` missing on six NIST/SEMATECH handbook pages: `…/prc/section1/prc131.htm`, `…/prc/section1/prc14.htm`, `…/prc/section2/prc242.htm`, `…/prc/section3/prc33.htm`, `…/prc/section4/prc47.htm`, `…/pri/section3/pri331.htm` (all `https://www.itl.nist.gov/div898/handbook/`). Spot check on `prc131`: a false alarm, see Spot checks.

**`thin content` / Markdown share warnings:** none. **Reading-rule warnings (`rule … removed`):** none.

**Not on the skill's report list, but a guide writer needs them:**

- Redirected to a different page (the guide's link is stale; cite the new `url`):
  - `https://docs.github.com/en/actions/learn-github-actions/variables` → `…/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables`
  - `https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions` → `…/how-tos/write-workflows/choose-what-workflows-do/use-secrets`
  - `https://docs.github.com/en/actions/sharing-automations/creating-actions/setting-exit-codes-for-actions` → `…/actions/how-tos/create-and-publish-actions/set-exit-codes`
  - `https://modelcontextprotocol.io/specification/2026-07-28/basic/utilities/cancellation` → `…/2026-07-28/basic/patterns/cancellation`
- Canonical: `https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/` declares
  `…/llmrisk/llm02-insecure-output-handling` (the 2023 LLM02, a different risk) as canonical. The
  body stored is the right one (title `LLM02:2025 Sensitive Information Disclosure`); the skill
  says do nothing, and that is right here.
- `no headings; search answers with the whole page as one Section`: `https://csrc.nist.gov/glossary/term/authentication`, the Foundations exam-guide PDF, `https://www.anthropic.com/engineering/{demystifying-evals-for-ai-agents, effective-context-engineering-for-ai-agents, multi-agent-research-system, writing-tools-for-agents}`, `https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/controlling-access-at-document-field-level`, `https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reindex-indices`. The four Anthropic engineering posts are core sources of both guides and are one Section each to `search`.

## Spot checks

1. **`md-twin` with a Reading** — `modelcontextprotocol.io/specification/2026-07-28/basic/transports`
   (4.4 KB Reading, 4.8 KB Version; smallest Reading). Page content: H1 "Overview", sections
   Messages / Request Metadata / Cancellation / Custom Transports / Backward Compatibility, numbered
   list intact. The Reading differs from the Version only by the dropped
   `> ## Documentation Index / Fetch the complete documentation index at: …/llms.txt` banner and the
   reduced frontmatter — cleaner, nothing lost. Same on `code.claude.com/docs/en/agent-sdk/overview`.
   Left in both: the MDX `<div id="enable-section-numbers" />` and site-relative links
   (`/specification/2026-07-28/basic/patterns`).
2. **`raw-twin`** — `github.com/anthropics/claude-code-action/blob/main/README.md` (5.5 KB): the
   README as written, H1 + 8 H2s, nothing else. `action.yml`: `# action.yml` then the whole file
   in a ```` ```yml ```` fence — correct. **But** `…/text_to_sql/guide.ipynb` (2.98 MB) is the raw
   notebook JSON in one ```` ````ipynb ```` fence, base64 PNG outputs included (4 `image/png`),
   one Section; the prose cells are JSON strings. Content is there, unreadable for search.
3. **`trafilatura`, warned** — `www.itl.nist.gov/div898/handbook/prc/section1/prc131.htm` (3.1 KB,
   `1 tables … missing`). The Original has 2 `<table>`s, both layout (breadcrumb, then the
   two-column body); the Markdown merged them into one pipe table holding every paragraph
   ("Determination of critical values", "p-values", "Good practice"). Nothing lost — false alarm.
   The title is: H1 `# 7.1.3.1.`, and the real title "Critical values and p values" ended as the
   table's last row.
4. **`trafilatura`, smallest** — `www.anthropic.com/research/evaluating-and-mitigating-discrimination-in-language-model-decisions`
   (2.4 KB file, ~1.5 KB body). Page content: `## Abstract` (full) and `## Policy Memo` (PDF
   link). Against the Original (466 words of text, mostly footer menus): complete; only the H1
   title is dropped (it is in `title:`).
5. **`markitdown`** — Professional exam guide PDF (21 KB). Page content, complete: sections 1–16
   through "16. Document Control", sample questions included. But: no Markdown headings at all
   (numbered section titles are plain lines), so one Section — and unlike the Foundations PDF no
   `no headings` warning. `title:` is the PDF metadata, an internal print URL:
   `b5effa80-….claudeusercontent.com/v1/design/projects/…/serve/Exam Guide - Architect Professional-print.dc.html?t=a280ea…&direct=1`.
6. **`trafilatura via crawl4ai`** — `www.hhs.gov/…/minimum-necessary-requirement/index.html`
   (6.2 KB; Original 212 KB). Page content: H1, CFR cite, Background / How the Rule Works /
   Uses and Disclosures, both bullet lists, date line. Section titles are `**bold**` paragraphs,
   so one Section to `search`.
7. Extra, the canonical case — `genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure`:
   right body, but trafilatura wrote headings as `###@ Sanitization:`, `###@ Access Controls:` —
   the `@` lands in `search`'s heading paths.

## Search

1. **Plain** — `lorekeep search 'minimum cacheable prompt length'`. The top 3 are passing
   mentions (`search-results…:2093` "see prompt caching for minimum cacheable lengths",
   `citations…:528`, `:629` code comments `// Minimum cacheable length`). The answer,
   `platform.claude.com--docs-en-build-with-claude-prompt-caching--caadb4de.md:615`
   ("Cache limitations", the per-model 512/1,024/2,048/4,096 list), ranks 6th; `haiku-5-5/overview:104`
   (4th) has the Haiku figure. Each `file:line` pointed exactly at the matched line; the ranking,
   not the pointer, is the weak part.
2. **`--exact`** — `lorekeep search --exact pause_turn`. 41 results ordered by file name, not by
   relevance: first `claude.termidy.com` pages (third-party, stored by another worker under the
   same Tag), then `code.claude.com/…/monitoring-usage:258`, then `code-execution-tool:1070`
   ("`pause_turn` stop reason" — a good answer, 6th). The page about it,
   `handling-stop-reasons`, is results 28–36. `--authority primary` lifted the useful hits to the
   top. `file:line` was exact each time.
3. **Needs `--all`** — `lorekeep search 'colang input rails'`: `no matches` /
   `+9 matches under other tags (--all)` — clear. With `--all`: NeMo Guardrails pages from
   `.cache/readings/…`; the 2nd (`rail-engine-support:10`, `[rails].[input].flows`) and 3rd
   (`configure-guardrails-overview:38`, the `rails/input.co` folder tree) point at the answer; the
   1st (`engine-feature-support:93`, a table header row) has no bracketed word in its snippet, so
   I could not tell why it matched.

## Friction

### The brief

1. `export LOREKEEP_anthropic=anthropic` — a typo for `LOREKEEP_TAG=anthropic`. As written, every
   `get` would exit 2 ("refuse to run without it"). I used `LOREKEEP_TAG=anthropic`, inferring the
   Tag from the value; the skill says the Tag is "never chosen by you", so the brief must spell it.
2. "open the file at `path` (the Reading) and, where `version` differs from `path`" — the
   vendored skill (`.agents/skills/lorekeep/SKILL.md`, untracked in this worktree) never mentions
   Readings or `version`. The packaged skill (`~/Projects/lorekeep/src/lorekeep/skill/SKILL.md`)
   does: the vendored copy is a version behind (no Reading paragraph, no
   `rule <name> removed` row, old `search` examples). The brief should name the copy to read, or
   the copy should be refreshed before the Run.
3. The Tag is shared with the termidy worker: `anthropic 389` in `status` vs my 217, and
   `claude.termidy.com` pages answer my `search` first. One line in the brief would have saved the
   surprise.
4. `err/<n>.txt` — what `n` is (line number? log line?) is not said; I used the batch line number.
5. The converter list names `verbatim` (none in this batch) but not `… via crawl4ai`, the browser
   path, which is the one a spot check most needs.
6. The exit-1 JSON shape: the skill's example has only `url` and `error`; I added `exit`. Say
   whether extra keys are fine.

### The skill

1. Stale copy (brief item 2): `status` prints `Readings: 85 of 378 Versions, 8 rules` and `get`
   returns `version` — neither explained by the vendored skill.
2. The two errors end in `the browser rendered a shell (358 characters after 3 attempts)`. The
   only mention of "rendered a shell" is under `thin content`, which "needs the browser
   (`lorekeep[browser]`), which waits longer" — but the browser already ran. I had to infer: not
   retryable, report. The real cause (a moved page: Twin 404 + an SPA shell) is not something the
   skill names; a row "Twin answered 404 … rendered a shell → the page probably moved; report as
   a dead link" would match what I found.
3. "stdout carries only the result; stderr carries lines starting `lorekeep: error:`, … `note:`"
   — false for PDFs: 35 lines `Could not get FontBBox from font descriptor because None cannot be parsed as 4 floats`
   in `err/70.txt` and `err/71.txt`. Nothing tells me to ignore them.
4. `no headings; search answers with the whole page as one Section` is described in prose under
   `get` but has no row in the stderr table, so whether it is reported is a guess (I listed it).
5. The `is in no host table` warning and the `third-party under no rule` note arrive together for
   every unknown host; the table gives the note a separate "report if primary" row. Is that one
   item or two? I reported once per URL.
6. "a page the guide treats as primary there (a vendor's repository; report when unsure)" — I
   judged by hand: `github.com/anthropics/*`, the S3-hosted exam guides, `claude.com`,
   `academy.claude.com` → primary; `fedramp.gov`, `hhs.gov` → government, the skill's law rule
   covers journals, not agency guidance pages.
7. A redirect to a *different* page (`url` ≠ `requested_url`, 4 here) — the skill says cite `url`
   but not whether to report the stale link to the owner. For a guide whose links are the
   content, it should.
8. "open a Version under 2 KB" — file size or body size? No file here is under 2 KB; the
   anthropic research page is 2.4 KB on disk and ~1.5 KB of body. I checked it anyway.
9. The `--exact` section does not say results come in file order, not ranked; I learnt it from a
   41-result list.

### The tool

1. **Error line on a moved page** — three causes in one 400-character line; the decisive fact
   (`.md answered 404`) sits in the middle. A short kind (`gone?`, `shell`) first, or `--json`
   on exit 1 with `{"kind": …}`, would make the log machine-countable. (I did not capture stdout
   on exit 1, so I do not know whether `--json` prints anything there.)
2. **pdfminer noise on stderr** (`Could not get FontBBox …`, 35 lines) — should be silenced or
   prefixed.
3. **PDF `title`** — PDF metadata wins: a `claudeusercontent.com/…/serve/…print.dc.html?t=<token>`
   URL with what looks like an access token. The first line of text ("Claude Certification
   Program … Exam Guide") would do.
4. **Notebooks** — `guide.ipynb` as raw JSON with base64 outputs (2.98 MB, one Section). A
   notebook converter (markitdown does ipynb) or stripping outputs would make three cookbook
   sources searchable.
5. **`no headings` inconsistency** — the Foundations PDF (87 KB) warns, the Professional PDF
   (21 KB, also 0 headings) does not; PDFs with numbered section lines could get headings.
6. **Table count false positive** on layout-table pages (NIST handbook: 2 layout tables merged
   into 1 → "1 tables missing"); six of my ten missing-table warnings are this.
7. **`###@` headings** (trafilatura on genai.owasp.org) pollute `search` heading paths.
8. **`--exact` ordering** — alphabetical by file; with a shared Tag the third-party study notes
   (`claude.termidy.com`) always come before `platform.claude.com`. Rank by authority, then by
   occurrences per Section, or by heading match.
9. **Plain search ranking** — passing mentions in long pages outrank the section that is about the
   query; a heading/title boost would put `prompt-caching:615` first.
10. Worked well: 219 URLs in 307 s alongside five writers, no lock waits; one clean JSON line per
    `get`; `warnings` recorded in frontmatter; Readings drop exactly the Mintlify banner;
    `+N matches under other tags (--all)` is clear and cheap.
