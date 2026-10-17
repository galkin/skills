---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-3"
title: "Choose extraction by the evidence required"
description: "Select Textract, Transcribe, Comprehend, or Bedrock multimodal understanding from the source modality and required evidence contract."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose Amazon Textract for document extraction, Amazon Transcribe for speech, Amazon Comprehend for text entities, or Bedrock multimodal models for image and document understanding.

## Core idea

For an architect selecting an extraction path, the deciding question is what the
next stage must receive. A table with cell relationships, a speech transcript,
a named-entity span, and an interpretation of a diagram are different outputs.
Their source files can overlap, but their evidence contracts do not.

Choose a service for the representation it produces and the uncertainty you can
validate. Use Textract when document structure matters, Transcribe when spoken
content must become text, Comprehend when text needs entity annotations, and a
compatible Bedrock multimodal model when the task requires interpreting visual
or document meaning. Combining paths is reasonable when one artifact needs both
structured extraction and semantic interpretation.

## How it works

### Extract document structure with Textract

Textract `AnalyzeDocument` is synchronous and returns `Blocks` describing detected
content and relationships. `FeatureTypes` selects analysis such as `TABLES`,
`FORMS`, `QUERIES`, `SIGNATURES`, or `LAYOUT`. Detected lines and words are included
even when they are unrelated to the selected feature types.

Choose the feature that matches the evidence requirement. An invoice consumer
that needs row and column relationships should retain table and cell blocks.
Flattening those results into one paragraph can lose which quantity belongs to
which price. Preserve block identifiers, relationships, and location information
instead of asking a downstream model to reconstruct that structure from prose.

For asynchronous document analysis, use `StartDocumentAnalysis` with an S3
`DocumentLocation`. It returns `JobId`; completion can be delivered to the SNS
topic configured in `NotificationChannel`. After a successful completion, retrieve
results with `GetDocumentAnalysis`. A job submission is not extracted evidence.
Pagination and final validation belong to the pipeline design in 1.3.5.

Textract extraction answers where text and document elements occur. It does not
establish whether an invoice is authorized or whether a contract clause should
be accepted. Those are separate source and business validations.

### Turn speech into text with Transcribe

For stored audio, `StartTranscriptionJob` identifies the input through
`Media.MediaFileUri` and requires `TranscriptionJobName`. Choose exactly one of
`LanguageCode`, `IdentifyLanguage`, or `IdentifyMultipleLanguages`. Supplying
more than one of these language-selection parameters makes the job fail.

Use a known language when it is part of the trusted input contract. Use single-
or multiple-language identification when the recording's language content
requires it. The choice should follow the media rather than a desire to set
every available option. A transcription error in a part number or a spoken
negation can change the meaning of the downstream request.

Transcribe owns speech recognition on this path. Keep the original recording
and the transcription result associated with the same source identity. If the
next stage needs named entities or a summary, apply that operation to the
transcript while retaining the distinction between recognized speech and
subsequent interpretation.

### Annotate text with Comprehend

Comprehend `DetectEntities` uses plain text with the pre-trained model. Supply
UTF-8 `Text` and the appropriate `LanguageCode`; the maximum `Text` size is 100 KB.
Its `Entities` output includes `Text`, `Type`, `Score`, `BeginOffset`, and
`EndOffset`. Those spans let your application associate an annotation with the
text that produced it.

The plain-text rule has a scope: custom entity recognition supports additional
input forms. A custom endpoint is selected with `EndpointArn`, and Comprehend
uses that model's language rather than a supplied language code. Do not infer
that every `DetectEntities` configuration accepts document bytes, or that
Comprehend universally requires Textract before it can analyze documents.

If you split a large text input, preserve a mapping from each segment's offsets
to the original text. Normalizing the text after entity detection without updating
that mapping can make a correct annotation point to the wrong source span.
See 1.3.10 for enrichment and validation of transformed content.

### Interpret visual meaning with Bedrock

A Bedrock multimodal model is appropriate when the question depends on meaning
such as a diagram's flow, the relationship between an image and a caption, or
a document's explanation. Check the selected model's Converse feature support;
sharing the API does not give every model image or document capabilities.

The Converse `Message` contract permits up to 20 images per message, each no
larger than 3.75 MB and 8,000 pixels in either dimension. It permits up to five
documents, each no larger than 4.5 MB. Images and documents belong in `user`
messages, and a document block requires a text block in the content array.
These interface ceilings do not override model-specific support.

A model-generated interpretation needs validation against the source. It can
produce a useful explanation while omitting a table row or misreading a label.
For a task that requires exact table values and a narrative explanation, retain
Textract's structured evidence and validate the model's narrative against it.
The service choice should preserve the evidence the business decision needs.

## Key distinctions and trade-offs

The following choices turn on the required result:

| Required result                   | Primary path                        | Evidence to preserve                         |
| --------------------------------- | ----------------------------------- | -------------------------------------------- |
| Form fields or table structure    | Textract document analysis          | Blocks and their relationships               |
| Spoken content as text            | Transcribe transcription            | Recording identity and transcript            |
| Named entities in text            | Comprehend entity detection         | Text spans, types, and scores                |
| Visual or document interpretation | Compatible Bedrock multimodal model | Source artifact and validated interpretation |

Specialized extraction makes its output contract explicit. Generative
interpretation offers broader task expression but adds answer-validation work.
A single multimodal prompt can reduce application steps while concealing which
stage lost evidence. Multiple services expose clearer boundaries but require
correlation, intermediate storage, and independent acceptance checks.

Confidence scores are signals from different tasks. Do not apply one threshold
to Textract extraction, Comprehend entity recognition, and model-generated claims
as though the values measured the same event.

## Architecture / decision scenario

A maintenance assistant receives a scanned inspection form, a technician's voice
memo, a typed incident report, and a photograph of a wiring diagram. The form
requires exact field and table relationships, so the pipeline selects Textract
with `FORMS` and `TABLES` rather than relying on a narrative summary.

The voice memo goes to `StartTranscriptionJob` with the appropriate language
selection. The incident report goes to pre-trained `DetectEntities` after text
size and language checks. A compatible Bedrock model receives the diagram image
and an explicit interpretation request within the Converse message limits.

The assistant keeps all four source identities. It checks that a component name
from the transcript or entity result refers to the same component shown in the
inspection evidence. If the diagram interpretation conflicts with the extracted
form, the application preserves the conflict for review instead of selecting the
most fluent answer. Each modality has a primary extraction path and a separate
acceptance decision.

## Common exam traps

- Choosing a narrative answer when the requirement is exact table relationships.
- Sending raw audio to a text entity detector.
- Setting multiple mutually exclusive Transcribe language-selection parameters.
- Assuming every Bedrock Converse model supports images and documents.
- Treating extraction confidence as proof of business correctness.

## What to remember

Select the output contract before the service. Textract extracts document
structure, Transcribe recognizes speech, Comprehend annotates entities, and
compatible Bedrock models interpret multimodal meaning. Preserve source evidence
and validate the result of each transformation.

## References

- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [StartDocumentAnalysis](https://docs.aws.amazon.com/textract/latest/APIReference/API_StartDocumentAnalysis.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [DetectEntities](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
