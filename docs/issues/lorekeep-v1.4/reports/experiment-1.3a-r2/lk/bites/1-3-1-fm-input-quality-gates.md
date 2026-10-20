---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-1"
title: "Define gates before admitting model inputs"
description: "Define measurable input acceptance gates for completeness, consistency, validity, and task suitability."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Define FM input quality thresholds for completeness, consistency, validity, and suitability.

## Core idea

An input quality threshold is an acceptance contract before a foundation model (FM) consumes data. It states what you measure, over which population, and what happens when the condition fails. A successful file read or model invocation does not establish that the input can support the intended answer.

Keep four decisions separate. Completeness asks whether required information exists. Consistency asks whether related representations agree. Validity asks whether values obey their declared contract. Suitability asks whether the information serves this particular model and task. A record can satisfy the first three and still describe the wrong product or omit the evidence needed for a decision.

Use AWS Glue Data Quality rules for measurable dataset properties and an application acceptance policy for task meaning. The thresholds in this lesson's scenario are illustrative business choices, not AWS defaults. Operationalizing and profiling the rules belongs to 1.3.2.

## How it works

### Make completeness explicit

AWS Glue's Data Quality Definition Language (DQDL) provides `Completeness`, which compares the proportion of non-null column values with an expression. `IsComplete` requires complete data throughout the column. Decide which fields tolerate partial coverage and which identify the record or carry essential evidence.

Null checks alone do not establish usable text. AWS documents that a blank CSV value in a string column can become an empty string and pass `Completeness`; a blank in an integer column can become null and fail. Combine null testing with an explicit content check. `ColumnLength` measures string length, and `ColumnValues` supports value and regular-expression checks. Use the `ColumnValues` keywords `EMPTY` for empty strings and `WHITESPACES_ONLY` for strings containing only whitespace. A value-list exclusion such as `ColumnValues "contact" not in [EMPTY, WHITESPACES_ONLY]` closes that content gap alongside the null check. Add application-defined placeholder strings to the exclusion list. If you combine conditions with an `or` composite instead, select `compositeRuleEvaluation.method` = `ROW` for row evaluation; see 1.3.2.

Distinguish field coverage from source coverage. A dataset can contain no nulls while omitting an entire expected delivery. Use `RowCount` for a count boundary or `RowCountMatch` when comparing counts with a reference dataset. Neither establishes that every expected identity arrived; identity reconciliation is a separate requirement.

### Define what must agree

Consistency requires a reference, not merely similar-looking values. Use `SchemaMatch` to compare schemas, `DatasetMatch` to compare datasets with column mappings, or `ReferentialIntegrity` to check relationships against a reference dataset. `CustomSql` expresses application-specific checks such as agreement between a header total and detail records.

Specify the normalization policy alongside the check. For example, the design might convert amounts to one currency representation before comparing totals. Do not silently discard the original value or unit: a transformation that hides the discrepancy can make the check pass without repairing the source. Record whether a failure means an extraction defect, a conflicting revision, or an invalid business relationship.

### Separate validity from plausibility

Use `ColumnDataType` for type compliance and `ColumnValues` for permitted values or ranges. A syntactically valid date can still describe an impossible business event. A numeric amount can still use the wrong unit. Add a `CustomSql` business condition when the decision depends on relationships between fields rather than one field's representation.

DQDL does not support nested or list-type column data. For an application accepting nested model messages, choose a deliberate projection into checkable columns or validate the original structure in application code. A passing flat projection is evidence about those projected fields; it is not a certificate for the full nested request. Request formatting and native payload validation belong to 1.3.6 and 1.3.7.

### Test suitability against the intended use

Suitability needs both a mechanical boundary and reviewed task evidence. For a supported Bedrock target, `CountTokens` uses `modelId` and the intended inference input to return `inputTokens`. Tokenization is model-specific. Compare the result with the selected model's documented capacity and your application's allocation; token-budget policy belongs to 1.3.9.

Being within a token budget does not prove relevance or adequate evidence. Define a reviewed acceptance rubric: required source period, product identity, supported language, and evidence needed for the requested outcome. Your application implements that rubric and records a disposition. Do not invent a universal AWS suitability score. A count measures size; reviewed cases establish whether your evidence and transformation preserve task meaning.

## Key distinctions and trade-offs

**Row versus dataset thresholds:** An allowed missing-value fraction can admit a dataset containing unusable individual records. Decide whether to exclude those records, reject the delivery, or permit partial publication. Document the denominator before reporting a percentage.

**Strict gates versus partial coverage:** Requiring every optional field can suppress useful evidence. Allowing missing identifiers can destroy traceability. Assign thresholds by consequence, and keep mandatory identity checks independent of optional enrichment.

**Independent rules versus one score:** A combined quality score can conceal a critical failure. Treat mandatory checks as separate release conditions. Improvement in average text coverage must not compensate for an inconsistent customer identity or invalid amount.

**Historical baseline versus acceptance contract:** A stable defect rate can be unacceptable. Historical observations help discover changes; business requirements determine which inputs may reach the model.

## Architecture / decision scenario

A procurement assistant consumes supplier records and extracted order text. The example policy requires every record to have an order identifier, at least 99% of optional contact fields to be non-null, matching order and supplier references, valid nonnegative amounts, and evidence about the requested product revision.

The team uses `IsComplete` for identifiers and `Completeness` for contact coverage. It adds `ColumnValues` exclusions using `EMPTY` and `WHITESPACES_ONLY` because non-null contact strings can still lack content. `ReferentialIntegrity` checks supplier membership, while a `CustomSql` condition compares totals with detail records. `ColumnValues` enforces the amount boundary.

Before inference, the application checks the requested product revision and required evidence against its reviewed suitability rubric. It also uses `CountTokens` for the supported target. A record about another revision remains unsuitable even when its schema and token count pass.

A missing optional contact can enter a partial-coverage output. A missing identifier or inconsistent total enters a quarantine output with the failed condition and source identity. A valid record without the requested evidence produces an explicit insufficient-evidence disposition. The release decision exercises all four dimensions instead of reducing them to one percentage.

## Common exam traps

- Treating a non-null string as proof of meaningful content.
- Applying a dataset pass rate as if it certified every row.
- Calling type compliance a test of business correctness.
- Assuming DQDL validates arbitrary nested request structures.
- Treating token fit as proof that evidence suits the task.
- Selecting round thresholds without defining a denominator or failure action.

## What to remember

Define the population, measurement, threshold, and disposition together. Use `Completeness`, comparison rules, and validity rules for the properties they actually measure. Add a task-specific suitability decision and preserve critical failures independently of aggregate scores. A quality gate controls admission; it does not repair missing evidence.

## References

- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Data Quality Definition Language reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl.html)
- AWS, [Completeness](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-Completeness.html)
- AWS, [CountTokens](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CountTokens.html)
