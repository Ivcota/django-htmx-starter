# TODOs

## Phase 2 — HTMX Patterns & DX

### Django messages + HTMX toast notifications
Every real app needs flash messages (success/error/info). Show toasts via HTMX OOB swaps — the pattern every project needs after the counter example. **Effort: S | Priority: P1**

### HTMX form submission example
The counter shows button clicks, but forms (create/edit with validation errors swapped inline) are the bread and butter of real apps. An "add item to list" example would complete the HTMX pattern set. **Effort: M | Priority: P1**

### HTMX search/filter example
Active search with `hx-trigger="keyup changed delay:300ms"` — demonstrates hx-trigger, hx-indicator (loading spinner), and partial list rendering. **Effort: M | Priority: P2**

### Ruff linter + pre-commit hooks
Add ruff config to pyproject.toml and .pre-commit-config.yaml. Ruff replaces flake8+isort+black in a single fast tool. **Effort: S | Priority: P2**

### Production email backend
Add env-var-based email backend switching (console for dev, SMTP/SendGrid/SES for production). Currently console-only. **Effort: S | Priority: P2**

## Vision — Delight Opportunities

### `just new-app <name>` recipe
Auto-create a Django app with the right structure (views, urls, tests, templates dir) and wire it into INSTALLED_APPS and config/urls.py.

### HTMX loading indicator
Global loading bar (thin progress bar at top, like YouTube/GitHub) that shows during any HTMX request via htmx:beforeRequest/afterRequest events.

### Dark/light theme toggle
The starter already has CSS variables for a dark theme. Add a toggle (stored in localStorage) that swaps the variable set.

### Environment-aware justfile recipes
Add recipes that are aware of deployment targets (e.g., `just deploy staging`). Requires deployment strategy to be finalized first. **Effort: L | Priority: P3**

### Favicon
An SVG favicon to complete the visual polish of the starter.
