---
name: debugging
description: Systematic debugging methodology
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - debug
    - troubleshooting
    - method
    category: development
    requires_toolsets: []
    provenance: official
---

# Systematic Debugging
Proceed by **method**, not by guessing. Order:
## 1. Reproduce reliably
- Find the minimal reproducible example (MRE). If you can't reproduce, solve that first.
- Fix the environment: version, input, config, clock/timezone.
## 2. Observe (without assuming)
- Read the real error/stack trace **to the end** — the root is usually the innermost.
- Raise the log level; print input/output values (`print`/logger).
- Write down "expected vs actual" clearly.
## 3. Narrow (bisect)
- Binary search: halve the location by eliminating where the problem is NOT.
- Use `git bisect` to find the commit that broke it.
- Isolate components (mock a dependency, run one module).
## 4. Hypothesis -> test
- Change one variable, measure again. One thing at a time.
- Build the "why" chain: ask "why" 5 times (5 whys), reach the root cause.
## 5. Fix & verify
- Fix the root cause (not the symptom).
- Write a **regression test** that catches the bug — so it doesn't return.
- Check side effects; run the full test suite.
## Common root causes
Off-by-one · null/None · race condition · stale cache · boundary values ·
encoding · timezone · float comparison · env difference (prod≠dev).
