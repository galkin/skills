# Development notes

For whoever changes the runner or the adapter. Using them needs none of this.

## Layout

`runner/` (resolve, conditions, outputs, spec, engine, queue, cli), `adapter/` (orca wrapper,
cli, budget, cost), `actions/commit.sh`, `schemas/dag.schema.json`, `tests/`, `bin/runner` and `bin/adapter` (the
same entry with inline script metadata for `uv run --script`, which may download wheels).

## Tests

```sh
cd .agents/skills/orca-orchestration
uv run --no-project --python 3.11 --with pyyaml --with jsonschema --with pytest python -m pytest -q tests
```

Runner tests are built from the Dagu spec examples; adapter tests run against
`tests/fake_orca.py` (`ORCA_CLI_COMMAND` points at it; it keeps state in `$FAKE_ORCA_STATE`,
logs every call to `$FAKE_ORCA_LOG`, completes tasks after `$FAKE_ORCA_AUTOCOMPLETE` polls,
runs `$FAKE_ORCA_ON_START` in the worker's worktree on `worker-start` so a whole workflow can
be tried without a vendor, answers `runtime_unavailable` for as many calls as the file named
by `$FAKE_ORCA_DOWN` counts down, and refuses `worker-release` for the dispatches in its
state's `retained` list); `tests/test_actions.py` drives `commit.sh` on temporary git
repositories. Add `--offline` when the machine must not reach the network.

To try a real workflow file end to end without Orca: a scratch git repository with the
project's workflow files, role files and `.task/`, a `git worktree` as the slot, stubs for the
project's check commands on `PATH`, the fake Orca as `ORCA_CLI_COMMAND`, and `runner queue`
on a one-item queue file.

## Choices

- Commands run under POSIX `sh -c` (`RUNNER_SHELL` overrides), a deliberate deviation from
  Dagu's `$SHELL`: zsh does not word-split `$VAR`, and a workflow must behave the same on
  every machine.
- The schema is Dagu 2.21.0's, hand-trimmed to the subset: every step needs an `id`, params
  take the rich list form only, no `action:`, `additionalProperties: false` throughout. The
  schema is the definition of the subset; `workflow-syntax.md` follows it.
- The queue keeps one slot process per worktree on purpose: the coordinator sleeps; a held
  item is the only thing that wakes it. The mailbox drainer is started by the coordinator,
  not by the queue, so the runner never knows the adapter exists.
- A retried step keeps its attempt history; the new attempt gets the next log number.
- The adapter reads the vendors' own logs for budget and cost instead of asking the vendors:
  nothing needs a credential, and a renamed field degrades to "no data", not a crash.
- The adapter reads four of the runner's exports by their Dagu names and nothing else of the
  runner: `DAG_PARAMS_JSON` and the process environment for `--spec-template`, `DAG_RUN_ID`
  and `DAG_RUN_STEP_NAME` for the ledger's item and step, `DAG_RUN_WORK_DIR` for the runs dir.
  Renaming an export in `engine.py` means changing `cli.py`/`ledger.py` too; both say so.

## Orca receipt shapes (verified on 1.4.229)

- `worker-start` for codex: `stage`, `task.id`, `dispatch.id`, `launch`; no terminal handle.
- `worker-start --terminal` for claude: `taskId`, `dispatchId`, `runId`, `stage`, `state`, `launch`, `setup`, `effects`.
- `dispatch-show --task`: `dispatch.id`, `dispatch.assignee_handle`, `dispatch.status`.
- `terminal list`: `terminals[].handle`, `worktreePath`, `title`; `terminal read`: `terminal.tail`.
- `task-list`: `tasks[].id`, `status`.

`adapter/orca.py` reads every receipt tolerantly (`find` over several candidate names), so a
renamed field degrades to a lookup, not a crash.

## Vendor log shapes (verified 2026-10)

- Codex rollout `~/.codex/sessions/<y>/<m>/<d>/rollout-*.jsonl`: a `session_meta` line with
  `payload.cwd`; user messages as `payload.type: message, role: user, content[].text` (the
  first is `<user_instructions>`, the Task comes later); `payload.type: token_count` with
  `info.total_token_usage` (`input_tokens`, `cached_input_tokens`, `output_tokens`),
  `info.last_token_usage` and `rate_limits.primary|secondary` (`used_percent`, `resets_at`).
- Claude session `~/.claude/projects/<path with non-alphanumerics as ->/<session>.jsonl`:
  `type: user` with `message.content` (string or `[{text}]`); `type: assistant` with
  `message.id` and `message.usage` (`input_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `output_tokens`), one line per content block of the same message.
  No rate limits: those reach only the status line, as `rate_limits.five_hour|seven_day`
  (`used_percentage`, `resets_at`).
