---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-2"
title: "Turn input profiles into enforced checks"
description: "Combine Data Wrangler profiling, Glue Data Quality rules, and Lambda quality telemetry without confusing exploration, enforcement, and execution health."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Validate and profile inputs using AWS Glue Data Quality, SageMaker Data Wrangler, and Lambda metrics.

## Core idea

As an architect, use profiling to discover input defects, validation to enforce an accepted contract, and metrics to observe that contract over time. These are complementary jobs. A profile does not reject the next invalid upload, and a successful Lambda invocation does not prove that its payload meets your foundation model's requirements.

SageMaker Data Wrangler helps inspect and prepare datasets. AWS Glue Data Quality runs explicit rules over datasets and in ETL pipelines. Lambda can validate individual events and publish application-defined measurements to CloudWatch. Choose the scope of each check from 1.3.1, then connect its result to an actual admission decision.

## How it works

### Discover defects with Data Wrangler

AWS documents Data Wrangler in Amazon SageMaker Canvas for the updated Studio experience. Its data flow represents preparation steps, including transformations, analysis, and export. Use the **Data Quality and Insights Report** to inspect missing and invalid values, feature types, outliers, and duplicate samples before deciding which conditions should become production rules.

The report can also examine a target column for classification or regression, expose class imbalance, and highlight possible target leakage. Those analyses answer questions about a prediction dataset. They do not establish that a foundation model's eventual answer is correct. A quick model's predictive performance and a generative assistant's evidence quality are different evaluation targets.

Record what data the profile actually covers. The documented report options include **50 K**, which uses the first 50,000 imported rows, and **Entire dataset**, which uses a SageMaker Processing job. The first 50,000 rows are not a random sample of all production sources. If a file is ordered by branch or date, its opening rows can conceal defects elsewhere. Match the report scope to the population named in the quality policy.

Interpret unusual values with domain knowledge. A rare currency can be legitimate; a frequently repeated row can be a real repeated observation. Use the profile to find candidates for investigation, then encode only reviewed requirements. Do not turn every outlier into a deletion rule.

### Enforce reviewed rules with Glue

AWS Glue Data Quality has separate Data Catalog and ETL entry points. Data Catalog evaluations suit already cataloged datasets. ETL checks can validate data before loading it and identify individual failed records. Do not assume that every capability is shared: AWS's comparison lists failed-record identification for ETL, not Data Catalog evaluations. Flatten nested or list-type input structures before evaluating them; Glue documents these structures as unsupported by data quality rules.

In an ETL script, `EvaluateDataQuality.apply` evaluates a DQDL ruleset against a `DynamicFrame` and returns evaluation results. Its result fields include `Rule`, `Outcome`, `FailureReason`, and `EvaluatedMetrics`. Retain the failed rule and measured value so an operator can distinguish a changed source format from missing source data.

The Glue Studio data quality transform can add `DataQualityRulesPass`, `DataQualityRulesFail`, `DataQualityRulesSkip`, and `DataQualityEvaluationResult` to its row-level output. Route rows using these documented fields, but also inspect dataset-level results. A failed `RowCount` rule can coexist with row-level `Passed` values because no particular row causes the count failure. Consult the rule-type reference for whether a rule supports row-level results; a skipped row-level evaluation is not evidence that the dataset passed.

Configure the failure consequence deliberately. Glue Studio's **On ruleset failure** action defaults to **None**, so a job can continue despite failed rules. Select an appropriate failure action when the whole dataset must be withheld, or explicitly separate accepted and rejected rows when partial publication is permitted. An S3 output existing is not an acceptance signal by itself.

For published evidence, `publishing_options` includes `enableDataQualityCloudWatchMetrics`, `dataQualityEvaluationContext`, `enableDataQualityResultsPublishing`, and `resultsS3Prefix`. CloudWatch publication is disabled by default in the documented transform options. Enable it explicitly when the operating process depends on those metrics; retain detailed results as well as aggregate signals.

