# 03: `lorekeep rules propose` — a model proposes, the tool measures, the owner accepts

**What to build:** `lorekeep rules propose PREFIX [--sample N] [--accept] [--store DIR]`: a sample of the Versions under the prefix goes to the model with the rule grammar (`Edges.proposer`, Anthropic API `claude-haiku-4-5-20251001`, `ANTHROPIC_API_KEY`, the `anthropic` SDK as the extra `lorekeep[rules]`); each candidate rule is applied to every Version under the prefix and reported (lines removed or headings inserted: total, min/median/max per Version, three examples; pass/fail against the limits: at most 30% of a Version's lines, no fence or table line, `drop_leading` only before the first heading); `--accept` appends the passing rules to the Store's `lorekeep.toml` with `accepted` and `removes` and rebuilds the Readings under the prefix. `get` and `search` never call the model. The first Store's rules and the engine defaults in `readings.toml` come from running it live. Decisions: `spec.md` › `rules propose`.

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] with a fake proposer returning a recorded candidate set (fixture: the TOML the model returned for `docs.nvidia.com/` on the first run), `rules propose docs.nvidia.com/` over three Fern Twin fixtures prints each candidate with its measurements and `pass`/`fail`, writes nothing
- [ ] a candidate that removes 40% of one Version, or a fence line, or a leading block after the first heading, is `fail` with the reason; `--accept` writes only the passing ones, with `accepted` today and `removes` the measured share, and `lorekeep read` has then built the Readings under the prefix
- [ ] without the extra, `rules propose` exits 2 naming `lorekeep[rules]`; without the key, exits 2 naming `ANTHROPIC_API_KEY`; `get` and `search` import nothing from the SDK
- [ ] run live by the implementer with the owner's key on the first Store for `docs.nvidia.com/`, `eur-lex.europa.eu/`, `learn.microsoft.com/` and `docs.nvidia.com/rag/latest/`: the ticket Comment records every candidate, its measurements and the verdict; the accepted engine-level rules (Fern banner, EUR-Lex articles, Microsoft Learn suffix) go into `src/lorekeep/readings.toml` with a test each; the Store's `lorekeep.toml` holds the rest
- [ ] `references/owner.md` documents `rules propose`, the `[[readings]]` keys with one example, the limits and the cycle (friction → propose → accept); `README.md` › Install names `lorekeep[rules]`; the flag test passes
