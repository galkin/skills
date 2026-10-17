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
2. As a pipeline worker, I want `get` to return the stored Version when one is fresh enough, so
   that the same page is never fetched twice in a Run.
3. As a pipeline worker, I want `get` of a page another Run fetched to return that Version and
   add my Run's Tag to it, so that nothing is fetched again across ecosystems.
4. As a pipeline worker, I want `get` of a Version older than the Project's freshness window to ask
   the publisher whether it changed before returning it, so that a Run months after the last one
   does not read stale pages without knowing.
5. As a pipeline worker, I want `get --fresh` to force that question regardless of age, so that I
   can insist on the current text for a fact in dispute.
6. As a pipeline worker, I want `get` to prefer the publisher's Markdown Twin (`.md`,
   `?accept=text/markdown`, a raw file host), so that I read the complete text with every code tab.
7. As a pipeline worker, I want `get` to accept a Twin only when the response really is Markdown,
   so that a host that answers `.md` with HTML does not poison the Store.
8. As a pipeline worker, I want `get` to extract the main content of a static HTML page and make
   its links absolute, so that navigation, cookie banners and `<div>` noise never reach me.
9. As a pipeline worker, I want `get` to follow HTTP redirects and `<meta http-equiv="refresh">`
   stubs, so that a redirect page is never stored as the page.
10. As a pipeline worker, I want `get` to fall back to a browser when a host refuses a plain client
    or renders on the client, so that such pages are still readable without my intervention.
11. As a pipeline worker, I want `get` to convert PDF and Office files to Markdown, so that an exam
    guide published as a PDF is read like any page.
12. As a pipeline worker, I want `get` to cut a very long document into parts by article or
    heading, so that I can `grep` one article of a regulation rather than print the whole law.
13. As a pipeline worker, I want `get` to print a warning when the host is not in the Project's
    host table, so that the owner learns to extend the table and I learn not to cite the page.
14. As the owner, I want `get` to refuse to run without a Tag, so that no Source is ever untagged.
15. As the owner, I want `add <file> --title …` to store research I pasted from a chat as a Source
    with `origin: owner` and `authority: generated`, so that it is searchable like any page while
    no brief ever cites it.
16. As the owner, I want a Source fetched under a URL that redirects or declares a canonical URL to
    be stored under that canonical URL, so that one page never lives in the Store twice.

### Provenance

17. As a pipeline reviewer, I want every Version's frontmatter to say its `url`, `fetched_at`,
    `sha256`, `publisher`, `authority` and `converter` with its version, so that I know what I am
    reading and how far to trust it without leaving the file.
18. As a pipeline reviewer, I want the `etag`, `last_modified` and the publisher's own `modified`
    date recorded when available, so that "checked as of" is a fact and not a guess.
19. As a pipeline reviewer, I want the Original the Markdown was made from stored beside it with
    its own hash, so that a doubtful conversion can be checked against the bytes received.
20. As the owner, I want the Original not stored when it is byte-identical to the Markdown (a Twin),
    so that the Store and the bucket are not doubled for nothing.
21. As the owner, I want every Version named `<host>--<path>--<sha8>.md` in one flat folder, so
    that I can see what a file is from its name and a changed page sits beside its older text.
22. As the owner, I want no file in the Store ever rewritten or deleted by the tool, so that the
    text a finished work was written from is always still there.
23. As the owner, I want a `datapackage.json` describing the Store's files and tables, generated
    from the files, so that the Store is a standard package and never hand-maintained.

### Search

24. As a pipeline author, I want `search <query>` to return a few ranked snippets with file name and
    heading path, so that I spend a kilobyte, not a hundred, finding where something is said.
25. As a pipeline author, I want the search to understand word forms (`caching` finds `cached`), so
    that I do not have to guess the vendor's wording.
26. As a pipeline author, I want the search scoped to my Run's Tag by default, so that an Anthropic
    question is not answered with eight Bedrock pages.
27. As a pipeline author, I want every search to end with `+N matches under other tags (--all)`,
    so that a page another ecosystem's Run fetched is never silently invisible to me.
