# google-cloud batch — lorekeep migration 3

Tag `google-cloud`, lorekeep 0.1.1, Store `~/orca/sources/agentic-system.design`. Log: `log.jsonl`
(324 lines, no retry lines — nothing qualified for a retry). Per-URL stderr: `err/<n>.txt`, `<n>` is
the line of `batch-google-cloud`; `rc.txt` is `<n> <exit> <url>`. Loop script: `run.sh`.

## Numbers

- **URLs:** 324 (317 distinct after normalisation, fragments dropped; the 322 successes resolve to 307
  distinct Versions — fragments, and redirects onto a page already asked).
- **Exit 0:** 322 — `stored` 299, `fresh` 15, `unchanged` 8 (`changed`/`gone`/`error`/`skipped`: 0).
- **Exit 1:** 2 — one `answered 404`, one `thin content … the browser rendered a shell`.
- **Exit 2:** 0.
- **Retries:** 0. Neither error names `ReadTimeout`, `ConnectError` or a 5xx, so the skill's rule
  says report, not retry.
- **Converters:** `trafilatura 2.3.1` 310, `md-twin` 8, `raw-twin` 4; no `markitdown` (no PDF in the
  batch), no `verbatim`, no `… via crawl4ai`.
- **Readings:** 6 lines carry a `version` field (`path` under `.cache/readings/`): code.claude.com/docs/en/mcp and five
  modelcontextprotocol.io pages.
- **Authorities:** `primary` 286 (google 259, a2a 8, mcp 5, ietf 4, anthropic 3, git 2,
  opentelemetry 2, nist 1, json-schema 1, kubernetes 1), `official` 12 (owasp 7, google 4,
  opentelemetry 1), `third-party` 24 (log lines; 17 unknown hosts + 3 github.com pages).
- **`url` ≠ `requested_url`:** 29 (redirects: `cloud.google.com` → `docs.cloud.google.com`,
  `vertex-ai/…` → `gemini-enterprise-agent-platform/…`, `google.github.io/adk-docs` → `adk.dev`,
  MCP 2025-06-18 → 2025-11-25 security page, `rfc-editor.org/rfc/rfcNNNN` → `/info/rfcNNNN`).
- **Warnings:** 72 Versions with `code blocks / tables … missing` (614 code blocks, 110 tables in
  total; 59 of the 72 on docs.cloud.google.com); 4 `no headings`; 6 canonical notices; 0
  `holds N%`, 0 `returning the stored Version`, 0 Index-rebuilt, 0 reading-rule warnings.
- **Wall time:** 556 s for 324 `get`s (21:02:51Z → 21:12:07Z), ≈1.7 s per URL, five other workers
  fetching into the same Store at the same time.

## To report to the owner

### Errors (exit 1, not retried)

- https://docs.cloud.google.com/gemini/enterprise/docs/workflows —
  `lorekeep: error: nothing stored for https://docs.cloud.google.com/gemini/enterprise/docs/workflows: the host rule names no Twin; https://docs.cloud.google.com/gemini/enterprise/docs/workflows answered 404`
  (the guide cites a page Google removed; the sibling `…/docs/workflow-builder` was stored).
