# 03: the browser waits for the page, escalates on its own, and a shell is an error

**What to build:** The browser step renders a page in up to three attempts without any per-host setting, using Crawl4AI's own `CrawlerRunConfig` parameters (documented at `https://docs.crawl4ai.com/api/parameters/` › Page Navigation & Timing, and `https://docs.crawl4ai.com/core/page-interaction/` › Wait Conditions): attempt 1 `wait_until="networkidle"`; if the Markdown is still thin, attempt 2 adds `delay_before_return_html=3.0`; if still thin, attempt 3 adds `wait_for` as a `js:` condition that the document's main text (`main`, `[role=main]`, `article`, else `body`, scripts excluded) has grown past the thin threshold, with `wait_for_timeout=15000`. A page thin after the last attempt exits 1 with `lorekeep: error: nothing stored for <url>: the browser rendered a shell (N characters after 3 attempts)`; nothing is stored. The thin check is the static step's (`THIN_CHARACTERS`, `THIN_WORDS`, ratio against the rendered document). The `wait_for` host-rule key of the earlier draft is NOT added: the owner wants no configuration. `scripts/smoke.py` proves the browser with a temporary `browser = true` rule instead of expecting `milvus.io` to refuse a plain client. Decisions: `spec.md` › Browser.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] with the fake fetcher recording each `CrawlerRunConfig` it receives, a page whose first render is a shell and second render is full is stored `via crawl4ai` after exactly two calls: the first with `wait_until="networkidle"` and no `wait_for`, the second with `delay_before_return_html=3.0`; a page full on the first render makes one call
- [x] a page that is a shell on all three renders (fixture: `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` as the browser returned it this round, 785 bytes of Markdown from a 77 KB document) exits 1 with the shell error, stores nothing, and the third call carried a `js:` `wait_for` and `wait_for_timeout=15000`
- [x] the same model card with its loaded content (second fixture, cut from the live page) stores `via crawl4ai` with the card's description text in the Markdown
- [x] a page that is short for real (rendered document and Markdown both small, ratio under the threshold) is stored on the first attempt, as today
- [x] `get` of such a page live (the orchestrator runs it on `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` with the `browser = true` rule of the first Store) stores the card, not the menu; the Comment records which attempt won and the wall time
- [x] `owner.md`'s `browser` key paragraph says the browser retries on its own and names the three attempts in one sentence; `SKILL.md`'s `thin content` bullet says the browser is tried with longer waits before the error; the flag test passes
- [x] `scripts/smoke.py --bucket <empty bucket>` run live by the orchestrator reports the browser step `ok` with no stale `milvus` expectation

**2026-10-17 — implemented (branch `galkin/lorekeep-v12-03`).**

What changed:

- **The seam** (`edges.py`): `PageFetcher.fetch(url, wait)` takes a `Wait`, a frozen dataclass
  whose fields are the `CrawlerRunConfig` parameters of the same names (`wait_until`,
  `delay_before_return_html`, `wait_for`, `wait_for_timeout`); `Wait.config()` is the keywords
  set, and `Crawl4AIFetcher` passes them to `CrawlerRunConfig` beside `cache_mode` and `verbose`.
  The fake cannot receive a real `CrawlerRunConfig` (Crawl4AI is an extra the suite runs without),
  so "the fake fetcher recording each `CrawlerRunConfig` it receives" is `FakeFetcher.configs`,
  the keywords of each call. `FakeFetcher` takes a sequence of files for a page and renders the
  next one on each call (the last one ever after).
- **The step** (`cascade/browser.py`): `ATTEMPTS` are three `Wait`s, each adding to the one
  before — `networkidle`; `+ delay_before_return_html=3.0`; `+ wait_for=GROWN,
  wait_for_timeout=15000` — and the next runs only when the render was a shell. `GROWN` is a
  `js:` arrow function over `main`, `[role=main]`, `article`, else `body`: its `innerText` (which
  leaves `<script>` out) split into words must reach `THIN_CHARACTERS` characters and
  `THIN_WORDS` words (built from the constants). Crawl4AI 0.9.5's `csp_compliant_wait` returns
  `false` on timeout instead of raising, so a timed-out third render comes back and is judged like
  the others (the orchestrator saw the same live). After three shells:
  `the browser rendered a shell (N characters after 3 attempts)`, N the last render's characters
  of Markdown text; nothing is stored. A `FetcherNotInstalled`/`PageFetchError` on any attempt
  ends the step with its own line, as before.
- **The thin check** (`cascade/html.py`): extracted into `thin(markdown, page_text)` and used by
  both steps. `convert_rendered` returns a `Shell` when the Markdown is thin against the rendered
  document's `text_content()` (scripts included, as in the static step), measured **after** the
  rule's `cut` (what the owner cut is not the page), and also when the document is empty or
  Trafilatura finds no text — before, those two were plain errors with no second render.
