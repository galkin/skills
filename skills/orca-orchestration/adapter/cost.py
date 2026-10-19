"""Token use per worker session, by run item and step, from the vendors' own session logs.

- **claude**: ``~/.claude/projects/<worktree path with every non-alphanumeric as ->/*.jsonl``
  (and each subagent a session forked, under ``<session>/subagents/``). Every assistant
  message carries ``usage`` (input, cache creation, cache read, output); one message is
  logged once per content block, so it is counted once by its id.
- **codex**: ``~/.codex/sessions/<y>/<m>/<d>/rollout-*.jsonl``. ``token_count`` events carry the
  running ``total_token_usage``, the ``last_token_usage`` (the context of that call) and the
  ``rate_limits`` windows, so a session's share of the 5-hour window is the first-to-last
  change of ``primary.used_percent`` (from zero when a new window began during the session).

A session is tied to an item and a step through the launch ledger (``ledger.py``): Orca's
preamble in the worker's first message names the task (``Your task ID is: task_…``), and the
ledger has that task's ``DAG_RUN_ID`` and ``DAG_RUN_STEP_NAME``. Logs older than the ledger
fall back to the Task text (``unit 1.3a …, step review round 2`` → item ``1.3a``, step
``review2``; ``quiz chunk 2-3, step write`` → item ``quiz-2-3``, step ``write``).

Numbers: ``calls`` model calls; ``ctx`` the context of the last call (input + cache), the
number to keep near 150k; ``fresh`` input and cache-creation tokens summed over calls (what
was newly read); ``cached`` cache-read tokens summed; ``out`` output tokens; ``window`` the
share of the vendor's 5-hour window the session took, when the log says (Codex only).
"""

from __future__ import annotations

import glob
import json
import os
import re
import time
from typing import Any

from . import ledger

UNIT = re.compile(r"\bunit (\S+) \(listed[^)]*\), step (verify|author|review round (\d+)|fix round (\d+))")
CHUNK = re.compile(r",\s*(\S+) chunk ([^\s,]+)\s*,\s*step (\w+)")  # "…, quiz chunk 2-3, step write"
TASK_ID = re.compile(r"Your task ID is: (task_\w+)")


def is_task(text: str) -> bool:
    """The message is a worker's Task: Orca's preamble names the task, or the text classifies."""
    return bool(TASK_ID.search(text)) or bool(classify(text)[0])


def attribute(text: str, launches: dict[str, dict]) -> tuple[str, str]:
    """(item, step) from the ledger when the preamble's task id is in it, else from the text."""
    m = TASK_ID.search(text)
    if m and m.group(1) in launches:
        r = launches[m.group(1)]
        if r.get("item"):
            return r["item"], r.get("step", "")
    return classify(text)


def classify(text: str) -> tuple[str, str]:
    """(item, step) from the Task text, or ("", first words) when it is not a run Task."""
    m = UNIT.search(text)
    if m:
        step = m.group(2)
        if step.startswith("review"):
            step = "review" + m.group(3)
        elif step.startswith("fix"):
            step = "fix" + m.group(4)
        return m.group(1), step
    m = CHUNK.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}", m.group(3)
    return "", " ".join(text.split())[:40]


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict))
    return ""


def claude_dir(worktree: str) -> str:
    return os.path.expanduser("~/.claude/projects/") + re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(worktree))


def scan_claude(path: str) -> dict:
    first = ""
    usage: dict[str, dict] = {}
    order: list[str] = []
    started = None
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if not isinstance(e, dict):
                continue
            m = e.get("message") if isinstance(e.get("message"), dict) else {}
            if started is None and e.get("timestamp"):
                started = e["timestamp"]
            if e.get("type") == "user" and not is_task(first):
                t = _text(m.get("content"))
                if t and (not first or is_task(t)):
                    first = t
            if e.get("type") == "assistant" and m.get("usage"):
                mid = m.get("id") or str(len(order))
                if mid not in usage:
                    order.append(mid)
                usage[mid] = m["usage"]
    calls = len(order)
    fresh = sum(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) for u in usage.values())
    cached = sum(u.get("cache_read_input_tokens", 0) for u in usage.values())
    out = sum(u.get("output_tokens", 0) for u in usage.values())
    last = usage[order[-1]] if order else {}
    ctx = last.get("input_tokens", 0) + last.get("cache_read_input_tokens", 0) + last.get("cache_creation_input_tokens", 0)
    return {"first": first, "started": started, "calls": calls, "ctx": ctx, "fresh": fresh, "cached": cached, "out": out, "window": None}


