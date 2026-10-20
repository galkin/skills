---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-5"
title: "Preserve evidence across every modality conversion"
description: "Build multimodal preprocessing stages that retain source identity and release only validated derived artifacts."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Build multimodal text, image, audio, and tabular preprocessing pipelines with provenance and validation checks.

## Core idea

A multimodal pipeline needs more than successful service calls. Every derived artifact must answer three questions: which source produced it, which transformation produced this representation, and which checks permit its use? Without those answers, a clean transcript or normalized table can become detached from the evidence it is supposed to represent.

Use modality-specific transformations behind a common acceptance contract. Preserve the raw source, retain a link from each derived artifact to that source, and validate both the input and the transformed output. The fields and application states proposed here are a design pattern, not an AWS-defined universal provenance schema.

Extraction selection belongs to 1.3.3, and the Lambda-versus-Processing compute decision belongs to 1.3.4. This lesson connects their outputs into a release that remains explainable after normalization, retries, and partial failure. Retrieval metadata and chunk provenance belong to 1.4.5.

## How it works

### Establish source identity before conversion

For S3 event notifications, retain the bucket, object key, event details, and available object version. The notification's `s3.object.versionId` identifies the version when bucket versioning is enabled; otherwise it can be null or absent. Decode object keys correctly: AWS documents URL-encoded keys, with a space represented by `+` in its example.

Do not treat event arrival order as source order. S3 notifications are not guaranteed to arrive in the order events occurred. For create and delete events on the same object key, `sequencer` supports ordering. Compare hexadecimal values after left-padding the shorter string with zeros. It cannot establish order between different object keys.

Build an application provenance record around that source identity. Example fields are `source_bucket`, `source_key`, `source_version`, `transform_version`, `artifact_uri`, `validation_status`, and `failure_reason`. Retain an explicit immutable source identity when S3 versioning is unavailable; a mutable key alone cannot establish which historical bytes produced an artifact.

Record each output-to-input relationship. A document might produce several images, extracted text, and a table. A normalized table can then produce text for an FM. Keep those relationships so a later defect can be traced to the exact transformation rather than only to the case that contained the source.

### Preserve meaning in each modality

For **text**, define an explicit normalization policy for encoding, whitespace, and boundaries. Preserve the original text and a transformation version. Check required content before and after normalization, because a non-empty source can become empty after cleaning. If later stages use offsets, preserve the text representation to which those offsets refer.

For **images** sent through Bedrock Converse, `ImageBlock.format` accepts `png`, `jpeg`, `gif`, or `webp`. A TIFF scan or HEIC photograph therefore needs conversion before it can be supplied as an image block. Treat the converted image as a derived artifact with its own identity and source relationship. Check that decoding, resizing, and conversion preserve the visual evidence the task requires; accepting a format does not establish readability. When Textract extracts document structure, preserve relevant `Block` relationships rather than only a flattened string. See 1.3.3 for extraction selection and request parameters.

For **audio**, retain Transcribe's `TranscriptionJobName` and the transcript's output location in the provenance record, linked to the source recording. See 1.3.3 for the transcription request contract. Validate the derived transcript's required content separately from successful transcription, and retain that validation result with this specific transcript artifact.

For **tabular data**, preserve column names, types, units, and record identity through transformations. Glue DQDL provides `ColumnDataType`, `ColumnValues`, `Completeness`, `ReferentialIntegrity`, and `CustomSql` for concrete checks. Validate the normalized dataset again: a unit conversion or join can create defects that were absent in the source. DQDL does not support nested or list-type column data, so validate nested artifacts separately or make the checked projection explicit.

### Keep execution and acceptance evidence together

For a batch transformation, retain the processing job name, input snapshot, container identity, and output location with the output's provenance; see 1.3.4 for the Processing execution contract. These records identify the transformation, while your implementation owns the semantic checks and publication policy.

Use separate application dispositions for accepted artifacts, rejected artifacts, and validation that could not complete. Store failed check identifiers and the source identity with a rejected result. A transient processing failure is not evidence that the content is invalid, and missing validation evidence is not a pass.

Validate after every lossy boundary. Flattening a table can remove headers, normalizing text can change offsets, and summarizing audio can omit a qualifier. Choose checks around the information the downstream task requires. For example, compare required identifiers before and after normalization and verify that a table-derived sentence retains the amount and its unit.

### Release a coherent input bundle

Define which modalities are mandatory for the task. A bundle that requires an image and transcript must remain unavailable when either required artifact fails validation. An optional attachment can be omitted only under a documented partial-coverage policy that exposes the omission to the consuming application.

For Bedrock Converse, image and document inputs use corresponding content blocks, and support depends on the selected model. A document block requires a related text prompt. Build that request only from accepted artifacts, with the source relationships retained outside the request as application evidence. Exact message formatting belongs to 1.3.6; provenance should survive even if a different runtime interface is selected.

## Key distinctions and trade-offs

**Source identity versus artifact identity:** One source can yield multiple derived outputs. Give each output its own identity and retain its parent relationship instead of overwriting a single source record with the last representation.

**Reprocessing versus replacement:** A different transform version can produce a different result from identical bytes. Preserve both the source revision and transformation version when comparing outputs or repeating a failed stage.

**File validity versus task evidence:** Decodable audio or an image in an accepted format can still lack the evidence needed for the task. Keep mechanical checks separate from semantic acceptance.

**Partial success versus coherent publication:** Releasing every successful branch independently can combine mismatched source revisions. Gate the bundle by required artifacts and source compatibility, with explicit treatment of optional failures.

## Architecture / decision scenario

A warranty assistant receives a typed complaint, a product photograph, a recorded explanation, and a CSV of purchases. The example contract requires all four modalities before the assistant can recommend a warranty outcome.

The pipeline captures source identity from the S3 notifications and records each transformation version. Text normalization preserves the raw complaint. Image processing checks decodability and retention of the serial-number region. Transcribe produces the recording's transcript under an identified job and controlled output location. Glue rules check purchase identifiers, types, allowed values, and references after normalization.

The pipeline then compares the product identity across the accepted representations. An unreadable photograph blocks the bundle, even when the transcript is valid. A missing currency unit in the normalized table also blocks release, even when its numeric columns pass type checks. A reordered S3 event cannot replace the accepted object revision without the application's source-order check.

After every required artifact passes, the application publishes one bundle with source and transform references. The downstream model receives accepted content, and a disputed recommendation can be traced through each modality to the source evidence and validation result.

## Common exam traps

- Treating an S3 key without a revision as immutable historical identity.
- Comparing `sequencer` values across unrelated object keys.
- Keeping only flattened text and losing document structure.
- Validating raw data while trusting every transformed output.
- Sending a TIFF scan directly as a Converse image block instead of creating a supported derived image.
- Publishing a bundle while a required modality is rejected or missing.

## What to remember

Give every artifact a source, transformation identity, and validation disposition. Preserve modality-specific evidence through conversion, and check the representation after each transformation. Release a coherent bundle only when every required branch passes its acceptance contract.

## References

- AWS, [Event message structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html)
- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [ImageBlock](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
