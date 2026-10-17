> This page is for version Latest (v1.5.1) (default).
> For other versions, use one of these documentation indexes:
> - Latest (v1.5.1) (default): https://docs.nvidia.com/dynamo/latest/llms.txt
> - dev: https://docs.nvidia.com/dynamo/dev/llms.txt
> - v1.5.1: https://docs.nvidia.com/dynamo/v1.5.1/llms.txt
> - v1.5.0: https://docs.nvidia.com/dynamo/v1.5.0/llms.txt
> - v1.4.2: https://docs.nvidia.com/dynamo/v1.4.2/llms.txt
> - v1.4.1: https://docs.nvidia.com/dynamo/v1.4.1/llms.txt
> - v1.4.0: https://docs.nvidia.com/dynamo/v1.4.0/llms.txt
> - v1.3.0: https://docs.nvidia.com/dynamo/v1.3.0/llms.txt
> - v1.2.1: https://docs.nvidia.com/dynamo/v1.2.1/llms.txt
> - v1.2.0: https://docs.nvidia.com/dynamo/v1.2.0/llms.txt
> - v1.1.1: https://docs.nvidia.com/dynamo/v1.1.1/llms.txt
> - v1.1.0: https://docs.nvidia.com/dynamo/v1.1.0/llms.txt
> - v1.0.2: https://docs.nvidia.com/dynamo/v1.0.2/llms.txt
> - v1.0.1: https://docs.nvidia.com/dynamo/v1.0.1/llms.txt
> - v1.0.0: https://docs.nvidia.com/dynamo/v1.0.0/llms.txt
> - v0.9.1: https://docs.nvidia.com/dynamo/v-0-9-1/llms.txt
> - v0.9.0: https://docs.nvidia.com/dynamo/v-0-9-0/llms.txt
> - v0.8.1: https://docs.nvidia.com/dynamo/v-0-8-1/llms.txt
> - v0.8.0: https://docs.nvidia.com/dynamo/v-0-8-0/llms.txt
> - v0.7.1: https://docs.nvidia.com/dynamo/v-0-7-1/llms.txt
> - v0.7.0: https://docs.nvidia.com/dynamo/v-0-7-0/llms.txt

> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/llms.txt. For full content including API reference and SDK examples, see https://docs.nvidia.com/dynamo/llms-full.txt.

# Router Guide

Use this guide to choose a router deployment topology. It does not replace the local or Kubernetes setup guides, which own the commands and manifests for each request path.

## Choose a Deployment Topology

| Topology | Where selection runs | Use it when | Setup guide |
| --- | --- | --- | --- |
| Frontend-embedded | Dynamo Frontend | Clients can call one Dynamo service directly. | [KV-Aware Routing for the CLI](/dynamo/cli/kv-aware-routing/overview) or [Dynamo Frontend Routing](/dynamo/kubernetes/kv-aware-routing/using-the-dynamo-frontend) |
| Gateway API | Dynamo Endpoint Picker Plugin (EPP) | A Kubernetes Gateway owns ingress policy and endpoint selection. | [KV-Aware Routing on Kubernetes](/dynamo/kubernetes/kv-aware-routing/overview) |
| Standalone | Dynamo router service | A custom request path or multi-tier architecture needs selection outside the Frontend. | [Standalone Router](/dynamo/cli/kv-aware-routing/standalone-router) |

The Frontend and EPP use the same worker selection behavior. Do not configure the Frontend to make another selection after an EPP has selected a worker.

## Choose a Routing Mode

Use `kv` mode when cache reuse should affect placement. Workers publish KV lifecycle events so the router can measure per-worker prefix overlap. Without worker events, `kv` mode uses load-only scoring; set `--no-router-kv-events` to predict cache state from routing decisions instead.

Use `round-robin`, `random`, `power-of-two`, `least-loaded`, or `device-aware-weighted` when cache state is not part of the decision. Use `direct` when an upstream component has already selected a worker. See [Routing Concepts](/dynamo/knowledge-base/modular-components/router/routing-concepts#basic-routing) for policy behavior and [Configuration and Tuning](/dynamo/knowledge-base/modular-components/router/configuration-and-tuning#kv-event-transport) for event transport.

<Info>
With `DYN_LORA_ENABLED`, use KV, random, or round-robin routing. Direct, power-of-two, least-loaded, and device-aware-weighted modes are not LoRA-aware and fail startup. Session affinity with LoRA is supported only in KV mode; random and round-robin plus affinity are rejected.
</Info>

## Configure Worker Sets Consistently

The Frontend's `--router-mode` sets the default routing configuration. A worker set can advertise its own router configuration, which replaces the Frontend configuration for requests routed to that set.

A worker set contains replicas with the same namespace, component, endpoint, model, and worker type. The first valid model deployment card observed by a Frontend reserves the set's configuration. Replicas with a different MDC checksum receive no traffic and cannot disrupt the incumbent, including during construction or retries. Once all incumbent workers disappear, the oldest remaining configuration becomes eligible for a fresh pipeline. See [Worker-Set Admission and Succession](/dynamo/knowledge-base/modular-components/router/configuration-and-tuning#worker-set-admission-and-succession) for checksum compatibility, rolling updates, and readiness behavior.

Worker-set configuration replaces rather than merges with the Frontend configuration. When a worker advertises `--router-mode kv`, restate every non-default router setting that it needs; omitting a setting selects that setting's default instead of inheriting the Frontend value. See [Configuration Scope and Precedence](/dynamo/knowledge-base/modular-components/router/configuration-and-tuning#configuration-scope-and-precedence) for examples and environment-variable implications.

## Choose Distributed Features Deliberately

Use [Disaggregated Serving](/dynamo/knowledge-base/modular-components/router/disaggregated-serving) for separate prefill and decode pools. Add [Topology-Aware KV Transfer](/dynamo/knowledge-base/modular-components/router/topology-aware-kv-transfer) when decode selection must honor transfer locality, and use the [Offloading Support Matrix](/dynamo/knowledge-base/modular-components/router/offloading-support-matrix) when lower cache tiers should influence routing.

For replicas, event recovery, and remote indexers, see [Router Operations](/dynamo/knowledge-base/modular-components/router/router-operations). For APIs that separate index, selection, or load tracking from the router process, see [Standalone Services](/dynamo/knowledge-base/modular-components/router/standalone-indexer).