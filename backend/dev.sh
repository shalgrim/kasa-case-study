#!/usr/bin/env bash
# Dev helper script — wraps common venv-dependent commands (compile deps,
# install, run server, tests) so they can be invoked as a single command
# without needing to manually activate the venv each time. Also makes it
# easier to grant blanket permission to an AI assistant to run these
# operations without approving raw `source .venv/bin/activate && ...` chains.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"

case "${1:-help}" in
  compile)
    source "$VENV/bin/activate"
    uv pip compile requirements.in -o requirements.txt
    uv pip compile requirements-dev.in -o requirements-dev.txt
    echo "Lock files compiled."
    ;;
  install)
    source "$VENV/bin/activate"
    pip install -r requirements-dev.txt
    echo "Dev dependencies installed."
    ;;
  compile-install)
    source "$VENV/bin/activate"
    uv pip compile requirements.in -o requirements.txt
    uv pip compile requirements-dev.in -o requirements-dev.txt
    pip install -r requirements-dev.txt
    echo "Compiled and installed."
    ;;
  check)
    source "$VENV/bin/activate"
    python -c "from app.main import app; print('FastAPI app loaded OK')"
    ;;
  run)
    source "$VENV/bin/activate"
    uvicorn app.main:app --reload --port "${2:-8000}"
    ;;
  test)
    source "$VENV/bin/activate"
    pytest "${@:2}"
    ;;
  help)
    echo "Usage: ./dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  compile          Compile .in files to lock files"
    echo "  install          Install dev dependencies from lock files"
    echo "  compile-install  Compile + install in one step"
    echo "  check            Verify the app imports cleanly"
    echo "  run [port]       Run the dev server (default port 8000)"
    echo "  test [args]      Run pytest with optional args"
    ;;
  *)
    echo "Unknown command: $1"
    "$0" help
    exit 1
    ;;
esac
