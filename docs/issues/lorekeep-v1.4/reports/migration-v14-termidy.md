# termidy batch: report

Batch: `batch-termidy`, 177 URLs from claude.termidy.com. lorekeep 0.1.1, Tag `anthropic`. Log:
`log.jsonl` (177 lines, one per URL, no retry lines); per-URL exit codes in `codes.txt`
(`<n> <exit> <url>`); stderr in `err/<n>.txt`; the loop in `run.sh`.

## Numbers

- **URLs:** 177, every one attempted once.
- **Exit 0:** 173, all `outcome: stored`. None were `fresh`, `unchanged`, `changed`, `gone`, `error` or `skipped`.
- **Exit 1:** 4, all of one kind: `thin content … the browser rendered a shell`. These are the four Moodle `/course/` URLs (lines 170–173).
- **Exit 2:** 0.
- **Retries:** 0. None of the four error lines names `ReadTimeout`, `ConnectError` or a 5xx, so the skill's rule says not to retry.
- **Converters:** `trafilatura 2.3.1` 173. There was no `md-twin`, `raw-twin`, `markitdown` or `verbatim`.
- **Readings:** none. No JSON line has `version`, so `path` is the Version itself every time.
- **Authorities:** `third-party` 173.
- **Publishers:** `termidy` 172, and `claude.termidy.com` 1 (the root page; see the tool section of Friction).
- **Wall time:** 345 s, from 2026-10-17T21:03:10Z to 21:08:55Z, which is about 2 s per URL. Five other workers were writing to the Store at the same time.
- **Versions under 2 KB:** 0. The smallest is 2,839 bytes (`/top/aboutus.php`).
- **Counts for worker_done:** stored 173, fresh or unchanged 0, errors 4.

## To report to the owner

**Unknown host.** The tool says the host is unknown, but it is not. A rule `claude.termidy.com/  termidy  third-party` exists. The root URL still gets the unknown-host warning, and `lorekeep status` now lists `claude.termidy.com` under "Unknown hosts":
- `https://claude.termidy.com/`:
  `lorekeep: warning: claude.termidy.com is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule`
  `lorekeep: note: https://claude.termidy.com is third-party under no rule`
  The Version has `publisher: "claude.termidy.com"`, while the other 172 pages have `termidy`.

**Error lines (exit 1, nothing stored). All four are `thin content`, and the browser already ran, three attempts each:**
- `https://claude.termidy.com/course/index.php`: `lorekeep: error: nothing stored for https://claude.termidy.com/course/index.php: the host rule names no Twin; thin content: https://claude.termidy.com/course/index.php converted to 317 characters of a page of 21969; the browser rendered a shell (317 characters after 3 attempts)`
- `https://claude.termidy.com/course/view.php?idnumber=claude_ccar_p`: `… converted to 434 characters of a page of 23942; the browser rendered a shell (434 characters after 3 attempts)`
- `https://claude.termidy.com/course/view.php?idnumber=claude_cca_f`: `… converted to 434 characters of a page of 24585; the browser rendered a shell (434 characters after 3 attempts)`
- `https://claude.termidy.com/course/view.php?idnumber=claude_ccdv_f`: `… converted to 434 characters of a page of 23933; the browser rendered a shell (434 characters after 3 attempts)`

These four are the Moodle question-bank pages. The site says the full banks need an account, so these are probably sign-in or enrolment pages. That is a guess: nothing was stored, so I could not look.

**Third-party pages the guide treats as primary:** none. The whole site is a third-party study aid, and the host rule says so correctly.

**Missing code or tables warnings:** two pages. In both, the content counted as missing is actually present, but in a damaged form (details under Spot checks):
- `https://claude.termidy.com/ccar-f/cheat-sheet`: `0 code blocks / 1 tables of the page are missing from the Markdown`. The 7-row "Exam facts" table is in the Version, but with no separator row, so it is not a GFM table.
- `https://claude.termidy.com/learn/ccdv-f/prompt-context-engineering/prompt-engineering`: `1 code blocks / 0 tables of the page are missing from the Markdown`. Both `<pre>` blocks are fenced in the Version, but they lost their language and their blank lines, and one comment was entity-decoded.

