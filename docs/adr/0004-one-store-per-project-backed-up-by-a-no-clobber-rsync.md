# One Store per Project, outside any repository, backed up by a no-clobber rsync

Each Project has one Store, a plain folder such as `~/orca/sources/agentic-system.design/`, shared by
all of its Runs; the tool finds it through `SOURCES_ROOT`. Its off-machine copy is a private,
versioned GCS bucket, filled by
`gcloud storage rsync <store> gs://<bucket> --recursive --no-clobber --exclude='^sources\.db$'` after
every command that wrote to the Store. Without `--delete-unmatched-destination-objects` a local
deletion never reaches the bucket, and `--no-clobber` never replaces an object that is already
there, which is the Store's own rule.

Sources are rarely shared between Projects — between vendors of one Project only four file names
matched — so a Store per Project costs almost nothing and keeps each Project's material and backup
inside its own boundary. A per-Run cache was the previous practice and lost everything a later Run
of the same guide could have reused.

## Considered Options

- **One Store for all Projects.** Rejected: nearly nothing to share, and a backup would cross
  Project boundaries.
- **A git repository or DataLad dataset from day one.** Deferred, not rejected: the folder's rules
  make either a later wrap.
- **`rclone`.** Rejected for now: not installed, and `gcloud` already is; it stays the fallback for
  a non-GCS backup.
