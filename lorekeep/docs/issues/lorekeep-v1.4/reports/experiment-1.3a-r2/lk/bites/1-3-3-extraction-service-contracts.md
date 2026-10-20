---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-3"
title: "Choose extraction by the required evidence"
description: "Choose document, speech, entity, or multimodal processing from the evidence structure the application must retain."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose Amazon Textract for document extraction, Amazon Transcribe for speech, Amazon Comprehend for text entities, or Bedrock multimodal models for image and document understanding.

## Core idea

Choose the service from the output contract you need, not merely the file extension. A scanned invoice can require table cells and form fields, named entities in extracted text, or an explanation of a visual relationship. These are different tasks even when the source object is identical.

Amazon Textract provides document analysis structures. Amazon Transcribe turns speech into a transcript. Amazon Comprehend identifies entities in text using a predefined or custom recognition model. A supported Amazon Bedrock multimodal model can interpret images and documents in a prompted task. Combine services when one stage's explicit output is another stage's input, and validate each boundary.

This lesson chooses the extraction mechanism. Enrichment validation belongs to 1.3.10, request construction to 1.3.6, and the complete provenance pipeline to 1.3.5.

## How it works

### Extract document structure with Textract

Textract `AnalyzeDocument` analyzes relationships between detected document items. The required `FeatureTypes` list chooses `TABLES`, `FORMS`, `QUERIES`, `SIGNATURES`, or `LAYOUT`. The response contains `Block` objects. Table analysis returns table and cell blocks; form analysis returns related key and value blocks of type `KEY_VALUE_SET`.

All detected lines and words appear in the response, including text unrelated to the selected feature types. Therefore, selecting `TABLES` does not mean the output is only table text. Your transformation must select and connect the relevant blocks rather than concatenate everything and assume table relationships survived.

`AnalyzeDocument` is synchronous, with a maximum document size of 10 MB. AWS directs asynchronous document analysis to `StartDocumentAnalysis`; asynchronous operations support PDF files up to 500 MB. Choose the execution path from both the required analysis and the applicable size boundary. Format acceptance alone does not establish that a document fits the synchronous path.

Use Textract when downstream checks need extracted structure: a form label paired with its value, a cell associated with a table, or a signature location. Signature detection establishes a detected signature's location; your application must separately decide what evidence establishes approval or authenticity.

### Transcribe speech with Transcribe

For file transcription, upload the media to Amazon S3 and call `StartTranscriptionJob`. Identify it with `TranscriptionJobName` and pass its location in `Media.MediaFileUri`. Select exactly one of `LanguageCode`, `IdentifyLanguage`, or `IdentifyMultipleLanguages`; AWS documents that supplying more than one causes the job to fail.

`IdentifyLanguage` is for media containing one language. `IdentifyMultipleLanguages` handles media containing multiple languages. That distinction concerns the media's language content, not how many languages the application supports across all customers.

If you specify `MediaSampleRateHertz`, it must match the detected media rate or the job fails. The documented range is 8,000–48,000 Hz. Avoid treating an invented sample-rate value as a quality repair: it describes the media, and changing the request field does not reconstruct missing audio information.

Choose `OutputBucketName` and `OutputKey` when the design requires a controlled transcript output location. The bucket field takes a bucket name, not an `s3://` URI. A transcript is the extracted representation of speech; product acceptance still needs checks against the source and task.

### Identify text entities with Comprehend

Choose pretrained `DetectEntities` for named entities in plain text, or select a custom entity recognizer through `EndpointArn` when the task requires your custom entity categories. AWS also documents document inputs for eligible custom models; do not generalize that support to the pretrained plain-text path.

Entity recognition labels mentions in the source. It does not replace speech transcription or the prompted visual interpretation assigned to the other branches here. For the input contract, entity response fields, and offset handling, see 1.3.10.

### Interpret visual evidence with Bedrock

The Bedrock Converse interface represents message content using content blocks. Its inference guide describes `image` and `document` inputs and directs you to model-specific capability information to determine supported blocks. Choose a target whose documented modalities match the task; a common API does not make all models multimodal.

A document block must be accompanied by a related text prompt in the message's content. This gives the model the task to perform on the document. Exact block construction belongs to 1.3.6; here the decision is whether you need prompted interpretation, such as explaining a diagram, rather than an extraction structure defined by a specialized API.

Validate the resulting claims against the source. A fluent visual explanation is a generated interpretation, and its wording alone does not establish that every extracted quantity or relationship is correct. For evidence-sensitive workflows, preserve the source and compare the necessary fields or relationships with reviewed expectations.

## Key distinctions and trade-offs

**Structure versus interpretation:** Textract's table and form blocks support explicit structural processing. A multimodal model supports a prompted understanding task. Do not replace a required cell-to-table relationship with an unverified narrative description.

**Transcription versus entity recognition:** Transcribe produces text from speech. Comprehend identifies entities in text. A conversation recording that needs organization names can use both stages, with source identity retained across the handoff.

**Service output versus business truth:** An entity score, a detected signature, and a generated explanation each have a particular meaning. None independently establishes that a transaction is correct or authorized.

**Pretrained versus custom scope:** Comprehend's pretrained plain-text contract and eligible custom document contract differ. Likewise, Bedrock modality support depends on the chosen model rather than the existence of a content-block field.

## Architecture / decision scenario

An equipment-support assistant receives a maintenance form, a technician's recording, an incident description, and a photograph of a control panel. The requested answer must reconcile a serial number, the reported fault, and the photographed switch position.

The team chooses Textract `AnalyzeDocument` with `FORMS` and `TABLES` for the form's labeled fields and service-history table. It uses `StartTranscriptionJob` for the recording, selecting one language strategy and preserving the transcript's S3 location. `DetectEntities` identifies named organizations and places in the incident text; it does not transcribe the recording or establish the equipment's condition.

A supported Bedrock multimodal target interprets the panel image with a task prompt. The application compares the relevant generated observation with reviewed visual evidence before allowing a consequential recommendation. It joins all outputs through the case and source revision, and flags disagreement instead of asking one service to silently overwrite another. The choice covers all four mechanisms while preserving their different evidentiary roles.

## Common exam traps

- Selecting one service solely because the source is a PDF.
- Treating Textract feature selection as a filter that removes unrelated text blocks.
- Supplying multiple Transcribe language-selection parameters.
- Choosing entity recognition when the required output is a speech transcript.
- Assuming every Bedrock target supports image and document blocks.
- Treating detected entities or signatures as proof of business correctness.

## What to remember

Choose Textract for document structures, Transcribe for speech transcription, Comprehend for entity recognition, and a supported Bedrock multimodal target for prompted visual or document interpretation. Preserve each stage's evidence contract and validate the business meaning after extraction.

## References

- AWS, [AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
- AWS, [StartTranscriptionJob](https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html)
- AWS, [DetectEntities](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
