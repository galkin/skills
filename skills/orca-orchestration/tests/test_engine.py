"""End-to-end runs of small workflows through the engine, driven by Dagu's own examples."""

import json
import textwrap
import time
from pathlib import Path

import pytest

from runner import engine
from runner.spec import load, resolve_params


def run(tmp_path, text, params=None, run_id="r1"):
    wf = tmp_path / "wf.yaml"
    wf.write_text(textwrap.dedent(text))
    dag = load(str(wf))
    status = engine.start(dag, resolve_params(dag, params or {}), tmp_path / "runs", run_id)
    return status, engine.load_state(tmp_path / "runs", run_id), dag


def test_outputs_flow_between_steps_via_env(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: build
            run: printf 'image=v1.2.3\\n' >> "$DAGU_OUTPUT_FILE"
            outputs:
              - name: image
          - id: deploy
            depends: build
            env:
              IMAGE: ${steps.build.outputs.image}
            run: echo "deploying $IMAGE" > "$DAG_RUN_WORK_DIR/deployed"
        """)
    assert status == "succeeded"
    assert st.steps["build"].outputs == {"image": "v1.2.3"}
    assert (tmp_path / "runs" / "r1" / "deployed").read_text() == "deploying v1.2.3\n"


def test_stdout_is_not_an_output(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: build
            run: echo image_tag=v1.2.3
            outputs:
              - name: image_tag
        """)
    assert status == "failed"
    assert "not emitted" in st.steps["build"].error


def test_precondition_skip_and_continue_on_skipped(tmp_path):
    status, st, _ = run(tmp_path, """
        env:
          FEATURE_FLAG: disabled
        steps:
          - id: enable_feature
            run: echo enabling
            preconditions:
              - condition: "${env.FEATURE_FLAG}"
                expected: enabled
            continue_on: skipped
          - id: process
            depends: enable_feature
            run: echo processing
          - id: strict
            run: echo never
            preconditions:
              - condition: "${env.FEATURE_FLAG}"
                expected: enabled
          - id: after_strict
            depends: strict
            run: echo never
        """)
    assert status == "failed"
    assert st.steps["enable_feature"].status == "skipped"
    assert st.steps["process"].status == "succeeded"
    assert st.steps["strict"].status == "skipped"
    assert st.steps["after_strict"].status == "canceled"


def test_continue_on_failure_gives_partial_success_and_runs_success_handler(tmp_path):
    status, st, _ = run(tmp_path, """
        handler_on:
          success:
            run: echo ok > "$DAG_RUN_WORK_DIR/success"
          failure:
            run: echo bad > "$DAG_RUN_WORK_DIR/failure"
          exit:
            run: echo "$DAG_RUN_STATUS" > "$DAG_RUN_WORK_DIR/exit"
        steps:
          - id: optional
            run: exit 1
            continue_on:
              failure: true
          - id: after
            depends: optional
            run: echo after
        """)
    assert status == "partially_succeeded"
    assert st.steps["optional"].status == "failed" and st.steps["optional"].continued
    assert st.steps["after"].status == "succeeded"
    assert (tmp_path / "runs" / "r1" / "success").exists()
    assert not (tmp_path / "runs" / "r1" / "failure").exists()
    assert (tmp_path / "runs" / "r1" / "exit").read_text().strip() == "partially_succeeded"


def test_continue_on_exit_code_output_and_mark_success(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: check_status
            run: exit 2
            continue_on:
              exit_code: [0, 1, 2]
              mark_success: true
          - id: validate
            run: echo "[WARN] something"; exit 3
            continue_on:
              output:
                - 're:^\\[WARN\\]'
          - id: process
            depends: [check_status, validate]
            run: echo processing
        """)
    assert status == "partially_succeeded"
    assert st.steps["check_status"].status == "succeeded"
    assert st.steps["validate"].status == "failed" and st.steps["validate"].continued
    assert st.steps["process"].status == "succeeded"


def test_failure_without_continue_cancels_dependents_and_runs_failure_handler(tmp_path):
    status, st, _ = run(tmp_path, """
        handler_on:
          failure:
            run: echo bad > "$DAG_RUN_WORK_DIR/failure"
        steps:
          - id: a
            run: exit 7
          - id: b
            depends: a
            run: echo b
          - id: c
            run: echo c
        """)
    assert status == "failed"
    assert st.steps["a"].exit_code == 7
    assert st.steps["b"].status == "canceled"
    assert st.steps["c"].status == "succeeded"  # an independent branch still runs
    assert (tmp_path / "runs" / "r1" / "failure").exists()


def test_retry_policy_counts_and_exit_code_filter(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: flaky
            run: |
              n=$(cat "$DAG_RUN_WORK_DIR/n" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$DAG_RUN_WORK_DIR/n"
              [ $n -ge 3 ] && exit 0 || exit 42
            retry_policy:
              limit: 3
              interval_sec: 0
              exit_code: [42]
          - id: not_retried
            run: exit 9
            retry_policy:
              limit: 3
              exit_code: [42]
            continue_on: failed
        """)
    assert status == "partially_succeeded"
    assert len(st.steps["flaky"].attempts) == 3 and st.steps["flaky"].status == "succeeded"
    assert len(st.steps["not_retried"].attempts) == 1


