# Reading the Store

A Reader searches the Store, opens the line it finds, and cites the Source it rests on; it `get`s
a page its brief names. [SKILL.md](../SKILL.md) holds the settings, the exit codes and what never
to do.

## `lorekeep search`

Need a fact: `lorekeep search '<words>'` first, and open the file at the `file:line` it prints.

Searches the Sections (the text under each heading) of the Latest Version of every Source in scope,
ranked by BM25; word forms match (`caching` finds `cached`). The scope is the Run's Tag, else the
whole Store; `--tag` (repeatable) sets it, `--all` searches every Tag. A plain query needs every
word in one Section, so use 2–4 content words in the page's own wording, never a question. When no
Section has them all, `search` prints the line
`lorekeep: note: no Section has every word; these have most of them` on stderr and ranks the
Sections holding most of the words but stopwords: a weaker answer, check it in the file.

```text
$ lorekeep search 'how do I set the perplexity threshold for jailbreak detection' --limit 1
lorekeep: note: no Section has every word; these have most of them
/…/store/.cache/readings/docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-jailbreak-protection--96543394.md:16 | Jailbreak Protection > Jailbreak Detection | …[jailbreak]_[detection]: server_endpoint: "http://0.0.0.0:1337/heuristics" length_per_[perplexity]_[threshold]: 89…
$ lorekeep search 'jailbreak perplexity threshold' --limit 1
/…/store/.cache/readings/docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-jailbreak-protection--96543394.md:16 | Jailbreak Protection > Jailbreak Detection | …[jailbreak]_detection: server_endpoint: "http://0.0.0.0:1337/heuristics" length_per_[perplexity]_[threshold]: 89…
```

`--exact` matches a case-sensitive substring of the text as written, for identifiers
(`cache_control`); `\_` and `\*` in the text match `_` and `*`. `search` takes `-- '<query>'` for
a query starting with `-`; flags may stand before or after it:
`lorekeep search --exact -- '--enable-auto-tool-choice'`.

Text output: one line per result, `file:line | heading path | snippet`, matched words in
`[brackets]`. `file:line` is the matching line: open the file there. `(top)` is text before the
first heading. No result prints `no matches` and exits `0`. A last line
`+N matches under other tags (--all)` means other guides' Sources answer too; widen with `--all`
or `--tag`.

```text
$ lorekeep search --exact length_per_perplexity_threshold --limit 1
/…/store/.cache/readings/docs.nvidia.com--nemo-guardrails-latest-configure-guardrails-guardrail-catalog-jailbreak-protection--96543394.md:39 | Jailbreak Protection > Jailbreak Detection | …server_endpoint: "http://0.0.0.0:1337/heuristics" [length_per_perplexity_threshold]: 89.79 prefix_suffix_perplexity_threshold: 1845.65 ``…
$ lorekeep search jailbreak --tag anthropic
no matches
+2 matches under other tags (--all)
```

A PDF Version (`markitdown …`) may run words together and keep ligatures (`proﬁle`, which
`search`, exact or not, reads as letters); it or a long page with no headings (`get` warns) is one
Section to `search`: read it rather than trusting it to find a phrase in it.

## `lorekeep get`

Need a page: `lorekeep get --json <url>`, then read the file at `path`. When the JSON has
`version`, `path` is a **Reading**: the Version with the publisher's banner and chrome dropped by
the Project's rules, every other line verbatim; `version` is the evidence, `url` the citation.
Text output, without `--json`: the path of the Reading, else the Version. `--fresh` asks the
publisher now (`--max-age 0`); only when a fact is in dispute.

`--json`, for a host no rule knows:

```text
$ lorekeep get --json https://helm.sh/docs/helm/helm_rollback/#synopsis
lorekeep: warning: helm.sh is in no host table; stored as third-party — tell the owner, who may add a [[hosts]] rule
lorekeep: note: https://helm.sh/docs/helm/helm_rollback is third-party under no rule
```

```json
{"path": "/…/store/helm.sh--docs-helm-helm_rollback--baae9b0a.md", "url": "https://helm.sh/docs/helm/helm_rollback", "asked": "https://helm.sh/docs/helm/helm_rollback/#synopsis", "requested_url": "https://helm.sh/docs/helm/helm_rollback", "sha256": "baae9b0a65857f5fcd96600fca791315f7e83a745368d32d1885fec8891e1312", "fetched_at": "2026-10-17T17:35:54Z", "converter": "trafilatura 2.3.1", "publisher": "helm.sh", "authority": "third-party", "verified_at": "2026-10-17T17:35:54Z", "outcome": "stored"}
```

## What to cite

Cite the Version's `url` as far as its `authority` allows:

- The returned `url` may differ from the address you asked (trailing slash, fragment, redirect,
  Twin reduction); it is the one to cite.
- `requested_url` in the JSON is the address you asked, normalised; compare it with `url`.
- Fragments (`#section`) are dropped from both and kept in `asked`: append the fragment to `url`
  when you cite a section.
- `authority`: `primary` and `official` are cited; `third-party` is context; `generated` (research
  the owner added) is never cited.
- A law or standard is `primary` on its official journal (EUR-Lex, the Federal Register, nist.gov
  for NIST) and `official` in an institution's reproduction (the AI Act Service Desk); cite the
  journal, and report a Version whose `authority` says otherwise.
- A `third-party` verdict from no rule or a whole-host rule prints a note on every `get`
  (`lorekeep: note: <url> is third-party under the github.com/ rule`, or `under no rule`); a page
  the guide treats as primary (a vendor's repository; report when unsure) is reported to the owner,
  who may add a host rule; until then it is context — the next `get` shows the new authority.

## stderr lines and what to do

| Line contains                                       | Do                                                           |
| --------------------------------------------------- | ------------------------------------------------------------ |
| `<host> is in no host table; stored as third-party` | report the host to the owner; the page is context            |
| `declares another page as canonical`                | nothing; cite `url`                                          |
| `N code blocks / M tables of the page are missing`  | report; compare with the Original; distrust nearby headings  |
| `the Markdown holds N% of the page's main text`     | report; compare with the Original                            |
| `is third-party under the <prefix> rule`            | report it if the guide treats the page as primary            |
| `returning the stored Version`                      | use it; the publisher could not be asked or dropped the page |
| `the Index was missing or stale and was rebuilt`    | nothing                                                      |
| `rule <name> removed N … (accepted at M …)`         | report; the Reading kept what that rule would have dropped   |

A Version's warnings print on every `get` that returns it (`fresh` and `unchanged` too); one
stored by an older lorekeep has none recorded.

On exit `1` nothing was stored. Retry once, only when the error line names `ReadTimeout`,
`ConnectError` or a `5xx` status (`answered 503`); otherwise, or when the retry fails too, report
the URL and the error line to the owner and move on.
