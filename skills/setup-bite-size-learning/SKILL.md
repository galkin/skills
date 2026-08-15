---
name: setup-bite-size-learning
description: Set up a new bite-size learning project through a guided interview. Use when the user wants course-specific Custom Instructions plus a persistent Learning Log and student Notes in a chosen long-term-memory system.
license: MIT
compatibility: Requires access to a writable persistent storage provider that can be read and updated across later chats and can return stable locators.
metadata:
  author: Nikita Galkin
  version: "0.1.0"
---

# Set Up Bite-Size Learning

Create one learning project. Finish with exactly three artifacts:

1. copy-ready Custom Instructions for the user to paste into the project's instructions;
2. a Learning Log created in the chosen long-term memory;
3. separate Notes created in the same long-term memory.

Run setup only. Leave teaching to later chats governed by the generated instructions.

## Interview

Map setup as a decision tree. Work in rounds: ask only questions whose prerequisites are settled, give a recommended answer where useful, and wait for the user's decisions before continuing. Find facts with available tools; ask the user for preferences and decisions, not discoverable facts.

Settle these inputs:

- an observable learning goal;
- current and desired capability;
- teaching language;
- how every bite will be verified;
- source requirements and authoritative curriculum, when one exists;
- the long-term-memory provider and exact parent location for both persistent artifacts.

Ask only for information still missing from the conversation. Help sharpen vague answers instead of treating the interview as a form.

## Long-term memory

Inspect the tools and writable destinations actually available. Offer only workable choices, with a local-file option when permitted. Let the user choose the provider; treat Notion as one option, not the default architecture.

Before planning artifact creation, verify that the selected provider supports:

- creating two separate documents;
- reading them in later chats;
- updating them after each completed bite;
- returning stable locators that Custom Instructions can name.

If the chosen provider is unavailable, explain the missing connection or capability and ask the user to connect it or choose another provider. Preserve the user's storage decision; do not silently substitute a fallback.

## Sources and curriculum

Determine whether the goal has an authoritative curriculum or scope, such as an exam guide, official syllabus, specification, or maintained documentation. Research current primary sources when accuracy or scope can vary by version. Distinguish verified findings from recommendations.

Propose:

- a concise source policy for later teaching;
- the authoritative basis for the plan, if any;
- an initial curriculum adapted to the learner's current and desired capability;
- a domain-appropriate verification method.

Let the subject determine the Learning Log structure and statuses. Avoid a universal schema when an exam guide, skill ladder, or other domain structure is clearer.

## Approval gate

Present one compact setup proposal containing all settled inputs, the source policy, and the initial curriculum. Ask for explicit approval or corrections.

Treat approval of the proposal as the creation gate. Before approval, write neither persistent artifact. A revised proposal requires renewed approval.

## Create the persistent artifacts

After approval, create both artifacts in the selected long-term memory.

### Learning Log

Make this the tutor's authoritative state between chats. Include only what is needed to resume and steer learning:

- goal and target capability;
- curriculum and domain-appropriate topic states;
- current position;
- next recommended bite;
- unresolved gaps and concise tutor-only notes;
- the curriculum's authoritative basis;
- last-updated state.

Keep it current rather than appending a verbose lesson diary. Store neither transcripts nor full learner answers.

### Notes

Make this a separate, student-facing resource for review. Give it a structure appropriate to the subject. Store concise explanations, useful examples, links, snippets, and anything the learner asks to preserve. Keep plan state and tutor-only observations in the Learning Log instead.

Create an intentionally sparse Notes document when there is not yet useful study material.

Read both artifacts back after creation. Confirm that their stable locators work and that both can be updated. If either write or verification fails, report the exact partial state and repair it before generating final instructions.

## Generate Custom Instructions

Generate the instructions only after both persistent artifacts are verified. Keep them under 8,000 characters and ready for manual copy-paste. Name the provider, access method, and exact Learning Log and Notes locators.

Include the course-specific values and only the runtime rules needed to enforce this contract:

- At the start of every new chat, read the Learning Log and Notes. Treat the Learning Log as authoritative over chat history. If it is inaccessible, surface the access problem instead of reconstructing the plan from memory.
- Select the current or next bite from the Learning Log. Teach one small coherent unit, adapting its size to the subject and learner.
- End every bite with the agreed observable verification. Complete the bite only after it passes; otherwise adapt within the same bite.
- After a completed bite, update the Learning Log and add to Notes only when useful to the learner.
- Recommend the next bite, then wait for explicit learner consent before starting it.
- Follow the learner's explicit intent. A request to study a topic is consent to that topic and may become a bite or a local plan addition without redundant confirmation.
- Agree on material changes to the overall curriculum first. Refine or split existing topics locally without extra ceremony.
- Let the learner initiate review. The tutor may recommend a review when errors reveal a gap, but starts a separate review bite only after consent; brief prerequisite recovery may remain inside the current bite.
- Apply the agreed source policy and prefer authoritative sources over model memory when facts or scope are version-sensitive.
- Keep Learning Log and Notes separate according to their audiences.

Do not embed the setup interview, generic pedagogy, duplicated storage content, or a fixed universal Learning Log schema in Custom Instructions.

## Handoff

Return:

1. one clearly labeled, copy-ready Custom Instructions block with its character count;
2. the verified locator for the Learning Log;
3. the verified locator for Notes;
4. one sentence telling the user to paste item 1 into the project's instructions.

State only completed writes as completed. End the setup session without starting the first bite.
