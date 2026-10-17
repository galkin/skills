# 13: The lorekeep skill, shipped with the package

**What to build:** The package ships a skill folder: a hand-written `SKILL.md` (frontmatter `name`, `description`; a section per command with its flags, its text output and, for `get`, `add`, `search` and `status`, the `--json` shape) and a reference file on the Store's layout and frontmatter. A test parses the command sections and compares every flag with the parser's `--help`, so the two cannot drift. `lorekeep skill` prints `SKILL.md`; `lorekeep skill --install <repo>` copies the folder to `<repo>/.agents/skills/lorekeep/`, refuses when that folder exists unless `--force`, and ends by reminding that the repository's skill lock, if it keeps one, needs the new hash. A README for humans and one manual smoke script against the live network (not part of `pytest`) complete v1.

**Blocked by:** 09, 10, 11, 12

**Status:** ready-for-agent

- [ ] `lorekeep skill` prints `SKILL.md`; the flag-comparison test passes and fails when a flag is added to the parser alone
- [ ] `--install` creates `.agents/skills/lorekeep/` in a temporary repo and prints the lock reminder; a second install exits non-zero and changes nothing; `--force` replaces the folder
- [ ] the README covers install with `uv` and the `browser` extra, `LOREKEEP_STORE` and `LOREKEEP_TAG`, `lorekeep.toml` and the default host table, the first Store's values, how to restore one deleted Version, and the reverse `rsync` plus `index` that brings a whole Store back onto an empty disk
- [ ] the smoke script fetches one Twin, one static page and one browser page live and prints their converters, and runs `restore --generation` against the real bucket for one object
