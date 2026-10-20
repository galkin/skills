# Verdict — group 1.3a, drafts X and Y

Severity scale, applied identically to both drafts:

- `blocking` — a wrong fact, or a core mechanism of the objective left unnamed.
- `should-fix` — a deciding number or a mechanism an exam option would print is missing, or the
  brief's contract is broken (reference count, word range, re-teaching a neighbour at length).
- `nit` — an unverified side claim, a short repeat of a neighbour, or a citation title mismatch.

Every finding was checked against the stored AWS page through `lorekeep get --tag aws`. Prose word
counts (frontmatter and references excluded) are all inside 900–1,400. No timeless-wording
violations in either draft (`latest` appears only inside URLs).

Quick Diagnostic scoring: all ten Bites are concept pages built on the same fixed skeleton, so
rows 1 (outcome in the opening: Learning objective plus Core idea), 2 (doc type), 4 (headings),
5 (no procedures), 6 (no code samples), 7 (voice), 8 (links and tables), 9 (timeless) and 10 (word
list) pass for every draft. Row 3 — every behaviour verified — is the only row that varies.

## 1.3.1 — FM input quality thresholds

**Verified in both (sample):** `Completeness` = share of non-null values; `IsComplete` = 100 %
complete; `EMPTY` and `WHITESPACES_ONLY` are `ColumnValues` keywords; `ReferentialIntegrity`,
`DatasetMatch` (column mapping), `CustomSql`, `ColumnDataType`, `ColumnLength` as described; the
rule-type table lists row-level support separately.

