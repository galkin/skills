# 04: a true `title`, a search that finds ligatured text, and a warning for pages without structure

**What to build:** Three things the tool owns, with no edit to the Markdown it stores (owner's decision 2026-10-17: stripping a publisher's banner is post-processing, not the tool's job, so the Fern llms.txt banner stays). (1) `title`: when a page has an `<h1>`, it wins over `<title>` for `title` and for the heading inserted when the Markdown has none (Microsoft Learn's `<title>` is `Retry pattern - Azure Architecture Center | Microsoft Learn`, its `<h1>` `Retry pattern`); a PDF's `title` comes from the PDF's metadata, else its first non-empty line. (2) Search: the Index and `--exact` compare text with the ligature code points `ﬁ ﬂ ﬀ ﬃ ﬄ` read as their letters, the way `\_` is already unescaped at Index time, so `--exact profile` hits a line the PDF spells `proﬁle`; the stored Markdown is unchanged. (3) A Version over 20,000 characters with no heading below its title prints `lorekeep: warning: <url>: no headings; search answers with the whole page as one Section` on the `get` that stores it. Decisions: `spec.md` › Converters (amended by this ticket).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] a Microsoft Learn fixture cut from the Store's Original (`learn.microsoft.com/…/patterns/retry`) stores `title: Retry pattern`, and its headings' paths in `search` start `Retry pattern`; a page with `<title>` and no `<h1>` keeps today's behaviour
- [ ] the first pages of `nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf` (fixture cut from the Store's Original) store `title` from the PDF's metadata; a PDF without metadata title takes its first non-empty line
- [ ] over that fixture, `search --exact profile` hits a line the Markdown spells `proﬁle`, the snippet shows the line as stored, and the Markdown file still contains `ﬁ`; a plain `search profile` finds it too; an Index built by v1.1 is rebuilt by the next reader (bump `SCHEMA_VERSION`)
- [ ] the EUR-Lex AI Act Original (`eur-lex.europa.eu/eli/reg/2024/1689/oj`, cut to under 100 KB but over 20,000 characters of Markdown) stores with the no-headings warning; the kubernetes.io Deployment fixture and a short headingless page print none
- [ ] `references/store.md` says `title` comes from `<h1>`, else `<title>`, else the first heading, and from a PDF's metadata; `SKILL.md`'s PDF sentence says `--exact` reads ligatures as letters; the flag test passes
