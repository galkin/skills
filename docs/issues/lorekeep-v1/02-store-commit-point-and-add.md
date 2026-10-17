# 02: The Store, its commit point, and `add`

**What to build:** The Store module that every later command writes through, proven with the one command that needs no network. `add <file> --title <t>` copies a Markdown or text file into the Store as a Version `owner--<slug>--<sha8>.md` with `url: owner:<slug>`, `origin: owner`, `authority: generated` (or `--authority`), `publisher` from `--publisher` (default `owner`), `converter: owner`, `fetched_at` from the file's mtime or `--fetched-at`, and the Run's Tag. Underneath: URL normalisation as the spec lists it, including reducing a Twin URL to its page URL under a host rule; the two-layer host table lookup by longest prefix with the unknown-host warning; the Version file name with its 200-byte cut and the stem rule (stem = file name without `.md`, hash included); the lookup of the latest Version for a URL without an Index (read every file's frontmatter, match `url` and `original.url`, newest `fetched_at` wins) and through the Index when ticket 08 provides one; and one commit function that writes a Version (and an Original when there is one) to `<name>.tmp-<pid>` then renames, leaves an existing target alone, appends `tags.csv` rows under `.lorekeep.lock`, and calls an Index notification that is a no-op until ticket 08. A test helper writes a Version with a chosen `fetched_at` for later tickets.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `add` of a text file creates `owner--<slug>--<sha8>.md` with the fields above and one `tags.csv` row; `sha256` equals the hash of the body after the frontmatter; the path is printed last in text mode and as the `path` field of one object with `--json`
- [ ] `add` of the same content twice creates one file, prints the same path, adds a `tags.csv` row only under a new Tag
- [ ] `--authority primary` and `--publisher claude` are honoured; `--fetched-at` overrides the mtime
- [ ] `add` without a Tag, with two `--tag`, or without `--title` exits non-zero before writing
- [ ] normalisation (tested through the lookup helper and the file name): fragment, `utm_*`/`ref`/`source`/`fbclid`/`gclid` dropped, other query parameters kept and sorted, trailing slash dropped, duplicate slashes collapsed, host lower-cased, `http` left alone; `…/prompt-caching.md` on `platform.claude.com` and `…?accept=text/markdown` on `learn.microsoft.com` reduce to the page URL
- [ ] host table: longest-prefix match sets `publisher` and `authority`; a `lorekeep.toml` rule for `raw.githubusercontent.com/anthropics/` can be `primary` while the package default for the rest of the host is not; an unknown host → `third-party` plus a stderr warning naming the host
- [ ] lookup without an Index: given Versions written by the helper, the newest for a URL is found by `url` and by `original.url`; nothing is found for an unknown URL
- [ ] after a commit the Store contains `.lorekeep.lock` and no `.tmp-*` file; a file name over 200 bytes is cut in the path part and keeps the full `url` in the frontmatter
