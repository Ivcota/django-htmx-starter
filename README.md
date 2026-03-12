# Django + HTMX + Tailwind Starter

A batteries-included Django starter template with:

- **[django-allauth](https://docs.allauth.org/)** — Email-based authentication with signup, login, logout, and password reset
- **[HTMX](https://htmx.org/)** — Add interactivity without writing JavaScript
- **[Tailwind CSS](https://tailwindcss.com/)** — Utility-first CSS with hot reload via django-tailwind
- **[Django Cotton](https://django-cotton.com/)** — Component-based templates with clean `<c-component />` syntax
- **PostgreSQL** — Production-grade database with Docker Compose for local dev
- **Deployment-ready** — Pre-configured for Railway and Docker

## Tech Stack

| Layer       | Tool                     |
|-------------|--------------------------|
| Framework   | Django 5.2               |
| Auth        | django-allauth           |
| Interactivity | HTMX + django-htmx    |
| CSS         | Tailwind CSS             |
| Components  | Django Cotton            |
| Database    | PostgreSQL               |
| Static Files| WhiteNoise               |
| Server      | Gunicorn + Uvicorn       |
| Packages    | uv                       |

## Quick Start

```bash
# Clone and enter the project
git clone <your-repo-url>
cd django-htmx-starter

# One-command setup (creates .env, starts DB, installs deps, runs migrations)
just setup

# Start development server + Tailwind watcher
just dev
```

Requires [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), and [Docker](https://www.docker.com/) (for PostgreSQL).

## Available Commands

```
just dev          # Run server + Tailwind watcher
just server       # Run Django dev server only
just tailwind     # Run Tailwind watcher only
just db           # Start PostgreSQL via Docker Compose
just db-stop      # Stop PostgreSQL
just migrate      # Run Django migrations
just test         # Run tests
just setup        # Full initial setup
```

## Project Structure

```
├── config/           # Django settings, URLs, WSGI/ASGI
├── core/             # Your application code (views, models, admin)
├── templates/        # HTML templates
│   ├── cotton/       # Reusable components (layout, header, footer, etc.)
│   └── account/      # Auth templates (login, signup, etc.)
├── theme/            # Tailwind CSS configuration
├── justfile          # Task runner recipes
├── docker-compose.yml
└── pyproject.toml
```
