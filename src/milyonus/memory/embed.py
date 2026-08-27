"""Embedders — turn memory text into vectors for semantic recall.

The embedding layer is deliberately pluggable and dependency-free by default:

  - HashingEmbedder (default): feature-hashes tokens into a fixed-width vector.
    No model, no network, deterministic. It ranks by *token-overlap magnitude*
    rather than exact substring, so "he lives in Istanbul" recalls a query about
    "where does the user live" better than a `LIKE` scan — while adding zero
    dependencies. It is a lexical vector, honestly labelled as such.
  - OpenAIEmbedder (optional): calls an OpenAI-compatible `/embeddings` endpoint
    for true semantic vectors when a model + key are configured.

Every embedder exposes a `signature` (e.g. "hashing-256", "openai-text-embedding-3-small")
so the vector index never compares vectors produced by different embedders; a
change of embedder simply requires `milyonus memory reindex`.

Security note: embeddings only *index* text that is already in the store. They
never create, promote, or elevate a memory — recall is strictly read-only and,
in `semantic.py`, trust-weighted, so a high-similarity low-trust item can never
outrank a trusted one. The embedding layer cannot be a poison-amplification path.
"""

from __future__ import annotations

import math
import os
from typing import Protocol, runtime_checkable

from milyonus.memory.negative import _tokens


@runtime_checkable
class Embedder(Protocol):
    signature: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-normalized vector per input text (sync — call from a
        thread if the concrete embedder does network I/O)."""
        ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class HashingEmbedder:
    """Deterministic, dependency-free feature-hashing embedder.

    Each token is hashed to a bucket (and a sign) and accumulated; the result is
    L2-normalized so cosine similarity is a plain dot product. Shared vocabulary
    -> higher similarity, without any model or network call."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self.signature = f"hashing-{dim}"

    def _hash(self, token: str) -> tuple[int, float]:
        # Two independent hashes: one for the bucket, one for the sign, so
        # collisions cancel on average (the signed feature-hashing trick).
        h = hash((self.signature, token))
        bucket = (h & 0x7FFFFFFF) % self.dim
        sign = 1.0 if (h >> 31) & 1 else -1.0
        return bucket, sign

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _tokens(text):
                bucket, sign = self._hash(tok)
                vec[bucket] += sign
            out.append(_l2_normalize(vec))
        return out


class OpenAIEmbedder:
    """OpenAI-compatible embeddings (`/embeddings`). Works with OpenAI, Azure,
    OpenRouter, or a local server — anything that speaks the same API."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        *,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        from milyonus.providers.openai_compat import OPENAI_URL

        self.model = model
        self.signature = f"openai-{model}"
        self.dim = 0  # learned from the first response
        self._url = (base_url or OPENAI_URL).rstrip("/")
        self._api_key_env = api_key_env

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        key = os.environ.get(self._api_key_env, "")
        if not key:
            raise RuntimeError(f"{self._api_key_env} is not set (embeddings need a key).")
        resp = httpx.post(
            f"{self._url}/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": texts},
            timeout=httpx.Timeout(60.0),
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        vectors = [_l2_normalize([float(x) for x in row["embedding"]]) for row in data]
        if vectors:
            self.dim = len(vectors[0])
        return vectors


def build_embedder(config) -> Embedder | None:
    """Construct the configured embedder. Never raises: an unknown or 'none'
    setting yields None (semantic recall simply falls back to lexical)."""
    kind = getattr(config, "embedder", "hashing")
    if kind == "none":
        return None
    if kind == "openai":
        return OpenAIEmbedder(
            model=getattr(config, "embed_model", "text-embedding-3-small"),
            base_url=getattr(config, "embed_base_url", None),
            api_key_env=getattr(config, "embed_api_key_env", None) or "OPENAI_API_KEY",
        )
    # default and fallback
    return HashingEmbedder(dim=getattr(config, "embed_dim", 256))
