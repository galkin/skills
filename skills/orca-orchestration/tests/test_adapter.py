"""The adapter against a fake `orca` (tests/fake_orca.py): launch routes, waits, wake-ups,
the mailbox drainer and the budget check."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

from adapter import budget, cli, cost

FAKE = Path(__file__).resolve().parent / "fake_orca.py"


class CliTime:
    """``time`` as adapter/cli.py looks it up (``cli.time``), with a stub ``sleep``.

    Not ``time.sleep`` process-wide: ``orca.call`` runs the fake orca with
    ``subprocess.run(..., timeout=...)``, which polls a child that has closed its pipes but not
    yet exited with ``time.sleep`` (0.0005 s, doubling); a process-wide stub would see those
    polls as the adapter's own pauses. Every other name is the real module's, read on use, so a
    test may still monkeypatch ``time.time``."""

    def __init__(self, sleep):
        self.sleep = sleep

    def __getattr__(self, name):
        return getattr(time, name)


@pytest.fixture
def wt(tmp_path):
    """A worktree with an author and a reviewer role file, for the codex route."""
    w = tmp_path / "wt"
    (w / ".claude" / "agents").mkdir(parents=True)
    for role in ("author", "reviewer"):
        (w / ".claude" / "agents" / f"{role}.md").write_text(f"---\nname: {role}\n---\n\nYou are the **{role}**.\n")
    return str(w)


@pytest.fixture
def orca_env(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    log = tmp_path / "calls.log"
    monkeypatch.setenv("ORCA_CLI_COMMAND", f"{sys.executable} {FAKE}")
    monkeypatch.setenv("FAKE_ORCA_STATE", str(state))
    monkeypatch.setenv("FAKE_ORCA_LOG", str(log))
    monkeypatch.setenv("DAGU_OUTPUT_FILE", str(tmp_path / "out"))
    monkeypatch.setattr(cli, "time", CliTime(lambda s: None))

    class Env:
        def calls(self):
            return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

        def state(self, **update):
            s = json.loads(state.read_text()) if state.exists() else {}
            s.update(update)
            state.write_text(json.dumps(s))
            return s

        def outputs(self):
            p = tmp_path / "out"
            return dict(l.split("=", 1) for l in p.read_text().splitlines()) if p.exists() else {}

        def clear_outputs(self):
            (tmp_path / "out").unlink(missing_ok=True)

    return Env()


def test_claude_route_creates_a_terminal_with_the_role_argv(orca_env, tmp_path):
    rc = cli.main(["run", "--run", "run_1", "--worktree", "/wt/alpha", "--launch", "claude:opus:medium", "--role", "author",
                   "--title", "Author 1.3a", "--spec", "Target: unit 1.3a"])
    assert rc == 0
    calls = orca_env.calls()
    assert calls[0][:2] == ["terminal", "create"]
    assert "claude --agent author --model opus --effort medium --dangerously-skip-permissions" in calls[0]
    assert "path:/wt/alpha" in calls[0]
    assert calls[1][:2] == ["terminal", "wait"] and "tui-idle" in calls[1]
    ws = calls[2]
    assert ws[:2] == ["orchestration", "worker-start"] and "--terminal" in ws and "--agent" not in ws
    assert ws[ws.index("--spec") + 1] == "Target: unit 1.3a"
    assert orca_env.outputs() == {"task": "task_2", "dispatch": "disp_2", "handle": "term_1"}


def test_codex_route_uses_worker_start_with_model_and_effort(orca_env, tmp_path):
    wt = tmp_path / "wt"
    (wt / ".claude" / "agents").mkdir(parents=True)
    (wt / ".claude" / "agents" / "author.md").write_text("---\nname: author\ntools: Read\n---\n\nYou are the **author**.\n")
    rc = cli.main(["run", "--run", "run_1", "--worktree", str(wt), "--launch", "codex:gpt-6.1-sol:medium", "--role", "author",
                   "--title", "Author", "--spec", "x"])
    assert rc == 0
    assert (wt / ".codex" / "config.toml").read_text() == 'developer_instructions = """\nYou are the **author**.\n"""\n'
    calls = orca_env.calls()
    # worker-start, then the handle lookup the receipt does not carry (Orca 1.4.229)
    assert [c[:2] for c in calls] == [["orchestration", "worker-start"], ["orchestration", "dispatch-show"]]
    for flag, value in (("--agent", "codex"), ("--model", "gpt-6.1-sol"), ("--effort", "medium")):
        assert calls[0][calls[0].index(flag) + 1] == value
    assert orca_env.outputs()["task"] == "task_1"


def test_spec_is_text_and_files_joined_in_order(orca_env, wt, tmp_path):
    brief = tmp_path / "author.md"
    brief.write_text("Read the brief.\n")
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t",
              "--spec", "Target: unit 1.3a", "--spec-file", str(brief), "--spec", "Do not commit."])
    ws = orca_env.calls()[0]
    assert ws[ws.index("--spec") + 1] == "Target: unit 1.3a\nRead the brief.\nDo not commit."


def test_reuse_task_injects_into_a_live_terminal_or_starts_fresh(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "reviewer", "--title", "Review r1", "--spec", "r1"])
    orca_env.clear_outputs()
    rc = cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "reviewer", "--title", "Review r2",
                   "--spec", "r2", "--reuse-task", "task_1"])
    assert rc == 0
    kinds = [c[1] for c in orca_env.calls()]
    assert kinds[-2:] == ["task-create", "dispatch"]
    assert "--inject" in orca_env.calls()[-1]
    assert orca_env.outputs()["handle"] == "term_2"
    # the terminal is gone: a fresh worker instead
    s = orca_env.state()
    s["terminals"] = {}
    orca_env.state(terminals={})
    orca_env.clear_outputs()
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "reviewer", "--title", "Review r3",
              "--spec", "r3", "--reuse-task", "task_1"])
    assert [c[1] for c in orca_env.calls()[-2:]] == ["worker-start", "dispatch-show"]


def test_wait_returns_when_the_task_completes(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    s = orca_env.state()
    s["tasks"]["task_1"]["complete_after"] = 3
    orca_env.state(tasks=s["tasks"])
    orca_env.clear_outputs()
    assert cli.main(["wait", "--run", "r", "--task", "task_1", "--poll-sec", "0"]) == 0
    assert orca_env.outputs() == {"status": "completed"}
    assert sum(1 for c in orca_env.calls() if c[1] == "task-list") == 3


def test_wait_exits_4_when_the_task_fails(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    s = orca_env.state()
    s["tasks"]["task_1"].update(complete_after=2, final="failed")
    orca_env.state(tasks=s["tasks"])
    assert cli.main(["wait", "--run", "r", "--task", "task_1", "--poll-sec", "0"]) == cli.EXIT_BAD_TASK
    assert orca_env.outputs()["status"] == "failed"


def test_wait_detects_a_usage_limit_on_the_screen(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    s = orca_env.state()
    s["terminals"]["term_2"]["tail"] = ["some output", "You've hit your usage limit. Try again at 3pm."]
    s["tasks"]["task_1"]["complete_after"] = 50
    orca_env.state(terminals=s["terminals"], tasks=s["tasks"])
    orca_env.clear_outputs()
    # stalled at the start of the wait: the adapter tries one wake-up; the fake does not recover on WAKE here
    s = orca_env.state()
    rc = cli.main(["wait", "--run", "r", "--task", "task_1", "--poll-sec", "0", "--stall-every", "2"])
    assert rc == 0  # the fake terminal "continues" after the wake-up text, so the wait proceeds
    assert any("Continue the task exactly where you stopped" in t for _, t in orca_env.state()["sent"])


def test_wait_exits_5_when_the_limit_appears_mid_task(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    state_path = Path(os.environ["FAKE_ORCA_STATE"])

    # after the first poll the screen shows the limit: patch the state between polls
    original = cli.orca.task_status

    def status_then_stall(run, task):
        st = original(run, task)
        s = json.loads(state_path.read_text())
        s["terminals"]["term_2"]["tail"] = ["You've hit your limit"]
        state_path.write_text(json.dumps(s))
        return st

    cli.orca.task_status = status_then_stall
    try:
        rc = cli.main(["wait", "--run", "r", "--task", "task_1", "--poll-sec", "0", "--stall-every", "1"])
    finally:
        cli.orca.task_status = original
    assert rc == cli.EXIT_STALLED
    assert orca_env.outputs()["status"] == "stalled"


def test_provider_error_schedules_a_reprompt(orca_env, wt, capsys):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    s = orca_env.state()
    s["terminals"]["term_2"]["tail"] = ["■ API Error: 429 Too Many Requests", "›"]
    s["tasks"]["task_1"]["complete_after"] = 3
    orca_env.state(terminals=s["terminals"], tasks=s["tasks"])
    assert cli.main(["wait", "--run", "r", "--task", "task_1", "--poll-sec", "0"]) == 0
    assert "re-prompt in 1 min" in capsys.readouterr().err


def test_unstall_wakes_only_stalled_terminals_outside_the_excluded_worktree(orca_env):
    orca_env.state(terminals={
        "t_coord": {"worktreePath": "/main", "tail": ["hit your usage limit"]},
        "t_a": {"worktreePath": "/wt/alpha", "tail": ["Working"]},
        "t_b": {"worktreePath": "/wt/beta", "tail": ["Keep current model", "hit your usage limit"]},
    })
    assert cli.main(["unstall", "--exclude", "/main"]) == 0
    sent = orca_env.state()["sent"]
    assert [h for h, _ in sent] == ["t_b", "t_b"]
    assert sent[0][1] == "2"


def q(mid, sender, created, subject="Question", body="A or B", kind="question", task=None):
    m = {"id": mid, "type": kind, "run_id": "r", "to_handle": "run:r", "from_handle": sender, "thread_id": mid,
         "subject": subject, "body": body, "created_at": created}
    if task:
        m["payload"] = json.dumps({"taskId": task})
    return m


def attention(out):
    return [l for l in out.splitlines() if l.startswith("ATTENTION")]


def test_drain_acks_benign_batches(orca_env, capsys):
    orca_env.state(messages=[{"deliveryId": "d1", "messages": [{"id": "m1", "type": "heartbeat"}, {"id": "m2", "type": "worker_done"}]}])
    assert cli.main(["drain", "--run", "r", "--once"]) == 0
    assert orca_env.state().get("acked") == ["d1"]
    assert attention(capsys.readouterr().out) == []


def test_drain_prints_every_pending_question_until_it_is_answered(orca_env, capsys, monkeypatch):
    """Two questions, one batch each: both are printed with id, sender and age, on every call,
    until each thread holds a reply (the live defect: the second was never shown)."""
    monkeypatch.setattr(time, "time", lambda: 1792591200.0)  # 2026-10-21T14:00:00Z
    orca_env.state(messages=[
        {"deliveryId": "d1", "messages": [{"id": "h", "type": "heartbeat"}, q("msg_a", "dispatch:ctx_1", "2026-10-21T13:50:00Z", task="task_1")]},
    ])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    assert attention(capsys.readouterr().out) == ["ATTENTION msg_a question from dispatch:ctx_1 task task_1 age 10m | Question | A or B"]
    assert orca_env.state()["acked"] == ["d1"]  # recorded in the inbox, so the batch is acked and the next one comes
    orca_env.state(messages=[{"deliveryId": "d2", "messages": [q("msg_b", "dispatch:ctx_2", "2026-10-21T13:57:00Z", body="line one\nline two")]}])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    lines = attention(capsys.readouterr().out)
    assert [l.split()[1] for l in lines] == ["msg_a", "msg_b"]  # the first is still open: printed again
    assert lines[1] == "ATTENTION msg_b question from dispatch:ctx_2 age 3m | Question | line one line two"
    orca_env.state(messages=[])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION  # no new batch: both still shown
    assert [l.split()[1] for l in attention(capsys.readouterr().out)] == ["msg_a", "msg_b"]
    assert cli.main(["drain", "--run", "r", "--ack", "msg_a", "--body", "Take A."]) == 0  # a reply in its thread
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    assert [l.split()[1] for l in attention(capsys.readouterr().out)] == ["msg_b"]
    assert ["orchestration", "reply", "--id", "msg_a", "--body", "Take A.", "--json"] in orca_env.calls()


def test_drain_finds_a_question_that_arrived_while_no_drain_ran(orca_env, capsys):
    """The inbox is the record: a question another check consumed, or one older than this
    drain, is still printed until answered; another run's and an answered one are not."""
    answered = q("msg_old", "dispatch:ctx_3", "2026-10-21T12:00:00Z")
    orca_env.state(delivered=[q("msg_new", "dispatch:ctx_4", "2026-10-21T13:00:00Z", kind="escalation", subject="Blocked"),
                              answered, {**q("msg_x", "dispatch:ctx_9", "2026-10-21T13:00:00Z"), "run_id": "other", "to_handle": "run:other"}],
                   inbox=[{"id": "msg_re", "thread_id": "msg_old", "from_handle": "run:r", "type": "status", "created_at": "2026-10-21T12:01:00Z"}])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    lines = attention(capsys.readouterr().out)
    assert len(lines) == 1 and lines[0].startswith("ATTENTION msg_new escalation from dispatch:ctx_4 ") and "| Blocked |" in lines[0]


