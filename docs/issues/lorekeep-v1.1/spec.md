# lorekeep v1.1: what the first migration taught

## Problem Statement

Three Opus workers brought the 379 pages the NCP-AAI guide cites into the first Store through the
v1 skill (2026-10-17, `~/orca/sources/agentic-system.design`, Tag `nvidia`). Every `get` but two
exited 0. The content was worse than the exit codes said:

- **Code and tables vanished** on every page built with Fern (NeMo Guardrails, Dynamo, Curator,
  Retriever on `docs.nvidia.com`) and Mintlify (`docs.langchain.com`): 22 of 22 Fern pages with
  code lost it, 18 of 18 with tables; 37 of 125 pages in another batch had `<pre>` in the Original
  and no fence in the Markdown. Link-only lists and page headings vanished on `kubernetes.io`
  (14 of 18 pages have no heading at all). A guide that teaches config keys cannot be written
  from this. `--exact` on an identifier then finds nothing.
- **A canonical link was trusted blindly.** `genai.owasp.org/llmrisk/llm062025-excessive-agency/`
  declares `…/llm06-sensitive-information-disclosure` as canonical, so the 2025 Excessive Agency
  text is stored under the 2023 risk's `url`, which the skill tells a Run to cite. `nemo/retriever/
  latest/…` was stored as `…/26.8.1/…` through its canonical, so a Recheck asks 26.8.1 forever;
  `a2a-protocol.org/v1.0.0/specification/` became `/latest/specification`.
- **GitHub `blob/` pages** (45 + 19 of them) are stored as GitHub's page chrome: "Repository
  navigation", "Copy path", one line number per line (500 lines before the first `import`), code
  unfenced with indentation lost. The `raw.githubusercontent.com` rule exists and was never used.
- **Client-rendered pages** (`build.nvidia.com` model cards) were stored as a 233-byte menu with
  exit 0 and no warning; the browser never ran.
- **One converter crash** (`lxml.etree._Comment` inside Trafilatura) printed a 40-line traceback
  instead of a `lorekeep: error:` line. JSON (`openapi_schema_rag_server.json`) is "unsupported
  media type" with no next step.
- **Search** reports the Section's heading line as `file:line` while the skill says "open the file
  at that line" (off by 2–41 lines); `--exact` misses identifiers the converter wrote as
  `free\_gpu\_memory\_fraction`; a query starting with `-` is an argparse error; headings carry
  `[#](…#anchor)` permalinks; a broken inline fence swallows every later heading of a page;
  zero results print only `+0 matches under other tags (--all)`.
- **No Version has a `title`**, although every page had one.
- **The skill** did not say that the returned `url` may differ from the one asked, that fragments
  are dropped, that `.md` is a Twin only under a rule, that parallel `get`s are safe, what to do on
  a non-transient exit 1, that the Tag is per guide, or how `citations.csv` is read; the
  unknown-host warning tells a Run to edit `lorekeep.toml`, which the skill forbids; and the file is
  long enough to be cut off in one read.

Full worker reports: `scratchpad/migrate/report-{aa,ab,ac,citations}.md` of session `24eaba17`
(copied below the tickets as `reports/` when this folder is committed).

## Solution

Fix the tool, not the workers: prefer the publisher's Markdown wherever it exists (Fern and
Mintlify serve `.md` twins; GitHub serves raw files), keep code, tables, lists and headings when
HTML must be converted, stop trusting a canonical that names another page, send thin pages to
the browser, make every failure a `lorekeep: error:` line, point `search` at the matching line,
and rewrite the skill around what a Run actually does. The Store from the first migration is
discarded and rebuilt with v1.1; its Originals are the test material.

## User Stories

1. As a Run, I want a Fern or Mintlify page to arrive as the publisher's Markdown, so that code and tables are complete.
2. As a Run, I want a GitHub `blob/` URL to give me the raw file, fenced by its extension when it is code, so that I read the file and not GitHub's page.
3. As a Run, I want `url` to be the address the page was served at, so that a publisher's wrong canonical link cannot file one page under another.
4. As a Run, I want a page that converted to almost nothing to be fetched by the browser or reported, never stored as a menu.
5. As a Run, I want every failure on stderr as one `lorekeep: error:` line that says what to do next.
6. As a Run, I want `search` to print the line of the match, so that I open the file there.
7. As a Run, I want `--exact cache_control` to find the identifier however the converter escaped it.
8. As a Run, I want a `title` on every Version, so that I can tell files apart.
9. As a Run, I want the skill to tell me what `get` returns, what may differ from what I asked, and what to do when it fails.
10. As the owner, I want JSON, YAML and plain-text files stored verbatim, so that an OpenAPI schema is a Source.
11. As the owner, I want the warnings to name the final host only and to tell the Run to report, not to edit my settings.

