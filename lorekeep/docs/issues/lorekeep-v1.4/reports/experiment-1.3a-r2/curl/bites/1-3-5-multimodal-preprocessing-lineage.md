---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-5"
title: "Preserve evidence through every preprocessing branch"
description: "Build text, image, audio, and tabular preprocessing branches that retain source provenance and validate prepared artifacts."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Build multimodal text, image, audio, and tabular preprocessing pipelines with provenance and validation checks.

## Core idea

A multimodal pipeline needs a shared evidence contract, even when each modality needs different transformations. Keep the original source identity, identify every derived artifact, and record which validation admitted it for model consumption. A text transcript, resized image, and normalized table should remain traceable to the evidence they represent.

Do not collapse the branches into an anonymous text field. That removes the page location, time interval, table meaning, or image relationship needed to investigate an incorrect answer. Preserve modality-specific evidence until the consuming model's input contract is assembled.

Extraction service selection belongs to 1.3.3 and compute selection to 1.3.4. This lesson connects those stages through provenance, validation, and publication decisions.

## How it works

### Establish source identity before transforming

Define an application-owned artifact manifest. Useful example fields are `source_id`, `source_revision`, `modality`, `parent_artifact_id`, `transform_version`, `artifact_uri`, `validation_status`, and `validation_reasons`. These are suggested application fields, not an AWS-defined manifest schema. Keep the schema stable enough that each branch can emit the same release evidence.

S3 event notifications provide concrete source attributes: bucket name, object `key`, `size`, `eTag`, and `versionId` when the bucket is versioning-enabled. Decode the object key using its documented URL-encoded representation before resolving it. Preserve the version identifier when available; do not silently treat a mutable key as an immutable source revision.

Event arrival order is not source revision order. S3's `sequencer` can order PUT and DELETE events for the same object key. Compare its hexadecimal value, left-padding shorter strings with zeros before a lexical comparison. It cannot order changes across different keys. Keep that boundary when deciding whether an event supersedes an artifact or belongs to another source entirely.

Use source revision plus transformation identity to distinguish a replay from intentional reprocessing. Record a changed transform as a different derivation even when the source is unchanged. The broader governance lineage model belongs to 3.3.3, and retrieval metadata to 1.4.5; the concern here is maintaining evidence through preprocessing.

### Preserve text meaning and location

For text inputs, validate decoding, required fields, and the application schema before normalization. Make whitespace, date, and delimiter handling explicit in the transformation version. Compare representative transformed examples against their originals, especially where identifiers, negation, units, or section boundaries affect meaning.

For extracted document text, retain Textract `Block` identifiers, `Relationships`, and `Geometry` with the text projection. A string assembled from cells can lose the association between a value and its column heading. Save that association rather than relying on the model to reconstruct it from an ambiguous sequence.

Validate after transformation as well as before it. A nonempty raw document can become an empty prepared artifact if extraction fails or a filter removes all content. Mark that result rejected with a reason instead of allowing an empty artifact to inherit the parent's accepted status.

### Prepare images without removing decisive detail

Preserve the original image and identify any crop or resize as a derived artifact. Record the transformation needed to relate derived coordinates to the original. Review whether the result retains the text, legend, or visual region the task needs; legal dimensions alone do not establish usability.

The Bedrock `Message` contract permits up to 20 images, each at most 3.75 MB and 8000 pixels in height and width. Check those constraints before constructing the request, then verify the selected model supports the intended image path using the checks in 1.3.3. Passing the message-level size check does not prove a model can interpret the image.

If an image branch uses a crop to meet its task, preserve both crop identity and original source identity. An answer about a chart should not cite a crop that omitted the legend defining its units. Route such an artifact for another transformation or review rather than filling the gap with a plausible interpretation.

### Prepare audio while retaining time evidence

