---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-4"
title: "Match preprocessing compute to workload boundaries"
description: "Choose SageMaker Processing or Lambda from preprocessing duration, resources, input delivery, and completion requirements."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose SageMaker Processing for batch preprocessing versus Lambda for event-driven transformations.

## Core idea

Choose the execution unit before choosing the service. A bounded transformation of an arriving object fits an event handler. A dataset transformation with explicit compute, storage, and artifact outputs fits a processing job. Arrival by event does not require all computation to happen inside that event's Lambda invocation.

SageMaker Processing runs preprocessing, postprocessing, feature engineering, and evaluation tasks on managed infrastructure. Lambda can process an S3 notification when an object arrives. A combined design can use Lambda to validate an event and submit a SageMaker Processing job, while the job owns the longer computation.

The deciding evidence is the measured workload: execution time, memory, local working data, dependency packaging, and output acceptance. The label “batch” or “serverless” alone does not establish fit.

## How it works

### Treat Processing as a job with explicit artifacts

`CreateProcessingJob` defines the processing job. `AppSpecification.ImageUri` identifies its container image, `ProcessingInputs` identifies input data, `ProcessingOutputConfig` defines outputs, and `ProcessingResources.ClusterConfig` specifies compute and storage. `RoleArn` identifies the IAM role SageMaker assumes for the work.

SageMaker launches the compute instances, processes the data, stores configured output in S3, and releases the resources after completion. You can use built-in processing containers or your own container. This makes the job a useful boundary for a dataset release: record its container, inputs, parameters, and output locations together.

For S3 inputs, `S3DataType` selects `S3Prefix` or `ManifestFile`. A prefix selects matching objects; a manifest lists object keys. A manifest makes the intended membership explicit, but a list of mutable keys alone does not freeze their contents. For reproducible processing, arrange stable input copies or otherwise pin the source revision in your application contract.

`S3InputMode` separates `File`, which copies inputs to the local storage volume before container processing, from `Pipe`, which streams them through named pipes. Select it based on how the container reads data and how much working storage the operation needs. With the default `AppManaged=False`, `LocalPath` must begin with `/opt/ml/processing/`.

For multiple instances, `S3DataDistributionType` distinguishes `FullyReplicated` from `ShardedByS3Key`. Sharding distributes objects by S3 key; it does not promise that one large object is divided into balanced rows or that your algorithm becomes distributed automatically. Choose object boundaries and container logic that match the distribution setting.

Set `StoppingCondition.MaxRuntimeInSeconds` to bound the job. Choose the value from the workload deadline rather than assuming submission guarantees timely completion. Keep validation failures and incomplete output separate from an accepted dataset release.

### Treat Lambda as a bounded event transformation

S3 can invoke Lambda asynchronously with an event containing object details. Use that reference to locate the source rather than embedding the whole media object in the invocation payload. A handler can validate metadata, normalize a small record, or submit a processing job after checking the event contract.

The standard Lambda function timeout is 900 seconds, or 15 minutes. Memory allocation ranges from 128 MB to 10,240 MB, with CPU allocated in proportion to memory. Configurable `/tmp` storage ranges from 512 MB to 10,240 MB. Evaluate working size after decoding or expanding the input; a small compressed object can still require more scratch space than your configuration provides.

Invocation payload limits are separate from S3 object sizes: synchronous buffered requests and responses are each limited to 6 MB, and asynchronous invocation payloads to 1 MB. Passing an object reference avoids placing the object's bytes inside that event, but does not remove download, memory, or runtime requirements from your transformation.

Scope the timeout correctly. AWS documents an exception for Lambda Managed Instances: asynchronous invocations and event source mapping invocations, except Amazon MQ and Amazon DocumentDB, support up to 5,400 seconds, or 90 minutes. Do not use “Lambda always stops at 15 minutes” as a universal rule. Verify the configured execution model before applying its limit.

Prevent feedback loops in the S3 integration. If your handler writes into the bucket that triggers it, an output object can trigger another invocation. Use separate input and output buckets or configure notifications only for the incoming prefix. A naming convention helps only when the trigger configuration actually enforces the boundary.

### Define what completion means

A handler returning after `CreateProcessingJob` has submitted work is not evidence that preprocessing finished. Record the job identity and use `DescribeProcessingJob.ProcessingJobStatus` to distinguish `InProgress`, `Completed`, `Failed`, `Stopping`, and `Stopped`. Keep the data unavailable until the status is `Completed` and output validation passes; retain `FailureReason` when the job fails. Conversely, a function that performs the entire transformation needs an explicit accepted or rejected result for that object.

Use the same acceptance contract whichever compute service runs the code. A successful process can produce empty or malformed output. Check record counts, required fields, and source coverage before publication; 1.3.1 owns those quality thresholds. This preserves the distinction between choosing adequate compute and proving acceptable data.

## Key distinctions and trade-offs

**Event trigger versus execution destination:** An S3 event can initiate a batch job. Trigger type describes arrival; it does not dictate where the expensive work runs.

**Job resources versus invocation resources:** Processing exposes instance count, instance type, and volume configuration. Lambda exposes its function resource envelope. Compare the actual algorithm and working set against the selected envelope.

**Sharding versus parallel correctness:** `ShardedByS3Key` assigns objects to instances. Global deduplication or cross-file joins still need an algorithm that reconciles data across those partitions.

**Capacity limit versus deadline:** A service's maximum runtime defines eligibility. Your workflow deadline defines whether the work is useful. Leave time for input loading, validation, and output delivery in the measured budget.

## Architecture / decision scenario

A knowledge pipeline receives small product updates throughout the day and rebuilds a document corpus overnight. Each product update needs a short schema check and deterministic normalization, so a Lambda handler processes the incoming object and writes to a separate prepared-data destination.

The corpus rebuild takes 40 minutes in the team's benchmark and needs a large local working set plus a custom container. The team chooses SageMaker Processing with a fixed input manifest, explicit volume capacity, and a bounded `MaxRuntimeInSeconds`. Independent source objects use `ShardedByS3Key`; the container retains a reconciliation stage for cross-file duplicates.

An arrival event can submit that job, but the handler stores its identity rather than claiming the corpus is ready. The workflow publishes only after job completion and quality validation. The decision follows the resource and completion contract; it does not rest solely on the 15-minute limit, because the documented Managed Instances exception has a different scope.

## Common exam traps

- Assuming event-driven arrival requires Lambda to do the entire transformation.
- Treating `CreateProcessingJob` submission as completed preprocessing.
- Confusing an S3 object's size with Lambda's invocation payload size.
- Assuming key-based sharding distributes records inside a single file.
- Applying the standard Lambda timeout to every Managed Instances invocation path.
- Writing outputs into an unfiltered S3 trigger path and creating a loop.

## What to remember

Use Lambda for work that fits the selected invocation envelope. Use Processing when the dataset job needs explicit containers, compute, storage, and artifact outputs. Separate submission, execution completion, and validated publication in either design.

## References

- AWS, [Data transformation workloads with SageMaker Processing](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html)
- AWS, [CreateProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateProcessingJob.html)
- AWS, [ProcessingS3Input](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingS3Input.html)
- AWS, [DescribeProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeProcessingJob.html)
- AWS, [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- AWS, [Process Amazon S3 event notifications with Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-s3.html)
