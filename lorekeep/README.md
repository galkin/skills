# lorekeep

lorekeep collects the Sources an LLM task reads — vendor documentation, specifications,
third-party pages, PDFs, research pasted from a chat — keeps each one as Markdown with its
Provenance, and makes a Project's Sources searchable and reusable across Runs. There is no LLM
inside it: it fetches, converts, records and searches.

One **Store** per Project holds every **Version** of every Source in one flat folder, each with
its Provenance in frontmatter and the **Original** bytes beside it. Files are written once and
never rewritten; the searchable **Index** is rebuilt from them whenever needed; `backup` copies
the Store to a private bucket without ever deleting or overwriting there. Words in bold are
defined in [`GLOSSARY.md`](GLOSSARY.md); the decisions behind them are in [`docs/adr/`](docs/adr/).

## Install

lorekeep is a Python package managed by [`uv`](https://docs.astral.sh/uv/); it is not on PyPI.
It lives in the `lorekeep/` folder of [galkin/skills](https://github.com/galkin/skills), and its
installable skill in `skills/lorekeep/`. It needs Python 3.13 (3.12's bundled SQLite fails the
Index's search; 3.14 has no wheel for a dependency of the PDF converter); `uv` picks or fetches
one.

A repository that runs agents vendors the skill, whose `bin/lorekeep` runs the released version
from its tag with `uvx`, so nothing is installed and every checkout shares one environment:

```sh
npx skills add galkin/skills    # choose lorekeep; then .agents/skills/lorekeep/bin/lorekeep …
```

For the command on your own `PATH`, from this folder:

```sh
uv tool install --editable .             # the `lorekeep` command, on your PATH
uv tool install --editable '.[browser]'  # the same, with the browser for pages that need one
```

The `browser` extra adds [Crawl4AI](https://docs.crawl4ai.com/), which `get` uses last, for a
host that refuses a plain client or renders its pages with JavaScript. Without it those pages
fail with a message saying so; everything else works. Crawl4AI drives Chromium through
Playwright, which needs the browser itself once:

```sh
"$(uv tool dir)/lorekeep/bin/playwright" install chromium
```

To work on lorekeep instead: `uv sync` (add `--extra browser` for the browser), then
`uv run lorekeep …`, `uv run pytest`, `uv run ruff check`, `uv run pyright`.

`uv tool uninstall lorekeep` removes the command; the Chromium download lives in Playwright's
cache (`~/Library/Caches/ms-playwright` on macOS) and is removed by hand.

## Settings

Two environment variables, both also given as flags of each subcommand:

- `LOREKEEP_STORE` (or `--store DIR`) — the Store folder. lorekeep never creates it: make the
  folder yourself once. Nothing in this repository names a Store.
- `LOREKEEP_TAG` (or `--tag TAG`) — the Run's **Tag**, named for the ecosystem the Run serves
  (`anthropic`, `aws`, …). `get` and `add` refuse to run without exactly one; `search` and
  `recheck` use it as their default scope and cover the whole Store without one, which is what you
  want from your own shell.

`--store` and `--tag` on a subcommand are a per-call override for a shell; a Run sets
`LOREKEEP_STORE` and `LOREKEEP_TAG` once in its environment and never passes them (ADR 0008).

```sh
export LOREKEEP_STORE=~/orca/sources/agentic-system.design
LOREKEEP_TAG=anthropic lorekeep get https://platform.claude.com/docs/en/build-with-claude/prompt-caching
lorekeep search 'cache breakpoints'
lorekeep status
```

### `lorekeep.toml`

The Project's settings live in `lorekeep.toml` at the root of the Store, so they are backed up
with it. Every top-level key is optional:

```toml
bucket = "agentic-system-design-sources"   # where `backup` copies the Store; required by backup/restore
freshness_days = 30                         # how old a Version may be before `get` asks again

[[hosts]]                                   # a host rule, as many as needed
prefix = "docs.example.com/api/"            # required: matched on host/path, longest prefix wins
publisher = "example"                       # required: who authored the pages
authority = "primary"                       # required: primary | official | third-party | generated
twin = "md-suffix"                          # md-suffix | accept-header | raw | github-raw; absent: inherited
page_suffix = ".html"                       # what md-suffix replaces; absent: .md is appended
browser = true                              # go straight to the browser on a first fetch
cut = ["nav", ".cookie-banner"]             # CSS selectors removed from a rendered page
```

`twin` says where the publisher serves the same page as Markdown — the **Twin**, which `get`
prefers to any conversion:

- `md-suffix` replaces `page_suffix` (or appends) with `.md` (Fern and Mintlify sites serve one);
  `text/markdown` is accepted, and `text/plain` when the body is not HTML.
- `accept-header` adds `?accept=text/markdown`.
- `raw` means the URL itself answers plain text.
- `github-raw` reads a `github.com/<owner>/<repo>/blob/<ref>/<path>` page from
  `raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>` and stores it under the `blob` address
  (`converter: raw-twin`): Markdown and `.txt` as published, any other file as `# <path>` and one
  fence named by its extension.

A Twin that answers `404` or anything but Markdown is skipped and the page itself is converted.
Files served as JSON, YAML, plain text, CSV or XML need no rule: they are stored verbatim in one
fence (`converter: verbatim`).

### The default host table

The package ships the hosts probed so far in
[`src/lorekeep/hosts.toml`](src/lorekeep/hosts.toml), in the same shape. A rule in
`lorekeep.toml` with the same `prefix` replaces the default one; any other rule is added beside
them. `lorekeep status --rules` prints the merged table, marking the Project's rules `(lorekeep.toml)`.
A rule that names neither `twin` nor `page_suffix` inherits both from the longest shorter prefix
of the merged table that names a `twin` (so `github.com/<org>/` with only `publisher` and
`authority` keeps `github-raw`; a rule replacing a default inherits from a shorter one, not from
the rule it replaces), marked `(inherited)` by `status --rules`; `browser` and `cut` are never
inherited.

| Prefix                             | Publisher   | Authority   | Twin                                          |
| ---------------------------------- | ----------- | ----------- | --------------------------------------------- |
| `platform.claude.com/`             | `anthropic` | primary     | `md-suffix`                                   |
| `docs.aws.amazon.com/`             | `aws`       | primary     | `md-suffix`, `.html` → `.md`                  |
| `skillbuilder.aws/`                | `aws`       | official    | — (`browser`; `cut` drops the cookie banner)  |
| `learn.microsoft.com/`             | `microsoft` | primary     | `accept-header`                               |
| `docs.nvidia.com/`                 | `nvidia`    | primary     | — (Sphinx and MkDocs sections serve no `.md`) |
| `docs.nvidia.com/cuvs/`            | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.nvidia.com/dynamo/`          | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.nvidia.com/nemo/curator/`    | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.nvidia.com/nemo/guardrails/` | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.nvidia.com/nemo/gym/`        | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.nvidia.com/openshell/`       | `nvidia`    | primary     | `md-suffix` (Fern)                            |
| `docs.langchain.com/`              | `langchain` | primary     | `md-suffix` (Mintlify)                        |
| `cloud.google.com/`                | `google`    | primary     | —                                             |
| `milvus.io/`                       | `milvus`    | primary     | —                                             |
| `claude.termidy.com/`              | `termidy`   | third-party | —                                             |
| `raw.githubusercontent.com/`       | `github`    | third-party | `raw`                                         |
| `github.com/`                      | `github`    | third-party | `github-raw`                                  |

A host matched by no rule is stored with `publisher = <host>` and `authority = third-party`, and
every `get` of it warns, so the table can be extended. A rule's `publisher` and `authority` reach
every stored Version at once: `get`, `search` and `status` judge a Version by the current rules,
while its frontmatter keeps what they said at fetch (`get --json` shows it as
`captured_authority` when they differ). Its `twin`, `browser` and `cut` say how a page is
obtained, so they apply to new fetches only: a Recheck rereads the page with the converter that
stored it, and a new Twin rule reaches only a Source first fetched after it — fetch the pages into
a new Store.

## The first Store

The first Project, `agentic-system.design`, uses:

| Setting          | Value                                                        |
| ---------------- | ------------------------------------------------------------ |
| `LOREKEEP_STORE` | `~/orca/sources/agentic-system.design/`                      |
| `bucket`         | `agentic-system-design-sources` (versioned, public access prevented) |
| `freshness_days` | `30` (the default)                                           |

```sh
mkdir -p ~/orca/sources/agentic-system.design
printf 'bucket = "agentic-system-design-sources"\n' > ~/orca/sources/agentic-system.design/lorekeep.toml
```

## For agents: the skill

`lorekeep skill` prints a skill ([`SKILL.md`](src/lorekeep/skill/SKILL.md)): what lorekeep is,
its settings and exit codes, and which reference each way of using it reads. A **Reader** searches
the Store and cites what it finds ([`references/reading.md`](src/lorekeep/skill/references/reading.md));
a **Collector** fills it for a guide or a section, then reports what failed
([`references/collecting.md`](src/lorekeep/skill/references/collecting.md)); the owner curates it
with `recheck`, `tag add`, `backup`, `restore`, `index`, `skill` and `[[hosts]]` rules
([`references/curating.md`](src/lorekeep/skill/references/curating.md)).
[`references/store.md`](src/lorekeep/skill/references/store.md) holds the Store's layout,
frontmatter, `--json` fields and `citations.csv`. It ships
inside the package, so it always matches the version. A release, from this folder:

```sh
# bump `version` in pyproject.toml, then:
uv lock && git add -A . && git commit -m "Release lorekeep <version>"
git tag -a lorekeep-v<version> -m "lorekeep <version>"   # annotated, so --follow-tags pushes it
uv run lorekeep skill --build ../skills/lorekeep         # bin/lorekeep pinned to the tag's commit
git add -A ../skills/lorekeep && git commit -m "Build the lorekeep <version> skill"
git push --follow-tags
```

A repository then updates its copy with `npx skills add galkin/skills` and records the new hash in
its skill lock (such as `skills-lock.json`).

## Backup and recovery

`lorekeep backup` copies the Store to `gs://<bucket>` with `gcloud storage`: an `rsync
--no-clobber` that never deletes and never replaces an object, then a `cp` of the six files that
grow (`tags.csv`, `checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`,
`lorekeep.toml`), whose history the bucket's versioning keeps. The Index, the lock file and
half-written files are left out. Both upload with `--gzip-in-flight-all`, compressed on the wire
only, because the Store's HTML and Markdown shrink about fivefold and the upload is the wait. Run `lorekeep backup --dry-run` first to see what it would do.
It needs an authenticated `gcloud` (`gcloud auth login`).

### Restore one deleted Version

A Version or an Original deleted from the Store is still in the bucket. Bring it back by name:

```sh
lorekeep restore platform.claude.com--docs-en-build-with-claude-prompt-caching--f264876f.md
```

`restore` refuses to overwrite a file that exists. The next `search`, `recheck`, `status` or
`index` notices the file and updates the Index; `get` finds it right away. A growing file restored
this way would be the bucket's latest copy; an older one is reached through its generation:

```sh
gcloud storage ls --all-versions gs://agentic-system-design-sources/checks.csv
mv "$LOREKEEP_STORE/checks.csv" "$LOREKEEP_STORE/checks.csv.broken"   # restore never overwrites
lorekeep restore checks.csv --generation 1760000000000000
```

### Bring a whole Store back onto an empty disk

The reverse `rsync` copies everything from the bucket into a new, empty Store folder; `index`
then rebuilds the Index, which is never backed up:

```sh
mkdir -p ~/orca/sources/agentic-system.design
gcloud storage rsync --recursive gs://agentic-system-design-sources ~/orca/sources/agentic-system.design
LOREKEEP_STORE=~/orca/sources/agentic-system.design lorekeep index
```

## Smoke test against the live network

The test suite never touches the network. One manual script checks lorekeep against the real
world: it fetches a Twin, a static page and, under a temporary `browser = true` rule, a page
through the browser into a temporary Store, prints their converters, and restores an older
generation of one object from the bucket with `restore --generation`. It writes nothing to the
bucket.

```sh
uv sync --extra browser
uv run python scripts/smoke.py --bucket agentic-system-design-sources
```
