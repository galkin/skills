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

Rebuilds the Index (`sources.db`) from the files. Rarely needed: every reader rebuilds a stale
Index, every write keeps it current.

- `--store DIR` — the Store folder (default: `$LOREKEEP_STORE`).

```text
Indexed 2 Versions, 26 Sections, 1 Tag row, 1 Recheck, 0 aliases, 1 Citation into /…/store/sources.db
```

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
  last step, for a page the plain request could not read (`thin content`, a `403`). A
  browser-rendered Version is never rechecked.
- `cut` — a list of CSS selectors removed from a page the browser rendered under the prefix
  before conversion (`cut = ["nav", ".cookie-banner"]`); the Original is the rendered document
  before the cut. It changes nothing for a static page or a Twin.

A Project rule with the same prefix as a default rule replaces it, and a Project rule with a longer
prefix wins over it; either way nothing is inherited, so a rule that omits `twin` and
`page_suffix` has no Twin. A rule that sets `publisher` and `authority` for a GitHub organisation
must repeat `twin = "github-raw"`, or its `blob/` pages are converted as HTML pages:

```toml
[[hosts]]
prefix = "github.com/NVIDIA-AI-Blueprints/"
publisher = "nvidia"
authority = "primary"
twin = "github-raw"
```

The same holds for `docs.langchain.com/` (`twin = "md-suffix"`) and every other default rule
`status --rules` shows with a `twin=`. A rule changed after pages were stored does not reach them
on Recheck (see `recheck` above).

A law or standard is `primary` where its issuer publishes the text, its official journal:
EUR-Lex for EU law, the Federal Register, nist.gov for NIST. An institution's reproduction of it
(the Commission's AI Act Service Desk) is `official`, and a Run cites the journal; set a rule's
`authority` that way, since the skill tells a Run to report a Version that says otherwise.

Pages a Run reports to you, and what fixes them: an unknown host or a mislabelled `authority` —
a `[[hosts]]` rule; `thin content` — `uv tool install --editable '.[browser]'` from the lorekeep
checkout (the README's Install section has the Chromium step); `unsupported media type`,
`could not convert`, missing code blocks or tables — a lorekeep issue.
