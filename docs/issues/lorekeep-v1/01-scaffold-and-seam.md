# 01: Scaffold and the test seam

**What to build:** A developer can `uv sync`, run `lorekeep --help` and see every subcommand of the spec as a stub, and run `lorekeep status` against an empty Store to get "0 Versions". The Store is resolved from `LOREKEEP_STORE` or `--store`, the Run's Tag from `LOREKEEP_TAG` or `--tag`, and the host table is two layers: the package's default table (the hosts the spec's fixtures come from, with their Twin rules, publisher and authority) and `lorekeep.toml` in the Store, read with its defaults (`freshness_days = 30`, no bucket) and able to extend or override the default rules. The command layer receives its three edges — an `httpx` transport, a page fetcher (browser) and a command runner (`gcloud`) — so a test can call any command in-process with argv, a temporary Store and fakes; each fake is built from paths and plain values so a child process can construct its own. The fake transport loads every folder under `tests/fixtures/` (format in its README, fixtures already committed), answers by `url` and `match_headers`, and records every request and every miss. `pytest`, `ruff` and `pyright` pass. Crawl4AI and Docling are declared as optional extras (`browser`, `layout`), not installed by `uv sync`; MarkItDown is installed with its `pdf` extra.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `uv sync && uv run lorekeep --help` lists `get add search index recheck backup restore tag status skill`
- [ ] `lorekeep status` on a new Store prints a summary with zero Versions and exits 0
- [ ] a missing `LOREKEEP_STORE`/`--store` is an error with a one-line message; a missing Tag is an error only for `get` and `add`
- [ ] `lorekeep.toml` is parsed; absent keys take the spec's defaults; a malformed file names the key that failed; a rule in it overrides the package's default rule for the same prefix
- [ ] the default host table resolves `platform.claude.com`, `docs.aws.amazon.com`, `learn.microsoft.com`, `docs.nvidia.com`, `claude.termidy.com` and `raw.githubusercontent.com/anthropics` to a publisher, an authority and (where one exists) a Twin rule
- [ ] a test can run a command with a fake transport, fake fetcher and fake runner and read its stdout, stderr and exit code
- [ ] the fake transport serves every committed fixture by URL, honours `match_headers`, and a request for an unknown URL is answered `404` and listed in the transport's misses
- [ ] `uv sync` installs neither Crawl4AI nor Docling; `uv sync --extra browser` installs Crawl4AI
- [ ] `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` all pass