28. As a pipeline author, I want `--all`, `--tag`, `--publisher` and `--authority` to widen or
    narrow the scope, so that "only primary Anthropic pages" and "everything" are one flag away.
29. As a pipeline reviewer, I want `search --exact '<identifier>'` or plain `grep` to keep working
    for exact identifiers, so that `cache_control` is found as written.
30. As a pipeline author, I want a page without headings still searchable in Sections of bounded
    size, so that an API reference or a PDF yields a snippet rather than a whole file.
31. As the owner, I want `index` to rebuild `sources.db` from the Store's files in seconds, so that
    the Index is never something I have to protect or restore.
32. As the owner, I want `index` to ingest `tags.csv`, `checks.csv` and a Project-supplied
    `citations.csv`, so that one SQLite file answers questions about Tags, Rechecks and which works
    rest on which Sources.

### Rechecking

33. As the owner, I want `recheck` to ask each Source's publisher whether it changed, using a
    conditional request when the server supports it and a full fetch compared by the Original's
    hash otherwise, so that the question costs one request and no tokens.
34. As the owner, I want every Recheck appended to `checks.csv` whatever the answer, so that "last
    verified on" is recorded even when nothing changed.
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
39. As the owner, I want the growing files (`tags.csv`, `checks.csv`, `datapackage.json`,
    `lorekeep.toml`) copied on every backup, so that the bucket reflects them, with history kept by
    the bucket's own versioning.
40. As the owner, I want the Index and its journal files excluded from the backup, so that a
    derived file is never restored over a rebuilt one.
41. As the owner, I want `backup --dry-run` to show what would be copied, so that I can trust it
    before the first real run.
42. As the owner, I want `restore <name>` to fetch one object, or a named older generation of it,
    from the bucket, so that recovering a deleted Version is one documented command.

### Working together

43. As the owner, I want six workers to call `get` against one Store concurrently without
    corrupting a file, a CSV or the Index, so that the pipeline needs no coordination around the
    Store.
44. As the owner, I want the Store's location and the Project's settings (bucket, host table,
    freshness window) read from `SOURCES_ROOT` and `lorekeep.toml` in the Store, so that nothing
    is hardcoded and the configuration is backed up with the data.
45. As the owner, I want `tag add <tag> <url-or-prefix>` for migrated or hand-added Sources, so
    that what a migration brings in can be scoped like what a Run fetched.
46. As the owner, I want `status` to summarise a Store — Versions, Sources, Tags, oldest and newest
    fetch, unknown hosts seen — so that I can see its shape without opening SQLite.
47. As an agent in any repository, I want one short reference of the commands and their output
    formats, so that a brief can point at it instead of describing lorekeep.

## Implementation Decisions

These restate the ADRs in `docs/adr/` where a builder needs the detail; the ADRs win on conflict.

### Commands and layout

- A Python 3.12 package managed by `uv`, exposing one console script `lorekeep` with subcommands
  `get`, `add`, `search`, `index`, `recheck`, `backup`, `restore`, `tag`, `status`. Commands print
  human-readable text by default and `--json` for machine use; `get` prints the Version's path on
  its last line in both modes so a shell can capture it.
- The Store is `SOURCES_ROOT` (an environment variable or `--store`), one flat folder. The Run's
  Tag is `LOREKEEP_TAG` or `--tag`; `get` and `add` fail without one.
- `lorekeep.toml` in the Store root holds: `bucket`, `freshness_days` (default 30), and the host
  table — ordered rules of `prefix → publisher, authority`, matched on `host/path` by longest
  prefix. An unmatched host yields `publisher = <host>`, `authority = third-party` and a warning on
  stderr.
- Version file name: `<host>--<path with every / and unsafe character as ->--<first 8 hex of
  sha256>.md`; the path part is cut to keep the whole name under 200 bytes. Original:
  `<same stem>.orig.<ext>` where `ext` follows the Original's media type. Sidecar for non-Markdown
  Versions: `<name>.meta.yml`. Owner-added Sources use `owner--<slug>--<sha8>.md` with
  `url: owner:<slug>`.
