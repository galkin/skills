"""``adapter`` command line: the workflow steps' way to Orca workers (layer 1).

    adapter run      --run <run_id> --worktree <path> --launch <vendor:model:effort> --role <role>
                     --title <text> (--spec <text> | --spec-file <file> | --spec-template <file>)...
                     [--reuse-task <id>] [--fallback <vendor:model:effort>] [--language <name>]
    adapter wait     --run <run_id> --task <id> [--handle <h>] [--poll-sec 60] [--runtime-wait 30]
    adapter followup --run <run_id> --handle <h> --title <text> (--spec|--spec-file|--spec-template)...
    adapter handle   --task <id>            adapter alive --handle <h>
    adapter unstall  [--worktree <path>] [--exclude <path>]
    adapter drain    --run <run_id> [--once] [--repeat-sec 300] | --run <run_id> --ack <msg_id> [--body <text>]
    adapter close    --worktree <path> [--all]   adapter release --task <id>
    adapter budget   [--costs step=pct,...] [--new pct] [--week pct] [--margin pct] [--reset] [--why]
    adapter cost     [--worktree <path>]... [--hours 12] [--json] [--write]

Outputs go to ``$DAGU_OUTPUT_FILE`` when it is set (``task=``, ``dispatch=``, ``handle=``,
``status=``), so a workflow step declares them as ``outputs``. Exit codes follow the old
drivers: 0 ok, 4 the task ended badly, 5 the agent sits on a usage limit, 6 provider errors
persist, 3 (``drain --once``) a question or escalation is unanswered, 1 other failures.

The spec is the ``--spec`` texts and files joined in order. ``--spec-file`` is literal;
``--spec-template`` resolves ``${params.x}`` from ``$DAG_PARAMS_JSON`` and ``${env.X}`` from
the environment (Dagu's names, nothing else: no shell, no runner import), refuses an
unresolved reference, and passes a backslash-escaped ``${…}`` through as literal text.

Every ``run`` and ``followup`` appends one line to ``<runs dir>/adapter/launches.jsonl``
(see ``ledger.py``); ``cost`` joins session logs on it and ``close`` acts only on what it lists.

Launch routes (Orca 1.4.229):
- ``claude``: ``terminal create --command "claude --agent <role> --model … --effort …
  --dangerously-skip-permissions"`` → ``terminal wait --for tui-idle`` → ``worker-start
  --terminal <h>`` (``--model/--effort`` cannot combine with ``--terminal``, so they ride in argv).
- ``codex``: ``worker-start --agent codex --model … --effort …``; the role reaches Codex as
  ``developer_instructions`` in the worktree's ``.codex/config.toml``, which ``run`` writes from
  the body of ``.claude/agents/<role>.md`` first (one role file serves both vendors).
- ``--fallback``: the launch used instead when the first one's vendor sits on its usage limit
  (a reused terminal that shows the limit, or, for Codex, spent windows per ``budget``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import time
from datetime import datetime
from pathlib import Path

from . import budget, cost, ledger, orca
from .orca import OrcaError, find

EXIT_BAD_TASK = 4
EXIT_STALLED = 5
EXIT_PROVIDER = 6
EXIT_ATTENTION = 3


def out(**values: str | None) -> None:
    path = os.environ.get("DAGU_OUTPUT_FILE")
    for k, v in values.items():
        line = f"{k}={'' if v is None else v}"
        print(line)
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} adapter {msg}", file=sys.stderr, flush=True)


REF = re.compile(r"(\\?)\$\{(params|env)\.([A-Za-z_][A-Za-z0-9_]*)\}")


def interpolate(text: str, name: str) -> str:
    r"""``${params.x}`` and ``${env.X}`` resolved; ``\${…}`` literal; anything unresolved refuses."""
    try:
        params = json.loads(os.environ.get("DAG_PARAMS_JSON") or "{}")
    except ValueError:
        raise SystemExit("adapter: DAG_PARAMS_JSON is not valid JSON")

    def sub(m: re.Match) -> str:
        if m.group(1):
            return m.group(0)[1:]
        kind, key = m.group(2), m.group(3)
        source = params if kind == "params" else os.environ
        if key not in source:
            raise SystemExit(f"adapter: {name}: ${{{kind}.{key}}} is not defined")
        return str(source[key])

    return REF.sub(sub, text)


def spec_text(args) -> str:
    parts = []
    for item in args.spec_parts:
        kind, value = item
        if kind == "file":
            parts.append(Path(value).read_text(encoding="utf-8").rstrip("\n"))
        elif kind == "template":
            parts.append(interpolate(Path(value).read_text(encoding="utf-8").rstrip("\n"), value))
        else:  # a spec written inside a YAML block keeps the block's indentation: drop it
            parts.append("\n".join(line.strip() for line in value.strip().splitlines()))
    text = "\n".join(parts).strip()
    if not text:
        raise SystemExit("adapter: a task spec is required (--spec or --spec-file)")
    return text


KINDS = {"--spec": "text", "--spec-file": "file", "--spec-template": "template"}


class SpecAction(argparse.Action):
    def __call__(self, parser, ns, value, option_string=None):
        ns.spec_parts.append((KINDS[option_string], value))


def add_spec(p: argparse.ArgumentParser) -> None:
    p.set_defaults(spec_parts=[])
    p.add_argument("--spec", action=SpecAction, help="spec text; repeatable, joined in order with the files")
    p.add_argument("--spec-file", action=SpecAction, help="file whose text is appended to the spec, literally")
    p.add_argument("--spec-template", action=SpecAction,
                   help="file whose text is appended with ${params.x} and ${env.X} resolved (from DAG_PARAMS_JSON and the environment)")
    p.add_argument("--title", required=True)
    p.add_argument("--runs-dir", default=None, help="where the launch ledger lives (default: $RUNS_DIR, else the parent of $DAG_RUN_WORK_DIR)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adapter", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="start a worker in a role, or send the task into a live session with --reuse-task")
    r.add_argument("--run", required=True, help="Orca Run id")
    r.add_argument("--worktree", required=True)
    r.add_argument("--launch", required=True, metavar="VENDOR:MODEL:EFFORT")
    r.add_argument("--role", required=True, help="Claude: .claude/agents/<role>.md; Codex: informational")
    r.add_argument("--reuse-task", help="reuse the terminal of this task when it is still alive")
    r.add_argument("--timeout-ms", type=int, default=180000, help="terminal readiness wait for the claude route")
    add_spec(r)
    r.add_argument("--fallback", default="", metavar="VENDOR:MODEL:EFFORT",
                   help="launch for a fresh worker when the --launch vendor is at its usage limit (its reused terminal shows the limit, or its windows are spent)")
    r.add_argument("--language", default="", help="claude: the session's output language (--settings), overriding the user's global one; codex: no-op, the role body carries it")

    f = sub.add_parser("followup", help="create a task and inject it into a live terminal")
    f.add_argument("--run", required=True)
    f.add_argument("--handle", required=True)
    add_spec(f)

    w = sub.add_parser("wait", help="poll a task until it settles; detect usage limits and provider errors")
    w.add_argument("--run", required=True)
    w.add_argument("--task", required=True)
    w.add_argument("--handle", nargs="?", default=None, help="optional; looked up from the task when empty")
    w.add_argument("--poll-sec", type=float, default=60)
    w.add_argument("--stall-every", type=int, default=5, help="check the screen for a limit every N polls")
    w.add_argument("--max-reprompts", type=int, default=8)
    w.add_argument("--runtime-wait", type=float, default=30, help="minutes to keep polling while Orca itself is unavailable (runtime_unavailable) before failing")

    h = sub.add_parser("handle", help="print the terminal handle of a task")
    h.add_argument("--task", required=True)

    a = sub.add_parser("alive", help="exit 0 when the terminal is listed")
    a.add_argument("--handle", required=True)

    u = sub.add_parser("unstall", help="wake every terminal whose screen still shows the usage limit")
    u.add_argument("--worktree", help="only this worktree's terminals")
    u.add_argument("--exclude", help="never this worktree (the coordinator's)")

    d = sub.add_parser("drain", help="consume heartbeat/worker_done batches; print every unanswered question or escalation each round")
    d.add_argument("--run", required=True)
    d.add_argument("--timeout-ms", type=int, default=300000)
    d.add_argument("--repeat-sec", type=float, default=300, help="print the pending questions again at least this often (default %(default)s)")
    d.add_argument("--retry-sec", type=float, default=30, help="pause before re-reading a batch the inbox does not show yet (default %(default)s)")
    d.add_argument("--inbox-limit", type=int, default=2000, help="how many of the newest inbox messages to search for questions and replies")
    d.add_argument("--once", action="store_true", help="one round: print what is pending, exit 3 when anything is")
    d.add_argument("--ack", metavar="MSG_ID", help="answer one question or escalation that needs no words: reply in its thread with --body, then exit")
    d.add_argument("--body", default="Acknowledged by the coordinator.", help="with --ack: the reply text")

    c = sub.add_parser("close", help="release the worktree's terminals the adapter started whose tasks have settled; retained and user-owned ones stay (exit 0, named in the log)")
    c.add_argument("--worktree", required=True)
    c.add_argument("--all", action="store_true", help="close every terminal of the worktree, whoever owns it (the playbook's last resort)")
    c.add_argument("--runs-dir", default=None, help="where the launch ledger lives (default: $RUNS_DIR, else the parent of $DAG_RUN_WORK_DIR)")

    rl = sub.add_parser("release", help="worker-release the settled dispatch of a task; exit 1 when Orca refuses")
    rl.add_argument("--task", required=True)

    b = sub.add_parser("budget", help="admission check against the Codex usage windows (exit 0 admit, 1 wait)")
    b.add_argument("--costs", default="", help="step=pct,... share of the Codex 5-hour window each step costs (Claude steps are not priced)")
    b.add_argument("--new", default=None, help="5-hour cost of the item about to start (default: sum of --costs)")
    b.add_argument("--week", type=float, default=1.7, help="weekly cost of one item (default %(default)s)")
    b.add_argument("--margin", type=float, default=3.0)
    b.add_argument("--runs-dir", default=os.environ.get("RUNS_DIR", ".task/runs"))
    b.add_argument("--reset", action="store_true", help="print the epoch of the fullest Codex window's reset; exit 1 when --step names a step --costs does not price")
    b.add_argument("--step", default=os.environ.get("STEP", ""), help="the step that stalled (default: $STEP, which the queue's stall hook gets)")
    b.add_argument("--why", action="store_true")
    k = sub.add_parser("cost", help="token use per worker session, by item and step, from the vendors' session logs")
    k.add_argument("--worktree", action="append", help="only sessions of this worktree (repeatable); default: every session")
    k.add_argument("--hours", type=float, default=12, help="look back this far (default %(default)s)")
    k.add_argument("--runs-dir", default=os.environ.get("RUNS_DIR", ".task/runs"))
    k.add_argument("--json", action="store_true")
    k.add_argument("--write", action="store_true", help="record the rows into <runs-dir>/<item>/cost.json")
    return p


# ----- commands -------------------------------------------------------------------


def parse_launch(text: str) -> tuple[str, str, str]:
    parts = text.split(":")
    if len(parts) != 3 or not all(parts):
        raise SystemExit(f"adapter: --launch expects vendor:model:effort, got {text!r}")
    return parts[0], parts[1], parts[2]


def cmd_run(args) -> int:
    spec = spec_text(args)
    launch = args.launch
    if args.reuse_task:
        handle = orca.task_handle(args.reuse_task)
        if orca.alive(handle):
            if args.fallback and orca.stalled(handle):
                log(f"{handle} of task {args.reuse_task} shows a usage limit; starting fresh with {args.fallback}")
                launch = args.fallback
            else:
                log(f"reusing {handle} of task {args.reuse_task}")
                return followup(args.run, handle, args.title, spec, args.runs_dir, args.worktree)
        else:
            log(f"task {args.reuse_task} has no live terminal; starting fresh")
    vendor, model, effort = parse_launch(launch)
    if args.fallback and launch == args.launch and budget.limited(vendor):
        log(f"{vendor} windows are spent; starting with {args.fallback}")
        vendor, model, effort = parse_launch(args.fallback)
    wt = f"path:{args.worktree}"
    if vendor == "claude":
        command = f"claude --agent {args.role} --model {model} --effort {effort} --dangerously-skip-permissions"
        if args.language:
            command += " --settings " + shlex.quote(json.dumps({"language": args.language}))
        t = orca.call("terminal", "create", "--worktree", wt, "--title", args.title, "--command", command)
        handle = find(t, "terminal.handle", "handle")
        if not handle:
            raise OrcaError(f"terminal create returned no handle: {t}")
        orca.call("terminal", "wait", "--terminal", handle, "--for", "tui-idle", "--timeout-ms", str(args.timeout_ms))
        receipt = orca.call(
            "orchestration", "worker-start", "--run", args.run, "--task-title", args.title, "--spec", spec,
            "--worktree", wt, "--terminal", handle,
        )
    elif vendor == "codex":
        write_codex_config(Path(args.worktree), args.role)
        receipt = orca.call(
            "orchestration", "worker-start", "--run", args.run, "--task-title", args.title, "--spec", spec,
            "--worktree", wt, "--agent", "codex", "--model", model, "--effort", effort,
        )
        handle = find(receipt, "assignee_handle", "assigneeHandle", "terminal.handle", "handle")
    else:
        raise SystemExit(f"adapter: unknown vendor {vendor!r} (claude or codex)")
    task = find(receipt, "task.id", "taskId", "task_id")
    dispatch = find(receipt, "dispatch.id", "dispatchId", "dispatch_id")
    if not handle and task:
        # Orca 1.4.229: the codex worker-start receipt carries the task and dispatch ids but
        # not the terminal; dispatch-show does (`dispatch.assignee_handle`).
        handle = orca.task_handle(task)
    log(f"worker-start receipt keys: {sorted(receipt) if isinstance(receipt, dict) else type(receipt).__name__}")
    log(f"started {vendor} {args.role} task={task} dispatch={dispatch} handle={handle} stage={find(receipt, 'stage')}")
    record(args.runs_dir, run=args.run, task=task, dispatch=dispatch, handle=handle, vendor=vendor, model=model,
           role=args.role, title=args.title, worktree=args.worktree, kind="start")
    out(task=task, dispatch=dispatch, handle=handle)
    return 0 if task else 1


def record(runs_dir: str | None, **rec: str | None) -> None:
    runs = ledger.runs_dir(runs_dir)
    if runs is None:
        log("no runs dir (--runs-dir, $RUNS_DIR or $DAG_RUN_WORK_DIR): launch not recorded in the ledger")
        return
    ledger.append(runs, **rec)


def role_body(role_file: Path) -> str:
    """The agent definition without its frontmatter."""
    text = role_file.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text.strip("\n") + "\n"


def write_codex_config(worktree: Path, role: str) -> Path:
    role_file = worktree / ".claude" / "agents" / f"{role}.md"
    if not role_file.exists():
        raise SystemExit(f"adapter: no role file {role_file} for the codex route")
    body = role_body(role_file)
    if '"""' in body:
        raise SystemExit(f"adapter: {role_file} must not contain a triple quote")
    out = worktree / ".codex" / "config.toml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'developer_instructions = """\n{body}"""\n', encoding="utf-8")
    log(f"wrote {out} from {role_file.name}")
    return out


def followup(run: str, handle: str, title: str, spec: str, runs_dir: str | None = None, worktree: str = "") -> int:
    t = orca.call("orchestration", "task-create", "--run", run, "--task-title", title, "--spec", spec)
    task = find(t, "task.id", "taskId", "task_id", "id")
    d = orca.call("orchestration", "dispatch", "--run", run, "--task", task, "--to", handle, "--inject")
    dispatch = find(d, "dispatch.id", "dispatchId", "dispatch_id", "id")
    log(f"followup task={task} dispatch={dispatch} into {handle}")
    # the terminal's vendor, model and role are those of the launch that created it
    first = next((r for r in ledger.read(ledger.runs_dir(runs_dir)) if r.get("handle") == handle), {})
    record(runs_dir, run=run, task=task, dispatch=dispatch, handle=handle, vendor=first.get("vendor", ""),
           model=first.get("model", ""), role=first.get("role", ""), title=title, worktree=worktree or first.get("worktree", ""), kind="followup")
    out(task=task, dispatch=dispatch, handle=handle)
    return 0


def cmd_followup(args) -> int:
    return followup(args.run, args.handle, args.title, spec_text(args), args.runs_dir)


WAKE = "The usage limit has reset. Continue the task exactly where you stopped."
REPROMPT = (
    "The previous turn failed with a provider error (rate limit or capacity), not a usage limit. "
    "Continue the task above from where you stopped."
)


def wake(handle: str) -> bool:
    """Answer Codex's switch-model menu if shown, tell the agent to continue; True when it moved on."""
    if "keep current model" in orca.tail(handle, 40).lower():
        orca.send(handle, "2")  # only when the menu is shown: otherwise a bare "2" is a user message
        time.sleep(5)
    orca.send(handle, WAKE)
    time.sleep(20)
    return not orca.stalled(handle)


