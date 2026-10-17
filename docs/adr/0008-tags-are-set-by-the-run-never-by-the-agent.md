# Tags are set by the Run, never by the agent

A Source may carry any number of Tags, one per ecosystem (`anthropic`, `nvidia`, `aws`), recorded
as append-only rows in `tags.csv` (`url, tag, added_at`). A Run declares its Tag once, in its
environment (`LOREKEEP_TAG`); every `get` it makes adds that Tag, and a `get` of a Source another
Run already fetched adds the Tag without fetching again. `get` refuses to run without a Tag, so no
Source is ever untagged. A `tag add` command exists for the owner — to tag what a migration brings
in — and is not part of any agent's brief.

A shared Store (ADR 0004) mixes ecosystems, and an index of three Runs showed what that does to
search: for `prompt caching`, eight of the top ten pages were AWS Bedrock, which is the wrong answer
for an author writing about Anthropic. Scoping by Tag restores what per-Run caches used to give for
free. The Tag is deliberately a label and not a corpus: it says only "a Run of this ecosystem read
this", never "this is everything the ecosystem documents", and the `+N matches under other tags`
line in every search (ADR 0005) keeps the rest visible.

## Considered Options

- **"Corpus", "collection", "ecosystem".** Rejected: the first two promise a curated, complete set,
  and an agent that finds nothing under a "corpus" concludes the vendor documents nothing — a false
  negative, the worst error for fact checking. "Ecosystem" is right for the first Project but
  lorekeep is not only for guides.
- **Agents tagging Sources themselves.** Rejected: an extra dimension for agents to maintain is the
  same trap as licences, and they do it badly.
- **A Store per ecosystem.** Rejected: the MCP specification belongs to both Anthropic and NVIDIA
  and would be stored twice, and "search everything" would need several indexes.
