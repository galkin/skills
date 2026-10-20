# lorekeep v1: a Store of Sources with Provenance, search and backup

Status: ready-for-agent

## Problem Statement

Every Run of the guide pipeline reads hundreds of vendor pages, and today each Run keeps them in a
cache of its own that is tarred up with its logs when the Run ends. Nothing in a cached file says
where it came from or when; a third of one Run's cache is HTML wrapped as Markdown; a later Run of
the same guide starts from nothing; and when a vendor updates its documentation there is no way to
learn which finished lessons rest on a page that changed. Material a site owner allowed us to reuse
(a site that is closing) was archived by hand in a format of its own. An agent looking for a fact
greps a 70 MB folder and reads 50,000 tokens of matches to find one paragraph.

## Solution

`lorekeep` is a command-line tool, with no LLM inside it, that keeps one Store per Project: a flat
folder of Markdown Versions, each with its Provenance in frontmatter and its Original beside it.
`get` fetches a page through a cascade that prefers the publisher's own Markdown and uses a browser
only when nothing else works; `search` answers from a SQLite Index of heading-level Sections with
short snippets scoped to the Run's Tag; `recheck` asks publishers what changed and, with the
Project's Citations, names the finished works to revisit; `backup` copies the Store to a private
bucket without ever deleting or overwriting there. Several workers use one Store at once. Every
file is written once, and the Index can always be rebuilt from the files.

## User Stories

### Fetching

1. As a pipeline worker, I want `get <url>` to return the path of a Markdown Version of that page,
   so that I can `grep` it without fetching or converting anything myself.
2. As a pipeline worker, I want `get` to return the stored Version when one is fresh enough —
   fetched or confirmed unchanged within the window — so that the same page is never fetched twice
   in a Run.
3. As a pipeline worker, I want `get` of a page another Run fetched to return that Version and
   add my Run's Tag to it, so that nothing is fetched again across ecosystems.
4. As a pipeline worker, I want `get` of a Version older than the Project's freshness window to ask
   the publisher whether it changed before returning it, so that a Run months after the last one
   does not read stale pages without knowing.
5. As a pipeline worker, I want `get --fresh` to force that question regardless of age, so that I
   can insist on the current text for a fact in dispute.
6. As a pipeline worker, I want `get` to prefer the publisher's Markdown Twin (`.md`,
   `?accept=text/markdown`, a raw file host), and to accept the Twin's own URL when a brief hands
   me that, so that I read the complete text with every code tab.
7. As a pipeline worker, I want `get` to accept a Twin only when the response really is Markdown,
   so that a host that answers `.md` with HTML does not poison the Store.
8. As a pipeline worker, I want `get` to extract the main content of a static HTML page and make
   its links absolute, so that navigation, cookie banners and `<div>` noise never reach me.
9. As a pipeline worker, I want `get` to follow HTTP redirects and `<meta http-equiv="refresh">`
   stubs, so that a redirect page is never stored as the page.
10. As a pipeline worker, I want `get` to fall back to a browser when a host refuses a plain client
    or renders on the client, so that such pages are still readable without my intervention.
11. As a pipeline worker, I want `get` to convert a PDF to Markdown, so that an exam guide
    published as a PDF is read like any page.
12. As a pipeline worker, I want `get` of a Source whose page is gone (`404`/`410`) or whose host
    is unreachable to return the stored Version with a warning, so that a vendor removing a page
    never stops a Run that already has its text.
13. As a pipeline worker, I want `get` to print a warning when the host is in neither the package's
    default host table nor the Project's, so that the owner learns to extend the table and I learn
    not to cite the page.
14. As the owner, I want `get` to refuse to run without a Tag, so that no Source is ever untagged.
15. As the owner, I want `add <file> --title …` to store research I pasted from a chat as a Source
    with `origin: owner` and `authority: generated`, so that it is searchable like any page while
    no brief ever cites it.
16. As the owner, I want a Source fetched under a URL that redirects or declares a canonical URL to
    be stored under that canonical URL and found again under either address, even when the old
    address is first used after the page is already stored, so that one page never lives in the
    Store twice and is never fetched twice because a brief used the old address.

### Provenance

