#!/usr/bin/env bash
# Launch the Trust Layer Agent Streamlit UI.
# Run from the project root:
#   bash scripts/run_ui.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate venv if present.
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

streamlit run src/ui/app.py --server.port 8501
