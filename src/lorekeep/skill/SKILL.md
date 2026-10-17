---
name: lorekeep
description: >
  Use lorekeep to fetch, keep and search the Sources a task reads: vendor documentation,
  specifications, third-party pages, PDFs, research pasted from a chat. `lorekeep get <url>`
  returns the path of a Markdown Version with its Provenance; `lorekeep search <query>` answers
  with `file:line` snippets from the Project's Store. Use it instead of fetching a page yourself
  or grepping a cache folder, whenever a brief names lorekeep, LOREKEEP_STORE or LOREKEEP_TAG.
---

# lorekeep

lorekeep keeps one **Store** per Project: a flat folder of Markdown **Versions**, each with its
**Provenance** in frontmatter and the **Original** bytes it was made from beside it. There is no
LLM inside it; it fetches, converts, records and searches. You decide what to read; lorekeep makes
sure it is read once, kept, and findable by every later Run.

## Before you start

- `LOREKEEP_STORE` names the Store folder (or pass `--store DIR` to any command). lorekeep never
  creates a Store: a folder that does not exist is an error.
- `LOREKEEP_TAG` names your Run's **Tag** (or pass `--tag TAG`). `get` and `add` refuse to run
  without exactly one Tag, and every Source they return carries it. `search` and `recheck` use it
  as their default scope and cover the whole Store without one. A Tag is set by the Run, never
  chosen by you: do not invent one.
- Every flag belongs to its subcommand: `lorekeep get --tag x URL`, never `lorekeep --tag x get`.
- Warnings and errors go to stderr, prefixed `lorekeep: warning:` / `lorekeep: error:`; stdout
  carries only the result, so a shell can capture it.
- Exit code `0` is success; `2` is a usage error (missing Store, missing Tag, bad flag); `1` is a
  failure of the work itself (nothing could be fetched, `gcloud` failed).

The Store's files, the frontmatter fields and the CSVs are described in
[references/store.md](references/store.md). Read it before opening a Version by hand or
reasoning about `authority`.

## How to work with it

1. Need a page? `lorekeep get <url>` and read the file at the path it prints. Do not fetch the
   page yourself, and do not paste its text into the Store.
2. Need a fact? `lorekeep search '<words>'` first; open the file at the `file:line` it prints.
   Use `--exact` for an identifier such as `cache_control`.
3. Cite the Version's `url`, and trust it as far as its `authority` says: `primary` and
   `official` can be cited; `third-party` is context; `generated` (research pasted by the owner)
   is never cited.
4. A warning that a host is in no host table means the page is `third-party`: do not cite it, and
   tell the owner the host may need a rule in `lorekeep.toml`.

## `lorekeep get`

`lorekeep get URL [--tag TAG] [--max-age DAYS | --fresh] [--json] [--store DIR]`

Returns a Markdown Version of the page at `URL`, fetching it only when needed, and tags it with
the Run's Tag. `URL` may be the page's address or its Twin's (`….md`, `?accept=text/markdown`);
both find the same Version. A redirect or a canonical URL stores the page under its final
address, and the old address finds it too.

- `--tag TAG` — the Run's Tag, exactly one (default: `$LOREKEEP_TAG`).
- `--max-age DAYS` — recheck a stored Version older than this many days (default: the Project's
  `freshness_days`, 30 unless `lorekeep.toml` says otherwise).
- `--fresh` — ask the publisher now whatever the Version's age (`--max-age 0`). Use it only when
  a fact is in dispute.
- `--json` — print one JSON object instead of the path.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

How it fetches, in order: the publisher's Markdown **Twin** when the host has a rule for one
(`….md` on Fern and Mintlify sites, `?accept=text/markdown`, a raw file; a GitHub `blob/` page is
read from its raw file and stored under the `blob` address, code fenced by its extension); the
static HTML, main content extracted, links made absolute, redirects and meta-refresh followed; a
PDF converted to Markdown; JSON, YAML, plain text, CSV or XML kept verbatim in one fence; a
browser, last, when the host refuses a plain client or renders on the
client. A stored Version younger than the window is returned without any request (`fresh`). An
older one is asked about with a conditional request; a page that is gone (`404`/`410`) or a host
that fails returns the stored Version with a warning. A Version rendered by the browser is never
rechecked by `get` (`skipped`, with a warning).

Text output: the Version's absolute path on the last line of stdout, nothing else.

```text
/…/store/platform.claude.com--docs-en-build-with-claude-prompt-caching--f264876f.md
```

`--json` output: one object, and nothing follows it.

