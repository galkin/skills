"""actions/commit.sh against real temporary git repositories."""

import os
import subprocess
from pathlib import Path

import pytest

COMMIT = Path(__file__).resolve().parent.parent / "actions" / "commit.sh"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repos(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git(main, "init", "-q", "-b", "integration")
    git(main, "config", "user.email", "t@example.com")
    git(main, "config", "user.name", "t")
    (main / "src").mkdir()
    (main / "src" / "a.md").write_text("a\n")
    git(main, "add", "-A")
    git(main, "commit", "-q", "-m", "init")
    slot = tmp_path / "slot"
    git(main, "worktree", "add", "-q", str(slot), "-b", "slot")
    git(slot, "config", "user.email", "t@example.com")
    git(slot, "config", "user.name", "t")
    return main, slot


def run_commit(slot, main, subject, **env):
    e = {**os.environ, "CHECKS_FULL": "", "CHECKS_FAST": "", **env}
    return subprocess.run(["sh", str(COMMIT), str(slot), str(main), subject], env=e, capture_output=True, text=True)


def test_commit_in_slot_then_cherry_pick_onto_integration(repos):
    main, slot = repos
    (slot / "src" / "b.md").write_text("b\n")
    r = run_commit(slot, main, "Add unit 1.3a", COMMIT_PATHS="src", COMMIT_TRAILER="Co-Authored-By: x",
                   AFTER_COMMIT="echo after > .task/after")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(main, "log", "--format=%s", "-1") == "Add unit 1.3a"
    assert "Co-Authored-By: x" in git(main, "log", "--format=%B", "-1")
    assert (main / "src" / "b.md").exists()
    assert (main / ".task" / "after").read_text().strip() == "after"
    assert not (main / ".task" / "merge.lock").exists()


def test_failed_checks_block_the_commit(repos):
    main, slot = repos
    (slot / "src" / "b.md").write_text("b\n")
    r = run_commit(slot, main, "x", CHECKS_FULL="echo boom >&2; exit 1")
    assert r.returncode == 1 and "CHECKS FAILED" in r.stdout
    assert git(slot, "log", "--format=%s", "-1") == "init"
    assert "boom" in (main / ".task" / "ci" / "x.log").read_text()


def test_nothing_to_commit_fails(repos):
    main, slot = repos
    r = run_commit(slot, main, "x")
    assert r.returncode == 1 and "NOTHING TO COMMIT" in r.stdout


def test_conflict_hook_resolves_a_cherry_pick_conflict(repos):
    main, slot = repos
    (main / "src" / "a.md").write_text("a from main\n")
    git(main, "commit", "-qam", "main edit")
    (slot / "src" / "a.md").write_text("a from slot\n")
    r = run_commit(slot, main, "slot edit")
    assert r.returncode == 1 and "MERGE FAILED" in r.stdout
    assert git(main, "log", "--format=%s", "-1") == "main edit"  # aborted cleanly
    r = run_commit(slot, main, "slot edit", CONFLICT_HOOK="printf 'merged %s\\n' \"$1\" > src/a.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "reusing the slot commit" in r.stdout
    assert git(main, "log", "--format=%s", "-1") == "slot edit"
    assert (main / "src" / "a.md").read_text().startswith("merged ")


def test_retry_after_failed_post_merge_checks_does_not_merge_twice(repos):
    main, slot = repos
    (slot / "src" / "b.md").write_text("b\n")
    r = run_commit(slot, main, "Add b", CHECKS_FAST="exit 1")
    assert r.returncode == 1 and "POST-MERGE CHECKS FAILED" in r.stdout
    assert git(main, "log", "--format=%s", "-1") == "Add b"  # already merged
    r = run_commit(slot, main, "Add b", AFTER_COMMIT="echo after > .task/after")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already merged" in r.stdout
    assert git(main, "rev-list", "--count", "HEAD") == "2"
    assert (main / ".task" / "after").read_text().strip() == "after"


def test_merge_all_cherry_picks_every_slot_commit_and_empty_ok_skips_the_commit(repos):
    main, slot = repos
    (slot / "src" / "q.md").write_text("q\n")
    r = run_commit(slot, main, "Add the quizzes for 2-3", MERGE="off")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(main, "rev-list", "--count", "HEAD") == "1"  # nothing merged yet
    (slot / "src" / "q.md").write_text("q improved\n")
    r = run_commit(slot, main, "Improve the quizzes for 2-3", MERGE="all", AFTER_COMMIT="echo after > .task/after")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(main, "log", "--format=%s", "-3").splitlines() == ["Improve the quizzes for 2-3", "Add the quizzes for 2-3", "init"]
    assert (main / ".task" / "after").exists()
    # the improve step changed nothing: no commit, the merge still runs
    (slot / "src" / "z.md").write_text("z\n")
    assert run_commit(slot, main, "Add z", MERGE="off").returncode == 0
    r = run_commit(slot, main, "Improve z", MERGE="all", EMPTY_OK="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nothing to commit" in r.stdout
    assert git(main, "log", "--format=%s", "-1") == "Add z"


def test_unknown_merge_mode_is_refused(repos):
    main, slot = repos
    (slot / "src" / "m.md").write_text("m\n")
    r = run_commit(slot, main, "Add m", MERGE="sometimes")
    assert r.returncode == 1 and "MERGE must be" in r.stdout


def test_staged_changes_in_the_integration_worktree_are_refused_before_the_checks(repos):
    main, slot = repos
    (main / "unrelated.md").write_text("staged\n")
    git(main, "add", "unrelated.md")
    (slot / "src" / "b.md").write_text("b\n")
    r = run_commit(slot, main, "Add unit 1.3a", CHECKS_FULL="echo ran > .task-checks-ran")
    assert r.returncode == 1 and "INTEGRATION INDEX DIRTY" in r.stdout
    assert not (slot / ".task-checks-ran").exists()  # refused before the slot's checks
    assert git(slot, "log", "--format=%s", "-1") == "init"
    r = run_commit(slot, main, "Add unit 1.3a", MERGE="off")  # a slot-only commit does not care
    assert r.returncode == 0, r.stdout + r.stderr


def test_conflict_hook_stages_only_the_conflicted_files(repos):
    main, slot = repos
    (main / "src" / "a.md").write_text("a from main\n")
    git(main, "commit", "-qam", "main edit")
    (main / "untracked.md").write_text("not for the commit\n")
    (slot / "src" / "a.md").write_text("a from slot\n")
    r = run_commit(slot, main, "slot edit", CONFLICT_HOOK="printf 'merged %s\\n' \"$1\" > src/a.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(main, "log", "--format=%s", "-1") == "slot edit"
    assert "untracked.md" not in git(main, "show", "--stat", "--format=", "HEAD")
    assert (main / "untracked.md").exists()


def test_lock_wait_is_bounded_and_names_the_lock(repos):
    main, slot = repos
    (slot / "src" / "b.md").write_text("b\n")
    (main / ".task" / "merge.lock").mkdir(parents=True)
    r = run_commit(slot, main, "x", LOCK_WAIT_SEC="0")
    assert r.returncode == 1 and "MERGE LOCK HELD" in r.stdout and "merge.lock is" in r.stdout
    assert (main / ".task" / "merge.lock").exists()  # nothing deleted
    assert git(slot, "log", "--format=%s", "-1") == "x"  # the slot commit is kept for the retry
    (main / ".task" / "merge.lock").rmdir()
    assert run_commit(slot, main, "x", LOCK_WAIT_SEC="0").returncode == 0
    assert git(main, "log", "--format=%s", "-1") == "x"


def test_index_dirtied_during_the_checks_is_refused_once_the_lock_is_held(repos):
    main, slot = repos
    (slot / "src" / "b.md").write_text("b\n")
    (main / "src" / "c.md").write_text("c\n")
    r = run_commit(slot, main, "x", CHECKS_FULL=f"git -C {main} add src/c.md")
    assert r.returncode == 1 and "INTEGRATION INDEX DIRTY" in r.stdout
    assert not (main / ".task" / "merge.lock").exists()
    assert git(main, "log", "--format=%s", "-1") == "init"
