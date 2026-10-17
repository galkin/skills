# Each Version carries its own Provenance; the package description is generated

A Version is a Markdown file whose YAML frontmatter holds its Provenance — `url` (normalised, the page
a reader would open), `fetched_at`, `sha256` of the Markdown body, `publisher`, `authority`,
`converter` with its version (`trafilatura 2.3.1`), and `etag` / `last_modified` when the server
sent them; optionally `title`, `modified` (the publisher's own date),
`original {url, mediatype, sha256, stored}` (`stored` is a boolean; the Original's name follows
from the Version's; `original.url` is the address the bytes came from), `requested` (the
address asked for, when a redirect or a canonical link changed it) and `origin` (`web` or
`owner`).
The Store's `datapackage.json` (Frictionless Data Package) is generated from those files and never
edited by hand.

The main reader is an agent that has already opened the file, so Provenance belongs where it is
read; this is how FineWeb and Dolma keep theirs, beside the text. Frictionless was chosen for the
package because what the Store holds beyond pages is tables, and because WACZ uses the same format.

Two hashes have two jobs. `sha256` of the Markdown is the Version's identity and name.
`original.sha256` is always the hash of the bytes received, and it is the first word on whether the
page *changed upstream*: equal bytes mean nothing changed and nothing is converted. Different bytes
are not yet a change — the raw HTML of Microsoft Learn, AWS and most CDNs carries per-request ids,
nonces and build hashes — so the page is converted again and the new Markdown compared with the
Version's; only when both differ is a new Version stored. Comparing Markdown alone was rejected
because a new release of a Converter rewrites every Markdown without any page having changed; the
Original comparison catches that case, the Markdown comparison catches the noise, and the rare
page that is both noisy and converted by a newer release is one false Version, not a Store of them.
For a Twin the Original is not stored (`original.stored: false`): the Markdown is the received
text minus the publisher's own frontmatter, and `original.sha256` still hashes what was received.

A Source the owner provides rather than fetches (research pasted from a chat) has no address: its
`url` is `owner:<slug>` and `origin: owner`, so one naming rule serves every Version.

Nothing that grows over time is in the frontmatter: which Tags a Source carries (ADR 0008) and when
it was rechecked (ADR 0007) live in append-only files beside it, because a Version is written once.

## Considered Options

- **RO-Crate (+ BagIt).** Rejected: its strength is lineage from inputs to outputs, which the
  consuming project already states in its own references and the Index derives; BagIt's fixity is
  covered by `hash` and `bytes` on each resource.
- **A separate `id` field.** Rejected: a normalised `url` already names the Source, and `url` +
  `sha256` names a Version.
- **Licence per file or per package.** Rejected by the owner: recording licences is not this tool's
  job and agents handle the field badly. Third-party Sources are kept like any other.