```json
{"path": "/…/store/platform.claude.com--docs-en-build-with-claude-prompt-caching--f264876f.md",
 "url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
 "requested_url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
 "sha256": "f264876f…", "fetched_at": "2026-10-17T14:40:37Z", "converter": "md-twin",
 "publisher": "anthropic", "authority": "primary", "verified_at": "2026-10-17T14:40:37Z",
 "outcome": "stored"}
```

`outcome` is one of `stored` (first fetch), `fresh` (returned without any request), `unchanged`,
`changed` (a new Version was stored and is the one returned), `gone`, `error` (the stored Version
is returned; see the warning), or `skipped` (a browser-rendered Version returned unasked).
`verified_at` is when the publisher last confirmed the text unchanged, or `fetched_at` when it
never has. With nothing stored and nothing fetchable, `get` prints an error and exits `1`.

## `lorekeep add`

`lorekeep add FILE --title TITLE [--publisher NAME] [--authority A] [--fetched-at WHEN] [--tag TAG] [--json] [--store DIR]`

Stores a Markdown or text file the owner provides (research pasted from a chat, a note) as a
Version with `url: owner:<slug of the title>`, `origin: owner`, `converter: owner`. It is
searchable like any page and is never cited unless `--authority` says otherwise.

- `--title TITLE` — required; the Source's title, whose slug names it.
- `--publisher NAME` — who produced the text, such as `claude` (default: `owner`).
- `--authority A` — `primary`, `official`, `third-party` or `generated` (default: `generated`).
- `--fetched-at WHEN` — an ISO 8601 time for `fetched_at` (default: the file's modification time).
- `--tag TAG` — the Run's Tag, exactly one (default: `$LOREKEEP_TAG`).
- `--json` — print one JSON object instead of the path.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: the new Version's path. `--json` output: the same object as `get --json`, with
`outcome: "stored"`, `converter: "owner"` and `url: "owner:<slug>"`.

## `lorekeep search`

`lorekeep search QUERY [--tag TAG]… [--all] [--publisher NAME] [--authority A] [--exact] [--limit N] [--json] [--store DIR]`

Searches the Sections (the text under each heading) of the latest Version of every Source in
scope, ranked by BM25. Word forms match (`caching` finds `cached`). The scope is the Run's Tag;
without one, the whole Store.

- `--tag TAG` — limit the scope to this Tag; repeat it for several (default: `$LOREKEEP_TAG`,
  else everything).
- `--all` — search every Tag.
- `--publisher NAME` — only Sources of this publisher (`anthropic`, `aws`, …).
- `--authority A` — only Sources of this authority (`primary`, `official`, `third-party`,
  `generated`).
- `--exact` — a case-sensitive substring match on the text as written, not a word search; use it
  for identifiers (`cache_control`, `max_tokens`).
- `--limit N` — how many results (default: 5).
- `--json` — print one JSON object instead of lines.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: one line per result, `file:line | heading path | snippet`, with the matched words in
`[brackets]`; open the file at that line. The last line counts the Sources the same query matches
outside the scope; it is omitted when the scope is already everything. A `+N` above zero means
another Run's Sources answer too: widen with `--all` or `--tag`.

```text
/…/store/platform.claude.com--docs-en-build-with-claude-prompt-caching--f264876f.md:690 | Caching strategies and considerations > Tracking cache performance | Monitor [cache] performance using these API response fields…
+2 matches under other tags (--all)
```

`--json` output: one object; `other_tags` is `0` when the scope is everything.

```json
{"results": [{"file": "/…/store/platform.claude.com--…--f264876f.md", "line": 690,
              "heading": "Caching strategies and considerations > Tracking cache performance",
              "snippet": "Monitor [cache] performance…",
              "url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
              "tag": ["anthropic"]}],
 "other_tags": 2}
```

When the Index is missing or out of date, `search` rebuilds it first and says so on stderr.

## `lorekeep status`

`lorekeep status [--json] [--store DIR]`

Summarises the Store: Versions, Sources, Tags, the oldest and newest fetch, Recheck results, hosts
matched by no rule, its size, and the Project's settings.

- `--json` — print one JSON object instead of lines.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output:

```text
Store: /…/store
2 Versions of 2 Sources
Tags: anthropic 2
Oldest fetched_at: 2026-10-17T14:40:37Z
Newest fetched_at: 2026-10-17T14:40:37Z
Rechecks: 0 unchanged, 0 changed, 0 gone, 0 error
Unknown hosts: none
Size on disk: 521577 bytes
Bucket: none
Freshness window: 30 days
Host rules (8):
  platform.claude.com/  anthropic  primary  twin=md-suffix
  …
```

A host rule from the Project's `lorekeep.toml` is marked `(lorekeep.toml)`.

`--json` output (settings and host rules are not part of it):

```json
{"versions": 2, "sources": 2, "tags": {"anthropic": 2},
 "oldest_fetched_at": "2026-10-17T14:40:37Z", "newest_fetched_at": "2026-10-17T14:40:37Z",
 "checks": {"unchanged": 0, "changed": 0, "gone": 0, "error": 0},
 "unknown_hosts": [], "bytes": 521577}
```

## `lorekeep index`

`lorekeep index [--store DIR]`

Rebuilds the Index (`sources.db`) from the Store's files. You rarely need it: every command that
reads the Index rebuilds it when it is stale, and every write keeps it current.

- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: one line, `Indexed N Versions, N Sections, N Tag rows, N Rechecks, N aliases,
N Citations into /…/store/sources.db`.

## `lorekeep recheck`

`lorekeep recheck [--tag TAG]… [--publisher NAME] [--prefix URL] [--citations] [--dry-run] [--store DIR]`

Asks the publisher of every Source in scope whether it changed since its latest Version — a
conditional request when the server supports one — records every answer in `checks.csv` and stores
a changed page as a new Version beside the old. `owner:` Sources and browser-rendered Versions
are counted as `skipped` and asked nothing. Usually the owner's job, not a Run's.

- `--tag TAG` — limit the scope to this Tag; repeat it for several (default: `$LOREKEEP_TAG`,
  else everything).
- `--publisher NAME` — only Sources of this publisher.
- `--prefix URL` — only Sources whose `url` starts with this.
- `--citations` — ask nothing; list the finished works whose cited Sources have a newer Version
  than the one the work was written from (from the Project's `citations.csv`).
- `--dry-run` — list what would be asked, ask nothing.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: one line per Source, `<result> <url>`, then a summary.

```text
unchanged https://platform.claude.com/docs/en/build-with-claude/prompt-caching
skipped owner:caching-notes
Rechecked 2 Sources: 1 unchanged, 0 changed, 0 gone, 0 error, 1 skipped
```

`--dry-run` prints `would ask <address>` or `skipped <url>: <reason>` per Source, then
`Would ask N Sources; N skipped`. `--citations` prints one line per work to revisit,
`<work_id>, <url>, <old sha8> → <new sha8>`, and nothing when there is none.

## `lorekeep tag add`

`lorekeep tag add TAG URL [--store DIR]` or `lorekeep tag add TAG --prefix URL [--store DIR]`

Adds a Tag to a stored Source, or to every Source whose `url` starts with a prefix — for Sources
migrated or added by hand. Owner's tool; a Run's Tags come from `get` and `add`.

- `--prefix URL` — tag every Source whose `url` starts with this, instead of one `URL`.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: `tagged <url>` for each Source that gained the Tag, then
`Tagged N Sources <tag>; N already carried it`. No Source matching is an error.

## `lorekeep backup`

`lorekeep backup [--dry-run] [--store DIR]`

Copies the Store to the Project's bucket (`bucket` in `lorekeep.toml`) with `gcloud storage`,
never deleting there and never replacing a Version or an Original already there; the growing
files (`tags.csv`, `checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`,
`lorekeep.toml`) are copied every time and the bucket's versioning keeps their history.
Regenerates `datapackage.json` first. Owner's tool.

- `--dry-run` — `rsync` in dry-run mode; `datapackage.json` is still regenerated; the `cp` of
  the growing files is listed, not run.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: what `gcloud` prints; with `--dry-run`, also
`Would copy <file> to gs://<bucket>/ (replacing; the bucket keeps the old one)` per growing file.

## `lorekeep restore`

`lorekeep restore NAME [--generation N] [--store DIR]`

Fetches one file of the Store back from the bucket, refusing to overwrite a local file. The next
command that reads the Index picks it up. Owner's tool.

- `--generation N` — an older generation of the object, as the bucket's versioning numbers it.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: the restored file's path.

## `lorekeep skill`

`lorekeep skill [--install REPO [--force]]`

Prints this skill. Needs no Store and no Tag.

- `--install REPO` — copy the skill folder into `REPO/.agents/skills/lorekeep/`, then remind that
  the repository's skill lock, if it keeps one, needs the new hash. Refuses when that folder
  exists.
- `--force` — with `--install`, replace an installed copy.

Text output: this file; with `--install`, the installed folder's path and the reminder.
