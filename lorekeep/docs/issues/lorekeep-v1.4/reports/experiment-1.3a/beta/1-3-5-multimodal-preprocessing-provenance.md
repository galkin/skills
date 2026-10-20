---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-5"
title: "Preserve evidence through every preprocessing branch"
description: "Design text, image, audio, and tabular preprocessing paths with traceable derivatives, complete job results, and explicit publication gates."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Build multimodal text, image, audio, and tabular preprocessing pipelines with provenance and validation checks.

## Core idea

For an architect building a multimodal pipeline, the central artifact is a
traceable accepted derivative. Converting everything into text is insufficient:
you must be able to explain which source version produced a value, which
transformation changed it, and which checks permitted its publication.

Treat text, images, audio, and tables as distinct branches joined by an explicit
source identity. Each branch validates its own representation and preserves a
mapping back to evidence. A final gate checks branch completion, cross-modal
agreement, and task suitability before the foundation model consumes the result.
The gate belongs to your application; a collection of successful service calls
does not implement it automatically.

Service selection is covered in 1.3.3, compute placement in 1.3.4, and quality
thresholds in 1.3.1. This lesson adds the evidence and completion contract that
holds those choices together.

## How it works

### Freeze source identity before transforming

Create an application-owned processing record for each source. Include a stable
source identifier, source location and revision, modality, transformation version,
output locations, validation policy version, and processing outcome. These fields
are a proposed application schema, not reserved AWS metadata names.

S3 Versioning supplies object version identity when enabled. S3 assigns unique
version IDs to objects written into a versioning-enabled bucket. Objects that
predate enabling versioning retain a null version ID until a subsequent write
creates a versioned object. Record bucket, key, and version rather than assuming
a key always identifies the same bytes.

Keep the original and derivative distinguishable. An application-computed content
hash can help verify the bytes used in processing, but it does not replace source
identity, authorization metadata, or transformation history. If you rerun a
changed parser, create a distinct derivative record even when the original is
unchanged. That makes comparisons and reprocessing explainable.

### Preserve mappings in every modality

For **text**, validate decoding and required fields before normalization. Preserve
the original text and either a mapping for changed offsets or a distinct version
for the normalized representation. A whitespace or Unicode transformation can
change the positions used by downstream annotations. If you detect entities,
retain Comprehend `BeginOffset` and `EndOffset` with the exact text version sent
to `DetectEntities`, not with an unrelated later rewrite.

For **images**, validate successful decoding and the selected consumer's format
and size requirements. Preserve original dimensions and any crop or resize
operation in your transformation record. A crop that removes the legend can
leave a visually clear diagram that is unsuitable for interpretation. If you
send an image through Converse, `ImageBlock.format` supports `png`, `jpeg`, `gif`,
and `webp`; `Message` imposes its own image-size and count restrictions. Check
those before invocation rather than relying on a downstream rejection.

For **audio**, preserve the recording identity alongside the transcription job
and output. Amazon Transcribe's JSON transcript includes word-level start and
end times and confidence scores. Retain those anchors when turning recognized
speech into segments. If you concatenate segments into a summary input, keep
the segment-to-recording mapping so a reviewer can locate the original speech.
A transcript without its recording identity is weak provenance even if the
recognized words look plausible.

For **tabular data**, preserve column names, declared types, units, and source-row
identity. Validate required columns and values before joining or filtering, then
validate the output after those operations. Glue DQDL supplies checks such as
`ColumnExists`, `ColumnDataType`, `RowCountMatch`, and `ReferentialIntegrity`.
Choose checks that explain losses and relationships, rather than assuming a
transformation that completed successfully preserved all rows.

### Verify asynchronous completeness

Document and transcription jobs introduce a second completion boundary.
`StartDocumentAnalysis` or `StartTranscriptionJob` returning an identifier means
the work was submitted. It does not mean the derivative is complete or acceptable.
Store that job identifier in your processing record.

