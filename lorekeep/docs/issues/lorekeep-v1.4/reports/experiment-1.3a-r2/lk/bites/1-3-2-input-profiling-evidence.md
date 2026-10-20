---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-2"
title: "Turn profiles into enforced input checks"
description: "Combine Glue rules, Data Wrangler profiles, and Lambda telemetry to distinguish input defects from processing failures."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Validate and profile inputs using AWS Glue Data Quality, SageMaker Data Wrangler, and Lambda metrics.

## Core idea

Profiling describes the data you inspected. Validation compares data with a declared acceptance rule. Runtime monitoring describes whether processing executed successfully. Use all three, with separate evidence and outcomes. A healthy Lambda function can accept unusable input, and a failed quality rule can coexist with a completed Glue job.

Use SageMaker Data Wrangler to discover candidate defects and distributions, AWS Glue Data Quality to evaluate repeatable dataset rules, and Lambda to implement application-specific event checks. Publish the results of those checks as custom metrics rather than interpreting infrastructure metrics as a content score. Threshold design belongs to 1.3.1; this lesson makes the evidence operational.

## How it works

### Profile the population you mean to assess

Data Wrangler's **Data Quality and Insights Report** analyzes imported data. Its summary includes missing and invalid values, feature types, and outlier counts. It can identify concerns such as target leakage or imbalance. These are diagnostic signals that guide investigation, not automatic proof that a record is fit for an FM request.

The report's **Data size** setting matters. **50 K** uses the first 50,000 rows of the imported dataset. **Entire dataset** uses the entire imported dataset and runs a SageMaker Processing job for the additional compute. Record which setting produced the report. Neither setting can assess source data that was never imported.

An ordered first segment can omit a later supplier, language, or document template. Design your inspection population around the failure you need to detect, and use the entire imported dataset when a release decision needs that coverage. Keep the report's population and time range beside its findings so another engineer can interpret them.

Selecting a **Target column** adds target analysis and feature prediction rankings, with a regression or classification problem type. Use that when the preparation task has a target to predict. Do not invent a target solely to obtain a quality report for a document corpus. Predictive power is not a measurement of whether passages support generated claims.

### Convert observations into repeatable rules

Glue Data Quality evaluates DQDL rules such as `Completeness`, `ColumnValues`, `ColumnDataType`, and `RowCount`. Translate a discovered issue into a named rule and explicit expected outcome. A report that shows blanks becomes a completeness and content-validation requirement; a shifted delivery size becomes a count investigation and a separately justified acceptance boundary.

In Glue Studio, the data-quality transform can return rule outcomes and row-level results. `DataQualityEvaluationResult` provides `Passed` or `Failed` for a row. AWS explicitly notes that a row can pass while the overall result fails, for example when `RowCount` fails but the row's other rules pass. Preserve both levels in the release evidence.

Configure an enforcement action. Under **On ruleset failure**, **None** is the default: the job continues despite ruleset failures. **Fail job without loading to target data** stops the job immediately and does not load targets, including the transform's results. Choose this when the release must stop before target loading, and design how diagnostic evidence is retained for that path. The third option, **Fail job after loading data to target**, is documented as failing the job with no data saved; specify an S3 location to retain its data-quality results.

Do not confuse a rule expression with its execution scope. DQDL composite rules evaluate component rules over the dataset by default and then combine their results. When the requirement is SQL-like row evaluation, the documented code example sets `compositeRuleEvaluation.method` to `ROW` in `additionalOptions`. Ratio-based rules such as `Completeness`, `DatasetMatch`, `ReferentialIntegrity`, and `Uniqueness` are excluded from that composite row evaluation. `ColumnDataType`, `ColumnValues`, and `CustomSql` also cannot participate when they include `with threshold`. Verify the chosen rules instead of assuming every aggregate can be applied per record.

### Instrument Lambda at two levels

Lambda publishes `Invocations`, `Errors`, `Throttles`, and `Duration`. Use `Sum` for invocation outcome counts. `Errors` counts invocations with function errors, including thrown exceptions and runtime failures. Throttled requests do not contribute to `Invocations` or `Errors`. `Duration` measures execution time in milliseconds and excludes cold start time.

Those metrics answer whether the validator ran and how it behaved operationally. They do not count semantic rejections unless your implementation deliberately maps rejection to an exception. Prefer a documented application disposition so expected bad input and infrastructure failure remain distinguishable.

For content quality, publish application-defined counters through CloudWatch `PutMetricData`. Specify `Namespace`, `MetricData`, `MetricName`, and `Value`, with dimensions that identify the relevant pipeline or rule version. Example names such as `RecordsChecked`, `RecordsRejected`, and `ValidationUnavailable` are your design, not built-in Lambda metrics.

Use a consistent accounting unit. If one invocation handles twenty records, invocation counts cannot be the denominator of a record rejection rate. Count evaluated records and rejected records over the same scope. Keep validation that could not complete separate from a successful pass. A missing result must not silently become acceptable input.

## Key distinctions and trade-offs

**Exploration versus enforcement:** Data Wrangler helps find patterns worth checking. Glue rules and application validators produce release decisions. A downloaded report does not enforce tomorrow's delivery.

**Operational failure versus rejected content:** A function timeout needs operational recovery. An invalid field needs correction, quarantine, or a documented partial output. Combining them into one error count makes the next action ambiguous.

**Dataset scope versus row scope:** Count and schema checks can reject a delivery even when individual rows pass. Conversely, an acceptable aggregate missing-value rate can coexist with unusable records. Decide which output is permitted at each level.

**Metric versus evidence record:** Counters support trend detection; they cannot explain which source failed. Retain a separate validation record with source identity and failed rules, using the provenance approach in 1.3.5.

## Architecture / decision scenario

A support application imports supplier CSV files before generating account summaries. Data Wrangler's first-50,000-row report looks healthy, but the files are ordered by supplier. The team profiles the entire imported dataset and discovers blank strings and an invalid status value concentrated in a later supplier's records.

It adds Glue `Completeness` and content rules for required fields, plus `ColumnValues` for allowed status values. A dataset count check guards against a truncated delivery. Glue's failure action prevents loading a failed delivery into the accepted target. The team retains both ruleset results and row-level `DataQualityEvaluationResult` rather than treating either as the other.

A Lambda validator checks incoming event metadata and publishes application-defined checked, rejected, and unavailable counters through `PutMetricData`. Operators inspect `Errors` and `Throttles` when the validator cannot run. A rejection-rate increase triggers a data investigation even if Lambda's operational metrics remain healthy. Thus the profile discovers the defect, the rules enforce the contract, and telemetry identifies which kind of failure needs attention.

## Common exam traps

- Treating the first 50,000 imported rows as a random or complete population.
- Assuming a failed Glue ruleset automatically fails the job.
- Assuming row-level `Passed` overrides a failed dataset rule.
- Reading Lambda `Errors` as a built-in data-quality rejection count.
- Dividing record failures by invocation counts for batched processing.
- Using prediction rankings as a grounding or suitability score.

## What to remember

Profile with a declared population, enforce explicit DQDL and application rules, and measure execution separately from acceptance. Configure Glue's failure behavior deliberately. Publish custom content counters with matching denominators, and retain source-linked records that explain the counts.

## References

- AWS, [Get Insights On Data and Data Quality](https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-data-insights.html)
- AWS, [Evaluating data quality for ETL jobs in AWS Glue Studio](https://docs.aws.amazon.com/glue/latest/dg/tutorial-data-quality.html)
- AWS, [Data Quality Definition Language reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl.html)
- AWS, [Types of metrics for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- AWS, [PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
