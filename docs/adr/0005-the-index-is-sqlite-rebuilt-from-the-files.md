# The Index is SQLite, rebuilt from the files, with one full-text table over Sections

`sources.db` sits in the Store and is derived from it entirely: it can be deleted and rebuilt at any
time and is not backed up. It holds every Version's Provenance, every Tag, every Recheck, every
Citation, and one FTS5 table (`porter unicode61`) over Sections — the text under each heading, with
its heading path and the line its heading sits on in the file, cut again at about 4 KB so a page
without headings still yields Sections — answered with `bm25` ranking and `snippet()`. An exact
identifier (`--exact`) is a substring match over the Sections' text rather than an FTS query,
because the tokenizer splits `cache_control` in two and "as written" has to mean that. Anything the Index reports that is not in a file is a
bug; so Tags are `tags.csv`, the log of Rechecks is `checks.csv`, and Citations are a
`citations.csv` (`work_id, url`) that the consuming Project generates from its own documents —
lorekeep never parses a Project's Markdown, which keeps the tool free of any one consumer's format.

A search is scoped to the Run's Tag by default and always ends with one line,
`+N matches under other tags (--all)`, so a page another Run fetched is never silently invisible;
`--all`, `--tag`, `--authority` and `--publisher` widen or narrow the scope.

Measured on one Run's cache of 1,403 pages (2026-10-17): 32,339 Sections, a 93 MB index built in
about 5 s; a question `grep` answered with roughly 210 KB of context, the Index answered with five
snippets of about 1.5 KB. The ranking is not semantic — the right Section came fourth — so queries
are cheap to refine, and `grep` stays for a file already known.

## Considered Options

- **A second FTS5 table with the `trigram` tokenizer** for exact identifiers. Rejected: it more than
  doubled the index (214 MB) for what `grep` already does.
- **Vector search** (sqlite-vec with local embeddings). Not now: the owner will ask for it when it is
  needed. When it is, measure it first on the Project's own Citations.
- **DuckDB.** Rejected: SQLite's CLI is on every machine and FTS5 is built in.
- **Parsing `## References` out of the Project's lessons inside lorekeep.** Rejected: it would bind a
  general tool to one consumer's file format.
