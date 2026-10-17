> This page is for version Main (default).
> For other versions, use one of these documentation indexes:
> - Main (default): https://docs.nvidia.com/nemo/gym/main/llms.txt
> - 0.7.0: https://docs.nvidia.com/nemo/gym/v0.7.0/llms.txt
> - 0.6.0: https://docs.nvidia.com/nemo/gym/v0.6.0/llms.txt
> - 0.5.1: https://docs.nvidia.com/nemo/gym/v0.5.1/llms.txt
> - 0.5.0: https://docs.nvidia.com/nemo/gym/v0.5.0/llms.txt
> - 0.4.0: https://docs.nvidia.com/nemo/gym/v0.4.0/llms.txt
> - 0.3.0: https://docs.nvidia.com/nemo/gym/v0.3.0/llms.txt
> - 0.2.1: https://docs.nvidia.com/nemo/gym/v0.2.1/llms.txt

> For clean Markdown of any page, append .md to the page URL.
> For a complete documentation index, see https://docs.nvidia.com/nemo/gym/llms.txt.
> For AI client integration (Claude Code, Cursor, etc.), connect to the MCP server at https://docs.nvidia.com/nemo/gym/_mcp/server.

# Build Verifiers

> Build the resources server that scores rollouts — the verifier, state, and verification patterns.

A verifier scores an agent's behavior on a task. In NeMo Gym you implement it in a **resources server** — the component that owns the verifier, per-task state, and any environment-specific tools.

> **Info**
>
> New to the concepts? Start with [Environments](/about/concepts/environments) and [Architecture](/about/architecture) to see how the resources server, agent server, and model server fit together.

## Resources Server Interfaces

You build a resources server by subclassing one of two base classes. At runtime it runs as a web server that the agent drives over HTTP:

* **`SimpleResourcesServer`** — the agent calls `/seed_session` at the start to initialize per-task state (optional) and `/verify` at the end to score the rollout. Tools are exposed as additional endpoints or over MCP.
* **`GymnasiumServer`** — scores incrementally via `/step` (with `/reset` at the start) instead of a single `/verify`, for environments that need per-turn observations and rewards. `GymnasiumServer` is provided by the bundled `resources_servers/gymnasium/` package, not the core `nemo_gym` library — import it with `from resources_servers.gymnasium import GymnasiumServer`.

#### [Verification Patterns](/build-verifiers/verification-patterns)

How to score a rollout, from execution and state checks to LLM-as-Judge.

#### [Multi-Reward Verification](/build-verifiers/multi-reward-verification)

Score an agent on several objectives at once.