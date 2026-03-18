#!/usr/bin/env bash
# Shared helpers for worktree setup and teardown

DB_PREFIX="django_starter"

# Convert a directory name to a valid Postgres database name.
# Usage: sanitize_db_name "my-feature/branch"
# Output: django_starter_my_feature_branch
sanitize_db_name() {
    local dir_name="$1"
    local sanitized
    sanitized=$(echo "$dir_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_]/_/g')
    echo "${DB_PREFIX}_${sanitized}"
}

# Generate a .env file for a worktree with a unique DATABASE_URL.
# Usage: generate_worktree_env "/path/to/.env.example" "/path/to/worktree"
generate_worktree_env() {
    local env_example="$1"
    local worktree_path="$2"
    local dir_name
    dir_name=$(basename "$worktree_path")
    local db_name
    db_name=$(sanitize_db_name "$dir_name")

    sed "s|postgresql://postgres:postgres@localhost:5432/django_starter|postgresql://postgres:postgres@localhost:5432/${db_name}|" \
        "$env_example" > "$worktree_path/.env"
}

# Get the database name for a worktree given its full path.
# Usage: worktree_db_name "/path/to/my-feature-branch"
# Output: django_starter_my_feature_branch
worktree_db_name() {
    local worktree_path="$1"
    sanitize_db_name "$(basename "$worktree_path")"
}

# Given a newline-separated list of databases and worktree paths,
# find databases that don't correspond to any existing worktree.
# Skips the main "django_starter" database (no suffix).
# Usage: find_orphaned_databases "$db_list" "$worktree_list"
find_orphaned_databases() {
    local db_list="$1"
    local worktree_list="$2"

    # Build a set of expected database names from worktree paths
    local expected_dbs=""
    while IFS= read -r wt_path; do
        [ -z "$wt_path" ] && continue
        expected_dbs="${expected_dbs}$(worktree_db_name "$wt_path")"$'\n'
    done <<< "$worktree_list"

    # Check each database — if it's not the main db and not in the expected set, it's orphaned
    while IFS= read -r db; do
        [ -z "$db" ] && continue
        [ "$db" = "$DB_PREFIX" ] && continue
        if ! echo "$expected_dbs" | grep -qx "$db"; then
            echo "$db"
        fi
    done <<< "$db_list"
}
