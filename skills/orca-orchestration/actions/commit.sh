#!/bin/sh
# commit.sh <slot worktree> <integration worktree> <subject> — a generic commit step (layer 2):
# run the full checks and make one commit in the slot, then cherry-pick it onto the integration
# worktree under a lock and re-run the fast checks there. Knows git and shell, nothing else.
#
# Configuration from the environment (a workflow sets it in `env:`):
#   CHECKS_FULL     command run with `sh -c` in the slot before the commit (may be empty)
#   CHECKS_FAST     command run in the integration worktree after the cherry-pick (may be empty)
#   COMMIT_PATHS    pathspecs for `git add -A` (default: everything)
#   COMMIT_TRAILER  text appended to the message after a blank line (optional)
#   CONFLICT_HOOK   command run in the integration worktree when the cherry-pick conflicts, with
#                   the commit sha as $1 and $COMMIT_SHA; it must leave the conflicted files
#                   resolved (only those are staged after it, so nothing else in the integration
#                   worktree gets into the commit); the cherry-pick continues if it exits 0
#   AFTER_COMMIT    command run in the integration worktree after a successful merge (optional)
#   CI_LOG_DIR      where check logs go (default: <integration>/.task/ci)
#   MERGE           last (default): cherry-pick the slot's last commit; all: every slot commit
#                   since the merge base with the integration branch (a pass that commits twice);
#                   off: commit in the slot only
#   EMPTY_OK        1: nothing staged is not a failure (an improve step that changed nothing);
#                   the merge still runs
#   LOCK_WAIT_SEC   how long to wait for another slot's merge lock (default 900); past it the
#                   step fails naming the lock and its age, and nothing is deleted: a stale
#                   lock (a power loss while it was held) is the coordinator's to remove
# Exit 1 on failed checks, commit, lock wait or merge, so the step fails and the item is held. Staged
# changes in the integration worktree are refused first, before the slot's checks run: a
# cherry-pick will not run over a dirty index, and finding that out after ten minutes of checks
# is the expensive way.
set -u
W=$1; MAIN=$2; SUBJECT=$3
LOGS=${CI_LOG_DIR:-$MAIN/.task/ci}; mkdir -p "$LOGS"
NAME=$(printf '%s' "$SUBJECT" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-60)
cd "$W" || exit 1
MERGE=${MERGE:-last}
case "$MERGE" in last|all|off) ;; *) echo "MERGE must be last, all or off, not '$MERGE'"; exit 1;; esac
[ "$(pwd -P)" = "$(cd "$MAIN" && pwd -P)" ] && MERGE=off   # the slot is the integration worktree: nothing to merge
if [ "$MERGE" != off ] && ! git -C "$MAIN" diff --cached --quiet; then
  echo "INTEGRATION INDEX DIRTY: $MAIN has staged changes and git cherry-pick refuses to run over them; unstage them (git reset) first"; exit 1
fi
if [ -n "${CHECKS_FULL:-}" ] && ! sh -c "$CHECKS_FULL" > "$LOGS/$NAME.log" 2>&1; then
  echo "CHECKS FAILED, see $LOGS/$NAME.log"; exit 1
fi
git add -A ${COMMIT_PATHS:-.} || exit 1
if git diff --cached --quiet; then
  # A retry after a failed merge or failed post-merge checks: the slot commit exists.
  C=$(git rev-parse HEAD)
  if [ "$(git log --format=%s -1)" = "$SUBJECT" ]; then
    echo "reusing the slot commit $(git log --oneline -1)"
  elif [ "${EMPTY_OK:-}" = 1 ]; then
    echo "nothing to commit for: $SUBJECT"
  else
    echo "NOTHING TO COMMIT"; exit 1
  fi
else
  git commit -q -m "$SUBJECT

${COMMIT_TRAILER:-}" || { echo "COMMIT FAILED"; exit 1; }
  C=$(git rev-parse HEAD); git log --oneline -1
fi
[ "$MERGE" = off ] && exit 0
if [ "$MERGE" = all ]; then
  BASE=$(git merge-base HEAD "$(git -C "$MAIN" rev-parse HEAD)") || exit 1
  COMMITS=$(git rev-list --reverse "$BASE..HEAD")
else
  COMMITS=$C
fi
cd "$MAIN" || exit 1
mkdir -p "$MAIN/.task"
LOCK=$MAIN/.task/merge.lock; WAITED=0
until mkdir "$LOCK" 2>/dev/null; do
  if [ "$WAITED" -ge "${LOCK_WAIT_SEC:-900}" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || stat -f %m "$LOCK" 2>/dev/null || date +%s) ))   # GNU first: BSD stat rejects -c, GNU accepts -f with another meaning
    echo "MERGE LOCK HELD: $LOCK is ${AGE}s old and was not released in ${WAITED}s; another slot's commit step holds it, or it is stale (a power loss while held): check, rmdir it, retry"; exit 1
  fi
  sleep 5; WAITED=$((WAITED + 5))
done
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
if ! git diff --cached --quiet; then   # again, now that nobody else can be mid-merge here
  echo "INTEGRATION INDEX DIRTY: $MAIN has staged changes and git cherry-pick refuses to run over them; unstage them (git reset) first"; exit 1
fi
for C in $COMMITS; do
  if git merge-base --is-ancestor "$C" HEAD || git cherry HEAD "$C" "$C^" | grep -q '^-'; then
    # A retry after failed post-merge checks: the commit is already on the integration branch.
    echo "already merged: $(git log --format=%s -1 "$C")"
  elif ! git cherry-pick "$C" > /dev/null 2>&1; then
    if [ -n "${CONFLICT_HOOK:-}" ] && COMMIT_SHA="$C" sh -c "$CONFLICT_HOOK" conflict "$C" \
       && git diff --name-only --diff-filter=U -z | xargs -0 git add -- && GIT_EDITOR=true git cherry-pick --continue > /dev/null 2>&1; then
      :
    else
      git cherry-pick --abort 2>/dev/null; echo "MERGE FAILED: $(git log --format=%s -1 "$C")"; exit 1
    fi
  fi
done
if [ -n "${CHECKS_FAST:-}" ] && ! sh -c "$CHECKS_FAST" > "$LOGS/$NAME.merge.log" 2>&1; then
  echo "POST-MERGE CHECKS FAILED, see $LOGS/$NAME.merge.log (the commit is already on the integration branch)"; exit 1
fi
git log --oneline -1
if [ -n "${AFTER_COMMIT:-}" ] && ! sh -c "$AFTER_COMMIT"; then
  echo "AFTER_COMMIT FAILED (the commit is already on the integration branch)"; exit 1
fi
exit 0
