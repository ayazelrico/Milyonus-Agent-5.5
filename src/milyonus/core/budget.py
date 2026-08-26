"""Iteration/token budget shared across a task (and, later, its subagents).

The loop checks the budget before each model call and injects a pressure hint as
the window fills, so the agent wraps up instead of being cut off mid-thought.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Budget:
    max_iterations: int = 50
    max_tokens: int = 500_000
    used_iterations: int = 0
    used_tokens: int = 0

    def record(self, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.used_iterations += 1
        self.used_tokens += input_tokens + output_tokens

    def exhausted(self) -> bool:
        return self.used_iterations >= self.max_iterations or self.used_tokens >= self.max_tokens

    def pressure(self) -> float:
        """0.0–1.0 fraction of the tighter of the two limits consumed."""
        it = self.used_iterations / self.max_iterations if self.max_iterations else 0
        tk = self.used_tokens / self.max_tokens if self.max_tokens else 0
        return max(it, tk)
