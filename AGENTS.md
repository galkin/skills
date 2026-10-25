# AGENTS.md

`CLAUDE.md` is a symlink to this file. The skills live in `skills/<name>/`; `README.md` says how they are installed and built.

## After you change a skill

A change to a skill is done only when every local project that installs it runs the new version:

1. Commit and push the change to `galkin/skills` (projects install from GitHub, not from this checkout).
2. For each project in `local-projects.txt` (git-ignored, one path per line; ask the user for it when it is missing), in that project's main checkout on its `main` branch:
   - skip the project when its `skills-lock.json` does not list the skill;
   - run `npx skills update <skill> -p -y`;
   - check that `skills-lock.json` and the skill's files changed as expected and that the project's own checks pass;
   - commit only `skills-lock.json` and the skill's folder, with a message naming the skill and its new version (`Update <skill> to <version> from galkin/skills`), leaving any unrelated work in the checkout untouched;
   - push only when the user asked for it.
3. Report each project: updated, skipped (and why), or failed (and why).
