# 07: a Twin under `page_suffix` keeps the address the page was asked at

**What to build:** When a host rule names `md-suffix` with a `page_suffix`, the Twin reduction gives a Version the address the page was asked at (normalised, after redirects), not the Twin's address with `page_suffix` glued on. Found live on 2026-10-17 with the first Store's new rule for `build.nvidia.com/` (`twin = "md-suffix"`, `page_suffix = "/modelcard"`, which serves every model card as `<model>.md` and so replaces the browser there): `get https://build.nvidia.com/nvidia/safety-for-agentic-ai` read the Twin `…/safety-for-agentic-ai.md` and stored `url: …/safety-for-agentic-ai/modelcard`, so the guide's citation of `…/safety-for-agentic-ai` is "not stored" to `recheck --citations`. The rule: the Twin address of page P is P with `page_suffix` replaced by `.md` when P ends with it, else P + `.md`; the reduction of that Twin address is P itself, and nothing else. `recheck` of such a Version asks the Twin address recorded in `original.url`, unchanged.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] under a rule `twin = "md-suffix"`, `page_suffix = "/modelcard"`: `get https://build.nvidia.com/nvidia/safety-for-agentic-ai` (fixture: the Twin served as `text/markdown` at `…/safety-for-agentic-ai.md`, cut from the first Store's Version) stores `url: https://build.nvidia.com/nvidia/safety-for-agentic-ai`, `original.url: …/safety-for-agentic-ai.md`, `converter: md-twin`
- [x] under the same rule, `get https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2/modelcard` stores `url` with `/modelcard` and `original.url` `…/nvidia-nemotron-nano-9b-v2.md`, as today
- [x] a redirect before the Twin (page P redirects to Q, Q's Twin is read) stores `url: Q`; the `ms-foundry` redirect fixtures of v1 still pass
- [x] `recheck` of the first Version asks `…/safety-for-agentic-ai.md` and records the check under `url: …/safety-for-agentic-ai`
- [x] `references/store.md` › Twins says the Version's `url` is the page's address, with or without `page_suffix`, as asked

## Comments

**2026-10-17** — done on `galkin/lorekeep-v12-07`; tests in `tests/test_get_twin_address.py`, one
per criterion, each naming its fixture, under the first Store's rule for `build.nvidia.com/`. New
fixtures: `build-safety-for-agentic-ai.twin`, cut from the first Store's Version
`build.nvidia.com--nvidia-safety-for-agentic-ai-modelcard--cfd52a76.md` (a Twin keeps no Original:
its body to `## Minimum System Requirements`, with the Version's `title` put back as the Twin's
frontmatter); `build-nemotron-nano.twin` and `build-safety-for-agentic-ai.301`, synthesised.

- **The Twin step files the Twin under the page asked** (`cascade/twin.py` › `asked_page`,
  `TwinStep.attempt`). When the Twin answered at the address built from the page asked, the
  Version's `url` is that page, normalised; `reread`, which a Recheck also calls, still returns
  the Twin's address, and a Recheck files under the stored `url`, so nothing there changed. After a
  redirect the `url` is the page of the Twin redirected to, in the form asked (`twins.py` ›
  `to_asked_page`): `page_suffix` goes back on only when the page asked carried it. `github-raw`
  is untouched (its `blob/` page is already the page asked).
- **`recheck`** already asked `original.url` and recorded under the stored `url`; the test pins it
  for this Version.
- `references/store.md` › Twins: the `md-suffix` bullet says `url` is the page's address as asked,
  with or without `page_suffix`. `SKILL.md` is unchanged (no sentence of it became false).

Where the ticket was wrong or loose:

- "**A redirect before the Twin** (page P redirects to Q, Q's Twin is read)": the cascade never
  asks the page before its Twin. The redirect `get` sees is the Twin's own (`P.md` → `Q.md`, as
  Microsoft Learn's `?accept=text/markdown` chain is), so the fixture is a `301` at the Twin
  address, and whether Q keeps `page_suffix` is taken from P.
- "**The reduction of that Twin address is P itself, and nothing else**" holds inside `get`, which
  knows P. `normalise` alone cannot know it: a Twin address given directly
  (`get …/safety-for-agentic-ai.md`, a `citations.csv` row naming it) still reduces to
  `…/safety-for-agentic-ai/modelcard`, as before, because `docs.aws.amazon.com/` needs `.md` →
  `.html` and a rule says nothing about which form a host's citations use. Ask for the page.
- The first Store's Version under `…/safety-for-agentic-ai/modelcard` is not rewritten (Versions
  never are); the owner fetches `…/safety-for-agentic-ai` again to have it under that address.
