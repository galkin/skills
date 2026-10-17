# 03: the browser waits for the page, and a shell is an error

**What to build:** The browser step waits for the network to be idle and, when the host rule names `wait_for` (a CSS selector), for that element, capped at 10 seconds; the thin check runs on the rendered Markdown and a page still thin exits 1 with `lorekeep: error: nothing stored for <url>: the browser rendered a shell (N characters)`. `scripts/smoke.py` proves the browser with a temporary `browser = true` rule instead of expecting `milvus.io` to refuse a plain client. Decisions: `spec.md` › Browser.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] with the fake fetcher recording its `CrawlerRunConfig`, `get` of a page under a rule with `wait_for = "[data-testid=model-card]"` passes `wait_until="networkidle"`, that selector, and a 10,000 ms timeout; without `wait_for`, `networkidle` alone
- [ ] a fixture of `build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` as the browser returned it this round (menu only, 785 bytes of Markdown) exits 1 with the shell error and stores nothing; the same page with its loaded content (second fixture) stores `via crawl4ai`
- [ ] `owner.md` documents `wait_for` beside `browser` and `cut`; the flag test passes
- [ ] `scripts/smoke.py --bucket <empty bucket>` run live by the orchestrator reports the browser step `ok` and no stale `milvus` expectation
