# lorekeep

Collects what an LLM task reads, keeps it with its provenance, and makes it findable again by every
later run of the same project.

## Language

### What is kept

**Source**:
Anything given to an LLM as input or downloaded from elsewhere for a task: a vendor page, a
specification, a third-party page, a PDF, research pasted from a chat.
_Avoid_: document, reference, material

**Version**:
One Source as it was at one moment, identified by the hash of its Markdown. A Source that changed
upstream has several Versions side by side.
_Avoid_: snapshot, revision, copy

**Latest Version**:
The Version that answers for a Source at a moment: the one its latest Recheck by then names, else
the one fetched most recently by then. A Recheck can make an older file the Latest Version again.
_Avoid_: current version (an Index is current; a Version is latest), newest version (that is
`fetched_at` alone), head

**Original**:
The bytes a Version's Markdown was made from, exactly as received.
_Avoid_: raw, source file, input

**Provenance**:
What a Version says about itself: where it came from, when, by which Converter, and how far it can
be trusted.
_Avoid_: metadata (too broad)

**Twin**:
A Markdown rendition the publisher serves beside a page, read instead of the page because it is the
same text without the page around it.
_Avoid_: mirror, markdown version

**Reading**:
A Version's Markdown after the Project's reading rules, built by the tool and kept in the Store's
`.cache/`: what a Run reads, while the Version stays the evidence and what is cited and rechecked.
A Version no rule changes has no Reading.
_Avoid_: clean copy, cleaned version, rendition

**Reading rule**:
One operation that makes a Reading from a Version — drop a leading or trailing block, drop lines
by pattern, cut a suffix from the title, insert a heading before lines by pattern — for the
Versions under a prefix or made by one engine. It never rewrites a kept line, never touches a code
fence or a table line, and records the most it removed from one Version when it was accepted: lines
for a block, a share for lines dropped by pattern.
_Avoid_: filter, cleanup, post-processing rule

### Trust

**Publisher**:
Who authored a Source's content — the vendor, the standards body, the third-party site, the chat
tool that produced a piece of research.
_Avoid_: vendor (not every publisher is one), site, origin

**Authority**:
How far a Source can be relied on for a fact: `primary` (a publisher documenting its own product or
specification), `official` (the publisher's other material), `third-party` (anyone writing about
someone else's product), or `generated` (produced by an LLM). A fetched Version's authority is the
one the current host rules give its `url`; its frontmatter keeps the one captured at fetch.
_Avoid_: citation, verdict, trust level

### Where it lives

**Project**:
The body of work a set of Sources serves, such as one website and all its guides.
_Avoid_: namespace, workspace

**Store**:
The one folder that holds every Version of every Source of one Project, shared by all of its Runs.
_Avoid_: cache, archive, corpus

**Run**:
One pass of an LLM pipeline over a Project, which reads Sources from the Store and adds to it.
_Avoid_: job, session, batch

**Tag**:
A label a Run leaves on every Source it reads, named for the ecosystem the Run serves. A Source may
carry several; a Tag says a Run read the Source, never that the ecosystem has nothing else.
_Avoid_: corpus, collection, category

**Index**:
The searchable view of a Store, rebuilt from its files whenever needed.
_Avoid_: database (the Store is the record; the Index only reflects it)

**Section**:
The part of a Version under one heading — of its Reading, where it has one — the unit the Index
searches and answers with.
_Avoid_: chunk, passage, fragment

### What happens to it

**Converter**:
What turned an Original into Markdown — the publisher's Twin, or one named extraction tool.
_Avoid_: parser, extractor

**Recheck**:
Asking a Source's publisher whether it changed since its latest Version, recorded whatever the
answer.
_Avoid_: check (a quiz in the first consuming Project), refresh, poll, sync

**Citation**:
A link from a finished work to the Source it rests on, as the work states it.
_Avoid_: reference, usage

**Collector**:
The LLM step that decides which Sources a piece of work needs before anyone writes it.
_Avoid_: crawler, fetcher, researcher
