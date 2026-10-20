---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-2"
title: "Separate profiling evidence from validation gates"
description: "Combine Glue Data Quality rules, Data Wrangler profiling, and Lambda telemetry to validate inputs without confusing quality with execution success."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Validate and profile inputs using AWS Glue Data Quality, SageMaker Data Wrangler, and Lambda metrics.

## Core idea

As an architect, you need three kinds of evidence before declaring a data pipeline
healthy: what the input population looks like, whether inputs satisfy policy,
and whether processing executes reliably. Data profiling, validation, and runtime
telemetry answer these questions separately.

Use SageMaker Data Wrangler to discover distributions and defects, AWS Glue Data
Quality to evaluate explicit rules, and Lambda metrics to observe execution.
Publish custom quality counters from your validator when you need operational
visibility into accepted and rejected inputs. Neither a clean profile nor a low
Lambda error rate proves that the model receives valid evidence.

The threshold policy belongs to 1.3.1. This lesson explains how to gather evidence
and turn it into an observable validation decision.

## How it works

### Profile before freezing rules

AWS documents Data Wrangler data preparation in Amazon SageMaker Canvas. Its
**Data Quality and Insights Report** describes missing values, invalid values,
feature types, outliers, and duplicate samples. Use that report to investigate
source behavior and identify which assumptions deserve executable rules.

A profile is descriptive. An outlier can be a legitimate expensive purchase; a
common value can be a repeated collection error. Investigate examples against
the source and business meaning before changing or deleting records. The report
helps you find candidates for policy; it does not approve those policies.

The report offers **Sampled dataset** and **Full dataset**. The interactive sample
can contain up to 200,000 rows. A full-dataset report uses a SageMaker Processing
job. Record which option you used and the source population it represents.
A sample with no invalid rows does not establish that the entire delivery is
clean, particularly when rare document types or languages are underrepresented.

For supervised modeling, the report also supports target-oriented analysis such
as leakage and feature predictive power. Those signals do not become evidence
that extracted text is factually faithful to a source document. Keep the analysis
aligned with the task you are preparing data for.

### Evaluate explicit Glue rules

Turn reviewed assumptions into a versioned DQDL ruleset. `ColumnExists` tests
schema presence, `IsComplete` tests full completeness, and `ColumnValues` tests
permitted values or patterns. Use the four quality dimensions from 1.3.1 to
explain why each rule exists rather than collecting unrelated checks.

In Glue ETL, `EvaluateDataQuality().process_rows` returns a collection containing
`ruleOutcomes` and `rowLevelOutcomes`. Rule outcomes contain `Rule`, `Outcome`,
`FailureReason`, and `EvaluatedMetrics`. These fields explain whether a rule
passed and which measurement caused a failure. Preserve them with the source
and ruleset version when investigating a rejected delivery.

Row outcomes add `DataQualityRulesPass`, `DataQualityRulesFail`,
`DataQualityRulesSkip`, and `DataQualityEvaluationResult`. Route supported
row-level failures using these results. A dataset-level schema or count rule
cannot necessarily identify one bad row, so inspect the rule-level decision too.
Do not claim every DQDL rule supports row-level routing; the rule-types reference
states support separately for each rule.

The ETL publishing options include `dataQualityEvaluationContext`,
`enableDataQualityCloudWatchMetrics`, and `enableDataQualityResultsPublishing`.
Configure those deliberately. Publishing a result makes it observable; your
pipeline still needs a branch that blocks or filters publication when the
required checks fail. A dashboard alone is not an enforcement mechanism.

### Interpret Lambda's runtime metrics correctly

Lambda's `Invocations` counts executions, including those ending in function
errors. `Errors` counts function errors, such as exceptions and timeouts.
`Throttles` counts rejected invocation requests; those requests do not count as
`Invocations` or `Errors`. Use `Sum` for these counts. `Duration` measures execution
time in milliseconds and excludes cold-start time.

