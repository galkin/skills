# Native agent definitions under Orca: Claude, Codex, Antigravity (2026-10-18)

**Question.** Can the invariant part of a Run role (author, reviewer, collector) live in a native
agent definition that the agent CLI enforces, instead of a brief the worker reads with `cat`, and
can Orca still launch and supervise such a worker?

**Method.** Orca docs and issues first (`orca skills get orchestration --full`, `orca-cli --full`,
`onorca.dev/docs`, `stablyai/orca` issues), then the three CLIs' own help and docs, then live
probes: one Orca Run (`run_07f95466e35b`) in the pipeline worktree, five probe workers, each
asked to report its identity marker, tools, model and whether `curl` and web tools work.
Versions: Orca 1.4.229, Claude Code 2.1.292, codex-cli 0.163.0, agy 1.4.2.

## What Orca can and cannot do

- `worker-start --agent <id>` takes only an Orca agent id (`claude`, `codex`, `cursor`,
  `antigravity`, `muse`, `zcode`, `opencode`, …) plus `--model` / `--effort`. No flag carries extra
  argv, a Claude agent name, a Codex profile or environment variables. Confirmed in `--help`,
  the orchestration guide (Launch preferences) and issues #2284, #14999, #22573.
- Orca launches a built-in agent as `<command> <agentDefaultArgs>`; both are **global** settings
  per agent (`agentCmdOverrides`, `agentDefaultArgs`, `agentDefaultEnv` in the profile-state
  `settings` document). On this machine: `claude --dangerously-skip-permissions`,
  `codex --dangerously-bypass-approvals-and-sandbox`, `agy --dangerously-skip-permissions`.
  A global override would change every launch of that agent, including interactive tabs.
- **Custom agent presets do not exist yet.** #2284 (May 2026, PR #2521 unmerged) and #18249 ask
  for named presets with command, args, env and detection; #22573 for saved agent profiles with
  orchestration routing; #28426 for per-agent params. The docs page `docs/agents/custom-cli`
  that once described "Add custom agent" is a 404; a maintainer called it a doc desync.
- **The blessed escape hatch** (reference `low-level-topology`): `terminal create --worktree
  current --command "<agent argv>"`, `terminal wait --for tui-idle`, then either
  `dispatch --inject` (unsupervised) or **`worker-start --terminal <handle> --worktree current`**,
  which takes lifecycle ownership of the terminal. `--model`/`--effort` cannot combine with
  `--terminal`; the model comes from the argv.

## What each CLI offers

| | Claude Code | Codex | Antigravity (`agy`) |
| --- | --- | --- | --- |
| Definition file | `.claude/agents/<name>.md` (project) or `~/.claude/agents/`; frontmatter `tools`, `disallowedTools`, `model`, `effort`, `permissionMode`, `skills` (preload), `omitClaudeMd`, `maxTurns`, `memory` | no agent files; `[agents.<name>]` is for subagent roles. Project-scoped `.codex/config.toml` (loaded when the folder is trusted) with `developer_instructions`, `web_search`, `sandbox_mode`, `[sandbox_workspace_write] network_access`; profiles `$CODEX_HOME/<name>.config.toml` via `-p` | `.agents/agents/<name>.md` (project) or `~/.gemini/config/`; frontmatter `name`, `description`, `model`, `mode` seen in the binary; also reads `.claude/agents/` |
| Select without argv | `"agent": "<name>"` in `.claude/settings.json` or `settings.local.json` | the project config applies by itself | none found: the default launch runs the default assistant |
| Select by argv | `claude --agent <name>` | `codex -p <profile>`, `-c key=value`, `--sandbox` | `agy --agent <name>` |
| Hard tool limits | yes: `tools` allowlist is enforced; WebFetch/WebSearch/Skill can be removed | sandbox only (`workspace-write` + `network_access=false`); `web_search = "disabled"` does not remove the Codex-apps MCP search tool | unknown; a custom agent ran with no shell tool at all |
| Network cut | no (Bash `curl` still works; only tools are removed) | yes under the sandbox, but see below | no |

## Probe results

