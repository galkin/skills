# lorekeep migration 3 — batch `microsoft` (Microsoft Multi-Agent AI Solutions Expert)

lorekeep 0.1.1, Tag `microsoft` (see Friction › the brief, item 1: the brief as written sets no Tag).
Log: `log.jsonl` (291 lines, no retry lines because there was nothing to retry), per-URL stderr in
`err/<n>.txt` (n = line number in `batch-microsoft`), exit codes in `rc.txt`, times in `time.txt`.

## Numbers

| What | Count |
| --- | --- |
| URLs in batch | 291 (no duplicates) |
| Exit 0 | 291 — `stored` 274, `fresh` 17, `unchanged` 0, `changed`/`gone`/`error`/`skipped` 0 |
| Exit 1 | 0 |
| Exit 2 | 0 |
| Retries | 0 (no `ReadTimeout`, `ConnectError` or 5xx) |
| Converters | `md-twin` 268, `trafilatura 2.3.1` 18, `raw-twin` 5 (no `markitdown`, no `verbatim`) |
| Readings (`version` in JSON, `path` under `.cache/readings/`) | 22 (7 docs.langchain.com, 6 learn.microsoft.com/azure/architecture, 9 modelcontextprotocol.io) |
| Authorities | `primary` 282, `third-party` 9 |
| Publishers | microsoft 252, langchain 9, mcp 9, github 5, opentelemetry 5, huggingface 3, code.visualstudio.com 2, pydantic.dev 2, python 2, a2a 1, json-schema 1 |
| `url` ≠ `requested_url` | 7 (listed below) |
| Versions under 2 KB | 1 |
| Wall time | 370 s (6 min 10 s), 2026-10-17T21:03:07Z → 21:09:17Z, sequential, alongside five other workers |

The 17 `fresh` were Versions another worker (or an earlier run) had just stored, e.g. a2a-protocol.org
`fetched_at` 21:02:53Z, 14 s before my loop started.

## To report to the owner

**Unknown hosts** (`<host> is in no host table; stored as third-party`):

- `code.visualstudio.com` — https://code.visualstudio.com/docs/agent-customization/custom-instructions, https://code.visualstudio.com/docs/devcontainers/create-dev-container
- `pydantic.dev` — https://pydantic.dev/docs/validation/latest/concepts/models, https://pydantic.dev/docs/validation/latest/concepts/strict_mode (asked as `docs.pydantic.dev/latest/…`, which now redirects to `pydantic.dev/docs/validation/latest/…`; the warning names the final host)

**Error lines with URLs:** none.

**`third-party` pages the guide likely treats as primary** (judged by publisher; the citations CSV does not say how a lesson uses a Source):

- Microsoft's own product docs on a host with no rule: the two code.visualstudio.com pages above (lesson `ms-ai500-2026-10-1-2-9`).
- Microsoft's official SDK repository, `third-party under the github.com/ rule`:
  - https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/agentic_evaluators/sample_task_completion.py (`1-2-8`)
  - https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/agentic_evaluators/sample_tool_call_success.py (`1-2-8`)
  - https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/agentic_evaluators/sample_tool_selection.py (`3-1-4`)
- Unsure (a `microsoft` org research repository, not product docs), same rule:
  - https://github.com/microsoft/rankerEval/blob/main/docs/source/metrics.rst (`3-1-6`)
  - https://github.com/microsoft/rankerEval/blob/main/rankereval/metrics.py (`3-1-6`)
- The library's own docs, but no rule: the two pydantic.dev pages (`0-10`).

**Missing code blocks / tables** (`N code blocks / M tables of the page are missing from the Markdown`):

- https://pydantic.dev/docs/validation/latest/concepts/models — 13 code blocks / 0 tables (checked: Original has 50 `<pre>`, Version 37 fences; e.g. the `list` example under "Data conversion" is gone, the sentence "such as [`list`]…:" now ends on nothing)
- https://pydantic.dev/docs/validation/latest/concepts/strict_mode — 3 code blocks / 0 tables
- https://reference.langchain.com/python/langchain-core/runnables/base/RunnableParallel — 0 / 2 tables (checked: worse than the warning says, see Spot checks)
- https://reference.langchain.com/python/langchain-core/runnables/base/RunnableSequence — 0 / 1 table (same page template as RunnableParallel; not opened)

**`thin content`:** none. **Main-text share warnings** (`holds N% of the page's main text`): none.
**Reading-rule warnings** (`rule <name> removed N …`): none.

**Not required by the skill, but the guide should know** — `url` differs from the cited address in a way that changes the page:

