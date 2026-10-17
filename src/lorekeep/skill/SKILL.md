---
name: lorekeep
description: >
  Use lorekeep to fetch, keep and search the Sources a Run reads: vendor documentation,
  specifications, third-party pages, PDFs, files. `lorekeep get <url>` returns the path of a
  Markdown Version with its Provenance; `lorekeep search <query>` answers with `file:line` from the
  Project's Store. Use it instead of fetching a page yourself, whenever a brief names lorekeep,
  LOREKEEP_STORE or LOREKEEP_TAG.
---

# lorekeep

lorekeep keeps one **Store** per Project: a flat folder of Markdown **Versions** of **Sources**,
each with its Provenance in frontmatter and its **Original** beside it. It fetches, converts,
records and searches; it holds no LLM. You decide what to read and cite. The Store's files and
fields: [references/store.md](references/store.md). The owner's commands (`recheck`, `tag add`,
`backup`, `restore`, `index`, `skill`, host rules) are in [references/owner.md](references/owner.md)
and are not a Run's to call.

## Before you start

- Run `lorekeep` from the `PATH` the orchestrator gives you; it is installed already, so
  install nothing. `lorekeep --version` names the version.
- `LOREKEEP_STORE` names the Store (or `--store DIR`). A missing folder is an error; lorekeep never
  creates one.
- `LOREKEEP_TAG` names the **Tag** (or `--tag TAG`): one per guide, shared by every worker of that
  guide, set by the brief and never chosen by you. `get` and `add` refuse to run without it.
- Every flag follows its subcommand: `lorekeep get --json URL`, never `lorekeep --json get URL`.
- stdout carries only the result; stderr carries lines starting `lorekeep: error:`,
  `lorekeep: warning:` or `lorekeep: note:`.
- Exit `0` is success, `1` a failure of the work (nothing could be fetched), `2` a usage error
  (no Store, no Tag, a bad flag): fix the command.
- Write to the Store only through `get` and `add`; never edit its files or `lorekeep.toml`.

## How a Run works

1. Need a page: `lorekeep get --json <url>`, then read the file at `path`.
2. Append every `get --json` line to your own log, and for an exit `1` the URL and the error
   line; the Tag says only that the guide read a Source, so your log is the record of what you
   read and what failed. Keep it where your brief says, else in your final message.
3. Need a fact: `lorekeep search '<words>'` first, and open the file at the `file:line` it prints.
4. Cite the Version's `url` as far as its `authority` allows (below).
5. Put everything this skill says to report in your final report to the owner, with its URL.

Parallel `get`s against one Store are safe: writers take turns on a lock, and two workers fetching
one page get one Version.

## What to cite

- The returned `url` may differ from the address you asked (trailing slash, fragment, redirect,
  Twin reduction); it is the one to cite.
- `requested_url` in the JSON is the address you asked, normalised; compare it with `url`.
- Fragments (`#section`) are dropped from both; keep the fragment yourself and append it to `url`
  when you cite a section.
- `.md` and `?accept=text/markdown` addresses are Twins only under a host rule; elsewhere they are
  fetched as pages of their own, so ask for the page's address.
- A canonical link the page declares never becomes `url`; it is recorded as `canonical`, with a
  warning, and changes nothing for you.
- `authority`: `primary` and `official` are cited; `third-party` is context; `generated` (research
  the owner added) is never cited.
- The `authority` of a law or standard published by its issuer (an EU regulation on EUR-Lex, a NIST
  publication on nist.gov) is `primary`, whatever its Version says; report a different value.
- A `third-party` page the guide treats as primary (a vendor's repository under the `github.com/`
  catch-all) is reported to the owner, who may add a host rule; until then it is context.

## stderr lines and what to do

| Line contains                                       | Do                                                           |
| --------------------------------------------------- | ------------------------------------------------------------ |
| `<host> is in no host table; stored as third-party` | report the host to the owner; the page is context            |
| `declares another page as canonical`                | nothing; cite `url`                                          |
| `N code blocks / M tables of the page are missing`  | report it; the Version is partial, its Original whole        |
| `returning the stored Version`                      | use it; the publisher could not be asked or dropped the page |
| `the Index was missing or stale and was rebuilt`    | nothing                                                      |

