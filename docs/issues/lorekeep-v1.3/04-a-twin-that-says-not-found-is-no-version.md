# 04: a Twin that says "Page Not Found" is not a Version

**What to build:** A Twin answered with `200` whose body is a not-found page is a soft 404 and must not be stored. Found live on 2026-10-17 on a copy of the first Store: NVIDIA moved the NeMo Guardrails pages from `docs.nvidia.com/nemo/guardrails/latest/…` to `docs.nvidia.com/nemo/guardrails/…`, and `get …/latest/about-nemo-guardrails/library/rail-types` read the Twin `…/rail-types.md`, which Fern serves as `text/markdown`, status `200`, body `# Page Not Found\n\nThis page does not exist.\n\n## Similar pages\n- […]`; lorekeep stored it as a new Version (24 lines, `converter: md-twin`) with `outcome: fresh`, so a Run reads a 404 and a Recheck replaces a good Version with it. The cascade's Twin step treats such an answer as a Fallthrough with the reason `the Twin answered 200 with a not-found page`, and the cascade goes on to the page itself (which answers a real 404 or redirects to the new address, as today); `recheck` of a stored Version whose Twin now answers so records the check as failed and keeps the Version. What counts as a not-found page: the first heading of the Twin is `Page Not Found` or `404` (case-insensitive) and the body is under 40 lines — the implementer pins the marker on the Fern fixture and writes it in `cascade/twin.py`'s docstring. Decisions: v1.2 `spec.md` › Converters (the tool never edits a Version, but it never stores a page that is not the page asked either).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] fixture `guardrails-rail-types.notfound.twin` (the body cut from that Version): `get` under the `docs.nvidia.com/` Twin rule does not store it; stderr names the Twin's reason; the cascade asks the page next and the fixture's page answers `404`, so `get` exits `1` with `nothing stored`
- [ ] the same page fixture answering `301` to the new address, whose Twin is the real page: `get` stores the Version under the new address, `outcome: fresh`
- [ ] `recheck` of a Version whose Twin now answers the not-found page records `outcome: failed` with the reason and leaves the Version the Latest
- [ ] `references/store.md` › Twins says a Twin's not-found page is never a Version; `SKILL.md` unchanged unless a sentence became false
