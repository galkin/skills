"""Thin wrapper over the Orca CLI (layer 1). Everything that knows Orca's commands, receipts
and screens lives here and in cli.py; nothing else in the skill calls ``orca``.

The executable follows the orchestration skill's rule: ``$ORCA_CLI_COMMAND`` when set, else
``orca``. Receipts are JSON with the payload under ``result`` (or at the top level on older
hosts); ``find`` searches them tolerantly so a renamed field degrades to "not found" instead of
a crash.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from typing import Any


class OrcaError(Exception):
    """A failed Orca call. ``code`` is the receipt's ``error.code`` when it gave one
    (``runtime_unavailable`` when the app is not running), else ``""``."""

    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


def executable() -> list[str]:
    cmd = os.environ.get("ORCA_CLI_COMMAND")
    return shlex.split(cmd) if cmd else ["orca"]


def call(*args: str, check: bool = True, timeout: float | None = None) -> dict:
    """Run ``orca <args> --json`` and return the parsed receipt (``result`` unwrapped)."""
    argv = executable() + list(args) + ["--json"]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    text = "\n".join(line for line in proc.stdout.splitlines() if "_keepalive" not in line)
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        data = {"raw": text}
    if check and proc.returncode != 0:
        code = find(data, "error.code") if isinstance(data, dict) else None
        raise OrcaError(
            f"{' '.join(args[:2])} exited {proc.returncode}: {(proc.stderr or text).strip()[:500]}",
            code=str(code or ""),
        )
    if isinstance(data, dict) and isinstance(data.get("result"), (dict, list)):
        inner = data["result"]
        if isinstance(inner, dict):
            inner = dict(inner)
            inner.setdefault("ok", data.get("ok"))
            return inner
        return {"items": inner, "ok": data.get("ok")}
    return data if isinstance(data, dict) else {"items": data}


def find(obj: Any, *names: str) -> Any:
    """First value under any of ``names`` (also ``a.b`` paths) anywhere in ``obj``."""
    for name in names:
        v = _path(obj, name.split(".")) if "." in name else _search(obj, name)
        if v not in (None, ""):
            return v
    return None


def _path(obj: Any, parts: list[str]) -> Any:
    for p in parts:
        if not isinstance(obj, dict) or p not in obj:
            return None
        obj = obj[p]
    return obj


def _search(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        if name in obj and obj[name] not in (None, ""):
            return obj[name]
        for v in obj.values():
            r = _search(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _search(v, name)
            if r is not None:
                return r
    return None


# ----- tasks and dispatches ---------------------------------------------------------


RUNNING = {"pending", "ready", "dispatched", "running", "in_progress", "claimed"}


def task_status(run: str, task_id: str) -> str:
    r = call("orchestration", "task-list", "--run", run)
    tasks = r.get("tasks") or r.get("items") or []
    for t in tasks:
        if t.get("id") == task_id:
            return t.get("status") or "missing"
    return "missing"


def task_handle(task_id: str) -> str | None:
    r = call("orchestration", "dispatch-show", "--task", task_id, check=False)
    return find(r, "dispatch.assignee_handle", "assignee_handle", "assigneeHandle", "handle")


def task_dispatch(task_id: str) -> str | None:
    r = call("orchestration", "dispatch-show", "--task", task_id, check=False)
    return find(r, "dispatch.id", "dispatchId", "dispatch_id")


def release(dispatch: str) -> tuple[bool, str]:
    """``worker-release``; (ok, what the receipt said: ``<state>: <reason>``).

    Orca 1.4.229 answers ``ok: true`` with ``state: retained`` and a ``reason`` when it keeps
    the terminal: ``external_terminal`` for one the adapter created itself (the claude route,
    which Orca never owns), ``ownership_transferred`` / ``user_takeover`` for one the user took.
    """
    r = call("orchestration", "worker-release", "--dispatch", dispatch, check=False)
    state = str(find(r, "state", "status", "terminalState") or "")
    reason = str(find(r, "reason", "error.code", "error.message") or "")
    ok = r.get("ok") is not False and state in ("released", "release_pending", "")
    return ok, ": ".join(x for x in (state, reason) if x) or str(r)[:200]


# ----- messages -------------------------------------------------------------------


def inbox(limit: int = 2000) -> list[dict]:
    """The newest ``limit`` messages across recipients (Orca 1.4.229: ``id``, ``run_id``,
    ``to_handle``, ``from_handle``, ``type``, ``thread_id``, ``created_at``, newest first).
    Raises ``OrcaError`` when Orca does not answer, so a caller never mistakes an outage for
    an empty mailbox."""
    r = call("orchestration", "inbox", "--limit", str(limit))
    rows = r.get("messages") or r.get("items") or []
    return [m for m in rows if isinstance(m, dict)]


def reply(message_id: str, body: str) -> None:
    call("orchestration", "reply", "--id", message_id, "--body", body)


def payload(m: dict) -> dict:
    """A message's payload as a dict (Orca 1.4.237 sends it as a JSON string: ``taskId``,
    ``dispatchId``; ``outcome`` and ``reportPath`` on worker_done; ``question`` and ``options``
    on a question)."""
    p = m.get("payload")
    try:
        p = json.loads(p) if isinstance(p, str) else p
    except ValueError:
        return {}
    return p if isinstance(p, dict) else {}


def in_run(m: dict, run: str) -> bool:
    return m.get("run_id") == run or m.get("to_handle") == f"run:{run}"


# ----- runs -----------------------------------------------------------------------


def current_run() -> str | None:
    """The Run this terminal is bound to (``run-current``), None when it is bound to none or
    Orca does not say. A process started from the coordinator's terminal inherits its binding."""
    try:
        r = call("orchestration", "run-current")
    except OrcaError:
        return None
    return find(r, "run.id", "runId", "run_id")


