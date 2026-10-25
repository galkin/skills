# The adapter

`bin/adapter <command>` from the skill folder (a uv script, no extra dependencies); a workflow
or a queue hook reaches it by path, `.agents/skills/orca-orchestration/bin/adapter`. It calls `$ORCA_CLI_COMMAND` when set, else `orca`.
A workflow step calls it through `run:`; outputs are appended to `$DAGU_OUTPUT_FILE`, so the
step declares them as `outputs`. `--help` on any command lists its flags.

## Contents

- Commands
- Exit codes
- A one-off worker: run --wait
- Watch, and the Run a terminal is bound to
- Launch routes and the fallback launch
- The launch ledger
- Budget: the Codex usage windows
- Cost: tokens per session, item and step
- A worker that is stuck: the playbook by hand

## Commands

| Command                                                                                         | Does                                                                                                                                                        | Outputs                      |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `run [--run R] --worktree W --launch vendor:model:effort [--fallback vendor:model:effort] --role <role> --title T (--spec … \| --spec-file … \| --spec-template …)… [--reuse-task <id>] [--language <name>] [--wait [--keep-terminal] [--poll-sec 30] [--inbox-limit 500]]` | Starts a supervised worker in the role. Without `--run`, the Run this terminal is bound to (`run-current`); none is an error. `--wait` sees a one-off worker through to its end (below). The spec is the `--spec` texts and files joined in order: `--spec-file` literal, `--spec-template` with `${params.x}` (from `DAG_PARAMS_JSON`) and `${env.X}` resolved, an unresolved one refused, `\${…}` literal. With `--reuse-task`, when that task's terminal is still alive the spec is injected there as a follow-up instead of a fresh worker. `--language` sets the Claude session's output language through `--settings`; Codex takes it from the role body. | `task=`, `dispatch=`, `handle=` |
| `wait --run R --task <id> [--handle H] [--poll-sec 60] [--stall-every 5] [--max-reprompts 8] [--runtime-wait 30]` | Polls the task until it settles. A usage limit on the screen at the start gets one wake-up; one found later exits 5. Provider errors (429, capacity, 5xx) re-prompt after 1, 2, 4 … 32 min. While Orca itself is down (`runtime_unavailable`: a restart, a power cut) it keeps polling for `--runtime-wait` minutes, then exits 1 as for any Orca error. `--handle` may be empty; it is looked up from the task. | `status=`                    |
| `followup --run R --handle H --title T (--spec …)…`                                             | A new task injected into a live terminal.                                                                                                                   | `task=`, `dispatch=`, `handle=` |
| `handle --task <id>`                                                                            | Prints the task's terminal handle.                                                                                                                          |                              |
| `alive --handle H`                                                                              | Exit 0 when the terminal is listed.                                                                                                                         |                              |
| `unstall [--worktree W] [--exclude <coordinator worktree>]`                                     | Wakes every terminal whose screen still shows a limit (answers Codex's model menu, sends "continue").                                                        |                              |
| `drain --run R [--once] [--repeat-sec 300]`, `drain --run R --ack <msg id> [--body T]` | Consumes heartbeat and worker_done batches so Orca never nudges the coordinator, and keeps every question and escalation of the run in view: one `ATTENTION <msg id> <type> from <sender> [task <id>] age <n>m \| <subject> \| <body>` line per open message, all of them again whenever a new one arrives and at least every `--repeat-sec`, until its thread holds a reply from someone other than its sender. The run's inbox is the record (so a question that came while no drain ran is found too); a batch holding a question is acked only once the inbox shows it, and stays unacked (replayed) while Orca cannot say so. It keeps running past a question; `--once` makes one round and exits 3 while anything is open. `--ack` answers a message that needs no words with a reply in its thread (default body "Acknowledged by the coordinator."). The coordinator runs it detached. **Only beside a running queue**: it consumes `worker_done` silently, so completion is seen in `slots.log` alone. Workers outside a queue are seen through with `run --wait` or watched with `watch`, never `drain`. While the terminal is bound to another Run, `check --run R` is refused (`consumer_fenced`): the drain logs `check --run R refused: …` and pauses `--retry-sec` instead of spinning, until the binding returns. |  |
| `watch --state F [--run R]… [--runs-file F] [--log slots.log]… [--types question,escalation,worker_done] [--poll-sec 30] [--inbox-limit 1000] [--once]` | One line per new question, escalation and worker_done of the Runs given (default: the bound Run), and per `HELD`, `stalled at`, `queue empty`, `retired` and `only held items` line of each slot log; heartbeats and replies dropped. Never consumes or rebinds. Runs until stopped; `--once` polls once. See Watch below. |  |
| `close --run R`                                                                                 | Frees every worker terminal of the Run (`worker-list --run`, so a worker launched outside any runs dir is found too) whose dispatches have all settled: `worker-release` on the owning dispatch, `terminal close` for an `external_terminal`. Keeps and names a terminal with a dispatch still running, one Orca keeps for the user, and the caller's own (`$ORCA_TERMINAL_HANDLE`); exit 0. The queue's Finish step, and the end of any Run of one-off workers. |  |
| `close --worktree W [--all]`                                                                    | Frees the worktree's terminals the adapter started (the launch ledger) whose last task has settled: `worker-release` on the dispatch `worker-start` returned for a Codex terminal, `terminal close` for a claude-route terminal (Orca calls it `external_terminal` and never owns it). Keeps and names the ones still running, the ones Orca keeps for the user (`user_takeover`, `ownership_transferred`) and the ones it did not start; exit 0 either way (the work is merged by the time a workflow closes). `--all` closes every terminal of the worktree, the playbook's last resort. |  |
| `release --task <id>`                                                                           | `worker-release` for a settled task; exit 1 with Orca's reason when it refuses (retained, not settled).                                                     |                              |
| `budget [--costs step=pct,…] [--new pct] [--week pct] [--margin pct] [--runs-dir D] [--reset] [--why]` | Admission by the Codex usage windows; see Budget.                                                                                                   |                              |
| `cost [--worktree W]… [--hours 12] [--runs-dir D] [--json] [--write]`                           | Tokens per worker session, by item and step, from the vendors' session logs; see Cost.                                                                     |                              |

## Exit codes

| Exit | Meaning                                                        |
| ---- | -------------------------------------------------------------- |
| 0    | ok (`wait`: the task completed)                                |
| 1    | other failure                                                  |
| 3    | `drain --once`: a question or escalation is unanswered; `run --wait`: the worker escalated |
| 4    | `wait`, `run --wait`: the task ended badly (failed, canceled, released), or its worker_done says `failed` |
| 5    | the agent sits on a usage limit (`wait`, `run --wait`, `unstall`) |
| 6    | `wait`: provider errors persisted through every re-prompt      |

A workflow maps 5 to the queue's `stall_exit_code`, so a stalled wait is resumed after the
reset rather than held.

## A one-off worker: run --wait

`run … --wait` launches, then polls as `wait` does (usage limits, provider errors, Orca
outages) and reads the inbox each poll for the task's own messages (by `taskId`, or the
dispatch):

