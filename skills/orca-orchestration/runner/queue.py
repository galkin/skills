"""The queue: one slot working through a list of items, continuous mode (decision 7).

This is the old ``slot.sh`` with its rules kept and its knowledge of units removed:

* an item is picked only when nothing of its ``group`` is active or held and every
  earlier item of the group is done; ``last_group`` items wait for everything else;
* an optional ``admission`` hook (exit 0 admits, stdout says why not) runs before each
  pick, so a budget check can idle the slot between items instead of mid-item;
* a ``before`` hook runs in the slot before each item (reset the branch, say);
* a run whose failed step exited with ``stall_exit_code`` is not held: the ``stall``
  hook prints a Unix time to wait for, then the run is retried from the failed step;
* any other failure holds the item and ends the slot process, which is what wakes the
  coordinator; ``--resume <item> [--step <id>]`` continues a held item after a decision;
* ``touch <runs_dir>/q/retire-<slot name>`` retires a slot once it is idle.

Queue file (YAML)::

    workflow: docs/pipeline/bites.yaml
    slot_param: worktree          # the param that receives the slot path
    params: {verify: "off"}       # shared by every item
    items:
      - {id: 1.3a, group: "1.3", params: {unit: 1.3a}}
      - {id: 1.3b, group: "1.3", params: {unit: 1.3b}}
    last_group: "0"               # optional
    stall_exit_code: 5            # optional
    working_dir: ../..            # optional: where the hooks run, relative to this file
    env: {ADAPTER: bin/adapter}   # optional: what the hooks see; the runtime names below win
    hooks:                        # optional, each a shell command; env SLOT, ITEM, GROUP, RUN_DIR
      admission: $ADAPTER budget --costs author=7.5
      before: git -C "$SLOT" reset -q --hard main
      stall: $ADAPTER budget --reset  # gets STEP, the step that stalled

Every item's params are checked against the workflow when the slot starts, before any hook
runs, so a typo in the queue file is refused at once rather than ten items in.

Item state is a file in ``<runs_dir>/q/``: ``<id>.active`` (slot name), ``<id>.held``
(reason), ``<id>.done``; the run itself is ``<runs_dir>/<id>/`` as for ``runner run``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from . import engine
from .spec import SpecError, load, resolve_params


@dataclass
class Item:
    id: str
    group: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class QueueSpec:
    workflow: str
    slot_param: str | None
    params: dict[str, str]
    items: list[Item]
    last_group: str | None
    stall_exit_code: int | None
    hooks: dict[str, str]
    path: str
    working_dir: str | None = None
    env: dict[str, str] = field(default_factory=dict)


def load_queue(path: str) -> QueueSpec:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    allowed = {"workflow", "slot_param", "params", "items", "last_group", "stall_exit_code", "hooks", "working_dir", "env"}
    unknown = set(raw) - allowed
    if unknown:
        raise SpecError(f"{path}: unknown queue field(s): {', '.join(sorted(unknown))}")
    if "workflow" not in raw or "items" not in raw:
        raise SpecError(f"{path}: workflow and items are required")
    items = []
    for i, it in enumerate(raw["items"]):
        if not isinstance(it, dict) or "id" not in it:
            raise SpecError(f"{path}: items[{i}] needs an id")
        extra = set(it) - {"id", "group", "params"}
        if extra:
            raise SpecError(f"{path}: items[{i}] has unknown field(s): {', '.join(sorted(extra))}")
        items.append(Item(str(it["id"]), str(it.get("group", it["id"])), {k: str(v) for k, v in (it.get("params") or {}).items()}))
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise SpecError(f"{path}: duplicate item ids")
    hooks = raw.get("hooks") or {}
    bad = set(hooks) - {"admission", "before", "stall"}
    if bad:
        raise SpecError(f"{path}: unknown hook(s): {', '.join(sorted(bad))}")
    here = os.path.dirname(os.path.abspath(path))
    workflow = raw["workflow"]
    if not os.path.isabs(workflow):
        workflow = os.path.join(here, workflow)
    working_dir = raw.get("working_dir")
    if working_dir is not None:
        working_dir = str(working_dir)
        if not os.path.isabs(working_dir):
            working_dir = os.path.normpath(os.path.join(here, working_dir))
        if not os.path.isdir(working_dir):
            raise SpecError(f"{path}: working_dir {working_dir} is not a directory")
    env = raw.get("env") or {}
    if not isinstance(env, dict):
        raise SpecError(f"{path}: env must be a map")
    return QueueSpec(
        workflow=workflow,
        slot_param=raw.get("slot_param"),
        params={k: str(v) for k, v in (raw.get("params") or {}).items()},
        items=items,
        last_group=None if raw.get("last_group") is None else str(raw["last_group"]),
        stall_exit_code=raw.get("stall_exit_code"),
        hooks={k: str(v) for k, v in hooks.items()},
        path=path,
        working_dir=working_dir,
        env={str(k): str(v) for k, v in env.items()},
    )


# When the stall hook gives no time: a Codex 5-hour window is rarely further than this
# from its reset once a limit has been hit; the wait step re-checks the screen anyway.
STALL_FALLBACK_SEC = 14 * 60


class Slot:
    def __init__(self, q: QueueSpec, runs_dir: Path, slot: str, poll_sec: float = 60):
        self.q = q
        self.runs_dir = runs_dir
        self.slot = slot
        self.name = Path(slot).name
        self.poll = poll_sec
        self.stall_margin = 60  # seconds past the stall hook's time before resuming
        self.qdir = runs_dir / "q"
        self.qdir.mkdir(parents=True, exist_ok=True)
        self.dag = load(q.workflow)
        self.shell = [os.environ.get("RUNNER_SHELL") or "sh", "-c"]
        for it in q.items:  # every item's params, before the first hook runs
            try:
                self.item_params(it)
            except SpecError as e:
                raise SpecError(f"{q.path}: item {it.id}: {e}") from e

    # ----- logging and state files ---------------------------------------------

    def log(self, msg: str) -> None:
        line = f"{datetime.now().strftime('%H:%M')} slot {self.name} {msg}"
        print(line, flush=True)
        with open(self.runs_dir / "slots.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def state(self, item_id: str) -> str | None:
        for s in ("active", "held", "done"):
            if (self.qdir / f"{item_id}.{s}").exists():
                return s
        return None

    def set_state(self, item_id: str, state: str, text: str = "") -> None:
        for s in ("active", "held", "done"):
            try:
                (self.qdir / f"{item_id}.{s}").unlink()
            except FileNotFoundError:
                pass
        (self.qdir / f"{item_id}.{state}").write_text(text + "\n")

    def lock(self) -> None:
        while True:
            try:
                (self.qdir / ".lock").mkdir()
                return
            except FileExistsError:
                time.sleep(1)

    def unlock(self) -> None:
        try:
            (self.qdir / ".lock").rmdir()
        except FileNotFoundError:
            pass

    # ----- picking ---------------------------------------------------------------

    def pick(self) -> Item | None:
        states = {it.id: self.state(it.id) for it in self.q.items}
        busy_groups = {it.group for it in self.q.items if states[it.id] in ("active", "held")}
        for it in self.q.items:
            if states[it.id] is not None or it.group in busy_groups:
                continue
            earlier_same_group = [o for o in self.q.items[: self.q.items.index(it)] if o.group == it.group]
            if any(states[o.id] != "done" for o in earlier_same_group):
                continue
            if self.q.last_group is not None and it.group == self.q.last_group:
                others = [o for o in self.q.items if o.group != self.q.last_group]
                if any(states[o.id] != "done" for o in others):
                    continue
            self.set_state(it.id, "active", self.name)
            return it
        return None

    # ----- hooks -----------------------------------------------------------------

    def hook(self, name: str, item: Item | None = None, **extra: str) -> tuple[int, str]:
        cmd = self.q.hooks.get(name)
        if not cmd:
            return 0, ""
        env = dict(os.environ, **self.q.env)
        env.update(SLOT=self.slot, RUNS_DIR=str(self.runs_dir), QUEUE=self.q.path)  # the runtime names win over env:
        if item:
            env.update(ITEM=item.id, GROUP=item.group, RUN_DIR=str(self.runs_dir / item.id))
        env.update(extra)
        proc = subprocess.run(self.shell + [cmd], env=env, cwd=self.q.working_dir, capture_output=True, text=True)
        return proc.returncode, (proc.stdout.strip() or proc.stderr.strip())

    # ----- one item --------------------------------------------------------------

    def item_params(self, item: Item) -> dict[str, str]:
        params = dict(self.q.params)
        params.update(item.params)
        if self.q.slot_param:
            params[self.q.slot_param] = self.slot
        return resolve_params(self.dag, params)

    def run_item(self, item: Item, resume_step: str | None = None, fresh: bool = True) -> bool:
        """Run (or resume) one item; True when done, False when held (the slot exits)."""
        run_dir = self.runs_dir / item.id
        if fresh and not (run_dir / "run.json").exists():
            code, out = self.hook("before", item)
            if code != 0:
                return self.hold(item, f"before hook exit {code}: {out}")
            params = self.item_params(item)  # validated for every item when the slot started
            self.log(f"{item.id} start")
            status = engine.start(self.dag, params, self.runs_dir, item.id)
        elif resume_step:
            self.log(f"{item.id} resume from {resume_step}")
            status = engine.retry(self.dag, self.runs_dir, item.id, resume_step, downstream=True)
        else:
            self.log(f"{item.id} resume")
            status = engine.retry(self.dag, self.runs_dir, item.id, None, downstream=False)
        while status == "failed":
            failed = self.failed_step(item.id)
            if failed is None or self.q.stall_exit_code is None or failed[1] != self.q.stall_exit_code:
                return self.hold(item, failure_text(self.runs_dir, item.id, failed))
            code, out = self.hook("stall", item, STEP=failed[0])  # the hook may pick the reset by step
            until = time.time() + STALL_FALLBACK_SEC if code != 0 or not out.strip().isdigit() else float(out.strip())
            self.log(f"{item.id} stalled at {failed[0]}: waits until {datetime.fromtimestamp(until).strftime('%d %H:%M')}")
            while time.time() < until + self.stall_margin:
                time.sleep(min(60, max(0.1, until + self.stall_margin - time.time())))
            self.log(f"{item.id} resume from {failed[0]}")
            status = engine.retry(self.dag, self.runs_dir, item.id, failed[0], downstream=True)
        self.set_state(item.id, "done", status)
        self.log(f"{item.id} done ({status})")
        return True

    def failed_step(self, run_id: str) -> tuple[str, int | None] | None:
        st = engine.load_state(self.runs_dir, run_id)
        for sid, s in st.steps.items():
            if s.status == "failed" and not s.continued:
                return sid, s.exit_code
        return None

    def hold(self, item: Item, reason: str) -> bool:
        self.set_state(item.id, "held", reason)
        self.log(f"{item.id} HELD: {reason}")
        return False

    # ----- the loop --------------------------------------------------------------

    def loop(self, resume: str | None = None, resume_step: str | None = None) -> int:
        """Exit 0 queue empty or retired, 2 an item is held, 7 only held items block the queue."""
        if resume:
            item = next((i for i in self.q.items if i.id == resume), None)
            if item is None:
                raise SpecError(f"unknown item {resume!r}")
            self.lock()
            self.set_state(item.id, "active", self.name)
            self.unlock()
            if not self.run_item(item, resume_step, fresh=False):
                return 2
        waiting = False
        while True:
            if (self.qdir / f"retire-{self.name}").exists():
                self.log("retired")
                return 0
            self.lock()
            try:
                code, why = self.hook("admission")
                item = None if code != 0 else self.pick()
            finally:
                self.unlock()
            if code != 0:
                if not waiting:
                    self.log(f"waiting: {why or 'admission refused'}")
                waiting = True
                time.sleep(self.poll)
                continue
            if waiting:
                self.log("admitted again")
                waiting = False
            if item is not None:
                if not self.run_item(item):
                    return 2
                continue
            states = [self.state(i.id) for i in self.q.items]
            if all(s == "done" for s in states):
                self.log("queue empty")
                return 0
            if "active" not in states:
                self.log("only held items block the queue")
                return 7
            time.sleep(self.poll)


def failure_text(runs_dir: Path, run_id: str, failed: tuple[str, int | None] | None) -> str:
    """``step <id> exit <code>, attempt <n>, log <path>``: what a held item's reason and the status say."""
    if failed is None:
        return "step ? exit ?"
    sid, code = failed
    st = engine.load_state(runs_dir, run_id).steps.get(sid)
    n = len(st.attempts) if st else 0
    return f"step {sid} exit {code}, attempt {n}, log {runs_dir / run_id / 'steps' / f'{sid}.{n}.log'}"


def queue_status(runs_dir: Path, q: QueueSpec) -> str:
    qdir = runs_dir / "q"
    lines = []
    for it in q.items:
        state = "-"
        detail = ""
        for s in ("active", "held", "done"):
            p = qdir / f"{it.id}.{s}"
            if p.exists():
                state = s
                detail = p.read_text().strip()
        lines.append(f"  {it.id:<16}{it.group:<10}{state:<8}{detail}")
    return "\n".join(lines)


def main_queue(args, runs_dir: Path) -> int:
    q = load_queue(args.queue)
    if args.status:
        print(queue_status(runs_dir, q))
        return 0
    if not args.slot:
        print("runner queue: --slot <worktree> is required", file=sys.stderr)
        return 2
    slot = Slot(q, runs_dir, os.path.abspath(args.slot), poll_sec=args.poll_sec)
    return slot.loop(resume=args.resume, resume_step=args.step)