- Growing files, all append-only CSV with a header: `tags.csv` (`url, tag, added_at`),
  `checks.csv` (`url, checked_at, result, status, sha256`), and `citations.csv` (`work_id, url`),
  the last written by the consuming Project, never by lorekeep.

### URL normalisation

- Lower-case scheme and host, `http` → `https` when the host answers it, drop the fragment, drop
  tracking parameters (`utm_*`, `ref`, `source`, `fbclid`, `gclid`), sort the remaining query
  parameters, drop a trailing slash, collapse duplicate slashes. All other query parameters are
  kept: they can select content (`?view=`, `?tabs=` on Microsoft Learn).
- The stored `url` is the final one after HTTP redirects and after a Twin's `canonicalUrl`
  frontmatter when present; the requested URL is kept in `original.url` when it differs.

### The cascade (`get`)

1. Twin: for a known host, the Twin URL rule from the host table (`<page>.md`,
   `?accept=text/markdown`, `raw.githubusercontent.com` rewrite); accepted only when the response
   media type is `text/markdown` or `text/plain` from a raw host. `converter: md-twin`.
2. Static HTML over `httpx`: follow redirects and `<meta http-equiv="refresh">`; extract with
   Trafilatura (formatting, links, tables on); rewrite relative links to absolute against the final
   URL. `converter: trafilatura <version>`.
3. Documents: PDF and Office files through MarkItDown; `--layout` switches a PDF to Docling.
   `converter: markitdown <version>` or `docling <version>`.
4. Browser: Crawl4AI, an optional dependency, used when step 2 gets `403`/`429`, an empty or
   JavaScript-only body, or when the host table marks the host `browser = true`; a per-host
   selector list in the host table says what to cut. `converter: crawl4ai <version>`.
5. Splitting: a Markdown body over a configurable size (default 150 KB) is cut at
   `Article N` / `Статья N` / `ANNEX` / top-level headings into part files with `part_of` and
   `part` set, and an index part listing them.

- `httpx` runs through an `hishel` file cache in the user's cache directory (never the Store) so a
  repeat request is conditional for free.
- Freshness: if the latest Version is younger than `freshness_days` and `--fresh` is absent,
  return it and append the Tag if missing. Otherwise send a conditional request (`If-None-Match`,
  `If-Modified-Since`); `304` → append a `checks.csv` row and return the latest Version; `200` →
  convert, compare `original.sha256` (or the Markdown hash for a Twin) with the latest Version:
  equal → `checks.csv` row, return latest; different → new Version, `checks.csv` row with
  `changed`.
- The browser and the `gcloud` binary are reached through two small interfaces (a page fetcher and
  a command runner) that the command layer receives; production wires Crawl4AI and `subprocess`,
  tests wire fakes.

### Provenance frontmatter

- Required: `url`, `fetched_at` (UTC ISO 8601), `sha256` (of the Markdown body, after the
  frontmatter), `publisher`, `authority` (`primary | official | third-party | generated`),
  `converter`. When served: `etag`, `last_modified`. Optional: `title`, `modified`,
  `original {url, mediatype, sha256, stored}`, `part_of`, `part`, `extracted_from`, `origin`
  (`web | owner`, default `web`).
- Nothing that changes later is in the frontmatter; Tags and Rechecks are rows in their CSVs.

### Index (`index`, `search`)

- `sources.db` in the Store, WAL mode, rebuilt in full by `index` and updated incrementally by
  `get`/`add`/`recheck`/`tag`. Tables: `versions` (one row per Version, every frontmatter field,
  file name), `tags`, `checks`, `citations`, `sections` (version, heading path, body, order), and
  `sections_fts` — FTS5 external-content over `sections(heading, body)` with
  `tokenize = 'porter unicode61'`.
- Sections: split at Markdown headings; a Section over 4 KB is cut again at paragraph boundaries
  with the same heading path; code fences are never split.