17. As a pipeline reviewer, I want every Version's frontmatter to say its `url`, `fetched_at`,
    `sha256`, `publisher`, `authority` and `converter` with its version, so that I know what I am
    reading and how far to trust it without leaving the file.
18. As a pipeline reviewer, I want the `etag`, `last_modified` and the publisher's own `modified`
    date recorded when available, so that "checked as of" is a fact and not a guess.
19. As a pipeline reviewer, I want the Original the Markdown was made from stored beside it with
    its own hash, so that a doubtful conversion can be checked against the bytes received.
20. As the owner, I want the Original not stored for a Twin, whose Markdown is the text received,
    so that the Store and the bucket are not doubled for nothing.
21. As the owner, I want every Version named `<host>--<path>--<sha8>.md` in one flat folder, so
    that I can see what a file is from its name and a changed page sits beside its older text.
22. As the owner, I want no file in the Store ever rewritten or deleted by the tool, so that the
    text a finished work was written from is always still there.
23. As the owner, I want a `datapackage.json` describing the Store's files and tables, generated
    from the files, so that the Store is a standard package and never hand-maintained.

### Search

24. As a pipeline author, I want `search <query>` to return a few ranked snippets with `file:line`
    and heading path, so that I spend a kilobyte, not a hundred, finding where something is said
    and can open the file at that line without searching for the heading again.
25. As a pipeline author, I want the search to understand word forms (`caching` finds `cached`), so
    that I do not have to guess the vendor's wording.
26. As a pipeline author, I want the search scoped to my Run's Tag by default, so that an Anthropic
    question is not answered with eight Bedrock pages.
27. As a pipeline author, I want every search to end with `+N matches under other tags (--all)`,
    so that a page another ecosystem's Run fetched is never silently invisible to me.
28. As a pipeline author, I want `--all`, `--tag`, `--publisher` and `--authority` to widen or
    narrow the scope, so that "only primary Anthropic pages" and "everything" are one flag away.
29. As a pipeline reviewer, I want `search --exact '<identifier>'` to match the text as written,
    so that `cache_control` is found as one word and not as `cache` near `control`.
30. As a pipeline author, I want a page without headings still searchable in Sections of bounded
    size, so that an API reference or a PDF yields a snippet rather than a whole file.
31. As the owner, I want `index` to rebuild `sources.db` from the Store's files in seconds, so that
    the Index is never something I have to protect or restore.
32. As the owner, I want `index` to ingest `tags.csv`, `checks.csv` and a Project-supplied
    `citations.csv`, so that one SQLite file answers questions about Tags, Rechecks and which works
    rest on which Sources.

### Rechecking

33. As the owner, I want `recheck` to ask each Source's publisher whether it changed, using a
    conditional request when the server supports it and a full fetch compared by received bytes and
    then by Markdown otherwise, so that the question costs one request and no tokens, and a page
    whose HTML carries a per-request id is not recorded as changed every time.
34. As the owner, I want every Recheck appended to `checks.csv` whatever the answer — unchanged,
    changed, gone or error — and the Sources it cannot ask counted as skipped, so that "last verified on" is recorded even when nothing changed and a
    removed page is on record.
35. As the owner, I want a changed page stored as a new Version beside the old, so that both the
    text a lesson was written from and the current text are kept.
36. As the owner, I want `recheck --citations` to list the finished works whose cited Sources
    changed since they were written, so that a vendor update becomes a to-do list.
37. As the owner, I want `recheck` restricted by `--tag`, `--publisher` or a URL prefix, so that a
    new guide version revisits only its own ecosystem.

### Backup

38. As the owner, I want `backup` to copy the Store to the Project's bucket without deleting
    anything there and without replacing an object already there, so that a local `rm` never
    propagates and an object is never overwritten.
39. As the owner, I want the growing files (`tags.csv`, `checks.csv`, `aliases.csv`,
    `citations.csv`, `datapackage.json`, `lorekeep.toml`) copied on every backup, so that the bucket reflects them,
    with history kept by the bucket's own versioning.
40. As the owner, I want the Index with its journal files, the lock file and half-written temporary
    files excluded from the backup, so that a derived or unfinished file never reaches the bucket.
41. As the owner, I want `backup --dry-run` to show what would be copied, so that I can trust it
    before the first real run.
