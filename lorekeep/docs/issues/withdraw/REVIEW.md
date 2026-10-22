# Review of 0f02c28 — fix on the same branch

Two-axis review: the brief is met and the four deviations stand. Fix these, one commit, then
re-run the gate and append a "Review fixes" section to REPORT.md ending `DONE withdraw-fixes`.

1. **One rule, one place (docs).** What a withdrawal does is listed in ADR 0010, `GLOSSARY.md`,
   `curating.md`, `store.md` and again in the `recheck --citations` bullets; "report a page stored
   by mistake to the owner" is in `SKILL.md`, `store.md` (twice) and `curating.md`. Keep the
   per-command list in one place in the skill (`store.md` › Withdrawals) and link to it; the ADR
   keeps the why, the glossary one sentence, `curating.md` the command and its flags; the
   report-to-owner rule only in `SKILL.md`.
2. **Check under the lock (ADR 0009).** `withdraw.run` and `refused_as_withdrawn` read
   `withdrawn()` before `commit` takes the lock. Make the "is it withdrawn / does this row change
   anything" decision inside the locked section, so two concurrent calls cannot both append.
3. **`revisits()`** leaves withdrawn Sources out, so a cited withdrawn Source gets only the error
   line, not also a revisit.
4. **`tag add`** (URL and `--prefix`) skips a withdrawn Source, saying so for a URL; and
   `rules sample` / `rules check` leave withdrawn Versions out. One shared predicate, not a new
   copy per command.
5. **Smaller:** `notify` loses its `withdrawals` parameter — `commit` skips `notify` instead;
   parse `withdrawals.csv` once per rebuild; rename `taken_back` in `read.py` to `withdrawn`;
   rewrap `index.notify`'s docstring.