def test_drain_does_not_count_the_askers_own_follow_up_as_an_answer(orca_env, capsys):
    orca_env.state(delivered=[q("msg_a", "dispatch:ctx_1", "2026-10-21T13:00:00Z")],
                   inbox=[{"id": "msg_f", "thread_id": "msg_a", "from_handle": "dispatch:ctx_1", "type": "question", "created_at": "2026-10-21T13:05:00Z"}])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    assert [l.split()[1] for l in attention(capsys.readouterr().out)] == ["msg_a"]


def test_drain_keeps_a_question_batch_unacked_while_the_inbox_is_down(orca_env, capsys):
    orca_env.state(inbox_down=True, messages=[{"deliveryId": "d1", "messages": [q("msg_a", "dispatch:ctx_1", "2026-10-21T13:00:00Z")]}])
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    assert [l.split()[1] for l in attention(capsys.readouterr().out)] == ["msg_a"]  # shown from the batch itself
    assert not orca_env.state().get("acked")  # not recorded anywhere it can be found again: replayed
    orca_env.state(inbox_down=False)
    assert cli.main(["drain", "--run", "r", "--once"]) == cli.EXIT_ATTENTION
    assert orca_env.state()["acked"] == ["d1"]


def test_drain_keeps_running_past_a_question(orca_env, capsys, monkeypatch):
    """The long-running drain does not exit on the first question (that left the second
    unseen for ten minutes): a later one is printed beside the first, at once."""
    orca_env.state(messages=[{"deliveryId": "d1", "messages": [q("msg_a", "dispatch:ctx_1", "2026-10-21T13:00:00Z")]}])
    real, checks = cli.orca.call, []

    class Stop(Exception):
        pass

    def call(*argv, **kw):
        if argv[1] == "check":
            checks.append(argv)
            if len(checks) == 2:  # the second question is sent while the first is still open
                orca_env.state(messages=orca_env.state()["messages"] + [{"deliveryId": "d2", "messages": [q("msg_b", "dispatch:ctx_2", "2026-10-21T13:02:00Z")]}])
            if len(checks) > 3:
                raise Stop
        return real(*argv, **kw)

    monkeypatch.setattr(cli.orca, "call", call)
    with pytest.raises(Stop):
        cli.main(["drain", "--run", "r"])
    ids = [l.split()[1] for l in attention(capsys.readouterr().out)]
    assert ids == ["msg_a", "msg_a", "msg_b"]  # the new one brings every open one back into view
    assert orca_env.state()["acked"] == ["d1", "d2"]


