# 10: `backup`, `restore` and the data package

**What to build:** `backup` regenerates `datapackage.json` under the Store lock (a resource for each CSV that exists, with a typed schema, and a `sources` resource with inline `data`: one flat row per Version, `url, file, sha256, bytes, fetched_at, publisher, authority, converter`), then runs through the command runner: one `gcloud storage rsync --recursive --no-clobber` of the Store excluding the six growing files, the Index with its journals, `.lorekeep.lock` and `.tmp-*` files, and one `gcloud storage cp` of the growing files that exist (`tags.csv`, `checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`, `lorekeep.toml`); `--dry-run` goes to `rsync` only (`gcloud storage cp` has no such flag): in dry-run the `cp` is not run and its file list is printed; nothing deletes. `restore <name> [--generation N]` copies one object from the bucket and refuses to overwrite a local file.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `backup` on a Store with Versions, `tags.csv` and no `citations.csv` writes a `datapackage.json` that `frictionless validate` accepts, with one row per Version in `sources` and no resource for the absent CSV
- [ ] the runner fake records exactly two commands: an rsync with `--no-clobber`, without `--delete-unmatched-destination-objects`, whose exclude pattern matches `tags.csv`, `checks.csv`, `aliases.csv`, `citations.csv`, `datapackage.json`, `lorekeep.toml`, `sources.db`, `sources.db-wal`, `sources.db-shm`, `.lorekeep.lock` and `x.md.tmp-123` and does not match a Version or an Original; and a `cp` of the growing files that exist
- [ ] `--dry-run` adds the flag to the rsync, runs no `cp`, prints the files the `cp` would copy, and still regenerates the package
- [ ] the package's schema for `checks.csv` types `status` as a string
- [ ] `backup` without a `bucket` in `lorekeep.toml` exits non-zero with a message
- [ ] `restore <name>` runs one `cp` from the bucket; with `--generation N` the object path carries `#N` (Google's documented form; the smoke script in ticket 13 exercises it live); an existing local file makes it exit non-zero without running anything