X (`X/1-3-1-fm-input-quality-gates.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| nit | :50 | Lists the `Message` limits (20 images, 3.75 MB, 8000 px; 5 documents, 4.5 MB) correctly, but omits the same page's scope that images and documents are allowed only when `role` is `user`. | https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html |
| nit | :28 | Explains non-null versus blank but not the documented CSV behaviour, where a blank string column becomes `""` and passes `Completeness` while a blank `Int` becomes NULL and fails. Y prints it. | https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-Completeness.html |

Y (`Y/1-3-1-fm-input-quality-gates.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| nit | :46, :66 | "For a supported Bedrock target, `CountTokens`…": the qualifier is unverified, because the page names no list of supported models. `modelId` → `inputTokens` and model-specific tokenisation are correct. | https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CountTokens.html |

Y also verified: CSV blank-string/`Int` behaviour (:28); `compositeRuleEvaluation.method` = `ROW`
(:28); `RowCount`/`RowCountMatch`/`SchemaMatch` (:30, :34); "DQDL does not support nested or
list-type column data" (:42, from the rule-type reference note).

Quick Diagnostic: **X 10/10, Y 10/10.**

**Better: Y.** Both are accurate, but Y names more of the mechanisms an exam option would print
(CSV blank behaviour, row-mode composite evaluation, count rules, the nested-data limit,
`CountTokens` for a size gate). X's distinctive item, the `Message` interface limits, is correct
but is a request-format fact that also appears in X's 1.3.5.

## 1.3.2 — Glue Data Quality, Data Wrangler, Lambda metrics

**Verified in both (sample):** 50 K = first 50,000 imported rows; Entire dataset runs a SageMaker
Processing job; the report covers missing and invalid values, feature types and outlier counts;
`Invocations` include function errors and exclude throttles; `Errors` include runtime timeouts;
`Duration` is in milliseconds; `PutMetricData` takes `Namespace`, `MetricData`, `MetricName`,
`Value` and `Dimensions`.

X (`X/1-3-2-input-profiling-evidence.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :44, :68 | "A failed required-code rule holds the affected release", but X never names the Glue mechanism that does it. Glue Studio's **On ruleset failure** (default **None**, then **Fail job after loading data to target** and **Fail job without loading to target data**) is the documented enforcement switch and a natural exam distractor. | https://docs.aws.amazon.com/glue/latest/dg/tutorial-data-quality.html |
| nit | :26, :28 | "the report controls described below are scoped to Studio Classic": unverified. The insights page does not say this. The Canvas page says only that Data Wrangler moved from Studio Classic to Canvas. | https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-data-insights.html, https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-data-prep.html |

X also verified: `EvaluateDataQuality` output columns `Rule`/`Outcome`/`FailureReason`/
`EvaluatedMetrics` (:36); `enableDataQualityCloudWatchMetrics` default False,
`dataQualityEvaluationContext` default `default_context`, `enableDataQualityResultsPublishing`
default True (:40); `Duration` supports `p95` (:48); `AllStatistics` is an analyzer and
`ColumnExists` returns no row-level results (:42).

Y (`Y/1-3-2-input-profiling-evidence.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| nit | :88 | The reference title "Types of metrics for Lambda functions" does not match the page title "Types of metrics for Lambda Event Functions". | https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html |

Y also verified: the three **On ruleset failure** options and their behaviour (:38);
`DataQualityEvaluationResult` `Passed`/`Failed` per row, where a row can pass while `RowCount`
fails (:36); composite `ROW` via `additionalOptions` in `processRows`, and the exclusions
`Completeness`, `DatasetMatch`, `ReferentialIntegrity` and `Uniqueness` plus `with threshold` on
`ColumnDataType`/`ColumnValues`/`CustomSQL` (:40); `Duration` excludes cold start (:44).

Quick Diagnostic: **X 9/10** (row 3: the unverified Studio Classic scoping), **Y 10/10.**

**Better: Y.** Y names the Glue switch that turns a failed rule into a stopped load and the
row-versus-dataset result field. X's publishing-option defaults are a real strength, but its
scenario relies on a "hold" whose mechanism it never prints.

## 1.3.3 — Textract, Transcribe, Comprehend, Bedrock multimodal

**Verified in both (sample):** `AnalyzeDocument` is synchronous, and `StartDocumentAnalysis` is
the asynchronous path; `FeatureTypes` takes `TABLES | FORMS | QUERIES | SIGNATURES | LAYOUT`;
`KEY_VALUE_SET`; exactly one of `LanguageCode`/`IdentifyLanguage`/`IdentifyMultipleLanguages`,
otherwise the job fails; `MediaSampleRateHertz` must match the detected rate; `OutputBucketName`
takes no `s3://`; `EndpointArn` makes Comprehend ignore the language code; a `DocumentBlock` needs
a related `text` prompt.

X (`X/1-3-3-extraction-service-contracts.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :92–99 | Eight references, against the brief's 2–5 (sometimes 6). `GetFoundationModel` and `FoundationModelDetails` could share one entry, and the two Textract pages could too. | docs/pipeline/briefs/aws-aip/author.md (contract) |
| nit | :40 | Separates punctuation from spoken-word items but does not print the field that does it: `type` = `pronunciation` \| `punctuation`. | https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html |

X also verified: synchronous PDF/TIFF are limited to 1 page and 10 MB; asynchronous PDF/TIFF to
3,000 pages and 500 MB; asynchronous JPEG/PNG to 10 MB (:28); no password-protected and no XFA PDFs
(:30); batch supports MP3, while streaming supports FLAC, Ogg Opus and PCM (:42); Comprehend
`Text` is UTF-8 with a maximum of 100 KB (:46); `inputModalities` enum `TEXT | IMAGE | EMBEDDING`
(:56).

Y (`Y/1-3-3-extraction-service-contracts.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :30, :72 | Gives the 10 MB synchronous size limit but not the deciding limit: synchronous PDF/TIFF are limited to **1 page**, and asynchronous ones to 3,000 pages. The scenario sends a form with a service-history table to synchronous `AnalyzeDocument` without checking page count. | https://docs.aws.amazon.com/textract/latest/dg/limits-document.html |
| should-fix | :52, :82 | "Choose a target whose documented modalities match" names no mechanism to check them. `GetFoundationModel` → `modelDetails.inputModalities` exists for images. | https://docs.aws.amazon.com/bedrock/latest/APIReference/API_FoundationModelDetails.html |
| should-fix | :46–48 | The Comprehend branch prints only `DetectEntities` and `EndpointArn`. It defers the input contract and response fields (`Text` ≤ 100 KB UTF-8; `Entities` with `Type`, `Score`, `BeginOffset`, `EndOffset`) to 1.3.10, which leaves this objective's "Comprehend for text entities" clause without its deciding limit. | https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectEntities.html |

Y also verified: "All detected lines and words appear… including text unrelated to the selected
feature types" (:28, quoted almost verbatim); `MediaSampleRateHertz` range 8,000–48,000 (:40);
asynchronous PDF up to 500 MB (:30).

Quick Diagnostic: **X 10/10, Y 10/10.**

**Better: X.** X prints the deciding Textract page and size limits, the batch-versus-streaming
audio formats, Comprehend's input limit and output fields, and the API that checks modality. Y is
accurate but thinner on exactly the numbers and identifiers a selection question turns on. X's
only real defect is a padded reference list.

## 1.3.4 — SageMaker Processing versus Lambda

**Verified in both (sample):** `CreateProcessingJob` with `AppSpecification`, `ProcessingInputs`,
`ProcessingOutputConfig` and `ProcessingResources.ClusterConfig`; `DescribeProcessingJob`
`ProcessingJobStatus` = `InProgress | Completed | Failed | Stopping | Stopped`, plus
`FailureReason`; Lambda timeout 900 s, with the Managed Instances exception of 5,400 s for
asynchronous and event-source-mapping invocations except MQ/DocumentDB; memory 128–10,240 MB;
`/tmp` 512–10,240 MB; payload 6 MB synchronous and 1 MB asynchronous.

X (`X/1-3-4-preprocessing-compute-boundaries.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :36, :70 | Sets `StoppingCondition.MaxRuntimeInSeconds` but never gives its ceiling, **777,600 s (9 days)**, the deciding number on the Processing side of a runtime comparison. | https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingStoppingCondition.html |

X also verified: `S3DataType` = `S3Prefix | ManifestFile`; `S3InputMode` `File` copies to the
local volume, `Pipe` streams; `LocalPath` must begin with `/opt/ml/processing/` (required when
`AppManaged` is False, the default); `S3DataDistributionType` = `FullyReplicated | ShardedByS3Key`
(:30–34); same-bucket S3 trigger loop, avoided with two buckets or an incoming prefix (:48).

Y (`Y/1-3-4-preprocessing-compute-boundaries.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| nit | :50 | Re-teaches `Duration`/`Errors`/`Throttles` semantics that 1.3.2 owns (LESSONS #8). Correct, but it should name 1.3.2. | https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html |
| nit | :94 | Reference title "Types of metrics for Lambda functions" does not match the page title ("…Lambda Event Functions"). | same |

Y also verified: `MaxRuntimeInSeconds` range 1–777,600 (:32); Athena and Redshift as alternative
input sources (:28); `InstanceCount`/`InstanceType`/`VolumeSizeInGB` in `ClusterConfig` (:26);
`Duration` excludes cold start (:50).

Quick Diagnostic: **X 10/10, Y 10/10.**

**Better: Y.** The objective is a choice between two runtime envelopes, and Y puts both ceilings
side by side (15 min / 90 min Managed Instances versus 9 days). X gives more Processing input
detail (`Pipe`, `ShardedByS3Key`, manifest), which is useful, but omits the Processing-side number
the decision turns on.

## 1.3.5 — Multimodal preprocessing with provenance and validation

**Verified in both (sample):** the S3 event carries `eTag` and `versionId` (null or absent without
versioning); the object key is URL-encoded (`red flower.jpg` → `red+flower.jpg`); `sequencer` is
present for PUT and DELETE only, compared after left-padding with zeros, and never across keys;
notifications are not guaranteed to arrive in order; Textract `Block` relationships.

X (`X/1-3-5-multimodal-preprocessing-lineage.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :42–48 | The image branch checks size and pixel limits but never the format contract: `ImageBlock.format` accepts only `png \| jpeg \| gif \| webp`, so a TIFF or HEIC source needs a derived, converted artifact. That is the concrete preprocessing step this objective's image clause implies. | https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html |
| nit | :46 | Repeats the `Message` image limits that X's own 1.3.1 already teaches. Correct, but a neighbour repeat (LESSONS #8). | https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html |

X also verified: Transcribe supports single- and dual-channel media, FLAC for both batch and
streaming (:52); `start_time`/`end_time`/`confidence` (:54); `DocumentBlock.format` includes
`csv`, `xls`, `xlsx` (:64); the `DocumentBlock.name` prompt-injection warning and the advice to use
a neutral name (:70); `IsPrimaryKey`, `ColumnExists` (:62).

Y (`Y/1-3-5-multimodal-preprocessing-provenance.md`)

| Severity | Where | Claim | Source |
|---|---|---|---|
| should-fix | :40, :72 | The audio branch records `TranscriptionJobName` and the output location but names no validation evidence for the transcript or the source audio: no channel or format check, and no `start_time`/`end_time`/`confidence`. "Validate the derived transcript's required content" stays abstract where AWS documents the fields. | https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html |
| nit | :42 | Repeats the DQDL nested/list-type limitation already taught in Y's 1.3.1. | https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html |

Y also verified: `ImageBlock.format` = `png | jpeg | gif | webp` (:38); a document block needs a
related text prompt (:56); `ColumnValues`, `Completeness`, `ReferentialIntegrity`, `CustomSql`
(:42).

Quick Diagnostic: **X 10/10, Y 10/10.**

**Better: tie.** Each covers one modality concretely where the other stays abstract: X covers
audio, plus the tabular `DocumentBlock` formats and the injection warning; Y covers the image
format conversion and job provenance. The two gaps are of equal weight.

## Summary

| Bite | X blocking / should-fix / nit | Y blocking / should-fix / nit | X score | Y score | Winner |
|---|---|---|---|---|---|
| 1.3.1 | 0 / 0 / 2 | 0 / 0 / 1 | 10 | 10 | Y |
| 1.3.2 | 0 / 1 / 1 | 0 / 0 / 1 | 9 | 10 | Y |
| 1.3.3 | 0 / 1 / 1 | 0 / 3 / 0 | 10 | 10 | X |
| 1.3.4 | 0 / 1 / 0 | 0 / 0 / 2 | 10 | 10 | Y |
| 1.3.5 | 0 / 1 / 1 | 0 / 1 / 1 | 10 | 10 | tie |
| **Total** | **0 / 4 / 5** | **0 / 4 / 5** | **49** | **50** | **Y 3, X 1, tie 1** |

**Overall: Y, narrowly.**

Neither draft states a wrong fact. Every load-bearing claim sampled from both checked out against
the stored AWS pages, so the decision rests on mechanism coverage and the deciding number, not on
accuracy. The defect totals are identical, but Y's should-fix findings cluster in one Bite (1.3.3,
where it is thin on Textract page limits, the modality-check API and Comprehend's contract). X's
are spread across four Bites and include a missing number on the side of a choice (1.3.4) and an
unnamed enforcement switch (1.3.2). That gives Y three of five Bites. X is the denser draft and
the stronger 1.3.3. Y more consistently prints the specific setting that carries each decision
(`On ruleset failure`, `DataQualityEvaluationResult`, `compositeRuleEvaluation.method`, the
777,600 s ceiling, `ImageBlock.format`). The margin is small enough that either draft would ship
after its listed should-fix edits.
