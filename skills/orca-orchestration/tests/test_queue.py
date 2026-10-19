"""The queue keeps slot.sh's rules: groups, holds, resume, admission and stall hooks."""

import textwrap
from pathlib import Path

import pytest

from runner.queue import Slot, load_queue
from runner.spec import SpecError

WORKFLOW = """
    params:
      - {name: unit, required: true}
      - {name: slot, required: true}
      - {name: fail_file, default: ""}
      - {name: exit_code, default: "1"}
    steps:
      - id: work
        run: |
          echo "${params.unit} in ${params.slot}" >> "$DAG_RUN_WORK_DIR/../order"
          if [ -n "${params.fail_file}" ] && [ -f "${params.fail_file}" ]; then exit ${params.exit_code}; fi
      - id: after
        depends: work
        run: echo after
    """


def setup(tmp_path, queue_text):
    (tmp_path / "wf.yaml").write_text(textwrap.dedent(WORKFLOW))
    (tmp_path / "queue.yaml").write_text(textwrap.dedent(queue_text))
    return load_queue(str(tmp_path / "queue.yaml")), tmp_path / "runs"


def slot(q, runs, tmp_path, name="alpha"):
    return Slot(q, runs, str(tmp_path / name), poll_sec=0.01)


def order(runs):
    return (runs / "order").read_text().split("\n")[:-1]


def test_items_run_in_order_and_groups_serialize(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        items:
          - {id: 2.1a, group: "2.1", params: {unit: 2.1a}}
          - {id: 2.1b, group: "2.1", params: {unit: 2.1b}}
          - {id: 2.2a, group: "2.2", params: {unit: 2.2a}}
        """)
    assert slot(q, runs, tmp_path).loop() == 0
    assert [o.split()[0] for o in order(runs)] == ["2.1a", "2.1b", "2.2a"]
    assert all((runs / "q" / f"{i}.done").exists() for i in ["2.1a", "2.1b", "2.2a"])


def test_a_second_slot_skips_a_group_that_is_active_elsewhere(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        items:
          - {id: 2.1a, group: "2.1", params: {unit: 2.1a}}
          - {id: 2.1b, group: "2.1", params: {unit: 2.1b}}
          - {id: 2.2a, group: "2.2", params: {unit: 2.2a}}
        """)
    s = slot(q, runs, tmp_path, "beta")
    (runs / "q").mkdir(parents=True, exist_ok=True)
    (runs / "q" / "2.1a.active").write_text("alpha\n")  # another slot holds group 2.1
    picked = s.pick()
    assert picked.id == "2.2a"


def test_last_group_waits_for_everything_else(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        last_group: "0"
        items:
          - {id: 0.1, group: "0", params: {unit: 0.1}}
          - {id: 1.1, group: "1", params: {unit: 1.1}}
        """)
    assert slot(q, runs, tmp_path).loop() == 0
    assert [o.split()[0] for o in order(runs)] == ["1.1", "0.1"]


def test_failure_holds_the_item_and_resume_continues(tmp_path):
    flag = tmp_path / "fail"
    flag.write_text("")
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        params: {{fail_file: {flag}}}
        items:
          - {{id: a, params: {{unit: a}}}}
          - {{id: b, params: {{unit: b}}}}
        """)
    s = slot(q, runs, tmp_path)
    assert s.loop() == 2  # a is held, the slot exits so the coordinator wakes
    assert (runs / "q" / "a.held").read_text().startswith("step work exit 1")
    assert not (runs / "b").exists()  # b did not start: the slot stopped on the hold
    flag.unlink()  # the coordinator "decides"
    assert slot(q, runs, tmp_path).loop(resume="a", resume_step="work") == 0
    assert (runs / "q" / "a.done").exists() and (runs / "q" / "b.done").exists()
    assert [o.split()[0] for o in order(runs)] == ["a", "a", "b"]


def test_stall_exit_code_waits_and_retries_instead_of_holding(tmp_path):
    flag = tmp_path / "limit"
    flag.write_text("")
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        stall_exit_code: 5
        params: {{fail_file: {flag}, exit_code: "5"}}
        hooks:
          stall: test "$STEP" = work && rm -f {flag} && date +%s
        items:
          - {{id: a, params: {{unit: a}}}}
        """)
    s = slot(q, runs, tmp_path)
    s.stall_margin = 0
    s.loop()  # the stall hook clears the limit and says "now"
    assert (runs / "q" / "a.done").exists()
    assert [o.split()[0] for o in order(runs)] == ["a", "a"]
    assert "stalled at work" in (runs / "slots.log").read_text()


def test_admission_hook_idles_the_slot_until_it_admits(tmp_path):
    gate = tmp_path / "gate"
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        hooks:
          admission: test -f {gate} || {{ echo "WAIT window at 90%"; touch {gate}; exit 1; }}
        items:
          - {{id: a, params: {{unit: a}}}}
        """)
    assert slot(q, runs, tmp_path).loop() == 0
    log = (runs / "slots.log").read_text()
    assert "waiting: WAIT window at 90%" in log and "admitted again" in log


