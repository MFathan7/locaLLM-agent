#!/usr/bin/env bash
# locaLLM Local Runner for Linux and macOS
# Automatically invokes locaLLM using the local virtual environment.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    exec "$SCRIPT_DIR/.venv/bin/python" -m locallm "$@"
elif [ -x "$SCRIPT_DIR/.venv/bin/locallm" ]; then
    exec "$SCRIPT_DIR/.venv/bin/locallm" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m locallm "$@"
else
    echo "Error: Python 3 environment not found." >&2
    echo "Please run './install.sh' first to set up locaLLM." >&2
    exit 1
fi
