---
kind: "bite"
itemId: "aws-aip-2026-10-1-3-4"
title: "Place preprocessing within its execution budget"
description: "Choose SageMaker Processing or Lambda from preprocessing duration, resources, data distribution, and completion requirements."
publishedAt: "2026-10-10"
lastUpdatedAt: "2026-10-10"
---

## Learning objective

Choose SageMaker Processing for batch preprocessing versus Lambda for event-driven transformations.

## Core idea

An architect should place a transformation where its complete working set and
execution contract fit. SageMaker Processing runs preprocessing workloads as
managed jobs with selected compute resources and input/output configuration.
Lambda runs event-driven transformations within a configured invocation budget.
Neither a file extension nor the word “batch” decides the choice by itself.

Separate the trigger from the worker. An S3 object-created event can invoke a
short Lambda transformation, or a Lambda handler can submit a larger Processing
job and record its identity. Receiving an event does not require completing all
preprocessing inside that invocation. Conversely, a small bounded batch can fit
in Lambda if its measured resource needs and delivery contract permit it.

## How it works

### Model the whole transformation

Estimate input size, decoded working set, intermediate storage, dependency load,
compute needs, and runtime under adverse inputs. A compressed archive or image
can expand substantially during processing. Size for the decoded representation
and temporary outputs rather than the uploaded object's byte count alone.

Measure the entire worker path: loading dependencies, reading input, transforming,
validating, and writing the accepted result. A benchmark that times only the core
transformation can choose a worker that times out during source transfer or
publication. Keep headroom for variable inputs rather than planning at the hard
execution boundary.

Quality policy stays independent of placement. Whether the worker is Lambda or
Processing, the pipeline must distinguish accepted data, rejected data, and an
unfinished transformation. See 1.3.1 for quality gates and 1.3.2 for telemetry.

### Use Lambda for bounded event work

Amazon S3 invokes Lambda asynchronously for configured object events. The event
contains object details, so use it to locate the data rather than embedding the
full source in the event. The handler can validate metadata, normalize a small
record, or submit longer work to another service.

Lambda's standard function timeout is 900 seconds. Configurable memory ranges
from 128 MB to 10,240 MB; CPU allocation increases with memory. Temporary `/tmp`
storage ranges from 512 MB to 10,240 MB. These limits bound different resources:
more temporary storage does not enlarge memory, and a larger package does not
increase available runtime.

Scope the timeout claim carefully. AWS documents a 5,400-second maximum for
Lambda Managed Instances functions invoked asynchronously or through event source
mappings, except Amazon MQ and Amazon DocumentDB. Do not treat 15 minutes as a
universal limit across that configuration, or assume the longer maximum applies
to every Lambda invocation. State the execution mode before making a decision
from a timeout.

Invocation payloads also differ: synchronous requests and responses have a 6 MB
limit each, while asynchronous invocation payloads have a 1 MB limit. These are
invocation limits, not maximum S3 object sizes the handler can read. A pointer
to an object avoids carrying its full content in the invocation, but the worker
still needs enough time, memory, and storage to process it.

Keep derived writes outside the triggering input path. AWS warns that writing
objects into the same triggering bucket can cause an invocation loop. Use two
buckets or restrict the notification to the incoming prefix. A successful
transformation that recursively triggers itself is an operational failure.

### Use Processing for managed batch jobs

Submit a SageMaker Processing job with `CreateProcessingJob`.
`AppSpecification.ImageUri` selects the processing container. `ProcessingInputs`
defines inputs, `ProcessingResources.ClusterConfig` selects compute and storage,
`ProcessingOutputConfig` defines outputs, and `RoleArn` supplies the execution
role. This is a job configuration, not a hosted inference endpoint.

For S3 inputs, `S3InputMode` selects `File` or `Pipe`. `File` copies input onto the
local ML storage volume before the container starts. `Pipe` streams input through
named pipes without staging it on that volume. Your processing code must support
the chosen access pattern; code that seeks randomly through a local file cannot
be assumed to work unchanged on a pipe.

`S3DataDistributionType` selects `FullyReplicated` or `ShardedByS3Key`.
Replication gives the input to all processing instances. Sharding distributes S3
keys among them. Increasing instance count does not automatically parallelize
one large object or implement global aggregation correctly. Partition records
and combine results deliberately when the transformation requires that behavior.

Set `StoppingCondition.MaxRuntimeInSeconds` to bound the job. The API allows
values from 1 to 777,600 seconds. That ceiling is not a recommended job duration;
choose a bound from your measured workload and recovery policy. SageMaker
launches resources for the job and releases them on completion, with outputs
stored in the specified S3 location.

## Key distinctions and trade-offs

Lambda avoids introducing a separate job lifecycle for short event work, but
each invocation must fit its configured operating envelope. Processing exposes
container, instance, distribution, and output choices for larger jobs, while
requiring the caller to track submission and completion separately.

Latency-sensitive event handling and throughput-oriented preprocessing can use
different workers in one pipeline. The event handler acknowledges durable work
submission; a later completion path validates and publishes output. Do not make
the short handler wait merely to present a long job as a synchronous action.

Local processing and distributed processing also carry different correctness
risks. A per-file normalization can shard naturally. A global deduplication or
join requires coordination across partitions. The job configuration provides
resources and data placement; your transformation still owns its algorithm.

## Architecture / decision scenario

A support assistant receives small ticket records throughout the day and a
nightly archive of scanned manuals. Measurements show that a ticket's metadata
normalization and schema checks finish in seconds with a small working set.
An S3 event invokes Lambda, which reads the object, writes an accepted result to
a separate output path, and records the quality decision.

The manuals require a container with document-processing dependencies, large
intermediate files, and a dataset-wide reconciliation step. The intake handler
submits `CreateProcessingJob` and records its job identity. The team selects
`File` mode because the parser requires local seekable input. It uses
`ShardedByS3Key` for independent manual files and an explicit reconciliation
stage for delivery-wide counts.

The job has a measured runtime budget expressed through
`MaxRuntimeInSeconds`. Publication waits for completion and required quality
checks; an output prefix existing is insufficient. If one manual becomes too
large, the team revisits partitioning and resources rather than increasing the
Lambda timeout indiscriminately. The event trigger remains useful even though
the heavy transformation runs elsewhere.

## Common exam traps

- Treating an event trigger as a requirement to finish all work in Lambda.
- Applying 900 seconds universally without checking Lambda execution mode.
- Confusing invocation payload size with the size of an S3 source object.
- Assuming more Processing instances split one object automatically.
- Assuming `Pipe` supports the same file-access behavior as `File`.

## What to remember

Place preprocessing by measured runtime, working set, storage, and access pattern.
Use Lambda for bounded event work and Processing for jobs that need its execution
contract. Separate job submission from completion, and keep quality acceptance
independent of compute placement.

## References

- AWS, [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- AWS, [Using AWS Lambda with Amazon S3](https://docs.aws.amazon.com/lambda/latest/dg/with-s3.html)
- AWS, [Data transformation workloads with SageMaker Processing](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html)
- AWS, [CreateProcessingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateProcessingJob.html)
- AWS, [ProcessingS3Input](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingS3Input.html)
- AWS, [ProcessingStoppingCondition](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingStoppingCondition.html)
