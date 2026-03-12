#!/usr/bin/env bash
set -o errexit

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies from lockfile
uv sync --frozen

# Collect static files
uv run python manage.py collectstatic --no-input

# Run database migrations
uv run python manage.py migrate
