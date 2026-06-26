#!/usr/bin/env bash

set -euo pipefail

if [ -n "${CI:-}" ]; then
  # CI: report and fail, never rewrite
  uv run ruff format --check src
  uv run ruff check src
else
  # local: actually fix
  uv run ruff format src
  uv run ruff check --fix src
fi

uv run ty check src