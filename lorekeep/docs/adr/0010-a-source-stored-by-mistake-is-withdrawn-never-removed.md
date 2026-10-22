# A Source stored by mistake is withdrawn, never removed

A Collector looking for a specification's logo stored four pages under Tag `specifications` that
have nothing to do with it — `ans.dev` (a networking company, not Agent Name Service),
`www.okf.dev` (a parked domain), `www.visa.sk` (visa.com redirected to a regional home page) and
`agoraprotocol.org` (not Agora's content) — and nothing could take them back: no command removed a
Source, and the skill forbids editing the Store's files. So the owner, as Curator, withdraws one:
`lorekeep withdraw URL --reason TEXT` appends a row to a new growing file, `withdrawals.csv`
(`url,recorded_at,action,reason`), and no file is removed. The `url` resolves as `get` resolves it
(normalised, Twin-reduced, through `aliases.csv`), so the address a Run reported works, and the row
names the Source, so every Version of it is withdrawn.

A hard delete is ruled out by the Store's own rules. A Version or an Original is never rewritten or
removed (ADR 0002), and the backup is a no-clobber rsync that never deletes in the bucket (ADR
0004): a file removed here would stay there, and the Store and its backup would disagree without
anyone being told; a `restore` would even bring it back. Provenance is the tool's point, and a row
keeps readable what was stored, when, and why it was taken back. A withdrawal is reversible, and a
Citation that still names a withdrawn Source fails loudly instead of pointing at a missing file.

What a withdrawal does: the Source's files stay, its `versions` rows stay in the Index (so its
address still resolves), but the Index holds no Section of it, so `search` never finds it; `read`
and an Index rebuild build no Reading of it; `recheck` leaves it out of every scope; `status` counts
it on its own `Withdrawn:` line and leaves it out of every other count; `get` refuses it, exit `1`,
with the time and reason of the withdrawal — before fetching when the address is known, and
before storing when a new address redirects to it — and so does `add` of a withdrawn `owner:`
Source; `recheck --citations` names every work citing it as an error and exits `1`. `backup` copies
`withdrawals.csv` with the other growing files and `datapackage.json` describes it.

**Undo** is a row too: `withdraw --undo URL --reason TEXT` appends `action` `undo`, and the last row
of a `url` decides. `--reason` is required both ways, so the file says why each change was made. A
row is appended only when it changes what holds: a second `withdraw` of a withdrawn Source, or an
`--undo` of one not withdrawn, writes nothing and says so (exit `0`, as `tag add` of a Tag a Source
already carries). A withdrawal row has no key and is never de-duplicated by the commit point; the
command's own check is what keeps the file to real changes.

A commit of a withdrawal row leaves the Index stale instead of notifying it: withdrawing takes
Sections out, and undoing brings them back read from Readings that were not built while the Source
was withdrawn, so the next reader rebuilds the Index (and those Readings) under the lock as it does
after any other change it cannot follow. Withdrawals are rare and the owner's; the rebuild they cost
is the price of one code path for Sections.

`withdraw` is a Curator's command, like `tag add`, and is not in any Run's brief: a Run that finds
a page stored by mistake reports it to the owner with its `url` and why, and the rule "write to the
Store only through `get` and `add`" stays true for Runs.

## Considered Options

- **Delete the files.** Rejected for the reasons above: it breaks ADR 0002's immutability, leaves
  the bucket and the Store disagreeing silently (ADR 0004), and loses the record of the mistake.
- **A `withdrawn` field in the Version's frontmatter.** Rejected: it rewrites a Version (ADR 0002),
  and a withdrawal belongs to the Source, not to one of its Versions.
- **The three columns `url,withdrawn_at,reason` with undo as a second file or an empty reason.**
  Rejected: a second file splits one history in two, and an empty reason as a signal is invisible
  to whoever reads the CSV. `action` says it in the row.
- **Filter withdrawn Sources only at query time, keeping their Sections in the Index.** Rejected:
  every query that joins Sections would need the filter, and one missed is a leak; with no Sections
  there is nothing to find.
