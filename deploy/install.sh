#!/usr/bin/env sh
# Milyonus Agent installer. Installs uv if missing, then the milyonus CLI.
set -eu

echo "✦ Milyonus Agent installer"

if ! command -v uv >/dev/null 2>&1; then
  echo "→ installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "→ installing milyonus-agent..."
uv tool install milyonus-agent

echo ""
echo "✦ done. Next:"
echo "    milyonus setup     # add your provider key"
echo "    milyonus doctor    # verify"
echo "    milyonus           # start a session"
