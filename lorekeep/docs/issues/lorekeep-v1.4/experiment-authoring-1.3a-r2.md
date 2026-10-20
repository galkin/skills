# Experiment, round 2: a whole unit with the Store versus fetching by hand (2026-10-20)

**Question.** Round 1 ([experiment-authoring-1.3a.md](experiment-authoring-1.3a.md)) found
quality a draw and the Store arm about a quarter dearer, for reasons a brief could remove. With
those reasons removed, and with the whole unit pipeline rather than the author alone, does the
Store arm cost less and write as well?

**Setup.** Guide `aws-aip-2026-10`, group part 1.3a (Bites 1.3.1–1.3.5), the same unit as round 1.
The pipeline repository's new declarative pipeline (`docs/pipeline/bites.yaml`: author → review
r1 → fix → review r2 → commit), run once per arm by `runner run` in Orca Run
`run_fdc9e55f6c96`. Author Codex `gpt-6.1-sol` medium, reviewer Claude `claude-opus-5-5` medium,
the roles in `.claude/agents/`, both arms started at the same minute.

- Branch `galkin/lorekeep-ab` of the pipeline repository, from `main`:
  - `5b43b215` — the five roles no longer name `curl` and `.task/sources`; they read pages "as the
    brief's Sources section says", and the curl briefs carry the cache rule. Behaviour of the
    curl arm is unchanged.
  - `bf7a57ff` — `docs/pipeline/briefs/aws-aip-lorekeep/{author,reviewer}.md`: the aws-aip briefs
    with the Sources section replaced by `lorekeep get --json` / `lorekeep search` against the
    Store (Tag `aws`), "read the file at `path` with `grep`/`sed -n`", cite `url`, and never curl
    or read any skill (lorekeep's included). Copy in `reports/experiment-1.3a-r2/briefs/`.
- Two Orca worktrees from that branch, each its own slot and integration worktree, the five Bites
  and their manifest items deleted, `.task/groups/1.3a.md` from the run archive, `INDEX.md`
  rebuilt, `.task/sources/` empty:
  - **lk** — `--param guide=aws-aip-lorekeep`: author **and** reviewer read through the Store;
  - **curl** — `--param guide=aws-aip`: the run's briefs, curl of `.md` twins into `.task/sources`.
- **Blind judge**: one fresh Opus session (medium) given both final drafts as X (curl) and Y (lk),
  one severity scale for both, facts checked through the Store; no git, no reports, no reviews.

## Result

| | lk | curl |
| --- | --- | --- |
| Path | r1 APPROVE → fix → r2 clean → commit | the same |
| Wall time to commit | **17.5 min** | 22 min |
| Author (Codex) fresh input / calls / Codex window | **117k** / 35 / 19 % | 151k / 40 / 22 % |
| Reviewer (Opus, r1+r2 in one session) fresh input | 108k | **95k** |
| Fresh input, both roles | **225k** | 246k |
| Output tokens | 45k | 45k |
| Own reviewer r1, blocking / should-fix / nit | 0 / 8 / 2 | 0 / 2 / 2 |
| **Judge**, blocking / should-fix / nit | 0 / 4 / 5 | 0 / 4 / 5 |
| **Judge**, Quick Diagnostic total | **50** | 49 |
| **Judge**, Bites won | **3** (1.3.1, 1.3.2, 1.3.4), tie 1.3.5 | 1 (1.3.3) |
| Pages from the web | 0 (author 5 `get` calls, 4 `search`) | 34 pages by curl, 540 KB |
| References in five Bites | 25 | 30 |

**Tokens.** Round 1's +25 % is gone: the Store arm is ~9 % cheaper in fresh input, all of it at
the author (−34k); its reviewer spent 13k more than the curl reviewer, which one pair cannot tell
from noise. Wall time favours the Store (−4.5 min), mostly at the author (8 vs 11 min).

**Behaviour.** The round 1 causes did not recur: in the lk arm no `orca skills get`, no read of
the lorekeep skill, no curl, no web search; Store files were read by `grep`/`sed -n` on the
`path` from the JSON (python only wrote the Bites). The lk reviewer used one `get` call over the
cited URLs and one `search`. Both arms read `technical-documentation/SKILL.md`, as the brief says.

**Quality: a draw, the Store arm narrowly ahead.** The judge found no wrong fact in either draft
and the same defect counts; it gave lk three Bites for naming the setting that carries each
decision (`On ruleset failure`, `compositeRuleEvaluation.method`, the 777,600 s ceiling,
`ImageBlock.format`), and curl 1.3.3 for the Textract page limits, Comprehend's input contract and
the modality check API. The lk author again missed the Textract one-page limit for synchronous
PDF/TIFF — three of the four authors of this unit across both rounds missed it, so it is a
`LESSONS.md` candidate, not a Store effect.

**Reviewer calibration again.** The two own reviewers differed 8 versus 2 should-fix; the judge,
on one scale, found 4 and 4. Arm comparisons need the blind judge, not r1 counts.

## What to change

- **Pipeline:** the role change in `5b43b215` is worth keeping regardless of lorekeep (the roles
  stop contradicting a brief that reads sources another way); the lorekeep briefs are the
  template for running a guide on the Store.
- **Brief:** the 3-command Sources section and "never read the skill" held; no other change.
- **Tool:** nothing the run hit. `get --json` length remained negligible (5 calls).
- **Measurement:** one pair per round; a third pair on a unit whose pages are not yet in the Store
  would measure the cold path, which this round (warm Store) did not.

Files: `reports/experiment-1.3a-r2/` — `{lk,curl}/` (Bites, reviews r1/r2, author report,
`cost.txt`), `judge-verdict.md`, `briefs/`.
