---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-3"
title: "Choose extraction by the required evidence"
description: "Select Textract, Transcribe, Comprehend, or Bedrock multimodal inference from the input modality and the evidence contract your application needs."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose Amazon Textract for document extraction, Amazon Transcribe for speech, Amazon Comprehend for text entities, or Bedrock multimodal models for image and document understanding.

## Core idea

For an architect choosing an extraction path, the deciding question is what artifact the next stage must receive. A document's table cells, a recording's spoken words, the organizations mentioned in text, and an explanation of an image are different outputs. Select the service whose documented interface matches the required evidence.

These services can form a sequence. Transcribe can produce text that Comprehend analyzes, while Textract can produce document structure that a Bedrock model interprets. The model's ability to accept the original file does not remove the need for traceable extraction when a downstream process requires exact fields or source locations.

## How it works

### Extract document structure with Textract

Use `AnalyzeDocument` for synchronous analysis of relationships among detected document items. Its `FeatureTypes` values include `TABLES`, `FORMS`, `QUERIES`, `SIGNATURES`, and `LAYOUT`. Select the feature that matches the required output rather than asking for an undifferentiated text description.

Textract returns `Blocks`. Tables and cells appear as related blocks; form fields use key and value `KEY_VALUE_SET` blocks. Lines and words are returned even when they do not relate to the requested feature types. Block fields include `Id`, `BlockType`, `Relationships`, `Geometry`, `Text`, and `Confidence`. Preserve relationships and geometry when the consumer needs to locate a value in the original document. Flattening everything into a string discards that contract.

For asynchronous document analysis, use `StartDocumentAnalysis` with `DocumentLocation` pointing to an S3 object. It returns `JobId`. The documented completion path publishes status to the SNS topic specified in `NotificationChannel`; after `SUCCEEDED`, use `GetDocumentAnalysis` with that job identifier. Starting the job is not receiving its extracted evidence. Choose this path when the document workflow needs asynchronous analysis rather than keeping the caller open for a synchronous result.

### Transcribe speech before analyzing its meaning

`StartTranscriptionJob` transcribes audio from a media file in S3. Supply `TranscriptionJobName`, `Media.MediaFileUri`, and exactly one of `LanguageCode`, `IdentifyLanguage`, or `IdentifyMultipleLanguages`. Sending multiple language-selection parameters makes the job fail; they are alternative strategies, not additive hints.

`GetTranscriptionJob` exposes `TranscriptionJobStatus`. A `COMPLETED` job provides its result location through `TranscriptFileUri`; a `FAILED` job provides `FailureReason`. Retrieve and validate the transcript before using it as model context. An accepted job request provides neither a completed transcript nor proof that the spoken content was captured accurately.

Choose the media preparation path deliberately. AWS documents different accepted formats for batch and streaming transcription and recommends lossless audio. Batch transcription can use WAV with PCM 16-bit encoding; streaming PCM does not mean a WAV container is accepted. If you supply `MediaSampleRateHertz` for a batch job, it must match the file's actual sample rate. Changing a parameter is not resampling the audio.

### Locate entities in text with Comprehend

Use `DetectEntities` when you need identified entities rather than a free-form explanation. For plain text, supply `Text` and a supported `LanguageCode`. The text must be UTF-8 and is limited to 100 KB. This limit is a byte-size boundary, not permission to send 100,000 arbitrary Unicode characters.

The `Entities` collection supplies the detected text, type, confidence `Score`, and `BeginOffset` and `EndOffset`. Retain the analyzed text revision with these offsets. If another stage rewrites the text first, offsets from the original analysis no longer identify spans in the rewritten artifact.

`EndpointArn` selects a custom entity recognition model. Without it, Comprehend detects its default entity types; it does not invent a business-specific taxonomy from your field names. The custom-model path also determines the model language and ignores a supplied language code. See 1.3.10 for enrichment and validation after extraction.

### Interpret images and documents with Bedrock

Use a supported multimodal Bedrock model when the task requires interpretation, such as explaining an equipment photograph or combining a diagram with surrounding text. Through `Converse`, `messages[].content` carries content blocks such as `image` or `document`. Model support varies; the existence of a content-block type does not mean every `modelId` accepts it.

The Converse `Message` contract permits up to 20 images, each no larger than 3.75 MB and 8,000 pixels in either dimension, and up to five documents of 4.5 MB each. Images and documents belong in user messages, and a document requires an accompanying text block. These interface restrictions sit alongside model-specific capabilities; see 1.3.6 for the full request contract.

`DocumentBlock.name` also needs care. AWS warns that a model can interpret the name as instructions and recommends a neutral name. Keep externally supplied filenames out of that instruction-like role. Retain the actual source identity in application provenance instead of relying on a model-facing display name to establish it.

## Key distinctions and trade-offs

The following output contracts guide selection:

| Required artifact                  | Primary choice                     | Evidence to preserve                                                      |
| ---------------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| Form fields or table relationships | Textract document analysis         | Block identities, relationships, geometry, and source document            |
| Spoken words from recorded media   | Transcribe batch transcription     | Job identity, transcript artifact, and original recording                 |
| Typed entity mentions in text      | Comprehend `DetectEntities`        | Entity spans, scores, and analyzed text revision                          |
| Image or document interpretation   | Supported Bedrock multimodal model | Source asset, prompt and model configuration, and reviewed interpretation |

Confidence fields do not share a universal acceptance scale or business meaning. A detected entity with a high score is not proof that its claim is true. A plausible visual explanation is not a substitute for the exact cell relationships a financial reconciliation requires. Validate the artifact against the consuming task.

## Architecture / decision scenario

An equipment-claims assistant receives scanned invoices, recorded technician statements, damage photographs, and typed incident notes. It must explain each recommendation from retained evidence.

The invoice path uses Textract `TABLES` and `FORMS`, retaining block relationships for amounts and identifiers. Its asynchronous path waits for analysis completion before obtaining results. The recording path uses `StartTranscriptionJob` with the chosen language strategy, then checks `GetTranscriptionJob` before admitting the transcript.

Comprehend analyzes entity mentions in the typed notes and the accepted transcript. Its offsets remain tied to those exact text artifacts. A supported Bedrock multimodal model interprets damage photographs and relevant document context, using neutral document names. The application compares its interpretation with the extracted claim facts before accepting a recommendation. No branch treats service completion or fluent generated prose as proof of evidentiary correctness.

## Common exam traps

- Choosing an image explanation when the consumer needs table cells and relationships.
- Treating `StartDocumentAnalysis` or `StartTranscriptionJob` as a completed result.
- Sending multiple Transcribe language-selection strategies in one request.
- Treating Comprehend's plain-text size limit as a character count.
- Assuming a built-in entity detector recognizes every business-specific entity type.
- Assuming all Bedrock models accept every Converse content block.

## What to remember

Select the service from the required output and its evidence contract. Textract preserves document structure, Transcribe produces speech transcripts, Comprehend locates typed mentions, and supported Bedrock multimodal models interpret content. Preserve each stage's source association and validate its output before the next stage consumes it.

## References

- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [StartDocumentAnalysis](https://docs.aws.amazon.com/textract/latest/APIReference/API_StartDocumentAnalysis.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [GetTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_GetTranscriptionJob.html)
- AWS, [Data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- AWS, [DetectEntities](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [DocumentBlock](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html)
