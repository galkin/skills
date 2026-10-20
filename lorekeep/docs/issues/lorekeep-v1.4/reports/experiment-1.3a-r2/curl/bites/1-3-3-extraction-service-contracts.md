---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-3"
title: "Choose extraction by the evidence required"
description: "Choose Textract, Transcribe, Comprehend, or a Bedrock multimodal model from the input modality and required evidence contract."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose Amazon Textract for document extraction, Amazon Transcribe for speech, Amazon Comprehend for text entities, or Bedrock multimodal models for image and document understanding.

## Core idea

Start with the evidence your downstream consumer needs. A table cell with its document location, a word with its audio timestamp, a named entity with its text offsets, and an explanation of a diagram are different outputs. Choose the service whose output contract fits the task, then validate that output before a foundation model consumes it.

These services can form successive stages. Transcribe can produce text for Comprehend; Textract can produce document text for subsequent enrichment. A Bedrock multimodal model can answer a visual question, but an answer alone does not replace the extraction evidence needed to audit a particular field.

## How it works

### Use Textract for document structure

Amazon Textract `AnalyzeDocument` analyzes relationships between detected document items. Set `FeatureTypes` to select the required analysis: `TABLES`, `FORMS`, `QUERIES`, `SIGNATURES`, or `LAYOUT`. The response contains `Block` objects, including detected lines and words, together with structures for the requested features.

For form data, key and value blocks use `KEY_VALUE_SET`. Tables have `TABLE` and `CELL` blocks. `Relationships` connects blocks; `Geometry` and `Confidence` provide location and confidence evidence. Preserve these fields when the consumer must trace an extracted amount to a source region. Flattening everything into text discards relationships that explain whether a number is a subtotal, a line item, or a field value.

`AnalyzeDocument` is synchronous. Use `StartDocumentAnalysis` for asynchronous document analysis. The limits make this a concrete choice: synchronous PDF and TIFF inputs are limited to one page and 10 MB; asynchronous PDF and TIFF inputs support up to 3,000 pages and 500 MB. Asynchronous JPEG and PNG inputs retain a 10 MB limit. These are service limits, not recommended operating sizes.

Check source eligibility before invoking extraction. Textract does not support password-protected PDFs or XFA-based PDFs. A larger retry budget cannot repair an unsupported source. Route it for an approved conversion or request a supported replacement, retaining the relationship to the original.

### Use Transcribe for speech evidence

Amazon Transcribe converts audio to text. For a stored recording, `StartTranscriptionJob` takes `Media.MediaFileUri`, a unique `TranscriptionJobName`, and a language selection. Specify exactly one of `LanguageCode`, `IdentifyLanguage`, or `IdentifyMultipleLanguages`. Single-language identification and multiple-language identification are separate choices; combining those selectors causes the job to fail.

If you supply `MediaSampleRateHertz`, it must match the detected sample rate. For batch transcription, you can omit it and let Transcribe determine the rate. Do not change only the declared rate while leaving the underlying audio unchanged.

Choose `OutputBucketName` and, when needed, `OutputKey` for your output location. `OutputBucketName` takes a bucket name, not an `s3://` URI. The service needs permission to write to the destination.

Transcription JSON contains paragraph text and word-level evidence. In `items`, spoken-word entries include `start_time`, `end_time`, and `alternatives` with `confidence` and `content`. Retain those associations for replay and review. Punctuation entries are distinct from spoken-word entries; do not assume every item has a meaningful audio duration.

Batch and streaming media support differ. For example, batch supports MP3, while the documented streaming formats are FLAC, Ogg Opus, and PCM. Choose the ingestion mode before choosing an encoding. A file extension accepted for a stored recording does not establish streaming compatibility.

### Use Comprehend for text entities

Amazon Comprehend `DetectEntities` detects named entities with a pretrained model or custom entities with a custom model. For pretrained named-entity detection, provide plain text through `Text` and select a supported `LanguageCode`. `Text` is a UTF-8 string with a maximum size of 100 KB.