def cmd_wait(args) -> int:
    handle = args.handle or orca.task_handle(args.task)
    if handle and orca.stalled(handle):
        log(f"{handle} shows a usage limit at the start of the wait; trying to wake it")
        if not wake(handle):
            out(status="stalled")
            return EXIT_STALLED
    tries = 0
    next_at = 0.0
    clean = 0
    n = 0
    down_since = 0.0
    while True:
        try:
            status = orca.task_status(args.run, args.task)
        except OrcaError as e:
            # Orca itself is down (a restart, a power cut): the task may still be running; keep
            # polling for --runtime-wait minutes, then fail as any other Orca error does.
            if e.code != "runtime_unavailable":
                raise
            down_since = down_since or time.time()
            waited = (time.time() - down_since) / 60
            if waited >= args.runtime_wait:
                log(f"Orca unavailable for {waited:.0f} min: {e}")
                raise
            log(f"Orca unavailable ({waited:.0f} of {args.runtime_wait:g} min): still waiting for task {args.task}")
            time.sleep(args.poll_sec)
            continue
        if down_since:
            log("Orca is back")
            down_since = 0.0
        if status == "completed":
            out(status=status)
            return 0
        if status not in orca.RUNNING:
            log(f"task {args.task} ended {status}")
            out(status=status)
            return EXIT_BAD_TASK
        n += 1
        if handle is None:
            handle = orca.task_handle(args.task)
        if n % args.stall_every == 0 and orca.stalled(handle):
            log(f"STALLED on a usage limit: task {args.task} handle {handle}")
            out(status="stalled")
            return EXIT_STALLED
        # provider errors: re-prompt after 1, 2, 4, 8, 16, 32, 32… minutes; reset after 10 clean polls
        if orca.provider_error(handle):
            clean = 0
            now = time.time()
            if next_at == 0:
                minutes = min(2**tries, 32)
                next_at = now + 60 * minutes
                log(f"provider error on {args.task}; re-prompt in {minutes} min")
            elif now >= next_at:
                if tries >= args.max_reprompts:
                    log(f"provider errors persist after {tries} re-prompts: {args.task}")
                    out(status="provider_error")
                    return EXIT_PROVIDER
                orca.send(handle, REPROMPT)
                tries += 1
                next_at = 0
                log(f"re-prompted {args.task} (attempt {tries})")
        else:
            next_at = 0
            clean += 1
            if clean >= 10:
                tries = 0
        time.sleep(args.poll_sec)