- https://modelcontextprotocol.io/specification/2026-07-28/basic/lifecycle → https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning. The 2026-07-28 revision has no Lifecycle page; the Version says "There is no negotiation handshake." Lessons `2-3-3` and `2-3-4` cite the lifecycle URL for that revision.
- https://learn.microsoft.com/en-us/agent-framework/hosting/azure-functions → https://learn.microsoft.com/en-us/agent-framework/hosting/durable-extension (lesson `2-4-6`).
- docs.pydantic.dev → pydantic.dev/docs/validation (2 URLs, above).
- Cosmetic (a `?view=` query added by the redirect): devops/pipelines/process/approvals `?view=azure-devops`, machine-learning/how-to-deploy-models-from-huggingface `?view=azureml-api-2`, python/api/overview/azure/ai-evaluation-readme `?view=azure-python`.
- Canonical warnings (skill: do nothing), for completeness: 3 huggingface.co `/en/` pages declare the language-less URL canonical.

## Spot checks

1. **`md-twin`, smallest and the only one under 2 KB** — https://learn.microsoft.com/en-us/agent-framework/workflows (1 935 B, no Reading). The page's content: H1 "Workflow capabilities", one paragraph, four H2s each with a two-column table of links (Composition, Interaction and durability, Operations, Multi-agent orchestration). It is a hub page, so small is right. There is no Original to compare (Twin, `original.stored: false`), so the skill's "compare it with its Original" could not be done.
2. **`raw-twin`, smallest** — https://github.com/microsoft/rankerEval/blob/main/docs/source/metrics.rst (3 161 B). The raw `.rst` file whole, inside one ```` ```rst ```` fence under `# docs/source/metrics.rst`; title, `autosummary` and the `code-block:: python` example all there. Content, verbatim; one Section to `search`.
3. **`trafilatura`, warned, smallest** — https://reference.langchain.com/python/langchain-core/runnables/base/RunnableParallel (Version 4 320 B, Original 435 601 B). The prose and both code examples are there, but every heading below the H1 is lost (the Original has h2/h3 "Constructors", "Attributes", "Methods", "Inherited from RunnableSerializable/Serializable/Runnable", "Parameters"), the method and attribute *names* are gone, and what is left is a run of orphaned one-liners ("Get the namespace of the LangChain object.", "Get the name of the `Runnable`.") plus one broken table fragment (`| Default:\`None\` The steps to include. |`). The Original has 5 `<table>`s; the warning says 2. The API-reference half of the page is effectively unusable; the conceptual half is fine.
4. **`trafilatura`, warned, large** — https://pydantic.dev/docs/validation/latest/concepts/models (52 070 B). Page content: H1 "Models", the H2/H3 structure intact, 37 code fences, prose intact. 13 code blocks missing (see above); fences carry no language tag; the admonition titles come out as stray `## API Documentation` headings (twice) in the middle of sections.
5. **`md-twin` with a Reading** — https://docs.langchain.com/oss/python/langgraph/persistence (Reading 5 026 B vs Version 5 827 B) and https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning. `diff` of Reading vs Version: the Reading dropped only the "> ## Documentation Index / Fetch the complete documentation index at …/llms.txt" banner and, for LangChain, the trailing `<div className="source-links">` callouts ("Connect these docs…", "Edit this page on GitHub"). Every other line identical. Cleaner, nothing lost. The Reading's frontmatter has only `url`, `version`, `sha256`, `rules`, `title` — no `authority`, `publisher` or `fetched_at`.

## Search

All with `LOREKEEP_TAG=microsoft`.

1. Plain: `lorekeep search 'magentic manager task ledger' --limit 3` → 3 results. Hit 1, `…ai-agent-design-patterns…md:242` (a Reading), is the paragraph that says "the magentic manager agent builds a task ledger" — correct (the paragraph is one long line). Hit 3, `…workflows-orchestrations-magentic…md:205`, points at the Section's first prose line ("Execute a complex task and handle events…"); the matched text in the snippet (`MagenticProgressLedger ledger = …`) is at line 258, 53 lines lower.
2. `--exact`: `lorekeep search --exact 'MCP-Protocol-Version' --limit 3` → 3 results from the 2025-11-25 lifecycle, 2025-11-25 transports and 2026-07-28 streamable-http Readings, `+4 matches under other tags (--all)`. `…streamable-http…md:256` is exactly the line `` `MCP-Protocol-Version` header. `` (second line of "Every POST request to the MCP endpoint **MUST** include an …"). Correct.
3. Expected to need `--all`: `lorekeep search 'jailbreak perplexity threshold'` → `no matches` / `+3 matches under other tags (--all)`; with `--all` → the NVIDIA NeMo Guardrails Readings. Hit 1 printed `…configuration-reference…md:378`, which is the line `jailbreak_detection:` of a YAML block; the snippet shows the table row `rails.config.jailbreak_detection.length_per_perplexity_threshold | float | 89.79`, which is line 394 (the YAML value is at 381). Near, not at.

So `file:line` was exact in 2 of the 4 hits I opened, and 16–53 lines off in the other 2.

## Friction

### The brief

