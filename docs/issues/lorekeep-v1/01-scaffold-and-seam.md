# 01: Scaffold and the test seam

**What to build:** A developer can `uv sync`, run `lorekeep --help` and see every subcommand of the spec as a stub, and run `lorekeep status` against an empty Store to get "0 Versions" (a directory count; ticket 11 replaces it with the Index). A `--store` that does not exist is an error; lorekeep never creates the folder. The Store is resolved from `LOREKEEP_STORE` or `--store`, the Run's Tag from `LOREKEEP_TAG` or `--tag`, and the host table is two layers in the shape the spec shows: the package's default table (exactly the rows the spec lists under the TOML example) and `lorekeep.toml` in the Store, read with its defaults (`freshness_days = 30`, no bucket) and able to extend or override the default rules by prefix. The command layer receives its three edges — an `httpx` transport, a page fetcher (browser, returning the rendered document untouched and the final URL) and a command runner (`gcloud`) — so a test can call any command in-process with argv, a temporary Store and fakes; each fake is built from paths and plain values so a child process can construct its own. The fake transport is built from a list of fixture folders (format and precedence in `tests/fixtures/README.md`, fixtures already committed), compares URLs after percent-decoding path and query and lower-casing the host (not `httpx.URL` equality, which keeps `%2F` and `/` apart), raises for an `error` fixture, and records every request and every miss. The fetcher fake has a "not installed" mode. Two test helpers live beside the fakes: one writes a Version straight from a fixture folder (body verbatim, `original.sha256` and `original.url` of that response, chosen `fetched_at`), the other ages a stored Version by rewriting `fetched_at` in its frontmatter. The host table parser merges the two layers into one ordered rule list (a `lorekeep.toml` rule replaces the default rule with the same prefix); the longest-prefix lookup over that list is ticket 02. Runtime dependencies are the spec's list, PyYAML included; `pytest`, `ruff`, `pyright` pass; `frictionless` is a dev dependency. Crawl4AI is the optional extra `browser`, not installed by `uv sync`; MarkItDown is installed with its `pdf` extra.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `uv sync && uv run lorekeep --help` lists `get add search index recheck backup restore tag status skill`
- [ ] `lorekeep status` on a new Store prints a summary with zero Versions and exits 0
- [ ] a missing `LOREKEEP_STORE`/`--store` is an error with a one-line message; a missing Tag is an error only for `get` and `add`
- [ ] `lorekeep.toml` is parsed in the spec's `[[hosts]]` shape; absent keys take the spec's defaults; a malformed file names the key that failed; the merged rule list has a `lorekeep.toml` rule in place of the default rule with the same prefix
- [ ] frontmatter is loaded with `yaml.BaseLoader`: a publisher value such as `2026-08-13T00:00:00.0000000Z` is read as a string, never a `datetime`; a written ETag keeps its quotes
- [ ] every flag is declared on its subcommand, none on the root parser; `--tag` is single on `get`/`add` and repeatable on `search`/`recheck`
- [ ] `cssselect` is a runtime dependency (`lxml`'s `.cssselect()` works after `uv sync` without extras)
- [ ] the default host table holds exactly the spec's eight rows with their publishers, authorities, Twin kinds and AWS's `page_suffix`; `milvus.io` has no `browser` flag
- [ ] `status` with a `--store` that does not exist exits non-zero and creates nothing
- [ ] a test can run a command with a fake transport, fake fetcher and fake runner and read its stdout, stderr and exit code
- [ ] the fake transport answers `…?accept=text%2Fmarkdown` with the fixture recorded as `…?accept=text/markdown`, prefers the fixture with the most matching `match_headers`, raises `httpx.ReadTimeout` for the `timeout` fixture, answers `404` for an unknown URL and lists it in its misses
- [ ] the fetcher fake in "not installed" mode reports that and records no call; both helpers exist and are used by one test each
- [ ] `uv sync` does not install Crawl4AI; `uv sync --extra browser` does
- [ ] `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` all pass
