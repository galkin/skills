# 07: `add` stores a Source the owner provides

**What to build:** `add <file> --title <t>` copies a Markdown or text file into the Store as a Version with `url: owner:<slug-of-title>`, `origin: owner`, `authority: generated` (or `--authority`), `publisher` from `--publisher` (default `owner`), `converter: owner`, `fetched_at` from the file's mtime or `--fetched-at`, and the Run's Tag. The file name is `owner--<slug>--<sha8>.md`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `add` of a text file creates `owner--<slug>--<sha8>.md` with the fields above and a `tags.csv` row
- [ ] `add` of the same content twice creates one file and prints the same path
- [ ] `--authority primary` and `--publisher claude` are honoured; `--fetched-at` overrides the mtime
- [ ] `add` without a Tag or without `--title` exits non-zero before writing
