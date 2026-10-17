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
| `guardrails-rail-types.twin`           | Fern Twin of NeMo Guardrails' `rail-types` page, as the first Store holds it (v1.2 ticket 01): one paragraph answers "which rail type validates tool call arguments" |
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
| `langchain-parent-document-retriever.html` | LangChain reference: `<title>` `ParentDocumentRetriever \| langchain_classic \| LangChain Reference`, `<h1>` `ParentDocumentRetriever`, no heading Trafilatura keeps (v1.2 ticket 04) |
| `ai-act-service-desk-article-26.html`  | AI Act Service Desk: the only `<h1>` is the site's banner `AI Act Explorer`, which the `<title>` does not begin with |
| `nist-ai-600-1.pdf`                    | page 5 of NIST AI 600-1 with the document's metadata `Title`; its text spells `proﬁle` with U+FB01 |
| `eur-lex-ai-act.html`                  | EUR-Lex AI Act: the head, the title block and the first 30 recitals (60 KB, 28,000 characters of Markdown), and the footer whose `Need help?` is the one heading |
| `build-safety-for-agentic-ai.twin`     | the `build.nvidia.com` Twin `nvidia/safety-for-agentic-ai.md` (`text/markdown`), cut from the first Store's Version to the text before `## Minimum System Requirements` (v1.2 ticket 07) |
| `build-nemotron-nano.twin`             | synthesised: a Twin at `nvidia/nvidia-nemotron-nano-9b-v2.md`, read for the `…/modelcard` page |
| `build-safety-for-agentic-ai.301`      | synthesised: `nvidia/agentic-ai-safety.md`, a `301` to `nvidia/safety-for-agentic-ai.md` |
| `ms-retry-pattern.twin`                | Microsoft Learn Twin of the Retry pattern (`?accept=text/markdown`), headed `# Retry pattern - Azure Architecture Center \| Microsoft Learn`: the first Store's Version body, whole (v1.3 ticket 01) |
| `eur-lex-ai-act.v1`                    | the AI Act as the first Store's Version holds it (Markdown, served as `text/markdown` for `write_version`): body lines 1–53 (the footer heading `Need help?`, the title block, recitals 1 and 2) and 410–495 (`HAVE ADOPTED THIS REGULATION:` to the first definitions of Article 3), so Articles 1, 2 and 3 stand as bare lines (v1.3 ticket 01) |
| `readings-fence-table.v1`              | synthesised: 25 lines where `Edit this page on GitHub` stands alone three times, in a fence and in a pipe table, `Article 7` in the fence, `Article 9` right under `## Article 9`, `Article 10` bare (v1.3 ticket 01) |
| `guardrails-rail-types.notfound.twin`  | Fern's not-found page served `200 text/plain` at `nemo/guardrails/latest/about-nemo-guardrails/library/rail-types.md`: the first Store's Version body, byte for byte (its `sha256` `93f114ec…`), whose type its `original.mediatype` records (v1.3 ticket 04) |
| `guardrails-rail-types.notfound.404`   | synthesised: that page itself answering `404` with a short HTML body |
| `guardrails-rail-types.notfound.301`   | synthesised: that page as a `301` to `nemo/guardrails/about-nemo-guardrails-library/rail-types`, the address NVIDIA moved it to |
| `guardrails-rail-types.moved.html`     | synthesised: the new address's HTML, the first paragraphs of `guardrails-rail-types.twin` |
| `guardrails-rail-types.moved.twin`     | the body of `guardrails-rail-types.twin`, served as the new address's Twin (`text/markdown`) |

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

## Rendered documents for the fake browser

These are single files, not folders: `FakeFetcher` returns a file as the document the browser
rendered, and a page given several files renders as the next one on each call.

| File                                          | What it shows                                                        |
| --------------------------------------------- | -------------------------------------------------------------------- |
| `build-nemotron-modelcard.rendered-shell.html` | the model card as Crawl4AI 0.9.5 rendered it with its default wait in the second migration (77,433 bytes): the menu, an empty `<main>` holding Next.js's `NEXT_HTTP_ERROR_FALLBACK;404` template, the payload `<script>`s; converts to about 216 bytes of menu |
| `build-nemotron-modelcard.rendered-card.html`  | the same document with the card's content in `<main>`: synthesised (2026-10-17), because the card is gone upstream and no loaded render was ever kept; the description is the page's own `<meta name="description">`, the two paragraphs are the overview of the earlier hand-written `RENDERED_CARD` |
| `browser-short-page.html`                     | synthesised: a page short for real, its document as small as its Markdown |
The four v1.2 ticket 04 folders are cut from the first Store's Originals (2026-10-17). The HTML
pages lose scripts, styles, SVG, images, forms, navigation and `style`/`data-*`/`aria-*`
attributes and keep only the subtrees a test reads, under the original `<title>`, canonical link and
`<meta>` tags (EUR-Lex keeps only its `og:` and `description` ones of 107 KB). The PDF is the
Original's fifth page, cut with `qpdf --pages . 5`, which keeps the information dictionary. Their
headers are the ones the Store's frontmatter records.
The v1.2 ticket 07 Twin is the first Store's Version body (2026-10-17): a Twin keeps no Original,
so the body is the text received after its frontmatter. Of that frontmatter only `title` (the
Version's) is put back; the rest, and the response headers, were never kept.
