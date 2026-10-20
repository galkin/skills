---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-1"
title: "Define acceptance before transforming model inputs"
description: "Define measurable completeness, consistency, validity, and suitability gates for foundation model inputs."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Define FM input quality thresholds for completeness, consistency, validity, and suitability.

## Core idea

For a foundation model (FM) pipeline, input quality is an acceptance contract. Specify what must be present, which values must agree, which representations are legal, and whether the evidence can serve the intended task. A record can pass three dimensions and fail the fourth. A complete, well-formed product description is still unsuitable evidence for a question about a different product version.

Separate measurements from decisions. AWS Glue Data Quality provides rules and metrics through Data Quality Definition Language (DQDL). Your application decides whether a failed condition rejects a record, holds a batch, requests a replacement, or routes evidence for review. Define that behavior before selecting a convenient percentage.

## How it works

### Make completeness specific to the task

Completeness asks whether required information exists. In DQDL, `Completeness` measures the proportion of non-null values in a column, while `IsComplete` requires complete data. `ColumnExists` checks the presence of a column. These are different checks: a dataset can contain a required column whose values are missing.

For required source identifiers, prefer a strict condition such as `IsComplete` over a tolerant aggregate threshold. For optional descriptive fields, a proportion can be useful. An illustrative contract might accept `Completeness "summary" > 0.95`; that threshold is a business example, not an AWS recommendation. At exactly 0.95 the strict greater-than expression fails.

Do not equate non-null with informative. Check empty strings and strings containing only whitespace explicitly with the DQDL `EMPTY` and `WHITESPACES_ONLY` keywords in `ColumnValues`. A source can fill every field with spaces while contributing no useful context. For documents, define completeness in terms of required sections or fields after extraction; a nonempty text blob is not proof that every required section survived.

### Define which values must agree

Consistency concerns relationships. A document's product identifier should agree with the approved product reference, and a currency code should agree with the meaning assigned to an amount. Choose the check that expresses the relationship rather than comparing unrelated quality scores.

DQDL `ReferentialIntegrity` checks references between datasets. `DatasetMatch` compares datasets using column mappings, and `CustomSql` expresses business checks in SQL. Use these mechanisms for relationships that a single-column datatype check cannot establish. Preserve the distinction between an inconsistency and an authorized difference: two regional prices can differ legitimately if their region and currency metadata explain why.

Define the scope of each relationship. Comparing a source snapshot to a reference snapshot requires a deliberate version choice. Otherwise, a reference update can turn a previously accepted batch into a failure without any change to the batch. Record which reference you used alongside the quality result.

### Check validity before interpreting meaning

Validity asks whether a value satisfies its representation contract. DQDL `ColumnDataType` checks datatype compliance, `ColumnValues` checks permitted values or regular expressions, and `ColumnLength` checks length. A date that parses successfully can still be wrong for the business event; parsing validity does not establish truth.

Document the denominator for every tolerant rule. A rule covering all rows answers a different question from a rule covering only one source or language. Keep critical identifiers and authorization attributes outside a permissive average. A high overall pass rate must not admit a record whose required identifier failed.

Also distinguish dataset outcomes from individual eligibility. A column-level rule passing at 99% does not identify every record as valid. Choose row-level checks where the consumer needs a per-record decision, and verify that the selected DQDL rule supports row-level results. The rule-type reference lists that support separately from support as an aggregate rule.

### Define suitability against the consuming model and task

Suitability asks whether acceptable data can actually answer the intended question through the selected interface. Define allowed subject matter, source revision, language, and required evidence coverage as application criteria. Use reviewed examples to decide whether a transformation preserves the information the task needs.

Add interface checks where AWS documents them. The Bedrock `Message` contract permits at most 20 images, each no larger than 3.75 MB and 8000 pixels in either dimension. It permits at most five documents, each no larger than 4.5 MB. These are message constraints, not a guarantee that every model supports every modality; see 1.3.3 for capability checks with `GetFoundationModel` and for separate document-support verification.

Treat those restrictions as hard eligibility checks alongside task suitability. A readable image can exceed the interface's size limit. Resizing it into compliance can remove the detail needed to answer the question. Validate the transformed image for both properties. Model selection belongs to 1.2.1, message formatting to 1.3.6, and context budgeting to 1.3.9.

## Key distinctions and trade-offs

**Hard gate versus monitored indicator:** A missing source identifier can block publication, while a declining optional-field completion rate can trigger investigation. Write the disposition next to the condition so a dashboard does not become the only enforcement point.

**Batch acceptance versus record acceptance:** An aggregate threshold measures a population. A per-record gate determines which evidence reaches the model. Use both when the batch must be healthy and each released record must meet critical requirements.

**Repair versus invention:** Normalizing whitespace can preserve evidence. Filling a missing contractual amount with a plausible model-generated value changes the evidence. Keep inferred values separate and subject them to the validation boundary in 1.3.10.

## Architecture / decision scenario

A warranty assistant ingests product sheets and a reference catalog. The team defines an illustrative contract: every released record needs a source identifier, product identifier, and revision; optional summaries must exceed 95% completeness across the batch.

Glue checks required values with `IsComplete`, allowed document categories with `ColumnValues`, and product references with `ReferentialIntegrity`. A `CustomSql` check rejects records whose effective dates contradict the team's warranty-period rule. These address completeness, validity, and consistency separately.

Suitability adds two gates: the sheet must cover the requested product revision, and its prepared document must satisfy the Bedrock `Message` constraints. A complete sheet for another revision stays unavailable for that answer. A correct sheet whose resized diagram loses the warranty legend goes for reprocessing rather than acceptance.

The release record stores the ruleset version, reference snapshot, outcomes, and disposition. A failed required field blocks that record; a failed batch summary threshold holds the batch for investigation. Neither a high average nor a successful model invocation overrides the gates.

## Common exam traps

- Treating `ColumnExists` as proof that required values are populated.
- Treating non-null strings as proof of meaningful content.
- Using a datatype check to establish cross-record consistency.
- Promoting every row because an aggregate rule passed.
- Applying Bedrock message limits as proof of model modality support.
- Repairing missing evidence with an unverified generated value.

## What to remember

Define all four dimensions independently, name the measurement, and specify the consequence. DQDL implements structural and relational checks; application criteria establish fitness for the task. An input reaches the model only after its critical record gates and relevant batch gates pass.

## References

- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Completeness](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types-Completeness.html)
- AWS, [Data Quality Definition Language reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl.html)
- AWS, [Message](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html)
