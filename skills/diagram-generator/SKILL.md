---
name: diagram-generator
description: Diagram authoring for certification study guides — decides whether an already written lesson earns a Mermaid diagram, then writes, improves or audits one that shows a mechanism the prose teaches, and validates it in the repository. Use for ```mermaid fences, flowchart, sequence diagram, state diagram, architecture diagram, diagram review, диаграмма, схема к уроку.
---

# Diagram generator

Add a diagram only where a cold reader would otherwise assemble a mechanism in their head from the prose — a flow that branches or joins, an exchange between parties, a lifecycle, a topology — and draw it so that the shape alone still says something. The diagram content is English; the report to the user is in the user's language.

## The contract lives in the project

This skill carries craft, not format. The allowed diagram types, the accessible-text fields, the sections a diagram may stand in, how many an item holds, the size a rendered diagram must fit, what a fence may not contain and the validation commands all come from the project's **diagram contract**, which `AGENTS.md` / `CLAUDE.md` names, together with the glossary that defines its words. Read both in full before any operation. Where this skill and the contract meet, the contract wins. A project with no contract gets a report saying so, and no files.

## Resolve the task

| Choice       | Values                                                                             |
| ------------ | ---------------------------------------------------------------------------------- |
| Operation    | `create`, `improve`, `audit` — read it off the request                             |
| Destination  | one **lesson** — a Bite, or the authored page of a Lab — named by the request      |
| Scope        | that lesson's body, in full; a Checkpoint or a Mock exam is never a destination    |
| Policy       | what the brief says about this batch — which sections to prefer, how dense, which types to balance; absent a brief, draw what passes the gates |

The knowledge boundary is always **the lesson itself**: every node, edge, state, participant and label is something the lesson's prose states, in the lesson's own words. Primary sources verify correctness and add nothing to the boundary. Ask the user one question only when the destination is ambiguous in a way that changes which file is touched; everything else has a default above. Sameness across a batch — every lesson closing with the same flowchart of its scenario — is the brief's to prevent and the reviewer's to catch, because one run sees one lesson; `pnpm diagram:check --inventory` lists what the corpus already holds.

## Steps

1. **Read the lesson**, in full, with the contract's section names in mind, and the glossary term for a diagram. _Done when_ you can say in one sentence what each section explains.
2. **List the mechanisms** the prose teaches: anything with an order, a branch, a loop, a hand-off between parties, a set of states, or a boundary being crossed. For each, write the **reader's question** it answers and the section it lives in. A list of features, a taxonomy, a comparison already served by a table, and a two-step "A calls B" are not mechanisms.
3. **Gate on warrant** with [diagram-design.md](references/diagram-design.md) › Warrant, the closing scenario included. When no mechanism passes, the answer is `No diagram recommended` and one line of why — and no file is changed. That outcome is as normal as the other.
4. **Choose the type by the question**, per the same file › Type, from the contract's allowed types only; then pick the one mechanism (two at most, the contract says how many) whose diagram changes the most for the reader.
5. **Draft, then gate.** Draft the fence with its accessible title and description, run it through the file's **Diagram gates**, rewrite a failure once, drop what still fails. [examples.md](references/examples.md) shows the gates applied. _Done when_ every survivor passes every gate, and every element traces to a sentence of the lesson.
6. **Write it.** By operation:
   - `create` — place the fence exactly where the contract allows, after one sentence that states the claim the diagram makes (the same claim as its accessible title). Where no existing sentence ends a paragraph with that claim, write that one sentence — it is the only prose `create` adds. Apply the contract's metadata rules for a content change. An item already holding its allowed count, or one already diagramming that mechanism, is left as it is and named in the report; replacing a diagram is `improve`.
   - `improve` — rework the named diagram in place: keep what passes, redraw what fails, keep the surrounding prose as it is unless the lead sentence is missing or wrong, and apply the contract's metadata rules for a content change. The diff stays inside the fence and its lead sentence.
   - `audit` — change no file. Report each finding as location, defect, why it matters for a reader, and a concrete replacement, with content defects (an element the prose does not state, a table restated, a missing branch) kept apart from form defects (type, size, labels, accessible text, forbidden styling).
7. **Validate.** Run every command the contract and `AGENTS.md` require before work is reported complete — the contract names the one that renders a lesson's diagrams and checks that they fit, which an `audit` runs too — and read the diff for unintended prose changes. _Done when_ each command's actual result is in hand; a command that could not run is reported as not run, and a render that failed is a finding, not a retry loop: fix the diagram against the error's text once, then report.

## Report

Changed files, the diagram's type and the mechanism it shows per destination, validation results as they came out, every element you could not trace to the prose and left out, and lessons deliberately left without a diagram with the reason. Candidate lists and gate notes stay in your working notes.

The skill's output is repository content and this report. How the fence is rendered, themed and sized is the project's build; the skill never writes colour, theme or config into a fence.
