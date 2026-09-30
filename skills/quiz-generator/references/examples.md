# The gates, applied

One draft, the defects the gates find in it, and the item that survives. The syntax is agentic-system.design's; the reasoning is the point.

## Draft

```md
What is the best way to improve a RAG system's answers?

- [ ] Use a bigger model
- [x] Add a reranking stage over the existing candidate set so that the most relevant passages reach the context window first, keeping retrieval unchanged
- [ ] Use all of the above
- [ ] Nothing

::rationale[Option 2 is correct because reranking is best.]
```

## What the gates find

| Gate | Defect |
| --- | --- |
| 1 | "Best way to improve answers" names no decision the reader has to make. |
| 4 | Nothing in the prompt says retrieval already finds the right passages — the fact that makes reranking best — so several changes could be defended. |
| 5 | "Use all of the above" and "Nothing" are not mistakes anyone makes; they are filler. |
| 6 | The correct choice is the odd one out — the only long, specific one, and the only one with a justification (`so that …`). |
| 7 | The rationale points at a position and asserts instead of teaching. |

## Accepted

```md
Evaluation shows that the candidate set already contains the relevant passages, but irrelevant passages appear above them in the final results. You must improve the final ordering while keeping candidate retrieval unchanged. Which change directly addresses the problem?

- [ ] Increase the number of retrieved candidates
- [x] Rerank the existing candidate set before selecting the final results
- [ ] Replace the embedding model used for candidate retrieval
- [ ] Increase the maximum length of the generated answer

::rationale[Reranking improves ordering within the retrieved candidate set. It cannot recover a passage retrieval never returned, but missing candidates are not the problem described here.]
```

- **Deciding constraint:** the candidates are already there; only their order is wrong.
- **Distractors as mistakes:** more candidates solves recall, the neighbouring problem; a new embedding model changes retrieval, which the prompt holds fixed; a longer answer treats the symptom downstream.
- **Parallel choices:** four short imperatives at one level of abstraction, none with a justification — with the prompt covered, nothing singles one out.
- **Rationale:** states the distinction — ordering versus recall — and names where reranking stops working.

Use it only where the lesson in scope teaches reranking; it illustrates the gates, it is not a question to reuse.
