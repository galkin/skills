---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-1"
title: "Set input gates before model consumption"
description: "Define measurable completeness, consistency, validity, and suitability gates that determine whether data can enter a foundation model workflow."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Define FM input quality thresholds for completeness, consistency, validity, and suitability.

## Core idea

For an architect preparing data for a foundation model (FM), input quality is an admission decision. A record that parses successfully can still omit evidence, contradict another record, or be inappropriate for the intended task. Define what the consumer needs before selecting a measurement.

Use four separate dimensions. **Completeness** asks whether required information is present. **Consistency** asks whether related values agree. **Validity** asks whether values meet declared constraints. **Suitability** asks whether the accepted information can support this particular model task. A high score in one dimension does not compensate for failure in another.

A threshold needs a population, a calculation, an acceptance boundary, and a consequence. “Good quality” supplies none of them. “Every admitted claim has a nonempty claim identifier, and at least 99% of expected source records arrive before publication” defines two different gates. The percentages in this lesson illustrate application policy; they are not AWS defaults.

## How it works

### Separate record requirements from dataset requirements

Start with the consumer's decision. An invoice assistant needs an identifiable invoice, interpretable currency, and enough evidence to explain a total. Mark the identifier and currency as mandatory for each admitted invoice. Separately, define whether the batch contains the expected invoices. A batch with complete rows can still be missing half its source files.

AWS Glue Data Quality expresses checks in Data Quality Definition Language (DQDL). `IsComplete` requires all values in a column to be non-null, while `Completeness` compares the fraction of non-null values with an expression. Use a strict requirement for identity fields and a calibrated population threshold for optional attributes. `RowCount` checks dataset size, and `RowCountMatch` compares counts against a reference dataset. Neither proves that the correct individual records arrived.

Define the denominator before interpreting a fraction. Is it all uploaded files, all parsed records, or only the records that survived a filter? Measuring completeness after silently dropping malformed records makes the result look better while reducing evidence coverage. Reconcile the source population with accepted and rejected populations so the quality gate cannot hide missing work.

### Make consistency and validity explicit

Consistency requires a relationship. `ReferentialIntegrity` checks relationships to a reference dataset; `DatasetMatch` compares datasets; `CustomSql` supports checks that need application-specific SQL. A currency code that belongs to the permitted set is valid. A currency code that disagrees with the currency on the associated invoice header is inconsistent. These failures require different evidence and different repairs.

For validity, Glue provides `ColumnDataType`, `ColumnValues`, and `ColumnLength`. Use `ColumnValues` for allowed categories, numeric constraints, or regular expressions. Choose positive acceptance conditions where practical: a blacklist of invalid codes cannot enumerate every malformed value. Keep the permitted domain and the rule version with the evaluation result.

Check parsing semantics before trusting a completeness score. AWS documents that a blank CSV value parsed as a string can become an empty string and pass `Completeness`; a blank parsed as an integer can become null and fail. A present-but-empty identifier therefore needs an additional content check. `ColumnValues` distinguishes `NULL`, `EMPTY`, and `WHITESPACES_ONLY`. Define whether each is acceptable rather than treating all three as interchangeable.

### Define suitability for the actual consumer

Suitability adds the task contract to structural checks. A technically valid transcript in an unsupported language, a table with unexplained units, or an image without the relevant subject can be unsuitable. Choose reviewed examples of usable and unusable input and record why the distinction matters to the downstream answer.

Implement measurable suitability proxies with the appropriate mechanism. Glue `ColumnValues` can constrain a normalized language or document-category field; `DataFreshness` can check a timestamp column. These rules validate the recorded attributes, not the truth of an image's meaning. If suitability depends on interpretation, keep a separate application assessment tied to source evidence. AWS does not provide one universal FM-suitability score.

The model interface is another gate, separate from semantic usefulness. For Bedrock Converse messages, the `Message` contract permits at most 20 images, each no larger than 3.75 MB or 8,000 pixels in either dimension, and five documents, each no larger than 4.5 MB. Documents require an accompanying text block, and images and documents belong in user messages. These are interface ceilings; model support still needs checking. See 1.3.6 for request construction.

## Key distinctions and trade-offs

An aggregate tolerance and an individual admission rule serve different purposes. A batch may meet a 99% completeness target while its remaining 1% must still be excluded from model input. Conversely, every retained row may pass validation while the batch fails a source-count reconciliation.

Hard gates protect requirements that cannot be relaxed, such as required identity or an allowed unit. Soft thresholds expose degradation that might justify investigation without rejecting all useful work. Calibrate soft thresholds on representative sources and review the cost of false rejection alongside the cost of accepting unusable evidence.

Do not adapt a threshold merely to make the observed dataset pass. Changing source populations, parsers, or business requirements can justify a revised policy, but retain the previous result and the reason for the change. Otherwise a more permissive rule can conceal a regression rather than resolve it.

## Architecture / decision scenario

An insurer prepares claim records for a summarization assistant. Each admitted record must contain a nonempty claim identifier. The batch must account for its expected source records. The policy accepts a small amount of missing optional contact information, but no missing identity information.

The team uses `Completeness` for the optional field and supplements identifier completeness with `ColumnValues` checks for empty and whitespace-only strings. It uses `RowCountMatch` against the intake reference, then checks claim-to-policy relationships with `ReferentialIntegrity`. `ColumnValues` constrains currency and document category; a custom cross-field check verifies that header and line-item currencies agree.

Suitability remains a separate decision. A complete, valid claim with an unsupported document category is withheld from this assistant. An outdated policy is assessed against the business freshness requirement rather than accepted because its fields parse. Accepted records carry the rule version and source identity. Missing source records hold the batch for reconciliation; isolated invalid records receive explicit rejection reasons. See 1.3.2 for the execution and measurement mechanisms.

## Common exam traps

- Treating non-null, nonempty, and meaningful as the same requirement.
- Using a population pass rate as permission to admit every row.
- Assuming a valid category guarantees agreement with related records.
- Measuring only records that survived preprocessing and ignoring missing inputs.
- Treating a model's supported payload size as proof that the content suits the task.
- Letting a single quality average hide a failed mandatory dimension.

## What to remember

Define the unit and denominator before choosing a threshold. Keep record admission, dataset coverage, relationship consistency, and task suitability distinct. Glue DQDL supplies concrete structural checks; application policy determines their thresholds and consequences. Preserve enough evidence to explain both acceptance and rejection.

## References

- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Completeness](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-Completeness.html)
- AWS, [ColumnValues](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-ColumnValues.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
- AWS, [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