def scan_codex(path: str) -> dict:
    first = ""
    cwd = ""
    started = None
    calls = 0
    total: dict = {}
    last: dict = {}
    seen_total = None
    w_first = w_last = None
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if not isinstance(e, dict):
                continue
            p = e.get("payload") if isinstance(e.get("payload"), dict) else {}
            if started is None and e.get("timestamp"):
                started = e["timestamp"]
            if e.get("type") == "session_meta":
                cwd = str(p.get("cwd") or "")
            if not is_task(first):
                t = ""
                if p.get("type") == "message" and p.get("role") == "user":
                    t = _text(p.get("content"))
                elif p.get("type") == "user_message":
                    t = str(p.get("message") or "")
                if t and (not first or is_task(t)):
                    first = t
            if p.get("type") == "token_count":
                info = p.get("info") or {}
                if info.get("total_token_usage") and info["total_token_usage"] != seen_total:
                    seen_total = total = info["total_token_usage"]
                    last = info.get("last_token_usage") or last
                    calls += 1
                prim = (p.get("rate_limits") or {}).get("primary")
                if prim and "used_percent" in prim:
                    w_first = w_first or prim
                    w_last = prim
    window = None
    if w_first and w_last:
        # The same window throughout: the session took the difference. A new window began during
        # the session (resets_at moved): what the old one held is gone, the new one holds only us.
        before = float(w_first["used_percent"]) if w_first.get("resets_at") == w_last.get("resets_at") else 0.0
        window = round(float(w_last["used_percent"]) - before, 1)
    inp = total.get("input_tokens", 0)
    cached = total.get("cached_input_tokens", 0)
    return {
        "first": first, "cwd": cwd, "started": started, "calls": calls, "ctx": last.get("input_tokens", 0),
        "fresh": inp - cached, "cached": cached, "out": total.get("output_tokens", 0), "window": window,
    }


def sessions(worktrees: list[str], hours: float, runs_dir: str | None = None) -> list[dict]:
    cutoff = time.time() - hours * 3600
    rows: list[dict] = []
    launches = ledger.by_task(ledger.runs_dir(runs_dir))
    roots = [claude_dir(w) for w in worktrees] or [os.path.expanduser("~/.claude/projects/*")]
    for root in roots:
        for d in glob.glob(root):
            for f in glob.glob(os.path.join(d, "*.jsonl")):
                if os.path.getmtime(f) < cutoff:
                    continue
                files = [(f, False)] + [(sf, True) for sf in glob.glob(f[:-6] + "/subagents/*.jsonl")]
                for path, sub in files:
                    s = scan_claude(path)
                    item, step = attribute(s["first"], launches)
                    rows.append({"vendor": "claude", "item": item, "step": step, "subagent": sub, "session": os.path.basename(path)[:8], **s})
    wanted = [os.path.abspath(w).rstrip("/") for w in worktrees]
    for f in glob.glob(os.path.expanduser("~/.codex/sessions/*/*/*/rollout-*.jsonl")):
        if os.path.getmtime(f) < cutoff:
            continue
        s = scan_codex(f)
        if wanted and not any(s["cwd"].rstrip("/") == w or f"worktree {w}" in s["first"] for w in wanted):
            continue
        item, step = attribute(s["first"], launches)
        rows.append({"vendor": "codex", "item": item, "step": step, "subagent": False, "session": os.path.basename(f)[8:27], **s})
    rows.sort(key=lambda r: (r["item"], r["started"] or ""))
    return rows


def table(rows: list[dict]) -> str:
    head = f"{'vendor':6} {'item':10} {'step':12} {'session':20} {'calls':>5} {'ctx':>6} {'fresh':>7} {'cached':>8} {'out':>6} {'window':>6}"
    lines = [head]
    tot = [0, 0, 0]
    for r in rows:
        win = f"{r['window']:.1f}%" if r["window"] is not None else "-"
        step = ("  └ " if r["subagent"] else "") + r["step"]
        lines.append(
            f"{r['vendor']:6} {r['item'][:10]:10} {step[:12]:12} {r['session'][:20]:20} {r['calls']:5} "
            f"{r['ctx'] // 1000:5}k {r['fresh'] // 1000:6}k {r['cached'] // 1000:7}k {r['out'] // 1000:5}k {win:>6}"
        )
        tot[0] += r["fresh"]; tot[1] += r["cached"]; tot[2] += r["out"]
    lines.append(f"total fresh {tot[0] // 1000}k · cached {tot[1] // 1000}k · out {tot[2] // 1000}k")
    return "\n".join(lines)


def write(rows: list[dict], runs_dir: str) -> list[str]:
    """Record the rows of every known item into <runs-dir>/<item>/cost.json (merged, by step)."""
    written = []
    by_item: dict[str, dict] = {}
    for r in rows:
        if not r["item"] or r["subagent"]:
            continue
        by_item.setdefault(r["item"], {})[r["step"]] = {
            k: r[k] for k in ("vendor", "session", "started", "calls", "ctx", "fresh", "cached", "out", "window")
        }
    for item, steps in by_item.items():
        d = os.path.join(runs_dir, item)
        if not os.path.isdir(d):
            continue
        path = os.path.join(d, "cost.json")
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        old.update(steps)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=1, sort_keys=True)
        written.append(path)
    return written


def main(args) -> int:
    rows = sessions(args.worktree or [], args.hours, args.runs_dir)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        print(table(rows))
    if args.write:
        for p in write(rows, args.runs_dir):
            print(f"wrote {p}")
    return 0
