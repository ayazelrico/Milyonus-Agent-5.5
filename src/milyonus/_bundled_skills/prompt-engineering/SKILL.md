---
name: prompt-engineering
description: Design LLM prompts and applications
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - prompt
    - llm
    - ai
    category: ai
    requires_toolsets: []
    provenance: official
---

# Prompt Engineering
## Basic structure
- **System:** role, rules, output format, constraints (persistent behavior).
- **User:** the concrete task + needed context.
- **Examples (few-shot):** 1–5 good examples show the format; add when zero-shot is not enough.
## Effective techniques
- **Explicit output contract:** "Return only JSON: {...}". Give a schema, validate.
- **Step-by-step reasoning:** ask to "plan first, then solve" for complex reasoning (avoid needless verbosity on short/precise answers).
- **State limits:** "If you don't know, say 'I don't know'", "don't make things up".
- **Role + audience:** "As a senior security engineer, explain to a junior".
- **Divide and conquer:** a chain (extract -> transform -> format) beats one giant prompt.
## Common mistakes
- Vague instruction -> vague output. Be concrete, give examples.
- Conflicting rules; state a priority order.
- Confusing "instruction" and "data" when embedding context — fence data explicitly (Milyonus does this with `<milyonus:memory>`).
## Evaluation
- Keep a test set (input -> expected); measure regressions when the prompt changes.
- Score subjective quality with an LLM-as-judge; set temperature to 0 (reproducibility).