On exit `1` nothing was stored:

- Retry once, only when the error line names `ReadTimeout`, `ConnectError` or a `5xx` status
  (`answered 503`).
- Otherwise, or when the retry fails too, report the URL and the error line to the owner and move
  on: never fetch the page another way (`curl`, a web tool, a browser) and never `add` a page.
- A `thin content` error means the page needs the browser: the owner installs `lorekeep[browser]`.
- `unsupported media type` and `could not convert` errors are the owner's to fix.

```text
lorekeep: error: nothing stored for https://example.test/slow: the host rule names no Twin; https://example.test/slow failed (ReadTimeout)
lorekeep: error: nothing stored for https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard: the host rule names no Twin; thin content: https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard converted to 290 characters of a page of 8309; this page needs a browser and Crawl4AI is not installed: install the extra lorekeep[browser] (uv sync --extra browser)
```

## `lorekeep get`

`lorekeep get URL [--tag TAG] [--max-age DAYS | --fresh] [--json] [--store DIR]`

Returns a Version of the page at `URL`, fetching only when the Store has none or it is older than
the freshness window, and adds the Tag to it. lorekeep reads, in order: the publisher's Markdown
**Twin** under a host rule (a GitHub `blob/` page from its raw file, code fenced by extension); the
static HTML, main content extracted; a PDF; JSON, YAML, plain text, CSV or XML verbatim in one
fence; the browser, last. A PDF Version (`converter` `markitdown …`) may run words together and
lack headings: read it rather than trusting `search` to find a phrase in it.

- `--tag TAG` — the Run's Tag, exactly one (default: `$LOREKEEP_TAG`).
- `--max-age DAYS` — recheck a stored Version older than this (default: the Project's
  `freshness_days`, 30).
- `--fresh` — ask the publisher now (`--max-age 0`); only when a fact is in dispute.
- `--json` — print one JSON object instead of the path.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Text output: the Version's absolute path, one line. `--json` output, here for an address that
redirected to another host:

```text
$ lorekeep get --json https://v3.helm.sh/docs/helm/helm_rollback/
lorekeep: warning: helm.sh is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule
```

```json
{"path": "/…/store/helm.sh--docs-helm-helm_rollback--baae9b0a.md", "url": "https://helm.sh/docs/helm/helm_rollback", "requested_url": "https://v3.helm.sh/docs/helm/helm_rollback", "sha256": "baae9b0a65857f5fcd96600fca791315f7e83a745368d32d1885fec8891e1312", "fetched_at": "2026-10-17T17:16:51Z", "converter": "trafilatura 2.3.1", "publisher": "helm.sh", "authority": "third-party", "verified_at": "2026-10-17T17:16:51Z", "outcome": "stored"}
```

`outcome` is `stored` (first fetch), `fresh` (returned without a request), `unchanged`, `changed`
(a new Version, the one returned), `gone` or `error` (the stored Version, with a warning), or
`skipped` (a browser-rendered Version, never rechecked). `verified_at` is when the publisher last
confirmed the text, else `fetched_at`.

## `lorekeep add`

`lorekeep add FILE --title TITLE [--publisher NAME] [--authority A] [--fetched-at WHEN] [--tag TAG] [--json] [--store DIR]`

Stores a Markdown or text file your brief hands you (research pasted from a chat, a note) as a
Version with `url` `owner:<slug of the title>`, searchable like any page. Never a fetched page.