def test_close_and_release(orca_env, wt, capsys):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    assert cli.main(["release", "--task", "task_1"]) == 0
    assert orca_env.calls()[-1][:4] == ["orchestration", "worker-release", "--dispatch", "disp_2"]
    assert cli.main(["close", "--worktree", wt, "--all"]) == 0
    assert orca_env.state()["terminals"] == {}


# ----- budget ------------------------------------------------------------------------


def budget_args(tmp_path, **kw):
    ns = cli.build_parser().parse_args(["budget", "--runs-dir", str(tmp_path / "runs"), "--costs", kw.pop("costs", "author=7.5,fix1=3.5")] + kw.pop("extra", []))
    return ns


def windows(primary, secondary, horizon=3600):
    t = time.time() + horizon
    return {"primary": {"used_percent": primary, "resets_at": t}, "secondary": {"used_percent": secondary, "resets_at": t}}


def test_budget_admits_reserves_running_steps_and_waits(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    (runs / "q").mkdir(parents=True)
    (runs / "q" / "1.3a.active").write_text("alpha\n")
    (runs / "1.3a").mkdir()
    (runs / "1.3a" / "run.json").write_text(json.dumps({"steps": {"author": {"status": "succeeded"}, "fix1": {"status": "not_started"}}}))
    monkeypatch.setattr(budget, "codex_limits", lambda: windows(70, 10))
    # 70 + 3.5 (fix1 still ahead of 1.3a) + 11 new + 3 margin = 87.5 -> admit
    assert budget.main(budget_args(tmp_path, extra=["--why"])) == 0
    assert capsys.readouterr().out.startswith("ADMIT codex: 5h used 70% + running 3.5% (1.3a:3.5%) + new 11%")
    monkeypatch.setattr(budget, "codex_limits", lambda: windows(85, 10))
    assert budget.main(budget_args(tmp_path)) == 1
    assert capsys.readouterr().out.startswith("WAIT ")


def test_budget_topup_and_reset(tmp_path, monkeypatch, capsys):
    (tmp_path / "runs" / "q").mkdir(parents=True)
    monkeypatch.setattr(budget, "codex_limits", lambda: windows(92, 10, horizon=1800))
    assert budget.main(budget_args(tmp_path)) == 0  # nothing running spends Codex: one item anyway
    assert capsys.readouterr().out.startswith("TOPUP ")
    assert budget.main(budget_args(tmp_path, extra=["--reset"])) == 0
    reset = int(capsys.readouterr().out.strip())
    assert abs(reset - (time.time() + 1800)) < 5


def test_budget_expired_window_counts_as_empty(tmp_path, monkeypatch):
    (tmp_path / "runs" / "q").mkdir(parents=True)
    monkeypatch.setattr(budget, "codex_limits", lambda: windows(99, 99, horizon=-10))
    assert budget.main(budget_args(tmp_path)) == 0


# ----- fallback launch ---------------------------------------------------------------


def test_fallback_starts_fresh_when_the_reused_terminal_shows_a_limit(orca_env, wt, monkeypatch):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "Author", "--spec", "a"])
    s = orca_env.state()
    s["terminals"]["term_2"]["tail"] = ["You've hit your usage limit. Try again at 5:00."]
    orca_env.state(terminals=s["terminals"])
    orca_env.clear_outputs()
    rc = cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--fallback", "claude:opus:medium", "--role", "author",
                   "--title", "Author fix r1", "--spec", "fix", "--reuse-task", "task_1"])
    assert rc == 0
    calls = orca_env.calls()
    assert [c[1] for c in calls[-3:]] == ["create", "wait", "worker-start"]  # the claude route, not an injection
    assert "--agent author --model opus" in " ".join(calls[-3])
    assert orca_env.outputs()["handle"] != "term_2"


