# Batch ab — NCP-AAI Sources into the lorekeep Store

lorekeep 0.1.1, Tag `nvidia`, Store `~/orca/sources/agentic-system.design`. Log: `log.jsonl` (127 lines, one per URL, no retry lines), stderr per URL: `err/<n>.txt` (n = line number in `batch-ab`), exit codes: `codes.txt`, loop: `run.sh`.

## Numbers

- URLs: 127 (126 distinct pages: line 88 is line 87 plus `#timeouts`).
- Exit 0: 126 — `stored` 125, `fresh` 1 (line 88, the fragment duplicate of line 87). No `unchanged`/`changed`/`gone`/`error`/`skipped`.
- Exit 1: 1 — `thin content` 1. No ReadTimeout / ConnectError / 5xx. Exit 2: 0.
- Retries: 0 — the one error is `thin content`, which the skill does not retry.
- Converters: `trafilatura 2.3.1` 78, `md-twin` 29, `raw-twin` 18, `verbatim` 1, `markitdown` 0 (no PDF in the batch).
- Authority: primary 104 (nvidia 84, vllm 7, python 6, ragas 5, eu 2), official 21 (nvidia/GitHub 18, owasp 3), third-party 1.
- Wall time: 145 s for the loop (~1.1 s/URL, with two other workers on the same Store; no lock waits noticed).

## To report to the owner

**Error lines (exit 1)**
- https://docs.nvidia.com/rag/latest/api-rag.html — `lorekeep: error: nothing stored for https://docs.nvidia.com/rag/latest/api-rag.html: the host rule names no Twin; thin content: https://docs.nvidia.com/rag/latest/api-rag.html converted to 303 characters of a page of 3273; this page needs a browser and Crawl4AI is not installed: install the extra lorekeep[browser] (uv sync --extra browser)`. (The page is a Swagger/Redoc shell; its schema `…/_static/api_reference/openapi_schema_rag_server.json` from the same batch was stored `verbatim` and holds the content.)

**Unknown hosts** — none (no `is in no host table` line in any stderr file).

**`third-party` pages the guide treats as primary**
- https://github.com/a2aproject/A2A/releases/tag/v1.0.0 — `publisher: github`, `authority: third-party` (github.com catch-all). It is the A2A project's own v1.0.0 release notes (the spec's breaking changes), i.e. a primary source for the protocol; a host rule for `github.com/a2aproject/` would fix it. Note: no stderr line flagged it — I found it only by scanning `authority` in the JSON.

**Missing code / tables warnings** (the Version is partial, its Original whole)
- https://docs.nvidia.com/nim-operator/latest/cache.html — 1 code block
- https://docs.nvidia.com/nim-operator/latest/service.html — 3 code blocks
- https://docs.nvidia.com/rag/latest/milvus-configuration.html — 3 code blocks
- https://docs.nvidia.com/vss/latest/real-time-vlm.html — 2 code blocks
- https://docs.nvidia.com/nim/large-language-models/latest/advanced-use-cases/tool-calling-and-mcp.html — 1 table
- https://docs.nvidia.com/nim/large-language-models/latest/deployment/kubernetes-deployment/helm-k8s.html — 1 table
- https://docs.nvidia.com/nim/large-language-models/latest/reference/advanced-configuration.html — 1 table
- https://docs.nvidia.com/nim/large-language-models/latest/reference/support-matrix.html — 3 tables
- https://docs.nvidia.com/nim/speech/latest/troubleshooting/tts.html — 1 table
- https://docs.nvidia.com/rag/latest/change-model.html — 1 table
- https://docs.python.org/3/library/asyncio-task.html — 1 table
- https://docs.python.org/3/library/sqlite3.html — 1 table
- https://eur-lex.europa.eu/eli/reg/2016/679/oj — 3 tables
- https://eur-lex.europa.eu/eli/reg/2024/1689/oj — 27 tables

**`thin content`** — https://docs.nvidia.com/rag/latest/api-rag.html (above).

