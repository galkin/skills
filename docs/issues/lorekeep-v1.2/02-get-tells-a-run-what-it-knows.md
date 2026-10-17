# 02: `get` tells a Run what the tool knows

**What to build:** `get --json`/`add --json` carry `asked` (the argument as given, fragment included); a Version stored with a missing-code/table or main-text-ratio warning records it in frontmatter `warnings` and `get` prints those warnings on every return of that Version; a `third-party` verdict from a catch-all rule or from no rule prints a `lorekeep: note:` naming the rule; the thin check gains a ratio against the page's main element that warns (and stores) when the Markdown holds under a fifth of it, whatever its absolute size. Index `versions.warnings`, `SCHEMA_VERSION` bump. Decisions: `spec.md` › What `get` tells a Run.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `get --json 'https://docs.langchain.com/oss/python/langchain/middleware/built-in#model-fallback'` prints `asked` with the fragment, `requested_url` and `url` without it
- [x] the Mintlify fixture that prints `1 code blocks / 0 tables … missing` on its first `get` prints the same warning on a second `get` (`outcome: fresh`) and its frontmatter has `warnings: ["1 code blocks / 0 tables of the page are missing from the Markdown"]`
- [x] `get` of a `github.com/someone/repo` page under the default catch-all prints `lorekeep: note: <url> is third-party under the github.com/ rule`; a page under no rule prints `… under no rule` beside the unknown-host warning; a page under `github.com/NVIDIA/` prints neither
- [x] (rewritten 2026-10-17, see Comments) a page whose Markdown holds under a fifth of its main element's text, navigation left out (synthesised `guides-catalog.html`), stores with `lorekeep: warning: <url>: the Markdown holds N% of the page's main text`; the Model-Optimizer `guides/1_quantization.html` fixture keeps its toctree list and prints no warning; the kubernetes.io Deployment fixture prints no such warning
- [x] an Index built by v1.1 is rebuilt by the next reader; `search --json` is unchanged
- [x] `references/store.md` documents `asked` and `warnings`; the flag test passes

## Comments

**2026-10-17 — implemented (branch `galkin/lorekeep-v12-02`).** Tests in
`tests/test_get_tells.py`, one per criterion, each naming its fixture.

- **`asked`.** `version_json` takes `asked`, placed after `url`: `get` passes its URL argument
  exactly as given, `add` its FILE argument (the "argument as given" for `add` is the file, not an
  address; `store.md` says so). `requested_url` is unchanged.
- **`warnings` in the frontmatter.** A converter's warnings no longer carry the address
  (`Converted.warnings` is the text alone); `provenance.build` writes them as `warnings`, a YAML
  flow list of quoted strings (`frontmatter.render` learned lists; `BaseLoader` reads them back as
  a list of strings), absent when empty. `get` no longer prints the cascade's warnings itself: its
  `report` reads the returned Version's `warnings` and prints `lorekeep: warning: <url>: <text>`
  on every return (`stored`, `fresh`, `unchanged`, `changed`, `gone`, `error`, `skipped`), `<url>`
  being the Version's `url`. A Recheck that stores a new Version keeps its warnings the same way.
  A Version stored by v1.1 has no `warnings` and prints none on a `fresh` return; a fetch whose
  Markdown hash equals such a Version's returns the old file and prints none either (the file is
  never rewritten).
- **The `third-party` note.** `urls.trust` returns a `note` beside its `warning`; `get` prints both
  once per call, on every return. "Catch-all" had no definition in the spec; it is a rule whose
  prefix is a whole host (`catch_all`: no `/` before the trailing one). In the default table that
  is `github.com/`, `raw.githubusercontent.com/` and `claude.termidy.com/`, so termidy pages now
  print the note too (their verdict is third-party for the whole host, which is what the note
  says). The criterion's `github.com/NVIDIA/` case is tested with the fixture there is,
  `github-docker-compose.raw` under the first Store's `github.com/NVIDIA-AI-Blueprints/` rule.
- **Main-text ratio — the ticket and the spec were wrong here, and the criterion is rewritten
  (orchestrator's decision, option A).** Measured on the first Store: the Model-Optimizer
  `1_quantization.html` Version keeps 700 characters of text of 1,087 in its `<main>` (1,001 in
  its `<article>`), 64%: the toctree it lost is about a third of the text. The spec's "under a
  fifth" holds only against the whole document (13%), which the same spec rules out. As
  specified (Markdown under a fifth of the text of `<main>`/`[role=main]`/`<article>`), the ratio
  also fired on 5 of the Store's 220 HTML Versions with a main element, all of them sites whose
  `<main>` holds their sidebar: `docs.docker.com` `compose/how-tos/startup-order` and
  `compose/how-tos/production` (14%), `grafana.com` `alerting/fundamentals/alert-rule-evaluation`
  (16%), `developers.openai.com` `chat/completions/methods/create` (18%) and
  `ai-act-service-desk.ec.europa.eu` `article-113` (9%). Built instead:
  - The ratio counts the main element's text without `script`, `style`, `noscript`, `template`,
    `nav`, `aside`, `header`, `footer` and `[role=navigation]` (`html.main_text`), and runs in
    `extract`, so the browser's output is measured too. On the Store it now fires on two Versions:
    the OpenAI API reference (18%; a real loss: every parameter name and nested parameter is
    missing) and AI Act article 113 (9%; a false positive, its recitals index is a plain `<div>`).
    The warning is `the Markdown holds N% of the page's main text`, stored in `warnings`. The
    600-character `thin content` error is unchanged and runs first.
  - The warning is tested on `guides-catalog.html`, synthesised: three paragraphs Trafilatura
    keeps, then sixteen headed link lists it drops (14%). No real Store page short enough for a
    fixture shows the defect: the OpenAI page is 2 MB and its cut loses the ratio.
  - The Model-Optimizer loss itself is fixed: a list alone in a `<div>` (Sphinx's
    `toctree-wrapper`) after the `<p>` that introduces it is a prose list (`html.wrapper`), so the
    v1.1 main-subtree retry keeps it. The fixture `model-optimizer-quantization.html` (cut from the
    Store's Original) stores all eight toctree entries and prints no warning. As with
    OpenTelemetry's signal names, the retry keeps each item's text and drops its link.
  - `kubernetes-deployment.html` prints no main-text warning.
- **Index.** `versions.warnings` holds the list as JSON text; `SCHEMA_VERSION` is 4. The test
  turns a built Index into a v1.1 one (schema 3, no `warnings` column) and checks that the next
  `search --json` rebuilds it and prints the same bytes as before.
- **Skill.** `references/store.md` documents `asked` (JSON) and `warnings` (frontmatter). In
  `SKILL.md`, the sentences ticket 05 wrote for v1.1 became false and were changed in place: the
  log keeps the fragment in `asked` (the separate `{"asked": …}` log line is gone); fragments are
  "kept in `asked`"; a `third-party` verdict from no rule or a whole-host rule prints a note; a
  Version's warnings print on every return. The stderr table gained the main-text and
  `third-party` rows; the `get --json` and `add --json` examples carry `asked`, and the `get`
  example's stderr the note line, as `tests/test_skill.py` requires. SKILL.md is 248 lines.