42. As the owner, I want `restore <name>` to fetch one object, or a named older generation of it,
    from the bucket, and the README to give the commands that bring a whole Store back from the
    bucket onto an empty disk, so that both recoveries are documented before they are needed.

### Working together

43. As the owner, I want six workers to call `get` against one Store concurrently without
    corrupting a file, a CSV or the Index, so that the pipeline needs no coordination around the
    Store.
44. As the owner, I want the Store's location and the Project's settings (bucket, host table,
    freshness window) read from `LOREKEEP_STORE` and `lorekeep.toml` in the Store, so that nothing
    is hardcoded and the configuration is backed up with the data.
45. As the owner, I want `tag add <tag> <url>` and `tag add <tag> --prefix <url-prefix>` for
    migrated or hand-added Sources, so that what a migration brings in can be scoped like what a
    Run fetched.
50. As the owner, I want `search` and `recheck` without a Tag to cover the whole Store, so that I
    can look at everything from my shell while a Run stays scoped to its own Tag.
51. As the owner, I want the Twin rules and publishers of the hosts already probed shipped inside
    the package, so that a new Project's `lorekeep.toml` only adds what is specific to it.
46. As the owner, I want `status` to summarise a Store — Versions, Sources, Tags, oldest and newest
    fetch, unknown hosts seen — so that I can see its shape without opening SQLite.
47. As an agent in any repository, I want a skill that teaches lorekeep's commands and output
    formats, shipped inside the package and printed by `lorekeep skill`, so that a brief points at
    the skill and the guide always matches the installed version.
48. As the owner, I want `lorekeep skill --install <repo>` to vendor that skill into a repository's
    `.agents/skills/lorekeep/`, refusing to replace an existing copy without `--force` and reminding
    me that the repository's skill lock needs updating, so that every agent tool in that repo finds
    it the way it finds the other skills.
49. As a pipeline worker, I want `get --max-age <days>` to override the Project's freshness window
    for one call, so that a brief can demand a 1-day-fresh page without touching the Store's
    configuration.

## Implementation Decisions

These restate the ADRs in `docs/adr/` where a builder needs the detail; the ADRs win on conflict.

### Commands and layout

