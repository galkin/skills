# 05: the skill after the second migration

**What to build:** The sentences the three migration workers missed, in the skill that ships (`src/lorekeep/skill/`), with no change to the tool. Read `../lorekeep-v1.1/reports/migration-v11-{aa,ab,ac}.md` › Friction first. Decisions: `spec.md` › The skill.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `SKILL.md` › `search` says: a plain query needs every word to occur in one Section, so use 2–4 content words in the page's own wording, never a question; shows one failing question and its working keywords
- [x] `SKILL.md` › How a Run works shows the exit-1 log line as one JSON example (`{"url": …, "error": …}`) beside the `get --json` line, and says to log the address as asked when it has a fragment
- [x] `SKILL.md` says a `third-party` verdict prints no warning: check `authority` in every JSON line, and name the catch-all (`github.com/`) as the usual cause
- [x] `SKILL.md` says a Twin has no Original file (`original.stored: false`) and that the Original of a converted page is `<stem>.orig.<ext>` beside the Version, so a partial Version can be checked against it
- [x] the `get --json` example is captured from a fixture whose host really has no rule (no synthesised redirect), and prints what the tool prints today
- [x] `owner.md` says what "issuer" means for laws and standards as `spec.md` decides it (journal `primary`, institutional reproduction `official`, cite the journal), and documents `browser` and `cut` on a rule in one place
- [x] `SKILL.md` stays under 250 lines; the flag test, the Run/owner split test and the JSON-fields test pass; `pytest`, `ruff`, `pyright` green

## Comments

**2026-10-17** — done on `galkin/lorekeep-v12-05`; no change to the tool.

- **`SKILL.md`** (245 lines). `search`: every word of a plain query in one Section, 2–4 content
  words in the page's wording, never a question, with a question that prints `no matches` and its
  keywords that find the Section; `no matches` exits `0`. How a Run works: the log example (an
  `asked` line for an address with a fragment, the `get --json` line, the exit-1 object
  `{"url": …, "error": …}`), and "judge each `get` by its own exit code". What to cite: no warning
  for a `third-party` verdict, check `authority` in every JSON line, `github.com/` the usual cause,
  `status --rules`; the issuer rule as the spec decides it. The intro: a converted page's Original
  is `<stem>.orig.<ext>`, a Twin has none (`original.stored: false`). The missing-code row: compare
  with the Original, distrust nearby headings. New after the table: warnings print only on the
  `get` that stored the Version; an exit `0` under 2 KB or from a browser-built host is opened and
  compared with its Original. The `thin content` thresholds; heading-poor long pages search as one
  Section.
- **`owner.md`**: `browser` and `cut` in the rule keys, in one place (what each does, when the
  browser runs without `browser`, a browser Version never rechecked, the Original before the cut);
  the issuer rule for laws and standards. **`store.md`**: `primary` says "on its official journal".
- **Examples captured, not typed.** The `get --json` example is `get --json
  https://helm.sh/docs/helm/helm_rollback/#synopsis` against `helm-rollback.html` (helm.sh is in
  no rule; no redirect), run in-process with the fakes of `tests/support.py`, Tag `nvidia`; the
  search examples against `guardrails-jailbreak-protection.twin` and `guardrails-self-check.html`.
  Two new tests rerun them: `test_the_get_example_is_what_get_prints_for_a_host_no_rule_knows`
  (stderr equal, JSON equal but for `fetched_at`/`verified_at`) and
  `test_the_search_examples_are_what_search_prints` (every `$ lorekeep search` example of
  `SKILL.md`, the v1.1 ones included). The JSON-fields test uses the same address.
- **Friction answered** beyond the criteria (reports aa, ab, ac): warnings only on the storing
  `get` (ab 3); thin-check thresholds (aa 7); a menu-only or list-losing Version at exit `0`
  (aa 2, ac 3); heading-poor pages (ab 5); `no matches` exits `0` (ab 1); which rule decided
  `authority` (aa 6); GitHub organisations when unsure (ac 5); the loop's exit code (ac). Not a
  skill matter: the Fern banner (ab 9, ticket 04), a wrong publisher `canonical` (ab 6; the skill
  already says it changes nothing).

**Where the ticket or the spec was wrong, or is pending.**

- **The issuer rule is pending the owner** (spec › Further Notes): written as the spec decides it
  (official journal `primary`, institutional reproduction `official`, cite the journal), in
  `SKILL.md`, `owner.md` and `store.md`. Overruling it changes those three places.
- **`wait_for`** (spec › The skill, for `owner.md`) does not exist before ticket 03; the ticket's
  criterion names `browser` and `cut`, which is what `owner.md` documents. Ticket 03 adds
  `wait_for` there.
- **`asked`, `warnings`, `relaxed` in `store.md`** wait for tickets 01–02; nothing of them is
  documented as the tool's. The log's `asked` line is the Run's own and uses the name ticket 02
  gives the field, so the log keeps its shape when the field lands.
- **"Beside the `get --json` line"**: the log example elides the `get --json` line (`…`) rather
  than repeat the 500-character example printed under `lorekeep get`.
- **The search examples pin today's behaviour**: after ticket 01 the question no longer prints
  `no matches`, and `test_the_search_examples_are_what_search_prints` fails until the example
  shows the relaxed answer and its note line, as the spec asks of ticket 01.
