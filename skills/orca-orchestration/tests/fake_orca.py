"""A stand-in for the `orca` CLI used by the adapter tests.

State lives in the JSON file named by $FAKE_ORCA_STATE; every call is appended to
$FAKE_ORCA_LOG as one line of argv. Receipts mimic Orca 1.4.229's shapes as the adapter
reads them (payload under "result").
"""

import json
import os
import sys


def load():
    try:
        with open(os.environ["FAKE_ORCA_STATE"]) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(state):
    with open(os.environ["FAKE_ORCA_STATE"], "w") as f:
        json.dump(state, f)


def opt(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def reply(result, ok=True):
    print(json.dumps({"ok": ok, "result": result} if ok else {"ok": ok, "error": result}))


def main():
    argv = sys.argv[1:]
    with open(os.environ["FAKE_ORCA_LOG"], "a") as f:
        f.write(json.dumps(argv) + "\n")
    s = load()
    s.setdefault("terminals", {})  # handle -> {worktreePath, tail: [...]}
    s.setdefault("tasks", {})  # id -> {status, handle, dispatch, polls, complete_after}
    s.setdefault("messages", [])  # batches: [{deliveryId, messages: [...]}]
    s.setdefault("n", 0)
    s.setdefault("sent", [])
    group, cmd = argv[0], argv[1]
    rest = argv[2:]

    down = os.environ.get("FAKE_ORCA_DOWN")  # a file holding how many more calls fail as if Orca were not running
    if down and os.path.exists(down):
        n = int(open(down).read().strip() or 0)
        if n > 0:
            open(down, "w").write(str(n - 1))
            reply({"code": "runtime_unavailable", "message": "Could not read Orca runtime metadata. Start the Orca app first."}, ok=False)
            sys.exit(1)

    if group == "terminal":
        if cmd == "create":
            s["n"] += 1
            h = f"term_{s['n']}"
            s["terminals"][h] = {"worktreePath": opt(rest, "--worktree", "").replace("path:", ""), "tail": ["$ ready"], "command": opt(rest, "--command")}
            save(s)
            return reply({"terminal": {"handle": h}})
        if cmd == "wait":
            return reply({"state": "tui-idle"})
        if cmd == "list":
            return reply({"terminals": [{"handle": h, "worktreePath": t["worktreePath"]} for h, t in s["terminals"].items()]})
        if cmd == "read":
            t = s["terminals"].get(opt(rest, "--terminal"), {"tail": []})
            return reply({"terminal": {"tail": t["tail"]}})
        if cmd == "send":
            h, text = opt(rest, "--terminal"), opt(rest, "--text")
            s["sent"].append([h, text])
            if "Continue the task" in text and h in s["terminals"]:
                s["terminals"][h]["tail"] = ["Working (esc to interrupt)"]
            save(s)
            return reply({"accepted": True})
        if cmd == "close":
            s["terminals"].pop(opt(rest, "--terminal"), None)
            save(s)
            return reply({"closed": True})

    if group == "orchestration":
        if cmd in ("worker-start", "task-create"):
            s["n"] += 1
            tid = f"task_{s['n']}"
            if cmd == "worker-start" and os.environ.get("FAKE_ORCA_ON_START"):
                # A workflow-level trial: pretend the worker produced something in its worktree.
                import subprocess
                subprocess.run(os.environ["FAKE_ORCA_ON_START"], shell=True, cwd=opt(rest, "--worktree", "").replace("path:", "") or None,
                               env={**os.environ, "TITLE": opt(rest, "--task-title", "")})
            if cmd == "worker-start":
                h = opt(rest, "--terminal")
                if not h:
                    s["n"] += 1
                    h = f"term_{s['n']}"
                    s["terminals"][h] = {"worktreePath": opt(rest, "--worktree", "").replace("path:", ""), "tail": ["Working"], "agent": opt(rest, "--agent")}
                d = f"disp_{s['n']}"
                s["tasks"][tid] = {"status": "running", "handle": h, "dispatch": d, "polls": 0, "title": opt(rest, "--task-title"), "spec": opt(rest, "--spec")}
                save(s)
                # Orca 1.4.229 (verified 2026-10-19): the receipt names the task and dispatch, not the terminal.
                return reply({"stage": "input_accepted", "task": {"id": tid}, "dispatch": {"id": d}, "launch": {"effective": opt(rest, "--agent", "terminal")}})
            s["tasks"][tid] = {"status": "pending", "handle": None, "dispatch": None, "polls": 0, "title": opt(rest, "--task-title"), "spec": opt(rest, "--spec")}
            save(s)
            return reply({"task": {"id": tid}})
        if cmd == "dispatch":
            tid, h = opt(rest, "--task"), opt(rest, "--to")
            s["n"] += 1
            d = f"disp_{s['n']}"
            s["tasks"][tid].update(status="running", handle=h, dispatch=d)
            save(s)
            return reply({"dispatch": {"id": d, "assignee_handle": h}})
        if cmd == "task-list":
            rows = []
            for tid, t in s["tasks"].items():
                t["polls"] += 1
                if t.get("complete_after") is None and os.environ.get("FAKE_ORCA_AUTOCOMPLETE"):
                    t["complete_after"] = t["polls"] + int(os.environ["FAKE_ORCA_AUTOCOMPLETE"]) - 1
                if t.get("complete_after") is None and os.environ.get("FAKE_ORCA_AUTOCOMPLETE"):
                    t["complete_after"] = t["polls"] + int(os.environ["FAKE_ORCA_AUTOCOMPLETE"]) - 1
                if t.get("complete_after") is not None and t["polls"] >= t["complete_after"]:
                    t["status"] = t.get("final", "completed")
                rows.append({"id": tid, "status": t["status"], "spec": t.get("spec")})
            save(s)
            return reply({"tasks": rows})
        if cmd == "dispatch-show":
            t = s["tasks"].get(opt(rest, "--task"))
            if not t:
                return reply({"error": "unknown task"}, ok=False)
            return reply({"dispatch": {"id": t["dispatch"], "assignee_handle": t["handle"]}})
        if cmd == "check":
            # A bound Run replays its oldest batch until it is acked (Orca 1.4.229), so a batch
            # leaves the queue on --ack, not on delivery.
            if "--ack" in rest:
                d = opt(rest, "--ack")
                s["acked"] = s.get("acked", []) + [d]
                if s["messages"] and s["messages"][0].get("deliveryId") == d:
                    s["delivered"] = s.get("delivered", []) + s["messages"].pop(0)["messages"]
            batch = s["messages"][0] if s["messages"] and "--wait" in rest else {"deliveryId": None, "messages": []}
            save(s)
            return reply(batch)
        if cmd == "inbox":
            if s.get("inbox_down"):
                reply({"code": "runtime_unavailable", "message": "inbox unavailable"}, ok=False)
                sys.exit(1)
            # Everything ever sent, newest first: replies, delivered batches, queued batches.
            rows = s.get("inbox", []) + s.get("delivered", []) + [m for b in s["messages"] for m in b["messages"]]
            rows = sorted(rows, key=lambda m: m.get("created_at", ""), reverse=True)
            return reply({"messages": rows[: int(opt(rest, "--limit", "1000"))], "count": len(rows)})
        if cmd == "reply":
            mid = opt(rest, "--id")
            s["n"] += 1
            s.setdefault("inbox", []).append({"id": f"msg_r{s['n']}", "thread_id": mid, "type": "status", "from_handle": "run:coordinator",
                                              "subject": "Re:", "body": opt(rest, "--body"), "created_at": "9999"})
            save(s)
            return reply({"message": {"id": f"msg_r{s['n']}"}})
        if cmd == "worker-release":
            d = opt(rest, "--dispatch")
            if d in s.get("retained", []):  # the user took the terminal: Orca keeps it (Orca 1.4.229 answers ok with state retained)
                return reply({"dispatchId": d, "state": "retained", "reason": "user_takeover"})
            if d in s.get("external", []):  # a terminal the caller created (terminal create + worker-start --terminal)
                return reply({"dispatchId": d, "state": "retained", "reason": "external_terminal"})
            s["released"] = s.get("released", []) + [d]
            save(s)
            return reply({"state": "released", "dispatch": d})

    reply({"error": f"fake orca: unknown {group} {cmd}"}, ok=False)
    sys.exit(1)


main()
