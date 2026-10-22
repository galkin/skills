# Collecting Sources

A Collector fetches the Sources a guide or a section needs into the Store: `status` first, then a
`get` per page, a log line per `get`, `add` for the owner's own inputs, and a report of every
failure. [reading.md](reading.md) comes first: its `search`, `get`, citation and stderr rules hold
here too.

## `lorekeep status`

Run `lorekeep status` once first: `Browser: not ready: …; fix: …` means browser pages will fail.
Report that line to the owner, never run its fix yourself, and go on.

Summarises the Store: Versions, Sources, the Sources the owner withdrew (left out of every other
count), Readings and reading rules, Tags, oldest and newest
fetch, Recheck results, hosts no rule knows, size, the Project's settings, and whether the browser
(Crawl4AI and Chromium) can start here. `--rules` also prints the host rules, merged (a Project's
own marked `(lorekeep.toml)`); `--json` prints no settings and no host rules.

```text
Store: /…/store
5 Versions of 5 Sources
Withdrawn: 0 Sources (0 Versions)
Readings: 1 of 5 Versions, 6 rules
Tags: nvidia 5
Oldest fetched_at: 2026-10-17T20:08:26Z
Newest fetched_at: 2026-10-17T20:08:26Z
Rechecks: 0 unchanged, 0 changed, 0 gone, 0 error
Unknown hosts: genai.owasp.org, helm.sh
Size on disk: 303355 bytes
Bucket: none
Freshness window: 30 days
Browser: ready (Crawl4AI 0.9.5)
```

## The log

Append every `get --json` line to your own log; the Tag says only that the guide read a Source, so
your log is the record of what you read and what failed; `asked` in each line is the address as
you gave it, `#fragment` included. For an exit `1`, append the address and the error line as one
JSON object. Judge each `get` by its own exit code, not your loop's. Keep the log where your brief
says, else in your final message:

```text
{"path": "/…/store/helm.sh--docs-helm-helm_rollback--baae9b0a.md", …, "asked": "https://helm.sh/docs/helm/helm_rollback/#synopsis", …, "outcome": "stored"}
{"url": "https://example.test/slow", "error": "lorekeep: error: nothing stored for https://example.test/slow: the host rule names no Twin; https://example.test/slow failed (ReadTimeout)"}
```

Parallel `get`s against one Store are safe: writers take a lock; one page gets one Version.

## How `get` reads a page

`get` returns a Version of the page at `URL`, fetching only when the Store has none or it is older
than the freshness window (`--max-age`, default the Project's `freshness_days`, 30), and adds the
Tag to it. lorekeep reads, in order: the publisher's Markdown **Twin** under a host rule (a GitHub
`blob/` page from its raw file, code fenced by extension); the static HTML, main content extracted;
a PDF; JSON, YAML, plain text, CSV or XML verbatim in one fence; the browser, last.

A Twin has no **Original** beside its Version: [store.md](store.md#files).

- `.md` and `?accept=text/markdown` addresses are Twins only under a host rule; elsewhere they are
  fetched as pages of their own, so ask for the page's address.
- A canonical link the page declares never becomes `url`; it is recorded as `canonical`, with a
  warning, and changes nothing for you.

What each `outcome` and `verified_at` mean: [store.md](store.md#what---json-adds).

## Failures and thin pages

Exit `0` can still be a menu or a page that lost a list: open a Version under 2 KB, compare it with
its Original, and report what is missing.

On exit `1`, retry and report as [reading.md](reading.md#stderr-lines-and-what-to-do) says, and:

- `thin content` (under 600 characters or 40 words from a page with five times the text) needs
  the browser, which waits longer before `rendered a shell`; report it with `status`'s Browser line.
- `unsupported media type` and `could not convert` errors are the owner's to fix.

## `lorekeep add`

Stores a Markdown or text file your brief hands you (research pasted from a chat, a note) as a
Version with `url` `owner:<slug of the title>`, searchable like any page. Never a fetched page.
`--title` is required, and its slug names the Source; `--publisher` is who produced the text, such
as `claude` (default: `owner`); `--authority` defaults to `generated`. `--json` prints the same
fields as `get` ([store.md](store.md#what---json-adds)); `outcome` is `unchanged` when the same
text was added before.
