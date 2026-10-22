# Report: withdraw a Source stored by mistake

Branch `lorekeep-withdraw` (from `main` at `3571e52`). Ticket:
[`01-withdraw-a-source.md`](01-withdraw-a-source.md). Decision record:
[ADR 0010](../../adr/0010-a-source-stored-by-mistake-is-withdrawn-never-removed.md).
No version bump, tag, skill build, merge or push.

## What was built

- **`lorekeep withdraw URL --reason TEXT [--undo] [--store DIR]`**
  (`src/lorekeep/commands/withdraw.py`). It is the Curator's command, like `tag add`. `URL` resolves
  through `store.latest`, the same way `get` resolves an address: normalised, Twin-reduced, then
  through `aliases.csv`. The row it appends names the Source, so the withdrawal covers every Version.
  A URL with no Source exits `2` and writes nothing. An empty `--reason` also exits `2`.
- **`withdrawals.csv`** (`url,recorded_at,action,reason`) goes through the one commit point under
  the lock, as `WithdrawalRow` in `store.FILE_OF`. That one entry puts it among the watched and
  growing files, so the Index fingerprints it, `backup` copies it and the backup `EXCLUDE` covers it.
  `store.withdrawn(store)` gives the Sources withdrawn now: those whose last row is `withdraw`.
- **The Index** (schema `8` → `9`) gains:
  - a `withdrawals` table;
  - a `withdrawn` view, which gives the same answer as `store.withdrawn`.

  A withdrawn Source keeps its `versions` rows, so its address still resolves, but it gets no
  Sections and no Reading in a rebuild. `latest_in_scope` leaves it out, so `recheck` never asks
  about it. A withdrawal commit does not notify the Index; the Index goes stale and the next reader
  rebuilds it. Without the rebuild, an undo would bring back Sections read from Readings that were
  never built.
- **Every command that deals with a withdrawn Source:**

  | Command | What happens to a withdrawn Source |
  | --- | --- |
  | `search` | Never finds it, because it has no Sections in the Index. |
  | `status` | Prints a `Withdrawn: N Sources (M Versions)` line and leaves the Source out of the other counts (Versions/Sources, Tags, fetched_at, Readings, unknown hosts). Rechecks still count every row. `--json` gains `withdrawn_sources` and `withdrawn_versions`. |
  | `get` | Exits `1` with `<url> was withdrawn by the owner at <time>: <reason> (lorekeep withdraw --undo takes it back)`. It refuses before any request when the address is known. It also refuses after a fetch when a new address redirects to the Source, so nothing is stored or tagged. |
  | `add` | Refuses a withdrawn `owner:` Source in the same way. |
  | `read` and Index rebuild | Build no Reading for it. |
  | `recheck` | Leaves it out of every scope. |
  | `recheck --citations` | Prints `lorekeep: error: <work_id> cites <url>, withdrawn at <time>: <reason>` and exits `1`. |
  | `backup` / `datapackage.json` | `backup` copies `withdrawals.csv`. `datapackage.json` gets a `withdrawals` resource, with `recorded_at` typed as datetime and `action` as an enum; it validates with frictionless. |
- **Docs:**
  - ADR 0010 is new.
  - ADR 0004 now lists `withdrawals.csv` among the growing files.
  - `GLOSSARY.md` gains **Withdrawal**, and Curator now mentions it.
  - `AGENTS.md` invariants, README's command list and backup paragraph.
  - Skill: `references/curating.md` gets a new `lorekeep withdraw` section, plus notes in recheck, backup and read. `references/store.md` gets the file row, a Withdrawals section, the citations failure and the `status --json` fields. `references/collecting.md` gets the `status` example and text.
  - `SKILL.md`: the Curator row lists `withdraw`. The rule "Write to the Store only through `get` and `add`" is unchanged and now continues: "A page stored by mistake is reported to the owner, with its `url` and why; the owner withdraws it." SKILL.md is 41 lines; the test limit is 250.
