---
layout: Conceptual
title: What is Microsoft Foundry? - Microsoft Foundry | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry
breadcrumb_path: ../breadcrumb/azure-ai/toc.json
feedback_help_link_url: https://learn.microsoft.com/answers/tags/133/azure
feedback_help_link_type: get-help-at-qna
feedback_product_url: https://feedback.azure.com/d365community/forum/79b1327d-d925-ec11-b6e6-000d3a4f06a4
feedback_system: Standard
permissioned-type: public
recommendations: true
recommendation_types:
- Training
- Certification
uhfHeaderId: azure-ai-foundry
ms.suite: office
author: sdgilley
learn_banner_products:
- azure
manager: mcleans
ms.author: sgilley
ms.collection: ce-skilling-ai-copilot
ms.update-cycle: 90-days
ms.service: microsoft-foundry
description: Microsoft Foundry is a trusted platform that empowers developers to build AI agents, models, and apps. Learn what you can build and how to choose your build approach.
ms.reviewer: nbrady
ms.date: 2026-08-13T00:00:00.0000000Z
ms.subservice: foundry-platform
ms.topic: overview
ai-usage: ai-assisted
ms.custom:
- classic-and-new
- ignite-2023
- build-2024
- ignite-2024
- build-aifnd
- build-2025
- doc-kit-assisted
keywords:
- Foundry Tools
- cognitive
locale: en-us
document_id: 52a4a7e6-19cd-f0f2-cdfb-762d7cc56935
document_version_independent_id: acde326f-6dee-6896-b5fc-7d8d38f2b8cb
updated_at: 2026-09-24T05:07:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/azure-ai-docs-pr/blob/live/articles/foundry/what-is-foundry.md
gitcommit: https://github.com/MicrosoftDocs/azure-ai-docs-pr/blob/faa3a600181c321d810335378964413d3a380325/articles/foundry/what-is-foundry.md
git_commit_id: faa3a600181c321d810335378964413d3a380325
site_name: Docs
depot_name: Learn.azure-ai
page_type: conceptual
toc_rel: toc.json
word_count: 1021
asset_id: foundry/what-is-foundry
moniker_range_name: 
monikers: []
item_type: Content
source_path: articles/foundry/what-is-foundry.md
cmProducts:
- https://microsoft-devrel.poolparty.biz/DevRelOfferingOntology/de19c5b8-e208-412e-9238-db3f631dea5b
- https://authoring-docs-microsoft.poolparty.biz/devrel/68ec7f3a-2bc6-459f-b959-19beb729907d
- https://microsoft-devrel.poolparty.biz/DevRelOfferingOntology/8a6e4dad-7050-4ce7-83f9-eb4123577a54
spProducts:
- https://microsoft-devrel.poolparty.biz/DevRelOfferingOntology/ea7bf5d6-7154-4ba9-8ebc-59117ccacd49
- https://authoring-docs-microsoft.poolparty.biz/devrel/90370425-aca4-4a39-9533-d52e5e002a5d
- https://microsoft-devrel.poolparty.biz/DevRelOfferingOntology/0a5fc323-00ce-4c20-9095-41948f54c83f
platformId: 86a0ca32-4cb3-f371-346b-152088b9f825
---

# What is Microsoft Foundry? - Microsoft Foundry | Microsoft Learn

Microsoft Foundry unifies agents, models, and tools under a single management grouping with built-in enterprise-readiness capabilities including tracing, monitoring, evaluations, and customizable enterprise setup configurations. The platform provides streamlined management through unified role-based access control (RBAC), networking, and policies under one Azure resource provider namespace.

Tip

- Coming from Azure OpenAI? [Upgrade your Azure OpenAI resource to a Foundry resource](how-to/upgrade-azure-openai) while preserving your endpoint, API keys, and existing state.
- Using hub-based projects? Hub-based projects are accessible in the [Foundry (classic) portal](../foundry-classic/what-is-foundry). New investments are focused on Foundry projects in the new portal.

## Get started

Build your first agent in minutes, or open the portal to explore models and tools.

