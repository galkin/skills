# Recorded responses

Every folder is one HTTP response the fake transport serves instead of the network. The fake loads
all folders, keys them by `url`, and answers a request with the fixture whose `url` equals the
request URL and whose `match_headers` (when present) are all sent by the request; otherwise it
answers `404` and records the miss, so a test sees exactly which URLs a command asked for.

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
| `ms-foundry.redirect-1`, `-2`, `.twin` | Microsoft Learn: two `301`s, then a Twin whose own frontmatter has a `canonicalUrl`        |
| `nim-introduction.stub`                | NVIDIA NIM 98-byte `<meta http-equiv="Refresh">` page                                      |
| `nim-overview.html`                    | the page that stub points at                                                               |
| `milvus-403`                           | a host that answers `403` to a plain client (browser step)                                 |
| `google-md-answers-html`               | a `.md` URL that answers `200` with HTML (must not be accepted as a Twin)                   |
| `js-only.html`                         | a body with no text after extraction (browser step)                                        |
| `exam-guide.pdf`                       | a one-page PDF served as `application/pdf` under a URL without `.pdf`                      |

The five measured pages (Anthropic, AWS, three termidy lessons) were captured on 2026-10-17; their
response headers were not kept, so the ones here are the minimum a test needs. The Microsoft and
NVIDIA responses carry the headers as received. The `403`, `304`, `google-md-answers-html`,
`js-only.html` and the PDF are synthesised. A ticket may add further synthesised folders in the
same format; keep this table current.
