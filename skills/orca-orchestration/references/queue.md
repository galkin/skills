# The queue

One `runner queue <q.yaml> --slot <worktree>` process per slot works through the items of a
queue file. The old `slot.sh` rules, without any knowledge of what an item is.

## Queue file

```yaml
workflow: ../../docs/pipeline/bites.yaml   # relative to this file
slot_param: worktree                  # the workflow param that receives the slot path
params:                               # shared by every item
  main: /abs/integration-worktree
  run: run_xxxxxxxxxxxx
items:
  - { id: 1.3a, group: "1.3", params: { unit: 1.3a } }
  - { id: 1.3b, group: "1.3", params: { unit: 1.3b } }
last_group: "0"                       # optional: these items wait for everything else
stall_exit_code: 5                    # optional: a step exit code that means "usage limit"
working_dir: ../..                    # optional: where the hooks run, relative to this file
env:                                  # optional: what the hooks see besides the process environment
  ADAPTER: .agents/skills/orca-orchestration/bin/adapter
hooks:                                # optional shell commands
  admission: $ADAPTER budget --costs author=7.5 --runs-dir "$RUNS_DIR"   # exit 0 admits; stdout says why not
  before: <command>                   # runs before each item, e.g. reset the slot branch
  stall: $ADAPTER budget --reset --costs author=7.5   # prints a Unix time to wait for; gets STEP, the step that stalled
```

The run id of an item is its `id`; its workflow params are `params` merged over the shared
ones plus `slot_param`. Hooks run in `working_dir` (default: the slot process's cwd) with
`env` merged over the process environment, and get `SLOT`, `RUNS_DIR`, `QUEUE`, `ITEM`,
`GROUP`, `RUN_DIR` (and `STEP` for `stall`), which win over `env`. `working_dir` and `env` are
the scheduler's settings, not Dagu workflow fields: the workflow has its own.

## Rules

- Every item's params are validated against the workflow when the slot starts, before any
  hook runs; a bad item refuses the whole queue (exit 2, naming the item) rather than holding
  it ten items later.
- An item is picked only when nothing of its `group` is active or held and every earlier item
  of the group is done. `group` is data, not derived from the id.
- `admission` runs before each pick; a non-zero exit idles the slot (polling every
  `--poll-sec`, default 60 s) instead of failing mid-item. Typical use: a vendor budget check.
- `before` runs in the slot before each item; a failure holds the item.
- A run whose failed step exited with `stall_exit_code` is not held: `stall` (with the step in
  `STEP`) prints an epoch, the slot sleeps until one minute past it, then retries the run from
  that step. A hook that fails or prints no epoch means a 14-minute wait, then the retry.
- Any other failure holds the item (`<id>.held` with the reason, `HELD` in the log) and the
  slot process exits 2. That exit is what wakes the coordinator.
- `--resume <id> [--step <s>]` continues a held item first (retrying from `<s>` and its
  descendants), then the slot goes on with the queue.
- An item whose `<runs dir>/<id>/run.json` already exists (a run started by hand with
  `runner run`, or left by a slot that died) is adopted: its failed, canceled and not-started
  steps run again with the run's own params, the succeeded ones stay, and the `before` hook
  is skipped since the run already owns its worktree.
- `touch <runs dir>/q/retire-<slot name>` retires a slot once it is idle (exit 0).

## States and exit codes

Item state is a file in `<runs dir>/q/`: `<id>.active` (holds the slot name), `<id>.held`
(the reason: `step <id> exit <code>, attempt <n>, log <path>`), `<id>.done`. `runner queue
<q.yaml> --status` lists them with the reason, and `runner status --run-id <id>` names the
failed step's log on its line, so one command says what to read.

| Exit | Meaning                               |
| ---- | ------------------------------------- |
| 0    | queue empty, or this slot was retired |
| 2    | an item is held                       |
| 7    | only held items remain                |
