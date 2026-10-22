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

A withdrawn Source is out of every Run's view and nothing is written for it: its files stay, and
its `versions` rows stay in the Index so its address still resolves, but the Index holds no Section
of it, no Reading is built for it, no Recheck asks about it, and every command that would read it,
tag it or store a Version of it refuses or leaves it out. The skill's `references/store.md` ›
Withdrawals lists what each command does; this record keeps why.

The refusal is decided at the commit point, under the Store lock (ADR 0009): a commit whose
Version or rows name a withdrawn Source writes nothing and raises, so a `get` racing a `withdraw`
cannot slip a Version or a Tag in after it. The commands also check before they fetch, but only to
save a request; the commit's check is the one that holds.

**Undo** is a row too: `withdraw --undo URL --reason TEXT` appends `action` `undo`, and the last row
of a `url` decides. `--reason` is required both ways, so the file says why each change was made. A
row is appended only when it changes what holds — a second `withdraw` of a withdrawn Source, or an
`--undo` of one not withdrawn, writes nothing and says so (exit `0`, as `tag add` of a Tag a Source
already carries) — and that is decided under the lock too (`store.change_withdrawal`), so two
`withdraw` calls at once append one row.

A withdrawal leaves the Index stale instead of notifying it: withdrawing takes Sections out, and
undoing brings them back read from Readings that were not built while the Source was withdrawn, so
the next reader rebuilds the Index (and those Readings) under the lock as it does after any other
change it cannot follow. Withdrawals are rare and the owner's; the rebuild they cost is the price
of one code path for Sections.

`withdraw` is a Curator's command, like `tag add`, and in no Run's brief: deciding that a page is a
mistake is a judgement about the Project, which the owner makes, so the rule that a Run writes only
through `get` and `add` stays true.

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
