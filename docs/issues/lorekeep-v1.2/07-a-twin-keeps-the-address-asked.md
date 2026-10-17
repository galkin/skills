# 07: a Twin under `page_suffix` keeps the address the page was asked at

**What to build:** When a host rule names `md-suffix` with a `page_suffix`, the Twin reduction gives a Version the address the page was asked at (normalised, after redirects), not the Twin's address with `page_suffix` glued on. Found live on 2026-10-17 with the first Store's new rule for `build.nvidia.com/` (`twin = "md-suffix"`, `page_suffix = "/modelcard"`, which serves every model card as `<model>.md` and so replaces the browser there): `get https://build.nvidia.com/nvidia/safety-for-agentic-ai` read the Twin `…/safety-for-agentic-ai.md` and stored `url: …/safety-for-agentic-ai/modelcard`, so the guide's citation of `…/safety-for-agentic-ai` is "not stored" to `recheck --citations`. The rule: the Twin address of page P is P with `page_suffix` replaced by `.md` when P ends with it, else P + `.md`; the reduction of that Twin address is P itself, and nothing else. `recheck` of such a Version asks the Twin address recorded in `original.url`, unchanged.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] under a rule `twin = "md-suffix"`, `page_suffix = "/modelcard"`: `get https://build.nvidia.com/nvidia/safety-for-agentic-ai` (fixture: the Twin served as `text/markdown` at `…/safety-for-agentic-ai.md`, cut from the first Store's Version) stores `url: https://build.nvidia.com/nvidia/safety-for-agentic-ai`, `original.url: …/safety-for-agentic-ai.md`, `converter: md-twin`
- [ ] under the same rule, `get https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` stores `url` with `/modelcard` and `original.url` `…/nvidia-nemotron-nano-9b-v2.md`, as today
- [ ] a redirect before the Twin (page P redirects to Q, Q's Twin is read) stores `url: Q`; the `ms-foundry` redirect fixtures of v1 still pass
- [ ] `recheck` of the first Version asks `…/safety-for-agentic-ai.md` and records the check under `url: …/safety-for-agentic-ai`
- [ ] `references/store.md` › Twins says the Version's `url` is the page's address, with or without `page_suffix`, as asked
