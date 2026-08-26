# Milyonus Agent 5.5 — hardened runtime image.
# Multi-stage: build a self-contained venv with uv, then a slim non-root runtime.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Copy only what the build needs (bundled skills live under src/milyonus/).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# Frozen, no dev deps -> reproducible runtime venv at /app/.venv.
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Milyonus Agent" \
      org.opencontainers.image.description="Self-improving agent that remembers, verifies, evolves." \
      org.opencontainers.image.version="5.5.0" \
      org.opencontainers.image.licenses="Apache-2.0"

# Non-root user; state lives in a volume owned by it.
RUN useradd --create-home --uid 10001 milyonus \
    && mkdir -p /data && chown milyonus:milyonus /data
COPY --from=build --chown=milyonus:milyonus /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    MILYONUS_HOME=/data \
    PYTHONUNBUFFERED=1
USER milyonus
WORKDIR /app
VOLUME ["/data"]

# Liveness: the CLI must resolve and report its version.
HEALTHCHECK --interval=1m --timeout=10s --start-period=10s --retries=3 \
    CMD ["milyonus", "--version"]

ENTRYPOINT ["milyonus"]
CMD ["--help"]
