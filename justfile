# Requires just >= 1.23
# https://github.com/casey/just

manage := "uv run python manage.py"
port := `uv run python -c "import hashlib, os; print(3000 + int(hashlib.md5(os.path.basename(os.getcwd()).encode()).hexdigest(), 16) % 57000)"`

# List all available recipes
default:
    @just --list

# ── Setup ─────────────────────────────────────────────────

# Initial project setup: create .env, start db, sync deps, install npm packages, run migrations
[group: 'setup']
setup: dotenv db sync npm-install migrate hooks

# Copy .env.example to .env (skips if .env already exists)
[group: 'setup']
dotenv:
    #!/usr/bin/env bash
    if [ -f .env ]; then
        echo ".env already exists, skipping"
    else
        cp .env.example .env
        echo "Created .env from .env.example"
    fi

# Sync Python dependencies with uv
[group: 'setup']
sync *args:
    uv sync {{args}}

# Install npm dependencies for Tailwind
[group: 'setup']
npm-install:
    cd theme/static_src && npm install

# Configure git to use project hooks
[group: 'setup']
hooks:
    git config core.hooksPath .githooks

# ── Development ───────────────────────────────────────────

# Run both the server and Tailwind watcher
[group: 'development']
dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just server &
    just tailwind &
    wait

# Run the Django development server
[group: 'development']
server:
    {{manage}} runserver {{port}}

# Start the Tailwind CSS watcher
[group: 'development']
tailwind:
    {{manage}} tailwind start

# ── Database ──────────────────────────────────────────────

# Start the PostgreSQL database via Docker Compose
[group: 'database']
db:
    docker compose up -d --wait

# Stop the PostgreSQL database
[group: 'database']
db-stop:
    docker compose down

# Reset database to empty state
[confirm('This will DELETE all data. Continue?')]
[group: 'database']
db-reset:
    {{manage}} flush --no-input
    {{manage}} migrate

# Run Django migrations
[group: 'database']
migrate:
    {{manage}} migrate

# Create new migrations from model changes
[group: 'database']
makemigrations *args:
    {{manage}} makemigrations {{args}}

# ── Django ────────────────────────────────────────────────

# Run any manage.py command
[group: 'django']
manage *args:
    {{manage}} {{args}}

# Open the Django shell
[group: 'django']
shell:
    {{manage}} shell

# Open the PostgreSQL shell
[group: 'django']
dbshell:
    {{manage}} dbshell

# Create a superuser
[group: 'django']
createsuperuser:
    {{manage}} createsuperuser

# Run Django system checks
[group: 'django']
check *args:
    {{manage}} check {{args}}

# Collect static files
[group: 'django']
collectstatic:
    {{manage}} collectstatic --noinput

# Seed example Products and Prices for development
[group: 'database']
seed-payments:
    {{manage}} seed_payments

# ── Worktree ─────────────────────────────────────────────

# Remove a worktree and drop its database
[group: 'worktree']
worktree-remove path:
    #!/usr/bin/env bash
    set -euo pipefail
    source scripts/worktree-helpers.sh
    WORKTREE_PATH="{{path}}"
    DB_NAME=$(worktree_db_name "$WORKTREE_PATH")
    echo "Dropping database: $DB_NAME"
    docker compose exec -T postgres dropdb -U postgres --if-exists "$DB_NAME"
    git worktree remove "$WORKTREE_PATH"
    echo "Removed worktree and database: $WORKTREE_PATH ($DB_NAME)"

# Drop databases for worktrees that no longer exist
[group: 'worktree']
worktree-prune:
    #!/usr/bin/env bash
    set -euo pipefail
    source scripts/worktree-helpers.sh
    # Get all databases matching our prefix
    DBS=$(docker compose exec -T postgres psql -U postgres -tAc \
        "SELECT datname FROM pg_database WHERE datname LIKE '${DB_PREFIX}_%';")
    # Get all worktree paths
    WORKTREES=$(git worktree list --porcelain | grep '^worktree ' | sed 's/^worktree //')
    ORPHANS=$(find_orphaned_databases "$DBS" "$WORKTREES")
    if [ -z "$ORPHANS" ]; then
        echo "No orphaned databases found."
    else
        while IFS= read -r db; do
            [ -z "$db" ] && continue
            echo "Dropping orphaned database: $db"
            docker compose exec -T postgres dropdb -U postgres --if-exists "$db"
        done <<< "$ORPHANS"
        echo "Prune complete."
    fi

# ── Quality ───────────────────────────────────────────────

# Run tests
[group: 'quality']
test *args:
    {{manage}} test {{args}}

# Run linter
[group: 'quality']
lint *args:
    uv run ruff check {{args}} .

# Auto-format code
[group: 'quality']
format *args:
    uv run ruff format {{args}} .

# Run worktree helper tests
[group: 'quality']
test-worktree:
    bash tests/test_worktree.sh

# Test static files with DEBUG off (verifies WhiteNoise is working)
[group: 'quality']
test-static:
    {{manage}} collectstatic --noinput
    DEBUG=0 ALLOWED_HOSTS='*' {{manage}} runserver {{port}}

# Run CI workflow locally using act
[group: 'quality']
ci:
    #!/usr/bin/env bash
    set -euo pipefail
    # Find and stop any container using port 5432
    CONTAINER=$(docker ps --format '{{{{.ID}}' --filter 'publish=5432' 2>/dev/null || true)
    if [ -n "$CONTAINER" ]; then
        echo "Stopping container on port 5432..."
        docker stop "$CONTAINER"
    fi
    cleanup() {
        # Stop any leftover act containers on 5432
        LEFTOVER=$(docker ps --format '{{{{.ID}}' --filter 'publish=5432' 2>/dev/null || true)
        if [ -n "$LEFTOVER" ]; then
            docker stop "$LEFTOVER" 2>/dev/null || true
        fi
        echo "Restarting dev postgres..."
        docker compose up -d --wait
    }
    trap cleanup EXIT
    echo "Running act..."
    act push --env-file /dev/null --secret GITHUB_TOKEN="$(gh auth token)"
