# 03: the browser waits for the page, escalates on its own, and a shell is an error

**What to build:** The browser step renders a page in up to three attempts without any per-host setting, using Crawl4AI's own `CrawlerRunConfig` parameters (documented at `https://docs.crawl4ai.com/api/parameters/` › Page Navigation & Timing, and `https://docs.crawl4ai.com/core/page-interaction/` › Wait Conditions): attempt 1 `wait_until="networkidle"`; if the Markdown is still thin, attempt 2 adds `delay_before_return_html=3.0`; if still thin, attempt 3 adds `wait_for` as a `js:` condition that the document's main text (`main`, `[role=main]`, `article`, else `body`, scripts excluded) has grown past the thin threshold, with `wait_for_timeout=15000`. A page thin after the last attempt exits 1 with `lorekeep: error: nothing stored for <url>: the browser rendered a shell (N characters after 3 attempts)`; nothing is stored. The thin check is the static step's (`THIN_CHARACTERS`, `THIN_WORDS`, ratio against the rendered document). The `wait_for` host-rule key of the earlier draft is NOT added: the owner wants no configuration. `scripts/smoke.py` proves the browser with a temporary `browser = true` rule instead of expecting `milvus.io` to refuse a plain client. Decisions: `spec.md` › Browser.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] with the fake fetcher recording each `CrawlerRunConfig` it receives, a page whose first render is a shell and second render is full is stored `via crawl4ai` after exactly two calls: the first with `wait_until="networkidle"` and no `wait_for`, the second with `delay_before_return_html=3.0`; a page full on the first render makes one call
- [ ] a page that is a shell on all three renders (fixture: `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` as the browser returned it this round, 785 bytes of Markdown from a 77 KB document) exits 1 with the shell error, stores nothing, and the third call carried a `js:` `wait_for` and `wait_for_timeout=15000`
- [ ] the same model card with its loaded content (second fixture, cut from the live page) stores `via crawl4ai` with the card's description text in the Markdown
- [ ] a page that is short for real (rendered document and Markdown both small, ratio under the threshold) is stored on the first attempt, as today
- [ ] `get` of such a page live (the orchestrator runs it on `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` with the `browser = true` rule of the first Store) stores the card, not the menu; the Comment records which attempt won and the wall time
- [ ] `owner.md`'s `browser` key paragraph says the browser retries on its own and names the three attempts in one sentence; `SKILL.md`'s `thin content` bullet says the browser is tried with longer waits before the error; the flag test passes
- [ ] `scripts/smoke.py --bucket <empty bucket>` run live by the orchestrator reports the browser step `ok` with no stale `milvus` expectation
