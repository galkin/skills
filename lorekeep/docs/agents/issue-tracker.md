# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files under `docs/issues/`.

They are committed, not ignored. An issue tracker that disappears on clone is not a tracker:
the files are the record, a commit can cite the ticket it closes, and the history of how a
decision was reached stays next to `docs/adr/`, which already works this way.

## Conventions

- One feature per directory: `docs/issues/<feature-slug>/`
- The spec is `docs/issues/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `docs/issues/<feature-slug>/<NN>-<slug>.md`,
  numbered from `01` — never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see
  `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments`
  heading

## When a skill says "publish to the issue tracker"

Create a new file under `docs/issues/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number
directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `docs/issues/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `docs/issues/<effort>/NN-<slug>.md`, numbered from `01`, with the question in
  the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a
  `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it
  lists is `resolved`.
- **Frontier**: scan `docs/issues/<effort>/` for ticket files that are open, unblocked, and
  unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append
  a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.

## Two deliberate departures from the skill's template

Both are choices about this repo, not defaults to be re-derived. `setup-matt-pocock-skills` seeds
this file with `.scratch/`; re-running it, or refreshing it from an updated template, would undo
them.

- **`docs/issues/`, not `.scratch/`.** The name has to match the role. A dot-prefixed directory
  called "scratch" reads as throwaway, and this is the work log — it sits beside `docs/adr/`
  because it is the same kind of artefact at a finer grain.
- **No inner `issues/` level.** The template nests tickets at `<feature>/issues/<NN>-<slug>.md`,
  which under this root would stutter as `docs/issues/<feature>/issues/…`. Tickets are numbered
  and `spec.md` is named, so the two never collide as siblings.
