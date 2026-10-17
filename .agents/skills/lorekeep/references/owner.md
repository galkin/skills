# The owner's commands and host rules

These commands keep a Store over time; a Run never calls them. Every one takes `--store DIR`
(default: `$LOREKEEP_STORE`). The Store's files are described in [store.md](store.md).

## `lorekeep recheck`

`lorekeep recheck [--tag TAG]… [--publisher NAME] [--prefix URL] [--citations] [--dry-run] [--store DIR]`

Asks the publisher of every Source in scope whether it changed since its Latest Version (a
conditional request when the server supports one), records every answer in `checks.csv`, and
stores a changed page as a new Version beside the old. `owner:` Sources and browser-rendered
Versions are `skipped`.

- `--tag TAG` — limit the scope to this Tag; repeat it for several (default: `$LOREKEEP_TAG`,
  else everything).
- `--publisher NAME` — only Sources of this publisher.
- `--prefix URL` — only Sources whose `url` starts with this.
- `--citations` — ask nothing; list the works whose cited Sources have a newer Version than the
  one the work was written from (`citations.csv`, see [store.md](store.md#citationscsv)).
- `--dry-run` — list what would be asked, ask nothing.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

A Recheck rereads a Version with the converter that stored it: a page stored through
`trafilatura` is reread, and any new Version of it made, through `trafilatura` even after a host
rule gives it a Twin. A new Twin rule takes effect only for a Source first fetched after it: fetch
the pages into a new Store.

```text
$ lorekeep recheck
changed https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents
Rechecked 1 Source: 0 unchanged, 1 changed, 0 gone, 0 error, 0 skipped
$ lorekeep recheck --citations
guides/cca/subagents, https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents, ecd013b9 → 9c9fc26a
```

`--dry-run` prints `would ask <address>` or `skipped <url>: <reason>` per Source, then
`Would ask N Sources; N skipped`. `--citations` prints one line per work to revisit
(`<work_id>, <url>, <old sha8> → <new sha8>`), nothing when there is none, and a warning per cited
`url` with no Version.

## `lorekeep tag add`

`lorekeep tag add TAG URL [--store DIR]` or `lorekeep tag add TAG --prefix URL [--store DIR]`

Adds a Tag to one stored Source, or to every Source whose `url` starts with a prefix, for Sources
migrated or added by hand. No Source matching is an error.

- `--prefix URL` — tag every Source whose `url` starts with this, instead of one `URL`.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
tagged https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/jailbreak-protection
Tagged 1 Source guardrails; 0 already carried it
```

## `lorekeep backup`

`lorekeep backup [--dry-run] [--store DIR]`

Copies the Store to the Project's bucket (`bucket` in `lorekeep.toml`) with `gcloud storage`,
never deleting there and never replacing a Version or an Original; the growing files (`tags.csv`,
`checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`, `lorekeep.toml`) are copied
every time and the bucket's versioning keeps their history. Regenerates `datapackage.json` first.
`.cache/` is never backed up, nor is the Index: the Readings in it are rebuilt from the Versions
and the rules by the next `get`, `search` or `read`, so a restored Store needs nothing more.

- `--dry-run` — `rsync` in dry-run mode; `datapackage.json` is still regenerated; the `cp` of the
  growing files is listed, not run.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

Output: what `gcloud` prints; with `--dry-run`, also
`Would copy <file> to gs://<bucket>/ (replacing; the bucket keeps the old one)` per growing file.

## `lorekeep restore`

`lorekeep restore NAME [--generation N] [--store DIR]`

Fetches one file of the Store back from the bucket, refusing to overwrite a local file; prints its
path. The next command that reads the Index picks it up.

- `--generation N` — an older generation of the object, as the bucket's versioning numbers it.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

## `lorekeep index`

`lorekeep index [--store DIR]`

Rebuilds the Index (`sources.db`) from the files, first building the Readings that are missing
or stale. Rarely needed: every reader rebuilds a stale Index (a change of the `[[readings]]` rules
makes it stale), every write keeps it current.

- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
Indexed 2 Versions, 26 Sections, 1 Tag row, 1 Recheck, 0 aliases, 1 Citation into /…/store/sources.db
```

## `lorekeep read`

`lorekeep read [--prefix URL] [--force] [--store DIR]`

Builds the Reading of every Version (owner-added ones aside) whose Reading is missing or stale:
the Version after the `[[readings]]` rules that apply to it, in `.cache/readings/<stem>.md` (see
[store.md](store.md#readings)). Rarely needed: `get` builds the Reading it returns, `recheck` the
Reading of a changed page, and `search` every missing or stale one when it rebuilds the Index. A
Version no rule changes has no Reading. A rule held back by the over-removal guard is named on stderr as
`lorekeep: warning: <url>: rule <name> removed N lines (accepted at M lines)` (a block operation)
or `… removed N% (accepted at M%)` (`drop_lines`).

- `--prefix URL` — only Sources whose `url` starts with this.
- `--force` — rebuild every Reading in scope, current or not.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
Built 3 Readings, 41 current
```

## `lorekeep rules sample`

`lorekeep rules sample PREFIX [--sample N] [--store DIR]`

Prints the paths of Versions under `PREFIX` (`host/path`, as a rule's `prefix`), the newest of each
Source: the shortest, the longest, then the others spread between them by length. They are what a
proposer of reading rules reads (below).

- `--sample N` — how many (default: 5).
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

## `lorekeep rules check`

`lorekeep rules check FILE [--store DIR]`

Measures each candidate `[[readings]]` table of `FILE` on its own on every Version it reaches, and
writes nothing. Per candidate: the lines removed (headings inserted, titles cut) in total and per
Version, three of them, and `pass` or `fail: <reason>`. The limits: `drop_lines` removes at most
30% of any Version's lines; a leading block ends before the first heading and no line after that
heading matches (a trailing block mirrors it after the last heading), with no limit on its size; no
rule removes a fence or table line; a candidate must be the grammar, carry no `accepted` or
`removes`, and change some Version.

- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
[1] docs.nvidia.com/ drop_leading = "llms\\.txt|For clean Markdown|/_mcp/server"
    over 5 Versions: 91 lines removed (per Version min 12, median 15, max 26)
    | > This page is for version Latest (v1.5.1) (default).
    | > - v0.7.0: https://docs.nvidia.com/dynamo/v-0-7-0/llms.txt
    | > For AI client integration (Claude Code, Cursor, etc.), connect to the MCP server at https://docs.…
    pass
[2] docs.nvidia.com/ drop_lines = "^# "
    over 5 Versions: 5 lines removed (per Version min 1, median 1, max 1), at most 3% of a Version
    | # Router Guide
    | # Guardrail Types
    | # Build Verifiers
    fail: matches a fence line, docs.nvidia.com--dynamo-latest-kubernetes-model-deployment-model-loading-fast-model-loading--eb7e8d5d.md:134
Checked 2 candidates: 1 pass, 1 fail
```

## `lorekeep rules accept`

`lorekeep rules accept FILE [--all] [--store DIR]`

Runs `rules check`, writes the passing candidates into the Store's `lorekeep.toml` with `accepted`
(today) and `removes` (the most one Version lost), prints `Accepted N rules, M failed`, then builds
the Readings they reach (`Built N Readings, M current`). A rule with the same `prefix` or `engine`
and operation as a `[[readings]]` table already there replaces that table where it stands; any
other is appended at the end; every other line of the file stays as written, comments included.
Of two candidates with the same operation, the later wins.

- `--all` — also accept the failing ones (your override); a candidate that is not the grammar
  never is.
- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

## Proposing reading rules

lorekeep calls no model. Rules come from this cycle, run by the orchestrator when a Run reports a
Reading with chrome left in it, or a new host lands in the Store:

1. `lorekeep rules sample PREFIX` — the Versions to read.
2. Launch a subagent on the cheapest model available (the Haiku tier) through Orca orchestration,
   as any worker, with this brief:
   - read the printed paths, and propose rules that drop what is not the page's content (banners,
     chrome, a site suffix in the title) or insert a heading before each article of a law;
   - the grammar: `[[readings]]` tables, each with `prefix = "PREFIX"` and exactly one operation —
     `drop_leading` (the lines up to the last match before the first heading), `drop_trailing`
     (from the first match after the last heading), `drop_lines` (every matching line),
     `strip_title_suffix` (the match ending the first heading), `heading_before` with `level`
     (a heading made of each matching line); every value a Python regular expression;
   - the limits of `rules check` above;
   - the answer: one TOML file of `[[readings]]` candidates and nothing else — no `accepted`, no
     `removes`, no prose; several candidates for one operation are fine.
3. `lorekeep rules check FILE` — read the report; a `fail` names the Version and line.
4. `lorekeep rules accept FILE` — the passing rules go into `lorekeep.toml` and the Readings under
   them are rebuilt; the next `search` reindexes them.

Engine rules (Fern, EUR-Lex, Microsoft Learn) found this way belong in lorekeep's own
`readings.toml`: file them as a lorekeep issue.

## `lorekeep skill`

`lorekeep skill [--install REPO [--force]]`

Prints `SKILL.md`. Needs no Store and no Tag.

- `--install REPO` — copy the skill folder into `REPO/.agents/skills/lorekeep/` and remind that
  the repository's skill lock, if any, needs the new hash; refuses when the folder exists.
- `--force` — with `--install`, replace an installed copy.

## `lorekeep.toml`

The Store's `lorekeep.toml` holds `bucket`, `freshness_days` (default 30) and `[[hosts]]` rules
over the package's default table (`lorekeep status --rules` prints the merged table). A rule
matches `host/path` by prefix and the longest matching prefix wins. Its keys:

- `prefix`, `publisher`, `authority` — required.
- `twin` — `md-suffix`, `accept-header`, `raw` or `github-raw` (see [store.md](store.md#twins)).
- `page_suffix` — with `md-suffix`, the page's suffix the Twin replaces (`.html`).
- `browser` — `true` sends the first fetch of every page under the prefix straight to the browser
  (Crawl4AI, the `lorekeep[browser]` extra), past the Twin and the static page: for a host whose
  pages build themselves in the browser (`build.nvidia.com`). Without it the browser is still the
  last step, for a page the plain request could not read (`thin content`, a `403`). The browser
  retries on its own, with no setting: it renders once waiting for the network to go quiet
  (`networkidle`), again with three more seconds when the Markdown is thin, and a third time
  waiting up to 15 seconds for the page's main text to grow past the thin threshold. A page still
  thin after the third render is the error `the browser rendered a shell` and nothing is stored.
  A browser-rendered Version is never rechecked.
- `cut` — a list of CSS selectors removed from a page the browser rendered under the prefix
  before conversion (`cut = ["nav", ".cookie-banner"]`); the Original is the rendered document
  before the cut. It changes nothing for a static page or a Twin.

A Project rule with the same prefix as a default rule replaces it, and a Project rule with a longer
prefix wins over it. A rule that names neither `twin` nor `page_suffix` inherits both from the
longest shorter prefix that names a `twin` — `github.com/<org>/` with only `publisher` and
`authority` keeps `github-raw`, while `docs.langchain.com/` replaced without `twin` has no Twin —
and `status --rules` marks them `(inherited)`; `browser` and `cut` are never inherited. A rule
changed after pages were stored does not reach them on Recheck (see `recheck` above).

`[[readings]]` rules make Readings (see [store.md](store.md#readings)), over the package's
defaults (`readings.toml`); a Project rule with the same `prefix` or `engine` and operation
replaces a default. Each rule has `prefix` (`host/path`, longest wins) or `engine` (`fern`,
`mintlify`, `sphinx`, `eur-lex`, `pdf`), exactly one operation — `drop_leading`,
`drop_trailing`, `drop_lines`, `strip_title_suffix`, or `heading_before` with `level` — whose value
is a regular expression, and `accepted` (a date) and `removes` (the most it removed from one
Version when accepted, with its unit: `"26 lines"` for `drop_leading` and `drop_trailing`, `"4%"`
of the Version's lines for `drop_lines`, none for the other two; a rule that removes more than
twice that from a Version is not applied to it). `rules accept` writes both. For example:

```toml
[[readings]]
prefix = "docs.nvidia.com/"
drop_leading = "llms\\.txt|For clean Markdown|/_mcp/server"
accepted = 2026-10-17
removes = "26 lines"
```

A law or standard is `primary` where its issuer publishes the text, its official journal:
EUR-Lex for EU law, the Federal Register, nist.gov for NIST. An institution's reproduction of it
(the Commission's AI Act Service Desk) is `official`, and a Run cites the journal; set a rule's
`authority` that way, since the skill tells a Run to report a Version that says otherwise.

Pages a Run reports to you, and what fixes them: an unknown host or a mislabelled `authority` —
a `[[hosts]]` rule; `thin content` — `uv tool install --editable '.[browser]'` from the lorekeep
checkout (the README's Install section has the Chromium step); `unsupported media type`,
`could not convert`, missing code blocks or tables — a lorekeep issue.