A validator can find an invalid invoice, record the rejection, and return
successfully. That is a successful execution with a negative quality outcome.
Conversely, a timeout means validation did not finish; it must not be counted
as a completed quality rejection. Treat unevaluated records as a separate state.

Publish application-defined metrics with CloudWatch `PutMetricData`. Supply
`Namespace` and `MetricData`, with fields such as `MetricName`, `Value`, and
`Dimensions`. Example names are `InputsEvaluated`, `InputsRejected`, and
`InputsAccepted`; these are your metrics, not built-in Lambda metrics. Define
what one increment means and count retries consistently.

Use bounded dimensions such as pipeline and ruleset version, and keep
record-specific evidence in the validation result rather than turning every
source identifier into a metric series. Compute rejection rate from rejected
records divided by evaluated records for the same population and time window.
Invocation count is the wrong denominator when one invocation handles many
records or retries the same record.

## Key distinctions and trade-offs

**Profiling versus enforcement:** Data Wrangler reveals patterns worth
investigating. Glue evaluates declared expectations. Replacing explicit rules
with periodic visual inspection leaves publication behavior undefined.

**Sample versus population:** Interactive sampling shortens exploration. A
full-dataset report examines the complete selected source through a processing
job. Even a full report proves only properties actually measured; it does not
establish semantic correctness for every source field.

**Quality failure versus processing failure:** A rejected record is a measured
business outcome. A failed invocation is missing processing evidence. Monitor
both, because a stable rejection rate can hide an increasing unevaluated backlog.

**Rule-level versus row-level results:** A batch result can stop a delivery,
while supported row results can separate accepted records. Neither result
substitutes for the other when the policy contains both kinds of rule.

## Architecture / decision scenario

A claims assistant receives daily CSV deliveries from several partners. One
partner changes its identifier format, while another introduces sparse optional
notes. The team profiles each source with Data Wrangler's Data Quality and
Insights Report and records whether each report covers a sample or the full
source. It reviews malformed identifiers and legitimate missing notes separately.

It then freezes a DQDL ruleset: required identifiers must be complete and match
the approved pattern; optional-note coverage has its own policy. The Glue ETL
job examines `ruleOutcomes`, sends rows with failed supported checks to a
rejection output, and publishes accepted rows only after batch gates pass.

A Lambda validator checks incoming delivery metadata. It emits custom
`InputsEvaluated` and `InputsRejected` counters through `PutMetricData`, even
when a normal rejection returns successfully. The dashboard presents those
counters alongside `Errors`, `Throttles`, and `Duration`.

If rejections rise while execution stays healthy, investigate source contracts.
If throttling rises, investigate processing capacity without relaxing quality
rules. If profiling misses a rare malformed record, the deterministic rule
still rejects it at publication. Every service contributes different evidence
to the same release decision.

## Common exam traps

- Treating a sampled profile as validation of every delivered row.
- Using Lambda `Errors` as a count of rejected business records.
- Including throttled requests in `Invocations` or `Errors`.
- Assuming CloudWatch publication automatically stops a Glue job.
- Assuming every DQDL rule produces a row-level verdict.

## Where the exam guide differs

:::callout{type="note"}
The objective names SageMaker Data Wrangler without specifying its interface.
AWS documents access through SageMaker Canvas for the Studio experience;
Studio Classic is the earlier interface described in the migration guidance.
Recognize Data Wrangler as the profiling and preparation capability, and use
the Canvas documentation for the workflow taught here.
:::

## What to remember

Profile to discover, validate to decide, and monitor to operate. Preserve the
population and ruleset behind each result. Use custom quality counters for
business outcomes and Lambda's runtime metrics for execution failures and delay.

## References

- AWS, [Data preparation](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-data-prep.html)
- AWS, [Perform exploratory data analysis (EDA)](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-analyses.html)
- AWS, [Getting started with AWS Glue Data Quality for ETL in AWS Glue Studio notebooks](https://docs.aws.amazon.com/glue/latest/dg/data-quality-gs-studio-notebooks.html)
- AWS, [DQDL rule types](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Types of metrics for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- AWS, [PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