For Textract, inspect `GetDocumentAnalysis.JobStatus`. The values include
`IN_PROGRESS`, `SUCCEEDED`, `FAILED`, and `PARTIAL_SUCCESS`. A partial result needs
an explicit business policy; do not silently treat it as complete. Follow
`NextToken` until all result pages are retrieved. The token paginates blocks,
so retrieving one response does not establish that all document evidence arrived.

For Transcribe, inspect `GetTranscriptionJob.TranscriptionJobStatus`.
`COMPLETED` identifies finished transcription, and `TranscriptFileUri` identifies
the result. `FAILED` includes a `FailureReason`. Read and validate the transcript
after completion; a finished job can still contain recognition errors that matter
to the task. Keep service completion separate from your acceptance outcome.

### Publish only after the join gate

Represent each required branch as pending, completed-and-validated, rejected, or
failed in your application record. Define which branches are mandatory for each
input type. An image-only submission should not wait for an audio branch that
was never required, while an inspection package requiring both a recording and
a table must not publish after only one arrives.

Reconcile expected and produced artifacts, required fields, source mappings,
and cross-modal identifiers. Publish a release record only when all mandatory
conditions pass. Retain rejected derivatives with reason codes outside the
accepted input set. Reprocessing should create reviewable evidence of what
changed rather than silently replacing the last accepted interpretation.

The evidence metadata carried into retrieval is covered in 1.4.5. This pipeline
must produce reliable source and transformation identity before that later
metadata projection can preserve it.

## Key distinctions and trade-offs

A common representation makes downstream assembly easier, but it must not erase
modality-specific evidence. Keep a shared envelope for identity and validation,
with modality-specific payloads for word times, image transforms, text spans,
and table structure. A plain-text-only contract often hides exactly the evidence
needed to diagnose an incorrect model answer.

Validation before transformation detects source defects. Validation afterwards
detects defects introduced by normalization, joining, transcription, or extraction.
Both are necessary when a valid source can become an invalid derivative.

Preserving intermediates improves reproducibility and investigation while
increasing storage and lifecycle responsibilities. Retain the evidence required
by the workflow's policy rather than collecting arbitrary copies. Provenance
means a demonstrable dependency chain, not indefinite retention of every file.

## Architecture / decision scenario

An equipment assistant consumes inspection packages containing a typed report,
a component photograph, a voice memo, and a CSV of measurements. The intake
record identifies all four expected artifacts by source revision and assigns a
shared inspection identifier.

The text branch preserves the original and normalized versions. The image branch
records its crop and checks that the equipment label remains visible. The audio
branch submits Transcribe and retains word-time anchors with the recording.
The tabular branch checks schema, numeric types, and relationships to the
inspection identifier with Glue rules.

A scanned attachment uses Textract. Its consumer checks `JobStatus`, retrieves
all `NextToken` pages, and validates expected content before marking that branch
accepted. A `PARTIAL_SUCCESS` result leaves the package unresolved under this
workflow's strict completeness policy.

The join gate compares the component identifier across the report, extracted
attachment, transcript, and table. If the photograph shows a different component,
the package goes to review with all source mappings intact. If the identifiers
agree and required checks pass, the release record selects the accepted
derivatives for model consumption. A later parser correction can be traced to
its source and transformation version without inventing a different inspection.

## Common exam traps

- Treating an S3 key without revision identity as immutable provenance.
- Marking asynchronous submission as completed preprocessing.
- Ignoring Textract pagination or accepting partial success implicitly.
- Keeping entity offsets after changing the referenced text.
- Publishing one successful modality while another required branch is unresolved.

## What to remember

Preserve original identity, transformation identity, and evidence mappings across
all modalities. Verify job completion and complete result retrieval, then apply
your own validation and join policy. Only an accepted release record should
select the derivatives the model consumes.

## References

- AWS, [Using versioning in S3 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- AWS, [DetectEntities](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html)
- AWS, [ImageBlock](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [Data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- AWS, [DQDL rule types](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [GetDocumentAnalysis](https://docs.aws.amazon.com/textract/latest/APIReference/API_GetDocumentAnalysis.html)
- AWS, [GetTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_GetTranscriptionJob.html)
