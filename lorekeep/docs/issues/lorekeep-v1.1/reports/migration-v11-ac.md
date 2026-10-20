# Batch ac: report (lorekeep 0.1.1, Tag `nvidia`)

## Numbers

- URLs in batch: 125 (the brief said ~127; `batch-ac` has 125 non-empty lines, ending in a newline). Lines in `log.jsonl`: 125.
- Exit 0: 125. By `outcome`: `stored` 125; `fresh` 0, `unchanged` 0, `changed` 0. No URL in this batch was in the Store already.
- Exit 1: 0. Exit 2: 0. No retries were needed, so none were run.
- Converters: `trafilatura 2.3.1` 73, `raw-twin` 44, `md-twin` 6, `markitdown 0.1.8` 2, `verbatim` 0.
- Authority: primary 74, official 47 (nvidia 41 GitHub repos, google/sre.google 6), third-party 4.
- Wall time: 152 s for the full loop (about 1.2 s per URL), running while two other workers used the same Store.
- In every line `url` equals `requested_url`, because trailing slashes are normalised away in both.

## To report to the owner

**Unknown hosts:** none. No `is in no host table` warning came up.

**Error lines:** none.

**`thin content`:** none.

**`third-party` pages the guide treats as primary** (all under the `github.com/` catch-all):
- https://github.com/triton-inference-server/tensorrtllm_backend/blob/main/docs/model_config.md. `triton-inference-server` is NVIDIA's own GitHub org, so this is vendor documentation for the NVIDIA guide. It probably needs a host rule like the one `github.com/NVIDIA` has (official).
- https://github.com/openai/openai-python and https://github.com/openai/openai-python/blob/main/README.md: OpenAI's own SDK repository. This page and the README are two Sources with almost the same text (42561 vs 42755 bytes).
- https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/transformprocessor/README.md: OpenTelemetry's own repository. opentelemetry.io is `primary`, but its GitHub org is third-party.

**Missing code/tables warnings** (each Version is partial; its Original is complete):
- https://redis.io/docs/latest/develop/using-commands/transactions/: 0 code / 2 tables
- https://sre.google/sre-book/effective-troubleshooting/: 2 code / 0 tables
- https://github.com/openai/openai-python: 0 code / 1 table (the `blob/main/README.md` raw-twin has the same text in full)
- https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/: 0 code / 3 tables
- https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/notification-policies/: 0 code / 2 tables
- https://grafana.com/docs/loki/latest/operations/storage/retention/: 0 code / 1 table
- https://kubernetes.io/docs/concepts/security/pod-security-standards/: 0 code / 1 table. This is the page's main table (the policy matrix).
- https://milvus.io/docs/rrf-ranker.md: 0 code / 4 tables