def test_repeat_until_condition_reads_the_published_output(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: poll
            run: |
              n=$(cat "$DAG_RUN_WORK_DIR/n" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$DAG_RUN_WORK_DIR/n"
              [ $n -ge 3 ] && s=ready || s=waiting
              printf 'state=%s\\n' "$s" >> "$DAGU_OUTPUT_FILE"
            outputs:
              - name: state
            repeat_policy:
              repeat: until
              condition: "${steps.poll.outputs.state}"
              expected: ready
              interval_sec: 0
              limit: 10
        """)
    assert status == "succeeded"
    assert st.steps["poll"].executions == 3
    assert st.steps["poll"].outputs == {"state": "ready"}


def test_repeat_limit_and_while_without_condition(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: loop
            run: echo tick
            repeat_policy:
              repeat: while
              interval_sec: 0
              limit: 4
        """)
    assert status == "succeeded"
    assert st.steps["loop"].executions == 4


def test_repeat_condition_evaluation_error_fails_the_step(tmp_path):
    status, st, _ = run(tmp_path, """
        steps:
          - id: poll
            run: printf 'v=abc\\n' >> "$DAGU_OUTPUT_FILE"
            outputs: [{name: v}]
            repeat_policy:
              repeat: until
              condition: "${steps.poll.outputs.v}"
              expected: "num:>5"
              limit: 3
        """)
    assert status == "failed"
    assert "evaluation error" in st.steps["poll"].error


def test_step_timeout_gives_124(tmp_path):
    t0 = time.monotonic()
    status, st, _ = run(tmp_path, """
        steps:
          - id: slow
            run: sleep 30
            timeout_sec: 1
        """)
    assert status == "failed"
    assert st.steps["slow"].exit_code == 124
    assert time.monotonic() - t0 < 10


def test_retry_from_a_step_resets_it_and_downstream(tmp_path):
    status, st, dag = run(tmp_path, """
        steps:
          - id: a
            run: printf 'v=1\\n' >> "$DAGU_OUTPUT_FILE"
            outputs: [{name: v}]
          - id: b
            depends: a
            run: test -f "$DAG_RUN_WORK_DIR/ok" && echo "b sees ${steps.a.outputs.v}"
          - id: c
            depends: b
            run: echo c
        """)
    assert status == "failed"
    assert st.steps["b"].status == "failed" and st.steps["c"].status == "canceled"
    (tmp_path / "runs" / "r1" / "ok").write_text("")
    status = engine.retry(dag, tmp_path / "runs", "r1", "b", downstream=True)
    st = engine.load_state(tmp_path / "runs", "r1")
    assert status == "succeeded"
    assert len(st.steps["a"].attempts) == 1  # kept, not rerun
    assert st.steps["b"].status == "succeeded" and st.steps["c"].status == "succeeded"
    # the failed attempt stays in the history; the retry got its own number and log file
    assert [a.n for a in st.steps["b"].attempts] == [1, 2]
    assert Path(st.steps["b"].attempts[1].log).name == "b.2.log"
    assert Path(st.steps["b"].attempts[1].log).read_text() == "b sees 1\n"


def test_run_state_is_plain_json(tmp_path):
    status, st, _ = run(tmp_path, "steps:\n  - {id: a, run: echo hi}\n", run_id="r2")
    data = json.loads((tmp_path / "runs" / "r2" / "run.json").read_text())
    assert data["status"] == "succeeded" and data["steps"]["a"]["status"] == "succeeded"
    assert Path(data["steps"]["a"]["attempts"][0]["log"]).read_text() == "hi\n"
    assert (tmp_path / "runs" / "r2" / "run.log").exists()


def test_existing_run_id_is_refused(tmp_path):
    run(tmp_path, "steps:\n  - {id: a, run: echo hi}\n")
    with pytest.raises(FileExistsError):
        run(tmp_path, "steps:\n  - {id: a, run: echo hi}\n")
