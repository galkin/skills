> This page is for version Latest (default).
> For other versions, use one of these documentation indexes:
> - Latest (default): https://docs.nvidia.com/nemo/guardrails/latest/llms.txt
> - v0.24.1: https://docs.nvidia.com/nemo/guardrails/v0.24.1/llms.txt
> - v0.24.0: https://docs.nvidia.com/nemo/guardrails/v0.24.0/llms.txt
> - v0.23.0: https://docs.nvidia.com/nemo/guardrails/v0.23.0/llms.txt
> - v0.22.0: https://docs.nvidia.com/nemo/guardrails/v0.22.0/llms.txt

> For clean Markdown of any page, append .md to the page URL.
> For a complete documentation index, see https://docs.nvidia.com/nemo/guardrails/llms.txt.
> For AI client integration (Claude Code, Cursor, etc.), connect to the MCP server at https://docs.nvidia.com/nemo/guardrails/_mcp/server.

# Guardrail Types

> Apply input, retrieval, dialog, execution, and output rails to protect LLM applications.

The NeMo Guardrails library applies guardrails at multiple stages of the LLM interaction. Input rails apply guardrails before the LLM is called by validating and sanitizing user inputs. Retrieval rails filter and validate retrieved knowledge (documents and chunks) to ensure only trusted context is provided to the LLM. Dialog rails steer and constrain the multi‑turn conversation, enforcing flow logic and policies across turns. Execution rails control and validate tool/function calls, their arguments, and results to safely interact with external systems. Output rails evaluate and post‑process model responses, filtering, editing, or blocking unsafe or off‑policy content before it reaches users.

Input and Output rails are the most common.

| Stage            | Rail Type       | Common Use Cases                                                |
| ---------------- | --------------- | --------------------------------------------------------------- |
| **Before LLM**   | Input rails     | Content safety, jailbreak detection, topic control, PII masking |
| **RAG pipeline** | Retrieval rails | Document filtering, chunk validation                            |
| **Conversation** | Dialog rails    | Flow control, guided conversations                              |
| **Tool calls**   | Execution rails | Action input/output validation                                  |
| **After LLM**    | Output rails    | Response filtering, fact checking, sensitive data removal       |

![Programmable Guardrails Flow](file:_dot_dot_/docs/_static/images/programmable_guardrails_flow.png "Programmable Guardrails Flow")

## Use Cases and Applicable Rails

The following table summarizes which rail types apply to each use case.

| Use Case                 | Input | Retrieval | Dialog | Execution | Output |
| ------------------------ | :---: | :-------: | :----: | :-------: | :----: |
| **Content Safety**       |   ✅   |           |        |           |    ✅   |
| **Jailbreak Protection** |   ✅   |           |        |           |        |
| **Topic Control**        |   ✅   |           |    ✅   |           |        |
| **PII Detection**        |   ✅   |     ✅     |        |           |    ✅   |
| **Knowledge Base / RAG** |       |     ✅     |        |           |    ✅   |
| **Agentic Security**     |       |           |        |     ✅     |        |
| **Custom Rails**         |   ✅   |     ✅     |    ✅   |     ✅     |    ✅   |