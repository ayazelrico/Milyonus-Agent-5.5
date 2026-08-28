# Milyonus Agent — developer convenience targets.
.PHONY: sync test lint fmt check hooks build docker-build docker-run poison safety

sync:        ## install deps (matches CI: dev + admin + discord)
	uv sync --extra dev --extra admin --extra discord

hooks:       ## enable the versioned git hooks (pre-push runs `make check`)
	git config core.hooksPath .githooks
	@echo "✓ git hooks enabled (.githooks). Pushes now run 'make check' first."

test:        ## run the test suite
	uv run pytest -q

lint:        ## lint
	uv run ruff check src tests

fmt:         ## format
	uv run ruff format src tests

check: lint  ## lint + format-check + test
	uv run ruff format --check src tests
	uv run pytest -q

build:       ## build the wheel
	uv build

poison:      ## run PoisonBench (rule-based)
	uv run python -m evals.poisonbench.run

safety:      ## run SafetyRegression
	uv run python -m evals.safety.run

docker-build:   ## build the hardened image
	docker build -f deploy/Dockerfile -t milyonus/agent:5.5.0 -t milyonus/agent:latest .

docker-run:     ## run a session in the container (mounts a data volume)
	docker run --rm -it \
	  --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 \
	  -v milyonus-data:/data milyonus/agent:latest doctor