def test_fallback_replaces_a_spent_vendor_for_a_fresh_worker(orca_env, wt, monkeypatch):
    monkeypatch.setattr(budget, "limited", lambda vendor: vendor == "codex")
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--fallback", "claude:opus:medium", "--role", "author",
              "--title", "Author", "--spec", "a"])
    assert [c[1] for c in orca_env.calls()[-3:]] == ["create", "wait", "worker-start"]
    monkeypatch.setattr(budget, "limited", lambda vendor: False)
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--fallback", "claude:opus:medium", "--role", "author",
              "--title", "Author 2", "--spec", "a"])
    assert "--agent" in orca_env.calls()[-2] and "codex" in orca_env.calls()[-2]


# ----- cost --------------------------------------------------------------------------


def test_cost_reads_claude_and_codex_sessions(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(tmp_path)))
    wt = tmp_path / "slots" / "alpha"
    wt.mkdir(parents=True)
    task = f"Target: worktree {wt}, unit 1.3a (listed in .task/groups/1.3a.md), step review round 1.\nChange: review."
    d = Path(cost.claude_dir(str(wt)))
    d.mkdir(parents=True)
    rows = [
        {"type": "user", "timestamp": "2026-10-19T15:00:00Z", "message": {"role": "user", "content": task}},
        {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 100, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0, "output_tokens": 50}}},
        {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 100, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0, "output_tokens": 50}}},
        {"type": "assistant", "message": {"id": "m2", "usage": {"input_tokens": 10, "cache_creation_input_tokens": 200, "cache_read_input_tokens": 1100, "output_tokens": 30}}},
    ]
    (d / "abcdef12-0000.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    cd = tmp_path / ".codex" / "sessions" / "2026" / "10" / "19"
    cd.mkdir(parents=True)
    atask = f"Target: worktree {wt}, unit 1.3a (listed in .task/groups/1.3a.md), step author.\nChange: write."
    t0 = 1_800_000_000
    crow = [
        {"timestamp": "2026-10-19T14:00:00Z", "type": "session_meta", "payload": {"cwd": str(wt)}},
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": atask}]}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 5000, "cached_input_tokens": 1000, "output_tokens": 100}, "last_token_usage": {"input_tokens": 5000}},
                                          "rate_limits": {"primary": {"used_percent": 10.0, "resets_at": t0}, "secondary": {"used_percent": 1, "resets_at": t0}}}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 20000, "cached_input_tokens": 12000, "output_tokens": 900}, "last_token_usage": {"input_tokens": 15000}},
                                          "rate_limits": {"primary": {"used_percent": 17.5, "resets_at": t0}, "secondary": {"used_percent": 1, "resets_at": t0}}}},
    ]
    (cd / "rollout-2026-10-19T14-00-00-abc.jsonl").write_text("\n".join(json.dumps(r) for r in crow) + "\n")
    assert cli.main(["cost", "--worktree", str(wt), "--json", "--runs-dir", str(tmp_path / "runs")]) == 0
    out = json.loads(capsys.readouterr().out)
    by = {(r["vendor"], r["step"]): r for r in out}
    c = by[("claude", "review1")]
    assert (c["item"], c["calls"], c["fresh"], c["cached"], c["out"], c["ctx"]) == ("1.3a", 2, 1310, 1100, 80, 1310)
    a = by[("codex", "author")]
    assert (a["item"], a["calls"], a["fresh"], a["cached"], a["out"], a["ctx"], a["window"]) == ("1.3a", 2, 8000, 12000, 900, 15000, 7.5)
    (tmp_path / "runs" / "1.3a").mkdir(parents=True)
    assert cli.main(["cost", "--worktree", str(wt), "--write", "--runs-dir", str(tmp_path / "runs")]) == 0
    rec = json.loads((tmp_path / "runs" / "1.3a" / "cost.json").read_text())
    assert rec["author"]["window"] == 7.5 and rec["review1"]["vendor"] == "claude"
    assert "total fresh" in capsys.readouterr().out


