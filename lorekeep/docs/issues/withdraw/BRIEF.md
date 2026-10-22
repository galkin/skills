# Withdraw a Source stored by mistake

Owner, 2026-10-22: a page stored by mistake must be removable from a Store. The case that raised
it: a collector, looking for a specification's logo, stored four pages under Tag
`specifications` that have nothing to do with it — `ans.dev` (a networking company, not Agent
Name Service), `www.okf.dev` (a parked domain), `www.visa.sk` (visa.com redirected to a regional
home page) and `agoraprotocol.org` (not Agora's content). Today there is no command for it, and
the skill forbids editing the Store's files.

## Decision (the coordinator's, delegated by the owner): soft delete

A **withdrawal** is a row appended to a new growing file, `withdrawals.csv`
(`url,withdrawn_at,reason`), never a removed file. Why:

- ADR 0002: a Version or an Original is never rewritten or removed; ADR 0004: the backup is a
  no-clobber rsync that never deletes — a hard delete would leave the bucket and the Store
  disagreeing, silently.
- Provenance is the tool's point: what was stored, when and why it was taken back stays readable.
- It is reversible, and a citation that still names a withdrawn Version fails loudly instead of
  pointing at a missing file.

Write an ADR for it (the next number), in the repository's ADR form, and add the term to
`GLOSSARY.md`.

## What to build

- `lorekeep withdraw URL --reason TEXT` — a Curator command (the owner's, like `tag add`): the
  `url` is resolved as `get` resolves it (normalised, Twin-reduced, through `aliases.csv`); a URL
  with no Source exits 2 with a message. Withdrawing withdraws the Source (every Version).
  Decide and document how a withdrawal is undone (for example `--undo`, appending a row), and
  what a second `withdraw` of the same Source does.
- A withdrawn Source is out of `search` and the Index, out of the Readings `read` builds, and
  counted on its own line by `status`. `get` of a withdrawn URL refuses with a message naming the
  withdrawal, unless the owner undoes it first. `recheck` skips it. `recheck --citations` (or
  whatever resolves citations) reports a citation of a withdrawn Version as a failure.
- `backup` copies `withdrawals.csv` with the other growing files; `datapackage.json` describes
  it.
- The skill: `references/curating.md` gets the command; `references/store.md` the file;
  `SKILL.md`'s rule "Write to the Store only through `get` and `add`" stays true for Runs, and
  says that a page stored by mistake is reported to the owner, who withdraws it. Keep SKILL.md
  inside its tests' limits.

Tests never touch the network (fixtures, as the suite does today).

## Flow

1. `git switch -c lorekeep-withdraw` in `/Users/galkin/Projects/skills` (the checkout is clean on
   `main`). Read `lorekeep/AGENTS.md`, `GLOSSARY.md`, `docs/adr/`, then file the ticket per
   `docs/agents/issue-tracker.md` under `docs/issues/withdraw/` beside this brief.
2. Build it. Gate from `lorekeep/`: `uv run pytest -q` (its exit code), `uv run ruff check`,
   `uv run ruff format --check`, `uv run pyright`.
3. Commit on the branch. Do not bump the version, tag, build the skill, merge or push: the
   coordinator reviews and releases.
4. Live check, read-only: `LOREKEEP_STORE=~/orca/sources/agentic-system.design uv run lorekeep
   status` must still run against the real Store. Do **not** withdraw anything in it.

## Report

`docs/issues/withdraw/REPORT.md`: what was built, the undo decision, the gate's output, the
commits, and anything in this brief that turned out wrong. Last line `DONE withdraw`.
