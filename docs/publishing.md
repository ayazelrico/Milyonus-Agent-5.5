# Publishing a release

Releases are automated by `.github/workflows/release.yml`: pushing a `vX.Y.Z`
tag runs the tests, builds the wheel, creates a GitHub Release, publishes to
PyPI, and builds + pushes the Docker image. Two one-time setups are required.

## 1. PyPI — Trusted Publishing (no stored token)

1. Reserve the project name on PyPI (upload once manually, or create the project
   via the Trusted Publisher form).
2. On PyPI → your project → *Publishing*, add a **GitHub Actions** trusted
   publisher:
   - Owner: `milyonus` (your org/user)
   - Repository: `milyonus-agent`
   - Workflow: `release.yml`
   - Environment: `release`
3. In the GitHub repo, create an **Environment** named `release` (Settings →
   Environments). Optionally add required reviewers to gate publishes.

No API token is stored — publishing uses short-lived OIDC credentials.

## 2. Docker Hub

1. Create the `milyonus/agent` repository on Docker Hub.
2. Create an access token (Docker Hub → Account Settings → Security).
3. Add repo secrets: `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

## Cutting a release

```bash
# bump version in pyproject.toml + src/milyonus/version.py, update CHANGELOG.md
git commit -am "Release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The workflow does the rest. Verify: the GitHub Release, `pip install
milyonus-agent==X.Y.Z`, and `docker pull milyonus/agent:vX.Y.Z`.

## Manual fallback

```bash
uv build
uv publish                       # needs PyPI credentials / trusted publishing
docker buildx build --platform linux/amd64,linux/arm64 \
  -f deploy/Dockerfile -t milyonus/agent:vX.Y.Z --push .
```
