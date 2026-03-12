---
name: adr
description: Create or list Architecture Decision Records (ADRs). Use when the user wants to document an architectural decision, review past decisions, or understand why something was built a certain way.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Architecture Decision Record (ADR) Skill

Create and manage Architecture Decision Records in `docs/adr/`.

## Usage

- `/adr` — List all existing ADRs
- `/adr <title>` — Create a new ADR with the given title

## When creating a new ADR

1. Read existing ADRs in `docs/adr/` to determine the next sequence number.
2. Create the file as `docs/adr/NNNN-<kebab-case-title>.md` (e.g., `0001-use-django-for-backend.md`).
3. Use the template below.
4. Fill in the **Context** and **Decision** sections based on the conversation so far and any arguments provided. If insufficient context exists, ask the user.
5. Leave **Consequences** with reasonable inferences but ask the user to confirm.

## When listing ADRs

Read all files in `docs/adr/` and present a summary table with: number, title, status, and date.

## Template

```markdown
# <NUMBER>. <Title>

Date: <YYYY-MM-DD>

## Status

<Proposed | Accepted | Deprecated | Superseded by [ADR-NNNN](NNNN-slug.md)>

## Context

<What is the issue that we're seeing that is motivating this decision or change?>

## Decision

<What is the change that we're proposing and/or doing?>

## Consequences

<What becomes easier or more difficult to do because of this change?>
```

## Conventions

- Sequence numbers are zero-padded to 4 digits.
- Status for new ADRs defaults to **Proposed**.
- Use today's date (from the system context) for the Date field.
- Keep language concise and direct.
