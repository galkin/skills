# Batch aa — NCP-AAI Sources into the lorekeep Store

lorekeep 0.1.1, Store `~/orca/sources/agentic-system.design`, Tag `nvidia`. Loop: `run.sh` in this
folder; per-URL exit codes in `rc.txt` (`<n> <rc> <url>`), stderr in `err/<n>.txt`.

## Numbers

- URLs: 127 lines, 127 attempted, 127 lines in `log.jsonl` (no retry lines — see below).
- Exit 0: 126 — `stored` 124, `fresh` 2. No `unchanged`, `changed`, `gone`, `error`, `skipped`.
  - The 2 `fresh` are lines 24–25, `…/middleware/built-in#model-fallback` and `#to-do-list`. They
    point at the same page as line 23, which stored it a moment earlier, so 124 distinct Sources.
  - Converters: `trafilatura 2.3.1` 75, `md-twin` 50, `markitdown 0.1.8` 1. No `raw-twin`, no `verbatim`.
  - Authority: `primary` 123, `official` 3. No `third-party`.
- Exit 1: 1 — `thin content` (line 5, build.nvidia.com modelcard).
- Exit 2: 0.
- Retries: 0. The only exit 1 is `thin content`, which the skill does not list as retryable
  (`ReadTimeout`/`ConnectError`/`5xx` only).
- Wall time: 147 s for the loop (about 1.2 s per URL, while the other two workers shared the lock).

## To report to the owner

**Unknown hosts:** none. No `is in no host table` warning in any `err/*.txt`.

**Error lines (exit 1):**

- https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard —
  `lorekeep: error: nothing stored for https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard: the host rule names no Twin; thin content: https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard converted to 290 characters of a page of 58538; this page needs a browser and Crawl4AI is not installed: install the extra lorekeep[browser] (uv sync --extra browser)`
  → **thin content**: the owner needs to install `lorekeep[browser]`.

**`third-party` pages the guide treats as primary:** none. Nothing in this batch came back `third-party`.

**Authority values the skill's rule may contradict:** the skill says *"The `authority` of a law or
standard published by its issuer … is `primary`, whatever its Version says; report a different value."*

- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-113 — `official`, publisher `eu`
- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-26 — `official`, publisher `eu`

  These pages are the EU AI Act's own articles, served by the Commission's AI Act Service Desk
  rather than EUR-Lex. If the owner counts the Commission as "the issuer", they should be `primary`.
  I report them and do not decide.
- https://creativecommons.org/licenses/by/4.0/legalcode.en — `official`. This is a licence
  published by its issuer. It is not a law or standard, so the rule probably does not apply. Listed
  for completeness.

**Missing code blocks / tables (the Version is partial, its Original is whole):**

- https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/functions-and-function-groups/function-groups.html — 8 code blocks / 0 tables
- https://docs.nvidia.com/nemo/agent-toolkit/latest/reference/rest-api/api-server-endpoints.html — 2 code blocks / 0 tables
- https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create — 1 code block / 0 tables
- https://docs.nvidia.com/nemo/agent-toolkit/latest/api/nat/data_models/interactive/index.html — 0 code blocks / 2 tables
- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/overview.html — 0 code blocks / 1 table
- https://docs.nvidia.com/deeplearning/riva/user-guide/docs/asr/asr-overview.html — 0 code blocks / 1 table
- https://docs.nvidia.com/nemo/agent-toolkit/latest/api/nat/plugins/redis/redis_editor/index.html — 0 code blocks / 1 table
- https://docs.nvidia.com/nemo/agent-toolkit/latest/components/auth/api-authentication.html — 0 code blocks / 1 table

**A Version that is navigation, not content (no warning, exit 0; see Spot checks):**

- https://build.nvidia.com/nvidia/safety-for-agentic-ai — `stored`, `trafilatura 2.3.1`, 1162 bytes.
  The body is the site menu. This is the same host as the thin-content error above, but this page
  slipped past the thin-content check.

**Other stderr (nothing to do, per the table):** `https://a2a-protocol.org/v1.0.0/specification declares another page as canonical (https://a2a-protocol.org/latest/specification)`.

## Spot checks

No `raw-twin` or `verbatim` Version exists in this batch, so I checked five Versions from the three
converters that occurred, choosing the most suspicious ones (the smallest file, a warned file):

1. **md-twin** — https://docs.nvidia.com/nemo/guardrails/latest/about-nemo-guardrails-library/rail-types
   (the smallest Twin). **Content.** It has the H1 `Guardrail Types`, H2s, and two proper Markdown
   tables. The body opens with the publisher's llms.txt boilerplate blockquote ("This page is for
   version Latest… For clean Markdown of any page, append .md…") before the H1. This is harmless,
   but the boilerplate lands in the `(top)` Section of every Twin from this host. There is also one
   broken image path: `file:_dot_dot_/docs/_static/images/…`.
2. **trafilatura** — https://build.nvidia.com/nvidia/safety-for-agentic-ai (the smallest Version of
   the batch). **Not content: a menu.** The body is `Skip to main content / Search / ⌘K / Explore /
   Models / Skills / … / Login`, twice, then the card's tag list ("This Blueprint has been
   deprecated", "View GitHub", "Deploy on Cloud"). It has no description text. It was stored with
   exit 0 and no warning.
3. **trafilatura** — https://docs.nvidia.com/nemo/agent-toolkit/latest/components/agents/tool-calling-agent/index.html
   (the second-smallest, 1365 bytes). **Content.** It has the H1 and two paragraphs. The Original
   (`….orig.html`, 204 KB) has only that one heading too, so this is a genuinely short index page,
   not lost content.
