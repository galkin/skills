---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-4"
title: "Match preprocessing compute to execution bounds"
description: "Choose SageMaker Processing or Lambda from workload resources, completion behavior, and event-handling requirements."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose SageMaker Processing for batch preprocessing versus Lambda for event-driven transformations.

## Core idea

Choose preprocessing compute from the unit of work and its resource envelope. A bounded transformation of one arrival event fits a different execution contract from a dataset-wide conversion with a container, substantial working storage, and a separately observed job lifecycle.

SageMaker Processing runs preprocessing, postprocessing, feature engineering, and evaluation work on managed infrastructure. Lambda runs event-handling code within function execution limits. These are useful architecture patterns, not exclusive trigger categories: an event handler can submit a processing job. The arrival of an event does not require the entire transformation to run inside that handler.

Service selection is separate from extraction selection in 1.3.3 and from the cross-modality validation contract in 1.3.5. Here the question is where the transformation executes and what evidence establishes its completion.

## How it works

### Define the batch as a processing job

SageMaker AI accepts `CreateProcessingJob` requests. `AppSpecification` selects the processing container. `ProcessingInputs` describes inputs, and `ProcessingOutputConfig` defines outputs, including S3 destinations. `ProcessingResources.ClusterConfig` carries instance and volume configuration, including `InstanceCount`, `InstanceType`, and `VolumeSizeInGB`.

The processing service provisions compute, processes the input, stores output at the configured destination, and releases the compute resources on completion. AWS documents S3 input storage, with Athena and Redshift also available as input sources. A processing job is a managed execution of your transformation, not an automatic definition of what makes the transformed data acceptable.

Choose this contract when the work benefits from explicit dataset inputs and outputs, a selected processing container, and resources appropriate to the batch. Examples include converting a historical image collection or normalizing a tabular snapshot. These are architecture examples; the appropriate resources still come from measurements of your implementation.

Set `StoppingCondition.MaxRuntimeInSeconds` to an intentional deadline for the job. Its documented range is 1–777,600 seconds, so a Processing job can have a maximum runtime of 9 days. Record the processing job name alongside the source snapshot and transformation version. A larger execution envelope does not remove the need to bound runtime or detect a stuck transformation.

`CreateProcessingJob` accepting the request is not completion. Use `DescribeProcessingJob` and inspect `ProcessingJobStatus`, whose values include `InProgress`, `Completed`, `Failed`, `Stopping`, and `Stopped`. If the job fails, `FailureReason` provides a reason. Publish the accepted output only after completion and the application's validation conditions both hold.

### Bound the Lambda transformation

For ordinary Lambda function invocations, the timeout limit is 900 seconds, or 15 minutes. The quotas documentation specifies an exception for Lambda Managed Instances: asynchronous and eligible event-source-mapping invocations can use up to 5,400 seconds, or 90 minutes, excluding Amazon MQ and Amazon DocumentDB mappings. Compare those Lambda ceilings with Processing's 777,600-second maximum, and name the execution mode before using runtime as the deciding boundary.

Lambda's function memory setting ranges from 128 MB to 10,240 MB, and `/tmp` storage ranges from 512 MB to 10,240 MB. CPU allocation rises with configured memory. Test the peak working set of the actual transformation, including decompression and intermediate results, rather than comparing only the compressed source size with available storage.

Invocation payload boundaries also matter: request and response are each limited to 6 MB for synchronous invocation, while an asynchronous request is limited to 1 MB. Pass an object reference and metadata when the transformation should fetch a larger source from S3. An object reference reduces the event payload; it does not increase function memory, disk, or execution duration.

Select Lambda for work that fits those boundaries and has a clear event-level outcome, such as validating arrival metadata, normalizing a small record, or dispatching a processing job. Keep the source identity in the outcome so a retry can be recognized. A transformation that exceeds the chosen mode's limits needs a different partitioning or execution design.

### Separate triggering from doing the work

An arrival handler can validate metadata, identify a source revision, and submit `CreateProcessingJob`. The handler's successful return then means submission succeeded, not that the batch output is ready. Track the processing job separately with `DescribeProcessingJob` and apply the validation gate at its output boundary.

For a transformation that completes inside Lambda, inspect `Duration`, `Errors`, and `Throttles` to understand execution behavior. `Duration` excludes cold start time; do not treat it as the full end-to-end ingestion delay. `Throttles` identifies rejected invocation attempts, and those attempts do not count as `Invocations` or `Errors`.

Choose one publication contract for either path. The accepted artifact should identify its source and transformation, and consumers should be able to distinguish submitted, running, failed, and accepted work. These are application states you design, not a claim that Lambda and Processing share one native lifecycle API.

## Key distinctions and trade-offs

**Event trigger versus execution scope:** A file event can initiate a dataset job. Trigger type alone cannot decide whether the transformation belongs in Lambda or Processing.

**Payload versus working set:** Passing an S3 reference addresses invocation-message size. The processing code still needs enough time, memory, and scratch space for the fetched object and intermediates.

**Submission versus completion:** A job-submission handler can be healthy while the submitted job fails. Retain the job identifier and inspect the job's own status before releasing output.

**Resources versus correctness:** More memory or a larger instance can resolve resource exhaustion. It cannot repair a faulty normalization rule or establish that the output supports the intended FM task.

## Architecture / decision scenario

A claims assistant receives small JSON updates throughout the day and a nightly archive of historical images and tables. The example requirement is to make valid small updates available promptly while converting the archive through one reproducible batch release.

A Lambda handler validates and normalizes each small update. Measurements show that the work fits the selected function's timeout, memory, scratch space, and invocation payload contract. It writes a source-linked validation result and keeps rejected content distinct from execution failures.

The archive path also starts with an event, but the handler submits `CreateProcessingJob`. The job uses a chosen container, explicit `ProcessingInputs`, configured cluster resources, an S3 output destination, and `MaxRuntimeInSeconds`. The application records the processing job name and waits for `DescribeProcessingJob` to report `Completed` before checking output quality.

A failed batch leaves the prior accepted release in use. A successful submission alone cannot replace it. If archive size grows, the team remeasures compute and partitioning requirements; it does not force the archive into Lambda because the first signal happened to be an event.

## Common exam traps

- Treating event-driven arrival as proof the full transformation belongs in Lambda.
- Presenting 15 minutes as universal across every Lambda execution mode.
- Confusing compressed object size with the transformation's peak working set.
- Assuming an S3 reference bypasses execution or memory limits.
- Treating `CreateProcessingJob` success as an accepted output artifact.
- Passing a multi-megabyte record inline in an asynchronous Lambda invocation, whose payload limit is 1 MB rather than the synchronous 6 MB.

## What to remember

Use Lambda for bounded event work and SageMaker Processing for a managed dataset job with explicit resources and artifacts. Check the exact Lambda execution mode before applying timeout limits. Separate job submission, execution completion, and validated publication in either architecture.

## References

- AWS, [Data transformation workloads with SageMaker Processing](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html)
- AWS, [CreateProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateProcessingJob.html)
- AWS, [DescribeProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeProcessingJob.html)
- AWS, [ProcessingStoppingCondition](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingStoppingCondition.html)
- AWS, [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- AWS, [Types of metrics for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