- https://www.nist.gov/itl/ai-risk-management-framework —
  `lorekeep: error: nothing stored for https://www.nist.gov/itl/ai-risk-management-framework: the host rule names no Twin; thin content: https://www.nist.gov/itl/ai-risk-management-framework converted to 201 characters of a page of 41077; the browser rendered a shell (201 characters after 3 attempts)`.
  `thin content` per the skill "needs the browser", but the line says the browser already ran
  three times; nothing a Run can do. (The batch's `airc.nist.gov` AI RMF Core page was stored.)

### Unknown hosts (17), each stored as `third-party`

agent-plugins.org (https://agent-plugins.org/specification), agentskills.io
(https://agentskills.io/home, https://agentskills.io/specification), airc.nist.gov
(https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), api-security.owasp.org
(https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/),
deepmind.google (https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/),
developers.google.com
(https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall),
developers.googleblog.com
(https://developers.googleblog.com/agents-cli-in-agent-platform-create-to-production-in-one-cli/),
geminicli.com (https://geminicli.com/docs/cli/gemini-md/), go.dev (https://go.dev/doc/diagnostics,
https://go.dev/doc/pgo), mcp-toolbox.dev (https://mcp-toolbox.dev/), opensource.org
(https://opensource.org/ai/open-source-ai-definition), pkg.go.dev
(https://pkg.go.dev/testing#hdr-Benchmarks), research.google
(https://research.google/pubs/judging-with-confidence-calibrating-autoraters-to-preference-distributions/),
saif.google (https://saif.google/focus-on-agents), spiffe.io
(https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/,
https://spiffe.io/docs/latest/spiffe-specs/x509-svid/), www.antigravity.google
(https://www.antigravity.google/docs/cli/plugins#managing-hooks,
https://www.antigravity.google/docs/hooks), www.sbert.net
(https://www.sbert.net/docs/quickstart.html#cross-encoder).

### `third-party` pages the guide treats as primary (my judgement; the owner decides the rule)

- **Google's own material on hosts no rule knows** — a Google Cloud guide cites these as Google's
  word: `www.antigravity.google` (the bare `antigravity.google` *is* known: same product, two
  verdicts), `geminicli.com`, `mcp-toolbox.dev` (Google's MCP Toolbox for Databases),
  `developers.google.com`, `developers.googleblog.com` and `deepmind.google` (likely `official`),
  `research.google`, `saif.google` (Google's SAIF).
- **Google's repositories under the `github.com/` rule** —
  `lorekeep: note: https://github.com/google/adk-python/blob/main/src/google/adk/agents/invocation_context.py is third-party under the github.com/ rule`,
  same for https://github.com/google/agents-cli and https://github.com/google/agents-cli/blob/main/plugin.json.
  The guide uses the ADK source and `agents-cli` as Google's primary artefacts.
- **Specifications on their own sites** — `spiffe.io` (SPIFFE specs), `agentskills.io/specification`,
  `agent-plugins.org/specification`, `go.dev` / `pkg.go.dev` (the Go project documenting Go).
- **NIST** — `airc.nist.gov` (NIST's AI Resource Center reproducing AI RMF Core): by the skill's own
  rule this is at least `official`, not `third-party`; the journal copy (www.nist.gov) failed above.
- **OWASP** — `api-security.owasp.org` is `third-party`, while `cheatsheetseries.owasp.org` and
  `genai.owasp.org` are `official` under the `owasp` publisher.

### Missing code / tables warnings (72 Versions)

Systemic on docs.cloud.google.com: spot check 3 confirms the cause — the client-library samples
(Go, C#, Java, Node.js, PHP, Python) live in `<div class="github-docwidget-gitinclude-code">` and are
dropped; the REST/`gcloud` samples survive. A REST reference page (spot check 4) is different: the
"JSON representation" code is kept but flattened into one table cell, so the warning there
overstates the loss. The full list, as printed:

- https://ai.google.dev/gemini-api/docs/prompting-strategies: 27 code blocks / 0 tables of the page are missing from the Markdown
- https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing: 0 code blocks / 16 tables of the page are missing from the Markdown
- https://codelabs.developers.google.com/agents-cli-agent-platform/agents-cli-agent-platform: 0 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/agent-registry/roles-permissions: 0 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/performance-optimization: 0 code blocks / 2 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/dialogflow/cx/docs/concept/agent-design: 0 code blocks / 2 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/dialogflow/cx/docs/concept/fulfillment: 0 code blocks / 3 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/dialogflow/cx/docs/concept/webhook: 0 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/fine-tune-rag-transformations: 0 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search-2/query-search/search: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/create-manage-index: 18 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/deploy-index-public: 22 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/overview: 0 code blocks / 3 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/query-index-public-endpoint: 3 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/update-rebuild-index: 6 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/audio-understanding: 10 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/content-generation-parameters: 4 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/get-token-count: 9 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/image-understanding: 10 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/video-understanding: 6 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/computer-use: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/embeddings/get-text-embeddings: 5 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/embeddings/task-types: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluate-judge-model: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-garden/use-models: 3 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/system-instruction-introduction: 3 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/rubric-metric-details: 2 code blocks / 17 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/tools/function-calling: 5 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/evaluation: 7 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/inference: 9 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/prompt-classes: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent: 38 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/manage-revisions-and-traffic: 10 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/sessions/manage-with-adk: 9 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/instruction: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/reference/rest/v1/projects.locations.apps.examples: 1 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/gemini/enterprise/docs/evaluate-search-quality: 8 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/answer: 6 code blocks / 4 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/check-grounding: 3 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/configure-field-settings: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/evaluate-search-quality: 8 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/prepare-data: 0 code blocks / 3 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/generative-ai-app-builder/docs/ranking: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/iam/docs/conditions-attribute-reference: 54 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/iam/docs/principal-access-boundary-policies-create: 6 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/mcp/configure-mcp-ai-application: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/model-armor/configure-floor-settings: 36 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/model-armor/manage-templates: 24 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/model-armor/reference/rest/v1/SanitizationResult: 24 code blocks / 24 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/model-armor/sanitize-prompts-responses: 44 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/run/docs/configuring/request-timeout: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/secure-source-manager/docs/reference/mcp: 1 code blocks / 1 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/sensitive-data-protection/docs/concepts-infotypes: 6 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/sensitive-data-protection/docs/creating-templates-inspect: 18 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data: 28 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/sensitive-data-protection/docs/inspecting-text: 13 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/sensitive-data-protection/docs/reference/rest/v2/InspectConfig: 25 code blocks / 25 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/storage/docs/retry-strategy: 7 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-gemini-controlled-generation-response-schema-2: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/workflows/docs/execute-parallel-steps: 6 code blocks / 0 tables of the page are missing from the Markdown
- https://docs.cloud.google.com/workflows/docs/reference/syntax/retrying: 10 code blocks / 0 tables of the page are missing from the Markdown
- https://geminicli.com/docs/cli/gemini-md: 3 code blocks / 0 tables of the page are missing from the Markdown
- https://git-scm.com/docs/git-diff: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://git-scm.com/docs/git-status: 1 code blocks / 0 tables of the page are missing from the Markdown
- https://github.com/google/agents-cli: 0 code blocks / 1 tables of the page are missing from the Markdown
- https://google.github.io/agents-cli/guide/lifecycle: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://mcp-toolbox.dev/documentation/introduction: 2 code blocks / 0 tables of the page are missing from the Markdown
- https://pkg.go.dev/testing: 10 code blocks / 1 tables of the page are missing from the Markdown
- https://www.rfc-editor.org/info/rfc8693: 18 code blocks / 0 tables of the page are missing from the Markdown
- https://www.rfc-editor.org/rfc/rfc8693.html: 18 code blocks / 1 tables of the page are missing from the Markdown
- https://www.rfc-editor.org/rfc/rfc9700.html: 7 code blocks / 1 tables of the page are missing from the Markdown

### `no headings` (search reads each as one Section)

- https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing (also 16 tables
  missing — a pricing page whose prices are tables)
- https://www.rfc-editor.org/info/rfc6749 (asked as `/rfc/rfc6749`)
- https://www.rfc-editor.org/rfc/rfc8693.html
- https://www.rfc-editor.org/rfc/rfc9700.html — the Original has 76 `<h2>`–`<h4>` section headings,
  the Version one `# RFC 9700`.

### Other things worth the owner's eye

- **RFC 8693 is stored twice**: `https://www.rfc-editor.org/rfc/rfc8693` redirects to
  `https://www.rfc-editor.org/info/rfc8693` while `https://www.rfc-editor.org/rfc/rfc8693.html` is
  its own Source — two Versions of one RFC, both with warnings.
- **A canonical that is malformed**: `https://www.sbert.net/docs/quickstart.html declares another page as canonical (https://www.sbert.netdocs/quickstart.html)` — harmless (never used), but the
  recorded `canonical` field is junk.
- **A query parameter kept in `url`**: `https://antigravity.google/docs/cli/sandbox` → `url`
  `https://antigravity.google/docs/sandbox?tab=cli` (same for `…/plugins?tab=cli`); the page
  declares the tab-less address as canonical. Probably one page per tab — fine, but a guide writer
  will cite `?tab=cli`.
- **OWASP LLM06 headings**: https://genai.owasp.org/llmrisk/llm062025-excessive-agency has one
  heading in the Version, `#### 3. Excessive Functionality`, so `search` labels the prevention text
  "3. Excessive Functionality"; the Original's other `<h*>` are empty. No warning fires.

### Reading-rule warnings

None printed.

## Spot checks

1. **`raw-twin`, smallest Version (1216 B)** —
   https://github.com/google/agents-cli/blob/main/plugin.json: `# plugin.json` and the whole file in
   one ```` ```json ```` fence, byte-identical content. Page content, nothing lost. (Authority
   `third-party`, see above.)
2. **`trafilatura`, the only body under 2 KB (1813 B)** —
   https://research.google/pubs/judging-with-confidence-calibrating-autoraters-to-preference-distributions:
   `## Abstract` and the abstract paragraph, complete. Lost against the Original: the paper's title
   as a heading (it is in `title:`), the **author list and the year** (14 authors, 2025 — the
   facts a citation needs), and the "Download / Google Scholar / Bibtex" links. Menu and footer
   correctly dropped. No warning fired. LaTeX quotes came through escaped:
   ``\`\`autoraters''``.
3. **`trafilatura`, warned `44 code blocks / 0 tables`** —
   https://docs.cloud.google.com/model-armor/sanitize-prompts-responses (64 KB): headings and REST
   (`curl`, JSON) fences are there; under `### Go`, `### C#`, `### Java`, `### Node.js`, `### PHP`,
   `### Python` of "Text prompts" and "File-based prompts" only the sentence "To run this code,
   first set up …" remains — the Original holds the sample in `<div
   class="github-docwidget-gitinclude-code">`, which the extraction drops. Streaming-section
   samples survived (different markup). The warning is accurate and actionable: distrust the
   language headings, they introduce nothing.
4. **`trafilatura`, warned `24 code blocks / 24 tables`** —
   https://docs.cloud.google.com/model-armor/reference/rest/v1/SanitizationResult (33 KB): every
   message's `Fields` and `Enums` tables are present and correct (`MATCH_FOUND`,
   `EXECUTION_SKIPPED` …). What is lost is form: each "JSON representation" block is a one-cell
   table holding the JSON with its newlines collapsed (`| ``` {   "filterMatchState": enum
   (FilterMatchState), … |`), and type cells come out broken, ``| `enum (`)[FilterMatchState](…)``. So
   "24 tables missing" overstates it — the data is there; the 24 JSON shapes are unreadable as code.
5. **`md-twin` with a Reading (`version` ≠ `path`)** —
   https://modelcontextprotocol.io/specification/2026-07-28/architecture: the Reading (6551 B) is
   the Version (6945 B) minus the blockquote "## Documentation Index / Fetch the complete
   documentation index at: https://modelcontextprotocol.io/llms.txt …" banner. Cleaner, nothing of
   the spec lost. But the Reading's frontmatter holds only `version`, `sha256`, `rules` and the
   title — no `url`, `publisher`, `authority`: a reader who opens only `path` cannot tell what to
   cite.

(Also looked at: https://www.rfc-editor.org/info/rfc6749 — the "info" page the `/rfc/` address
redirects to still carries the full RFC text, 163 KB, so the redirect lost nothing but headings.
No `markitdown` or `verbatim` Version in this batch.)

## Search

1. **Plain** — `lorekeep search 'floor settings enforcement' --limit 3`: the right page
   (model-armor/configure-floor-settings), right Sections, `+5 matches under other tags (--all)`.
   But **`file:line` did not point at the snippet**: result 1 printed `…:18 | (top) | …Inline
   [enforcement] is configured at the project level…`; line 18 is "This document describes how to
   view and update…", the snippet is lines 26–28. Result 2 printed `:370`, the snippet's
   `--enable-floor-setting-enforcement=true` is line 382; result 3 printed `:142`, snippet at 144.
   It seems to be the first line in the Section with *any* query word, not the matching line the
   skill promises ("`file:line` is the matching line: open the file there"). Off by 2–12 lines;
   cheap here, costly in a long Section.
2. **`--exact`** — `lorekeep search --exact max_iterations --limit 3`: all three hits in
   adk.dev/agents/custom-agents, and each `file:line` was exactly the line with `max_iterations`.
   The page a writer wants, adk.dev/agents/workflow-agents/loop-agents (lines 65, 170), ranks 6th
   and 7th of 7 — exact results seem ordered by file, not by relevance — and `+16 matches under
   other tags (--all)`.
3. **Expected to need `--all`** — `lorekeep search 'excessive agency'` scoped to the Tag already
   answered from genai.owasp.org LLM06 (line 18, correct line), with `+2 matches under other tags
   (--all)`; `--all` added a claude.termidy.com page from another guide — context, not a better
   answer. Same with `'agent card signature'`: the Tag gives `a2a-protocol.org/latest/specification`
   at `:2320`, exactly "Clients verifying Agent Card signatures **MUST**:", and `--all` adds the
   pinned `v1.0.0/specification` copy, a useful second Source another guide fetched. `--all` was
   never *needed* for pages of this batch; it is useful to find a pinned version. Search ran in
   0.2–0.9 s.

## Friction

### The brief

- `export LOREKEEP_google-cloud=google-cloud` is not valid shell (zsh: `not valid in this
  context`); I read it as `LOREKEEP_TAG=google-cloud`, which the skill names. A template
  substitution went wrong; say `LOREKEEP_TAG=google-cloud` literally.
- "open the file at `path` (the Reading) and, where `version` differs from `path`, the Version
  too" — the skill never says "Reading" nor documents a `version` field; the brief was my only
  hint, and I still had to find a line with `version` to learn that `path` points into
  `.cache/readings/`.
- "retry what the skill says to retry" — fine, but say the expected answer could be zero; I spent
  a moment checking whether `thin content` ("needs the browser") counts as retryable.
- "Write only under …google-cloud/" while also saying the loop should run "in the background" — a
  scratch script has to live in that folder too (`run.sh`); say so, or allow the session
  scratchpad.
- The five other workers' existence explains `fresh` outcomes on first ask (15 here: pages another
  guide had just fetched). One line saying "`fresh` on a first ask is normal" would save a check.

### The skill

- **Readings are undocumented.** `lorekeep status` prints `Readings: 85 of 378 Versions, 8 rules`;
  `get --json` may add `"version": "…/<stem>.md"` and point `path` at `.cache/readings/<stem>.md`.
  Neither SKILL.md nor `store.md` mentions Reading, `.cache/readings`, `version` or the Reading's
  frontmatter (`version`, `sha256`, `rules`). The JSON example under `lorekeep get` has no
  `version` key. I had to infer: read `path`, cite `url` from the JSON, the Version is the
  provenance copy.
- **No rule for a warning that overstates the loss.** "report; compare with the Original; distrust
  nearby headings" — comparing the Original is a 240 KB HTML file; the skill gives no way to do
  that comparison other than ad-hoc grepping. On docs.cloud.google.com 59 Versions warn, almost all
  the same cause; the skill should say whether to report each or the pattern once.
- **`thin content` rule contradicts the error.** The skill: "`thin content` … needs the browser
  (`lorekeep[browser]`), which waits longer before `rendered a shell`". The error line already
  says `the browser rendered a shell (201 characters after 3 attempts)`. So the browser is
  installed and failed; the skill's sentence reads as an action I cannot take. Say: report it.
- **"`file:line` is the matching line: open the file there"** is not what the tool does (Search §1).
- **No guidance on `third-party` when a known publisher's other host is unknown**
  (`antigravity.google` known, `www.antigravity.google` not; `owasp` official, `api-security.owasp.org`
  third-party). "report when unsure" covered it, but I had to judge 17 hosts by hand.
- **`unchanged` on a first ask.** `outcome` `unchanged` is described among Recheck words; I got it
  for addresses I asked for the first time that redirected onto a page stored seconds earlier
  (`…/vertex-ai/docs/vector-search/overview` → the `gemini-enterprise-agent-platform` page). The
  skill should say that a redirect onto a stored Source returns `unchanged`/`fresh`, not `stored`.
- **The `no headings` warning** is not in the stderr table; the PDF paragraph mentions "a long page
  with no headings (`get` warns)". I treated it as "report"; the table should list it. Its wording
  is also inexact: RFC 9700's Version has one heading, `# RFC 9700`.
- **"open a Version under 2 KB, compare it with its Original"** — useful; it found the lost author
  list on research.google. Worked well.

### The tool

- **The same warning prints once per ask**, so a page asked with three fragments prints it three
  times (`…/generative-ai-app-builder/docs/answer: 6 code blocks / 4 tables …` ×3). With 72 warned
  Versions the stderr was 132 lines for a 324-URL batch; fine, but a `fresh` return could say
  "(recorded)" to tell an old warning from a new one.
- **Code-sample loss on docs.cloud.google.com is systemic** (`github-docwidget-gitinclude-code`),
  614 code blocks across 72 Versions. One host rule or extractor fix would clear most of the
  warnings of this guide.
- **REST reference pages**: the JSON shape inside a table cell is collapsed to one line and type
  cells come out as ``| `enum (`)[FilterMatchState](…)`` — broken Markdown. The "N tables missing"
  count there is wrong in the other direction (the tables are present).
- **`search` `line`** is not the snippet's line (Search §1); `--exact` ranks by file, not relevance
  (the page that defines `LoopAgent.max_iterations` came 6th).
- **A Reading's frontmatter lacks `url`/`authority`**; a worker that opens the file without the JSON
  line cannot cite it. Copy `url`, `publisher`, `authority` into the Reading.
- **`canonical` is recorded unvalidated** (`https://www.sbert.netdocs/quickstart.html`).
- **Two Sources for one RFC** (`/info/rfc8693` via redirect and `/rfc/rfc8693.html`); an
  rfc-editor host rule could reduce both to one address.
- **Exit codes and the one-line `lorekeep: error:` were easy to log**; per-URL JSON with `outcome`,
  `converter`, `authority` made every count in this report one `python3` call. 1.7 s per URL with
  six writers on one lock is fine. Worked well.