def cmd_handle(args) -> int:
    h = orca.task_handle(args.task)
    print(h or "")
    return 0 if h else 1


def cmd_alive(args) -> int:
    return 0 if orca.alive(args.handle) else 1


def cmd_unstall(args) -> int:
    still = 0
    exclude = (args.exclude or "").rstrip("/")
    for t in orca.terminals(args.worktree):
        if exclude and str(t.get("worktreePath") or "").rstrip("/") == exclude:
            continue
        h = t.get("handle")
        if not orca.stalled(h):
            continue
        log(f"waking {h}")
        if not wake(h):
            log(f"STILL STALLED {h}")
            still += 1
    return EXIT_STALLED if still else 0


BENIGN = {"heartbeat", "worker_done"}
ANSWERABLE = {"question", "escalation"}  # pending until a reply in their thread


def attention_line(m: dict, now: float) -> str:
    """``ATTENTION <id> <type> from <sender> [task <id>] age <n>m | <subject> | <body>``."""
    sender = m.get("from_handle") or m.get("from") or m.get("fromHandle") or "?"
    task = ""
    try:
        payload = m.get("payload")
        payload = json.loads(payload) if isinstance(payload, str) else payload or {}
        task = payload.get("taskId") or "" if isinstance(payload, dict) else ""
    except ValueError:
        pass
    age = "?"
    created = m.get("created_at") or m.get("createdAt")
    if created:
        try:
            t = datetime.fromisoformat(str(created).replace("Z", "+00:00")).timestamp()
            age = f"{max(0, int((now - t) // 60))}m"
        except ValueError:
            pass
    body = " ".join(str(m.get("body") or "").split())[:400]
    return f"ATTENTION {m.get('id')} {m.get('type')} from {sender}{f' task {task}' if task else ''} age {age} | {m.get('subject')} | {body}"


