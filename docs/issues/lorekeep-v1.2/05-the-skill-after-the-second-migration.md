# 05: the skill after the second migration

**What to build:** The sentences the three migration workers missed, in the skill that ships (`src/lorekeep/skill/`), with no change to the tool. Read `../lorekeep-v1.1/reports/migration-v11-{aa,ab,ac}.md` › Friction first. Decisions: `spec.md` › The skill.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `SKILL.md` › `search` says: a plain query needs every word to occur in one Section, so use 2–4 content words in the page's own wording, never a question; shows one failing question and its working keywords
- [ ] `SKILL.md` › How a Run works shows the exit-1 log line as one JSON example (`{"url": …, "error": …}`) beside the `get --json` line, and says to log the address as asked when it has a fragment
- [ ] `SKILL.md` says a `third-party` verdict prints no warning: check `authority` in every JSON line, and name the catch-all (`github.com/`) as the usual cause
- [ ] `SKILL.md` says a Twin has no Original file (`original.stored: false`) and that the Original of a converted page is `<stem>.orig.<ext>` beside the Version, so a partial Version can be checked against it
- [ ] the `get --json` example is captured from a fixture whose host really has no rule (no synthesised redirect), and prints what the tool prints today
- [ ] `owner.md` says what "issuer" means for laws and standards as `spec.md` decides it (journal `primary`, institutional reproduction `official`, cite the journal), and documents `browser` and `cut` on a rule in one place
- [ ] `SKILL.md` stays under 250 lines; the flag test, the Run/owner split test and the JSON-fields test pass; `pytest`, `ruff`, `pyright` green
