# 01: Twins for Fern, Mintlify and GitHub, and verbatim files

**What to build:** `get` of a `docs.langchain.com` page or a Fern-built `docs.nvidia.com` page stores the publisher's Markdown (`converter: md-twin`), with its code and tables; `get` of a `github.com/<owner>/<repo>/blob/<ref>/<path>` address stores the raw file under the `blob` URL (`converter: raw-twin`), fenced by extension when it is not Markdown or text; `get` of a JSON, YAML, plain-text, CSV or XML response stores the bytes verbatim in one fence (`converter: verbatim`) instead of "unsupported media type". Decisions: `spec.md` › Twins and verbatim files.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `get https://docs.langchain.com/oss/python/langchain/sql-agent` (fixture: the Twin recorded from the live host) stores `converter: md-twin` with at least one fence and one pipe table in the body; the same for a Fern Guardrails page under `docs.nvidia.com/nemo/guardrails/`, and for a Dynamo page whose Twin answers `text/plain` with a body that does not start with `<`
- [ ] the package default table lists which `docs.nvidia.com` prefixes serve `.md` (probed live once, recorded in the table's comments) and leaves the Sphinx sections (`/nim/`, `/nemo/agent-toolkit/` or whichever do not) to the page step; a Twin `404` still falls through to the page as in v1
- [ ] `get https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/docker-compose.yaml` (fixture: the raw file) stores `url: https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/docker-compose.yaml`, `original.url` the raw address, body `# docker-compose.yaml` then one ` ```yaml ` fence holding the file verbatim; a `blob/…/README.md` stores the Markdown as is; a raw address given directly still works under the `raw.githubusercontent.com` rule
- [ ] `get` of `https://docs.nvidia.com/rag/latest/_static/api_reference/openapi_schema_rag_server.json` (fixture: `application/json`) stores `converter: verbatim`, `title: openapi_schema_rag_server.json`, body one ` ```json ` fence; the same path for `text/plain`, `application/yaml`, `text/csv`
- [ ] a Recheck of each new converter rereads through its own step: a `md-twin` Version through the Twin step as today, `raw-twin` through the Twin step under the `github-raw` rule, `verbatim` through the page step gated to its media types
- [ ] `tests/fixtures/README.md` names the new fixtures; the host table's `twin` kinds are documented in `README.md`'s `lorekeep.toml` section and in `SKILL.md`'s one sentence on Twins (the full skill rewrite is ticket 05)
