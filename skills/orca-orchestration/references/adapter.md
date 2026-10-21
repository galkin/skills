# The adapter

`bin/adapter <command>` from the skill folder (a uv script, no extra dependencies); a workflow
or a queue hook reaches it by path, `.agents/skills/orca-orchestration/bin/adapter`. It calls `$ORCA_CLI_COMMAND` when set, else `orca`.
A workflow step calls it through `run:`; outputs are appended to `$DAGU_OUTPUT_FILE`, so the
step declares them as `outputs`. `--help` on any command lists its flags.

## Contents

- Commands
- Exit codes
- Launch routes and the fallback launch
- The launch ledger
- Budget: the Codex usage windows
- Cost: tokens per session, item and step
- A worker that is stuck: the playbook by hand

## Commands

| Command                                                                                         | Does                                                                                                                                                        | Outputs                      |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `run --run R --worktree W --launch vendor:model:effort [--fallback vendor:model:effort] --role <role> --title T (--spec … \| --spec-file … \| --spec-template …)… [--reuse-task <id>] [--language <name>]` | Starts a supervised worker in the role. The spec is the `--spec` texts and files joined in order: `--spec-file` literal, `--spec-template` with `${params.x}` (from `DAG_PARAMS_JSON`) and `${env.X}` resolved, an unresolved one refused, `\${…}` literal. With `--reuse-task`, when that task's terminal is still alive the spec is injected there as a follow-up instead of a fresh worker. `--language` sets the Claude session's output language through `--settings`; Codex takes it from the role body. | `task=`, `dispatch=`, `handle=` |
| `wait --run R --task <id> [--handle H] [--poll-sec 60] [--stall-every 5] [--max-reprompts 8] [--runtime-wait 30]` | Polls the task until it settles. A usage limit on the screen at the start gets one wake-up; one found later exits 5. Provider errors (429, capacity, 5xx) re-prompt after 1, 2, 4 … 32 min. While Orca itself is down (`runtime_unavailable`: a restart, a power cut) it keeps polling for `--runtime-wait` minutes, then exits 1 as for any Orca error. `--handle` may be empty; it is looked up from the task. | `status=`                    |
| `followup --run R --handle H --title T (--spec …)…`                                             | A new task injected into a live terminal.                                                                                                                   | `task=`, `dispatch=`, `handle=` |
| `handle --task <id>`                                                                            | Prints the task's terminal handle.                                                                                                                          |                              |
| `alive --handle H`                                                                              | Exit 0 when the terminal is listed.                                                                                                                         |                              |
| `unstall [--worktree W] [--exclude <coordinator worktree>]`                                     | Wakes every terminal whose screen still shows a limit (answers Codex's model menu, sends "continue").                                                        |                              |
| `drain --run R [--once] [--repeat-sec 300]`, `drain --run R --ack <msg id> [--body T]` | Consumes heartbeat and worker_done batches so Orca never nudges the coordinator, and keeps every question and escalation of the run in view: one `ATTENTION <msg id> <type> from <sender> [task <id>] age <n>m \| <subject> \| <body>` line per open message, all of them again whenever a new one arrives and at least every `--repeat-sec`, until its thread holds a reply from someone other than its sender. The run's inbox is the record (so a question that came while no drain ran is found too); a batch holding a question is acked only once the inbox shows it, and stays unacked (replayed) while Orca cannot say so. It keeps running past a question; `--once` makes one round and exits 3 while anything is open. `--ack` answers a message that needs no words with a reply in its thread (default body "Acknowledged by the coordinator."). The coordinator runs it detached. **Only beside a running queue**: it consumes `worker_done` silently, so completion is seen in `slots.log` alone. Workers outside a queue are supervised with Orca's own `orchestration check --wait` and its acks, never `drain`. |  |
| `close --worktree W [--all]`                                                                    | Frees the worktree's terminals the adapter started (the launch ledger) whose last task has settled: `worker-release` on the dispatch `worker-start` returned for a Codex terminal, `terminal close` for a claude-route terminal (Orca calls it `external_terminal` and never owns it). Keeps and names the ones still running, the ones Orca keeps for the user (`user_takeover`, `ownership_transferred`) and the ones it did not start; exit 0 either way (the work is merged by the time a workflow closes). `--all` closes every terminal of the worktree, the playbook's last resort. |  |
| `release --task <id>`                                                                           | `worker-release` for a settled task; exit 1 with Orca's reason when it refuses (retained, not settled).                                                     |                              |
| `budget [--costs step=pct,…] [--new pct] [--week pct] [--margin pct] [--runs-dir D] [--reset] [--why]` | Admission by the Codex usage windows; see Budget.                                                                                                   |                              |
| `cost [--worktree W]… [--hours 12] [--runs-dir D] [--json] [--write]`                           | Tokens per worker session, by item and step, from the vendors' session logs; see Cost.                                                                     |                              |

## Exit codes

| Exit | Meaning                                                        |
| ---- | -------------------------------------------------------------- |
| 0    | ok (`wait`: the task completed)                                |
| 1    | other failure                                                  |
| 3    | `drain --once`: a question or escalation is unanswered          |
| 4    | `wait`: the task ended badly (failed, canceled, released)      |
| 5    | the agent sits on a usage limit (`wait`, `unstall`)            |
| 6    | `wait`: provider errors persisted through every re-prompt      |

A workflow maps 5 to the queue's `stall_exit_code`, so a stalled wait is resumed after the
reset rather than held.

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
