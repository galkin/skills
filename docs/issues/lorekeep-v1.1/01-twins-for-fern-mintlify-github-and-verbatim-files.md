# 01: Twins for Fern, Mintlify and GitHub, and verbatim files

**What to build:** `get` of a `docs.langchain.com` page or a Fern-built `docs.nvidia.com` page stores the publisher's Markdown (`converter: md-twin`), with its code and tables; `get` of a `github.com/<owner>/<repo>/blob/<ref>/<path>` address stores the raw file under the `blob` URL (`converter: raw-twin`), fenced by extension when it is not Markdown or text; `get` of a JSON, YAML, plain-text, CSV or XML response stores the bytes verbatim in one fence (`converter: verbatim`) instead of "unsupported media type". Decisions: `spec.md` › Twins and verbatim files.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `get https://docs.langchain.com/oss/python/langchain/sql-agent` (fixture: the Twin recorded from the live host) stores `converter: md-twin` with at least one fence and one pipe table in the body; the same for a Fern Guardrails page under `docs.nvidia.com/nemo/guardrails/`, and for a Dynamo page whose Twin answers `text/plain` with a body that does not start with `<`
- [x] the package default table lists which `docs.nvidia.com` prefixes serve `.md` (probed live once, recorded in the table's comments) and leaves the Sphinx sections (`/nim/`, `/nemo/agent-toolkit/` or whichever do not) to the page step; a Twin `404` still falls through to the page as in v1
- [x] `get https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/docker-compose.yaml` (fixture: the raw file) stores `url: https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/docker-compose.yaml`, `original.url` the raw address, body `# docker-compose.yaml` then one ` ```yaml ` fence holding the file verbatim; a `blob/…/README.md` stores the Markdown as is; a raw address given directly still works under the `raw.githubusercontent.com` rule
- [x] `get` of `https://docs.nvidia.com/rag/latest/_static/api_reference/openapi_schema_rag_server.json` (fixture: `application/json`) stores `converter: verbatim`, `title: openapi_schema_rag_server.json`, body one ` ```json ` fence; the same path for `text/plain`, `application/yaml`, `text/csv`
- [x] a Recheck of each new converter rereads through its own step: a `md-twin` Version through the Twin step as today, `raw-twin` through the Twin step under the `github-raw` rule, `verbatim` through the page step gated to its media types
- [x] `tests/fixtures/README.md` names the new fixtures; the host table's `twin` kinds are documented in `README.md`'s `lorekeep.toml` section and in `SKILL.md`'s one sentence on Twins (the full skill rewrite is ticket 05)

## Comments

**2026-10-17** — implemented on `galkin/lorekeep-v11-01`.

- **Probe of `docs.nvidia.com`** (one page per section of the NCP-AAI migration, `<page>.md`):
  `200 text/markdown` from `cuvs/`, `dynamo/`, `nemo/curator/`, `nemo/guardrails/`, `nemo/gym/`,
  `openshell/` (all Fern, `x-fern-renderer: static`); `404 text/html` from
  `datacenter/cloud-native/`, `deeplearning/{dali,riva,triton-inference-server}/`,
  `nemo/agent-toolkit/`, `nemo/megatron-bridge/`, `nemo/retriever/` (MkDocs; one page of five
  answered, so it gets no rule), `nemo/rl/`, `nim/`, `nim-operator/`, `rag/`, `vss/`. Recorded in
  `hosts.toml`'s comments; each Fern section has its own `md-suffix` rule without `page_suffix`.
- **Deviation from the spec: the `docs.nvidia.com/` catch-all names no Twin.** The spec made it
  `md-suffix` with `page_suffix = ".html"`. Every Sphinx/MkDocs page would then pay a `404`, and
  the reverse reduction would file a Fern page of an unlisted section under `<page>.html`, an
  address that does not exist. A Twin `404` under a Fern rule still falls through to the page
  (`test_a_twin_404_under_a_fern_rule_falls_through_to_the_page`).
- **Dynamo answers `text/markdown` live, not `text/plain`.** The `text/plain` gate for `md-suffix`
  (accepted when the body does not start with `<`) is built as the spec says and proven on
  `dynamo-fast-model-loading.plain`, the recorded Dynamo Twin served as `text/plain`.
- **`sql-agent` has no pipe table** (it has fences only); the table half of the first box is proven
  on LangChain's `tools` Twin, recorded beside it.
- **`NVIDIA-AI-Blueprints/rag/blob/main/docker-compose.yaml` does not exist** (`404`); the YAML
  fixture is `NVIDIA-AI-Blueprints/deep-researcher-agent/blob/main/deploy/compose/docker-compose.yaml`
  from the migration's batch. Its heading is the path within the repository
  (`# deploy/compose/docker-compose.yaml`, as the spec's `# <path>` says), and so is its `title`.
- `raw-twin`: Markdown files keep their frontmatter mining and lose leading blank lines like any
  Twin; `.txt` is stored as is; any other file (extension-less too, with a bare fence) gets a fence
  longer than any backtick run inside it. The GitHub rule takes `text/markdown` and `text/plain`.
  A `github.com` address that is not a `blob/` asks for no raw file and goes to the page step. A
  raw address given directly stays under the `raw.githubusercontent.com` rule (`md-twin`, raw URL)
  — it is not reduced to the `blob` page, as the ticket's third box asks.
- `verbatim`: the Original is stored (`.orig.json` etc.) because the Markdown is a wrapping of it;
  the charset the response names decodes it (UTF-8 otherwise); an empty file is declined with
  `no content`. `step_of` maps `raw-twin` to the Twin step and `verbatim` to the page step gated
  to the verbatim media types.
- Beyond the ticket, small: a Twin with no `title` in its frontmatter takes its first `# ` heading
  outside a fence (Fern and Mintlify Twins have no frontmatter; story 8).
- `pyproject.toml`: `tests/fixtures` is excluded from ruff, because `ruff format --check` formats
  Python fences inside recorded Markdown bodies.
- `tests/test_get_html.py`: the "media type decides" test used `application/json` as the
  unsupported type; it now uses `application/octet-stream`.
