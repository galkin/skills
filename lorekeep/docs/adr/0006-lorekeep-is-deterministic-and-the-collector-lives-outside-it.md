# lorekeep is deterministic; the Collector lives outside it

lorekeep calls no LLM. Every command — fetch, convert, index, check, back up — gives the same result
for the same input and costs no tokens. Deciding *which* Sources a piece of work needs is the
Collector's job, an LLM step of the consuming pipeline that calls lorekeep; in the
`agentic-system.design` pipeline it runs before the authors behind a flag that is on by default.

Knowledge of how to fetch belongs in code, not in prompts: written into a brief it is paid for in
every Run and followed differently by every worker. Keeping the model out also keeps the tool usable
by tasks other than writing guides, which was the reason to make it a tool of its own rather than
part of the pipeline's skill.
