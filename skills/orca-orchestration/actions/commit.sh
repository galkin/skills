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
#   CONFLICT_HOOK   command run in the integration worktree when the cherry-pick or merge
#                   conflicts, with the commit sha (for a merge: the slot's HEAD) as $1 and
#                   $COMMIT_SHA; it must leave the conflicted files resolved (only those are
#                   staged after it, so nothing else in the integration worktree gets into the
#                   commit); the cherry-pick or merge continues if it exits 0
#   AFTER_COMMIT    command run in the integration worktree after a successful merge (optional)
#   CI_LOG_DIR      where check logs go (default: <integration>/.task/ci)
#   MERGE           last (default): cherry-pick the slot's last commit; all: every slot commit
#                   since the merge base with the integration branch (a pass that commits twice),
#                   or, when those include a merge commit, the slot's branch as `branch` lands
#                   it; branch: land the slot's HEAD, a fast-forward when the integration
#                   branch is its ancestor, else `git merge --no-ff` (a long-lived branch that
#                   merges its base); off: commit in the slot only
#   EMPTY_OK        1: nothing staged is not a failure (an improve step that changed nothing);
#                   the merge still runs
#   LOCK_WAIT_SEC   how long to wait for another slot's merge lock (default 900); past it the
#                   step fails naming the lock and its age, and nothing is deleted: a stale
#                   lock (a power loss while it was held) is the coordinator's to remove
#   CHECK_ONLY      1: run CHECKS_FULL in the slot and stop there (CHECKS PASSED or CHECKS
#                   FAILED): nothing is staged, committed or merged. A coordinator who edited a
#                   slot by hand runs the workflow's own commit step this way (`runner exec …
#                   --env CHECK_ONLY=1`), then resumes the run so this script commits the edit
# The landing is all or nothing: on a failed cherry-pick or merge the integration branch is reset
# (`git reset --keep`, which never overwrites a local edit) to where it was before the first pick.
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
case "$MERGE" in last|all|branch|off) ;; *) echo "MERGE must be last, all, branch or off, not '$MERGE'"; exit 1;; esac
[ "$(pwd -P)" = "$(cd "$MAIN" && pwd -P)" ] && MERGE=off   # the slot is the integration worktree: nothing to merge
if [ "${CHECK_ONLY:-}" = 1 ]; then
  if [ -n "${CHECKS_FULL:-}" ] && ! sh -c "$CHECKS_FULL" > "$LOGS/$NAME.check.log" 2>&1; then
    echo "CHECKS FAILED, see $LOGS/$NAME.check.log"; exit 1
  fi
  echo "CHECKS PASSED (CHECK_ONLY: nothing committed)"; exit 0
fi
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
TIP=$(git rev-parse HEAD)
if [ "$MERGE" = all ]; then
  BASE=$(git merge-base HEAD "$(git -C "$MAIN" rev-parse HEAD)") || exit 1
  if [ -n "$(git rev-list --merges -n 1 "$BASE..HEAD")" ]; then
    # A cherry-pick cannot replay a merge commit (it stops there, half done): land the branch.
    echo "the slot's commits since the merge base include a merge commit: landing the branch"
    MERGE=branch
  fi
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
ORIG=$(git rev-parse HEAD)
# fail_merge <what>: undo every pick or merge of this step, so the integration branch is never left
# half landed, and fail naming what failed and what git said.
fail_merge() {
  git cherry-pick --abort > /dev/null 2>&1; git merge --abort > /dev/null 2>&1
  if [ "$(git rev-parse HEAD)" = "$ORIG" ] || git reset -q --keep "$ORIG" 2>/dev/null; then
    WHERE="the integration branch is back at $(git log --oneline -1 "$ORIG")"
  else
    WHERE="THE INTEGRATION BRANCH COULD NOT BE RESET: it is at $(git log --oneline -1), it was at $ORIG (git reset --keep $ORIG)"
  fi
  echo "MERGE FAILED: $1; $WHERE${GIT_SAID:+; git said: $GIT_SAID}"; exit 1
}
# resolve <sha> <continue command>: CONFLICT_HOOK, stage only the conflicted files, continue.
resolve() {
  [ -n "${CONFLICT_HOOK:-}" ] && COMMIT_SHA="$1" sh -c "$CONFLICT_HOOK" conflict "$1" \
    && git diff --name-only --diff-filter=U -z | xargs -0 git add -- && GIT_EDITOR=true $2 > /dev/null 2>&1
}
# said <git output>: its CONFLICT, error and fatal lines (else its first line), on one line.
said() {
  { printf '%s\n' "$1" | grep -E '^(CONFLICT|error|fatal)' || printf '%s\n' "$1" | grep -v '^hint:' | grep . | head -n 1; } \
    | head -n 3 | tr '\n' ' ' | sed 's/ *$//'
}
if [ "$MERGE" = branch ]; then
  BRANCH=$(git -C "$W" symbolic-ref -q --short HEAD || echo "$TIP")
  if git merge-base --is-ancestor "$TIP" HEAD; then
    echo "already merged: $BRANCH at $(git log --oneline -1 "$TIP")"
  elif git merge-base --is-ancestor HEAD "$TIP"; then
    OUT=$(git merge -q --ff-only "$TIP" 2>&1) || { GIT_SAID=$(said "$OUT"); fail_merge "fast-forward to $BRANCH"; }
    echo "fast-forwarded to $BRANCH"
  elif ! OUT=$(git merge -q --no-ff --no-edit -m "Merge $BRANCH: $SUBJECT" "$TIP" 2>&1); then
    GIT_SAID=$(said "$OUT")
    if [ -z "$(git diff --name-only --diff-filter=U)" ] || ! resolve "$TIP" "git merge --continue"; then
      fail_merge "merge of $BRANCH"
    fi
  fi
else
  for C in $COMMITS; do
    if git merge-base --is-ancestor "$C" HEAD || git cherry HEAD "$C" "$C^" | grep -q '^-'; then
      # A retry after failed post-merge checks: the commit is already on the integration branch.
      echo "already merged: $(git log --format=%s -1 "$C")"
    elif ! OUT=$(git cherry-pick "$C" 2>&1); then
      GIT_SAID=$(said "$OUT")
      resolve "$C" "git cherry-pick --continue" || fail_merge "$(git log --format=%s -1 "$C")"
    fi
  done
fi
if [ -n "${CHECKS_FAST:-}" ] && ! sh -c "$CHECKS_FAST" > "$LOGS/$NAME.merge.log" 2>&1; then
  echo "POST-MERGE CHECKS FAILED, see $LOGS/$NAME.merge.log (the commit is already on the integration branch)"; exit 1
fi
git log --oneline -1
if [ -n "${AFTER_COMMIT:-}" ] && ! sh -c "$AFTER_COMMIT"; then
  echo "AFTER_COMMIT FAILED (the commit is already on the integration branch)"; exit 1
fi
exit 0
