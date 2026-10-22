# 01: withdraw a Source stored by mistake

**What to build:** `lorekeep withdraw URL --reason TEXT`, the Curator's command that takes a Source
stored by mistake out of every Run's view without removing a file (`BRIEF.md` beside this ticket).
The case that raised it: a Collector looking for a specification's logo stored four unrelated pages
under Tag `specifications` — `ans.dev`, `www.okf.dev`, `www.visa.sk`, `agoraprotocol.org`. A
withdrawal is a row appended to a new growing file, `withdrawals.csv`; `--undo` appends the row that
takes it back. The URL resolves as `get` resolves it (normalised, Twin-reduced, through
`aliases.csv`) and the withdrawal covers every Version of the Source. A withdrawn Source is out of
`search` and the Index's Sections, out of the Readings `read` builds, out of `recheck`'s scope and
counted on its own line by `status`; `get` refuses it naming the withdrawal; `recheck --citations`
reports a Citation of it as a failure; `backup` copies `withdrawals.csv` and `datapackage.json`
describes it. Decisions: ADR 0010.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `withdraw URL --reason TEXT` appends one row and names the Source; an alias or a Twin address
      of it withdraws the same Source; a URL with no Source exits 2 and writes nothing
- [x] a second `withdraw` of a withdrawn Source appends nothing and says when and why it was
      withdrawn; `withdraw --undo URL --reason TEXT` appends the row that takes it back, and an
      `--undo` of a Source not withdrawn appends nothing
- [x] `search` finds no Section of a withdrawn Source, finds it again after `--undo`; `status` prints
      a `Withdrawn:` line and leaves the Source out of its other counts
- [x] `get` of a withdrawn URL exits 1 naming the withdrawal, fetches nothing, adds no Tag
- [x] `read` builds no Reading of a withdrawn Version; `recheck` asks nothing about it
- [x] `recheck --citations` of a work citing a withdrawn Source prints the failure and exits 1
- [x] `backup` copies `withdrawals.csv`; `datapackage.json` has a `withdrawals` resource
- [x] ADR 0010, `GLOSSARY.md` › Withdrawal, `references/curating.md`, `references/store.md`,
      `SKILL.md`'s Store rule

## Comments

**2026-10-22** — done on `lorekeep-withdraw`; tests in `tests/test_withdraw.py`, one or more per
criterion, on Versions written from fixtures (no network).

- **Columns.** `withdrawals.csv` is `url,recorded_at,action,reason`, not the brief's
  `url,withdrawn_at,reason`: an undo needs a row of its own, and `action` (`withdraw` | `undo`)
  says which; the last row of a `url` decides (`store.withdrawn`, the Index's view `withdrawn`).
- **Undo.** `withdraw --undo URL --reason TEXT` appends an `undo` row. A second `withdraw`, or an
  `--undo` of a Source not withdrawn, appends nothing, says so and exits `0`.
- **The Index.** `SCHEMA_VERSION` 9: a `withdrawals` table, the `withdrawn` view, and no Sections
  for a withdrawn Source (its `versions` rows stay, so its address resolves). A withdrawal commit
  does not notify the Index; the next reader rebuilds it, with the Readings an undo needs.
- **Also refused:** `add` of a withdrawn `owner:` Source, and a `get` of a new address that
  redirects to a withdrawn Source (checked before the commit, so nothing is stored or tagged).
- **Live check** on an APFS clone of the first Store (3237 Versions): `status` exit `0`; the four
  pages of the brief withdrawn in the clone leave `search`, the Tag count and the unknown hosts, and
  `get https://www.visa.sk` exits `1` naming the withdrawal. The real Store was not touched: the
  schema bump makes any reader rebuild its Index (see `REPORT.md`).
