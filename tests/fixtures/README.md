# Recorded responses

Every folder is one HTTP response the fake transport serves instead of the network. A test builds
the fake from a list of folders (all of them by default, or a chosen subset when two fixtures share
a URL, as the `.noisy` variant does). The fake answers a request with the fixture whose `url`
equals the request URL after percent-decoding the path and query and lower-casing the host (`httpx.URL` equality is not used: it keeps `%2F` and `/` apart) and whose
`match_headers`, when present, are all sent by the request; when several match, the one with the
most matching `match_headers` wins, so a conditional request gets the `304` and a plain one the
page. A fixture with `error` raises that `httpx` exception instead of answering. Any other URL is
answered `404` and recorded as a miss, so a test sees exactly which URLs a command asked for.

`response.json`:

```json
{
  "url": "https://host/path",
  "status": 200,
  "headers": { "content-type": "text/markdown; charset=utf-8", "etag": "\"…\"" },
  "body": "body.md",
  "match_headers": { "if-none-match": "\"…\"" }
}
```

or, for a failure, `{ "url": "https://host/path", "error": "ReadTimeout" }`.

`body` names the file beside it with the response bytes, absent for an empty body. Header names
are lower-case. `match_headers` is optional.

## What is here

| Folder                                 | Case                                                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| `anthropic-prompt-caching.twin`        | Twin (`.md`) of the Anthropic page; the most complete rendition measured                   |
| `anthropic-prompt-caching.html`        | the same page as HTML (3 MB)                                                               |
| `anthropic-prompt-caching.304`         | `304` to a conditional request with the Twin's ETag                                        |
| `aws-prompt-caching.twin` / `.html`    | AWS Bedrock page as Twin and HTML; the HTML carries cookie banners                         |
| `termidy-*.html`                       | three lessons of a site reused under permission; no Twin exists                            |
| `termidy-coordinator-and-subagents.noisy` | the same lesson with a per-request nonce in a `<script>`: different bytes, same Markdown |
| `termidy-coordinator-and-subagents.changed` | the same lesson with a changed `<h1>`: different bytes, different Markdown           |
| `termidy-coordinator-and-subagents.alias` | the same lesson under `…/index.html`; its `<link rel="canonical">` names the lesson URL |
| `timeout`                              | a URL whose request raises `ReadTimeout`                                                   |
| `ms-foundry.redirect-1`, `-2`, `.twin` | Microsoft Learn: two `301`s, then a Twin whose own frontmatter has a `canonicalUrl`        |
| `nim-introduction.stub`                | NVIDIA NIM 98-byte `<meta http-equiv="Refresh">` page                                      |
| `nim-overview.html`                    | the page that stub points at                                                               |
| `milvus-403`                           | a host that answers `403` to a plain client (browser step)                                 |
| `google-md-answers-html`               | a `.md` URL that answers `200` with HTML (must not be accepted as a Twin)                   |
| `google-overview.html`                 | the page behind that `.md` URL, served as HTML                                             |
| `js-only.html`                         | a body with no text after extraction (browser step)                                        |
| `relative-links.html`                  | a page with `rel.html`, `../`, `/` and `//` links (resolved as a browser would)            |
| `exam-guide.pdf`                       | a one-page PDF served as `application/pdf` under a URL without `.pdf`                      |
| `exam-guide.html-as-pdf`               | HTML served as `text/html` under a URL ending in `.pdf` (never handed to MarkItDown)       |
| `exam-guide.zip`                       | a body served as `application/zip`, a media type no step takes                             |
| `exam-guide.not-a-pdf`                 | HTML bytes served as `application/pdf` (refused, not guessed at)                           |
| `langchain-sql-agent.twin`             | Mintlify Twin of LangChain's `sql-agent` page (`text/markdown`): code, no tables           |
| `langchain-tools.twin`                 | Mintlify Twin of LangChain's `tools` page: code and pipe tables                            |
| `guardrails-jailbreak-protection.twin` | Fern Twin of a NeMo Guardrails page on `docs.nvidia.com`: code and pipe tables             |
| `dynamo-fast-model-loading.twin`       | Fern Twin of a Dynamo page (`text/markdown`)                                               |
| `dynamo-fast-model-loading.plain`      | the same bytes served as `text/plain` (a Fern Twin that does not say Markdown)             |
| `guardrails-no-twin.html`              | a page under a Fern rule whose `.md` has no fixture (`404`), so the page is converted      |
| `github-docker-compose.raw`            | a raw YAML file behind a GitHub `blob/` page (`text/plain`)                                |
| `github-readme.raw`                    | a raw `README.md` behind a GitHub `blob/` page (`text/plain`)                              |
| `rag-openapi-schema.json`              | NVIDIA RAG's OpenAPI schema (`application/json`), cut to one path                          |
| `verbatim-notes.text`, `verbatim-values.yaml`, `verbatim-models.csv`, `verbatim-feed.xml` | plain text, YAML, CSV and XML served under their media types |
| `owasp-excessive-agency.html`          | OWASP's 2025 Excessive Agency page, whose canonical link names the 2023 LLM06 page          |
| `owasp-sensitive-information-disclosure.301` | that canonical address: a `301` back to the Excessive Agency page                    |
| `nvidia-retriever-concepts.html`       | a NeMo Retriever `latest` page whose canonical link names `26.8.1`                         |
| `helm-rollback.v3`                     | `v3.helm.sh` serving the page itself (`200`), its canonical link naming `helm.sh`          |
| `helm-rollback.v3-redirect`            | the same address as a `301` to `helm.sh` (a cross-host redirect)                           |
| `helm-rollback.html`                   | the page on `helm.sh`                                                                      |