- A Python 3.12–3.13 package managed by `uv` (`requires-python = ">=3.12,<3.14"`; the owner's
  machine has 3.13, and 3.14 lacks an `onnxruntime` wheel); runtime dependencies are `httpx`, `trafilatura` (which
  brings `lxml`), `markitdown[pdf]`, `cssselect` (what `lxml` needs for CSS selectors; it comes with
  neither `lxml` nor Trafilatura), `PyYAML` (frontmatter is read with `yaml.BaseLoader`, which
  yields strings only — `safe_load` turns `2026-08-13T00:00:00.0000000Z` into a `datetime`;
  frontmatter is written with values quoted, so an ETag's quotes survive) and the optional
  `crawl4ai`; `frictionless` is a dev dependency. The package exposes one console script
  `lorekeep` with subcommands
  `get`, `add`, `search`, `index`, `recheck`, `backup`, `restore`, `tag`, `status`, `skill`. Commands print
  human-readable text; `get`, `add`, `search` and `status` also take `--json`, and no other
  command does.
  In text mode `get` prints the Version's path on its last line so a shell can capture it; with
  `--json` it prints one object `{path, url, sha256, fetched_at, converter, publisher, authority,
  verified_at, outcome}` (`outcome` one of `stored | fresh | unchanged | changed | gone | error |
  skipped`, `fresh` meaning returned without any request; `verified_at` the `checked_at` of the last `unchanged` row or else `fetched_at`) and
  nothing follows it; `add --json` prints the same object with `outcome: stored`. `search --json` prints `{results: [{file, line, heading, snippet, url,
  tag[]}], other_tags: N}`; `status --json` prints `{versions, sources, tags: {name: count}, oldest_fetched_at,
  newest_fetched_at, checks: {unchanged, changed, gone, error}, unknown_hosts: [host], bytes}`.
  Warnings go to stderr in every mode.
- A Store folder is never created by lorekeep: a `--store` that does not exist is an error.
- The Store is `LOREKEEP_STORE` (an environment variable or `--store`), one flat folder. The Run's
  Tag is `LOREKEEP_TAG` or `--tag`; `get` and `add` fail without one and accept exactly one;
  `search` and `recheck` take `--tag` repeated as their scope and without any cover the whole
  Store. `--tag`, like every flag, belongs to the subcommand, never to the root parser.
- The host table is two layers: a default table shipped in the package (every host probed so far,
  with its Twin rule, `publisher` and `authority`), and `lorekeep.toml` in the Store root, which
  holds `bucket`, `freshness_days` (default 30) and rules that extend or override the default.
  Rules are matched on `host/path` by longest prefix. A host matched by neither layer yields
  `publisher = <host>`, `authority = third-party` and a warning on stderr. The shape, in
  `lorekeep.toml` and in the package default alike (every key but `publisher` and `authority` is
  optional):

  ```toml
  [[hosts]]
  prefix = "learn.microsoft.com/"
  publisher = "microsoft"
  authority = "primary"
  twin = "accept-header"        # "md-suffix" | "accept-header" | "raw" | absent (no Twin)

  [[hosts]]
  prefix = "docs.aws.amazon.com/"
  publisher = "aws"
  authority = "primary"
  twin = "md-suffix"
  page_suffix = ".html"         # what md-suffix replaces; absent means .md is appended

  [[hosts]]
  prefix = "example.test/app/"
  publisher = "example"
  authority = "third-party"
  browser = true
  cut = ["nav", ".cookie-banner"]
  ```

  `md-suffix` replaces the page's `page_suffix` (or appends when there is none) with `.md`, and
  the reverse reduction puts `page_suffix` back; `accept-header` adds `?accept=text/markdown`;
  `raw` means the URL as given answers plain text and is its own Twin. The package default table
  holds exactly: `platform.claude.com/` → `anthropic`, primary, `md-suffix`;
  `docs.aws.amazon.com/` → `aws`, primary, `md-suffix` with `page_suffix = ".html"`;
  `learn.microsoft.com/` → `microsoft`, primary, `accept-header`; `docs.nvidia.com/` → `nvidia`,
  primary; `cloud.google.com/` → `google`, primary; `milvus.io/` → `milvus`, primary (no
  `browser` flag: the `403` is the signal); `claude.termidy.com/` → `termidy`, third-party;
  `raw.githubusercontent.com/` → `github`, third-party, `raw`.
- Finding the latest Version of a URL never needs the Index: without one, the frontmatter of
  every `.md` file in the Store is read (a few thousand small headers, well under a second) and
  matched against the normalised request on `url`, and `aliases.csv` is consulted for an address
  that maps to a `url`; among a Source's Versions the one named by the `sha256` of its latest
  `checks.csv` row wins, and the newest `fetched_at` when there is no row — a page that goes
  A → B → A reuses A's immutable file, and only the log says it is current again. With a current
  Index the same question is one query; with a stale or missing one the lookup falls back to the
  scan and never rebuilds: rebuilding is for `search`, `recheck`, `status` and `index`.
- Version file name: `<host>--<path with every / and unsafe character as ->--<first 8 hex of
  sha256>.md`; the path part is cut to keep the whole name under 200 bytes. The *stem* is that
  name without `.md`, hash included; two Versions of one page share a prefix, never a stem.
  Original: `<stem>.orig.<ext>` where `ext` follows the Original's media type, so every Version
  has its own Original and `original.stored` is a boolean. Every Version is Markdown. Owner-added
  Sources use `owner--<slug>--<sha8>.md` with `url: owner:<slug>`.
- Growing files, all append-only CSV with a header: `tags.csv` (`url, tag, added_at`),
  `aliases.csv` (`alias, url, added_at` — an address that led to a Version stored under another
  `url`),
  `checks.csv` (`url, checked_at, result, status, sha256` — `result` is one of `unchanged`,
  `changed`, `gone`, `error`; `status` the HTTP status code, or the exception's class name such as
  `ReadTimeout` when there was no response;
  `sha256` the Markdown hash of the Version that is latest after the check), and `citations.csv`
  (`work_id, url[, as_of]`), the last written by the consuming Project, never by lorekeep. Six
  growing files in all.
- The lock file is `.lorekeep.lock` in the Store root; temporary files are `<name>.tmp-<pid>`.
  Both are excluded from backup.

### URL normalisation

- Lower-case scheme and host, percent-decode the query values (`text%2Fmarkdown` is
  `text/markdown`; the path keeps its encoding), drop the fragment, drop tracking parameters (`utm_*`, `ref`,
  `source`, `fbclid`, `gclid`), sort the remaining query parameters, drop a trailing slash,
  collapse duplicate slashes. All other query parameters are kept: they can select content
  (`?view=`, `?tabs=` on Microsoft Learn). `http` is not rewritten; redirects decide.
- A request that is itself a Twin URL under a host rule (`….md`, `?accept=text/markdown`) is
  reduced to the page URL first, so a brief that hands over the Twin's address finds the same
  Version.
- What goes on the wire is the address as given (or the Twin address built from it by the host
  rule), untouched; normalisation applies to what is stored, looked up and compared, never to
  what is sent.
- The stored `url` is the final one after HTTP redirects (and meta refreshes), normalised, with
  the Twin suffix removed. When the normalised address asked for differs from `url`, the pair is
  appended to `aliases.csv` by the commit — also when the Version already existed, which is the
  case a frontmatter field could not record. *Amended by v1.1 (ticket 02):* a Twin's
  `canonicalUrl` or an HTML page's `<link rel="canonical">` no longer decides `url` — it is
  recorded as frontmatter `canonical` when it differs, with a warning, and never as an alias —
  because OWASP's 2025 Excessive Agency page declares the 2023 Sensitive Information Disclosure
  page as canonical and v1 filed one under the other. `original.url` is something else: the address the bytes
  came from (the Twin URL, the target of a meta-refresh stub).

### The cascade (`get`)

1. Twin: for a host whose rule names one, the Twin URL per the rule's `twin` kind; accepted only
   when the response media type is `text/markdown`, or `text/plain` under a `raw` rule. The Twin's
   own frontmatter, if any, is removed from the body and mined for `title`, `canonicalUrl` and
   `modified` (the first present of `ms.date`, `updated_at`, `lastmod`, `date`); the body is
   otherwise as published, links included, with leading blank lines removed. A Twin URL that
   answers anything but Markdown is discarded and the page URL is fetched by step 2. `converter:
   md-twin`; the Original is not stored, `original.sha256` hashes the bytes received.
2. Static HTML over `httpx`: follow redirects and `<meta http-equiv="refresh">`; extract with
   Trafilatura (formatting, links, tables on, the final URL passed as `url`, which is what makes
   its links absolute). `converter: trafilatura <version>`.
3. PDF: a response whose media type is `application/pdf` — whatever the URL ends in — goes
   through MarkItDown with its `pdf` extra. `converter: markitdown <version>`.
4. Browser: Crawl4AI, an optional extra (`lorekeep[browser]`), used on a first fetch when step 2
   gets `403`/`429`, an empty or JavaScript-only body, or when the host rule says `browser = true`.
   The page fetcher returns the rendered document (`result.html`, untouched by Crawl4AI's own
   pruning) and the final URL; lorekeep removes the rule's `cut` selectors itself with `lxml`
   and `cssselect`, then step 2 converts that HTML and stores it as the
   Original. `converter: trafilatura <version> via crawl4ai <version>` (the Crawl4AI version
   string is `crawl4ai.__version__.__version__`; `crawl4ai.__version__` is a module).

- Plain `httpx`, no cache library: the Store is the cache and the conditional requests below are
  lorekeep's own. The client sends a `User-Agent` naming lorekeep and its version.
- Freshness: the window is `freshness_days` from `lorekeep.toml` (default 30) unless `--max-age
  <days>` is given on the call; `--fresh` is `--max-age 0`. A Version's age is counted from the
  later of its `fetched_at` and its last `checks.csv` row of any result, so a gone or failing
  page is asked once per window, not once per call. If the latest Version is
  younger than the window, return it and append the Tag if missing. Otherwise send a conditional
  request (`If-None-Match`, `If-Modified-Since` from the frontmatter) to `original.url`, the
  address the Version's bytes came from; `304` → `unchanged` row, return the latest Version;
  `200` → the media-type gate of the Version's step applies first (a Twin address answering
  `text/html` is `error` with status `200`, never stored), then compare the received bytes with
  `original.sha256`: equal → `unchanged`; different → convert with the Version's step and compare
  the Markdown hash with the Version's: equal → `unchanged`; different → new Version and a
  `changed` row. `404`/`410` → `gone` row, a warning, the latest Version is returned; a publisher
  that dropped its Twin shows up as `gone` and the next `get --fresh` on the page runs the whole
  cascade. Any other status (`403`,
  `429`, `5xx`) → `error` row with that status, a warning, the latest Version returned — the
  browser is never used for a comparison; a transport exception → `error` row with the exception's class name, likewise.
  Without any stored Version the same failures exit non-zero. A Version whose `converter` says
  `via crawl4ai` is never rechecked by `get`: it is returned with a warning and `outcome:
  skipped`, because rendered bytes differ on every visit.