def test_before_hook_failure_holds_without_running(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        hooks:
          before: echo dirty; exit 6
        items:
          - {id: a, params: {unit: a}}
        """)
    assert slot(q, runs, tmp_path).loop() == 2
    assert (runs / "q" / "a.held").read_text().startswith("before hook exit 6: dirty")
    assert not (runs / "a").exists()


def test_retire_file_stops_an_idle_slot(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        items:
          - {id: a, params: {unit: a}}
        """)
    (runs / "q").mkdir(parents=True, exist_ok=True)
    (runs / "q" / "retire-alpha").write_text("")
    assert slot(q, runs, tmp_path).loop() == 0
    assert not (runs / "a").exists()


def test_only_held_items_exit_7(tmp_path):
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        items:
          - {id: a, params: {unit: a}}
        """)
    (runs / "q").mkdir(parents=True, exist_ok=True)
    (runs / "q" / "a.held").write_text("step work exit 1\n")
    assert slot(q, runs, tmp_path).loop() == 7


def test_queue_file_validation(tmp_path):
    with pytest.raises(SpecError, match="unknown queue field"):
        setup(tmp_path, "workflow: wf.yaml\nitems: []\nslots: 3\n")
    with pytest.raises(SpecError, match="unknown hook"):
        setup(tmp_path, "workflow: wf.yaml\nitems: []\nhooks: {after: x}\n")
    with pytest.raises(SpecError, match="needs an id"):
        setup(tmp_path, "workflow: wf.yaml\nitems: [{group: x}]\n")


def test_every_item_is_validated_before_the_first_hook(tmp_path):
    touched = tmp_path / "touched"
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        hooks:
          before: touch {touched}
        items:
          - {{id: good, params: {{unit: y}}}}
          - {{id: bad, params: {{unit: x, nosuch: 1}}}}
        """)
    with pytest.raises(SpecError, match="item bad: .*nosuch"):
        slot(q, runs, tmp_path)
    assert not touched.exists() and not (runs / "good").exists()


def test_working_dir_and_env_reach_the_hooks_and_the_runtime_names_win(tmp_path):
    (tmp_path / "sub").mkdir()
    q, runs = setup(tmp_path, """
        workflow: wf.yaml
        slot_param: slot
        working_dir: sub
        env: {TOKEN: tok, SLOT: bogus}
        hooks:
          before: echo "$(pwd) $TOKEN $SLOT" > "$RUNS_DIR/where"
        items:
          - {id: a, params: {unit: a}}
        """)
    assert q.working_dir == str(tmp_path / "sub")
    assert slot(q, runs, tmp_path).loop() == 0
    assert (runs / "where").read_text().split() == [str(tmp_path / "sub"), "tok", str(tmp_path / "alpha")]
    with pytest.raises(SpecError, match="working_dir .* is not a directory"):
        setup(tmp_path, "workflow: wf.yaml\nitems: []\nworking_dir: nowhere\n")
    with pytest.raises(SpecError, match="env must be a map"):
        setup(tmp_path, "workflow: wf.yaml\nitems: []\nenv: [A=1]\n")


def test_a_held_item_names_the_step_exit_attempt_and_log(tmp_path):
    from runner import engine
    from runner.queue import queue_status

    flag = tmp_path / "fail"
    flag.write_text("")
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        params: {{fail_file: {flag}}}
        items:
          - {{id: a, params: {{unit: a}}}}
        """)
    assert slot(q, runs, tmp_path).loop() == 2
    log = runs / "a" / "steps" / "work.1.log"
    assert (runs / "q" / "a.held").read_text().strip() == f"step work exit 1, attempt 1, log {log}"
    assert f"held    step work exit 1, attempt 1, log {log}" in queue_status(runs, q)
    assert f"work            failed               exit=1 attempts=1 log={log}" in engine.status_text(engine.load_state(runs, "a"), runs)


def test_queue_adopts_a_run_started_by_hand(tmp_path):
    """A run started with `runner run` under the same runs dir and id is resumed, not restarted."""
    from runner import engine
    from runner.spec import load

    flag = tmp_path / "fail"
    flag.write_text("")
    q, runs = setup(tmp_path, f"""
        workflow: wf.yaml
        slot_param: slot
        params: {{fail_file: {flag}}}
        items:
          - {{id: a, params: {{unit: a}}}}
        """)
    dag = load(str(tmp_path / "wf.yaml"))
    # by hand, in another worktree: "work" fails, "after" is canceled
    assert engine.start(dag, {"unit": "a", "slot": "by-hand", "fail_file": str(flag), "exit_code": "1"}, runs, "a") == "failed"
    flag.unlink()
    assert slot(q, runs, tmp_path).loop() == 0
    assert (runs / "q" / "a.done").exists()
    assert order(runs) == ["a in by-hand", "a in by-hand"]  # resumed with the hand run's own params