4. **trafilatura, with a warning** — function-groups.html ("8 code blocks … missing"). **Content,
   with damage you can see.** The headings and most code blocks are present (33 fences in the
   Version against 41 `<pre>` in the Original, which matches the "8 missing" warning exactly). Three
   kinds of damage:
   - At least one Python block lost its fence, so its comments became Markdown headings: lines
     253/255/263 read `# Get the function group`, `# Get all functions, even excluded ones`, and
     `# Only works if "add" is in the include list`. These now appear as fake Sections in `search`.
   - No fence has a language tag.
   - Blank lines inside the code are gone.
5. **markitdown** — https://dam-cdn.nvd.orangelogic.com/AssetLink/64tei188l3tt132l265u1ipjoexdl1p5.pdf
   (the NCP-AAI Exam Study Guide PDF). **Content.** It has the title (repeated) and the contents list
   with exam weights, and no Markdown headings, which matches what the skill warns about PDFs.
   Words are not run together in the part I read.

## Search

1. Plain search, worded the way a guide writer asks:
   `lorekeep search 'which rail type validates tool call arguments'` → `no matches` (exit 0).
   The same idea with fewer words, `lorekeep search 'execution rails tool call arguments' --limit 3`,
   returned the answer as its third hit, `…rail-types--c0162b5b.md:31 | Guardrail Types | …[Execution] [rails] control and validate [tool]/function [calls], their [arguments]…`.
   Line 31 is exactly the sentence that answers the question. The first two hits (runtime-security
   FAQ:107 and tool-calling catalog:31) are relevant too. **`file:line` pointed at the answer**, but
   only after I dropped the question words.
2. Exact: `lorekeep search --exact 'instance_name__function_name'` → one hit,
   `…function-groups.html--812b7a09.md:238 | Function Groups > Key Concepts > Function Naming and Namespacing | …**Pattern**: [instance_name__function_name]…`.
   **Correct line.** `--exact register_function_group --limit 3` also returned the correct lines
   (function-groups:140 and :528, middleware:543).
   The first search printed `lorekeep: note: the Index was missing or stale and was rebuilt (374 Versions, 8219 Sections)`.

## Friction

1. **A plain query worded as a question returns `no matches` with no hint.** The skill says *"ranked
   by BM25; word forms match"*, which reads like ranking without a requirement that every word
   match. In practice `which rail type validates tool call arguments` found nothing, while a subset
   of the same words found three good hits. So the search apparently requires every word (or some
   stopword handling is missing), and the skill does not say so. A writer will ask in questions.
   Either the skill should say "use the page's own words, not a question; every word must occur",
   or `no matches` should say which terms matched nothing.
2. **The thin-content check missed a menu-only page.** https://build.nvidia.com/nvidia/safety-for-agentic-ai
   was stored as navigation chrome, with exit 0 and no warning. Its neighbour on the same host (the
   modelcard) correctly failed as thin. The skill gives no way to notice this except opening the
   file. If an exit 0 can be a menu, the skill should say "check the size, or open the file, for
   build.nvidia.com and other SPA hosts". Better, the check should catch it: 1162 bytes, almost all
   of it nav lines.
3. **The Version keeps no fragment, so my log loses what I asked for.** Lines 23–25 of the batch are
   one page with no fragment, `#model-fallback` and `#to-do-list`. All three log lines are identical
   (`requested_url` drops the fragment too). The skill says *"keep the fragment yourself"*, but with
   the log format the brief prescribes ("append each JSON line") there is nowhere to keep it. I could
   tell them apart only from `rc.txt`. Suggestions: put an `asked` field with the raw argument in the
   JSON, or have the skill say to log the raw URL beside the JSON.
4. **"Missing code blocks" understates the damage.** The warning `8 code blocks / 0 tables of the
   page are missing from the Markdown` suggests the blocks are absent. In fact some were unfenced and
   became prose, and their `#` comments became headings, which then create fake Sections in
   `search` (`Function Groups > … > Get the function group`). The skill's instruction *"report it;
   the Version is partial, its Original whole"* does not tell a reader to distrust the headings near
   such blocks, or that the Original is the `.orig.html` beside the Version. I had to find that file
   by `ls`, because the path is not in the JSON or the skill (it may be in `references/store.md`,
   which I did not open, per the brief).
5. **The authority rule for laws is hard to apply.** *"a law or standard published by its issuer (an
   EU regulation on EUR-Lex …) is `primary`, whatever its Version says"* — the AI Act service desk
   (ai-act-service-desk.ec.europa.eu) is the Commission, not EUR-Lex, and lorekeep says `official`.
   I could not tell whether that is "its issuer", so I reported it rather than deciding. A sentence
   on what "issuer" covers (only the official journal, or any EU institution) would settle it.
6. **Without a warning, nothing tells me the authority was a rule's decision.** No host was unknown,
   so every page came back `primary`/`official` silently. Pages such as
   developers.openai.com (`primary`, publisher `openai`) are fine, but I cannot see which rule
   matched without `status --rules`. The skill lists that command under `status`, which is not
   forbidden, but the brief is silent on it, so I did not run it.
7. **The skill's example error says "a page of 8309", the real one "a page of 58538".** That is
   fine, but the skill could state the threshold, so a reader knows why 1162 bytes passed and 290
   characters failed.
8. **Worked well:** parallel `get` with two other workers produced no lock errors and no slowdown
   worth noting. The `--json` lines are easy to aggregate. The stderr table covered every warning I
   saw. The `lorekeep: note:` about the index rebuild is self-explanatory.
