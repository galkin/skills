# 04: a Twin that says "Page Not Found" is not a Version

**What to build:** A Twin answered with `200` whose body is a not-found page is a soft 404 and must not be stored. Found live on 2026-10-17 on a copy of the first Store: `get …/latest/about-nemo-guardrails/library/rail-types` (a mistyped address — see the Comment; the ticket first blamed a move by NVIDIA) read the Twin `…/rail-types.md`, which Fern serves as `text/markdown`, status `200`, body `# Page Not Found\n\nThis page does not exist.\n\n## Similar pages\n- […]`; lorekeep stored it as a new Version (24 lines, `converter: md-twin`) with `outcome: fresh`, so a Run reads a 404 and a Recheck replaces a good Version with it. The cascade's Twin step treats such an answer as a Fallthrough with the reason `the Twin answered 200 with a not-found page`, and the cascade goes on to the page itself (which answers a real 404 or redirects to the new address, as today); `recheck` of a stored Version whose Twin now answers so records the check as failed and keeps the Version. What counts as a not-found page: the first heading of the Twin is `Page Not Found` or `404` (case-insensitive) and the body is under 40 lines — the implementer pins the marker on the Fern fixture and writes it in `cascade/twin.py`'s docstring. Decisions: v1.2 `spec.md` › Converters (the tool never edits a Version, but it never stores a page that is not the page asked either).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] fixture `guardrails-rail-types.notfound.twin` (the body cut from that Version): `get` under the `docs.nvidia.com/` Twin rule does not store it; stderr names the Twin's reason; the cascade asks the page next and the fixture's page answers `404`, so `get` exits `1` with `nothing stored`
- [x] the same page fixture answering `301` to the new address, whose Twin is the real page: `get` stores the Version under the new address, `outcome: fresh`
- [x] `recheck` of a Version whose Twin now answers the not-found page records `outcome: failed` with the reason and leaves the Version the Latest
- [x] `references/store.md` › Twins says a Twin's not-found page is never a Version; `SKILL.md` unchanged unless a sentence became false

## Comments

**2026-10-17** — done on `galkin/lorekeep-v13-04`; tests in `tests/test_get_twin_not_found.py`,
one per criterion, each naming its fixtures, under the default `docs.nvidia.com/nemo/guardrails/`
rule, plus one parametrised test of the marker. New fixtures: `guardrails-rail-types.notfound.twin`,
the first Store's Version `…-rail-types--93f114ec.md` body byte for byte (its `sha256` is the
Version's), served `text/plain` as that Version's `original.mediatype` records;
`guardrails-rail-types.notfound.404`, `.notfound.301`, `.moved.html` and `.moved.twin`,
synthesised (the last is the body of `guardrails-rail-types.twin` at the new address).

- **The marker** (`cascade/twin.py` › module docstring, `not_found`): after the publisher's
  frontmatter, the first `# ` heading outside a fence is `Page Not Found` or `404`, case-folded,
  and the Markdown has fewer than 40 lines. It sits in `TwinStep.reread`, after the media-type
  gate and before the `Same` comparison, so `get` and a Recheck both see it, and a Version that
  already holds a not-found page (the first Store's `93f114ec`) rechecks as `error`, never
  `unchanged`. The reason is `no Twin: <twin address> answered 200 with a not-found page`, in the
  form of the step's other reasons. `github-raw` files are exempt: raw GitHub answers real `404`s
  and a repository's `# 404` page is a file.
- **A page that moved is read from its new Twin** (`cascade/__init__.py` › `redirected_twin`,
  the coordinator's choice): when the page step was redirected to an address whose rule names an
  `md-suffix` or `accept-header` Twin not asked yet, that Twin is asked once and taken over the
  HTML already fetched; if it declines, the HTML is converted as before. `cascade.Request` gained
  `rules` (the host table) so the new address gets its own rule; `get` passes it. The order is in
  the `cascade` docstring and `references/store.md` › Twins.
- **`recheck`** needed no change of its own: a `Fallthrough` from `reread` was already `error`
  with status `200` and the reason on stderr, the Version kept.
- `references/store.md` › Twins: a Twin's not-found page is never a Version; the cascade's order
  with the redirected Twin. `SKILL.md` is unchanged (its order sentence is still true).

Where the ticket was wrong or loose:

- "**Fern serves as `text/markdown`**": the first Store's Version records `original.mediatype:
  text/plain`, so the fixture serves that; the marker does not depend on the type.
- "**`outcome: fresh`**" for the moved page: a first `get` that stores a Version says `stored`. The
  test asserts `stored` on the first `get` of the old address and `fresh` on the second, which
  reaches the Version through the alias.
- "**The cascade goes on to the page itself (… redirects to the new address, as today)**" and "the
  new address, **whose Twin is the real page**" could not both hold: as of v1.2 the page step
  converted the new page's HTML and never asked its Twin. Hence `redirected_twin`, and a fifth
  fixture, the new page's HTML, which the page step fetches before the Twin is asked (one request
  spent); a test pins the fallback to that HTML when the new Twin is missing.
- "**Records `outcome: failed`**": a Recheck has no `failed` result; it records `error` (status
  `200`, the Version's `sha256`), and the reason goes to stderr — `checks.csv` has no reason column.
- The live case was not quite the migration: the address asked was
  `…/latest/about-nemo-guardrails/library/rail-types` (a `/` for the `-` of
  `about-nemo-guardrails-library`), and the good Version under `…/latest/about-nemo-guardrails-library/…`
  was never replaced. The fixtures keep the address asked; the `301` to the new address is synthesised.
