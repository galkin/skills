"""Admission by the Codex usage windows.

May a slot start a new item without a worker stopping on its usage limit halfway? Codex has
a 5-hour window and a weekly one, each ``used %`` plus ``resets_at``, read from the newest
``rate_limits`` Codex wrote to ``~/.codex/sessions`` (``primary`` is the 5-hour window,
``secondary`` the weekly one). Only Codex: Claude Code keeps its windows out of every file on
disk (they reach the status line alone), so Claude steps are not priced and a Claude limit is
met when it shows on the screen (``adapter wait`` exit 5, the queue's stall path).

Costs are shares of the 5-hour window per Codex step: ``--costs author=7.5,fix1=3.5``. A
running item reserves the priced steps that have not succeeded yet (from its ``run.json``),
and a new item is admitted only if ``used + reserved + new + margin`` stays under 100 % and
the weekly window allows one more item. Exit 0 = admit, 1 = wait.

Top-up: when the check fails but nothing running still spends Codex, exactly one item is
admitted anyway (``TOPUP``), so a window is spent to 100 % rather than left unused; if it
stalls, the queue's stall hook (``--reset``) waits for the reset.

``--reset`` prints the epoch to wait for: the fullest Codex window's. With ``--step`` (the
queue exports the stalled step as ``$STEP``, the default) naming a step ``--costs`` does not
price, the stall is not Codex's and its reset is unknown: exit 1, and the queue falls back
to its own short wait.
"""

from __future__ import annotations

import glob
import json
import os
import re
import time


def codex_limits() -> dict | None:
    best = None
    files = sorted(glob.glob(os.path.expanduser("~/.codex/sessions/*/*/*/*.jsonl")), key=os.path.getmtime)[-12:]
    for f in files:
        try:
            with open(f, errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for line in lines:
            if '"rate_limits"' not in line:
                continue
            m = re.search(r'"timestamp":"([^"]+)"', line)
            pr = re.search(r'"rate_limits":\{[^{]*"primary":(\{[^}]*\})', line)
            se = re.search(r'"rate_limits":\{.*?"secondary":(\{[^}]*\})', line)
            if not (m and pr and se):
                continue
            try:
                r = {"primary": json.loads(pr.group(1)), "secondary": json.loads(se.group(1))}
            except ValueError:
                continue
            if best is None or m.group(1) > best[0]:
                best = (m.group(1), r)
    return best[1] if best else None


def used(window: dict | None) -> tuple[float, float | None]:
    """(used %, resets_at epoch) of one window; an expired or missing window is empty."""
    if not isinstance(window, dict):
        return 0.0, None
    try:
        reset = float(window.get("resets_at") or 0)
        pct = float(window.get("used_percent", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0, None  # a shape this reader does not know counts as no data
    if reset and reset <= time.time():
        return 0.0, None
    return pct, (reset or None)


def windows() -> dict:
    """{"5h": (used, reset), "week": (used, reset), "known": bool} for Codex."""
    c = codex_limits()
    return {"5h": used(c and c.get("primary")), "week": used(c and c.get("secondary")), "known": c is not None}


def parse_costs(text: str) -> dict[str, float]:
    """``step=pct,...`` → {step: pct}; Codex steps only."""
    costs: dict[str, float] = {}
    for item in text.split(","):
        if not item.strip():
            continue
        step, sep, pct = item.partition("=")
        if ":" in step:
            raise SystemExit(f"budget: --costs prices Codex steps only (step=pct); leave Claude steps out, got {item.strip()!r}")
        try:
            costs[step.strip()] = float(pct)
        except ValueError:
            raise SystemExit(f"budget: --costs expects step=pct, got {item.strip()!r}") from None
    return costs


def remaining(runs_dir: str, item: str, costs: dict[str, float]) -> float:
    """5-hour share a running item still needs: the priced steps that have not succeeded."""
    try:
        with open(os.path.join(runs_dir, item, "run.json"), encoding="utf-8") as f:
            steps = json.load(f)["steps"]
    except (OSError, ValueError, KeyError):
        return sum(costs.values())  # not started yet: everything is ahead
    return sum(pct for step, pct in costs.items() if steps.get(step, {}).get("status") != "succeeded")


def main(args) -> int:
    costs = parse_costs(args.costs)
    new = float(args.new) if args.new is not None else sum(costs.values())
    week = float(args.week)
    w = windows()
    u5, reset5 = w["5h"]
    uw, resetw = w["week"]
    fullest = max((u5, reset5 or 0), (uw, resetw or 0))
    if args.reset:  # epoch of the reset a stalled item waits for
        if args.step and args.step not in costs:
            print(f"step {args.step} is not a priced Codex step; its reset is unknown")
            return 1  # the queue then waits its fallback and retries
        print(int(fullest[1] or time.time()))
        return 0
    active = [os.path.basename(p)[: -len(".active")] for p in glob.glob(os.path.join(args.runs_dir, "q", "*.active"))]
    reserve = {p: remaining(args.runs_dir, p, costs) for p in active}
    need5 = u5 + sum(reserve.values()) + new + args.margin
    needw = uw + len(active) * week + week + args.margin
    ok = need5 <= 100 and needw <= 100
    running = ", ".join(f"{p}:{c:.1f}%" for p, c in reserve.items()) or "none"
    why = (
        f"codex: 5h used {u5:.0f}% + running {sum(reserve.values()):.1f}% ({running}) + new {new:.0f}% "
        f"+ margin {args.margin:.0f}% = {need5:.0f}%; week {uw:.0f}% -> {needw:.0f}%"
    )
    if not w["known"]:
        why += " (no window data)"
    if ok:
        if args.why:
            print("ADMIT " + why)
        return 0
    spending = any(c > 0 for c in reserve.values())
    if not spending and u5 < 100 and uw < 100:
        print("TOPUP " + why)
        return 0
    reset = reset5 if need5 > 100 else resetw
    if reset:
        why += f"; wait for reset at {time.strftime('%d %H:%M', time.localtime(reset))}"
    print("WAIT " + why)
    return 1


def limited(vendor: str) -> bool:
    """True when the vendor's windows are readable and spent (a fresh worker would stall): Codex only."""
    if vendor != "codex":
        return False
    w = windows()
    return w["5h"][0] >= 100 or w["week"][0] >= 100