The five measured pages (Anthropic, AWS, three termidy lessons) were captured on 2026-10-17; their
response headers were not kept, so the ones here are the minimum a test needs. The Microsoft and
NVIDIA responses carry the headers as received. The LangChain, Guardrails, Dynamo and GitHub bodies
were recorded whole from the live hosts on 2026-10-17 (v1.1 ticket 01) with their `content-type`,
`etag` and `last-modified`; the OpenAPI schema was recorded then and cut to its first path. The
`.plain` variant, `guardrails-no-twin.html` and the four `verbatim-*` files are synthesised. The `403`, `304`, `google-md-answers-html`,
`js-only.html`, `.noisy`, `.changed`, `.alias`, `google-overview.html`, `timeout`, `relative-links.html`, the PDF and its three `exam-guide.*` variants are synthesised. A ticket may add further synthesised folders in the
same format; keep this table current.

The OWASP and NVIDIA pages are cut from the Originals of the first migration's Store (captured
2026-10-17) to the `<head>` with its canonical link and the first paragraphs; their headers are
the ones the Store's frontmatter records. The OWASP `301` and both helm `200`s were recorded from
the live hosts with `curl` on 2026-10-17, bodies cut short. `helm-rollback.v3-redirect` is
synthesised: `v3.helm.sh` answered `200` itself on that day, not a redirect.
| `vllm-cli-serve.v1`                    | Markdown body of the vLLM `cli/serve` Version as v1 stored it, cut: an inline ```` ``` ```` after `Example (new format):`, headings with `[¶](…)` permalinks |
| `trtllm-kv-cache.v1`                    | hand-written Markdown as v1 wrote it: `free\_gpu\_memory\_fraction`, `[#](…)` heading permalinks, text before the first heading |
| `guardrails-jailbreak-protection.html` | Fern (NeMo Guardrails): 3 `<pre class="code-block-root">` of one `<div>` per line, 4 tables in scroll-area wrappers |
| `guardrails-self-check.html`           | Fern (NeMo Guardrails): 16 code blocks                                                     |
| `langchain-middleware-built-in.html`   | Mintlify: 10 code blocks (one in a callout Trafilatura drops), 29 parameter names drawn as `<button>`s |
| `langchain-sql-agent.html`             | Mintlify: `<!-- -->` comments in the content, which crashed Trafilatura 2.3.1              |
| `kubernetes-deployment.html`           | Hugo/Docsy: headings, the page title and a list of links Trafilatura dropped               |
| `opentelemetry-signals.html`           | Hugo/Docsy: a list of link-only items (the signal names) Trafilatura dropped               |
| `trtllm-kvcache.html`                  | Sphinx (`nvidia.github.io`): `a.headerlink` in every heading                               |
| `nim-tool-calling.html`                | Sphinx (`docs.nvidia.com`): 4 highlighted code blocks, `\_` escapes, a table inside a list item Trafilatura drops |
| `build-nemotron-modelcard.html`        | a client-rendered page: a menu as static HTML, its Next.js payload in a `<script>`          |
| `model-optimizer-quantization.html`    | Sphinx (`nvidia.github.io`): a toctree list in a `toctree-wrapper` `<div>` after the paragraph that introduces it (v1.1 dropped it) |
| `guides-catalog.html`                  | synthesised: three paragraphs, then sixteen headed lists of links Trafilatura drops, all in `<main>` (Markdown at 14% of the main text) |

The five measured pages (Anthropic, AWS, three termidy lessons) were captured on 2026-10-17; their
response headers were not kept, so the ones here are the minimum a test needs. The Microsoft and
NVIDIA responses carry the headers as received. The `403`, `304`, `google-md-answers-html`,
`js-only.html`, `.noisy`, `.changed`, `.alias`, `google-overview.html`, `timeout`, `relative-links.html`, the PDF and its three `exam-guide.*` variants are synthesised. The two `.v1` folders are Markdown bodies for `write_version`, served as
`text/markdown`; the vLLM one is cut from the first migration's Store (2026-10-17). A ticket may add
further synthesised folders in the same format; keep this table current.
`js-only.html`, `.noisy`, `.changed`, `.alias`, `google-overview.html`, `timeout`, `relative-links.html`, the PDF and its three `exam-guide.*` variants are synthesised. A ticket may add further synthesised folders in the
same format; keep this table current.

The pages from `guardrails-jailbreak-protection.html` down, `guides-catalog.html` aside, are
Originals of the first migration (2026-10-17), cut to the part that shows the defect: scripts,
styles, SVG, images, `style`/`data-*` attributes (but `data-component-part`) and the site's
navigation removed, long pages cut after the sections a test reads
(`model-optimizer-quantization.html` keeps its whole `<main>` and six items of the global table of
contents); the model card keeps the first 8,000 characters of its payload `<script>`, which is what makes it thin. `langchain-sql-agent.html` was recorded live the
same day, because its Original was never stored, and cut to the step whose tab buttons hold the
comments. Their headers are the minimum a test needs.
