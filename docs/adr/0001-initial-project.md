# 0001. Initial Project

Date: 2026-03-13

## Status

Proposed

## Context

We need a reusable Django starter template that prioritizes developer productivity and a server-driven architecture. The goal is to avoid the complexity of a separate frontend SPA (React, Vue, etc.) while still delivering a modern, interactive user experience. The stack should include authentication out of the box, utility-first styling, component-based templates, and be deployment-ready from day one.

## Decision

We are adopting the following technology stack:

- **Django 5.2** as the web framework, using a `config/` project layout with a `core/` app for application code.
- **HTMX** (via `django-htmx`) for adding interactivity without writing JavaScript, keeping the server as the single source of truth.
- **Tailwind CSS** (via `django-tailwind`) for utility-first styling with hot reload during development.
- **Django Cotton** for component-based templates using `<c-component />` syntax, replacing verbose `{% include %}` patterns.
- **django-allauth** for email-based authentication (signup, login, logout, password reset) with social account support available.
- **PostgreSQL 17** as the database, run locally via Docker Compose.
- **WhiteNoise** for serving static files without a CDN or separate file server.
- **Gunicorn + Uvicorn** as the production WSGI/ASGI server.
- **uv** for Python package management.
- **just** as a task runner for common development commands.
- Deployment pre-configured for **Railway** (via `railway.toml`, `Procfile`, and `build.sh`).

## Consequences

- **Easier:** Rapid prototyping with a cohesive, batteries-included stack. No frontend build pipeline beyond Tailwind. Authentication works immediately. Deployment to Railway requires minimal configuration.
- **Easier:** Server-driven approach with HTMX means less client-side state management and no API serialization layer to maintain.
- **More difficult:** Teams accustomed to SPA patterns will need to learn the HTMX/hypermedia approach. Complex client-side interactions may require supplementing HTMX with Alpine.js or similar.
- **More difficult:** Django Cotton is a newer library with a smaller community compared to established template approaches.
