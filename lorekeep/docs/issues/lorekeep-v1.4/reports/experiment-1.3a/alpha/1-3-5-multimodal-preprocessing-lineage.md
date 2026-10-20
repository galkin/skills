---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-5"
title: "Preserve evidence across multimodal preprocessing stages"
description: "Build text, image, audio, and tabular preprocessing branches that preserve source revisions, validate transformations, and publish only accepted artifacts."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Build multimodal text, image, audio, and tabular preprocessing pipelines with provenance and validation checks.

## Core idea

For an architect composing a multimodal pipeline, the common contract is traceable evidence, not a common file extension. Text normalization, image preparation, transcription, and tabular cleanup change different properties. Each branch must preserve the association between its derived artifact and the exact source material that produced it.

Treat every stage as a transformation with named inputs, outputs, and validation evidence. A joined record becomes eligible for foundation model consumption only when its required branches have completed and their outputs satisfy the task contract. A missing transcript is not an empty transcript, and a generated image description is not the original image.

Use 1.3.3 for extraction-service selection and 1.3.4 for compute selection. This lesson adds the cross-stage contract: how artifacts retain meaning, how failed branches affect the whole record, and what establishes permission to publish a prepared input.

## How it works

### Freeze source identity before transformation

Retain original assets in S3 and identify their exact revisions. In a versioning-enabled bucket, S3 assigns a unique version ID to a stored object; two versions can share the same key. A key alone therefore does not establish which source bytes were processed. Objects that existed before versioning was enabled retain their null version IDs until replaced with versioned writes.

Define an application manifest that records the source bucket, key, version ID, source type, and logical record identity. Add the transform version, configuration, output locations, and validation outcome for each stage. These are application fields, not a claim that S3 automatically generates a transformation graph. The pipeline must write and retain the associations itself.

Use a source revision plus transform configuration to identify intended work. This gives retries a stable target and distinguishes a deliberate reprocessing run from an accidental duplicate. Keep access and domain metadata attached as data passes between branches; see 1.4.5 for the full provenance schema and 3.3.3 for lineage governance.

### Give each modality its own checks

For **text**, preserve the original and record the normalization performed by the processing code. Normalize encoding and whitespace only according to the consumer's requirements. Validate nonempty required content and retain a mapping or the original revision when a later stage refers to source spans. Rewriting text without retaining that association makes extracted offsets and quotations difficult to verify. Meaning-changing enrichment and its independent validation belong to 1.3.10.

For **images**, validate that the declared format matches decodable content, inspect dimensions, and record any resizing or conversion performed by the worker. Preserve the original image and the transformation settings. A smaller derivative can meet an interface limit while making fine print unreadable, so test whether task-relevant detail survives rather than treating file-size compliance as the complete quality gate.

When preparing images for Bedrock Converse, enforce the documented `Message` boundaries: at most 20 images, each at most 3.75 MB and 8,000 pixels in either dimension. Check model support separately. If a scanned document also uses Textract, retain its `Blocks` with `Geometry` and `Relationships` beside the source reference. Do not replace a table's structure with an untraceable description.

For **audio**, validate the media format and actual sample rate before transcription. AWS documents different batch and streaming input contracts and recommends lossless formats. In a batch `StartTranscriptionJob`, a supplied `MediaSampleRateHertz` must match the recording; altering the declared rate does not alter its samples. Retain the original recording and any converted derivative as distinct artifacts.

Track the transcription job separately from the transcript. `GetTranscriptionJob.TranscriptionJobStatus: COMPLETED` indicates that results are available through `TranscriptFileUri`. `FAILED` carries `FailureReason`. Copy or retain the result under your artifact policy, associate it with the recording revision and job name, and validate that required speech content is usable before joining it with other evidence.

For **tabular data**, declare column meanings, types, units, missing-value policy, and row identity before applying cleanup. A processing script can normalize dates or units, but it must not silently convert an unknown unit into an assumed one. Use Glue Data Quality checks such as `ColumnDataType`, `ColumnValues`, `Completeness`, and `RowCount` to test the normalized dataset. See 1.3.1 for threshold policy and 1.3.2 for enforcement.

### Carry branch outcomes into publication

Use a worker appropriate to the branch. `CreateProcessingJob` names the container in `AppSpecification`, input artifacts in `ProcessingInputs`, and output artifacts in `ProcessingOutputConfig`. Write both the prepared artifact and a machine-readable validation result. A successful transformation process must not erase the difference between accepted, rejected, and incomplete data.

Step Functions `Choice` states can route those results. Define an application outcome such as accepted, rejected, or awaiting review, then branch on the validated outcome. `Choices` determines the next state; a `Default` branch handles unmatched cases. Send an unknown or missing result to an explicit failure or review path rather than allowing it to reach publication.

Define required and optional branches per record type. For an audio-only request, an absent image is expected. For a claim whose explanation depends on both a photograph and a statement, a completed photograph branch cannot compensate for failed transcription. Check required-branch completion before creating the consumer-facing manifest.

Do not publish partial outputs merely because their objects exist. Retain intermediate artifacts for diagnosis, then expose an accepted manifest containing only the approved artifact set and its source associations. This is an application publication rule implemented by the workflow, not an automatic guarantee of object storage.

## Key distinctions and trade-offs

Normalization makes representation consistent; extraction derives a structured view; interpretation makes a semantic judgment. Preserve these stages separately so you can repeat or repair one without pretending that the original source changed.

Keeping originals, derivatives, and validation evidence requires more storage and metadata handling. It also lets you identify whether an incorrect answer originated in the source, conversion, transcription, table cleanup, or model interpretation. Retention and access rules still apply to every retained copy; provenance is not a reason to retain sensitive artifacts indefinitely.

Partial acceptance can preserve useful work when a branch is optional. Whole-record rejection is necessary when a failed branch removes required evidence. Express that dependency in the workflow rather than allowing whichever branch finishes first to decide the record's meaning.

## Architecture / decision scenario

A maintenance assistant receives a typed incident description, a damage photograph, an audio inspection note, and a table of sensor readings. Its task requires all four inputs to explain whether further inspection is necessary.

The intake manifest fixes each S3 source revision. The text branch records normalization; the image branch creates a size-compliant derivative and verifies that the damaged component remains visible. The audio branch checks media properties, starts transcription, and admits the transcript only after completion and content validation. The tabular branch normalizes declared units and runs data quality rules over types, allowed ranges, completeness, and record counts.

Each branch records output locations, transform configuration, and its validation result. Step Functions `Choice` logic routes any rejected or missing required result away from publication. If all four pass, the publication step writes an accepted manifest joining those precise artifacts. A later transcription repair creates a traceable replacement result; it does not silently overwrite the evidence behind a previous recommendation.

## Common exam traps

- Treating an S3 key as an immutable source revision.
- Keeping originals while discarding the associations to their derivatives.
- Assuming image size compliance proves that useful detail survived resizing.
- Changing an audio sample-rate parameter without converting the recording.
- Treating an asynchronous job submission as completed preprocessing.
- Publishing a joined record while a required branch is failed or absent.

## What to remember

Use modality-specific transformations and a shared provenance contract. Preserve source revisions, transformation settings, output identities, and validation evidence. Distinguish branch completion from quality acceptance, and make required-branch dependencies determine whether a prepared input can be published.

## References

- AWS, [How S3 Versioning works](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [Data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [GetTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_GetTranscriptionJob.html)
- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [CreateProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateProcessingJob.html)
- AWS, [Choice workflow state](https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html)