### Measure Lambda validation separately from execution

A Lambda validator can reject malformed records according to your application contract and still return successfully. Lambda's built-in `Errors` counts function and runtime errors, including timeouts; it does not count all business rejections. `Invocations` counts executed invocations, while throttled requests count in `Throttles` rather than `Invocations` or `Errors`. `Duration` measures execution time, not input correctness.

Publish quality measurements with CloudWatch `PutMetricData`. Supply a custom `Namespace` and `MetricData` entries containing `MetricName`, `Value`, and appropriate `Dimensions`. For example, your application might define `RecordsExamined`, `RecordsRejected`, and `MissingRequiredField`. These are names you define, not built-in Lambda metrics. Use bounded dimensions such as source type and rule version; keep individual document identifiers in detailed evidence.

Choose a coherent denominator. One Lambda invocation can inspect many records, so `RecordsRejected / Invocations` is not the rejected-record fraction. Compare sums of rejected and examined records over the same population and period. Preserve failure reasons separately so a rising rejection rate identifies a specific quality problem rather than merely producing an alarm.

## Key distinctions and trade-offs

Profiles describe the data inspected; rules determine accepted conditions; metrics summarize observed events. None substitutes for the others. A useful profile suggests a rule, a rule produces a decision, and telemetry reveals whether its outcomes change by source or release.

Dataset checks catch failures that event validators cannot see in isolation, such as a missing partition or a broken relationship to a reference dataset. Event validators can reject a malformed upload before expensive batch work. Use both when both failure modes matter, while keeping their populations and thresholds explicit.

## Architecture / decision scenario

A support assistant consumes monthly account exports and individual ticket uploads. Data Wrangler's report reveals duplicate export rows and missing account identifiers. The team examines the entire dataset before approving identifier and duplication requirements; a profile of its first rows would miss one supplier's malformed records.

The batch pipeline evaluates DQDL rules in Glue ETL. It retains `FailureReason` and `EvaluatedMetrics`, withholds the batch if coverage fails, and uses row-level failure columns for permitted partial rejection. It explicitly configures **On ruleset failure**, rather than treating job completion as approval.

The ticket Lambda applies the corresponding per-record checks and publishes application-defined examined and rejected counts through `PutMetricData`. Operators compare these with `Errors`, `Throttles`, and `Duration`. A rising business-rejection rate with stable execution metrics points toward source quality; rising runtime errors require a separate operational investigation. Every admission decision remains traceable to the rules that produced it.

## Common exam traps

- Treating a first-50,000-row profile as representative of every source.
- Using Data Wrangler's quick model as a generative-answer quality score.
- Assuming Data Catalog evaluations expose the same failed-record outputs as ETL.
- Interpreting row-level `Passed` as proof that all dataset rules passed.
- Assuming Glue rules automatically fail the job or publish CloudWatch metrics.
- Reading Lambda `Errors` as the number of invalid business records.

## What to remember

Discover requirements with Data Wrangler, enforce them with explicit Glue or application checks, and observe them with correctly defined metrics. Name the dataset, rule version, result field, and consequence. Keep business rejection separate from runtime failure and avoid ratios whose numerator and denominator count different units.

## References

- AWS, [Data preparation](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-data-prep.html)
- AWS, [Get Insights On Data and Data Quality](https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-data-insights.html)
- AWS, [AWS Glue Data Quality](https://docs.aws.amazon.com/glue/latest/dg/glue-data-quality.html)
- AWS, [EvaluateDataQuality class](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-crawler-pyspark-transforms-EvaluateDataQuality.html)
- AWS, [Evaluating data quality for ETL jobs in AWS Glue Studio](https://docs.aws.amazon.com/glue/latest/dg/tutorial-data-quality.html)
- AWS, [DQDL rule type reference](https://docs.aws.amazon.com/glue/latest/dg/dqdl-rule-types.html)
- AWS, [Types of metrics for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- AWS, [PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