## Implementation Decisions

These extend the v1 spec (`../lorekeep-v1/spec.md`); where they contradict it, v1.1 wins, and
the ADR that loses is amended by the ticket that changes the behaviour.

### Twins and verbatim files (ticket 01)

- Two new Twin kinds in the host table. `md-suffix` already covers Fern and Mintlify (both answer
  `<page>.md` with `text/markdown`; Fern's Dynamo answers `text/plain`): the media-type gate for
  `md-suffix` accepts `text/plain` too when the body does not start with `<`. `github-raw`: a
  `github.com/<owner>/<repo>/blob/<ref>/<path>` address is fetched from
  `raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>`; the reverse reduction maps the raw
  address back to the `blob` page, which is what is stored and cited. A raw file whose extension is
  not `.md`/`.markdown`/`.txt` is stored as one fenced block with the extension as the language
  (` ```yaml `), preceded by one heading `# <path>`; `converter: raw-twin`.
- The package default table gains: `docs.langchain.com/` (langchain, primary, md-suffix),
  `github.com/` (github, third-party, github-raw); and the `docs.nvidia.com/` rule becomes
  `md-suffix` with `page_suffix = ".html"` for the Sphinx sections — but Sphinx sections do not
  serve `.md`, so a `404` on the Twin falls through to the page as today; measure with the live
  hosts which `docs.nvidia.com` sections answer `.md` and give those their own, longer prefixes
  (`docs.nvidia.com/nemo/guardrails/`, `/dynamo/`, `/nemo/curator/`, `/nemo/retriever/`,
  `/nemo/agent-toolkit/` are known Fern or Sphinx; the ticket says which).
- The page step gains a verbatim converter for `application/json`, `application/yaml`,
  `text/yaml`, `text/plain`, `text/csv` and `application/xml`/`text/xml`: the bytes decoded as
  UTF-8 inside one fence, `converter: verbatim`, title from the last path segment.

### URL identity (ticket 02)

- `url` is the final address after HTTP redirects (and meta-refresh), Twin-reduced and
  normalised. A `<link rel="canonical">` or a Twin's `canonicalUrl` is **never** the `url`. It is
  recorded in the frontmatter as `canonical` when it differs from `url` after normalisation, with
  one stderr warning naming both; nothing is written to `aliases.csv` for it. ADR 0003 and the v1
  spec's "URL normalisation" bullet are amended. A page that redirects keeps today's behaviour:
  the requested address becomes an alias of the final one.
- `get --json` and `add --json` gain `requested_url` (the normalised address asked) so a caller
  sees when `url` differs; the text mode is unchanged.
- The unknown-host warning names the final host only (one warning per `get`) and reads
  `lorekeep: warning: <host> is in no host table; stored as third-party — tell the owner, who may
  add a [[hosts]] rule`.
- A Version whose `publisher` came from a catch-all rule is no different from any other; the
  skill, not the tool, tells a Run to report a `third-party` page its guide treats as primary.

### HTML extraction (ticket 03)

- Before Trafilatura: comments are removed (`remove_comments=True`); permalink anchors are
  dropped (`a.headerlink`, `a.anchor`, and any `<a>` inside `h1`–`h6` whose text is `#`, `¶`, `🔗`
  or empty); every `<pre>` is flattened to its text content inside one `<pre><code>` so nested
  `<div>`/`<span>` syntax-highlighting structure cannot hide it; a `<table>` keeps its rows.
- After Trafilatura: the Markdown is checked against the tree: when the Original has `<pre>` or
  `<table>` and the Markdown has no fence or no pipe table, extraction is retried with the
  document's `<main>`/`<article>`/`role=main` subtree handed to Trafilatura with `favor_recall`;
  when it still lacks them, a warning `lorekeep: warning: <url>: N code blocks / M tables of the
  page are missing from the Markdown` is printed and the Version is stored (a partial Version
  with a warning beats none).
- `_` is not escaped: `\_` written by Trafilatura is unescaped everywhere; `\[`, `\]`, `\*` stay.
- `title`: Trafilatura's `extract_metadata` title, else `<title>`, else the first `h1`.
- Thin page: when the Markdown has fewer than 600 characters of text or fewer than 40 words and
  the Original's text content is at least five times longer, the step declines with
  `needs_browser` and reason `thin content`; with no browser installed that is the error the Run
  sees, with the install command in the message.
- A converter exception is caught by the page step and reported as `lorekeep: error: <url>:
  could not convert <media type> (<ExceptionName>: <message>); report it to the owner`, exit 1,
  nothing stored.
- Headings on pages whose `<h1>` Trafilatura drops: the title is inserted as the first `# ` line
  when the Markdown has no heading at all.
- Fixtures for every rule above are cut from the Originals of the first migration
  (`scratchpad/migrate` logs name the files); they move to `tests/fixtures/` under their host
  names: a Fern Guardrails page, a Mintlify LangChain page, a kubernetes.io page without headings,
  a build.nvidia.com menu, the OWASP page with the wrong canonical, a GitHub `blob` page, a Sphinx
  page with headerlinks, the LangChain `sql-agent` page that crashed.

### Search and Sections (ticket 04)

- `file:line` is the line of the first Section line that contains a matched term (`--exact`: the
  needle; FTS: any query word, case-insensitively, after unescaping); when none is found (stemmed
  match) it is the Section's first content line. The JSON gains `heading_line` beside `line`.
- `--exact` compares after unescaping both sides' `\_` and `\*`.
- Heading paths have permalink links stripped (`[#](…)`, `[¶](…)`) when the Index is built, so
  old Versions search cleanly too; an empty heading path prints as `(top)`.
- A fence opener counts only when the line is nothing but the fence (and an optional info
  string); a fence that is never closed ends at the next heading.
- Zero results print `no matches` on stdout (exit 0); the `+N matches under other tags (--all)`
  line is printed only when N > 0.
- `search` accepts the query after `--` and documents it; `lorekeep --version` prints the version;
  `status` prints the host rules only with `--rules`.

### The skill (ticket 05, after 01–04)

- `SKILL.md` covers what a Run uses — `get`, `search`, `add`, `status` — in under 250 lines; the
  owner's commands move to `references/owner.md`, the Store layout stays in
  `references/store.md`. It states: the returned `url` may differ from the address asked (trailing
  slash, fragment, redirect, Twin reduction) and is the one to cite; `requested_url` in JSON;
  fragments are dropped and the caller keeps them; `.md` and `?accept=` are Twins only under a
  host rule; parallel `get`s against one Store are safe; on exit 1 say whether to retry (only
  `ReadTimeout`/`ConnectError`/`5xx`, once) and otherwise report the URL and the error line to the
  owner, never fetch another way, never `add` a page; the Tag is per guide, keep your own log of
  `get --json` lines; a `third-party` page the guide treats as primary is reported to the owner;
  `authority` of laws and standards published by their issuer is `primary`; `search` needs
  `-- '<query>'` for a query starting with `-`; `file:line` is the matching line.
- `references/store.md` documents `citations.csv` fully: header required, one row per
  `(work_id, url)`, `as_of` an ISO date (read as the end of that day, UTC) or timestamp, `url`
  normalised, Twin-reduced and taken through `aliases.csv`, a cited `url` with no Version is a
  warning of `recheck --citations`.
- The flag-vs-`--help` test keeps passing for both files.

## Testing Decisions

As v1: the command layer is the seam; fixtures are recorded responses; the new fixtures are the
first migration's Originals, cut to the smallest HTML that still shows the defect. Every bullet
above has one test naming its fixture. `pytest`, `ruff`, `pyright` stay the gate.

## Out of Scope

- PDF quality (joined words, no headings in NIST PDFs): noted, not fixed; Docling stays out.
- Writing a `checks.csv` row for a URL that never stored: a Run's log is the record.
- `--query` as a flag.
- Any change to `backup`, `restore`, the Index schema beyond `heading_line`, or concurrency.