- a **question** is printed once, `QUESTION <msg id> run <run> from <sender> task <id> |
  <subject> | <body> [| options: …]`, followed by `  reply: orca orchestration reply --id <msg
  id> --body '…'`; the wait goes on, since the worker blocks on its `ask` until the reply;
- an **escalation** is printed the same way and ends the wait, exit 3, the terminal kept;
- the **worker_done** ends it: `DONE <outcome> <msg id> task <id> | <subject>`, the whole body,
  `report <path>` when it names one; exit 0 (4 when the outcome is `failed`). The adapter waits
  for Orca to settle the task, then frees the terminal as `close` does (release, or `terminal
  close` for a claude-route terminal), unless `--keep-terminal`;
- a task Orca completes with no worker_done in the inbox prints `DONE task <id> completed
  without a worker_done message` and is freed the same way.

The outputs are `run`'s (`task=`, `dispatch=`, `handle=`) and then `wait`'s `status=`
(`worker_done`, `escalation`, `completed`, `stalled`, …). A question of a Run other than the
bound one carries the `run-use` hint described next.

## Watch, and the Run a terminal is bound to

A coordinator's terminal is bound to one Run: `run-create` binds the new Run, `run-use --id R`
rebinds. Verified on Orca 1.4.237 from a bound coordinator terminal:

- `orchestration inbox` (no `--terminal`) returns the newest messages of **every** Run,
  whatever the binding (`run_id`, `to_handle`, `type`, `thread_id`, `payload` as a JSON string,
  `sequence`, `created_at`, newest first). It has no `--run` flag.
