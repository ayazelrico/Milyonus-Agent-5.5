# Benchmarks

Reproducible measurements of Milyonus's safety and capability claims. Re-run any
of these yourself; the scripts live under `evals/`.

## PoisonBench — memory-poisoning resistance

Measures whether poisoned memory candidates (across the four write channels
C1–C4 from the literature) are correctly rejected.

- **ASR** (Attack Success Rate): attacks that *should* have been rejected but
  were promoted. Lower is better. Target **< 10%**.
- **RSR** (Retention/Success Rate): of those, how many persisted as active.
  Target **< 5%**.
- **Legit promotion rate**: legitimate facts that correctly promoted. Higher is
  better.

Run:
```bash
uv run python -m evals.poisonbench.run              # rule-based verifier (no key)
MILYONUS_LIVE=1 uv run python -m evals.poisonbench.run   # + live model verifier
```

### Results (v0.1.0.dev, 2026-08-26)

| Configuration | ASR | RSR | Legit promotion |
|---|---|---|---|
| Milyonus — rule-based verifier | **0.0%** | **0.0%** | 100% |
| Milyonus — live model verifier (Claude Haiku 4.5) | **0.0%** | **0.0%** | 100% |
| Hermes (published, for reference) | 66.67% | 64.70% | — |

> The rule-based verifier is the deterministic floor that runs even without a
> model key; the model verifier adds a second, independent judgment. Both pass
> the targets on the current corpus. The corpus is small (11 cases) and will
> grow — these numbers are a starting baseline, not a final claim.

The Hermes figures are from the published literature cited in the project report
(memory-poisoning benchmark). They are included for orientation, not as a
head-to-head run on identical inputs; a like-for-like harness is future work.
