"""Execution of one workflow run with file-backed state.

Semantics follow the Dagu specs the subset was taken from: step run (013), outputs
(012), preconditions (023), repeat (075), continue_on and retry (docs). Steps execute
one at a time in dependency order; a step is eligible when every dependency reached a
status its ``continue_on`` lets dependents start from.

Commands run under ``sh -c`` (POSIX; ``$RUNNER_SHELL`` overrides), not ``$SHELL`` as Dagu's
platform fallback does: a workflow must behave the same on every machine, and zsh, for one, does
not word-split ``$VAR``.

State lives in ``<runs_dir>/<run_id>/``: ``run.json`` (rewritten atomically after every
change), ``run.log`` (the timeline), ``steps/<id>.<attempt>.log`` (stdout+stderr) and
``steps/<id>.<attempt>.out`` (the attempt's ``DAGU_OUTPUT_FILE``). Everything is plain
text, readable without the runner.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .conditions import EvalError
from .outputs import OutputError, parse_output_file
from .resolve import Scope, resolve
from .spec import Dag, Handler, Step, topological

# Step statuses (Dagu names): not_started, running, succeeded, failed, skipped, canceled.
# Run statuses: running, succeeded, partially_succeeded, failed.


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Attempt:
    n: int
    exit_code: int | None = None
    started: str = ""
    finished: str = ""
    log: str = ""
    error: str = ""


@dataclass
class StepState:
    status: str = "not_started"
    attempts: list[Attempt] = field(default_factory=list)
    executions: int = 0  # repeat executions (each may carry retries)
    outputs: dict[str, str] = field(default_factory=dict)
    continued: bool = False  # failed/skipped but continue_on lets dependents run
    error: str = ""
    started: str = ""
    finished: str = ""

    @property
    def exit_code(self) -> int | None:
        return self.attempts[-1].exit_code if self.attempts else None


@dataclass
class RunState:
    run_id: str
    dag: str
    workflow: str
    params: dict[str, str]
    status: str = "running"
    started: str = ""
    finished: str = ""
    steps: dict[str, StepState] = field(default_factory=dict)
    handlers: dict[str, dict] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "run_id": self.run_id,
            "dag": self.dag,
            "workflow": self.workflow,
            "params": self.params,
            "status": self.status,
            "started": self.started,
            "finished": self.finished,
            "steps": {
                sid: {
                    "status": st.status,
                    "exit_code": st.exit_code,
                    "executions": st.executions,
                    "attempts": [a.__dict__ for a in st.attempts],
                    "outputs": st.outputs,
                    "continued": st.continued,
                    "error": st.error,
                    "started": st.started,
                    "finished": st.finished,
                }
                for sid, st in self.steps.items()
            },
            "handlers": self.handlers,
        }

    @classmethod
    def from_json(cls, d: dict) -> "RunState":
        rs = cls(d["run_id"], d["dag"], d["workflow"], d["params"], d["status"], d["started"], d["finished"])
        for sid, s in d["steps"].items():
            st = StepState(
                status=s["status"],
                attempts=[Attempt(**a) for a in s["attempts"]],
                executions=s.get("executions", 0),
                outputs=s["outputs"],
                continued=s["continued"],
                error=s["error"],
                started=s["started"],
                finished=s["finished"],
            )
            rs.steps[sid] = st
        rs.handlers = d.get("handlers", {})
        return rs


class Runner:
    def __init__(self, dag: Dag, params: dict[str, str], run_dir: Path, run_id: str, state: RunState | None = None):
        self.dag = dag
        self.params = params
        self.run_dir = run_dir
        self.run_id = run_id
        self.shell = [os.environ.get("RUNNER_SHELL") or "sh", "-c"]
        self.state = state or RunState(run_id, dag.name, dag.path, params, started=now())
        for s in dag.steps:
            self.state.steps.setdefault(s.id, StepState())
        (run_dir / "steps").mkdir(parents=True, exist_ok=True)
        self.log_file = run_dir / "run.log"
        self.dag_dir = str(Path(dag.path).resolve().parent)
        self.base_env = dict(os.environ)
        self.base_env.update(
            {
                "DAG_NAME": dag.name,
                "DAG_RUN_ID": run_id,
                "DAG_RUN_LOG_FILE": str(self.log_file),
                "DAG_RUN_WORK_DIR": str(run_dir),
                "DAG_PARAMS_JSON": json.dumps(params, sort_keys=True),
            }
        )

    # ----- state and logging -------------------------------------------------

    def log(self, msg: str) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save(self) -> None:
        data = json.dumps(self.state.to_json(), indent=2, sort_keys=False)
        fd, tmp = tempfile.mkstemp(dir=self.run_dir, prefix=".run.", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, self.run_dir / "run.json")

    # ----- scopes ------------------------------------------------------------

    def scope(self, steps_available: bool = True) -> Scope:
        outputs = {sid: st.outputs for sid, st in self.state.steps.items() if st.status == "succeeded"}
        return Scope(params=self.params, env=self.dag_env(), steps=outputs, steps_available=steps_available)

    def dag_env(self) -> dict[str, str]:
        env = dict(self.base_env)
        scope = Scope(params=self.params, env=env, steps={}, steps_available=False)
        for k, v in self.dag.env:
            env[k] = resolve(v, scope)
            scope.env = env
        return env

    def step_env(self, step: Step, attempt_dir: Path, attempt: int) -> tuple[dict[str, str], Scope]:
        env = self.dag_env()
        scope = self.scope()
        scope.env = env
        for k, v in step.env:
            env[k] = resolve(v, scope)
        env["DAGU_OUTPUT_FILE"] = str(attempt_dir / f"{step.id}.{attempt}.out")
        env["DAG_RUN_STEP_NAME"] = step.id
        env["DAG_RUN_STEP_LOG_FILE"] = str(attempt_dir / f"{step.id}.{attempt}.log")
        return env, scope

    def working_dir(self, step_dir: str | None, scope: Scope) -> str:
        base = self.dag.working_dir
        if base is not None:
            base = resolve(base, scope)
            base = base if os.path.isabs(base) else os.path.join(self.dag_dir, base)
        else:
            base = os.getcwd()
        if step_dir is None:
            return base
        d = resolve(step_dir, scope)
        return d if os.path.isabs(d) else os.path.join(base, d)

    # ----- the run -----------------------------------------------------------

    def execute(self) -> str:
        self.state.status = "running"
        self.state.finished = ""
        self.save()
        self.log(f"run {self.run_id} {self.dag.name} params={json.dumps(self.params, sort_keys=True)}")
        deadline = time.monotonic() + self.dag.timeout_sec if self.dag.timeout_sec else None
        for step in topological(self.dag.steps):
            st = self.state.steps[step.id]
            if st.status in ("succeeded", "skipped") or (st.status == "failed" and st.continued):
                continue  # kept from a previous run (retry)
            if not self.eligible(step):
                st.status = "canceled"
                st.error = "a dependency did not succeed"
                self.log(f"step {step.id} canceled")
                self.save()
                continue
            if deadline is not None and time.monotonic() > deadline:
                st.status = "canceled"
                st.error = "DAG timeout"
                self.log(f"step {step.id} canceled (DAG timeout)")
                self.save()
                continue
            self.run_step(step, deadline)
        self.finish()
        return self.state.status

    def eligible(self, step: Step) -> bool:
        for dep_id in step.all_depends:
            dep = self.state.steps[dep_id]
            if dep.status == "succeeded":
                continue
            if dep.status in ("failed", "skipped") and dep.continued:
                continue
            return False
        return True

    def finish(self) -> None:
        statuses = self.state.steps.values()
        if any(s.status == "failed" and not s.continued for s in statuses) or any(s.status == "canceled" for s in statuses):
            status = "failed"
        elif any(s.status == "failed" for s in statuses):
            status = "partially_succeeded"
        else:
            status = "succeeded"
        self.state.status = status
        self.state.finished = now()
        self.save()
        self.log(f"run {self.run_id} {status}")
        handlers = self.dag.handlers
        event = "failure" if status == "failed" else "success"
        if event in handlers:
            self.run_handler(event, handlers[event])
        if "exit" in handlers:
            self.run_handler("exit", handlers["exit"])

    def run_handler(self, name: str, h: Handler) -> None:
        scope = self.scope(steps_available=False)
        env = scope.env
        for k, v in h.env:
            env[k] = resolve(v, scope)
        env["DAG_RUN_STATUS"] = self.state.status
        cwd = self.working_dir(h.working_dir, scope)
        log = self.run_dir / "steps" / f"handler_{name}.log"
        code = self.spawn(resolve(h.run, scope), env, cwd, log, h.timeout_sec)
        self.state.handlers[name] = {"exit_code": code, "log": str(log), "finished": now()}
        self.log(f"handler {name} exit {code}")
        self.save()

    # ----- one step ----------------------------------------------------------

    def run_step(self, step: Step, deadline: float | None) -> None:
        st = self.state.steps[step.id]
        st.status = "running"
        st.started = now()
        st.error = ""
        self.save()
        steps_dir = self.run_dir / "steps"
        scope = self.scope()
        env = self.dag_env()
        scope.env = env
        for k, v in step.env:
            env[k] = resolve(v, scope)
        cwd = self.working_dir(step.working_dir, scope)

        # Preconditions: once, before retries and repeats.
        try:
            for c in step.preconditions:
                if not c.check(scope, env, cwd, self.shell):
                    st.status = "skipped"
                    st.continued = step.continue_on.skipped
                    st.finished = now()
                    self.log(f"step {step.id} skipped (precondition not met: {c.condition!r})")
                    self.save()
                    return
        except EvalError as e:
            self.fail(step, st, f"precondition evaluation error: {e}")
            return

        repeat = step.repeat
        delay = repeat.interval_sec if repeat else 0.0
        while True:
            ok = self.run_with_retries(step, st, steps_dir, deadline)
            st.executions += 1
            if not repeat:
                break
            if repeat.limit is not None and st.executions >= repeat.limit:
                break
            try:
                again = self.repeat_decision(step, st, ok, env, cwd)
            except EvalError as e:
                self.fail(step, st, f"repeat condition evaluation error: {e}")
                return
            if not again:
                break
            self.log(f"step {step.id} repeats in {delay:g}s (execution {st.executions})")
            time.sleep(delay)
            delay = _grow(delay, repeat.backoff, repeat.max_interval_sec)

        if ok:
            st.status = "succeeded"
            st.finished = now()
            self.log(f"step {step.id} succeeded")
            self.save()
        else:
            self.fail(step, st, st.error or f"exit code {st.exit_code}")

    def repeat_decision(self, step: Step, st: StepState, ok: bool, env: dict[str, str], cwd: str) -> bool:
        policy = step.repeat
        assert policy is not None
        if policy.condition is None:
            met = ok
        else:
            scope = self.scope()
            scope.env = env
            scope.steps[step.id] = st.outputs  # the step may read what it just published
            met = policy.condition.check(scope, env, cwd, self.shell)
        return met if policy.repeat == "while" else not met

    def run_with_retries(self, step: Step, st: StepState, steps_dir: Path, deadline: float | None) -> bool:
        policy = step.retry
        retries = 0
        delay = policy.interval_sec
        while True:
            ok = self.attempt(step, st, steps_dir, deadline)
            if ok:
                return True
            code = st.exit_code
            retryable = policy.exit_code is None or code in policy.exit_code
            if retries < policy.limit and retryable and code != 124:
                retries += 1
                self.log(f"step {step.id} failed (exit {code}); retry {retries}/{policy.limit} in {delay:g}s")
                time.sleep(delay)
                delay = _grow(delay, policy.backoff, policy.max_interval_sec)
                continue
            return False

    def attempt(self, step: Step, st: StepState, steps_dir: Path, deadline: float | None) -> bool:
        n = len(st.attempts) + 1
        a = Attempt(n=n, started=now(), log=str(steps_dir / f"{step.id}.{n}.log"))
        st.attempts.append(a)
        env, scope = self.step_env(step, steps_dir, n)
        cwd = self.working_dir(step.working_dir, scope)
        out_file = env["DAGU_OUTPUT_FILE"]
        open(out_file, "w").close()  # a fresh, empty output file per attempt (spec 012)
        timeout = step.timeout_sec
        if deadline is not None:
            left = max(0.0, deadline - time.monotonic())
            timeout = left if timeout is None else min(timeout, left)
        self.log(f"step {step.id} attempt {n}: {step.run[0][:80]!r}" + (" …" if len(step.run) > 1 else ""))
        self.save()
        code = 0
        for command in step.run:
            code = self.spawn(resolve(command, scope), env, cwd, Path(a.log), timeout)
            if code != 0:
                break
        a.exit_code = code
        a.finished = now()
        if code != 0:
            a.error = "timeout" if code == 124 else f"exit code {code}"
            st.error = a.error
            self.save()
            return False
        try:
            st.outputs = parse_output_file(out_file, step.outputs)
        except OutputError as e:
            a.error = f"output parsing failed: {e}"
            a.exit_code = 1
            st.error = a.error
            self.save()
            return False
        st.error = ""
        self.save()
        return True

    def fail(self, step: Step, st: StepState, error: str) -> None:
        st.status = "failed"
        st.error = error
        st.finished = now()
        co = step.continue_on
        code = st.exit_code
        st.continued = co.failure or (code in co.exit_code) or self.output_matches(step, st, co.output)
        if st.continued and co.mark_success:
            st.status = "succeeded"
        self.log(f"step {step.id} {st.status}: {error}" + (" (continue_on)" if st.continued else ""))
        self.save()

    def output_matches(self, step: Step, st: StepState, patterns: list[str]) -> bool:
        if not patterns or not st.attempts:
            return False
        try:
            text = Path(st.attempts[-1].log).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        for line in text.split("\n"):
            for pat in patterns:
                if pat.startswith("re:"):
                    if re.search(pat[3:], line):
                        return True
                elif pat in line:
                    return True
        return False

    # ----- processes ---------------------------------------------------------

    def spawn(self, command: str, env: dict[str, str], cwd: str, log: Path, timeout: float | None) -> int:
        with open(log, "ab") as logf:
            try:
                proc = subprocess.Popen(
                    self.shell + [command],
                    env=env,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as e:
                logf.write(f"runner: cannot start: {e}\n".encode())
                return 127
            try:
                return proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                logf.write(b"runner: timeout, process tree terminated\n")
                return 124


def _grow(delay: float, backoff: float, cap: float | None) -> float:
    delay = delay * backoff if backoff > 1 else delay
    return min(delay, cap) if cap is not None else delay


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, PermissionError):
        return
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


# ----- entry points used by the CLI ------------------------------------------


def start(dag: Dag, params: dict[str, str], runs_dir: Path, run_id: str) -> str:
    run_dir = runs_dir / run_id
    if (run_dir / "run.json").exists():
        raise FileExistsError(f"run {run_id!r} already exists in {runs_dir}; use retry or another --run-id")
    runner = Runner(dag, params, run_dir, run_id)
    return runner.execute()


def load_state(runs_dir: Path, run_id: str) -> RunState:
    with open(runs_dir / run_id / "run.json", encoding="utf-8") as f:
        return RunState.from_json(json.load(f))


def retry(dag: Dag, runs_dir: Path, run_id: str, step_id: str | None, downstream: bool) -> str:
    state = load_state(runs_dir, run_id)
    if step_id is None:
        targets = [sid for sid, st in state.steps.items() if st.status in ("failed", "canceled", "not_started", "running")]
    else:
        dag.step(step_id)  # KeyError for an unknown step
        targets = [step_id] + (dag.descendants(step_id) if downstream else [])
    # Reset the status but keep the attempt history, so the next attempt gets a new number
    # and a fresh log file instead of appending to the failed one.
    for sid in targets:
        state.steps[sid] = StepState(attempts=state.steps[sid].attempts)
    # Steps that were canceled only because a target failed get another chance too.
    for sid, st in state.steps.items():
        if st.status == "canceled":
            state.steps[sid] = StepState(attempts=st.attempts)
    runner = Runner(dag, state.params, runs_dir / run_id, run_id, state)
    runner.log(f"retry {run_id} steps={','.join(targets) or '-'}")
    return runner.execute()


def exec_step(dag: Dag, runs_dir: Path, run_id: str, step_id: str, extra_env: dict[str, str]) -> int:
    """Run one step's commands once, outside the run, exactly as the run would run them.

    The run's params, the outputs of its succeeded steps, the DAG and step environment and
    the step's working directory, with ``extra_env`` over all of them. Preconditions, retries
    and repeats do not apply and ``run.json`` is not touched: this is how a coordinator runs a
    step's own checks on a slot it edited by hand (``CHECK_ONLY=1`` on a commit step) before
    resuming the run. The log is ``steps/<step>.exec.<n>.log`` and is echoed to stdout; the
    exit code is the command's.
    """
    step = dag.step(step_id)
    state = load_state(runs_dir, run_id)
    run_dir = runs_dir / run_id
    runner = Runner(dag, state.params, run_dir, run_id, state)
    steps_dir = run_dir / "steps"
    n = 1
    while (steps_dir / f"{step.id}.exec.{n}.log").exists():
        n += 1
    log = steps_dir / f"{step.id}.exec.{n}.log"
    env, scope = runner.step_env(step, steps_dir, n)
    env["DAGU_OUTPUT_FILE"] = str(steps_dir / f"{step.id}.exec.{n}.out")  # never the run's own attempt files
    env["DAG_RUN_STEP_LOG_FILE"] = str(log)
    env.update(extra_env)
    open(env["DAGU_OUTPUT_FILE"], "w").close()
    cwd = runner.working_dir(step.working_dir, scope)
    code = 0
    for command in step.run:
        code = runner.spawn(resolve(command, scope), env, cwd, log, step.timeout_sec)
        if code != 0:
            break
    runner.log(f"exec {step.id} ({' '.join(f'{k}={v}' for k, v in extra_env.items()) or 'no extra env'}) exit {code}, log {log}")
    print(log.read_text(encoding="utf-8", errors="replace"), end="")
    return code


def status_text(state: RunState, runs_dir: Path | None = None) -> str:
    """One line per step; a failed step also names its last attempt's log when ``runs_dir`` is given."""
    lines = [f"{state.run_id}  {state.status}  dag={state.dag}  params={json.dumps(state.params, sort_keys=True)}"]
    for sid, st in state.steps.items():
        extra = ""
        if st.exit_code is not None:
            extra += f" exit={st.exit_code}"
        if st.attempts:
            extra += f" attempts={len(st.attempts)}"
        if st.status == "failed" and st.attempts and runs_dir is not None:
            extra += f" log={runs_dir / state.run_id / 'steps' / f'{sid}.{len(st.attempts)}.log'}"
        if st.outputs:
            extra += " " + " ".join(f"{k}={v!r}" for k, v in st.outputs.items())
        if st.error and st.status != "succeeded":
            extra += f"  {st.error}"
        if st.continued:
            extra += " (continue_on)"
        lines.append(f"  {sid:<16}{st.status:<20}{extra}")
    return "\n".join(lines)
