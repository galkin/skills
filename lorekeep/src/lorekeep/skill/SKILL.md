---
name: lorekeep
description: >
  Use lorekeep to read, collect and keep the Sources a Run works from: vendor documentation,
  specifications, third-party pages, PDFs, files. Reading: `lorekeep search <words>` answers with
  `file:line` from the Project's Store, and `lorekeep get <url>` returns the path of a Markdown
  Version with its Provenance, to cite. Collecting: fetch the pages a guide or a section needs into
  the Store, log every one and report what failed. Curating: the owner's host and reading rules,
  Rechecks, Tags and backups. Use it instead of fetching a page yourself, whenever a brief names
  lorekeep, LOREKEEP_STORE or LOREKEEP_TAG.
---

# lorekeep

lorekeep keeps one **Store** per Project: a flat folder of Markdown **Versions** of **Sources**,
each with its Provenance in frontmatter. lorekeep fetches, converts, records and searches; it holds
no LLM. You decide what to read and cite.

| Your work                                                                                         | Read                                                                    |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Reader**: find a fact in the Store, open it, cite it; `get` a page your brief names              | [references/reading.md](references/reading.md)                          |
| **Collector**: fetch the Sources a guide or a section needs, log every `get`, report the failures | [references/reading.md](references/reading.md), then [references/collecting.md](references/collecting.md) |
| **Curator**, the owner: `recheck`, `tag add`, `withdraw`, `backup`, `restore`, `index`, `skill`, host rules — never a Run's to call | [references/curating.md](references/curating.md)                        |
| Any: the Store's files, a Version's frontmatter, every `--json` field                              | [references/store.md](references/store.md)                              |

## Before you start

- `lorekeep` below is `bin/lorekeep` in this skill's folder (vendored:
  `.agents/skills/lorekeep/bin/lorekeep`) or the one on your `PATH`; it needs only `uv`.
- `LOREKEEP_STORE` names the Store (or `--store DIR`); lorekeep never creates a missing one.
- `LOREKEEP_TAG` names the **Tag** (or `--tag TAG`), set by the brief or the Project's own docs,
  never chosen by you; `get` and `add` refuse to run without it.
- Every flag follows its subcommand: `lorekeep get --json URL`, never `lorekeep --json get URL`.
  `lorekeep <command> --help` lists a command's flags and their defaults.
- stdout carries only the result; stderr lines start `lorekeep: error:`, `warning:` or `note:`.
- Exit `0` is success, `1` a failure of the work (nothing could be fetched), `2` a usage error
  (no Store, no Tag, a bad flag): fix the command.
- Write to the Store only through `get` and `add`; never edit its files or `lorekeep.toml`. A page
  stored by mistake is reported to the owner, with its `url` and why; the owner withdraws it.
- Never fetch a page another way (`curl`, a web tool, a browser), and never `add` a page `get` could not store.
- Put everything this skill says to report in your final report to the owner, with its URL.
