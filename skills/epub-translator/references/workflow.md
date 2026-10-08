# Workspace operations

Reference for exceptions. Commands accept `--root <workspace>` before the subcommand.

## Extraction and repair

`extract` runs `epub2md` into a temporary directory, checks coverage, then installs the result; an existing extraction is skipped. Pass `--depth N` only when inspecting a nested TOC justifies it; the default is the converter's auto mode. `--repair-missing` copies only missing files after a fresh extraction matches every existing file and the recorded baseline. There is no `--force`.

If a different converter or depth produces different chapter boundaries or bytes, keep the workspace intact, inspect the fresh result separately and reconcile the extraction with existing translations explicitly. Never clear the baseline to silence an error.

Coverage compares text from every readable spine document of the EPUB with the extracted Markdown, and checks numeric filenames, reading order, image-only pages and image occurrences. It catches omitted source documents even when the source and translation file sets match, but it is a diagnostic, not proof: inspect an unusual TOC yourself. The opening image-only cover may be absent from extraction; the build carries it separately. `check-source` runs coverage without recording anything.

`verify-source` records hashes of the EPUB and all extracted files when coverage passes and no baseline exists; it never overwrites a baseline. `check`, `build` and `mark` refuse a missing or changed baseline.

## Review state

Each file has its own JSON receipt under `books/<book>/state/` with stage, source and translation hashes, reviewer, note and the language pair at marking time. `mark` also refuses broken structure.

- `missing`: no translation file.
- `untracked`: a translation without a `translated` or `reviewed` receipt.
- `translated`: handed off for review.
- `reviewed`: semantic review recorded; only this stage permits `build`.
- `stale`: either text changed after marking, or the receipt's language pair differs from `translation.json`.

Structural checks compare Pandoc-parsed Markdown and technical HTML attributes: headings, explicit anchors, emphasis, links, images, lists, blockquotes and separators. A short translation is flagged for inspection; meaning and completeness remain the reviewer's job.

## Build metadata and links

Example `books/<book>/metadata.json` for English -> Russian:

```json
{
  "title": "Все навыки — книга 3",
  "author": "Онор Рэй",
  "labels": {
    "contents": "Содержание",
    "cover": "Обложка"
  },
  "sections": {
    "01-title-page.md": "Титульная страница",
    "02-copyright.md": "Авторские права"
  },
  "link_targets": {}
}
```

`labels` are the reader-visible table-of-contents and cover strings; they are required and never inferred from the language code. `sections` optionally overrides navigation labels; otherwise the first heading or opening text is used.

When the build cannot map an original link, add a `link_targets` entry from the original href to a translated filename with an optional existing anchor, for example `"old.xhtml#section": "12-chapter-7.md#retained-anchor"`. Inspect the source destination first; map to a whole file only when it represents the entire destination.

Images come from the extracted resources or the original EPUB. Missing or remote images, unknown links and unresolved anchors block the build. The original cover artwork is kept; a translated cover is a separate editorial task. `check-package` revalidates an EPUB in `dist/` that was produced earlier or modified outside `build`. Package validation does not replace EPUBCheck or visual inspection.

## Existing glossary cleanup

When a glossary contains work history, move it intact to `series/translation-log.md`. Consolidate duplicate terms after checking the translations that use them. Log corrections of apparent source typos so later chapters do not silently reverse them.
