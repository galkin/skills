# Experiment: authoring with the Store versus fetching by hand (2026-10-18)

**Question.** Does a Run author write better or cheaper Bites when it reads Sources through
lorekeep instead of fetching AWS pages itself?

**Setup.** Guide `aws-aip-2026-10`, group part 1.3a (Bites 1.3.1–1.3.5: input quality
thresholds, Glue Data Quality / Data Wrangler / Lambda metrics, Textract / Transcribe / Comprehend /
Bedrock multimodal, SageMaker Processing vs Lambda, multimodal pipelines with provenance). The
five Bites and their manifest items were deleted in two worktrees of the pipeline repository and
re-authored from the same `.task/` (group file, LESSONS, INDEX without the five) by one fresh Codex
author each (`gpt-6.1-sol`, effort medium, the run's `AUTHOR.md`), then reviewed by one fresh
Claude reviewer each (`claude-opus-5-5`, effort medium, the run's `REVIEWER.md`, round 1, no fix
round). Authoring only: no quiz, no diagrams, no Labs.

- **alpha** — the `sources` worktree: the Store (661 of 662 AWS pages cited by the guide, as
  Markdown Twins) and the lorekeep skill; `AUTHOR.md` › Reading AWS pages replaced by lorekeep
  (`get --json`, `search`, cite `url`, no curl, no web).
- **beta** — a worktree from `main`: the run's `AUTHOR.md` as it was (curl the `.md` twin into an
  empty `.task/sources/`, web search to find pages).
- **baseline** — the original 1.3a of the run (2026-10-10, same author model and briefs), review
  round 1 as recorded in the archive.

## Result

| | alpha (lorekeep) | beta (as main) | baseline (run) |
| --- | --- | --- | --- |
| Verdict | CHANGES_REQUESTED | APPROVE | APPROVE |
| blocking / should-fix / nit | 1 / 5 / 3 | 0 / 8 / 3 | 0 / 9 / 3 |
| Quick Diagnostic scores | 9, 10, 10, 10, 10 | 10, 9, 10, 10, 10 | 10, 9, 10, 10, (10) |
| claims the reviewer verified, all correct | 33 | 25+ | ~30 |
| words (author's count) | 1095–1248 | 1080–1219 | 1168–1347 |
| references in five Bites | 38 (5–9 each) | 30 (4–8 each) | — |
| wall time, author | 6 min 27 s | 6 min 15 s | — |
| Codex turns / tool calls | 31 / 30 | 29 / 28 | — |
| input tokens, uncached | 141k | 111k | — |
| output tokens | 21.1k | 18.6k | — |
| context at the last turn | 149k | 119k | — |
| pages fetched from the web | 0 | 29 (two 404 on guessed paths) | — |

**Quality: a draw.** Both authors made the same substantive miss, the Textract synchronous /
asynchronous boundary (10 MB and one page vs 500 MB and 3,000 pages); alpha's reviewer rated it
blocking, beta's should-fix. Everything else is should-fix: duplicated Converse limits and
re-teaching between Bites in alpha, missing mechanisms (DQDL analyzers, Bedrock Data Automation,
Processing completion) and reference titles in beta. Both reviewers found every verified claim
correct and both flagged too many references (alpha 8–9 per Bite). The reviewers differ in
severity calibration more than the Bites differ in quality.

**Tokens: alpha cost about a quarter more, for reasons that are not the Store.** Where alpha's
extra ~30k input tokens went, from the Codex session:

1. ~10k: `orca skills get orchestration`, which the author ran on its own; beta did not.
2. ~10k: reading `.agents/skills/lorekeep/SKILL.md` (249 lines) in full, as the brief said.
3. ~12k: reading Store files through Python scripts that printed 20–27 KB slices, instead of
   `grep`/`sed -n` as the brief said; the Twins in the Store are the same text beta fetched.
4. The `get --json` lines themselves: 10 calls, ~600 characters each; negligible.

Beta spent ~15k on two web searches (40 KB and 19 KB of results) and on 404s from guessed
`.md` paths, which lorekeep made unnecessary: alpha asked for 10 pages and got all 10 from the
Store (`fresh`), none fetched. So the Store removed the search-and-guess cost (~15k) and added the
skill-reading cost (~10k); the rest of the difference is the author's own wandering, which a
brief can stop (name the page-reading commands in two lines, forbid other skills).

**Behaviour.** Alpha cited only `url`s from the JSON, every one an `.html` address; beta cited
`.html` too. Alpha's report carries the full `get --json` log, which is the provenance the run
wanted. Neither author cited a `.md` address. Alpha used `search` once, `get` nine times.

## What to change

- **Brief:** the lorekeep paragraph should be three lines (env, `get --json`, cite `url`), and
  the brief should say "read the file at `path` with `grep`/`sed -n`, never print it"; the skill
  need not be read in full by an author whose brief gives the two commands. Saves ~10k.
- **Skill:** nothing the experiment proves wrong; the author did not hit a Reading, a warning or
  a failure.
- **Tool:** `get --json` output is long for a Run that only needs `path` and `url`; a
  `--format path,url` or a shorter default would trim each call. Minor.
- **Measurement:** one author per arm is one sample; the reviewer's severity varies more than the
  arms. A second pair with the trimmed brief would show whether alpha reaches beta's cost.

Files: `reports/experiment-1.3a/{alpha,beta}/` hold both arms' Bites, author reports and
reviews; `codex-usage.json` the token counts.
