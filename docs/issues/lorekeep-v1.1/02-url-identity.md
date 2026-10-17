# 02: `url` is where the page was served, never its canonical link

**What to build:** A `<link rel="canonical">` or a Twin's `canonicalUrl` no longer decides `url`: the final address after redirects (Twin-reduced, normalised) does. A canonical that differs is recorded as frontmatter `canonical` with one warning, and nothing in `aliases.csv` points at it. `get --json` and `add --json` carry `requested_url`. The unknown-host warning names the final host only and tells the Run to report, not to edit `lorekeep.toml`. Decisions: `spec.md` › URL identity. Amend ADR 0003's canonical sentence and the v1 spec's "URL normalisation" bullet, saying why (the OWASP case).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `get https://genai.owasp.org/llmrisk/llm062025-excessive-agency/` (fixture cut from the Store's Original: the page declares canonical `…/llm06-sensitive-information-disclosure`) stores `url: https://genai.owasp.org/llmrisk/llm062025-excessive-agency`, `canonical: https://genai.owasp.org/llmrisk/llm06-sensitive-information-disclosure`, prints one `lorekeep: warning: … declares another page as canonical …` line, and writes no `aliases.csv` row; a later `get` of the canonical address fetches that page as its own Source
- [ ] `get https://docs.nvidia.com/nemo/retriever/latest/…` whose canonical names `26.8.1` stores `url` with `latest` and `canonical` with `26.8.1`; a Recheck asks `original.url` (the `latest` address)
- [ ] the Microsoft Learn redirect chain (`ms-foundry.redirect-1/-2/.twin`) still stores the page URL (Twin-reduced final address) and the requested address as an alias, with no `canonical` field because the Twin's `canonicalUrl` equals `url` after normalisation
- [ ] `get --json` prints `requested_url` (the normalised address asked); `add --json` prints it equal to `url`; `SKILL.md`'s JSON example shows it
- [ ] `get https://v3.helm.sh/docs/helm/helm_rollback/` (fixture: `301` to `helm.sh`) prints one warning naming `helm.sh` only, worded `lorekeep: warning: helm.sh is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule`; the Index's `unknown_hosts` is unchanged
- [ ] the `canonical` column exists in the Index's `versions` table and the data package's `sources` rows do not change
