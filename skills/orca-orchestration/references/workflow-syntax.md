# Workflow files: the Dagu subset (v1)

The schema is `schemas/dag.schema.json`; anything it does not list fails `runner validate`.
Field semantics follow Dagu's specs (`dagucloud/dagu`: 003/005/007 value resolution and inferred
dependencies, 012 outputs, 013 run forms, 023 preconditions, 075 repeat, the continue_on
reference). The Dagu binary is never involved.

## Contents

- DAG fields
- Step fields
- References
- Conditions (preconditions, repeat)
- Outputs
- continue_on, retry_policy, repeat_policy
- Statuses and the run outcome
- Pitfalls

## DAG fields

| Field         | Meaning                                                                                              |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| `name`        | Run name, exported as `DAG_NAME`.                                                                    |
| `description` | Free text.                                                                                           |
| `params`      | Ordered list of `{name, type: string\|integer\|boolean, default, required, enum, description}`. Values come from `--param k=v`, else `default`; unknown names, missing required ones and enum violations are rejected. |
| `env`         | Map `{KEY: value}` or list of `KEY=value`; values may use references. Merged over the process environment for every step. |
| `working_dir` | Relative to the workflow file. Every step runs there unless it sets its own.                         |
| `timeout_sec` | Whole-run timeout.                                                                                   |
| `handler_on`  | `success`, `failure`, `exit` (always runs last). Each is `{run, env, working_dir, timeout_sec}`, gets `DAG_RUN_STATUS`, and cannot read step outputs. |

## Step fields

| Field            | Meaning                                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------------------- |
| `id`             | Required, unique; `${steps.<id>.outputs.*}` and `depends` use it.                                    |
| `depends`        | One id or a list. References to another step's outputs add a dependency on it (inferred, printed by `validate`). |
| `run`            | Required. One line, a multi-line script, or a list of commands (stops at the first failure). Runs under POSIX `sh -c`. |
| `env`, `working_dir`, `timeout_sec` | As for the DAG, per step. Timeout gives exit 124.                                  |
| `description`    | Free text.                                                                                           |
| `outputs`        | Declared `[{name, type: string\|json}]`; see Outputs.                                                |
| `preconditions`  | A list of conditions, checked once before the first attempt; not met → `skipped`.                    |
| `continue_on`    | What counts as "continued" for dependents; see below.                                               |
| `retry_policy`   | `{limit, interval_sec, backoff, max_interval_sec, exit_code}`: retry on failure (only on the listed exit codes when `exit_code` is set). |
| `repeat_policy`  | `{repeat: while\|until, condition, expected, interval_sec, backoff, max_interval_sec, limit}`: rerun the step while/until the condition holds. |

Steps run one at a time in dependency order (no `max_active_steps`).

## References

`${params.x}`, `${env.X}` (the merged process, DAG and step environment) and
`${steps.<id>.outputs.<name>}`, resolved before the shell sees the text. `\${…}` is passed
through as literal `${…}`. Anything else (`$NAME`, `${NAME}`, `$(…)`) belongs to the shell.
An unresolvable reference is left as its literal text and noted in the log.

Each attempt also gets `DAGU_OUTPUT_FILE`, `DAG_NAME`, `DAG_RUN_ID`, `DAG_RUN_WORK_DIR`
(the run directory), `DAG_RUN_STEP_NAME`, `DAG_PARAMS_JSON`.

## Conditions

A condition is `{condition, expected, negate}`.

- With `expected`, `condition` is data (usually a reference) compared with `expected`:
  - a literal matches when any line of the value equals it;
  - `re:<pattern>` matches when any line matches;
  - `num:<op><number>` (`>`, `>=`, `<`, `<=`) compares the whole trimmed value as a number;
    the number may itself be one reference.
- Without `expected`, `condition` is a shell command; exit 0 means met.
- `negate: true` inverts the result.

A `num:` comparison of text that is not a number is an evaluation error and fails the step.

## Outputs

A step declares `outputs`; its command appends records to `$DAGU_OUTPUT_FILE`:

```sh
printf 'task=%s\n' "$id" >> "$DAGU_OUTPUT_FILE"
printf 'body<<EOF\n%s\nEOF\n' "$text" >> "$DAGU_OUTPUT_FILE"
```

The file is fresh and empty for every attempt. Records are published as
`${steps.<id>.outputs.<name>}` only when the attempt succeeds; undeclared names are ignored
with a notice; `type: json` must parse.

## continue_on, retry_policy, repeat_policy

`continue_on` decides whether dependents may start after this step did not succeed:
`skipped` / `failed` (string forms) or `{failure, skipped, exit_code: n | [n…], output: substring |
"re:…" | [...], mark_success}`. It is evaluated after retries. `mark_success: true` records the
step as succeeded. A step that was skipped by its preconditions needs `continue_on: skipped`
for its dependents to run.

`retry_policy` retries the same attempt on failure; `repeat_policy` reruns a succeeded step
(`while`: as long as the condition holds; `until`: until it holds), with `limit` and an
interval that may back off.

## Statuses and the run outcome

Step: `not_started | running | succeeded | failed | skipped | canceled`. A dependent is
eligible only when every dependency succeeded or was continued by its `continue_on`;
otherwise it is `canceled`. Run: `succeeded`, `partially_succeeded` (something failed but was
continued), `failed`. The `exit` handler runs in every case.

## Pitfalls

- A precondition on an output of a step that may be skipped sees the unresolved text
  `${steps.x.outputs.y}`. Compare it with `re:` (not met) rather than `num:` (evaluation error).
- An empty output used unquoted in `run` disappears from the argument list (`--handle ${…}`
  became `--handle --next-flag`). Quote references that may be empty.
- Commands run under `sh`, not the user's shell: no zsh or bash extensions.
- `working_dir: ../..` in `docs/pipeline/x.yaml` is the repository root, wherever the runner was started.
