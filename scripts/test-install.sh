#!/usr/bin/env bash

# Run Docker-based integration tests for install.sh.
# Requires Docker to be installed and running.

set -euo pipefail

source "$(dirname "$0")/env.sh"

TESTS_DIR="$REPO_ROOT/tests/install"
IMAGE_BASE="se-install-test"
IMAGE_NO_D2="se-install-test-no-d2"
IMAGE_OLD_PYTHON="se-install-test-old-python"

# --- Build wheel artifacts ---

echo "Building wheel for testing..."
ARTIFACTS_DIR="$(mktemp -d)"
trap 'rm -rf "$ARTIFACTS_DIR"' EXIT

wheel_filename="$("$REPO_ROOT/scripts/build-wheel.sh" "$ARTIFACTS_DIR")"
echo "  Wheel: $wheel_filename"

# --- Build Docker images ---

echo ""
echo "Building Docker images..."
docker build -t "$IMAGE_BASE" -f "$TESTS_DIR/Dockerfile" "$TESTS_DIR"
docker build -t "$IMAGE_NO_D2" -f "$TESTS_DIR/Dockerfile.no-d2" "$TESTS_DIR"
docker build -t "$IMAGE_OLD_PYTHON" -f "$TESTS_DIR/Dockerfile.old-python" "$TESTS_DIR"

# --- Helper ---

run_container() {
    local image="$1"
    shift
    docker run --rm \
        -v "$ARTIFACTS_DIR:/artifacts:ro" \
        -v "$REPO_ROOT/install.sh:/install.sh:ro" \
        "$image" \
        bash -c "$*"
}

pass=0
fail=0

run_test() {
    local name="$1"
    local image="$2"
    shift 2
    local script="$*"

    echo ""
    echo "--- Test: $name ---"
    if run_container "$image" "$script"; then
        echo "OK: $name"
        pass=$((pass + 1))
    else
        echo "FAIL: $name" >&2
        fail=$((fail + 1))
    fi
}

run_test_expect_fail() {
    local name="$1"
    local image="$2"
    local expect_msg="$3"
    shift 3
    local script="$*"

    echo ""
    echo "--- Test: $name ---"
    local output
    if output=$(run_container "$image" "$script" 2>&1); then
        echo "FAIL: $name (expected failure but script succeeded)" >&2
        fail=$((fail + 1))
    elif echo "$output" | grep -qi "$expect_msg"; then
        echo "OK: $name"
        pass=$((pass + 1))
    else
        echo "FAIL: $name (exited non-zero but output did not contain '$expect_msg')" >&2
        echo "Output: $output" >&2
        fail=$((fail + 1))
    fi
}

# --- Test cases ---

run_test "Fresh install" "$IMAGE_BASE" '
    bash /install.sh --local /artifacts &&
    test -L "$HOME/.local/bin/systems-engineering" &&
    test -d "$HOME/.local/share/systems-engineering/venv" &&
    "$HOME/.local/bin/systems-engineering" --version
'

run_test "Idempotent upgrade" "$IMAGE_BASE" '
    bash /install.sh --local /artifacts &&
    bash /install.sh --local /artifacts &&
    "$HOME/.local/bin/systems-engineering" --version
'

run_test "Uninstall" "$IMAGE_BASE" '
    bash /install.sh --local /artifacts &&
    "$HOME/.local/bin/systems-engineering" --version &&
    bash /install.sh --uninstall &&
    test ! -e "$HOME/.local/bin/systems-engineering" &&
    test ! -d "$HOME/.local/share/systems-engineering/venv"
'

run_test_expect_fail "Missing d2" "$IMAGE_NO_D2" "d2" \
    'bash /install.sh --local /artifacts'

run_test_expect_fail "Missing Python 3.10+" "$IMAGE_OLD_PYTHON" "python" \
    'bash /install.sh --local /artifacts'

run_test_expect_fail "Bad checksum" "$IMAGE_BASE" "checksum" '
    mkdir -p /tmp/bad-artifacts &&
    cp /artifacts/*.whl /tmp/bad-artifacts/ &&
    echo "0000000000000000000000000000000000000000000000000000000000000000  fake.whl" > /tmp/bad-artifacts/fake.whl.sha256 &&
    bash /install.sh --local /tmp/bad-artifacts
'

# --- Summary ---

echo ""
echo "================================"
echo "Results: $pass passed, $fail failed"
echo "================================"

if [[ $fail -gt 0 ]]; then
    exit 1
fi

echo ""
echo "All install integration tests passed."
