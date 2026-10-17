# 04: cleaner Markdown from Twins, HTML and PDF

**What to build:** `md-twin` drops Fern's llms.txt banner (a leading blockquote before the first heading mentioning `llms.txt` or `For clean Markdown`); `trafilatura` takes the `<h1>` over `<title>` for `title` and the inserted heading when both exist; `markitdown` sets `title` from the PDF's metadata (else its first non-empty line) and normalises the ligature code points `ﬁ ﬂ ﬀ ﬃ ﬄ` to letters; a Version over 20,000 characters with no heading below the title prints `lorekeep: warning: <url>: no headings; search answers with the whole page as one Section`. Decisions: `spec.md` › Converters.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] the Fern Guardrails Twin fixture of v1.1, with NVIDIA's banner prepended as the Store holds it, stores with the H1 on line 1 of the body and no `llms.txt` in the Markdown; a Twin without a banner is byte-identical to before
- [ ] a Microsoft Learn fixture (`<title>Retry pattern - Azure Architecture Center | Microsoft Learn</title>`, `<h1>Retry pattern</h1>`) stores `title: Retry pattern` and its headings' paths start `Retry pattern`
- [ ] the first pages of `NIST.AI.600-1.pdf` store `title` from the PDF's metadata and `search --exact profile` hits a line that the PDF spells `proﬁle`; `search --exact proﬁle` finds nothing
- [ ] the EUR-Lex AI Act Original stores with the no-headings warning; the kubernetes.io fixture prints none
- [ ] `references/store.md`'s converter list says what `md-twin` strips and what `markitdown` normalises