1. **The Tag line is broken.** `export LOREKEEP_microsoft=microsoft` sets no Tag; as written, `lorekeep get` answers `lorekeep: error: get needs the Run's Tag: set LOREKEEP_TAG or pass --tag` (exit 2, checked). `brief-template.md` has `export LOREKEEP_TAG=TAG`, and the substitution replaced both `TAG`s; `brief-aws-a.md` has `LOREKEEP_aws=aws`, so all six briefs likely carry it. I used `LOREKEEP_TAG=microsoft`, which the skill forbids me to choose ("set by the brief and never chosen by you"). Substitute a placeholder that cannot appear elsewhere (`{{TAG}}`).
2. **The brief and the vendored skill disagree on the model.** The brief says "open the file at `path` (the Reading) and, where `version` differs from `path`, the Version too" and asks for "reading-rule warnings". The skill it sends me to, `.agents/skills/lorekeep/SKILL.md` (untracked in this worktree), never says "Reading", has no `version` field and no `rule <name> removed` row. The shipped `~/Projects/lorekeep/src/lorekeep/skill/SKILL.md` has all three. I read that diff to understand the output. Either refresh the vendored copy before dispatch or name the file to read.
3. "third-party pages the guide treats as primary" needs to know how a lesson uses a Source; the batch is a bare URL list and the citations CSV has only `work_id,url,as_of`. I judged by publisher. A column saying primary/context, or a sentence saying "judge by publisher", would settle it.
4. The brief asks to "Spot-check … a `markitdown …`, a `verbatim` if your batch has them" — fine; it could say converters are in the JSON so a one-liner `Counter` finds them (it does say so).
5. Worked well: the per-URL `err/<n>.txt` instruction, the exact log format for exit 1, and "Five other workers… lorekeep's lock handles that" (no contention observed).

### The skill

1. Stale vendored copy (Brief 2): a Run following it would not know that `path` can be under `.cache/readings/`, that `version` is the evidence, or that search returns Reading paths.
2. "open a Version under 2 KB, compare it with its Original" — 273 of my 291 are Twins with no Original (`original.stored: false`). What to compare a small Twin with? Also: is 2 KB the file (frontmatter is ~600 B of it) or the body? I used file size.
3. "`N code blocks / M tables … missing` → report; compare with the Original; distrust nearby headings". Comparing a 435 KB HTML Original by eye is not practical; I wrote a Python tag counter. And "distrust nearby headings" understates RunnableParallel, where *all* headings were gone, not misplaced. Say what a Run should do with the result (report only? avoid citing the Version for the lost part?).
4. "a page the guide treats as primary there (a vendor's repository; report when unsure)" — for Microsoft, is `github.com/microsoft/<research repo>` a vendor's repository? I reported it as unsure. An example with an org vs a project would help.
5. Nothing in the skill tells a Run to notice that `url` is a *different page* from the one asked (lifecycle → versioning). "The returned `url` may differ … it is the one to cite" makes it sound always harmless; for a guide it means the cited page no longer exists.
6. "`file:line` is the matching line: open the file there." — not true for 2 of 4 hits I checked (Search 1 hit 3, Search 3).
7. Readings have no `authority` in frontmatter, so "Cite the Version's `url` as far as its `authority` allows" needs the JSON line or the Version open, which the skill does not say.
8. Minor: the exit-1 example line appears twice (in the Run example and again after the retry list); the shipped skill removed the second.

### The tool

1. **No signal for a redirect to another page.** `requested_url` `…/2026-07-28/basic/lifecycle` → `url` `…/basic/versioning` came with empty stderr; I found it only by diffing two JSON fields. Wanted: `lorekeep: note: <asked> was served as <url>` when the path changes (not for a slash, fragment or added `?view=`).
2. **`file:line` in search is the Section's first matched-word line, not the matched text.** Hit at `:205` with the snippet at `:258`; hit at `:378` with the snippet at `:394`. Wanted: the line of the snippet's first bracketed term.
3. **The missing-tables count undercounts and headings are not checked.** RunnableParallel: warning "0 code blocks / 2 tables", the Original has 5 tables and 11 h2 + 6 h3, the Version has only the H1. A "N of M headings missing" check would have flagged the real loss.
4. **Reading frontmatter lacks `authority`, `publisher`, `fetched_at`.** Whoever opens `path` (or a search hit under `.cache/readings/`) cannot see the authority without opening the Version.
5. trafilatura fences have no language tag (pydantic, RunnableParallel), and admonition titles become stray `##` headings ("## API Documentation" mid-section in pydantic models), which split Sections for `search`.
6. `fresh` does not say whether this `get` added the Tag; `fresh` vs `stored` across concurrent workers is otherwise noise in the counts.
7. Worked well: 291 fetches in 370 s with five concurrent writers and no lock errors; stderr is short and greppable (14 of 291 URLs said anything at all); the JSON line is complete and stable; `+N matches under other tags (--all)` told me exactly when to widen.
