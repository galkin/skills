# 01: Scaffold and the test seam

**What to build:** A developer can `uv sync`, run `lorekeep --help` and see every subcommand of the spec as a stub, and run `lorekeep status` against an empty Store to get "0 Versions". The Store is resolved from `SOURCES_ROOT` or `--store`, the Run's Tag from `LOREKEEP_TAG` or `--tag`, and `lorekeep.toml` is read with its defaults (`freshness_days = 30`, empty host table, no bucket). The command layer receives its three edges — an `httpx` transport, a page fetcher (browser) and a command runner (`gcloud`) — so a test can call any command in-process with argv, a temporary Store and fakes. The fixture loader reads recorded responses (status, headers, body) from the fixtures folder. `pytest`, `ruff` and `pyright` pass.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `uv sync && uv run lorekeep --help` lists `get add search index recheck backup restore tag status skill`
- [ ] `lorekeep status` on a new Store prints a summary with zero Versions and exits 0
- [ ] a missing `SOURCES_ROOT`/`--store` is an error with a one-line message; a missing Tag is an error only for `get` and `add`
- [ ] `lorekeep.toml` is parsed; absent keys take the spec's defaults; a malformed file names the key that failed
- [ ] a test can run a command with a fake transport, fake fetcher and fake runner and read its stdout, stderr and exit code
- [ ] the recorded-response fixture format is documented in the tests folder and one fixture exists
- [ ] `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` all pass
