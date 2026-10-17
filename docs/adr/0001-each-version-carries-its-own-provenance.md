# Each Version carries its own Provenance; the package description is generated

A Version is a Markdown file whose YAML frontmatter holds its Provenance — `url` (normalised, the page
a reader would open), `fetched_at`, `sha256` of the Markdown body, `publisher`, `authority`,
`converter`, and `etag` / `last_modified` when the server sent them; optionally `title`, `modified`
(the publisher's own date), `original {url, mediatype, sha256, stored}`, `part_of` / `part`,
`extracted_from` and `origin` (`web` or `owner`). A file that is not Markdown gets the same fields in
a `<file>.meta.yml` sidecar. The Store's `datapackage.json` (Frictionless Data Package) is generated
from those files and never edited by hand.

The main reader is an agent that has already opened the file, so Provenance belongs where it is
read; this is how FineWeb and Dolma keep theirs, beside the text. Frictionless was chosen for the
package because what the Store holds beyond pages is tables, and because WACZ uses the same format.

## Considered Options

- **RO-Crate (+ BagIt).** Rejected: its strength is lineage from inputs to outputs, which the
  consuming project already states in its own references and the Index derives; BagIt's fixity is
  covered by `hash` and `bytes` on each resource.
- **A separate `id` field.** Rejected: a normalised `url` already names the Source, and `url` +
  `sha256` names a Version.
- **Licence per file or per package.** Rejected by the owner: recording licences is not this tool's
  job and agents handle the field badly. Third-party Sources are kept like any other.