- `orchestration check --run <another Run>` is refused: `consumer_fenced`, "This coordinator
  terminal is bound to run_X, not run_Y." `reply` to that Run's message failed the same way in a live session (not re-run: it would send a message).
- `task-list --run`, `worker-list --run` and `run-show` read any Run.

So `watch` reads only `inbox` and never needs, or performs, a `run-use`: rebinding from a
background process would fence the bound Run's drain and the coordinator's own `check`.
Instead a question or escalation of a Run other than the bound one ends with `| bound to
<run>: orca orchestration run-use --id <its run> before replying`. Reply, then `run-use` back.

`watch` keeps `{"seen": [ids], "logs": {path: offset}, "seq": n}` in `--state` (written
atomically; the last 20 000 ids). A first start, with no state file, records the history as
seen and prints only the questions and escalations whose thread holds no reply from anyone but
the asker (an escalation is rarely answered in its thread, so old ones show once). A slot log
is followed from its end when first seen and from the start when it shrank; a line still being
written waits for the next poll. When a poll's oldest message is newer than the last one seen
(the `sequence` jumped) and the poll was full, it warns to raise `--inbox-limit`. An inbox that
does not answer is logged and retried; the watch does not exit.

## Launch routes and the fallback launch

`--launch` is `vendor:model:effort`.

- `claude`: `terminal create --command "claude --agent <role> --model <m> --effort <e>
  --dangerously-skip-permissions"`, `terminal wait --for tui-idle`, then `worker-start
  --terminal <handle>`. The role is `.claude/agents/<role>.md` **in the worktree**.
- `codex`: `worker-start --agent codex --model <m> --effort <e>`. The role reaches Codex as
  `developer_instructions` in the worktree's `.codex/config.toml`, which `run` writes from the
  body of `.claude/agents/<role>.md` first (one role file serves both vendors). The receipt has
  no terminal handle, so `run` looks it up with `dispatch-show --task`.

`--fallback vendor:model:effort` names a second launch for the moment the first one's vendor
is at its usage limit: with `--reuse-task`, when the task's terminal is alive but its screen
shows the limit, the spec goes to a fresh worker on the fallback launch instead of being
injected (the role file tells the worker how to pick up in a fresh session); without a reuse,
when the vendor is Codex and its 5-hour or weekly window is spent (Budget below), the fresh
worker starts on the fallback launch. Empty means wait for the reset instead (the queue's
stall path).

A role file must not contain a triple quote. The worktree must hold the role file and
whatever the role reads (briefs, lessons) before `run` is called.

`--language <name>` is for a Claude Code whose global `language` setting is not the one the
roles write in: the claude route appends `--settings '{"language": "<name>"}'` to the command,
so nothing is written into the worktree. The codex route ignores it: the role body says the
language, and Codex reads the role body.

## The launch ledger

Every `run` and `followup` appends one JSON line to `<runs dir>/adapter/launches.jsonl`: the
task, dispatch and terminal handle Orca returned, the vendor, model and role, the worktree,
the title, and the item and step from `DAG_RUN_ID` / `DAG_RUN_STEP_NAME` (the runner exports
them to every step; a queue hook has `RUNS_DIR`). The runs dir is `--runs-dir`, else
`$RUNS_DIR`, else the parent of `$DAG_RUN_WORK_DIR`; with none of them the launch is logged
as not recorded. `cost` and `close` read it; nothing else does. A launch by hand outside a
run is simply not in it.

## Budget: the Codex usage windows

Codex has a 5-hour window and a weekly one, each `used %` and `resets_at`, read from the
newest `rate_limits` Codex wrote to `~/.codex/sessions` (`primary` = 5-hour, `secondary` =
weekly). Only Codex: Claude Code writes its windows to no file (they reach the status line
alone), so Claude steps are not priced, and a Claude limit is met when it shows on the
worker's screen: `wait` exits 5 and the queue stalls the item.

`budget` admits (exit 0) when `used 5h + reserved + new + margin` stays under 100 % and the
weekly window allows one more item. `--costs step=pct,…` prices the Codex steps; the steps
that active runs (`q/*.active`) have not finished are reserved, read from their `run.json`.
`--new` is the cost of the next item (default: the sum of `--costs`), `--week` the weekly
cost of one item (default 1.7). `TOPUP` admits one item anyway when nothing running spends
Codex, so a window is spent to 100 % rather than left unused. `--why` prints the arithmetic.
Exit 1 means wait.