def test_cost_classifies_pass_chunks():
    assert cost.classify("Target: worktree /w, quiz chunk 2-3, step write.") == ("quiz-2-3", "write")
    assert cost.classify("Target: worktree /w, unit 0b (listed in .task/groups/0b.md), step fix round 2.") == ("0b", "fix2")
    assert cost.classify("Target: worktree /w, unit 0b (listed in .task/groups/0b.md), step review round 10.") == ("0b", "review10")
    assert cost.classify("Review the chunk 3, step write")[0] == ""  # prose is not a Task
    assert cost.classify("hello there")[0] == ""


def test_cost_skips_log_lines_it_does_not_understand(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text('[]\nnull\n{"type": "assistant", "message": {"id": "m", "usage": {"input_tokens": 3, "output_tokens": 1}}}\n')
    assert cost.scan_claude(str(f))["calls"] == 1
    assert cost.scan_codex(str(f))["calls"] == 0


def test_budget_tolerates_unknown_window_shapes():
    assert budget.used({"used_percent": "12", "resets_at": "soon"}) == (0.0, None)
    assert budget.used({"used_percent": 12, "resets_at": str(int(time.time()) + 100)})[0] == 12.0
    with pytest.raises(SystemExit):
        budget.parse_costs("author")
    with pytest.raises(SystemExit):
        budget.parse_costs("claude:review1=4")  # Claude steps are not priced


def test_budget_reset_knows_only_codex_steps(tmp_path, monkeypatch, capsys):
    (tmp_path / "runs" / "q").mkdir(parents=True)
    tc = time.time() + 3600
    monkeypatch.setattr(budget, "codex_limits", lambda: windows(50, 10))  # resets in 1 h
    costs = "author=7.5,fix1=3.5"
    # a Codex step stalled: Codex's reset
    assert budget.main(budget_args(tmp_path, costs=costs, extra=["--reset", "--step", "author"])) == 0
    assert abs(int(capsys.readouterr().out.strip()) - tc) < 5
    # a step --costs does not price (a Claude review): no time, exit 1 (the queue's own fallback wait)
    assert budget.main(budget_args(tmp_path, costs=costs, extra=["--reset", "--step", "review1"])) == 1
    assert "not a priced Codex step" in capsys.readouterr().out
    # no step known (the hook run by hand): the fullest Codex window
    monkeypatch.delenv("STEP", raising=False)
    assert budget.main(budget_args(tmp_path, costs=costs, extra=["--reset"])) == 0
    assert abs(int(capsys.readouterr().out.strip()) - tc) < 5


# ----- step 2 of ticket 03: templates, language, the ledger, outages, cleanup scope ----------


def test_spec_template_resolves_dagu_references_and_spec_file_stays_literal(orca_env, wt, tmp_path, monkeypatch):
    monkeypatch.setenv("DAG_PARAMS_JSON", json.dumps({"unit": "1.3a"}))
    monkeypatch.setenv("ROUND", "2")
    t = tmp_path / "review.md"
    t.write_text("Unit ${params.unit}, round ${env.ROUND}, literal \\${params.unit}.\n")
    b = tmp_path / "brief.md"
    b.write_text("Code: ${params.unit} stays.\n")
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t",
              "--spec-template", str(t), "--spec-file", str(b)])
    ws = orca_env.calls()[0]
    assert ws[ws.index("--spec") + 1] == "Unit 1.3a, round 2, literal ${params.unit}.\nCode: ${params.unit} stays."
    t.write_text("No such ${params.nope}.\n")
    with pytest.raises(SystemExit, match=r"\$\{params.nope\} is not defined"):
        cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec-template", str(t)])


def test_language_reaches_the_claude_command_only(orca_env, wt):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "claude:opus:medium", "--role", "author", "--title", "t",
              "--spec", "x", "--language", "English"])
    create = orca_env.calls()[0]
    assert create[:2] == ["terminal", "create"]
    assert create[create.index("--command") + 1].endswith("""--dangerously-skip-permissions --settings '{"language": "English"}'""")
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t",
              "--spec", "x", "--language", "English"])
    assert "--settings" not in " ".join(orca_env.calls()[-2])  # worker-start --agent codex: the role body carries the language


