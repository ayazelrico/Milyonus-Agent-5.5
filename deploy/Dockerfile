# Milyonus Agent — hardened runtime image.
# Multi-stage: build a venv with uv, then a slim non-root runtime.
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# Install into a self-contained venv.
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

# Non-root user; data lives in a volume owned by it.
RUN useradd --create-home --uid 10001 milyonus \
    && mkdir -p /data && chown milyonus:milyonus /data
COPY --from=build --chown=milyonus:milyonus /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    MILYONUS_HOME=/data \
    PYTHONUNBUFFERED=1
USER milyonus
WORKDIR /app
VOLUME ["/data"]
ENTRYPOINT ["milyonus"]
CMD ["--help"]
