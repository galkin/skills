# 13: The lorekeep skill, shipped with the package

**What to build:** The package ships a skill folder (`SKILL.md` plus reference files) that teaches an agent every command, flag, output format and the Store's layout, generated from the same declarations the CLI parser uses so the two cannot drift. `lorekeep skill` prints `SKILL.md`; `lorekeep skill --install <repo>` copies the folder to `<repo>/.agents/skills/lorekeep/` and refuses to overwrite a modified copy. A README for humans and one manual smoke script against the live network (not part of `pytest`) complete v1.

**Blocked by:** 09, 10, 11, 12

**Status:** ready-for-agent

- [ ] `lorekeep skill` prints a `SKILL.md` with frontmatter (`name`, `description`) and a section per command whose flags match `--help` (a test compares them)
- [ ] `--install` creates `.agents/skills/lorekeep/` in a temporary repo; a second install with a locally edited file exits non-zero and changes nothing
- [ ] the README covers install with `uv`, the Store, `lorekeep.toml`, the first Store's values, and how to restore a deleted Version
- [ ] the smoke script fetches one Twin, one static page and one browser page live and prints their converters
