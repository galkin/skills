# AGENTS.md

Engineering contract for **lorekeep** — a command-line tool that collects the sources an LLM task
reads (vendor documentation, specifications, third-party pages, research pasted from chats), keeps
each one as Markdown with its provenance, and makes a project's sources searchable and reusable
across runs. Its first consumer is the certification guide pipeline of `agentic-system.design`.

`CLAUDE.md` is a symlink to this file. Repository content is written in English; conversation with
the owner is in Russian.

## Read this much

| Doing                              | Read                                                                   |
| ---------------------------------- | ---------------------------------------------------------------------- |
| Any task                           | this file, then `GLOSSARY.md` and the ADRs in `docs/adr/`              |
| Filing or picking up an issue      | `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`         |

## Commands

Python 3.13 managed by `uv` (`requires-python = ">=3.13,<3.14"`: 3.12's bundled SQLite 3.50 fails
the Index's search queries, and 3.14 has no wheel for a transitive dependency of `markitdown[pdf]`). `uv sync` installs everything; then:

- `uv run pytest` — the test suite. Tests never touch the network: fetching is tested against pages
  saved under `tests/fixtures/`.
- `uv run ruff check && uv run ruff format --check` — lint and format, non-mutating.
- `uv run pyright` — type checking.

Run all three before reporting work complete.

## Invariants

- **A store lives outside this repository.** The tool reads its location from one setting
  (`LOREKEEP_STORE`); no path to a store is ever hardcoded, and no store content is committed here.
- **A Version or an Original in a store is never rewritten.** A changed page is a new file beside
  the old one; the few files that grow (`tags.csv`, `checks.csv`, `withdrawals.csv`,
  `datapackage.json`) are appended or regenerated; a Source stored by mistake is withdrawn, never
  removed (ADR 0010); and the index is always rebuildable from the files.
- **The tool never changes the machine it runs on** beyond the store it was pointed at and the
  folder `skill --build <dir>` was pointed at — no installs, no profiles, no services.
  Anything else is shown to the owner as a command to run.

## Agent skills

### Issue tracker

Local Markdown under `docs/issues/<feature>/`, committed. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles under their default names, plus `done`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` at the root and `docs/adr/`. See `docs/agents/domain.md`.