- The browser and the `gcloud` binary are reached through two small interfaces (a page fetcher and
  a command runner) that the command layer receives; production wires Crawl4AI and `subprocess`,
  tests wire fakes.

### Provenance frontmatter

- Required: `url`, `fetched_at` (UTC ISO 8601), `sha256` (of the Markdown body, after the
  frontmatter), `publisher`, `authority` (`primary | official | third-party | generated`),
  `converter`. When served: `etag`, `last_modified`. Optional: `title`, `modified` (a date,
  `YYYY-MM-DD`, parsed leniently from whatever the publisher gives — `2026-08-13T00:00:00.0000000Z`
  becomes `2026-08-13` — and omitted when nothing parses), `original {url, mediatype,
  sha256, stored}`, `origin` (`web | owner`, default `web`).
- Nothing that changes later is in the frontmatter; Tags and Rechecks are rows in their CSVs.
- One commit point: every command that writes to the Store goes through one function of the
  Store module whose full signature is fixed in the first ticket that builds it: an optional
  Version (frontmatter plus body) with its optional Original bytes, a list of `tags.csv` rows and
  a list of `checks.csv` rows and a list of `aliases.csv` rows — any of them may be empty — and it
  takes `.lorekeep.lock`, renames the files into place, appends the rows that are not already
  present (so two workers tagging one page under one lock produce one row), notifies the Index,
  and releases the lock. Later tickets pass different arguments; the Index ticket fills only the
  notification; nobody widens the signature. The lock itself is one named context manager of the
  Store module, which the commit, an Index rebuild and the package regeneration share; nothing
  else takes it.

