# 02: `get` tells a Run what the tool knows

**What to build:** `get --json`/`add --json` carry `asked` (the argument as given, fragment included); a Version stored with a missing-code/table or main-text-ratio warning records it in frontmatter `warnings` and `get` prints those warnings on every return of that Version; a `third-party` verdict from a catch-all rule or from no rule prints a `lorekeep: note:` naming the rule; the thin check gains a ratio against the page's main element that warns (and stores) when the Markdown holds under a fifth of it, whatever its absolute size. Index `versions.warnings`, `SCHEMA_VERSION` bump. Decisions: `spec.md` › What `get` tells a Run.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `get --json 'https://docs.langchain.com/oss/python/langchain/middleware/built-in#model-fallback'` prints `asked` with the fragment, `requested_url` and `url` without it
- [ ] the Mintlify fixture that prints `1 code blocks / 0 tables … missing` on its first `get` prints the same warning on a second `get` (`outcome: fresh`) and its frontmatter has `warnings: ["1 code blocks / 0 tables of the page are missing from the Markdown"]`
- [ ] `get` of a `github.com/someone/repo` page under the default catch-all prints `lorekeep: note: <url> is third-party under the github.com/ rule`; a page under no rule prints `… under no rule` beside the unknown-host warning; a page under `github.com/NVIDIA/` prints neither
- [ ] the Model-Optimizer `guides/1_quantization.html` fixture (toctree list dropped, 1331 bytes of Markdown) stores with `lorekeep: warning: <url>: the Markdown holds N% of the page's main text` for N under 20; the kubernetes.io Deployment fixture prints no such warning
- [ ] an Index built by v1.1 is rebuilt by the next reader; `search --json` is unchanged
- [ ] `references/store.md` documents `asked` and `warnings`; the flag test passes