Validate the actual encoding, channel layout, and sample rate before transcription. Transcribe supports one- and two-channel media. Batch and streaming support different formats; choose the accepted encoding for the route. For example, lossless FLAC is supported for both, while streaming PCM has its own encoding requirements.

Keep transcription text paired with the original recording. Transcribe's word evidence includes `start_time`, `end_time`, and alternative `confidence` values for spoken words. Preserve those fields through cleanup so a reviewer can replay the relevant interval. Do not invent timing for punctuation or assume that combining transcript segments preserves word alignment automatically.

Define validation for the output you intend to use: required speech segments represented, language suitable for the task, and important identifiers reviewed when transcription is uncertain. These are application acceptance criteria. A confidence field provides review evidence; it is not a substitute for checking the business-critical content.

### Prepare tables with explicit semantics

For tabular inputs, retain the source row or business key, column names, units, and schema version. Normalize types and join references deliberately. Avoid flattening an amount into prose while dropping the currency or losing which source row supplied it.

Glue DQDL provides `ColumnExists`, `ColumnDataType`, `IsComplete`, and `IsPrimaryKey` for structural checks, and `ReferentialIntegrity` for cross-dataset relationships. Choose the applicable rules and validate the prepared table again. A join or cast can change completeness and uniqueness after the raw dataset passed.

Bedrock `DocumentBlock.format` includes `csv`, `xls`, and `xlsx`, among other formats. That interface vocabulary does not establish support by every model or remove the need for table validation. Keep message assembly separate from preparation; see 1.3.6.

### Join only validated artifacts

Give each branch an explicit accepted, rejected, or review-required disposition in the application manifest. The join checks that every required modality for the task has an accepted artifact from the intended source revision. Optional evidence can be omitted only under the task's declared policy.

When sending documents through Bedrock, use a neutral `DocumentBlock.name`. AWS warns that this field is vulnerable to prompt injection because a model can interpret its value as instructions. Keep source provenance in trusted application metadata rather than copying an untrusted filename into an instruction-sensitive field.

## Key distinctions and trade-offs

**Normalized content versus original evidence:** Prepared content improves consumption. The original and its mapping make the transformation reviewable. Preserve both when a transformation can change interpretation.

**Branch success versus complete input:** One accepted transcript does not compensate for a missing required table. Evaluate completeness at the join as well as within each branch.

**Shared manifest versus shared transformation:** Common provenance fields unify the release decision. They do not justify applying text cleanup rules to image coordinates, audio timing, or typed table values.

## Architecture / decision scenario

A maintenance assistant receives a technician's note, an equipment photograph, a spoken report, and a parts spreadsheet. All four are required for the team's diagnosis workflow.

The text branch preserves equipment identifiers through normalization. The image branch creates a bounded artifact while keeping the original and crop mapping. The audio branch retains transcript words and time intervals. The table branch checks required columns, unique part keys, and equipment references with DQDL.

Each branch emits the application manifest fields and its validation disposition. The final join detects that the image crop removed the equipment label and that a parts join introduced missing references. It holds the input package, while keeping the accepted note and transcript available for investigation.

Reprocessing creates corrected derived artifacts tied to the same source revisions and a different transformation version. Only after both failed branches pass does the join release the complete package. The model receives validated evidence; the application retains enough provenance to explain every branch's contribution.

## Common exam traps

- Treating an S3 key without revision information as immutable evidence.
- Ordering unrelated object keys with `sequencer`.
- Dropping coordinates, timestamps, or table headings during text conversion.
- Assuming pre-transformation validation also covers the prepared output.
- Joining partial branch success into a supposedly complete package.
- Copying untrusted filenames into Bedrock document names.

## What to remember

Preserve source identity, transformation identity, and modality-specific mappings. Validate both raw and prepared artifacts, then enforce required coverage at the join. A usable multimodal input is a traceable, accepted evidence package.

## References

- AWS, [Event message structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html)
- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [Data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [DocumentBlock](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html)
