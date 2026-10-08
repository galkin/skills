# Translation Contract

Apply these rules to every translated Markdown file.

`translation.json` at the workspace root defines the `source_language` and `target_language` (BCP 47 `code` plus display `name`). It is authoritative: never infer either language from existing prose, directory names or habit.

## Goal

Produce a natural literary translation in the target language that reads as professionally translated fiction while remaining faithful to the source — not a word-for-word rendering.

## Fidelity

- Preserve meaning, tone, pacing, characterization, humor, emotional nuance and narrative voice.
- Do not summarize, shorten, simplify, censor or add content.
- Translate all reader-visible text, including title page, copyright, dedication, contents, recaps and author material: prose, dialogue, chapter and part titles, UI/game text, notifications, descriptions and captions.
- Preserve paragraph boundaries wherever reasonably possible.
- Preserve deliberate repetition, ambiguity, jokes and character-specific speech when they matter.

## Markdown and technical structure

- Preserve Markdown structure: headings, emphasis, blockquotes, lists, separators and other constructs.
- Preserve exact filenames. Do not move prose between files unless the source structure requires it.
- Never modify image references, URLs, anchors, link destinations or other technical references; translate reader-visible link text when appropriate.

## Target-language prose

- Prefer natural literary prose over source-language syntax copied mechanically (avoid calques).
- Use the target language's punctuation and dialogue conventions.
- Preserve differences in register, formality, personality, sarcasm and emotional intensity.
- Do not embellish beyond what the source supports, and do not normalize intentional roughness or unusual voice.
- Follow `series/style-guide.md` for series-specific conventions such as address policy, dialogue punctuation and name transliteration.

## Terminology

`series/glossary.md` is the source of truth. Consistency matters especially for names and nicknames, places, organizations and titles, classes, skills, cards, ranks, levels, stats and other system concepts, items, magic terms, recurring catchphrases and forms of address.

Prefer a sensible translation already established in earlier chapters. When a new recurring term appears, choose a natural target-language equivalent and use it consistently; in parallel work, submit it to the coordinator, otherwise update the glossary directly. Keep the glossary to terms, aliases and short usage notes; reasoning and history belong in `series/translation-log.md`.

## Existing partial translations

When a translation file already exists:

1. Compare it structurally with the source and decide whether it is complete or partial.
2. Preserve good existing prose and continue from the correct source position if partial.
3. Do not rewrite a complete file for style unless consistency or correctness requires it.

## Completeness and review

A translated file must represent the full reader-visible content of its source counterpart. Target-language text or a matching heading does not make a file complete.

A file is reviewed only after a full source-to-translation comparison: no omissions, no untranslated prose, unchanged numbers and system messages, glossary terminology.
