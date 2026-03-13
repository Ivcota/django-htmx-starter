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
setup: dotenv db sync npm-install migrate

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

# Test static files with DEBUG off (verifies WhiteNoise is working)
[group: 'quality']
test-static:
    {{manage}} collectstatic --noinput
    DEBUG=0 ALLOWED_HOSTS='*' {{manage}} runserver {{port}}