def test_ledger_records_launches_and_followups(orca_env, wt, tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setenv("DAG_RUN_WORK_DIR", str(runs / "1.3a"))
    monkeypatch.setenv("DAG_RUN_ID", "1.3a")
    monkeypatch.setenv("DAG_RUN_STEP_NAME", "author")
    cli.main(["run", "--run", "run_1", "--worktree", wt, "--launch", "codex:gpt:medium", "--role", "author", "--title", "Author 1.3a", "--spec", "x"])
    monkeypatch.setenv("DAG_RUN_STEP_NAME", "fix1")
    cli.main(["run", "--run", "run_1", "--worktree", wt, "--launch", "codex:gpt:medium", "--role", "author", "--title", "Author 1.3a fix r1",
              "--spec", "y", "--reuse-task", "task_1"])
    rows = [json.loads(l) for l in (runs / "adapter" / "launches.jsonl").read_text().splitlines()]
    assert [(r["kind"], r["item"], r["step"], r["vendor"], r["model"], r["task"]) for r in rows] == [
        ("start", "1.3a", "author", "codex", "gpt", "task_1"),
        ("followup", "1.3a", "fix1", "codex", "gpt", "task_3"),
    ]
    assert rows[0]["handle"] == rows[1]["handle"] == "term_2" and rows[1]["worktree"] == wt
    assert rows[0]["run"] == "run_1" and rows[0]["dispatch"] == "disp_2"


def test_cost_joins_sessions_on_the_ledger_before_the_task_text(tmp_path, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(tmp_path)))
    wt = tmp_path / "slots" / "alpha"
    wt.mkdir(parents=True)
    runs = tmp_path / "runs"
    (runs / "adapter").mkdir(parents=True)
    (runs / "adapter" / "launches.jsonl").write_text(json.dumps({"task": "task_9", "item": "2.1", "step": "review2", "vendor": "claude"}) + "\n")
    d = Path(cost.claude_dir(str(wt)))
    d.mkdir(parents=True)
    preamble = "Please carry out this task.\nYou are a dispatched worker.\nYour task ID is: task_9\n\nLook at the chunk and judge it."
    rows = [
        {"type": "user", "timestamp": "2026-10-20T15:00:00Z", "message": {"role": "user", "content": preamble}},
        {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 100, "output_tokens": 5}}},
    ]
    (d / "aaaa0000-1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    old = [{"type": "user", "timestamp": "2026-10-20T15:00:00Z",
            "message": {"role": "user", "content": "Your task ID is: task_7\nTarget: worktree /w, unit 0b (listed in .task/groups/0b.md), step author."}},
           {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 1, "output_tokens": 1}}}]
    (d / "bbbb0000-1.jsonl").write_text("\n".join(json.dumps(r) for r in old) + "\n")
    got = {r["session"]: (r["item"], r["step"]) for r in cost.sessions([str(wt)], 12, str(runs))}
    assert got["aaaa0000"] == ("2.1", "review2")  # the ledger, though the text has no Task grammar
    assert got["bbbb0000"] == ("0b", "author")  # not in the ledger: the text


def test_wait_keeps_polling_while_orca_is_unavailable(orca_env, wt, tmp_path, monkeypatch, capsys):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    down = tmp_path / "down"
    down.write_text("3")  # the screen check at the start of the wait takes the first failing call (check=False)
    monkeypatch.setenv("FAKE_ORCA_DOWN", str(down))
    monkeypatch.setenv("FAKE_ORCA_AUTOCOMPLETE", "1")
    assert cli.main(["wait", "--run", "r", "--task", "task_1", "--handle", "term_2", "--poll-sec", "0", "--runtime-wait", "30"]) == 0
    err = capsys.readouterr().err
    assert err.count("Orca unavailable") == 2 and "Orca is back" in err
    down.write_text("3")
    assert cli.main(["wait", "--run", "r", "--task", "task_1", "--handle", "term_2", "--poll-sec", "0", "--runtime-wait", "0"]) == 1
    assert "Orca unavailable for 0 min" in capsys.readouterr().err


def test_close_releases_only_the_pipelines_settled_terminals(orca_env, wt, tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    monkeypatch.setenv("RUNS_DIR", str(runs))
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "reviewer", "--title", "t2", "--spec", "x"])
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "claude:opus:e", "--role", "verifier", "--title", "t3", "--spec", "x"])
    # a fix round into the author's terminal: its task settles the terminal, the start dispatch still owns it
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "fix", "--spec", "y", "--reuse-task", "task_1"])
    s = orca_env.state()
    s["terminals"]["term_user"] = {"worktreePath": wt, "tail": ["$"]}  # the owner's own terminal in the slot
    for t in ("task_1", "task_3", "task_6", "task_7"):  # the fake numbers terminals and tasks from one counter
        s["tasks"][t]["status"] = "completed"
    s["retained"] = ["disp_4"]  # the reviewer's terminal was taken over by the user
    s["external"] = ["disp_6"]  # the claude route: a terminal the adapter created (term_5)
    orca_env.state(**s)
    assert cli.main(["close", "--worktree", wt]) == 0  # keeping is not a failure: the work is merged by now
    err = capsys.readouterr().err
    assert "released term_2 (task task_7 completed)" in err  # settled by the follow-up's task, released by disp_2
    assert "kept term_4: worker-release refused: retained: user_takeover" in err
    assert "closed term_5 (task task_6 completed; Orca never owned it: retained: external_terminal)" in err
    assert "kept term_user: not started by the adapter" in err
    assert "1 terminal(s) of" in err  # the refused one; the owner's own terminal is named but not counted
    assert orca_env.state()["released"] == ["disp_2"]
    assert set(orca_env.state()["terminals"]) == {"term_2", "term_4", "term_user"}  # release is Orca's; the external one closed
    s = orca_env.state()
    s["tasks"]["task_7"]["status"] = "running"
    s["retained"] = []
    orca_env.state(**s)
    assert cli.main(["close", "--worktree", wt]) == 0
    assert "kept term_2: task task_7 is running" in capsys.readouterr().err
    assert cli.main(["close", "--worktree", wt, "--all"]) == 0
    assert orca_env.state()["terminals"] == {}