- **Docs**: `owner.md`'s `browser` paragraph names the three renders in one sentence and the
  error; `SKILL.md`'s `thin content` bullet says the browser is tried with longer waits before
  `the browser rendered a shell` (one line added, 246 lines); README: the smoke paragraph, and the
  `milvus.io/` row no longer says "answers `403`" (`hosts.toml`'s comment saying so is removed).
- **`scripts/smoke.py`** appends a `milvus.io/docs/` rule with `browser = true` to the throw-away
  Store's `lorekeep.toml`, so the browser step is proved whatever Milvus answers a plain client.

Tests: `tests/test_get_browser_waits.py`, one per criterion 1–4, all under the first Store's
`build.nvidia.com/` rule (`browser = true`). Fixtures (README section "Rendered documents for the
fake browser"; single files, not response folders):
`build-nemotron-modelcard.rendered-shell.html`, `build-nemotron-modelcard.rendered-card.html`,
`browser-short-page.html`. The existing browser tests pass unchanged (their rendered pages are
short for real and stored on the first render).

Where the ticket or spec was wrong or could not be met as written:

- **"785 bytes of Markdown from a 77 KB document"**: the shell Original (77,433 bytes, provided
  by the orchestrator: the Version itself was removed from the Store by hand) converts to 216
  bytes of Markdown today; 785 was probably the Version file with its frontmatter. The document's
  text is 58,496 characters, so the ratio holds by far.
- **The shell was already a 404.** Its empty `<main>` holds Next.js's
  `<template data-dgst="NEXT_HTTP_ERROR_FALLBACK;404">`: the card was gone from
  `build.nvidia.com` before the second migration rendered it, and no wait would have loaded it.
  The orchestrator's live renders of the page today (`networkidle` + 3 s, and a `js:` wait of
  20 s) return 257 KB whose `<main>` reads "404 Error Even AI can't find this page!" behind a
  `200`: with this change that page ends in the shell error, nothing stored, which is the right
  outcome (a not-found page must not become a Version), though the line does not say "not found".
- **"Cut from the live page"**: impossible for the same reason, so the loaded card is synthesised
  from the shell: `<main>` replaced by the card's header, the page's own `<meta
  name="description">` (from the static fixture) and the overview paragraphs of the earlier
  hand-written `RENDERED_CARD`. The static fixture's payload, cut to 8,000 characters, holds no
  card text to take.
- **The exact error line** (`nothing stored for <url>: the browser rendered a shell (…)`) is what
  `get` prints under a `browser = true` rule. Without the rule the browser runs after the plain
  steps, and their reasons come first, joined by `; ` as for every error:
  `… the host rule names no Twin; thin content: … ; the browser rendered a shell (…)`.
- **Criterion 5 (live `get`)** and **criterion 7 (live smoke)** are the orchestrator's to run and
  are left unticked here. The nano-9b-v2 card cannot be stored live (above); the orchestrator
  runs criterion 5 on `nvidia/llama-3_1-nemotron-safety-guard-8b-v3/modelcard` instead and
  records the attempt that won and the wall time. Expect `networkidle` alone to cost 5–8 s on
  `build.nvidia.com`, so a shell costs about 3 × (5–8 s) + 3 + 3 + 15 s, 36–45 s, before the error.
- Seen on the way, not acted on: the static model card names a Markdown rendition,
  `<link rel="alternate" type="text/markdown" href="https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2.md">`;
  if `build.nvidia.com` serves Twins, a `twin` on its rule would spare the browser entirely.

**2026-10-17 — accepted (orchestrator), live criteria 5 and 7.**

- Live `get` with the first Store's `browser = true` rule, from the merged tree: the removed
  `nvidia-nemotron-nano-9b-v2/modelcard` ends in `the browser rendered a shell (42 characters
  after 3 attempts)` in 48 s; the existing `llama-3_3-nemotron-super-49b-v1_5/modelcard` ends the
  same way in 39 s. The 42 characters are "404 Error Even AI can't find this page!": headless
  Chromium gets a client-side not-found from `build.nvidia.com` for every card, so no wait helps
  on that host. The escalation itself behaves as built (three renders, nothing stored).
- Smoke (`scripts/smoke.py --bucket agentic-system-design-sources`): Twin ok, static ok,
  browser page `trafilatura 2.3.1 via crawl4ai 0.9.5` ok under the temporary rule; `restore`
  FAILs only because the bucket is still empty (first backup pending).
- **The implementer's aside is the real fix.** `build.nvidia.com/nvidia/<model>.md` answers
  `text/markdown` with the whole model card (frontmatter, `# <model>`, Model Overview …), and the
  "removed" nano-9b-v2 card is there in full (55 KB). A rule `twin = "md-suffix"`,
  `page_suffix = "/modelcard"` stores all three guide pages and
  `llama-3_3-nemotron-super-49b-v1_5/modelcard` as `md-twin` in a second each, no browser. The
  first Store's rule is changed to that. One wrinkle: a page without `/modelcard`
  (`nvidia/safety-for-agentic-ai`) is stored under `url` `…/safety-for-agentic-ai/modelcard`,
  because the Twin reduction appends `page_suffix` to the Twin's address; both addresses exist on
  the site, and the guide cites the shorter one, so `recheck --citations` must be checked for it.