- `--title TITLE` — required; its slug names the Source.
- `--publisher NAME` — who produced the text, such as `claude` (default: `owner`).
- `--authority A` — `primary`, `official`, `third-party` or `generated` (default: `generated`).
- `--fetched-at WHEN` — ISO 8601 time for `fetched_at` (default: the file's modification time).
- `--tag TAG` — the Run's Tag, exactly one (default: `$LOREKEEP_TAG`).
- `--json` — print one JSON object instead of the path.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

`--json` output (`outcome` is `unchanged` when the same text was added before):

```json
{"path": "/…/store/owner--guardrail-latency-research--83067bf1.md", "url": "owner:guardrail-latency-research", "requested_url": "owner:guardrail-latency-research", "sha256": "83067bf10e219211e8062cf9d11a8f07d3f39ad768ed27d994a54ba46c3e7265", "fetched_at": "2026-10-17T17:16:52Z", "converter": "owner", "publisher": "claude", "authority": "generated", "verified_at": "2026-10-17T17:16:52Z", "outcome": "stored"}
```

## `lorekeep search`

`lorekeep search QUERY [--tag TAG]… [--all] [--publisher NAME] [--authority A] [--exact] [--limit N] [--json] [--store DIR]`

Searches the Sections (the text under each heading) of the Latest Version of every Source in scope,
ranked by BM25; word forms match (`caching` finds `cached`). The scope is the Run's Tag, else the
whole Store.

- `--tag TAG` — limit the scope to this Tag; repeat it for several (default: `$LOREKEEP_TAG`,
  else everything).
- `--all` — search every Tag.
- `--publisher NAME` — only Sources of this publisher.
- `--authority A` — only Sources of this authority.
- `--exact` — case-sensitive substring of the text as written, for identifiers
  (`cache_control`); `\_` and `\*` in the text match `_` and `*`.
- `--limit N` — how many results (default: 5).
- `--json` — print one JSON object instead of lines.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

`search` takes `-- '<query>'` for a query starting with `-`; flags may stand before or after it:
`lorekeep search --exact -- '--enable-auto-tool-choice'`.

Text output: one line per result, `file:line | heading path | snippet`, matched words in
`[brackets]`. `file:line` is the matching line: open the file there. `(top)` is text before the
first heading. No result prints `no matches`. A last line `+N matches under other tags (--all)`
means other guides' Sources answer too; widen with `--all` or `--tag`.

```text
$ lorekeep search --exact length_per_perplexity_threshold --limit 1
/…/store/docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-jailbreak-protection--96543394.md:60 | Jailbreak Protection > Jailbreak Detection | …server_endpoint: "http://0.0.0.0:1337/heuristics" [length_per_perplexity_threshold]: 89.79 prefix_suffix_perplexity_threshold: 1845.65 ``…
$ lorekeep search jailbreak --tag anthropic
no matches
+2 matches under other tags (--all)
```

`--json` output: `line` is the matching line, `heading_line` the Section's heading (`null`, with
`heading` `""`, before the first heading); `other_tags` is `0` when the scope is everything.

```json
{"results": [{"file": "/…/store/docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-jailbreak-protection--96543394.md", "line": 60, "heading_line": 35, "heading": "Jailbreak Protection > Jailbreak Detection", "snippet": "…server_endpoint: \"http://0.0.0.0:1337/heuristics\" [length_per_perplexity_threshold]: 89.79 prefix_suffix_perplexity_threshold: 1845.65 ``…", "url": "https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/jailbreak-protection", "tag": ["nvidia"]}], "other_tags": 0}
```

## `lorekeep status`

`lorekeep status [--rules] [--json] [--store DIR]`

Summarises the Store: Versions, Sources, Tags, oldest and newest fetch, Recheck results, hosts no
rule knows, size, and the Project's settings.

- `--rules` — also print the host rules, merged (a Project's own marked `(lorekeep.toml)`).
- `--json` — print one JSON object instead of lines (no settings, no rules).
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
Store: /…/store
5 Versions of 5 Sources
Tags: nvidia 5
Oldest fetched_at: 2026-10-17T17:16:51Z
Newest fetched_at: 2026-10-17T17:16:52Z
Rechecks: 0 unchanged, 0 changed, 0 gone, 0 error
Unknown hosts: genai.owasp.org, helm.sh
Size on disk: 133079 bytes
Bucket: none
Freshness window: 30 days
```

```json
{"versions": 5, "sources": 5, "tags": {"nvidia": 5}, "oldest_fetched_at": "2026-10-17T17:16:51Z", "newest_fetched_at": "2026-10-17T17:16:52Z", "checks": {"unchanged": 0, "changed": 0, "gone": 0, "error": 0}, "unknown_hosts": ["genai.owasp.org", "helm.sh"], "bytes": 133079}
```
