# 03: `get` stores a Twin as a Version

**What to build:** A worker runs `get <url>` for a page whose host rule names a Twin and receives the path of a Version `<host>--<path>--<sha8>.md` with frontmatter `url` (normalised, after redirects and `canonicalUrl`, Twin suffix removed and `page_suffix` restored), `requested` when it differs, `fetched_at`, `sha256`, `publisher`, `authority`, `converter: md-twin`, `etag`/`last_modified` when served, `title`, `modified` (first present of `ms.date`, `updated_at`, `lastmod`, `date` in the Twin's frontmatter), `original {url, mediatype, sha256, stored: false}` where `original.url` is the Twin address the bytes came from and `original.sha256` hashes them. The Twin's own frontmatter is stripped from the body. A Twin is accepted only when the response is `text/markdown`, or `text/plain` under a `raw` rule; otherwise the response is discarded, `get` reports that no Twin was found and, in this ticket, exits non-zero (ticket 04 then fetches the page URL instead). Before any request, `get` uses ticket 02's lookup and, when a Version exists, returns it without fetching and appends the Run's Tag if missing. The cascade is an ordered list of steps that 04–06 extend; every write goes through ticket 02's commit function. Every request carries a `User-Agent` starting with `lorekeep/`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `get` of the Anthropic Twin fixture creates exactly one `.md` file and prints its path last (text) or as `path` in one object (`--json`); frontmatter holds every required field, `etag` from the fixture, `original.stored: false`, and no `.orig.*` file exists
- [ ] the Microsoft Learn chain (two `301`s, then a Twin with its own frontmatter) is stored once under the `canonicalUrl` without the `?accept=` suffix, the normalised `ai-foundry` address in `requested`, the final `?accept=` address in `original.url`, the body starting at the Twin's first heading, `title` from the Twin's frontmatter and `modified: 2026-08-13` parsed from its `ms.date`
- [ ] the AWS Twin fixture is stored under `…/prompt-caching.html` (the `page_suffix` restored) with `original.url` ending in `.md`
- [ ] `get` of the Anthropic page by its Twin address (`….md`) and by its page address store and find one Version
- [ ] the `google-md-answers-html` fixture, with a test `lorekeep.toml` rule giving `cloud.google.com` a `md-suffix` Twin, is not stored and `get` reports no Twin
- [ ] second `get` of the same URL, and a `get` of the Microsoft page by its original `ai-foundry` address: zero transport calls, same path, one new `tags.csv` row only when the Tag is new
- [ ] `get` without a Tag exits non-zero before any request; an unknown host warns on stderr
- [ ] every recorded request carries a `User-Agent` that starts with `lorekeep/`