[Open the Foundry portal](https://ai.azure.com) | [Get an Azure account](https://azure.microsoft.com/pricing/purchase-options/azure-account)

## What you can build

| Capability | Description |
| --- | --- |
| **Agents** | Build declarative [prompt agents](agents/quickstarts/prompt-agent) and managed [voice-based prompt agents](agents/quickstarts/prompt-voice-agent) in the portal or SDK, or deploy [hosted agents](agents/quickstarts/quickstart-hosted-agent) that run your own code. Learn more in [Foundry Agent Service](agents/overview). |
| **Models** | Access more than 10,000 models from Microsoft, OpenAI, Anthropic, Meta, and others. Browse the [Foundry Models catalog](concepts/foundry-models-overview). |
| **Tools and knowledge** | Extend agents with built-in tools, memory, and retrieval using a [Foundry Toolbox](agents/concepts/toolbox-overview). |

Not sure where to start? See the [product and capability map](concepts/capabilities) to match your goal to a starting point.

### Voice-based prompt agents

Build real-time, spoken experiences with a voice-based prompt agent in Foundry Agent Service. Configure the model, instructions, audio settings, optional greeting, and tools. Then connect to the agent through Voice Live. Foundry manages the agent lifecycle and voice orchestration, so you don't need to host that infrastructure yourself. For more information, see [Quickstart: Create a voice-based prompt agent](agents/quickstarts/prompt-voice-agent).

## Enterprise-ready platform

Foundry brings platform capabilities to every project. Some capabilities are in preview. For current status, see the [general availability overview](concepts/general-availability).

- **Observability:** Trace and evaluate agents and models, and monitor them with built-in dashboards (preview). See [Observability](concepts/observability).
- **Governance and security:** Apply Microsoft Entra identity, role-based access control, content filters, network isolation, and Azure Policy. See the [Foundry control plane](control-plane/overview).
- **One management plane:** Manage agents, models, and tools as a single Azure resource with unified access control, networking, and policies.

## Start by building an agent

Most projects on Foundry center on an agent: a model paired with instructions and tools that can reason over a request and take action. The main decision is how much you want to customize and control how that agent runs. Think of it as a spectrum from declarative to full code.

- **Declarative, with the least to manage.** Specify instructions, choose a model, and attach tools in the Foundry portal or with the SDK. Foundry hosts and runs the agent for you, with no application code or containers to maintain. In Foundry, this is a **prompt agent**. [Create a prompt agent](agents/quickstarts/prompt-agent). For a real-time spoken experience, build a **voice-based prompt agent**. [Create a voice-based prompt agent](agents/quickstarts/prompt-voice-agent).
- **Full code, with the most control.** Bring your own code or framework (for example, Microsoft Agent Framework, LangGraph, or Semantic Kernel), package it as a container, and Foundry runs it with a managed endpoint, scaling, identity, and observability. In Foundry, this is a **hosted agent**. [Deploy a hosted agent](agents/quickstarts/quickstart-hosted-agent).

You can start declarative and move to code as your needs grow. For a detailed comparison, see [What are hosted agents?](agents/concepts/hosted-agents). For the end-to-end build, test, and ship cycle, see the [agent development lifecycle](agents/concepts/development-lifecycle).

Not building an agent yet? If you only need to send prompts to a model with no tools or orchestration, start with a single [model call](quickstarts/get-started-code).

## Choose your developer surface

Foundry supports several surfaces. Many developers combine them, for example, prototyping in the portal and then moving to code.

| Surface | Best for | Start here |
| --- | --- | --- |
| **Foundry portal** | Exploring models, prototyping prompts, and building prompt agents without writing code. | [Playgrounds and quick evaluation](concepts/concept-playgrounds) |
| **SDKs** | Building applications in Python, C#, JavaScript, or Java. | [Microsoft Foundry SDKs](how-to/develop/sdk-overview) |
| **Azure Developer CLI (azd)** | Scaffolding, running, testing, and deploying Hosted agent projects from the command line. | [Develop agents with the Azure Developer CLI](agents/concepts/cli-agent-development) |
| **Visual Studio Code** | Building and debugging agents in your editor with the Foundry extension. | [Work in VS Code](how-to/develop/get-started-projects-visual-studio-code) |
| **Coding agents and MCP** | Driving Foundry from coding agents (for example, GitHub Copilot or Claude Code) with the Foundry Skill and MCP server. | [Use the Microsoft Foundry Skill in coding agents](how-to/develop/use-microsoft-foundry-skill) |

## Recommended path for new developers

Follow these steps to go from zero to a working integration:

1. **Make your first model call.** Set up your environment and send a prompt with the [build with models and agents quickstart](quickstarts/get-started-code).
2. **Set up your developer environment.** Install the CLI and SDK so you can build in code. See [Set up your developer environment](how-to/develop/install-cli-sdk).
3. **Choose a model.** Browse the catalog and compare options in the [Foundry Models overview](concepts/foundry-models-overview).
4. **Build your first agent.** Start with a [prompt agent](agents/quickstarts/prompt-agent), or go straight to a [Hosted agent](agents/quickstarts/quickstart-hosted-agent) if you want to bring your own code.
5. **Add tools and knowledge.** Extend your agent with tools, retrieval, and memory (preview). Start with the [toolbox overview](agents/concepts/toolbox-overview), the recommended way to add tools to an agent.

## Evolution of Foundry

Foundry consolidates several previous Azure AI services and tools into a unified platform. For detailed guidance on transitioning, see [Navigate from classic to the new experience](how-to/navigate-from-classic).

Previous concepts and their current equivalents

| Dimension | Previous | Current |
| --- | --- | --- |
| Brand | Azure AI Studio / Azure AI Foundry | Microsoft Foundry |
| Brand | Azure AI Services | Foundry Tools |
| Portal | [Foundry (classic)](/en-us/azure/foundry-classic/) | [Foundry](/en-us/azure/foundry) |
| Agent API | Assistants API (Agents v0.5/v1) | Responses API (Agents v2) |
| API versioning | Monthly `api-version` params | v1 stable routes (`/openai/v1/`) |
| Resource model | Hub + Azure OpenAI + Azure AI Services | Foundry resource (single, with projects) |
| SDKs & endpoints | Multiple packages (`azure-ai-inference`, `azure-ai-generative`, `azure-ai-ml`, `AzureOpenAI()`) against 5+ endpoints | Unified project client (`azure-ai-projects` 2.x) + `OpenAI()` against one project endpoint. |
| Terminology | Threads, Messages, Runs, Assistants | Conversations, Items, Responses, Agent Versions |