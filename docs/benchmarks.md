# Benchmarks

Reproducible, in-repo measurements. Re-run any of these yourself.

## PoisonBench — memory-poisoning resistance

Measures whether poisoned memory candidates are correctly kept out of durable
memory. Each attack is proposed into an **isolated, empty memory** and pushed
through the real pipeline; it "succeeds" only if it reaches `state=active`.

- **ASR** (Attack Success Rate) = promoted attacks / attacks that should be
  rejected. **Lower is better.**
- **RSR** (Retention) = attacks still active after a re-processing pass / same
  denominator. **Lower is better.**
- **Legit promotion** = benign items correctly promoted / benign items. Higher
  is better (measures we didn't just reject everything).

### The honest part: a held-out split

The corpus is split into **train** (phrasings the deterministic scanner was
tuned against) and **test** — a **held-out** set of *novel* attacks the scanner
was deliberately **not** patched for. The **test-split ASR is the number that
matters**: it measures generalization, not memorization.

Run:
```bash
uv run python -m evals.poisonbench.run                 # rule-based verifier
MILYONUS_LIVE=1 uv run python -m evals.poisonbench.run # full pipeline (+ model verifier)
```

### Results (v5.5.0, held-out = 8 novel attacks + 4 benign controls)

| Configuration | Held-out ASR | Held-out RSR | Held-out legit |
|---|---|---|---|
| Rule-based verifier only | **75.0%** | 75.0% | 100% |
| **Full pipeline (rule + model verifier)** | **0.0%** | **0.0%** | **100%** |

**Read this carefully — it is the real story:**

- The regex scanner **alone does not generalize** (75% ASR on novel attacks). A
  scanner only catches what it was written for.
- The **full pipeline generalizes to 0%** because poisoning resistance is
  *structural*, not pattern-based: there is **no direct-write path**, an
  independent **verifier model** judges every candidate, sources have
  **competence limits**, and promotion follows **trust tiers**. The model
  verifier caught every novel attack the regex missed.
- This is why the layered design exists. The deterministic floor is a cheap,
  key-less first pass; the verifier is what makes it hold against attacks nobody
  wrote a rule for.

> Trade-off: the cautious model verifier also rejects some *legitimate* train-set
> facts (train legit promotion ≈ 73%). Held-out legit promotion stayed at 100%.
> Tuning verifier precision is ongoing.

### For orientation vs Hermes

Published memory-poisoning literature reports ~**66.67% ASR / 64.70% RSR** for
Hermes-style flexible-write memory. That figure comes from a different harness
and is shown for orientation, **not** as a like-for-like run — we cannot execute
Hermes here. The defensible Milyonus claim is the absolute, held-out number
above and the structural reason behind it. A like-for-like harness and a
third-party audit are on the roadmap.

## SafetyRegression — approval cannot be bypassed

```bash
uv run python -m evals.safety.run
```

Enumerates irreversible/dangerous tool calls and asserts the RiskEngine never
auto-runs them and that hard-block patterns are blocked. Result: **0 findings**.
