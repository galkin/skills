# 02: `get` stores a Twin as a Version

**What to build:** A worker runs `get <url>` for a page whose publisher serves a Markdown Twin and receives the path of a Version file in the Store: `<host>--<path>--<sha8>.md`, frontmatter with `url` (normalised, after redirects and `canonicalUrl`), `fetched_at`, `sha256`, `publisher`, `authority`, `converter: md-twin`, `etag`/`last_modified` when served, `title`, `original {url, mediatype, sha256, stored: false}`. The host table in `lorekeep.toml` decides the Twin rule, `publisher` and `authority` by longest prefix; an unknown host gets `third-party` and a warning on stderr. A Twin is accepted only when the response is `text/markdown` (or `text/plain` from a raw host); a `.md` URL that answers HTML is rejected and `get` reports that no Twin was found (later tickets add the next steps). A second `get` of the same URL returns the same path without fetching and appends the Run's Tag to `tags.csv` if missing. Files are written to a temporary name and renamed; CSV appends happen under the Store's lock. This ticket defines the cascade as an ordered list of steps that 03–05 extend.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `get` of a Twin fixture creates exactly one `.md` file named by host, dashed path and the first 8 hex of the body's sha256, and prints its path on the last line (also with `--json`)
- [ ] frontmatter holds every required field and the optional ones the fixture provides; `sha256` equals the hash of the body after the frontmatter
- [ ] URL normalisation: fragment, `utm_*`/`ref`/`fbclid`/`gclid` dropped, other query parameters kept and sorted, trailing slash dropped, host lower-cased; a Microsoft Learn Twin with `canonicalUrl` is stored under the canonical URL with the requested one in `original.url`
- [ ] host table: longest-prefix match sets `publisher` and `authority`; `raw.githubusercontent.com/anthropics` can be `primary` while the rest of GitHub is not; an unknown host → `third-party` plus a stderr warning naming the host
- [ ] a `.md` URL answering `text/html` is not stored as a Twin
- [ ] second `get` of the same URL: no request made (fake transport records zero calls), same path printed, one new `tags.csv` row only when the Tag is new
- [ ] `get` without a Tag exits non-zero before any request
- [ ] a Version's Original is not stored when it is byte-identical to the Markdown
- [ ] the fixture set includes the Anthropic and AWS `prompt-caching` Twins and the Microsoft Learn Twin with `canonicalUrl`
