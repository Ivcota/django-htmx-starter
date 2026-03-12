port := `uv run python -c "import hashlib, os; print(3000 + int(hashlib.md5(os.path.basename(os.getcwd()).encode()).hexdigest(), 16) % 57000)"`

# List all available recipes
default:
    @just --list

# Run the Django development server
server:
    uv run python manage.py runserver {{port}}

# Start the Tailwind CSS watcher
tailwind:
    uv run python manage.py tailwind start

# Run both the server and Tailwind watcher
dev:
    just server & just tailwind & wait

# Start the PostgreSQL database via Docker Compose
db:
    docker compose up -d --wait

# Stop the PostgreSQL database
db-stop:
    docker compose down

# Copy .env.example to .env (skips if .env already exists)
dotenv:
    @[ -f .env ] && echo ".env already exists, skipping" || cp .env.example .env && echo "Created .env from .env.example"

# Sync dependencies with uv
sync:
    uv sync

# Run Django migrations
migrate:
    uv run python manage.py migrate

# Install npm dependencies for Tailwind
npm-install:
    cd theme/static_src && npm install

# Run tests
test *args:
    uv run python manage.py test {{args}}

# Test static files with DEBUG off (verifies WhiteNoise is working)
test-static:
    uv run python manage.py collectstatic --noinput
    DEBUG=0 ALLOWED_HOSTS='*' uv run python manage.py runserver {{port}}

# Initial project setup: create .env, start db, sync deps, install npm packages, run migrations
setup: dotenv db sync npm-install migrate
