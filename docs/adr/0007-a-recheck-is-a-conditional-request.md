# A Recheck is a conditional request, run on demand

`recheck` asks each Source's publisher whether it changed: a request with `If-None-Match` /
`If-Modified-Since` from the latest Version, or, when the server offers neither, a full fetch whose
Original's hash is compared (ADR 0001 says why not the Markdown's). A `304` or an equal hash appends
a row to `checks.csv`; a different hash stores a new Version. It runs when someone asks — typically
when a new guide version starts — and there is no watcher service.

`get` performs the same request on its own when the latest Version is older than the Project's
freshness window (`lorekeep.toml`, default 30 days): younger, it returns what is stored; older, one
conditional request decides, and `--fresh` forces it. Without that window a Run months after the
last one would read stale pages without knowing.

What matters after a vendor update is the list of finished works whose Sources changed, and
Citations in the Index turn the Recheck log into exactly that list. A watcher would add a running
service for a question that is asked a few times a year.

The command is `recheck`, not `check`: the first consuming Project calls its quizzes "Knowledge
checks" and "Checkpoints", and the same agents work in both repositories.
