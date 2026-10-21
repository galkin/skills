---
name: orca-orchestration
description: Runs a project's agent workflows (author → review → fix → commit and the like) unattended with its own runner for a subset of Dagu YAML, a queue per slot worktree, plain-file run state under .task/runs, and an adapter CLI for Orca workers (start, wait, wake, drain, budget, cost). Use when starting, watching, resuming or retiring such a run, when a slot reports HELD or STALLED, or when writing or changing a workflow or queue file.
---

# orca-orchestration

Three layers, two of them here. The **adapter** (`adapter/`) is the only code that knows Orca.
The **runner** (`runner/`, `actions/`) executes workflow files and the queue and knows nothing
about roles or Orca. The **project** supplies the rest: the workflow files (here `docs/pipeline/*.yaml`), role files, briefs,
a queue file, and a doc naming its paths (here: `docs/pipeline/README.md`).

The coordinator's job is small: start the slots, sleep, decide when a slot holds, finish.
Everything else runs on its own.

## Commands

From the skill folder, with `uv` (both dependencies are in its cache; nothing is installed).
`bin/runner` and `bin/adapter` are uv scripts: they work from any shell and under `nohup`:

```sh
cd .agents/skills/orca-orchestration
```

| Command                                                              | Does                                                                                         |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `bin/runner validate <wf.yaml>`                                              | Schema and load-time checks; prints the inferred step order.                                 |
| `bin/runner run <wf.yaml> --run-id <id> --param k=v …`                       | One run. Exit 0 succeeded or partially succeeded, 1 failed, 2 invalid.                       |
| `bin/runner retry <wf.yaml> --run-id <id> [--step <s> [--downstream]]`       | Rerun failed and not-run steps, or reset one step and its descendants and continue.          |
| `bin/runner exec <wf.yaml> --run-id <id> --step <s> [--env K=V …]`           | One step's commands once, in the run's params, outputs and env, outside the run (`run.json` untouched); exits with the command's code. |
| `bin/runner status [--run-id <id>]`                                          | Per-step status, exit code, outputs and error; without `--run-id`, every run.                |
| `bin/runner queue <q.yaml> --slot <worktree> [--resume <item> [--step <s>]]` | Continuous mode for one slot. Exit 0 queue empty or retired, 2 an item is held, 7 only held. |
| `bin/runner queue <q.yaml> --status`                                         | Item states.                                                                                 |
| `bin/adapter drain --run <run id>`                                            | Consumes worker heartbeats and done messages and keeps running; prints an `ATTENTION` line for every unanswered question or escalation, again each round until its thread holds a reply. `--ack <msg id>` answers one that needs no words. Only beside a running queue: see [adapter.md](references/adapter.md#commands). |
| `bin/adapter unstall`, `bin/adapter close --worktree W`, `bin/adapter release --task <id>`      | Wake limit-stalled terminals; release the worktree's settled terminals the adapter started (`--all`: every terminal); release a settled task. |
| `bin/adapter cost --worktree <slot> [--write]`                                | Tokens per worker session by item and step (joined through the launch ledger); `--write` records them beside the run state. |

`--runs-dir` goes before the subcommand and defaults to `.task/runs` relative to the cwd, so
pass it and the workflow file as absolute paths. A workflow's `working_dir` is relative to
the workflow file, not to the cwd.

## Run a queue

1. **Prepare.** The project doc names the workflow, the queue file, the slot worktrees and
   what each slot must contain. Make sure every slot has it, then `bin/runner validate <wf.yaml>`.
   The queue checks every item's params against the workflow when a slot starts, before any
   hook runs.
2. **Start**, detached, with the skill folder as cwd and `$W` the integration worktree:

   ```sh
   nohup bin/runner --runs-dir $W/.task/runs queue $W/.task/runs/queue.yaml --slot <slot path> >> $W/.task/runs/slots.log 2>&1 &
   nohup bin/adapter drain --run <run id> >> $W/.task/runs/drain.log 2>&1 &
   caffeinate -i -w <pid of a slot> &
   ```

   One `queue` process per slot. A slot takes the next item as soon as its own is done, idles
   while the admission hook says no, and waits out a usage limit by itself.
3. **Sleep.** Watch `slots.log` for `HELD`, `queue empty` and `retired`, and `drain.log` for
   `ATTENTION` (a Monitor on those words, or a check every 30 minutes). Read nothing else
   unless one of them fires: every step's output is on disk for later. Every `ATTENTION` line
   names a message id, its sender and its age, and the open ones are printed together again
   (at once when another arrives, else every `--repeat-sec`) until each is answered: `orca
   orchestration reply --id <msg id> --body …`, or `bin/adapter drain --run <run id> --ack
   <msg id>` for an escalation that needs action rather than words. The drain does not exit
   on a question, so it never needs restarting to see the next one.
4. **Decide** when a slot exits 2 (`HELD`):

   ```sh
   bin/runner --runs-dir $W/.task/runs queue $W/.task/runs/queue.yaml --status
   bin/runner --runs-dir $W/.task/runs status --run-id <item>        # which step, exit code, outputs, the failed step's log
   cat $W/.task/runs/<item>/steps/<step>.<n>.log              # what it said
   ```

   Fix the cause (the project doc says which of these it allows), then restart the slot on
   that item: `… queue <q.yaml> --slot <slot> --resume <item> --step <step>`. The slot
   finishes the item and continues the queue. For a unit outside the queue,
   `bin/runner retry <wf.yaml> --run-id <id> --step <step> --downstream` does the same.

   - **Another targeted-fix round**, when the workflow declares one
     ([workflow-syntax.md](references/workflow-syntax.md#a-targeted-fix-round)): resume at its
     fix step; the owning role fixes what is left and a focused re-review checks that
     correction. Prefer it to a waiver for a finding nobody accepts.
   - **A fix by hand** goes through the commit step like a worker's, never through `git
     commit` or an edit in the integration worktree: edit the **slot**, run the workflow's own
     commit step in check-only mode,
     `bin/runner --runs-dir $W/.task/runs exec <wf.yaml> --run-id <item> --step <commit step> --env CHECK_ONLY=1`
     (the same `CHECKS_FULL`, nothing committed; see [actions.md](references/actions.md)),
     repeat until it passes, then resume at the decision step so the workflow's commit step
     commits and merges the edit. A hand fix is unreviewed: the project doc says what records
     it (a waiver, or a targeted round's re-review).
   - **A waiver or a follow-up to the worker**, as the project doc defines them.
5. **Finish.** `touch <runs dir>/q/retire-<slot name>` retires an idle slot; `bin/adapter close
   --worktree <slot>` releases the terminals the adapter started there once their tasks settled
   and names what it kept (a retained one, the owner's own); `bin/adapter cost --worktree <slot>
   --write` records what each step cost, which is where the next queue file's `--costs` come from.

One item by hand, without the queue: `bin/runner run <wf.yaml> --run-id <id> --param …` with the same
`--runs-dir`. The queue adopts such a run: an item whose run directory already holds a
`run.json` is resumed from its unfinished steps with the run's own params, not restarted, so
a unit started by hand under the queue's runs dir and item id can be handed to a slot by
simply listing it.

## Run state

`<runs dir>/<id>/run.json` (status, params, every step's attempts, exit codes, outputs),
`run.log`, `steps/<step>.<n>.log` and `.out` (the attempt's output records), `steps/<step>.exec.<n>.log`
(a `runner exec` by hand);
`<runs dir>/q/<item>.active|held|done` for the queue. Plain files: nothing needs the runner
or Orca to be running to be read.

Step statuses are Dagu's: `succeeded | failed | skipped | canceled`. A step that exits
non-zero without `continue_on` fails the run and cancels its descendants; that is a decision
point, and `retry --step` resumes from it. A `wait` step that exits 5 (usage limit) is retried
by the queue after the stall hook's time, not held.

## References

- Writing or changing a workflow file: [references/workflow-syntax.md](references/workflow-syntax.md)
  (the Dagu subset: fields, references, conditions, outputs, continue_on, retry, repeat, pitfalls).
- Writing a queue file, hooks, item states: [references/queue.md](references/queue.md).
- The adapter commands a workflow step calls, their outputs, exit codes, launch routes, the
  fallback launch, the budget and cost commands: [references/adapter.md](references/adapter.md).
- `actions/commit.sh` (checks, commit, cherry-pick under a lock) and its environment:
  [references/actions.md](references/actions.md).
- Tests, the shell choice, Dagu provenance, verified Orca receipt and vendor log shapes:
  [references/development.md](references/development.md).