def pending_attention(run: str, seen: dict[str, dict], limit: int) -> tuple[dict[str, dict], set[str]] | None:
    """The run's questions and escalations nobody has answered, and the ids the inbox holds.

    A message is answered when its thread holds a message from someone other than its
    sender (``orchestration reply``). The inbox is the record, so a question that arrived
    while no drain ran is found too; ``seen`` adds what this process was delivered. None when
    Orca does not answer: nothing may then be taken as answered or recorded.
    """
    try:
        rows = orca.inbox(limit)
    except OrcaError as e:
        log(f"inbox unavailable ({e}); pending questions cannot be listed this round")
        return None
    replied: dict[str, set[str]] = {}
    for m in rows:
        thread = m.get("thread_id")
        if thread and thread != m.get("id"):
            replied.setdefault(thread, set()).add(str(m.get("from_handle") or ""))
    candidates = {m["id"]: m for m in rows if m.get("id") and m.get("type") in ANSWERABLE
                  and (m.get("run_id") == run or m.get("to_handle") == f"run:{run}")}
    for mid, m in seen.items():
        candidates.setdefault(mid, m)
    pending = {mid: m for mid, m in candidates.items()
               if not (replied.get(mid, set()) - {str(m.get("from_handle") or "")})}
    return pending, {m.get("id") for m in rows}