- `search`: `bm25` ranking, `snippet()` of the body, default 5 results, `--limit`; output lines are
  `file | heading path | snippet`; the final line is always `+N matches under other tags (--all)`
  computed from the same query without the Tag filter (`+0` when none). `--exact` runs the query as
  an FTS5 phrase. `--json` returns the same as objects.
- Scope: default `tag = LOREKEEP_TAG`; `--all`; `--tag a,b`; `--publisher`; `--authority`.

### Recheck

- Iterates the latest Version per Source in scope, performs the conditional request or full fetch
  as in `get`, appends to `checks.csv`, stores new Versions. `--citations` joins `citations.csv`
  with `versions` and prints `work_id, url, old sha8 → new sha8` for every work whose cited Source
  has a Version newer than the one the work was written from: the Version current at the time in
  `citations.csv`'s optional third column `as_of`, or the oldest Version when `as_of` is absent.

### Backup

- `backup` runs two `gcloud storage rsync` invocations through the command runner: (1) the Store
  with `--recursive --no-clobber --exclude='^(tags|checks)\.csv$|^datapackage\.json$|^lorekeep\.toml$|^sources\.db(-wal|-shm)?$'`;
  (2) the four growing files with `gcloud storage cp`. `--dry-run` passes through. Nothing in
  `backup` deletes.
- `restore <name> [--generation N]` runs `gcloud storage cp gs://<bucket>/<name>[#N] <store>/` and
  refuses to overwrite an existing local file.
- `datapackage.json` is regenerated before every backup and by `index`: resources for each CSV with
  a typed schema, and one `sources` resource listing every Version with its frontmatter fields,
  `hash` and `bytes`.

### Concurrency

- Versions and Originals: write to `<name>.tmp-<pid>` then `os.replace`; an existing target is left
  alone (same hash, same bytes).
- CSV appends and `datapackage.json` regeneration under one `fcntl` lock file in the Store.
- SQLite in WAL mode with a busy timeout; incremental updates are small transactions.

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
  `tests/fixtures/` (status, headers, body), and fakes for the page fetcher (browser) and the
  command runner (`gcloud`) that record their calls and return canned results.
- Fixtures are the five measured pages (three termidy lessons, Anthropic and AWS `prompt-caching`,
  each as HTML and as Twin) plus one each of: a `.md` URL answering HTML, a meta-refresh stub, a
  `403` to the plain client, a `304`, a Microsoft Learn Twin with `canonicalUrl`, a long legal text
  with Articles, a PDF. Fixtures are committed; the live network is touched only by one manual
  smoke script outside `pytest`.
- Concurrency is tested with a process pool calling `get` on the same URLs against one Store and
  asserting one file per Version, complete CSVs and a consistent Index.
- `pytest`, `ruff`, `pyright` are the whole gate; no coverage threshold.

## Out of Scope

- The Collector (the LLM step that decides what to fetch) and any change to the
  `orca-author-reviewer` skill or the first Project's briefs.
- Migration of existing archives into a Store, and producing `citations.csv` from the Project's
  lessons — both belong to the consuming Project and a later session.
- Vector or semantic search; a trigram FTS table.
- A daemon, a watcher, or a scheduled backup (the `launchd` job is proposed separately).
- WACZ capture of whole sites; `rclone`; any backend other than GCS.
- Licences, permissions, or any rights metadata.
- Publishing the package to PyPI (the name is taken by another project).

## Further Notes

- Decisions and their reasons: `docs/adr/0001` – `0009`; vocabulary: `GLOSSARY.md`. Use its terms
  in code and output (`Version`, `Original`, `Tag`, `Recheck`, `Section`).
- Measurements behind the cascade and the Index (converter sizes, FTS size and timing, top-10
  contamination across ecosystems) are quoted in ADR 0003, 0005 and 0008.
- The first Store will be `~/orca/sources/agentic-system.design/` with bucket
  `agentic-system-design-sources` (already created, versioned, public access prevented).
