# A Recheck is a conditional request, run on demand

`recheck` asks each Source's publisher whether it changed, through the same cascade `get` uses (so
a page only a browser can see is asked through the browser): a request with `If-None-Match` /
`If-Modified-Since` from the latest Version, or, when the server offers neither, a full fetch
compared as ADR 0001 says — received bytes first, then the Markdown. A `304` or an equal comparison
appends an `unchanged` row to `checks.csv`; a real change stores a new Version and appends
`changed`; a `404`/`410` appends `gone` and the stored text stays, which is the point of keeping it;
a network failure appends `error`. lorekeep makes these requests itself from the `etag` and
`last_modified` in the frontmatter — an HTTP cache library in between (`hishel` was tried on paper)
answers a conditional request from its own cache and hides the `304` that this log records. It
runs when someone asks — typically when a new guide version starts — and there is no watcher
service; `owner:` Sources have no publisher to ask, and Sources that only a browser could read
have no answer a byte comparison can use, so both are counted as skipped.

`get` performs the same request on its own when the latest Version is older than the Project's
freshness window (`lorekeep.toml`, default 30 days, `--max-age <days>` for one call): younger, it
returns what is stored; older, one conditional request decides, and `--fresh` forces it. The age
is counted from the later of the Version's `fetched_at` and its last `unchanged` row in
`checks.csv`, because the file is immutable and an `unchanged` answer is what moves the clock. When that
request fails or the page is gone, `get` still returns the stored Version, with a warning, because
a stale page the Run knows about beats no page. Without the window a Run months after the last one
would read stale pages without knowing.

What matters after a vendor update is the list of finished works whose Sources changed, and
Citations in the Index turn the Recheck log into exactly that list. A watcher would add a running
service for a question that is asked a few times a year.

The command is `recheck`, not `check`: the first consuming Project calls its quizzes "Knowledge
checks" and "Checkpoints", and the same agents work in both repositories.
