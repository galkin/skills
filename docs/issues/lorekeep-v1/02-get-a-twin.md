# 02: `get` stores a Twin as a Version

**What to build:** A worker runs `get <url>` for a page whose publisher serves a Markdown Twin and receives the path of a Version file in the Store: `<host>--<path>--<sha8>.md`, frontmatter with `url` (normalised, after redirects and `canonicalUrl`, Twin suffix removed), `fetched_at`, `sha256`, `publisher`, `authority`, `converter: md-twin`, `etag`/`last_modified` when served, `title`, `original {url, mediatype, sha256, stored: false}` where `original.sha256` hashes the bytes received. A Twin's own frontmatter is stripped from the body and mined for `title`, `canonicalUrl` and a modification date. The host table (package default plus `lorekeep.toml`) decides the Twin rule, `publisher` and `authority` by longest prefix; an unknown host gets `third-party` and a warning on stderr. A Twin is accepted only when the response is `text/markdown` (or `text/plain` from a raw host); a `.md` URL that answers HTML is rejected and `get` reports that no Twin was found (later tickets add the next steps). Before any request, `get` looks for an existing Version without the Index: candidates are `<stem>--*.md`, their frontmatter is matched on `url` and `original.url`, the newest `fetched_at` wins; found, it returns that path without fetching and appends the Run's Tag to `tags.csv` if missing. Every Version and Tag is written through one commit function of the Store module (temporary file and rename, CSV appends under `.lorekeep.lock`, then an Index notification that is a no-op until ticket 08). This ticket defines the cascade as an ordered list of steps that 03–05 extend without touching the commit function.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `get` of the Anthropic Twin fixture creates exactly one `.md` file named by host, dashed path and the first 8 hex of the body's sha256, and prints its path on the last line; with `--json` it prints one object with a `path` field and nothing after it
- [ ] frontmatter holds every required field and the optional ones the fixture provides; `sha256` equals the hash of the body after the frontmatter; `original.sha256` equals the hash of the response bytes; `original.stored` is `false` and no `.orig.*` file exists
- [ ] the Microsoft Learn chain (two `301`s, then a Twin with its own frontmatter) is stored once under the `canonicalUrl` without the `?accept=` suffix, the requested URL in `original.url`, the body starting at the Twin's first heading, `title` taken from the Twin's frontmatter
- [ ] URL normalisation: fragment, `utm_*`/`ref`/`fbclid`/`gclid` dropped, other query parameters kept and sorted, trailing slash dropped, host lower-cased, `http` left for redirects to decide
- [ ] host table: longest-prefix match sets `publisher` and `authority`; `raw.githubusercontent.com/anthropics` can be `primary` while the rest of GitHub is not; an unknown host → `third-party` plus a stderr warning naming the host
- [ ] the `google-md-answers-html` fixture is not stored as a Twin
- [ ] second `get` of the same URL, and a `get` of the Microsoft page by its original `ai-foundry` address: no request made (fake transport records zero calls), same path printed, one new `tags.csv` row only when the Tag is new
- [ ] `get` without a Tag exits non-zero before any request
- [ ] the Store contains `.lorekeep.lock` and no `.tmp-*` file after a `get`
