# Versions are immutable files in one flat folder per Project

A Store is a single folder with no subfolders. A Version is named
`<host>--<path with / as ->--<first 8 hex of sha256>.md`, its Original sits beside it as
`<same stem>.orig.<ext>`, and the path part is truncated when the name would be too long — the hash
keeps it unique and the full `url` is in the frontmatter. A Source that changes upstream gets a new
file beside the old one; no file is ever rewritten or deleted by the tool.

Keeping every Version is the point of the Store: a finished work rests on the text it was written
from, and that text must still be there when the page has changed or gone. One folder was preferred
over `host/path/` trees because the owner found nested folders hard to work with, and a few
thousand files in one folder are no burden for the filesystem or `grep`. Immutability is also what
makes the Store cheap to put under git, DataLad or a bucket later: such a move wraps the folder and
transforms nothing.