def workers(run: str) -> list[dict]:
    """``worker-list --run``: every Dispatch of the Run with its terminal (Orca 1.4.237:
    ``dispatchId``, ``taskId``, ``dispatchStatus``, ``agentTerminalHandle``, ``terminalState``
    and ``resource.retainedReason`` / ``resource.ownerDispatchId``), all pages."""
    rows: list[dict] = []
    cursor = None
    for _ in range(50):
        argv = ["orchestration", "worker-list", "--run", run, "--limit", "100"]
        if cursor:
            argv += ["--cursor", cursor]
        r = call(*argv)
        rows += [w for w in (r.get("workers") or r.get("items") or []) if isinstance(w, dict)]
        cursor = find(r, "page.nextCursor", "nextCursor")
        if not cursor:
            break
    return rows


# ----- terminals ------------------------------------------------------------------


def terminals(worktree: str | None = None) -> list[dict]:
    r = call("terminal", "list")
    rows = r.get("terminals") or r.get("items") or []
    if worktree:
        w = worktree.rstrip("/")
        rows = [t for t in rows if str(t.get("worktreePath") or "").rstrip("/") == w]
    return rows


def alive(handle: str | None) -> bool:
    return bool(handle) and any(t.get("handle") == handle for t in terminals())


def tail(handle: str, lines: int = 10) -> str:
    r = call("terminal", "read", "--terminal", handle, check=False)
    rows = find(r, "terminal.tail", "tail") or []
    return "\n".join(rows[-lines:]) if isinstance(rows, list) else str(rows)


LIMIT = re.compile(r"hit your usage limit|hit your limit|try again at", re.I)
PROVIDER = re.compile(
    r"^\s*■ .*(429|Too Many Requests|at capacity|retry limit|server error|Service Unavailable|Bad Gateway|stream disconnected|overloaded)|API Error",
    re.I | re.M,
)
BUSY = re.compile(r"Working \(|esc to interrupt")


def stalled(handle: str | None) -> bool:
    """The last screen lines show a usage limit (only the tail: old scrollback lingers)."""
    return bool(handle) and bool(LIMIT.search(tail(handle)))


def provider_error(handle: str | None) -> bool:
    """The turn ended on a provider error (429, capacity, 5xx) and the agent sits idle."""
    if not handle:
        return False
    s = tail(handle)
    return bool(PROVIDER.search(s)) and not BUSY.search(s)


def send(handle: str, text: str) -> None:
    call("terminal", "send", "--terminal", handle, "--text", text, "--enter")


def close(handle: str) -> None:
    call("terminal", "close", "--terminal", handle, check=False)
