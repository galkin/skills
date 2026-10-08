# Parallel translation and review

A coordinator assigns workers concrete, disjoint numeric filename ranges, each processed in order. Pass the translation contract, current glossary/style guide, relevant continuity context and established new names to each worker.

The coordinator maintains one assignment list in `series/translation-log.md`. Before reallocating a range, tell its current owner to stop before that range and confirm ownership, then dispatch it. Rebalance only unstarted files; preserve completed text and receipts. Keep the coordinator available for terminology decisions and final validation.

Each worker:

- Writes only assigned translation files and their per-file state receipts.
- Reads one chapter at a time, retaining adjacent context as necessary.
- Sends important new names or card terms to the coordinator before they spread across ranges.
- Writes proposed terms to its own file under `series/term-proposals/`, rather than editing the shared glossary concurrently.
- Reviews each assigned file as the translation contract requires before recording `reviewed`, then reports completed filenames, outstanding issues and source inconsistencies.

The coordinator reconciles aliases and conflicting terms across all affected translations. Those edits invalidate prior receipts; reread the changed passages and reconfirm the review only after the original full review still applies. An independent reader should check high-risk passages, unusually short translations and system messages when available.

On usage limits or interruption, retain files and receipts and report the exact remaining ranges. Retry when access is restored; never label an unfinished book complete or build it by bypassing the review gate.
