# 06: a host rule inherits the Twin of the longest shorter prefix

**What to build:** A rule that omits `twin` and `page_suffix` inherits both from the longest shorter-prefix rule of either layer that has them (`github.com/NVIDIA/` with `publisher`/`authority` only gets `github-raw` from the default `github.com/`); a rule naming `twin` keeps its own; `browser` and `cut` are not inherited. `status --rules` marks inherited values `(inherited)`. Decisions: `spec.md` › Host rules inherit.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] a Store whose `lorekeep.toml` has `[[hosts]] prefix = "github.com/NVIDIA/"` with publisher and authority only: `get` of a `blob/` page under it stores `converter: raw-twin`, `publisher: nvidia`
- [x] a rule with the same prefix as a default and no `twin` inherits from the next shorter default prefix, not from the rule it replaces (`docs.langchain.com/` replaced without `twin` and no shorter rule → no Twin, as today)
- [x] `status --rules` prints `twin=github-raw (inherited)` for the rule above
- [x] the README's and `owner.md`'s paragraphs on repeating `twin` become one sentence on inheritance; the four explicit GitHub rules in the first Store's `lorekeep.toml` still work unchanged

## Comments

**2026-10-17** — done on `galkin/lorekeep-v12-06`; tests in `tests/test_host_inheritance.py`,
fixtures `tests/fixtures/github-readme.raw` (served under a `github.com/NVIDIA/` address for the
first criterion, as `test_get_twin_kinds.py` re-points fixtures) and
`tests/fixtures/langchain-sql-agent.html`; no new fixture.

- Built in `project.py`: `merge_rules` ends with `inherit`, so inheritance runs over the merged
  two-layer table and a rule replacing a default never sees the rule it replaced. `HostRule`
  gains `inherited`; `status --rules` appends ` (inherited)` to each inherited `twin=` and
  `page_suffix=`. `normalise`, the Twin step and Recheck read the resolved rule, so nothing else
  changed.
- **"The rule of either layer that has them" is read as "that names a `twin`".** A rule naming
  only `page_suffix` neither inherits nor gives (`page_suffix` means nothing without `md-suffix`);
  the donor's `page_suffix` comes with its `twin`, absent or not. Taking only explicit donors gives
  the same result as chaining through an inherited one.
- **The third criterion's "rule above" is the first criterion's `github.com/NVIDIA/` rule**; the
  second criterion's rule has no Twin to print.
- **The task brief's "see hosts.py" names no file**: the merged table is built in `project.py`
  (`hosts.toml` is the default table).
- The four explicit GitHub rules of the first Store's `lorekeep.toml` were not read (the brief
  allows reading the Store's Originals only); the test pins a rule of their shape, the
  `github.com/NVIDIA-AI-Blueprints/` example `owner.md` used to show, as still storing `raw-twin`
  with its own publisher and no `(inherited)` mark.
- `README.md`'s `lorekeep.toml` example now says `twin` absent means inherited, and the paragraph
  under the default table and `owner.md`'s paragraph (with its TOML example) are one sentence on
  inheritance each; `SKILL.md` said nothing about it and is unchanged.
