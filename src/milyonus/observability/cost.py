"""Token → USD cost estimation.

Prices are per one million tokens (input, output), in USD. They are approximate
and configurable — override with set_price() or a config table. Unknown models
fall back to a conservative mid-tier estimate so a cost is always produced (and
flagged as estimated).
"""

from __future__ import annotations

from dataclasses import dataclass

# (input $/Mtok, output $/Mtok). Approximate public list prices; adjust freely.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-opus-5": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
}
_FALLBACK = (3.0, 15.0)  # conservative mid-tier when a model is unknown


@dataclass(slots=True)
class Cost:
    usd: float
    estimated: bool  # True when the model price was a fallback


def set_price(model: str, input_per_m: float, output_per_m: float) -> None:
    _PRICES[model] = (input_per_m, output_per_m)


def cost_of(model: str, input_tokens: int, output_tokens: int) -> Cost:
    price = _PRICES.get(model)
    estimated = price is None
    inp, out = price or _FALLBACK
    usd = (input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out
    return Cost(usd=round(usd, 6), estimated=estimated)