**Losses with no warning.** These are larger than anything the warnings flag:
- **HTML diagrams are dropped.** The Originals hold 415 `class="diagram …"` blocks on 123 pages. The first four words of only 6 of them appear in the Versions. Example: the three diagrams of the prompt-engineering lesson ("Three failures, three missing pieces", "Refining a prompt against test cases", "Four quick fixes for bad output, one method") are gone.
- **The per-lesson quizzes are not in any Version.** 154 Originals hold them as `const DATA = [{"id":"check-1", … "question": …, "options": [… "explanation": …]}]` inside a `<script>`. The Versions keep only the heading "Check your understanding" and its intro sentence. The Originals (`*.orig.html`) do keep the data. If the archive is meant to keep the practice questions with their explanations, the Markdown does not hold them.
- **Code fences lose their language on every page.** 119 Versions have fences and 0 have a language tag, even where the Original says `<code class="python">`.

**`thin content`:** the four exit-1 URLs above. No exit-0 page warned `the Markdown holds N% of the page's main text`.

**Reading-rule warnings:** none. There are no Readings for this host.

## Spot checks

Every Version is `trafilatura 2.3.1` and none has a Reading, so I chose five pages by size and by warning rather than by converter.

1. **`https://claude.termidy.com/top/aboutus.php`**, the smallest Version (2,839 B): **the page's content**. All its H3 sections, lists, emphasis and the mailto link are there. The visible H1 "About" is missing from the body; it survives only as the frontmatter `title`. The menu and footer chrome are gone, which is good.
2. **`https://claude.termidy.com/articles`**, an index page (2,942 B): **content, in a damaged form**. The breadcrumb, H1 and intro are there. Each list item runs the link title, description and date together with no separator: `[CCAO-F versus CCAR-F: the Associate and Architect exams comparedThe two Claude exams people most often confuse, …28 September 2026 · 4 min](…)`.
3. **`https://claude.termidy.com/`**, the root (7.3 KB): **the text is all there, but the structure is not**. The Original has 11 `<h1>`/`<h2>`. The Version opens with `- # Pass your Claude certification. Free Claude …` (an H1 inside a list item, run into the lede and the buttons), and everything after "Study free, then practise" is one line of about 4 KB with `## Which Claude certifications does this cover?`-style headings inline. Search therefore sees almost no Sections. `get` printed no "no headings" warning.
4. **`https://claude.termidy.com/ccar-f/cheat-sheet`**, warned about a table (9.9 KB): **the page's content**: H1, every domain H2, the scenario list with inline code. The "Exam facts" table is present as `| Questions | 60, multiple choice … |` rows, with no header row and no `|---|` separator, so it renders as plain lines. The warning's word "missing" is too strong: the data is there, but the table structure is not.
5. **`https://claude.termidy.com/learn/ccdv-f/prompt-context-engineering/prompt-engineering`**, warned about code (21 KB, Original 66 KB): **the page's content**. All the 6.2.x headings, the prose, and both code blocks are there. Against the Original:
   - Fences have no language (` ``` ` where the Original has `<code class="python">` and `<code class="text">`).
   - Blank lines inside the Python block are dropped (`import html, json, re` runs straight into `def clean(…)`).
   - The comment `# &quot; becomes a real quote` became `# " becomes a real quote`. That is a double unescape, and it changes what the comment says.
   - The three HTML diagrams and the quiz (4 questions with per-option explanations) are absent.

   The warning counts one code block missing, but neither is missing; what was lost is the diagrams and the quiz, which the warning does not count.

## Search

All three searches ran with the scope Tag `anthropic`.

1. **Plain query:** `lorekeep search 'scaled score 720 domain percentages' --limit 3`. All three hits are in `…articles-how-claude-certification-exams-are-scored…md`. The top hit, `:24`, is the lede ("What a [scaled] [score] of [720] out of 1,000 actually means…"), and the second, `:95` "> The short version", is the answer itself ("720 of 1,000 is a fixed standard on a scale that equalises exam forms, not a percentage."). **file:line pointed at the answer.** I opened line 95 and it matched.
2. **`--exact` for an identifier:** `lorekeep search --exact escalate_to_human --limit 3`. It returned `…the-six-ccar-f-exam-scenarios-explained…md:37`, `…ccar-f--204fac85.md:89` and `…ccar-f-cheat-sheet…md:39`, plus `+1 matches under other tags (--all)`. **All three lines hold the identifier.** I opened all three; they match.
3. **A query I expected to need `--all`:** first `lorekeep search 'jailbreak detection perplexity'`. Under `anthropic` it printed `no matches` / `+4 matches under other tags (--all)`. With `--all --limit 2` it found the NVIDIA NeMo Guardrails pages (`.cache/readings/docs.nvidia.com--nemo-guardrails…jailbreak-protection…md:16`), so the hint works. Second, `--exact escalate_to_human --all`: the extra match is `docs.langchain.com--oss-python-langchain-multi-agent-handoffs…md:33` under `nvidia`, but it appeared only once I raised `--limit` to 20. With `--all --limit 5`, five termidy hits filled the list. That cost me two extra calls (see Friction).

## Friction

### The brief

- **The Tag variable is misnamed.** `export LOREKEEP_anthropic=anthropic` should be `LOREKEEP_TAG=anthropic`. As written, my first `get` exited 2 with `lorekeep: error: get needs the Run's Tag: set LOREKEEP_TAG or pass --tag`. I used `LOREKEEP_TAG=anthropic`, assuming `anthropic` was the intended Tag. The brief should name the Tag explicitly, since the skill says the Tag is "set by the brief and never chosen by you".
- **The brief points at the wrong skill copy.** It says to read `.agents/skills/lorekeep/SKILL.md`, and that copy is older than the installed tool. It has no Readings and no `version` field, and its `search` examples show Store paths rather than `.cache/readings/` paths. Step 3 of the brief, "open the file at `path` (the Reading) and, where `version` differs from `path`, the Version too", uses terms the vendored skill never defines. I found them only by diffing against `~/Projects/lorekeep/src/lorekeep/skill/SKILL.md`. Either refresh the vendored copy before the Run or point the brief at the tool's own copy.
- **The converter list did not fit this batch.** The brief says to spot-check "a `md-twin`, a `raw-twin`, a `trafilatura …`, a `markitdown …`, a `verbatim` if your batch has them". This batch is one HTML site, and all 173 Versions are trafilatura. One line saying "a single-site batch will be all one converter; choose by size and warnings instead" would have saved a moment of doubt.
- **It did not say whether the archive is meant to keep the quizzes.** The brief says the Project "archives it whole now". It did not say whether "whole" includes the practice questions and the diagrams, which for this site are much of its value and which the Markdown loses. Saying whether the Originals count as the archive, or only the Versions, would tell a worker how loudly to report these losses.
- **Worked well:** the shell-loop instruction, the error JSON shape and the stderr-per-URL layout were clear and enough.

### The skill

- **The skill does not say what to do when `thin content` comes after the browser has already run.** It says: "`thin content` … needs the browser (`lorekeep[browser]`), which waits longer before `rendered a shell`." Here the error already says `the browser rendered a shell (434 characters after 3 attempts)`. Is that the end, or should I retry? I inferred "report, do not retry", because the line names no `ReadTimeout`, `ConnectError` or 5xx. The skill should say plainly: "a `thin content` that already names the browser is final; report it". As written, it reads as if I should go and get the browser.
- **The warning table has no row for silent losses.** "Exit `0` can still be a menu or a page that lost a list: open a Version under 2 KB". Here no Version was under 2 KB, yet 123 pages lost their diagrams and 154 their quizzes. A size rule cannot catch that. The skill could say that a warning-free large page can still lose embedded structures (HTML diagrams, script-held data), and that comparing one typical page with its Original is worth doing once per host.
- **The code/tables warning says "missing" when the content is only degraded.** The skill says to "report; compare with the Original; distrust nearby headings". In both warned pages nothing was missing: the table was present without its separator, and the code was present without its language and blank lines. The skill should say that "missing" can mean "not recognisable as a table or fence".
- **The unknown-host row contradicts the host rules here.** "`<host> is in no host table; stored as third-party` → report the host to the owner". The skill gives no hint that this can fire for a host that has a rule. I had to run `status --rules` to tell that apart from a real unknown host.
- **I could not tell when to read `references/store.md`.** It is linked for "The Store's files and fields". I needed `version` and Reading, and the vendored `store.md` does not mention them either; see the brief section.
- **The `--all` hint does not mention `--limit`.** The skill says "A last line `+N matches under other tags (--all)` means other guides' Sources answer too; widen with `--all` or `--tag`". It does not say that `--all` keeps the default `--limit 5`, so the other-tag hit can still fall below the cut.
- **Worked well:** the exit-1 retry rule (ReadTimeout, ConnectError or 5xx only) was quick to apply, and the log-line format was unambiguous.

### The tool

- **A host-root URL does not match a `host/` prefix rule.** `https://claude.termidy.com/` is normalised to `https://claude.termidy.com` (no slash) and then fails the rule `claude.termidy.com/`. The result is a false `is in no host table` warning, `publisher: "claude.termidy.com"` instead of `termidy`, and `claude.termidy.com` listed in `status`'s "Unknown hosts". Every other worker's root URL will hit the same bug for any host whose rule has a trailing slash.
- **The trafilatura code path has several fidelity bugs**, all on the prompt-engineering lesson:
  - fences lose `class="python"`; across this batch 0 of 119 Versions have a fence language;
  - blank lines inside `<pre>` are dropped;
  - `&quot;` inside code is decoded twice, from `&amp;quot;` to `&quot;` to `"`, so the code says something different from the page.
- **A table whose rows lead with `<th>` comes out with no separator row.** On `ccar-f/cheat-sheet`, the "Exam facts" table became pipe rows with no `|---|`, and the warning reports it as missing. Emitting an empty header row plus a separator would keep it a table.
- **The diagrams and quizzes are lost silently.** 415 diagrams on 123 pages, and 154 quizzes in a script, disappear with no warning. A warning that counts dropped `<figure>`/diagram blocks, or large text-bearing blocks that did not make it into the Markdown, would surface this. The "N% of main text" check did not fire, probably because main-text extraction drops those blocks too.
- **A page whose headings are not on their own lines gets no warning.** The root page's 11 headings became a list-item H1 and one 4 KB line with inline `##`. The skill promises a warning for "a long page with no headings", but none was printed, perhaps because the line contains `#`.
- **Link text runs into the description.** On the articles index, `<a>` blocks containing several block children lose the space or newline between title, description and date.
- **The thin-content error buries the important part.** A 300+ character error line puts "the browser rendered a shell (434 characters after 3 attempts)", the part that says retrying is pointless, at the very end. The leading `the host rule names no Twin;` is noise for a host where no Twin is expected.
- **The `+N matches under other tags` line does not say where those matches rank.** With `--all` and the default limit, the other-tag result did not appear. Printing the best rank of the other-tag hits, or showing at least one under `--all`, would save a call.
- **`--exact` results seem to come back in filename order.** `articles-…`, `ccar-f--…`, `ccar-f-cheat-sheet…`, `learn-…`, then the s3 page. That is fine for an identifier, but the skill does not say so.
- **Worked well:** 177 fetches against a Store shared with five writers in 345 s, with no lock errors; the stderr is short and one line per fact; the JSON lines appended cleanly.