`--reset` is the queue's `stall` hook: it prints the epoch of the fullest Codex window's
reset. The queue exports the stalled step as `$STEP` (the default of `--step`); a step the
same `--costs` does not price stalled on another vendor, whose reset is unknown, so `--reset`
exits 1 and the queue falls back to its own short wait and retries.

Typical queue hooks:

```yaml
hooks:
  admission: cd "$RUNS_DIR/../.." && .agents/skills/orca-orchestration/bin/adapter budget --costs author=7.5,fix1=3.5 --runs-dir "$RUNS_DIR"
  stall: cd "$RUNS_DIR/../.." && .agents/skills/orca-orchestration/bin/adapter budget --reset --costs author=7.5,fix1=3.5
```

## Cost: tokens per session, item and step

`cost` reads the vendors' own session logs and prints one row per worker session:

| Column   | Meaning                                                                              |
| -------- | ------------------------------------------------------------------------------------ |
| `item`   | the run item the session worked on (`1.3a`, `quiz-2-3`), from the Task text          |
| `step`   | `author`, `review1`, `fix2`, `write`, `improve` …, from the Task text                 |
| `calls`  | model calls                                                                          |
| `ctx`    | context of the last call (input + cache): the number to keep near 150k               |
| `fresh`  | input and cache-creation tokens over all calls: what was newly read                  |
| `cached` | cache-read tokens over all calls                                                     |
| `out`    | output tokens                                                                        |
| `window` | the session's share of the vendor's 5-hour window, when the log says (Codex)         |

Claude sessions come from `~/.claude/projects/<worktree path, non-alphanumerics as ->/`
(each subagent a session forked is a row under it); Codex sessions from
`~/.codex/sessions/`. `--worktree` (repeatable) keeps only the sessions of those worktrees,
`--hours` how far back to look. The item and step come from the launch ledger: Orca's
preamble in the worker's first message names the task (`Your task ID is: task_…`), the ledger
has that task's item and step, so the Task text may say anything. A session older than the
ledger falls back to the Task text's `unit <id> …, step <name>` or `<pass> chunk <id>, step
<name>`. `--write` records the rows into `<runs-dir>/<item>/cost.json` (merged by step), so
the next guide's `--costs` are read off the last one's `window` column.

## A worker that is stuck: the playbook by hand

No adapter command; these are the Orca calls, in order, for a worker `wait` cannot settle
(a usage limit it never wakes from, a worker that finished on disk but never reported):

1. Look: `orca orchestration dispatch-show --task <id> --json` (state, `assignee_handle`),
   `orca terminal read --terminal <h> --screen` (what the screen says), and the files the role was to
   write (the report in `.task/reports/`, the Bites).
2. **Finished on disk, never reported**: `orca orchestration worker-abandon --dispatch <id>`
   fences the worker, then `task-update --task <id> --status completed`; the workflow's next
   step reads the disk, not the report. `task-update` refuses `completed`/`failed` while a
   supervised dispatch is active, so abandon first.
3. **Not finished**: `worker-stop --dispatch <id>`, `task-update --task <id> --status failed`,
   and `retry --step <that step>` (or the queue's `--resume <item> --step`), with a
   `--fallback` launch when the limit is the reason.
4. In both cases close the terminal, `orca terminal close --terminal <h>`: a stalled terminal
   left open wakes after the reset and works in parallel with its replacement. A retained
   worker (`ownership_transferred`, `user_takeover`) answers `worker-release` with `state:
   retained` and the reason, and `adapter close --worktree` keeps it too, naming it; `terminal
   close` by hand, or `close --worktree --all` for every terminal of the slot, is the way out
   once you have looked at it. Orca 1.4.229 accounting, as `worker-list --run` shows it: a
   Codex worker's terminal is `active` while it runs and `reclaimable` once its dispatch
   completed (that dispatch's `worker-release` frees it); a follow-up's dispatch is
   context-only and always `retained`; a claude-route terminal is `retained` with
   `external_terminal` because the adapter created it, so only `terminal close` frees it.
