# 02: `url` is where the page was served, never its canonical link

**What to build:** A `<link rel="canonical">` or a Twin's `canonicalUrl` no longer decides `url`: the final address after redirects (Twin-reduced, normalised) does. A canonical that differs is recorded as frontmatter `canonical` with one warning, and nothing in `aliases.csv` points at it. `get --json` and `add --json` carry `requested_url`. The unknown-host warning names the final host only and tells the Run to report, not to edit `lorekeep.toml`. Decisions: `spec.md` › URL identity. Amend ADR 0003's canonical sentence and the v1 spec's "URL normalisation" bullet, saying why (the OWASP case).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `get https://genai.owasp.org/llmrisk/llm062025-excessive-agency/` (fixture cut from the Store's Original: the page declares canonical `…/llm06-sensitive-information-disclosure`) stores `url: https://genai.owasp.org/llmrisk/llm062025-excessive-agency`, `canonical: https://genai.owasp.org/llmrisk/llm06-sensitive-information-disclosure`, prints one `lorekeep: warning: … declares another page as canonical …` line, and writes no `aliases.csv` row; a later `get` of the canonical address fetches that page as its own Source
- [x] `get https://docs.nvidia.com/nemo/retriever/latest/…` whose canonical names `26.8.1` stores `url` with `latest` and `canonical` with `26.8.1`; a Recheck asks `original.url` (the `latest` address)
- [x] the Microsoft Learn redirect chain (`ms-foundry.redirect-1/-2/.twin`) still stores the page URL (Twin-reduced final address) and the requested address as an alias, with no `canonical` field because the Twin's `canonicalUrl` equals `url` after normalisation
- [x] `get --json` prints `requested_url` (the normalised address asked); `add --json` prints it equal to `url`; `SKILL.md`'s JSON example shows it
- [x] `get https://v3.helm.sh/docs/helm/helm_rollback/` (fixture: `301` to `helm.sh`) prints one warning naming `helm.sh` only, worded `lorekeep: warning: helm.sh is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule`; the Index's `unknown_hosts` is unchanged
- [x] the `canonical` column exists in the Index's `versions` table and the data package's `sources` rows do not change

## Comments

**2026-10-17 (implementation).**

- `Fetched` carries `canonical` beside `final_url`; no step lets it decide `final_url` any more.
  `urls.other_canonical` normalises it and keeps it only when it differs from `url`; `get` warns
  `lorekeep: warning: <url> declares another page as canonical (<canonical>); stored under the
  address it was served at`. A Recheck that stores a new Version records `canonical` the same way,
  without a warning.
- The unknown-host warning is printed once, for the host of the Version `get` returns (the stored
  one, or the fetched one's final host). A `get` that stores nothing prints only its error line.
- `requested_url` sits right after `url` in the JSON; `add` passes none and it equals `url`.
- The Index's `versions` gains `canonical`. Because `CREATE TABLE IF NOT EXISTS` keeps an older
  table, `meta` now records `schema = 2`: an Index without it reads as stale, the rebuild drops and
  recreates the tables, and a commit's notification leaves an older Index alone. Ticket 04's
  `heading_line` should bump `SCHEMA_VERSION` again.
- The termidy `.alias` tests were inverted: `…/index.html` is now its own Source with `canonical`
  naming the lesson, not an alias of it.

**Where the ticket was wrong.**

- **helm:** `v3.helm.sh` does not redirect. Measured with `curl` on 2026-10-17 it answers `200`
  with the same page and `<link rel=canonical href=https://helm.sh/…>`. v1 stored it under
  `helm.sh` through that canonical, and the report took that for a redirect. Both are recorded:
  `helm-rollback.v3` (live `200`) stores `url` on `v3.helm.sh`, `canonical` on `helm.sh`, and warns
  about `v3.helm.sh`; a synthesised `helm-rollback.v3-redirect` (`301` to `helm.sh`) checks the
  rule the ticket meant, that a warning names the final host only.
- **OWASP:** the canonical address `…/llm06-sensitive-information-disclosure/` answers `301` to
  the Excessive Agency page on the live host. So a later `get` of it does fetch it on its own (the
  Store never answers it from the `canonical` field), but the redirect makes it an alias of the
  Excessive Agency Version. The test records that. The "its own Source" case is tested with
  `helm.sh` after `v3.helm.sh` and with the termidy lesson after its `index.html`.
- **ADR 0003** had no canonical sentence. The rule and the OWASP and NVIDIA cases are added there
  as a paragraph, and the sentence that did say it, in ADR 0001 (canonical links as aliases), is
  amended.

**Not done.** `SKILL.md` still says "a redirect or a canonical URL stores the page under its final
address" and its rule 4 tells a Run to add a rule to `lorekeep.toml`. `references/store.md` still
describes `url` as possibly the canonical URL. Only the JSON example was in scope here. Ticket 05
rewrites those files.