The response's `Entities` entries contain the detected `Text`, `Type`, `Score`, `BeginOffset`, and `EndOffset`. Preserve the exact text version used for detection. Normalizing the text afterward without an offset mapping can make the saved positions point to different characters.

Do not generalize the plain-text requirement to every Comprehend path. Custom entity recognition supports additional document inputs under its documented conditions. `EndpointArn` selects a custom entity recognition endpoint; with that endpoint, Comprehend uses the custom model's language and ignores the supplied language code. The service's presence in a pipeline does not mean arbitrary entities or languages are supported.

### Use multimodal models for visual interpretation

Choose an eligible Bedrock multimodal model when the task requires interpreting an image or relating document content to a question, such as explaining a diagram's relationship to nearby prose. With `Converse`, `modelId` selects the model or inference target and `messages` carries the input. The API supplies a consistent interface for models that support messages; it does not erase model-specific capabilities.

Call `GetFoundationModel` and inspect `modelDetails.inputModalities` for `IMAGE` when checking image input. The documented enum is `TEXT | IMAGE | EMBEDDING`; it has no `DOCUMENT` value. Check document input separately against the selected model's documented support for the Converse `document` content block, using the model cards identified in AWS's Converse guide. Neither the absence of `DOCUMENT` nor the presence of `IMAGE` decides document support. Keep the model identifier, question, source identity, and generated result in your application evidence. Treat the interpretation as generated output that needs independent checks, especially when an answer turns on a consequential value. Detailed message construction belongs to 1.3.6, and enrichment validation to 1.3.10.

## Key distinctions and trade-offs

**Extraction versus interpretation:** Textract exposes document relationships; Transcribe exposes speech-to-text evidence; Comprehend exposes entity spans. A multimodal answer can explain meaning but needs its own verification contract.

**Confidence versus correctness:** A service confidence field measures its detection signal. It does not prove that an amount is the business value requested or that a statement is authoritative. Set review policies from representative errors rather than assuming one cutoff transfers across services.

**One service versus composition:** Choose the smallest set of stages that preserves the evidence required. Adding Comprehend after transcription is useful when entity spans are required; it is unnecessary if the consumer only needs a transcript.

## Architecture / decision scenario

A claims assistant receives a multipage form, a recorded customer statement, a typed note, and a damage photograph. The form needs table cells and field relationships, so the team uses asynchronous Textract analysis with `TABLES` and `FORMS`. Its page count rules out synchronous `AnalyzeDocument`.

The recording enters a Transcribe batch job with the appropriate language selector. The pipeline retains word timestamps for review. The typed note enters pretrained Comprehend `DetectEntities` as text, retaining entity offsets against that exact note revision.

A selected Bedrock multimodal model interprets visible damage in the photograph against the user's question. Its description remains a separate derived assertion. A consistency check compares extracted claim identifiers across the branches, and disputed amounts go to review with their page regions or audio timestamps.

The design does not force four different outputs into an untraceable summary. Each branch produces the evidence required by its task before the assistant assembles an answer.

## Common exam traps

- Sending a multipage PDF to synchronous `AnalyzeDocument`.
- Selecting Comprehend for speech-to-text conversion.
- Combining multiple Transcribe language selectors.
- Assuming batch audio formats also work for streaming.
- Treating Comprehend offsets as valid after changing the source text.
- Treating a multimodal model's explanation as a verified extracted field.
- Reading `IMAGE` as proof of document support, or the missing `DOCUMENT` enum as proof of its absence.

## What to remember

Choose by the required output: document blocks, timestamped speech, entity spans, or visual interpretation. Check the selected operation's limits and preserve its evidence before applying downstream validation.

## References

- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [Set quotas in Amazon Textract](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [Data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- AWS, [DetectEntities](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- AWS, [GetFoundationModel](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_GetFoundationModel.html)
- AWS, [FoundationModelDetails](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_FoundationModelDetails.html)
