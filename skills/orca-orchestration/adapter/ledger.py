"""The launch ledger: one JSON line per worker the adapter started or re-tasked.

``<runs dir>/adapter/launches.jsonl`` records what the adapter knew at launch time and the
runner had already exported: the task, dispatch and terminal handle Orca returned, the vendor
and model, the role, the worktree, and ``DAG_RUN_ID`` / ``DAG_RUN_STEP_NAME`` (the item and
step). ``cost`` joins a session log to its item and step on the task id, which Orca writes into
the worker's first message (``Your task ID is: task_…``), so the Task text may say anything.
``close`` reads it to know which terminals of a worktree are the pipeline's own.

The runs dir comes from ``--runs-dir``, else ``$RUNS_DIR`` (what the queue exports to its
hooks), else the parent of ``$DAG_RUN_WORK_DIR`` (what the runner exports to every step).
Without any of them nothing is written and the caller logs that.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def runs_dir(explicit: str | None = None) -> Path | None:
    if explicit:
        return Path(explicit)
    if os.environ.get("RUNS_DIR"):
        return Path(os.environ["RUNS_DIR"])
    if os.environ.get("DAG_RUN_WORK_DIR"):
        return Path(os.environ["DAG_RUN_WORK_DIR"]).parent
    return None


def path(runs: Path) -> Path:
    return runs / "adapter" / "launches.jsonl"


def append(runs: Path, **record: str | None) -> dict:
    rec = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "item": os.environ.get("DAG_RUN_ID", ""),
        "step": os.environ.get("DAG_RUN_STEP_NAME", ""),
        **{k: ("" if v is None else v) for k, v in record.items()},
    }
    p = path(runs)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def read(runs: Path | None) -> list[dict]:
    if runs is None or not path(runs).exists():
        return []
    rows = []
    with open(path(runs), encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                rows.append(rec)
    return rows


def by_task(runs: Path | None) -> dict[str, dict]:
    """Task id → its record (the last one wins)."""
    return {r["task"]: r for r in read(runs) if r.get("task")}
