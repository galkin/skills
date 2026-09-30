---
name: quiz-generator
description: Quiz authoring for certification study guides — writes, improves and audits knowledge checks that close a lesson, checkpoints over a finished unit, and mock exams, then inserts and validates them in the repository. Use for `:::quiz`, knowledge check, checkpoint, mock exam, quiz review, квиз, вопросы для самопроверки.
---

# Quiz generator

Write original, single-answer questions that make a prepared reader _decide_ — apply, diagnose, distinguish — and teach through the rationale when they get it wrong. The quiz content is English; the report to the user is in the user's language.

## The contract lives in the project

This skill carries craft, not format. Syntax, question and choice limits, placement, file names, manifest entries, metadata and validation commands all come from the project's **quiz contract**, which `AGENTS.md` / `CLAUDE.md` names, together with the glossary that defines its words. Read both in full before any operation. Where this skill and the contract meet, the contract wins. A project with no contract gets a report saying so, and no files.

## Resolve the task

| Choice      | Values                                                                        |
| ----------- | ----------------------------------------------------------------------------- |
| Operation   | `create`, `improve`, `audit` — read it off the request                        |
| Destination | a **lesson quiz** closing one lesson, a **checkpoint** over one finished unit of the curriculum, or a **mock exam** |
| Scope       | the lesson, the unit, or — for a mock exam — the whole exam blueprint          |

The destination sets the **knowledge boundary**; it is never chosen separately:

- **Lesson quiz and checkpoint — `materials`.** Every fact a reader needs to reach the answer is taught in the lessons in scope, including the authored pages that introduce hands-on labs; the content of an external exercise is outside it. A novel scenario is welcome; a hidden prerequisite is not. Primary sources verify correctness and add nothing to the boundary.
- **Mock exam — `exam`.** The boundary is the certification's published objectives for that blueprint version, read from the project's manifest. Knowledge the lessons do not teach is in bounds when an official technical source supports it. Spread questions across the blueprint's sections as the contract's norm says, weighted roughly by their published weights.

Ask the user one question only when the destination or the unit is ambiguous in a way that changes which files are created. Everything else has a default above.

## Steps

1. **Read the sources.** For a lesson quiz or a checkpoint: every lesson in scope, in full — the body, not the title — plus its references, keeping a running list of what each one lets you assess. For a mock exam: the objectives from the manifest, then per objective the official documentation that supports it, opening the guide's lesson for that objective only when you need to see how it frames the topic. _Done when_ every lesson or objective in scope is on the list, or named in the report as not read.
2. **List the decisions.** For each lesson, the things a reader must decide, distinguish, apply or diagnose. For a checkpoint, also the relationships _between_ lessons — the synthesis only a unit-level check can ask. For a mock exam, map each decision to the objective it serves. Recall earns a place only when an objective literally asks for it.
3. **Gate on sufficiency.** When no decision supports a question with plausible alternatives, the answer is `No knowledge check recommended` and one line of why — and no heading, file or manifest entry is created.
4. **Verify the claims** each candidate depends on against version-appropriate primary sources. A lesson that contradicts its source is a finding: report the conflict and leave the dependent question out. A claim you could not check — no access, no source found — is reported as unverified, and the question that rests on it stays out.
5. **Draft, then gate.** Draft more candidates than you need, run every one through [question-design.md](references/question-design.md), rewrite failures once, drop what still fails. Then run the whole-set review in the same file. [examples.md](references/examples.md) shows the gates applied. _Done when_ every surviving item passes every gate.
6. **Fit the set to the contract.** Its question limit for the destination is a ceiling, never a quota: a lesson quiz keeps its strongest items up to that limit; a checkpoint and a mock exam take as many as survive, within the contract's norm. When the request asks for more than the contract allows, keep the contract and offer the nearest conforming option — the strongest items, or a checkpoint for the rest.
7. **Write it.** By operation:
   - `create` — insert the new quiz or item exactly as the contract places it, with every entry and metadata change the contract ties to it. An existing quiz stays as it is and is named in the report; replacing one is `improve`.
   - `improve` — rework the named quiz in place: keep the items that pass, rewrite or replace those that fail, bring the prose between the heading and the quiz to what the contract allows, and apply the contract's metadata rules for a content change.
   - `audit` — change no file. Report each finding as location, defect, why it matters for a reader, and a concrete replacement, with content defects kept apart from syntax defects.
8. **Validate.** Run every command the contract and `AGENTS.md` require before work is reported complete, and read the diff for unintended prose changes, duplicate headings or entries, and broken references. _Done when_ each command's actual result is in hand; a command that could not run is reported as not run.

## Report

Changed files, question count per destination, validation results as they came out, source conflicts, and any lessons or objectives deliberately left uncovered with the reason. Distractor analyses and scores stay in your working notes.

The skill's output is repository content and this report. Presenting, scoring and storing attempts is the project's runtime, and question banks are outside the repository.
