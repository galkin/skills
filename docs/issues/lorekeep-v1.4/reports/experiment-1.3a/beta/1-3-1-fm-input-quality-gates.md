---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-1"
title: "Define input gates before model consumption"
description: "Translate completeness, consistency, validity, and suitability requirements into measurable foundation model input gates."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Define FM input quality thresholds for completeness, consistency, validity, and suitability.

## Core idea

For an architect preparing data for a foundation model (FM), input quality is an
acceptance contract. You define which evidence must exist, which relationships
must hold, which values are legal, and whether the resulting input serves the
intended task. A successful model invocation establishes none of these properties.

Keep four dimensions separate. **Completeness** means required information is
present. **Consistency** means related representations agree. **Validity** means
values satisfy their declared constraints. **Suitability** means the material is
appropriate for this task and model route. A record can pass three dimensions and
still fail the fourth: a complete, internally consistent invoice from the wrong
customer is unsuitable evidence for the request.

Thresholds express business decisions. AWS Glue Data Quality supplies executable
checks; it does not supply a universal FM readiness percentage. Define the scope,
denominator, boundary, and failure action before selecting a rule.

## How it works

### Define completeness at two levels

Specify fields that every accepted record needs, then specify coverage across the
expected delivery. A batch with no missing identifiers can still omit half of the
expected documents. Conversely, a complete delivery can contain unreadable records.

In AWS Glue Data Quality Definition Language (DQDL), `IsComplete` checks complete
coverage of a column, while `Completeness` compares the fraction of non-null values
with an expression. For example, a business policy might require completeness
above 0.99 for an optional description while requiring every source identifier.
These are illustrative policy thresholds, not AWS recommendations. State whether
an exact boundary passes: greater than 0.99 excludes exactly 99%.

Null semantics matter. The `Completeness` documentation explains that a blank CSV
string can become an empty string and pass the rule; a blank numeric value can
become null and fail. Define whitespace-only and empty-text checks separately,
using `ColumnLength` or `ColumnValues` after your declared normalization. Otherwise,
a column can satisfy null completeness while giving the model no usable evidence.

### Define consistency across representations

Consistency checks compare things that can each be valid in isolation. A currency
code might be legal while conflicting with the currency recorded in the source
ledger. A source identifier might exist while referring to the wrong revision.
Write the relationship, its authoritative side, and its allowed exceptions.

DQDL provides `ReferentialIntegrity` for relationships to a reference dataset,
`DatasetMatch` for matching datasets, and `SchemaMatch` for comparing schemas. Use
`CustomSql` when a cross-field business relation needs a specific SQL expression.
Choose the check that represents the relationship; uniqueness alone does not prove
that a foreign key points to the intended source.

Normalize only representations whose meaning you can preserve. Converting an
unambiguous date into a canonical format can make comparisons reliable. Guessing
whether 03/04 means March 4 or April 3 creates apparent consistency by inventing
information. Mark that record unresolved and retain the original value.

### Separate validity from suitability

Validity checks ask whether the representation meets its contract. DQDL
`ColumnDataType` checks type compliance, `ColumnValues` checks permitted values or
patterns, and `ColumnLength` checks lengths. A valid numeric amount can still be
wrong, so retain reconciliation checks against the source where the task requires
financial correctness.

Suitability requires task-specific evidence. Define whether a record contains the
right product, revision, language, and information needed to answer the intended
question. Some suitability conditions become deterministic field checks. Others
need reviewed examples comparing the source and the prepared input. Do not label
a non-null paragraph suitable merely because it contains many words.

Model-interface suitability is another gate. The Bedrock Converse `Message`
contract permits images and documents only in `user` messages and requires a text
content block when a document block is present. Those are checkable request
conditions, not proof of semantic suitability. See 1.3.6 for request construction
and 1.3.9 for context budgeting.

### Attach each threshold to an action

Record each rule's owner, policy version, evaluated population, measured value,
and disposition. Distinguish rejecting one record from blocking publication of
the entire delivery. A failed row-level identifier check should not disappear into
a passing average across unrelated columns.

In Glue ETL, `EvaluateDataQuality().process_rows` produces `ruleOutcomes` and
`rowLevelOutcomes`. The latter includes `DataQualityRulesPass`,
`DataQualityRulesFail`, `DataQualityRulesSkip`, and `DataQualityEvaluationResult`.
Use rule outcomes for batch decisions and supported row outcomes for record
routing. A skipped row-level rule needs its dataset-level result; skipped does
not mean passed. See 1.3.2 for profiling and operational measurement.

## Key distinctions and trade-offs

A hard gate protects an invariant; a warning identifies a condition worth review.
Make source identity and critical business constraints hard gates when a wrong
record could change the decision. A descriptive-field coverage warning might
permit a reduced service only if the product defines that behavior explicitly.

A dataset threshold tolerates a proportion of defects. A record gate decides
whether a particular item can proceed. If a batch permits 1% missing optional
summaries, that does not authorize sending a record with a missing customer
identifier to the model. The two policies govern different populations.

Strict thresholds reduce questionable inputs but can suppress useful evidence.
Loose thresholds increase coverage while transferring uncertainty downstream.
Choose boundaries from reviewed examples and error costs, and report results by
source and document type so a strong majority cannot hide a failing minority.

## Architecture / decision scenario

A procurement assistant consumes supplier invoices and a purchase-order ledger.
The team defines completeness as present source and order identifiers for every
accepted invoice, plus delivery counts reconciled to the expected intake list.
It uses `IsComplete` for identifiers and `RowCountMatch` for delivery reconciliation.

Consistency requires the referenced purchase order to exist and invoice currency
to agree with the ledger. `ReferentialIntegrity` checks the relationship;
`CustomSql` checks the currency relation. Validity requires numeric amounts and
permitted currency values, measured with `ColumnDataType` and `ColumnValues`.

Suitability requires an approved supplier revision and readable evidence of the
amount due. The application checks revision metadata and routes ambiguous source
extraction for review. A reviewed sample establishes the extraction acceptance
policy; no arbitrary confidence value substitutes for that work.

The publication process blocks on failed reconciliation or consistency rules.
It publishes only rows whose required row checks pass and whose suitability
review is resolved. The release record preserves the ruleset and measured values,
so changing a threshold becomes a reviewable policy change.

## Common exam traps

- Treating non-null text as complete, readable, and suitable evidence.
- Assuming a dataset percentage authorizes every individual record.
- Using uniqueness to establish agreement with an authoritative source.
- Treating a skipped row-level rule as a successful check.
- Assuming AWS defines one FM input quality score or threshold.

## What to remember

Define completeness, consistency, validity, and suitability independently. Give
each threshold a population, an exact boundary, and a failure action. Use DQDL
rules for measurable properties and task-specific review for semantic fitness.
Preserve the source instead of repairing ambiguity by guessing.

## References

- AWS, [DQDL rule types](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Completeness](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-Completeness.html)
- AWS, [Getting started with AWS Glue Data Quality for ETL in AWS Glue Studio notebooks](https://docs.aws.amazon.com/glue/latest/dg/data-quality-gs-studio-notebooks.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
