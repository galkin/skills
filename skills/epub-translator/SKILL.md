---
name: epub-translator
description: Translate EPUB books between a source and target language configured in translation.json. Resumable per-file translation with review receipts, consistent series terminology, extraction and structure validation, and reproducible validated EPUB builds. Also use to inspect the workspace or validate existing translations.
license: MIT
metadata:
  author: Nikita Galkin
  version: "0.3.0"
---

# EPUB Translator

Use the current directory as the workspace. Below, `<ctl>` means `python3 <skill-dir>/scripts/bookctl.py`; see `<ctl> <command> --help` for arguments.

## Workspace

```text
translation.json                  source/target language (code + name); never infer a language elsewhere
source/<book>.epub                immutable original
books/<book>/en/NN-*.md           immutable extracted source ("en" means source, whatever the language)
books/<book>/ru/NN-*.md           translation with the same filenames ("ru" means translation)
books/<book>/extraction.json      baseline hashes of the EPUB and extracted source
books/<book>/state/*.md.json      per-file translation/review receipts
books/<book>/metadata.json        translated title, author, labels; optional sections/link_targets
series/glossary.md                terminology only (source term -> target term)
series/style-guide.md             series decisions for the target language
series/translation-log.md         history, decisions, source inconsistencies
dist/<book>.<target-code>.epub    generated book
```

Process only the books the user requested; inspecting the workspace does not start translation. Never modify `source/` or extracted source. Keep completed translated text unless it has a correctness or consistency problem.

## Start or resume

1. Run `<ctl> status [book]` for each file's [stage](references/workflow.md#review-state). Inspect existing translations; a file or old receipt does not prove completion.
2. On a new workspace or a tool error, run `<ctl> doctor [book]`, then `bash <skill-dir>/scripts/bootstrap.sh` for missing tools and `<ctl> init --source-language <code> --source-language-name <Name> --target-language <code> --target-language-name <Name>` for missing workspace files.
3. A book without extraction: `<ctl> extract <book>`. An extraction without a verified baseline: `<ctl> verify-source <book>`. Resolve reported gaps with [workflow.md](references/workflow.md#extraction-and-repair).
4. Read `translation.json`, [translation-contract.md](references/translation-contract.md), `series/style-guide.md` and `series/glossary.md`. Process books in natural filename order and files in numeric order, keeping each working context to one source file plus needed context.

## Translate and review

Translate each file following the translation contract and save work per file. Mark a file reviewed only after the full comparison in [its review section](references/translation-contract.md#completeness-and-review):

```bash
<ctl> mark <book> <filename> --stage reviewed --reviewer <name> --note "<what you compared and any findings>"
```

The receipt is an attestation by the reviewer; the command checks only structure and hashes. Use `--stage translated` only when handing a file to another reviewer or pausing before review. Use `--all` only when every file has had that review.

For a substantial book, when delegation is authorized, read [collaboration.md](references/collaboration.md) and split disjoint file ranges between workers; respect a request to work with one agent. Continue between chapters without asking for approval.

## Build

1. Write `books/<book>/metadata.json` in the target language: `title`, `author`, `labels.contents` and `labels.cover` (format: [workflow.md](references/workflow.md#build-metadata-and-links)).
2. Run `<ctl> build <book>`. It reruns every check and validates the package; a failed build keeps the previous EPUB. `<ctl> check <book>` runs the same checks without building; `--structure-only` skips receipts and metadata and never permits a build.
3. Report completed books, remaining or unreviewed files, findings and EPUB paths. Distinguish structural validation from semantic review and from visual inspection in a reader; claim only checks actually performed.
