# A Check is a conditional request, run on demand

`check` asks each Source's publisher whether it changed: a request with `If-None-Match` /
`If-Modified-Since` from the latest Version, or, when the server offers neither, a full fetch whose
Markdown hash is compared. A `304` or an equal hash appends a row to `checks.csv`; a different hash
stores a new Version. It runs when someone asks — typically when a new guide version starts — and
there is no watcher service.

What matters after a vendor update is the list of finished works whose Sources changed, and
Citations in the Index turn the Check log into exactly that list. A watcher would add a running
service for a question that is asked a few times a year.