def cmd_drain(args) -> int:
    """Keep the coordinator's inbox quiet and every open question in view.

    Benign batches are acknowledged. A question or escalation is printed as an ATTENTION line
    with its id, sender and age, and printed again on every round until its thread holds a
    reply, so a second question never hides behind the first and none is consumed silently.
    A batch holding one is acknowledged only once the inbox shows it (the inbox, not the
    batch, is what the next round reads); while Orca cannot say so, the batch stays unacked
    and is replayed. The process keeps running; ``--once`` makes one round and exits 3 while
    anything is pending.
    """
    if args.ack:
        orca.reply(args.ack, args.body)
        log(f"acknowledged {args.ack} with a reply in its thread")
        return 0
    seen: dict[str, dict] = {}  # the open questions and escalations, as far as this process knows
    shown: set[str] = set()
    first = True
    last_shown = 0.0
    prev = None
    while True:
        argv = ["orchestration", "check", "--run", args.run, "--wait", "--timeout-ms", str(args.timeout_ms)]
        if prev:
            argv += ["--ack", prev]
        r = orca.call(*argv, check=False, timeout=args.timeout_ms / 1000 + 60)
        prev = None
        messages = r.get("messages") or []
        delivery = find(r, "deliveryId", "delivery_id")
        now = time.time()
        other = [m for m in messages if m.get("type") not in BENIGN]
        for m in other:
            if m.get("type") in ANSWERABLE and m.get("id"):
                seen[m["id"]] = m
            else:  # nothing to answer: shown once, then it is the coordinator's to read
                print(attention_line(m, now), flush=True)
        # The inbox is read on the first round (what arrived while no drain ran) and while
        # anything is open; a round of heartbeats with nothing open needs no lookup.
        found = pending_attention(args.run, seen, args.inbox_limit) if first or seen else ({}, set())
        first = False
        recorded = found is not None and all(m.get("id") in found[1] for m in other if m.get("type") in ANSWERABLE)
        if messages and delivery and (not other or recorded):
            prev = delivery
        if found is not None:
            seen = dict(found[0])  # answered ones drop out here
        fresh = set(seen) - shown
        if seen and (args.once or fresh or now - last_shown >= args.repeat_sec):
            for m in sorted(seen.values(), key=lambda m: str(m.get("created_at") or "")):
                print(attention_line(m, now), flush=True)
            last_shown = now
        shown = set(seen)
        if args.once:
            if prev:
                orca.call("orchestration", "check", "--run", args.run, "--ack", prev, check=False)
            return EXIT_ATTENTION if seen else 0
        if messages and delivery and not prev:
            time.sleep(args.retry_sec)  # an unrecorded batch is replayed at once: do not spin on it


