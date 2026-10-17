# 06: Acceptance of tickets 01–04

**What to build:** Nothing. Records the orchestrator's acceptance of the four v1.1 implementation branches merged into `main` (`76f4fef`, `7b9d56f`, `e57a9e0`, `eb56ce4`), and what the live re-check found.

**Blocked by:** 01, 02, 03, 04

**Status:** done

- [x] gate on the merged tree: `pytest` green (all tests), `ruff check`, `ruff format --check`, `pyright` 0 errors
- [x] merge conflicts resolved by hand: tickets 02 and 04 both introduced an Index `SCHEMA_VERSION`; one implementation kept (`_DROP` of every table, `_schema_of`), version bumped to `3` covering both `versions.canonical` and `sections.heading_line`; tickets 02 and 03 both extended `Fetched`/`Converted` (`canonical` and `warnings`): both kept
- [x] live re-check on a fresh Store with the first Store's `lorekeep.toml`: Fern Guardrails → `md-twin` with fences and tables (`--exact length_per_perplexity_threshold` hits line 60 inside the fence); LangChain → `md-twin` (21 pipe-table rows); GitHub `blob/` → `raw-twin` (one fence); OpenAPI JSON → `verbatim`; OWASP Excessive Agency → stored under its own `url`, `canonical` recorded with a warning; kubernetes.io Deployment → `title: Deployments`, headings present; every Version has a `title`

## Comments

2026-10-17 — Accepted. Two things learnt on the live re-check, for the owner and ticket 05:

1. **A Project rule does not inherit the default rule's Twin.** The first Store's `lorekeep.toml` had `docs.langchain.com/` and `github.com/` rules (publisher and authority only) that replaced the package defaults, and `github.com/NVIDIA/`-style rules with a longer prefix that won over the default `github.com/` rule — in every case the Twin was lost and the page went through Trafilatura. Fixed in that Store by adding `twin = "github-raw"` to each GitHub rule and dropping the two plain overrides. Decision for the spec (not built): a rule without `twin` under a longer prefix should inherit the `twin` and `page_suffix` of the longest shorter-prefix rule, so an owner can set `publisher`/`authority` for an organisation without re-declaring how the host serves Markdown; `SKILL.md`/`README.md` must say so, and ticket 05 should at least warn in `references/owner.md` until then.
2. **A Recheck cannot adopt a new Twin rule**: a Version stored through Trafilatura is reread through Trafilatura (v1 "known limitation"). After rules change, the pages must be fetched into a new Store or with a new Source; the trial Store is being discarded anyway.

Ticket 05 (the skill rewrite) is next and is dispatched through Orca orchestration, as the owner asked.