def test_close_keeps_a_terminal_the_adapter_only_re_tasked(orca_env, wt, tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    monkeypatch.setenv("RUNS_DIR", str(runs))
    # a worker started by hand (no ledger record), then re-tasked through followup
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x", "--runs-dir", str(tmp_path / "elsewhere")])
    cli.main(["followup", "--run", "r", "--handle", "term_2", "--title", "more", "--spec", "y"])
    s = orca_env.state()
    s["tasks"]["task_3"]["status"] = "completed"
    orca_env.state(**s)
    assert cli.main(["close", "--worktree", wt]) == 0
    assert "kept term_2: not started by the adapter (re-tasked only" in capsys.readouterr().err
    assert "term_2" in orca_env.state()["terminals"] and not orca_env.state().get("released")


def test_close_without_a_ledger_closes_nothing(orca_env, wt, capsys):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    assert cli.main(["close", "--worktree", wt]) == 0
    assert "nothing closed" in capsys.readouterr().err
    assert "term_2" in orca_env.state()["terminals"]


def test_release_reports_a_refused_release(orca_env, wt, capsys):
    cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "t", "--spec", "x"])
    orca_env.state(retained=["disp_2"])
    assert cli.main(["release", "--task", "task_1"]) == 1
    assert "retained: user_takeover" in capsys.readouterr().err
    orca_env.state(retained=[])
    assert cli.main(["release", "--task", "task_1"]) == 0


# ----- run --wait: a one-off worker to completion -------------------------------------


def one_off(wt, *extra, launch="codex:m:e"):
    return cli.main(["run", "--worktree", wt, "--launch", launch, "--role", "author", "--title", "One-off", "--spec", "x",
                     "--wait", "--poll-sec", "0", *extra])


