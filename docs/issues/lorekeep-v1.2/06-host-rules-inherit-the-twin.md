# 06: a host rule inherits the Twin of the longest shorter prefix

**What to build:** A rule that omits `twin` and `page_suffix` inherits both from the longest shorter-prefix rule of either layer that has them (`github.com/NVIDIA/` with `publisher`/`authority` only gets `github-raw` from the default `github.com/`); a rule naming `twin` keeps its own; `browser` and `cut` are not inherited. `status --rules` marks inherited values `(inherited)`. Decisions: `spec.md` › Host rules inherit.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] a Store whose `lorekeep.toml` has `[[hosts]] prefix = "github.com/NVIDIA/"` with publisher and authority only: `get` of a `blob/` page under it stores `converter: raw-twin`, `publisher: nvidia`
- [ ] a rule with the same prefix as a default and no `twin` inherits from the next shorter default prefix, not from the rule it replaces (`docs.langchain.com/` replaced without `twin` and no shorter rule → no Twin, as today)
- [ ] `status --rules` prints `twin=github-raw (inherited)` for the rule above
- [ ] the README's and `owner.md`'s paragraphs on repeating `twin` become one sentence on inheritance; the four explicit GitHub rules in the first Store's `lorekeep.toml` still work unchanged