**Content lost with no warning** (my own finding; the skill's list does not cover it):
- https://nvidia.github.io/Model-Optimizer/guides/1_quantization.html: the Version is 1331 bytes. It ends at "Below, you can find the documentation for the quantization toolkit in ModelOpt:", and the list after it is missing. The Original has that list (the Sphinx toctree: Basic Concepts, Best practices…, PyTorch Quantization, quant_cfg, ONNX Quantization Linux/Windows…). trafilatura dropped it, and lorekeep gave neither a warning nor a `thin content` error.

**Other things to note:**
- https://v3.helm.sh/docs/helm/helm_rollback/ produced `declares another page as canonical (https://helm.sh/docs/helm/helm_rollback); stored under the address it was served at`. It was stored as `helm`/`primary` with `url` = `https://v3.helm.sh/...`. Per the skill, nothing needs doing.
- Near-duplicate Sources in the batch: https://nvidia.github.io/TensorRT-LLM/features/quantization.html and https://nvidia.github.io/TensorRT-LLM/latest/features/quantization.html (6066 vs 6087 bytes).

## Spot checks

| Converter | URL | Verdict |
| --- | --- | --- |
| `md-twin` | learn.microsoft.com/…/patterns/retry | Page content: H1 title, `## Context and problem`, `### Retry strategies`, 13 headings, a 3-row table, an image with a site-relative path. Leftover chrome words ("Azure", "Note") stand alone on lines. The H1 is the HTML `<title>` ("Retry pattern - Azure Architecture Center \| Microsoft Learn"), so every search heading path for MS pages starts with that whole string. |
| `raw-twin` | github.com/triton-inference-server/tensorrtllm_backend/blob/main/docs/model_config.md | Page content: the raw Markdown file, 16 headings and 198 table rows intact. |
| `trafilatura` | nvidia.github.io/TensorRT-LLM/features/kvcache.html | Page content: `# KV Cache System`, 25 headings, 5 code fences with YAML intact, 7 table rows. Code fences have no language tag (plain ```` ``` ````). |
| `trafilatura` | nvidia.github.io/Model-Optimizer/guides/1_quantization.html | Partial: title and intro are present, the toctree list is lost (see above). |
| `trafilatura` | github.com/openai/openai-python (repo landing page) | Page content (the README as rendered), 63 headings and 50 fenced blocks; one table is missing, as the warning says. |
| `markitdown` | nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf | Body text of the PDF with no headings (0 `#` lines over 4020 lines), as the skill warns. It keeps PDF ligatures (`proﬁle`, 249 occurrences of `ﬁ`). Footnotes run inline. The frontmatter has no `title`. |

No `verbatim` Version in this batch.

## Search

(full output in `search.txt`)

1. Plain: `lorekeep search 'how does the retry pattern handle exponential backoff for transient faults'` returned **`no matches`**, with no hint as to why. A shorter query, `'retry exponential backoff transient'`, found only a LangChain middleware page: the Microsoft Retry page never says "backoff". Then `'retry strategies' --publisher microsoft` returned `…patterns-retry--0d9886b6.md:45 | … > Solution > Retry strategies`, and line 45 is the answer (the strategies paragraph). So `file:line` is accurate once a query matches, but a guide writer's natural question gets nothing back. It looks like every word has to match.
2. Exact: `lorekeep search --exact enable_block_reuse` returned three hits in `…TensorRT-LLM-features-kvcache…md` at lines 76, 148 and 190. Line 76 is the sentence that answers the question ("…can be disabled by setting `enable_block_reuse` to False"). Correct.
3. Ligatures, tried on my own initiative: the plain query `cross-sectoral profile` does find the PDF's `proﬁle` (it is normalised), and `--exact 'cross-sectoral proﬁle'` with the ligature finds it too. `--exact 'profile'` would miss it in the PDF.

## Friction

- **What a plain query requires is not stated.** The skill says "`lorekeep search '<words>'` first" and "ranked by BM25". BM25 implies OR-style ranking, but a natural-language question returned `no matches`, so every word, stopwords included, seems to be required. The skill should say "use 2–4 content words; all must occur in one Section". `no matches` could also hint at "fewer words".
- **The helm example in the skill no longer matches what lorekeep does.** The skill's `get --json` example shows `v3.helm.sh` redirecting to `helm.sh` with `helm.sh is in no host table; stored as third-party` and `url` = `https://helm.sh/...`. In this run I got the canonical warning instead, `url` stayed `https://v3.helm.sh/...`, and authority was `primary`. An example that contradicts the tool makes you doubt the output.
- **Silent content loss has no rule.** The table covers "code blocks / tables missing" and `thin content`, but a list (toctree) dropped from a 1.3 KB Version raised nothing. I found it only because I sorted by file size. The skill could suggest "a Version under ~2 KB: open it and compare with the Original".
- **The `stored: false` Original is not explained.** For `md-twin`/`raw-twin` the frontmatter has `original.stored: false`, yet the skill says each Version has "its **Original** beside it" and the missing-code row says "its Original whole". It is unclear whether a Twin's Original is expected to be absent. (I did not open `store.md`; the skill did not send me there for this.)
- **It is unclear which `authority` value goes in the report.** "`third-party` page the guide treats as primary" needs judgement on which GitHub orgs count as the vendor. `triton-inference-server` is NVIDIA's but nothing in the output says so. I reported all 4.
- **The brief and the batch disagree on the count:** ~127 vs 125. Minor.
- **Things that cost time:** the `PATH`/`LOREKEEP_*` exports in every shell call (expected). My zsh loop returned the last command's exit code, which made the summary shell look failed when it wasn't.
- **What worked well:** a one-loop batch, quiet stderr, a single-line JSON log, the lock under three parallel workers (no errors, 1.2 s/URL), and precise `file:line` and heading paths.
