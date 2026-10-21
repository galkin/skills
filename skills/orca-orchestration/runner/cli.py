"""``runner`` command line.

    runner validate <workflow.yaml>
    runner run <workflow.yaml> --run-id <id> [--param k=v ...]
    runner retry <workflow.yaml> --run-id <id> [--step <id>] [--downstream]
    runner exec <workflow.yaml> --run-id <id> --step <id> [--env K=V ...]
    runner status --run-id <id> | runner status
    runner queue <queue.yaml> --slot <worktree> [--resume <item> [--step <id>]] [--poll-sec N]
    runner queue <queue.yaml> --status

Exit codes: 0 the run succeeded or partially succeeded, 1 it failed, 2 the workflow,
parameters or usage are invalid; ``exec`` exits with the step command's own code.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import engine, queue
from .spec import SpecError, load, resolve_params

DEFAULT_RUNS_DIR = os.environ.get("RUNNER_RUNS_DIR", ".task/runs")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runner", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR, help="where run state lives (default: %(default)s, or $RUNNER_RUNS_DIR)")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate a workflow file against the subset schema and the load-time rules")
    v.add_argument("workflow")

    r = sub.add_parser("run", help="execute a workflow once")
    r.add_argument("workflow")
    r.add_argument("--run-id", required=True, help="name of the run; its state goes to <runs-dir>/<run-id>/")
    r.add_argument("--param", action="append", default=[], metavar="NAME=VALUE")

    t = sub.add_parser("retry", help="rerun a run: failed and not-run steps, or one step (and optionally its descendants)")
    t.add_argument("workflow")
    t.add_argument("--run-id", required=True)
    t.add_argument("--step")
    t.add_argument("--downstream", action="store_true", help="also reset every step reachable from --step")

    e = sub.add_parser("exec", help="run one step's commands once in the run's environment, outside the run (run.json untouched)")
    e.add_argument("workflow")
    e.add_argument("--run-id", required=True)
    e.add_argument("--step", required=True)
    e.add_argument("--env", action="append", default=[], metavar="NAME=VALUE", help="set over the DAG and step environment")

    s = sub.add_parser("status", help="print the state of one run, or list runs")
    s.add_argument("--run-id")

    qp = sub.add_parser("queue", help="work through a queue file in one slot (continuous mode), or show the queue")
    qp.add_argument("queue")
    qp.add_argument("--slot", help="slot worktree this process works in")
    qp.add_argument("--resume", metavar="ITEM", help="continue a held item first")
    qp.add_argument("--step", help="with --resume: retry from this step and its descendants")
    qp.add_argument("--poll-sec", type=float, default=60, help="idle polling interval (default %(default)s)")
    qp.add_argument("--status", action="store_true")
    return p


def parse_params(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SpecError(f"--param and --env expect NAME=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs_dir = Path(args.runs_dir)
    try:
        if args.cmd == "validate":
            dag = load(args.workflow)
            inferred = [(d, s.id) for s in dag.steps for d in s.inferred if d not in s.depends]
            print(f"{args.workflow}: valid ({len(dag.steps)} steps)")
            for producer, consumer in inferred:
                print(f"inferred: {producer} -> {consumer}")
            return 0
        if args.cmd == "run":
            dag = load(args.workflow)
            params = resolve_params(dag, parse_params(args.param))
            status = engine.start(dag, params, runs_dir, args.run_id)
            return 0 if status in ("succeeded", "partially_succeeded") else 1
        if args.cmd == "retry":
            dag = load(args.workflow)
            if args.downstream and not args.step:
                raise SpecError("--downstream requires --step")
            status = engine.retry(dag, runs_dir, args.run_id, args.step, args.downstream)
            return 0 if status in ("succeeded", "partially_succeeded") else 1
        if args.cmd == "exec":
            return engine.exec_step(load(args.workflow), runs_dir, args.run_id, args.step, parse_params(args.env))
        if args.cmd == "queue":
            return queue.main_queue(args, runs_dir)
        if args.cmd == "status":
            if args.run_id:
                print(engine.status_text(engine.load_state(runs_dir, args.run_id), runs_dir))
                return 0
            for d in sorted(runs_dir.iterdir()) if runs_dir.exists() else []:
                if (d / "run.json").exists():
                    st = engine.load_state(runs_dir, d.name)
                    print(f"{d.name:<24}{st.status:<20}{st.started}")
            return 0
    except (SpecError, FileExistsError, FileNotFoundError, KeyError) as e:
        print(f"runner: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