**Not on the skill's report list, but the owner should know**
- OWASP canonicals are wrong on the publisher's side: https://genai.owasp.org/llmrisk/llm062025-excessive-agency declares canonical `…/llm06-sensitive-information-disclosure`, and https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses declares `…/llm08-excessive-agency` (2023-numbering slugs of *other* risks). The skill says "nothing; cite `url`", which is the right result here — but a reader of `canonical` in the frontmatter would be misled.
- The OWASP Version (trafilatura) lost almost all headings: `llm062025-excessive-agency` has one heading (`#### 3. Excessive Functionality`) and no title; "Common examples / Prevention / Attack scenarios" sections are flat paragraphs, so `search` returns one big Section with no heading path.
- EUR-Lex AI Act (https://eur-lex.europa.eu/eli/reg/2024/1689/oj): the only Markdown heading is site chrome `# Need help?` (line 17); all 113 Articles are plain lines, so every search hit carries the heading path `Need help?`. The page also says `In force: This act has been changed. Current consolidated version: 27/07/2026` — the stored text is the 2024 OJ original, not the consolidated text. Authority `primary` is correct.
- Five NeMo Retriever `latest` pages declare a pinned-version canonical (`…/retriever/26.8.1/…`): audio-video, concepts, content-metadata, multimodal-extraction, prerequisites-support-matrix. Nothing to do per the skill; noted because `latest` will drift from what was cited.

## Spot checks

- **md-twin** — `docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-pii-detection--309612ca.md`: page content. `# PII Detection`, 9 headings, 18 fence lines with `yaml` languages, 5 table rows. Preceded by ~12 lines of NVIDIA's llms.txt banner (`> This page is for version Latest (default)… For clean Markdown of any page, append .md…`, an MCP-server pointer) before the H1 — noise, harmless.
- **raw-twin** — `github.com--ai-dynamo-aiperf-blob-main-docs-benchmark-datasets.md--ce091a85.md`: the file's content, as written: the dataset table is raw HTML `<table>` (as in the repo source, not a conversion fault), `## Dataset Options` heading. Fine.
- **trafilatura** — `docs.nvidia.com--nemo-megatron-bridge-latest-modelopt-distillation.html--6e352078.md`: page content. `# Knowledge Distillation`, 14 headings, lists, 4 code fences (no language tag: bare ```` ``` ```` for a YAML block). Good. Counter-example in the same converter: the OWASP page above (headings lost) and EUR-Lex (articles not headings, layout tables kept as `|  | … |`).
- **verbatim** — `docs.nvidia.com--rag-latest-_static-api_reference-openapi_schema_rag_server.json--e2742fb9.md`: the whole OpenAPI 3.1.0 JSON in one ```` ```json ```` fence (2033 lines), title `openapi_schema_rag_server.json`. Exactly the content.
- **markitdown** — none in this batch (no PDF).

## Search

- Plain, as a writer would phrase it: `lorekeep search 'how does GLiNER PII detection mask entities'` → `no matches` (exit 0). Rephrased with key words only, `lorekeep search 'GLiNER PII masking'` → top hit `…pii-detection--309612ca.md:37 | PII Detection > GLiNER-based PII Detection` — the right line (the sentence introducing GLiNER detection and masking); hits 2, 4 point at the config blocks for hosted/local NIMs. Good once rephrased.
- `--exact`: `lorekeep search --exact logit_kl_temperature` → `…modelopt-distillation.html--6e352078.md:51 | Knowledge Distillation > Configuration > Knowledge Distillation Config` — line 51 is exactly the `logit_kl_temperature` bullet. Correct.
- Extra (EUR-Lex): `lorekeep search 'human oversight high-risk AI system'` → `eur-lex…2024-1689-oj…md:968 | Need help? | …Article 14 [Human] [oversight] 1\. [High-risk]…`. Right document, but line 968 is a table row of Annex/Article 13 material; `Article 14` / `Human oversight` sits at lines 988–990, 20 lines lower, and the heading path is the site-chrome `Need help?`.

## Friction

1. **Query semantics are not stated.** The skill says "ranked by BM25; word forms match" and gives `lorekeep search '<words>'`, but not that every word must appear (a natural question returned `no matches`). One sentence ("all words must match; drop question words") would have saved a retry. Also: `no matches` exits 0 — fine, but the skill does not say.
2. **`third-party` via a catch-all is silent.** The stderr table covers only `<host> is in no host table`; for the github.com catch-all there is no stderr line, so the rule "A `third-party` page the guide treats as primary … is reported" can only be applied by scanning `authority` in every JSON line. The skill should say "check `authority` in the JSON; there is no warning for it", or lorekeep should emit a `note:`.
3. **Warnings repeat on `fresh`?** Line 87 (stored) printed the missing-table warning; line 88 (`fresh`, fragment) printed nothing. So a worker that hits a page another worker already stored never sees its missing-code/table warning, and that page is under-reported. Either the skill should say "the warning prints only on the fetch that stores", or `fresh` should repeat it.
4. **"Report it" for missing code/tables has no threshold or remedy.** 14 of 126 pages carry it, including EUR-Lex with 27 tables that were actually kept as layout-table rows (844 `|` lines in the AI Act Version). I could not tell whether "missing" means "lost" or "counted differently"; the skill gives no way to check (the Original is there, but nothing says to compare it).
5. **Heading-poor conversions are not flagged.** OWASP (one heading, title lost) and EUR-Lex (only `# Need help?`) pass with no warning, yet they break the Section model `search` depends on (`heading path` is wrong/empty). Not on the skill's report list — I reported them on judgement.
6. **`canonical` warning for wrong publisher canonicals.** "declares another page as canonical → nothing" is right, but the frontmatter keeps a `canonical` that points to a different OWASP risk; nothing tells a later reader it is wrong.
7. **Fragment duplicates in a batch.** The skill says fragments are dropped and to keep them yourself; with the JSON-only log, the fragment of line 88 is lost from the log (`requested_url` is normalised). My log keeps it only because `codes.txt` records the raw line. A `fragment` field in the JSON, or a sentence "log the address you asked, not only the JSON", would close that.
8. **Logging an exit 1.** The brief and skill say "append the URL and the error line"; I had to pick a format (`{"url","error","exit"}` built with Python for safe JSON escaping) — a one-line example in the skill would remove the guess.
9. Minor: the md-twin Versions carry NVIDIA's llms.txt banner before the H1; harmless, adds a `(top)` Section of boilerplate to every NVIDIA docs page.

Worked well: one shell loop, no usage errors, the flag order and stdout/stderr split exactly as documented, parallel workers on one Store with no lock trouble, the thin-content error line told me precisely what to do.