| Probe | Launch | Result |
| --- | --- | --- |
| Claude, setting | `worker-start --agent claude` with `.claude/settings.local.json` `{"agent": "probe-reviewer"}` and `.claude/agents/probe-reviewer.md` (`tools: Read, Grep, Glob, Bash`, `model: sonnet`) | Ran as the agent: marker in the system prompt, tools **Read and Bash only**, no WebFetch, model `claude-sonnet-5-5`. `curl` from Bash answered `HTTP/2 200`. Sent `worker_done` normally. |
| Claude, argv | `terminal create --command "claude --agent probe-reviewer --dangerously-skip-permissions"` + `worker-start --terminal` | Same result; supervised, `worker_done` delivered. |
| Codex, project config | `worker-start --agent codex` with `.codex/config.toml` (`developer_instructions`, `web_search = "disabled"`, `sandbox_mode = "workspace-write"`, `network_access = false`) | Config loaded: marker present, the worker refused the web probes on instruction. But Orca's default arg `--dangerously-bypass-approvals-and-sandbox` won: **sandbox `danger-full-access`, network on**, and the MCP tool `mcp__codex_apps__search_service_web_run` still listed. `CODEX_HOME` was empty in the shell. |
| Codex, argv sandbox | `terminal create --command "codex --sandbox workspace-write -a never -c sandbox_workspace_write.network_access=false"` + `worker-start --terminal` | Sandbox held (`workspace-write`, network restricted), but **`orca orchestration send` failed with `EPERM`**: the worker could not deliver `worker_done`; its report was read from the transcript and the dispatch abandoned. |
| Antigravity, default | `worker-start --agent antigravity` with `.agents/agents/probe-agy.md` | Ran as the default assistant (no marker), model Gemini 3.8 Flash, `curl` worked; it listed the custom agents `probe-agy` **and `probe-reviewer`** from `.claude/agents/`. |
| Antigravity, argv | `terminal create --command "agy --agent probe-agy --dangerously-skip-permissions"` + `worker-start --terminal` | Ran as `probe-agy` (marker present), but the custom agent had **no shell tool**, so it could not run `orca orchestration send`; it printed the command instead. Abandoned. |

## Conclusions

1. **Claude: fully native today.** A project `.claude/agents/<role>.md` plus `"agent"` in
   `.claude/settings.json` turns every plain `claude` launch, including `worker-start --agent
   claude`, into that role with an enforced tool allowlist and a pinned model. No Orca change,
   no argv. Per-worktree variation is `settings.local.json`, which the pipeline's `.task/` setup
   can write. Limit: Bash keeps the network, so "no web" is enforced only for the WebFetch and
   WebSearch tools, and `Skill` can be removed outright.
2. **Codex: instructions and web search go native, the sandbox does not.** A trusted
   `.codex/config.toml` in the worktree is read by Orca-launched Codex and carries the role
   text (`developer_instructions`) and `web_search = "disabled"`. Cutting the network needs the
   sandbox, and the sandbox blocks the `orca` CLI itself (EPERM), so a sandboxed Codex cannot be
   a supervised worker until Orca's socket is reachable from inside it (`features.network_proxy`
   with an allow list is the candidate, experimental, unverified). Orca's own default arg
   bypasses the sandbox, so `worker-start` never sandboxes Codex anyway.
3. **Antigravity: `--agent` works only through the argv path**, and a custom agent needs its
   tool set declared (the probe lost the shell). Worth a second probe with a `tools` field once
   the definition format is confirmed; not a blocker for us, since the pipeline uses Claude and
   Codex.
4. **The `--terminal` path is a real option**, not only a workaround: `worker-start --terminal`
   gave a supervised worker with receipts for both Claude and Antigravity. Its costs: two extra
   calls per worker, no `--model`/`--effort` (they go in the argv) and a terminal that Orca
   does not close on release.
5. **Instruction-only limits still leak.** The Codex probe honoured "never fetch" because it was
   a probe; the 1.3a author ran `orca skills get orchestration` on its own under a similar brief.
   Only a tool allowlist (Claude) or a sandbox (Codex, once Orca is reachable) removes the
   option rather than discouraging it.

## Recommendation for the pipeline

- Reviewer and collector as Claude agent definitions in the pipeline repo
  (`.claude/agents/reviewer.md`, `collector.md`): `tools: Read, Grep, Glob, Bash`, no Skill,
  pinned model and effort, `skills:` preloading the lorekeep skill for the collector only.
  `.task/` setup writes `settings.local.json` with the role for that worktree. Launch stays
  `worker-start --agent claude`.
- Author as Codex with a project `.codex/config.toml`: `developer_instructions` holding the
  invariant author contract, `web_search = "disabled"`, model and effort. The brief shrinks to
  the per-unit lines. Network stays open until the Orca-in-sandbox question is settled.
- Open Orca items to track: #2284 / #22573 (presets and profiles would remove the argv path),
  #14999 (per-launch tool and MCP policy). File nothing new yet; our need is covered by the
  settings route for Claude and the project config for Codex.
- Measure with a second 1.3a pair before changing the run skill.

Probe artefacts: scratchpad `native/` (help texts, issue dumps, launch receipts, check logs).
Probe files were removed from the worktree; the Run's terminals were closed.