### Index (`index`, `search`)

- `sources.db` in the Store, WAL mode with a busy timeout, rebuilt in full by `index` and updated
  incrementally through the commit point by `get`/`add`/`recheck`/`tag`. Tables: `versions` (one
  row per Version, every frontmatter field, file name), `tags`, `checks`, `aliases`, `citations`,
  `sections`
  (version, heading path, line of the heading in the file, body, order), and `sections_fts` —
  FTS5 external-content over `sections(heading, body)` with `tokenize = 'porter unicode61'`.
- Staleness: a command that reads the Index first compares, without any lock, the count of
  `.md` files with the `versions` rows and the size and mtime of `tags.csv`, `checks.csv`,
  `aliases.csv` and `citations.csv` with the values the Index recorded in its `meta` table at build time. Only on a
  mismatch or a missing file does it take the Store lock, compare again, and rebuild if still
  stale; so queries never wait, a commit (which holds the lock from rename to notification) is
  never seen half-done, six workers finding no Index produce one rebuild, and a rewritten
  `citations.csv` is picked up by the next `recheck --citations`. The incremental notification
  updates `meta` in the same transaction, so a commit never looks like staleness. A rebuild runs
  in place, in one transaction that empties and refills the tables, never by replacing the file
  under other processes' open connections. The lock is never taken twice by one command: a
  lookup queries without it, a commit and a rebuild each take it alone. `restore` and a
  hand-copied file are therefore picked up by the next `search`, `recheck`, `status` or `index`,
  and by a `get` through its scan.
- Sections: split at Markdown headings; a Section over 4 KB is cut again at paragraph boundaries
  with the same heading path; code fences are never split.
- `citations.csv` at ingest: `url` is normalised and Twin-reduced like a request, so a Project may
  cite the `.md` address; `as_of` is an ISO 8601 date or timestamp compared against `fetched_at`.