def test_run_wait_surfaces_a_question_prints_the_done_message_and_frees_the_terminal(orca_env, wt, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_ORCA_AUTOCOMPLETE", "3")
    orca_env.state(bound="run_b",  # no --run: the bound Run
                   on_start=[{"type": "heartbeat", "subject": "alive"},
                             {"type": "question", "subject": "Question", "body": "A or B?", "payload": {"options": ["A", "B"]}}],
                   done_message={"subject": "Cast drafted", "body": "Wrote cast.yaml.\nTwo open points.",
                                 "payload": {"outcome": "succeeded", "reportPath": ".task/reports/cast.md"}})
    assert one_off(wt) == 0
    out = capsys.readouterr()
    lines = out.out.splitlines()
    assert "no --run: using the bound Run run_b" in out.err
    q_line = next(l for l in lines if l.startswith("QUESTION"))
    assert q_line.startswith("QUESTION msg_4 run run_b from dispatch:disp_2 task task_1 | Question | A or B? | options: A / B")
    assert "run-use" not in q_line  # the bound Run: the reply needs no rebinding
    assert "  reply: orca orchestration reply --id msg_4 --body '…'" in lines
    assert not any(l.startswith("HEARTBEAT") for l in lines)
    done = lines.index(next(l for l in lines if l.startswith("DONE")))
    assert lines[done:done + 4] == ["DONE succeeded msg_5 task task_1 | Cast drafted", "Wrote cast.yaml.", "Two open points.",
                                    "report .task/reports/cast.md"]
    assert ["orchestration", "worker-release", "--dispatch", "disp_2", "--json"] in orca_env.calls()
    assert "released term_2" in out.err
    assert ["orchestration", "worker-start"] == next(c for c in orca_env.calls() if c[1] == "worker-start")[:2]
    assert next(c for c in orca_env.calls() if c[1] == "worker-start")[3] == "run_b"


def test_run_wait_closes_a_claude_route_terminal_and_keep_terminal_keeps_it(orca_env, wt, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_ORCA_AUTOCOMPLETE", "2")
    orca_env.state(bound="r", external=["disp_2"], done_message={"subject": "Done", "payload": {"outcome": "succeeded"}})
    assert one_off(wt, launch="claude:opus:medium") == 0
    assert "closed term_1" in capsys.readouterr().err
    assert "term_1" not in orca_env.state()["terminals"]  # Orca never owned it: terminal close
    orca_env.state(done_message={"subject": "Done", "payload": {"outcome": "succeeded"}})
    assert one_off(wt, "--keep-terminal") == 0
    assert "kept (--keep-terminal)" in capsys.readouterr().err
    assert sum(1 for c in orca_env.calls() if c[1] == "worker-release") == 1


def test_run_wait_stops_on_an_escalation_and_keeps_the_terminal(orca_env, wt, capsys):
    orca_env.state(bound="r", on_start=[{"type": "escalation", "subject": "Blocked", "body": "The batch API is down."}])
    assert one_off(wt) == cli.EXIT_ATTENTION
    out = capsys.readouterr()
    assert any(l.startswith("ESCALATION msg_3 run r ") and "| Blocked | The batch API is down." in l for l in out.out.splitlines())
    assert not any(c[1] == "worker-release" for c in orca_env.calls())
    assert orca_env.outputs()["status"] == "escalation"


def test_run_wait_reports_a_task_completed_without_a_worker_done(orca_env, wt, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_ORCA_AUTOCOMPLETE", "2")
    orca_env.state(bound="r")
    assert one_off(wt) == 0
    assert "DONE task task_1 completed without a worker_done message" in capsys.readouterr().out


def test_run_without_a_run_needs_a_binding(orca_env, wt):
    with pytest.raises(SystemExit, match="bound to no Run"):
        one_off(wt)


# ----- watch ----------------------------------------------------------------------------


def msg(mid, run, kind, created, subject="", body="", thread=None, sender="dispatch:ctx_1", **payload):
    return {"id": mid, "type": kind, "run_id": run, "to_handle": f"run:{run}", "from_handle": sender, "thread_id": thread,
            "created_at": created, "subject": subject, "body": body, "payload": json.dumps(payload)}


def test_watch_prints_new_events_of_every_run_once_and_drops_heartbeats(orca_env, tmp_path, capsys):
    state = tmp_path / "watch.json"
    runs_file = tmp_path / "runs"
    runs_file.write_text("run_a  # the queue's Run\nrun_b\n")
    orca_env.state(bound="run_a", inbox=[
        msg("m1", "run_a", "worker_done", "01", "Old unit", outcome="succeeded"),       # history: not printed on the first start
        msg("m2", "run_b", "question", "02", "Question", "Answered already?", thread="m2"),
        {"id": "m3", "thread_id": "m2", "from_handle": "run:run_b", "type": "status", "created_at": "03"},
        msg("m4", "run_b", "question", "04", "Question", "Still open?", thread="m4", taskId="task_9"),
    ])
    assert cli.main(["watch", "--runs-file", str(runs_file), "--state", str(state), "--once"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].split(" ", 1)[1] == (
        "QUESTION m4 run run_b from dispatch:ctx_1 task task_9 | Question | Still open? | bound to run_a: orca orchestration run-use --id run_b before replying")
    orca_env.state(inbox=orca_env.state()["inbox"] + [
        msg("m5", "run_a", "heartbeat", "05", "alive"),
        msg("m6", "run_a", "worker_done", "06", "Unit 2 done", "Body", outcome="succeeded", reportPath="r.md"),
        msg("m7", "run_c", "question", "07", "Question", "Not watched", thread="m7"),
        msg("m8", "run_a", "escalation", "08", "Blocked", "Need a decision"),
    ])
    assert cli.main(["watch", "--runs-file", str(runs_file), "--state", str(state), "--once"]) == 0  # a restart
    lines = [l.split(" ", 1)[1] for l in capsys.readouterr().out.splitlines()]
    assert lines == ["DONE succeeded m6 run run_a from dispatch:ctx_1 | Unit 2 done | Body | report r.md",
                     "ESCALATION m8 run run_a from dispatch:ctx_1 | Blocked | Need a decision"]
    runs_file.write_text("run_a\nrun_b\nrun_c\n")  # a Run added while it runs
    assert cli.main(["watch", "--runs-file", str(runs_file), "--state", str(state), "--once"]) == 0
    assert [l.split()[2] for l in capsys.readouterr().out.splitlines()] == ["m7"]
    assert not any(c[1] == "check" or c[1] == "run-use" for c in orca_env.calls())  # nothing consumed, nothing rebound


def test_watch_follows_the_slot_logs_for_holds_and_stalls(orca_env, tmp_path, capsys):
    log = tmp_path / "slots.log"
    log.write_text("09:00 slot alpha 1.1 HELD: an old hold, before the watch\n")
    state = tmp_path / "watch.json"
    args = ["watch", "--run", "r", "--log", str(log), "--state", str(state), "--once"]
    assert cli.main(args) == 0
    assert capsys.readouterr().out == ""  # a log is followed from its end when first seen
    with log.open("a") as f:
        f.write("10:00 slot alpha 1.2 start\n10:05 slot alpha 1.2 stalled at author: waits until 25 15:00\n"
                "10:06 slot beta 1.3 HELD: step review exit 1, attempt 1, log x\n10:07 slot beta partial")
    assert cli.main(args) == 0
    assert capsys.readouterr().out.splitlines() == ["SLOT 10:05 slot alpha 1.2 stalled at author: waits until 25 15:00",
                                                    "SLOT 10:06 slot beta 1.3 HELD: step review exit 1, attempt 1, log x"]
    with log.open("a") as f:
        f.write(" line done\n10:08 slot beta queue empty\n")
    assert cli.main(args) == 0
    assert capsys.readouterr().out.splitlines() == ["SLOT 10:08 slot beta queue empty"]


def test_watch_keeps_going_while_the_inbox_is_down(orca_env, tmp_path, capsys):
    orca_env.state(inbox_down=True)
    assert cli.main(["watch", "--run", "r", "--state", str(tmp_path / "w.json"), "--once"]) == 0
    assert "inbox unavailable" in capsys.readouterr().err


# ----- close --run and drain under another binding ------------------------------------------


def test_close_run_frees_the_settled_worker_terminals_of_a_run(orca_env, wt, monkeypatch, capsys):
    for title in ("a", "b", "c", "d"):
        cli.main(["run", "--run", "r", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", title, "--spec", "x"])
    cli.main(["run", "--run", "other", "--worktree", wt, "--launch", "codex:m:e", "--role", "author", "--title", "e", "--spec", "x"])
    s = orca_env.state()
    for t in ("task_1", "task_3", "task_5", "task_9"):
        s["tasks"][t]["status"] = "completed"
    # task_1 term_2 settled; task_3 term_4 settled, the user took it; task_5 term_6 settled, claude route;
    # task_7 term_8 still running; task_9 term_10 another Run's
    orca_env.state(tasks=s["tasks"], retained=["disp_4"], external=["disp_6"])
    monkeypatch.setenv("ORCA_TERMINAL_HANDLE", "term_coordinator")
    capsys.readouterr()
    assert cli.main(["close", "--run", "r"]) == 0
    err = capsys.readouterr().err
    assert "released term_2" in err and "closed term_6" in err
    assert "kept term_4: worker-release refused: retained: user_takeover" in err
    assert "kept term_8: dispatch disp_8 is dispatched" in err
    assert "run r: 2 terminal(s) freed, 2 kept" in err
    assert set(orca_env.state()["terminals"]) == {"term_2", "term_4", "term_8", "term_10"}  # released stays listed in the fake
    assert ["orchestration", "worker-release", "--dispatch", "disp_10", "--json"] not in orca_env.calls()


def test_drain_pauses_instead_of_spinning_when_its_run_is_fenced(orca_env, monkeypatch, capsys):
    """The coordinator ran run-use for another Run: check --run answers consumer_fenced at once."""
    orca_env.state(bound="other")
    pauses = []

    class Stop(Exception):
        pass

    def sleep(sec):
        pauses.append(sec)
        if len(pauses) > 1:
            raise Stop

    monkeypatch.setattr(cli, "time", CliTime(sleep))
    with pytest.raises(Stop):
        cli.main(["drain", "--run", "r"])
    assert pauses == [30, 30]
    assert "check --run r refused: This coordinator terminal is bound to other, not r." in capsys.readouterr().err
