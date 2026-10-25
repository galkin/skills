# Actions

Generic steps a workflow calls through `run:`. They know git and shell, nothing else.

## commit.sh

```sh
sh actions/commit.sh <slot worktree> <integration worktree> "<subject>"
```

1. Refuses, with `INTEGRATION INDEX DIRTY`, when a merge is due and the integration worktree
   has staged changes (a cherry-pick will not run over them; unstaged changes are fine), so
   the slot's checks are not spent on a merge that cannot happen. An unknown `MERGE` value is
   refused here too.
2. Runs `CHECKS_FULL` in the slot (log in `CI_LOG_DIR/<subject>.log`), then stages
   `COMMIT_PATHS` (`git add -A`) and commits with `<subject>` and `COMMIT_TRAILER`.
   Nothing staged is a failure, unless the slot's last commit already has this subject (then
   that commit is reused: a retry after a failed merge or failed post-merge checks) or
   `EMPTY_OK=1` (then there is no commit and the merge still runs).
3. When the slot is not the integration worktree and `MERGE` is not `off`: takes
   `<integration>/.task/merge.lock` (a directory; waits up to `LOCK_WAIT_SEC` while another
   slot holds it, then fails with `MERGE LOCK HELD`, the lock's path and age, and deletes
   nothing: a stale lock after a power loss is the coordinator's to `rmdir`), checks the
   integration index once more now that nobody else can be mid-merge, and lands the slot's
   work by `MERGE`:
   - `last`: cherry-picks the slot's last commit.
   - `all`: cherry-picks every slot commit since the merge base with the integration branch,
     in order. When those include a merge commit, it lands the branch as `branch` does
     instead (a cherry-pick cannot replay a merge commit).
   - `branch`: lands the slot's HEAD: a fast-forward when the integration branch is its
     ancestor, else `git merge --no-ff` with the message `Merge <slot branch>: <subject>`.
     For a long-lived branch that merges its base after each upstream change.

   A commit already on the branch (`git cherry`; for `branch`, a HEAD already merged) is
   skipped, so a retry after failed post-merge checks merges nothing twice. On a conflict runs
   `CONFLICT_HOOK` with the sha (for a merge, the slot's HEAD) as `$1` and `$COMMIT_SHA`, which
   must leave the conflicted files resolved; only those files are staged, and the cherry-pick
   or merge continues. **The landing is all or nothing**: if the hook is unset or fails, or git
   refuses (an unstaged edit in the way), the cherry-pick or merge is aborted and the
   integration branch is reset to where it was before the first pick (`git reset --keep`,
   which never overwrites a local edit), and the step fails with `MERGE FAILED: <what>; the
   integration branch is back at <sha subject>; git said: <its CONFLICT or error lines>`. Should
   even that reset be refused, the message says so in capitals and names the sha to go back to.
4. Runs `CHECKS_FAST` on the integration worktree, then `AFTER_COMMIT`; a failure of either
   fails the step with the commit already merged (not reset: the landing itself was complete,
   and the retry finds it merged).

| Variable         | Meaning                                                                    | Default                   |
| ---------------- | -------------------------------------------------------------------------- | ------------------------- |
| `CHECKS_FULL`    | Command run in the slot before the commit                                  | none                      |
| `CHECKS_FAST`    | Command run on the integration worktree after the cherry-pick              | none                      |
| `COMMIT_PATHS`   | Pathspecs to stage                                                         | `.`                       |
| `COMMIT_TRAILER` | Text appended to the message after a blank line                            | none                      |
| `MERGE`          | `last` (the slot's last commit), `all` (every commit since the merge base; the branch when they include a merge), `branch` (the slot's HEAD: fast-forward or `merge --no-ff`), `off` (commit only) | `last` |
| `EMPTY_OK`       | `1`: nothing staged makes no commit and is not a failure                   | unset (failure)           |
| `CONFLICT_HOOK`  | Resolver run on the integration worktree on a cherry-pick or merge conflict | none (conflict = failure) |
| `AFTER_COMMIT`   | Command run on the integration worktree after a successful merge           | none                      |
| `CI_LOG_DIR`     | Where check logs go                                                        | `<integration>/.task/ci`  |
| `LOCK_WAIT_SEC`  | How long to wait for another slot's merge lock before failing              | `900`                     |
| `CHECK_ONLY`     | `1`: run `CHECKS_FULL` in the slot and stop (`CHECKS PASSED` / `CHECKS FAILED`, log `CI_LOG_DIR/<subject>.check.log`); nothing staged, committed or merged | unset |

A pass that commits twice (writer, then improver) sets `MERGE=off` on the first commit step
and `MERGE=all` with `EMPTY_OK=1` on the second, so both commits reach the integration branch
together and an improver that changed nothing is not a failure.

A slot that is a long-lived branch (a story branch that merges its base after each upstream
change) sets `MERGE=branch`: its history lands as it is, with a fast-forward while the
integration branch has not moved and one merge commit when it has. `MERGE=all` on such a
slot does the same rather than replaying the branch commit by commit; `branch` says so in the
workflow file. A queue whose slots are reset to the integration branch before each item keeps
`all` or `last`, so its history stays linear while several slots land in turn.

## A coordinator's edit in a slot

The coordinator's edit takes the worker's path: it is made in the slot, never in the
integration worktree, and never committed or cherry-picked by hand. Before resuming, the
workflow's own commit step runs in check-only mode, with the run's params and environment:

```sh
bin/runner --runs-dir $W/.task/runs exec <wf.yaml> --run-id <item> --step <commit step> --env CHECK_ONLY=1
```

It runs `CHECKS_FULL` exactly as the commit will, so a failure (a formatter, a schema) shows
now rather than inside the commit. Once it passes, the run is resumed at its decision step and
the workflow's commit step commits the edit with the unit's subject and merges it. Since this
script runs `CHECKS_FULL` before it commits anything and the merge takes only slot commits, an
edit that reaches the integration branch this way has passed the same checks as a worker's.

Exit 1 on failed checks, an empty commit, a lock not released in time, or a failed merge, so
the step fails and the queue holds the item. The messages are `CHECKS FAILED`, `NOTHING TO
COMMIT`, `COMMIT FAILED`, `INTEGRATION INDEX DIRTY`, `MERGE LOCK HELD`, `MERGE FAILED`,
`POST-MERGE CHECKS FAILED` (the commit is already on the integration branch).
