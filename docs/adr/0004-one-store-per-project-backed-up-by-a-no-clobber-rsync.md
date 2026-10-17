# One Store per Project, outside any repository, backed up by a no-clobber rsync

Each Project has one Store, a plain folder such as `~/orca/sources/agentic-system.design/`, shared by
all of its Runs; the tool finds it through `LOREKEEP_STORE`, and the Project's configuration
(`lorekeep.toml`: bucket, host table, freshness window) sits in the Store's root so it is backed up
with the data. Its off-machine copy is a private, versioned GCS bucket.

The backup is two `gcloud storage` passes — an `rsync` and a `cp` — because the Store has two kinds
of file. Versions
and Originals are written once, so they go with `--no-clobber`: an object already in the bucket is
never replaced, and a local deletion never reaches it because
`--delete-unmatched-destination-objects` is not given. The few files that grow — `tags.csv`,
`checks.csv`, `citations.csv`, `datapackage.json`, `lorekeep.toml` — are copied plainly, and the
bucket's own versioning keeps their history. `sources.db` with its `-wal` / `-shm` companions, the
lock file and any `.tmp-*` a worker is still writing are excluded; the Index is rebuilt, not
restored.

`backup` is its own command, run by the pipeline at the end of a unit or on a timer — not after
every `get`: six workers each listing a bucket of thousands of objects after every page would slow
a Run for nothing.

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