def cmd_close(args) -> int:
    """Release the terminals the adapter started in the worktree once their tasks settled.

    Pipeline-owned means recorded in the launch ledger. Settlement is the terminal's last task
    (a follow-up's); the release goes to the dispatch that owns the terminal, the one
    ``worker-start`` returned (a follow-up's dispatch is context-only and Orca reports it as
    retained). A terminal Orca calls ``external_terminal`` is one the adapter created itself
    (the claude route): Orca never owns it, so it is closed with ``terminal close``. A terminal
    whose task still runs, one Orca keeps for another reason (ownership transferred, user
    takeover) and one the adapter did not start are kept and named, so nothing of the user's
    is closed; keeping is not a failure (the item's work is merged by the time a workflow
    closes), so the exit is 0 and the log says what stayed. ``--all`` is the old behaviour,
    every terminal of the worktree, for the playbook's last resort.
    """
    live = {t.get("handle"): t for t in orca.terminals(args.worktree)}
    if args.all:
        for h in live:
            orca.close(h)
            log(f"closed {h}")
        return 0
    runs = ledger.runs_dir(args.runs_dir)
    mine: dict[str, dict] = {}  # handle -> the last record (its task settles the terminal)
    owner: dict[str, str] = {}  # handle -> the dispatch worker-start returned (it owns the terminal)
    for r in ledger.read(runs):
        if r.get("handle") in live:  # live is already this worktree's
            mine[r["handle"]] = r
            if r.get("kind") == "start" and r.get("dispatch"):
                owner[r["handle"]] = r["dispatch"]
    if not mine:
        where = ledger.path(runs) if runs else "no runs dir"
        log(f"no terminal of {args.worktree} is in the launch ledger ({where}); nothing closed (--all closes every one)")
    kept = 0
    for h, r in mine.items():
        if not (r.get("run") and r.get("task")):
            log(f"kept {h}: the ledger has no task for it, so its settlement cannot be verified")
            kept += 1
            continue
        status = orca.task_status(r["run"], r["task"])
        if status in orca.RUNNING:
            log(f"kept {h}: task {r['task']} is {status}")
            kept += 1
            continue
        if h not in owner:  # only re-tasked by the adapter (a follow-up into a terminal it did not start)
            log(f"kept {h}: not started by the adapter (re-tasked only; task {r['task']} {status})")
            kept += 1
            continue
        ok, said = orca.release(owner[h])
        if ok:
            log(f"released {h} (task {r['task']} {status})")
        elif "external_terminal" in said:
            orca.close(h)
            log(f"closed {h} (task {r['task']} {status}; Orca never owned it: {said})")
        else:
            log(f"kept {h}: worker-release refused: {said}")
            kept += 1
    for h in live:
        if h not in mine:
            log(f"kept {h}: not started by the adapter")
    if kept:
        log(f"{kept} terminal(s) of {args.worktree} kept; see above")
    return 0


def cmd_release(args) -> int:
    d = orca.task_dispatch(args.task)
    if not d:
        log(f"task {args.task} has no dispatch to release")
        return 1
    ok, said = orca.release(d)
    log(f"release {d}: {said or 'ok'}")
    return 0 if ok else 1


def cmd_budget(args) -> int:
    return budget.main(args)


def cmd_cost(args) -> int:
    return cost.main(args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fn = globals()[f"cmd_{args.cmd}"]
    try:
        return fn(args)
    except OrcaError as e:
        log(str(e))
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
