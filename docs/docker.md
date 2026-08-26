# Docker

Milyonus ships a hardened multi-stage image (`deploy/Dockerfile`): a uv build
stage produces a frozen venv, and a slim non-root runtime stage runs it. Bundled
skills travel inside the package, so the image is self-contained.

## Build

```bash
make docker-build         # or:
docker build -f deploy/Dockerfile -t milyonus/agent:5.5.0 .
```

## Run

State (config, memory, skills, secrets) lives in a `/data` volume owned by the
non-root `milyonus` user (uid 10001).

```bash
# one-off diagnostics
docker run --rm -it \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 \
  -v milyonus-data:/data milyonus/agent:5.5.0 doctor

# an interactive session (add your key to the volume's .env first)
docker run --rm -it -v milyonus-data:/data milyonus/agent:5.5.0 chat
```

Put secrets in the volume's `.env` (never bake them into the image):

```bash
docker run --rm -v milyonus-data:/data milyonus/agent:5.5.0 \
  sh -c 'echo ANTHROPIC_API_KEY=sk-ant-... > /data/.env && chmod 600 /data/.env'
```

## Gateway with compose (production)

`deploy/compose.yaml` runs the gateway with the full hardening set: read-only
root filesystem, `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, and a
size-limited noexec `/tmp`.

```bash
cp deploy/compose.yaml .
echo 'ANTHROPIC_API_KEY=sk-ant-...' > milyonus.env
echo 'TELEGRAM_BOT_TOKEN=...'      >> milyonus.env
docker compose up -d
docker compose logs -f
```

The image declares a `HEALTHCHECK` (`milyonus --version`) so orchestrators can
tell when it is live.
