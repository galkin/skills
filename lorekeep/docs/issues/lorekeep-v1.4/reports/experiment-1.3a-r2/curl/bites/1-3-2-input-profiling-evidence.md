---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-2"
title: "Separate profiling findings from enforcement metrics"
description: "Combine Glue Data Quality, Data Wrangler reports, and Lambda telemetry to measure and enforce input quality."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Validate and profile inputs using AWS Glue Data Quality, SageMaker Data Wrangler, and Lambda metrics.

## Core idea

Profiling discovers what a dataset contains. Validation compares it with an acceptance contract. Operational metrics show whether the code performing those checks runs successfully. Use all three kinds of evidence without substituting one for another.

AWS Glue Data Quality provides executable DQDL rules. SageMaker Data Wrangler provides exploration and a Data Quality and Insights Report. Lambda publishes invocation and performance metrics; your function must also publish application measurements if you want telemetry about rejected inputs. A function can successfully reject a malformed record without producing a Lambda function error.

The thresholds themselves belong to 1.3.1. Here the decision is which mechanism produces the evidence, how much data it covers, and what consumes its result.

## How it works

### Explore the distribution with Data Wrangler

AWS integrates Data Wrangler into SageMaker Canvas. In Amazon SageMaker Studio, you access Data Wrangler through Canvas; the report controls described below are scoped to Studio Classic. Use Data Wrangler in Canvas to prepare and analyze data through a data flow. Its Data Quality and Insights Report identifies abnormalities; the documented report includes missing and invalid values, feature types, and outlier counts. These findings help you discover candidate rules, such as a required field arriving empty from one supplier or a numeric field containing a source-specific sentinel.

Treat report coverage as part of the evidence. The Studio Classic report documentation distinguishes **50 K**, which uses the first 50,000 imported rows, from **Entire dataset**, which uses all imported data and runs a SageMaker Processing job. Those controls describe that documented experience; do not assume that a report generated over a bounded import represents every source object.

A first-rows report is especially weak evidence for a failure confined to later files or a minority source. Record the imported population, time range, selected data size, and flow step. Inspect the data after transformations as well as before them: a cast or join can introduce missing values even when raw inputs look healthy.

When the report includes a target column, its predictive analyses concern a classification or regression task. They are not direct measurements of foundation-model grounding or answer quality. Use those findings only where the target and analysis match your preparation problem.

### Turn findings into Glue validation

Express approved conditions in Data Quality Definition Language (DQDL), then evaluate them at the appropriate pipeline boundary. The Glue `EvaluateDataQuality.apply` transform accepts a `DynamicFrame` and a ruleset. Its result includes `Rule`, `Outcome`, `FailureReason`, and `EvaluatedMetrics`.

Keep all four fields in the validation evidence. `Outcome` carries the rule decision; `FailureReason` explains a failure; `EvaluatedMetrics` preserves the measured value. Storing only a pass percentage loses the distinction between a missing column and a completeness measurement below its threshold.

Configure publishing deliberately. In `publishing_options`, `enableDataQualityCloudWatchMetrics` controls CloudWatch publication and defaults to `False`. `dataQualityEvaluationContext` specifies the namespace for published CloudWatch metrics and data quality results; its default is `default_context`. `enableDataQualityResultsPublishing` controls visibility on the Glue Studio **Data Quality** tab and defaults to `True`. A results page and published monitoring metrics are separate settings.

Choose checks with the output granularity you need. The DQDL rule-type reference distinguishes support as a rule, as an analyzer, and for row-level results. For example, `AllStatistics` gathers several metrics as an analyzer; it is not itself an acceptance rule. `ColumnExists` checks schema presence without returning row-level results. Do not promise a rejected-record list from every rule.

Make the consumer of the rule result explicit. Your pipeline can hold an output partition when a critical rule fails, or separate acceptable records using supported row-level checks. Publishing an `Outcome` does not, by itself, define your release policy. Retain the ruleset identity and evaluated dataset identity alongside the result so the same measurement can be interpreted later.

### Observe Lambda execution and data decisions separately

Lambda `Invocations` counts executions, including executions that return a function error. `Errors` counts function errors such as thrown exceptions and runtime timeouts. `Throttles` counts throttled invocation requests; those requests do not count as `Invocations` or `Errors`. Use `Sum` to inspect these counts. `Duration` measures function execution time in milliseconds and supports percentile statistics such as `p95`.

These metrics diagnose execution, not semantic validity. If a validator detects an invalid date, records a rejection, and returns normally, that rejection is an application outcome. If parsing crashes unexpectedly, the function can produce an `Errors` measurement. Preserve that distinction so data defects do not disappear behind a low runtime error rate.

Publish custom quality measurements with CloudWatch `PutMetricData`. Set your own `Namespace` and provide `MetricData` entries containing `MetricName` and `Value`; add `Dimensions` for useful bounded categories. For example, `InputChecked` and `InputRejected` can be application-defined counts grouped by source family and validator version. These names are design examples, not built-in Lambda metrics.

Keep a denominator for rejection rates. Count checked records separately from invocations because one invocation can process multiple records. Store record identifiers and detailed failure evidence in the validation record rather than turning every identifier into a metric dimension. For retry-sensitive business totals, count distinct records in your durable results instead of assuming execution counts equal unique inputs.

## Key distinctions and trade-offs

**Profile versus rule:** A profile describes observed values. A rule declares acceptance. Review a surprising outlier before making its observed range the next production threshold.

**Analyzer versus validator:** An analyzer can produce useful metrics without a pass/fail condition. Select a DQDL rule when downstream processing needs an explicit `Outcome`.

**Data rejection versus execution failure:** A healthy validation service can reject bad inputs. A broken validation service cannot establish their quality. Give these conditions separate measurements and responses.

## Architecture / decision scenario

A support assistant receives structured ticket exports. Data Wrangler profiling reveals missing product codes and a second date format. The team records the report's input population, approves date normalization, and defines required-code and valid-date rules in Glue.

The Glue run retains `Outcome`, `FailureReason`, and `EvaluatedMetrics` and explicitly enables CloudWatch publication. A failed required-code rule holds the affected release. Reprofiling after normalization verifies that the cast did not silently remove dates.

A Lambda adapter validates arriving records before they enter the next batch. It publishes application-defined checked and rejected counts through `PutMetricData`. Operators inspect Lambda `Errors` and `Duration` for execution defects, and compare those with the rejection rate for source defects.

If rejected counts rise while `Errors` stays flat, the team investigates source quality. If timeouts rise and checks stop completing, it investigates the validator's execution path. The scenario needs all three tools because discovery, enforcement, and runtime health answer different questions.

## Common exam traps

- Reading a successful Lambda invocation as proof of acceptable input.
- Including throttled requests in the `Invocations` denominator.
- Assuming Glue CloudWatch metric publication is enabled by default.
- Treating `AllStatistics` as a pass/fail rule.
- Claiming first-50,000-row coverage represents the entire dataset.
- Treating a tabular quick-model score as an FM answer-quality score.

## What to remember

Use Data Wrangler to discover candidate defects, Glue DQDL to evaluate explicit rules, and Lambda metrics to diagnose the validator. Publish custom CloudWatch measurements for application quality decisions and retain the population and ruleset behind each result.

## References

- AWS, [Data preparation](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-data-prep.html)
- AWS, [Get insights on data and data quality](https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-data-insights.html)
- AWS, [EvaluateDataQuality](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-crawler-pyspark-transforms-EvaluateDataQuality.html)
- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Types of metrics for Lambda Event Functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- AWS, [PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
