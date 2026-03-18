#!/usr/bin/env bash
set -euo pipefail

# ── Test helpers ─────────────────────────────────────────
PASS=0
FAIL=0

assert_eq() {
    local description="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS: $description"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $description"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

# Resolve project root relative to this script
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Source the helpers we're testing
source "$PROJECT_ROOT/scripts/worktree-helpers.sh"

# ── Tests ────────────────────────────────────────────────

echo "=== sanitize_db_name ==="

assert_eq "simple directory name" \
    "django_starter_my_feature" \
    "$(sanitize_db_name "my_feature")"

assert_eq "hyphens become underscores" \
    "django_starter_my_feature_branch" \
    "$(sanitize_db_name "my-feature-branch")"

assert_eq "slashes become underscores" \
    "django_starter_feature_auth" \
    "$(sanitize_db_name "feature/auth")"

assert_eq "dots become underscores" \
    "django_starter_v2_1_hotfix" \
    "$(sanitize_db_name "v2.1.hotfix")"

assert_eq "mixed special characters" \
    "django_starter_feature_auth_v2" \
    "$(sanitize_db_name "feature/auth-v2")"

assert_eq "uppercase becomes lowercase" \
    "django_starter_my_feature" \
    "$(sanitize_db_name "My-Feature")"

echo ""
echo "=== generate_worktree_env ==="

# Set up a temp directory to simulate a worktree
TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Create a fake .env.example in our "project root"
FAKE_PROJECT="$TMPDIR_TEST/django-htmx-starter"
mkdir -p "$FAKE_PROJECT"
cat > "$FAKE_PROJECT/.env.example" <<'ENVEOF'
SECRET_KEY=django-insecure-dev-key-change-me
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/django_starter
WEB_CONCURRENCY=4
ENVEOF

# Simulate a worktree directory
FAKE_WORKTREE="$TMPDIR_TEST/my-feature-branch"
mkdir -p "$FAKE_WORKTREE"

# Run the function
generate_worktree_env "$FAKE_PROJECT/.env.example" "$FAKE_WORKTREE"

# Verify .env was created
if [ -f "$FAKE_WORKTREE/.env" ]; then
    assert_eq ".env file created" "true" "true"
else
    assert_eq ".env file created" "true" "false"
fi

# Verify DATABASE_URL was rewritten with sanitized name
ACTUAL_DB_URL=$(grep "^DATABASE_URL=" "$FAKE_WORKTREE/.env" | cut -d= -f2-)
assert_eq "DATABASE_URL uses worktree db name" \
    "postgresql://postgres:postgres@localhost:5432/django_starter_my_feature_branch" \
    "$ACTUAL_DB_URL"

# Verify other values are preserved
ACTUAL_DEBUG=$(grep "^DEBUG=" "$FAKE_WORKTREE/.env" | cut -d= -f2-)
assert_eq "other env vars preserved" "true" "$ACTUAL_DEBUG"

echo ""
echo "=== just setup sets hooksPath ==="

ACTUAL_HOOKS_PATH=$(cd "$PROJECT_ROOT" && git config --local core.hooksPath 2>/dev/null || echo "NOT SET")
assert_eq "core.hooksPath is .githooks" ".githooks" "$ACTUAL_HOOKS_PATH"

echo ""
echo "=== worktree_db_name (resolve db name from path) ==="

assert_eq "derives db name from worktree path" \
    "django_starter_my_feature_branch" \
    "$(worktree_db_name "/tmp/worktrees/my-feature-branch")"

assert_eq "derives db name from nested path" \
    "django_starter_fix_auth" \
    "$(worktree_db_name "/home/user/code/fix-auth")"

echo ""
echo "=== find_orphaned_databases ==="

# Simulate: 3 databases exist, but only 2 worktrees
MOCK_DBS="django_starter
django_starter_feature_auth
django_starter_old_branch
django_starter_active_work"

MOCK_WORKTREES="/Users/me/project
/Users/me/feature-auth
/Users/me/active-work"

ORPHANS=$(find_orphaned_databases "$MOCK_DBS" "$MOCK_WORKTREES")
assert_eq "identifies orphaned database" "django_starter_old_branch" "$ORPHANS"

# ── Summary ──────────────────────────────────────────────

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
