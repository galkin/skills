# 13: The lorekeep skill, shipped with the package

**What to build:** The package ships a skill folder (`SKILL.md` plus a hand-written reference on the Store's layout and frontmatter) that teaches an agent every command, flag and output format, with the command reference generated from the same declarations the CLI parser uses so the two cannot drift. `lorekeep skill` prints `SKILL.md`; `lorekeep skill --install <repo>` copies the folder to `<repo>/.agents/skills/lorekeep/`, refuses when that folder exists unless `--force`, and ends by reminding that the repository's skill lock, if it keeps one, needs the new hash. A README for humans and one manual smoke script against the live network (not part of `pytest`) complete v1.

**Blocked by:** 09, 10, 11, 12

**Status:** ready-for-agent

- [ ] `lorekeep skill` prints a `SKILL.md` with frontmatter (`name`, `description`) and a section per command whose flags match `--help` (a test compares them)
- [ ] `--install` creates `.agents/skills/lorekeep/` in a temporary repo and prints the lock reminder; a second install exits non-zero and changes nothing; `--force` replaces the folder
- [ ] the README covers install with `uv` and the extras, `LOREKEEP_STORE` and `LOREKEEP_TAG`, `lorekeep.toml` and the default host table, the first Store's values, how to restore one deleted Version, and the reverse `rsync` plus `index` that brings a whole Store back onto an empty disk
- [ ] the smoke script fetches one Twin, one static page and one browser page live and prints their converters
