# Diagram design

The craft every diagram is held to. Run a candidate mechanism through **Warrant**, pick its **Type**, draw it by the **Authoring rules**, then run the fence through the **Diagram gates**.

## Warrant

A diagram earns its place only when **all** of these hold. One failing is `No diagram recommended`.

1. **It shows a mechanism.** The prose describes something with an order, a branch or loop, an exchange of several messages between parties in a fixed order, states with non-trivial transitions, or a boundary being crossed — something the reader would otherwise assemble in their head.
2. **The shape says something on its own.** Cover the labels: a fan-out, a loop back, a fork and join, two parallel lanes, a box inside a box still carry meaning. A straight chain of boxes does not, and a sentence is faster.
3. **It answers one stated question for one reader job.** Write the question down before drawing — "which path does a request take when the gate rejects it?", "who calls whom to complete a task?". For this guide the job is usually to trace what happens at runtime or to decide between options under exam conditions.
4. **A comparison draws the difference.** The edge or hop one option adds or removes, side by side — never one labelled box per option with nothing connecting them, which is a restated list.
5. **Everything in it is taught by the lesson, before the reader reaches it.** Every node, edge, participant, state and transition traces to a sentence of the prose, in the prose's words, and every name in it has been introduced by the time the reader meets the fence — a diagram of a later section's example stands in that section. Nothing is inferred from general knowledge; a relationship the lesson does not state is left out, however true it is.
6. **It is not redundant.** A table, a list or a numbered sequence already in the lesson is not redrawn. A diagram adds a shape, not a second copy.

Typical rejections: a taxonomy, a feature inventory, a vendor product map with no flow, a two-step call, a mindmap of the section headings, a table in boxes.

When more than one mechanism passes, draw the one that changes the most for the reader: the mechanism the objective is about, in its own section, before the closing scenario that applies it. Whether a scenario is drawn at all when the mechanism section already has a diagram, and how many lessons of a batch get one, is the brief's policy, not this file's — read the brief.

## Type

Choose by the question the reader asks, from the contract's allowed types.

| The reader asks                                                  | Type                | Notes                                                                                                                                     |
| ---------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Which path is taken — where does it branch, loop or join?        | `flowchart`         | The default. Agent loops, routing, guardrail checks, fan-out and fan-in, pipelines. A trust boundary or a phase is a `subgraph`.           |
| Who calls whom, in what order?                                   | `sequenceDiagram`   | Tool and function calling, client–server protocols, approval round-trips, streaming updates. Declare participants, initiator first.        |
| What states can a thing be in, and what moves it?                | `stateDiagram-v2`   | Task and session lifecycles, approval states, retry and circuit-breaker behaviour.                                                        |
| How do the components and boundaries sit when deployed?         | `architecture-beta` | Services inside groups with edges between them. Only when the lesson lays out a deployment; a trust boundary or data flow is a flowchart. |
| What does each option add or remove?                             | `flowchart`         | Two parallel `subgraph`s drawing the delta, or two small diagrams.                                                                        |

Quantities, timelines, rankings and taxonomies have no type here: a study guide seldom has real numbers, and invented ones mislead. A number the lesson itself states — a two-second deadline — may appear in a label; one the lesson does not state may not.

## Authoring rules

- **Size.** Five to twelve nodes, at most five participants, one level of nesting. Above that, split or move detail to prose — split when readability suffers, not at a count. The count is advice; what fails a build is the contract's rule on the rendered width, which a short left-to-right chain can break while a taller top-down one passes.
- **Direction.** Top-down by default; left-to-right only for a short linear chain of four or five nodes. The contract scales a wide diagram down to its column, so width costs legibility and height does not.
- **Labels.** Two to five words, the lesson's own terms and the glossary's, verb phrases for actions and noun phrases for components, parallel across comparable nodes. No emoji, no code in nodes. Quote every label: `id["…"]`. A flowchart label wraps by word on its own; a `<br>` in one forces a break the wrapper would not choose and tends to orphan a word, so use it only in a `stateDiagram-v2` label, which does not wrap.
- **Edges.** Label every edge whose meaning is not obvious from its endpoints, and every edge out of a decision. One meaning per line style within a diagram: solid for the main path, dotted for the asynchronous, optional or failure path. Labels on parallel edges share one row and run into each other — in a `stateDiagram-v2` label a transition only when the target state's name does not already say it, and never more than two transitions out of one state; the contract fails the build on labels that overlap.
- **Ids.** Readable and stable (`planner`, `toolCall`), distinct from labels, never `end`, never equal to a subgraph's id.
- **Order.** Declare nodes in reading order and keep a group's nodes adjacent in the source. Minimise back-edges, except the one loop that is the point of a loop diagram.
- **Sequence.** Participants explicit, initiator first, at most five. `alt`/`loop`/`par` blocks balanced; never deactivate a participant in both branches of an `alt`.
- **Architecture.** Connect through `L`/`R` ports; an edge from a `B` or `T` port runs through the label under the icon. Every service inside a boundary is declared `in` that group — the contract checks the drawn geometry against the declarations.
- **Styling.** None. No `classDef` with colour, no `style`, no `%%{init}%%`, no frontmatter; emphasis, when needed, is `classDef emphasised stroke-width:2px` or `classDef optional stroke-dasharray:4 2` applied with `class`, and never colour alone. The contract fails the build on the rest.
- **One claim.** The last sentence before the fence states what the reader should see; the accessible title states the same claim; the accessible description gives the read order and the takeaway — "Starts at …, branches on …, every path ends at …" — not "a flowchart of X". A sentence after the fence is commentary, not the lead.

## Diagram gates

A fence is accepted only when all eight hold:

1. It passes every Warrant condition, and its reader's question is written down.
2. Its type is the contract's and fits the question.
3. Every element traces to a sentence of the lesson, in the lesson's words; nothing is invented or inferred.
4. It restates no table, list or sequence already in the lesson.
5. It is within the size rules, top-down unless short, with quoted labels and labelled decisions.
6. It carries the accessible title and description the contract requires, the title matching the lead sentence's claim.
7. It contains no styling, config or interaction the contract forbids.
8. It stands where the contract allows, after its lead sentence, within the item's allowed count.

Rewrite a failing fence once. If it still fails, drop it — a lesson without a diagram beats one with a wrong diagram.

## Pitfalls that break a render

| Written                                        | Result                                   | Instead                                     |
| ---------------------------------------------- | ---------------------------------------- | ------------------------------------------- |
| `A --> end`                                    | parse error (`end` is reserved)          | `done["End"]`                               |
| `A[Call (tool)]`                               | parse error on the parentheses           | `A["Call (tool)"]`                          |
| `A->>B: one; two` in a sequence                | `;` ends the statement                   | rephrase, or `#59;`                         |
| `A --> B %% note` on one line                  | parse error                              | `%%` comments on their own line             |
| node id equal to its subgraph's id             | renders a cycle error                    | distinct ids                                |
| `B-->>-A` in both `alt` branches               | "inactivate an inactive participant"     | deactivate once, after the block            |
| `A---oB`                                       | silently a circle-headed edge            | `A --- oB`, or capitalise                   |
| `\n` in a label                                | literal `\n`                             | `<br>`                                      |
| `graph TD`                                     | not an allowed type                      | `flowchart TD`                              |
| `A --> A` (a self-loop, as a retry)            | a stub too small to read, label adrift   | a separate `retry` node, or prose           |
| arrows from another type (`->>` in a flowchart) | parse error                             | each type's own arrows                      |