- `search`: `bm25` ranking, `snippet()` of the body, default 5 results, `--limit`; output lines are
  `file:line | heading path | snippet`; the final line is always `+N matches under other tags
  (--all)` where N counts distinct Sources matched by the same query outside the scope (`+0`
  when none), omitted when the scope is already everything. `--exact` is a case-sensitive substring match over `sections.body`
  instead of an FTS query, so an identifier is found as written. `--json` returns the same as
  objects.
- Scope: the latest Version of each Source (the one the lookup would return), so a page
  rechecked three times appears once; default `tag = LOREKEEP_TAG`, everything when no Tag is
  set; `--all`; `--tag` repeated;
  `--publisher`; `--authority`.

### Recheck

- Iterates the latest Version per Source in scope (`--tag` repeated, `--publisher`, `--prefix
  <url-prefix>`; default the Run's Tag, everything when no Tag is set), performs the conditional
  request or full fetch through the same cascade as `get` with the same outcomes, appends to
  `checks.csv`, stores new Versions and prints counts per outcome; `owner:` Sources and Versions
  whose `converter` says `via crawl4ai` are counted as `skipped` and asked nothing. `--citations`
  is a pure report, no request and no Tag needed: it joins `citations.csv`
  with `versions` and prints `work_id, url, old sha8 → new sha8` for every work whose cited Source
  has a Version newer than the one the work was written from: the Version current at the time in
  `citations.csv`'s optional third column `as_of`, or the oldest Version when `as_of` is absent.

### Backup

- `backup` runs two `gcloud storage` invocations through the command runner: (1) `rsync` of the
  Store with `--recursive --no-clobber` and an `--exclude` covering the six growing files,
  `sources.db` with `-wal`/`-shm`, `.lorekeep.lock` and `.tmp-`; (2) `cp` of the six growing files
  (`tags.csv`, `checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`, `lorekeep.toml`),
  those that exist. `--dry-run` is passed to `rsync`, which has it; `cp` has no such flag, so in
  dry-run the `cp` is not run and the files it would copy are printed instead. Nothing in
  `backup` deletes.
- `restore <name> [--generation N]` runs `gcloud storage cp gs://<bucket>/<name>[#N] <store>/` and
  refuses to overwrite an existing local file; the next Index read picks the file up. Bringing a
  whole Store back is a documented reverse `rsync` followed by `index`, in the README.
- `datapackage.json` is regenerated by `backup` only, under the Store lock: a resource for each
  CSV that exists, with a typed schema (`checks.csv`'s `status` is a string: it holds `304` and
  `ReadTimeout` alike), and one `sources` resource whose `data` is inline — one
  flat row per Version: `url, file, sha256, bytes, fetched_at, publisher, authority, converter`.
  The `#N` generation syntax of `restore` is documented by Google but was not exercised here; the
  smoke script proves it.

### Concurrency

- Versions and Originals: write to `<name>.tmp-<pid>` then `os.replace`; an existing target is left
  alone (same hash, same bytes).
- CSV appends, `datapackage.json` regeneration and Index rebuilds under the one `flock` lock file
  `.lorekeep.lock` in the Store (`fcntl.flock`, not `lockf`, which is re-entrant), through the Store module's one lock context manager.
- SQLite in WAL mode with a busy timeout; incremental updates are small transactions. The Store
  must be on a local filesystem, which WAL requires.

### The skill (`skill`)

- The package ships a `SKILL.md` (with any reference files beside it) that documents every
  command, its flags, its output format and the Store's layout for an agent, in the shape the
  `.agents/skills/` convention expects. `lorekeep skill` prints it; `lorekeep skill --install
  <repo>` copies the folder to `<repo>/.agents/skills/lorekeep/`, refuses when that folder exists
  unless `--force`, and ends by reminding that the repository's skill lock (if it keeps one) needs
  the new hash. `SKILL.md` is hand-written; a test parses its command sections and compares every
  flag with the parser's `--help`, so the two cannot drift.

### Owner-added Sources (`add`)

- `add <file> --title <t> [--publisher claude]` copies a Markdown or text file as a Version with
  `url: owner:<slug-of-title>`, `origin: owner`, `authority: generated` unless `--authority` says
  otherwise, `converter: owner`, the Run's Tag, and the file's modification time as `fetched_at`
  unless `--fetched-at` is given.

## Testing Decisions

- One seam: the command layer. A test calls a command in-process with argv and a temporary Store
  and asserts on what is observable from outside — files and their frontmatter, CSV rows, `search`
  output, exit code and printed text. Modules under the seam (normalisation, cascade steps, section
  splitting) are exercised only through commands.
- Two fakes at the seam's edge: an `httpx` mock transport serving recorded responses from
  `tests/fixtures/` (one folder per response: `response.json` with `url`, `status`, `headers`,
  optional `match_headers`, optional `error` naming an `httpx` exception to raise instead, and a
  body file; URLs compare after percent-decoding path and query and lower-casing the host (not as
  `httpx.URL`, whose equality keeps `%2F` and `/` apart); when several
  fixtures match, the one with the most matching `match_headers` wins; any other URL is answered
  `404` and recorded as a miss), and fakes for the page fetcher (browser) and the command runner
  (`gcloud`) that record their calls and return canned results; the fetcher fake also has a "not
  installed" mode. All three are built from paths and plain values, so a child process can
  construct its own. There is no clock edge. Two test helpers: one writes a Version straight from
  a fixture folder, body copied verbatim whatever its type, `original.sha256` and `original.url`
  of that response, with a chosen `fetched_at` — for lookup and Index tests that need files, not
  conversions; the other ages a Version already in a Store by rewriting `fetched_at` in its
  frontmatter, which leaves the file name valid because `sha256` covers only the body.
- Fixtures are committed already and described in `tests/fixtures/README.md`: the five measured
  pages (three termidy lessons, Anthropic and AWS `prompt-caching`, each as HTML and, for the two
  vendors, as Twin), the Microsoft Learn redirect chain ending in a Twin with `canonicalUrl`, the
  NVIDIA NIM meta-refresh stub with its target, and synthesised `403`, `304`, `.md`-answers-HTML,
  JavaScript-only, timeout, noisy-HTML, changed-HTML, canonical-alias and PDF responses. The live network is touched only by one manual smoke script
  outside `pytest`.
- Concurrency is tested with a process pool calling `get` on the same URLs against one Store and
  asserting one file per Version, complete CSVs and a consistent Index.
- `pytest`, `ruff`, `pyright` are the whole gate; no coverage threshold. `frictionless` is a dev
  dependency for the package test only.

## Out of Scope

- The Collector (the LLM step that decides what to fetch) and any change to the
  `orca-author-reviewer` skill or the first Project's briefs.
- Migration of existing archives into a Store, and producing `citations.csv` from the Project's
  lessons — both belong to the consuming Project and a later session.
- Vector or semantic search; a trigram FTS table.
- Splitting a long document into part Versions: Sections of 4 KB already answer "one article of a
  regulation", and parts would need an identity of their own beside the URL.
- An HTTP cache library (`hishel`): the Store is the cache, and a cache in between hides the `304`
  that `checks.csv` records.
- Politeness delays or per-host concurrency limits.
- Office documents and Docling (`--layout`): the stories ask for PDF; both return when a story
  does.
- Rewriting `github.com` URLs to `raw.githubusercontent.com`: a raw URL is accepted as given.
- A daemon, a watcher, or a scheduled backup (the `launchd` job is proposed separately).
- WACZ capture of whole sites; `rclone`; any backend other than GCS.
- Licences, permissions, or any rights metadata.
- Publishing the package to PyPI (the name is taken by another project).

## Further Notes

- A host added to the table after its pages were fetched does not change those Versions:
  frontmatter is immutable, so they keep `publisher = <host>` and `third-party` until a `get
  --fresh` stores a new Version. Known and accepted for v1.

- Decisions and their reasons: `docs/adr/0001` – `0009`; vocabulary: `GLOSSARY.md`. Use its terms
  in code and output (`Version`, `Original`, `Tag`, `Recheck`, `Section`).
- Measurements behind the cascade and the Index (converter sizes, FTS size and timing, top-10
  contamination across ecosystems) are quoted in ADR 0003, 0005 and 0008.
- The first Store will be `~/orca/sources/agentic-system.design/` with bucket
  `agentic-system-design-sources` (already created, versioned, public access prevented).
