---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-4"
title: "Match preprocessing compute to work boundaries"
description: "Choose SageMaker Processing or Lambda by transformation scope, resource needs, execution limits, and the contract for accepting results."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose SageMaker Processing for batch preprocessing versus Lambda for event-driven transformations.

## Core idea

For an architect preparing foundation model inputs, the trigger and the compute boundary are separate decisions. An uploaded file can trigger Lambda, which performs a small transformation or submits a SageMaker Processing job. A scheduled batch can also contain small transformations. “An event arrived” does not prove that all its work belongs inside one function invocation.

Choose Lambda for bounded event transformations that fit its execution environment. Choose SageMaker Processing when the work is a dataset job with explicit input artifacts, container dependencies, compute resources, and output artifacts. Decide from measured work size and resource needs, then define how the application observes completion and validates the result.

## How it works

### Bound the Lambda transformation

Amazon S3 can invoke Lambda asynchronously with an event describing an object. Use the event as a reference to work rather than putting a large source file into the invocation payload. Retrieve the source under the application's access controls, validate it, and write a separate derived artifact.

The documented Lambda limits give concrete boundaries. The standard function timeout has a maximum of 900 seconds, or 15 minutes. The quota page qualifies this: Lambda Managed Instances supports up to 5,400 seconds, or 90 minutes, for asynchronous invocations and event source mapping invocations except Amazon MQ and Amazon DocumentDB. Do not describe 15 minutes as a universal limit for every Lambda configuration.

Function memory ranges from 128 MB to 10,240 MB, and `/tmp` storage ranges from 512 MB to 10,240 MB. CPU allocation scales with configured memory; increasing memory changes more than storage capacity for Python objects. Benchmark the complete operation, including download, decoding, transformation, validation, and upload. A compressed input's file size is not its peak working-memory requirement.

Invocation payload limits are 6 MB for synchronous requests and responses and 1 MB for asynchronous invocation. These are invocation boundaries, not maximum S3 object sizes. A small event can identify a large object whose processing still exceeds the function's time, memory, or temporary-storage budget.

Watch where derived files are written. AWS warns that a function writing to the same bucket that triggers it can create an invocation loop. Use separate buckets or an incoming-prefix trigger that excludes outputs. This routing choice is part of the transformation design, not an incidental bucket naming preference.

### Define the SageMaker Processing job

SageMaker Processing runs preprocessing, postprocessing, feature engineering, and evaluation work on managed infrastructure. It launches resources for a processing job and releases them after completion. You can use supplied processing containers or bring a container with the required libraries.

`CreateProcessingJob` makes the job contract explicit. `AppSpecification.ImageUri` selects the container, while `ContainerEntrypoint` and `ContainerArguments` define its invocation. `ProcessingResources.ClusterConfig` identifies `InstanceType`, `InstanceCount`, and `VolumeSizeInGB`. `RoleArn` identifies the role SageMaker assumes, and `StoppingCondition.MaxRuntimeInSeconds` bounds the job's execution.

`ProcessingInputs` describes the input data; `ProcessingOutputConfig.Outputs` describes outputs. For S3 inputs, `S3Input.S3Uri` identifies data and `LocalPath` defines where the container receives it. The documented local input path begins with `/opt/ml/processing/`. Keep accepted output and validation evidence distinct, even when both are produced by the same job.

Input distribution determines whether additional instances perform useful parallel work. `S3DataDistributionType: FullyReplicated` sends the data to all processing instances. `ShardedByS3Key` distributes S3-key shards among instances. Choosing more instances does not by itself partition a single large object's records or make a script distributed. Match file layout and processing logic to the distribution setting.

`S3InputMode: File` copies input to the local volume before the container starts processing. `Pipe` streams input into named pipes without using the ML storage volume for that input. Select the mode from the container's reading behavior: code that requires random access to local files cannot automatically consume a stream.

### Observe execution and acceptance independently

Submitting `CreateProcessingJob` does not supply accepted preprocessing output. `DescribeProcessingJob.ProcessingJobStatus` distinguishes `InProgress`, `Completed`, `Failed`, `Stopping`, and `Stopped`; `FailureReason` explains a failed job. The application must still inspect its validation artifacts before admitting the output to foundation model consumption.

For Lambda, built-in `Errors`, `Throttles`, and `Duration` expose operational behavior. They do not establish whether a transform preserved all required fields or produced suitable evidence. Use the quality results described in 1.3.2 for that decision. A successfully executed transformation can be a correctly completed rejection.

## Key distinctions and trade-offs

Lambda's event integration is useful for quick validation, normalization, and dispatch. SageMaker Processing makes a dataset and its resource configuration the job boundary. A hybrid design can keep event handling short while delegating substantial processing to a tracked job.

SageMaker Processing adds job submission, resource startup, and result tracking. Lambda avoids that job lifecycle for small work, but every invocation still needs a bounded resource budget. Measure total time to accepted output, including queueing and data movement; compare the workload you actually have rather than assuming that “serverless” or “batch” determines performance.

Choose reproducibility deliberately. Retain the processing image identity, arguments, source set, and validation policy with a batch result. For an event transformation, retain the deployed transform version and source identity. Compute selection changes the execution unit; it does not remove the need to explain how a derived artifact was produced.

## Architecture / decision scenario

A service receives small support-ticket JSON files throughout the day and rebuilds a large historical document dataset overnight. The ticket transformation validates required fields and normalizes a few values. A benchmark includes S3 transfer and output validation and fits comfortably within the selected Lambda limits, so the event path transforms each ticket directly.

The historical rebuild needs a fixed library stack, substantial local working storage, and dataset-wide checks. It uses `CreateProcessingJob` with a recorded image, cluster configuration, inputs, outputs, and runtime bound. Separate source objects allow `ShardedByS3Key` to distribute work; a shared reference input uses `FullyReplicated` when every worker needs it.

An S3 event can still launch that batch path through Lambda. The function records the job association and returns rather than waiting for the entire rebuild. The release process requires `Completed` plus passed validation artifacts before publishing results. Output prefixes are excluded from the incoming S3 trigger, preventing derived files from launching the same work again.

## Common exam traps

- Equating event-driven dispatch with transformation inside Lambda.
- Applying the standard 15-minute limit to every Managed Instances invocation.
- Confusing a small event payload with a small processing workload.
- Assuming extra Processing instances automatically shard records inside one file.
- Giving a file-based script a `Pipe` input without adapting its reader.
- Accepting outputs solely because a function returned or a job reached `Completed`.

## What to remember

Choose the execution unit from work scope, measured resource needs, and completion semantics. Lambda suits bounded event transformations; SageMaker Processing suits explicit dataset jobs and containerized processing. Name the relevant limits, distribution mode, status field, and independent validation gate before approving the architecture.

## References

- AWS, [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- AWS, [Process Amazon S3 events with Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-s3.html)
- AWS, [Data transformation workloads with SageMaker Processing](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html)
- AWS, [CreateProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateProcessingJob.html)
- AWS, [ProcessingS3Input](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingS3Input.html)
- AWS, [DescribeProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeProcessingJob.html)
- AWS, [Types of metrics for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