- **Tests:** `tests/test_withdraw.py` has 16 tests, all on fixtures with no network. They cover:
  - finding the Source by its alias, by its address normalised as in a request, and by its Twin's address;
  - exit `2`, a missing `--reason`, a second withdraw, and undo;
  - search before, after and after undo, and the status line and JSON;
  - `get` refusal without a request or a Tag, refusal of a redirect to a withdrawn Source, and `add` refusal;
  - `read` and the Index building no Reading, `recheck` scope and `--citations` failure;
  - backup `cp` and the data package.

  `tests/test_status.py`'s JSON shape gained the two new keys.

## Undo, and a second `withdraw`

- `withdraw --undo URL --reason TEXT` appends a row with `action` `undo`. The last row for a `url`
  decides. `--reason` is required both ways, so every change in the file says why.
- A row is appended only when it changes the state. A second `withdraw` of a withdrawn Source prints
  `… was already withdrawn at <time>: <reason>; nothing written`. An `--undo` of a Source that is not
  withdrawn prints `… is not withdrawn; nothing written`. Both exit `0`, as `tag add` does for a Tag
  already there.
- After an undo, the Source can be found again once the next reader rebuilds the Index and its
  Readings. `search`, `status` and `index` do that rebuild on their own.

## Gate (from `lorekeep/`)

```text
$ uv run pytest -q            → 422 passed in 16.61s, exit 0
$ uv run ruff check           → All checks passed!, exit 0
$ uv run ruff format --check  → 198 files already formatted, exit 0
$ uv run pyright              → 0 errors, 0 warnings, 0 informations, exit 0
```

## Live check

`status` was run on an APFS clone (`cp -c`) of `~/orca/sources/agentic-system.design`, not on the
Store itself (reason below):

- It exited `0` after a rebuild of 13.9 s: 3237 Versions of 3236 Sources, then `Withdrawn: 0 Sources (0 Versions)`.
- In the clone only, I withdrew the brief's four Sources: `https://ans.dev`, `https://www.okf.dev`,
  `https://www.visa.sk` and `https://agoraprotocol.org`. `status` then showed:
  - `3233 Versions of 3232 Sources`;
  - `Withdrawn: 4 Sources (4 Versions)`;
  - `specifications 907 → 903`;
  - `ans.dev`, `www.okf.dev` and `www.visa.sk` gone from Unknown hosts.
- `get https://www.visa.sk` exited `1` naming the withdrawal. A second `withdraw` wrote nothing.
- The clone was then deleted.

The real Store still has no `withdrawals.csv`, and its Index still reads schema `8`.

## What in the brief turned out wrong

- **"Live check, read-only: `lorekeep status` against the real Store."** On this branch that is not
  read-only. The Index schema went from 8 to 9, so the first reader on this branch rebuilds the real
  Store's `sources.db`, and `status` reads through `index.ensured`. After that, the released 0.2.7,
  which Runs use and which expects schema 8, would rebuild it back on its next read, and the two
  would keep rebuilding over each other until 0.2.8 is installed. Each rebuild takes about 14 s;
  nothing is lost, because the Index is derived. So I ran the check on a clone. After the release,
  `status` against the real Store is a one-time rebuild and is safe to run.
- **"`withdrawals.csv` (`url,withdrawn_at,reason`)".** Three columns cannot record an undo as an
  appended row. The file is `url,recorded_at,action,reason`, with `action` either `withdraw` or
  `undo`. ADR 0010 › Considered Options gives the reasons.
- **"`get` of a withdrawn URL refuses … unless the owner undoes it first"** holds as written. I also
  made `get` refuse a *new* address that redirects to a withdrawn Source; without that, the redirect
  would add an alias and a Tag to it. And `add` refuses a withdrawn `owner:` Source. The brief did
  not ask for either.
- **Unchanged and worth knowing:** `tag add` (with a URL or `--prefix`) can still tag a withdrawn
  Source. That is harmless, since a withdrawn Source counts under no Tag. `rules sample` and
  `rules check` still measure withdrawn Versions; the brief did not mention them.

## Commits

- `0f02c28` lorekeep: withdraw a Source stored by mistake
- plus the commit that adds this report

DONE withdraw
