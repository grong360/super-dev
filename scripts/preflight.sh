#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ALLOW_DIRTY=0
SKIP_BENCHMARK=0
SKIP_PACKAGE=0
SKIP_DELIVERY_SMOKE=0
SKIP_HOST_COMPAT_GATE=0
USE_UV=0

for arg in "$@"; do
    case "$arg" in
        --allow-dirty)
            ALLOW_DIRTY=1
            ;;
        --skip-benchmark)
            SKIP_BENCHMARK=1
            ;;
        --skip-package)
            SKIP_PACKAGE=1
            ;;
        --skip-delivery-smoke)
            SKIP_DELIVERY_SMOKE=1
            ;;
        --skip-host-compat-gate)
            SKIP_HOST_COMPAT_GATE=1
            ;;
        --uv)
            USE_UV=1
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./scripts/preflight.sh [--allow-dirty] [--skip-benchmark] [--skip-package] [--skip-delivery-smoke] [--skip-host-compat-gate] [--uv]"
            exit 2
            ;;
    esac
done

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[ERROR] python3/python not found in PATH"
    exit 1
fi

if [[ "$USE_UV" -ne 1 ]] && command -v uv >/dev/null 2>&1 && [[ -f "$ROOT_DIR/uv.lock" ]]; then
    USE_UV=1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="output/release/preflight-$TIMESTAMP"
mkdir -p "$REPORT_DIR"

SUMMARY_FILE="$REPORT_DIR/summary.txt"
touch "$SUMMARY_FILE"

echo "[INFO] Preflight started at $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$SUMMARY_FILE"
echo "[INFO] Project root: $ROOT_DIR" | tee -a "$SUMMARY_FILE"
echo "[INFO] Python: $PYTHON_BIN" | tee -a "$SUMMARY_FILE"
if [[ "$USE_UV" -eq 1 ]]; then
    echo "[INFO] Package manager: uv" | tee -a "$SUMMARY_FILE"
else
    echo "[INFO] Package manager: pip/python" | tee -a "$SUMMARY_FILE"
fi

if [[ "$ALLOW_DIRTY" -ne 1 ]]; then
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "[ERROR] Working tree is dirty. Commit or stash changes, or run with --allow-dirty." | tee -a "$SUMMARY_FILE"
        exit 1
    fi
else
    echo "[WARN] --allow-dirty enabled; skipping clean working tree check." | tee -a "$SUMMARY_FILE"
fi

FAILED=0

run_check() {
    local name="$1"
    local cmd="$2"
    local log_file="$REPORT_DIR/${name}.log"

    echo "[INFO] Running: $name" | tee -a "$SUMMARY_FILE"
    set +e
    bash -lc "$cmd" >"$log_file" 2>&1
    local code=$?
    set -e
    if [[ $code -eq 0 ]]; then
        echo "[PASS] $name" | tee -a "$SUMMARY_FILE"
    else
        echo "[FAIL] $name (exit $code) -> $log_file" | tee -a "$SUMMARY_FILE"
        FAILED=1
    fi
}

run_advisory_check() {
    local name="$1"
    local cmd="$2"
    local log_file="$REPORT_DIR/${name}.log"

    echo "[INFO] Running advisory: $name" | tee -a "$SUMMARY_FILE"
    set +e
    bash -lc "$cmd" >"$log_file" 2>&1
    local code=$?
    set -e
    if [[ $code -eq 0 ]]; then
        echo "[PASS] $name" | tee -a "$SUMMARY_FILE"
    else
        echo "[WARN] $name advisory failed (exit $code) -> $log_file" | tee -a "$SUMMARY_FILE"
    fi
}

project_run() {
    local cmd="$1"
    if [[ "$USE_UV" -eq 1 ]]; then
        printf 'uv run %s' "$cmd"
    else
        printf '%s' "$cmd"
    fi
}

require_python_module() {
    local module="$1"
    if [[ "$USE_UV" -eq 1 ]]; then
        uv run "$PYTHON_BIN" -c "import $module" >/dev/null 2>&1
    else
        "$PYTHON_BIN" -c "import $module" >/dev/null 2>&1
    fi
}

run_check "ruff" "$(project_run "ruff check super_dev tests --output-format concise")"
run_check "type-gates" "$(project_run "$PYTHON_BIN scripts/check_type_gates.py --project-dir \"$ROOT_DIR\"")"
run_advisory_check "mypy-full" "$(project_run "mypy super_dev")"
run_check "pytest" "$(project_run "pytest -q")"
run_check "knowledge-audit" "$(project_run "$PYTHON_BIN scripts/audit_development_kb.py")"
run_check "knowledge-gates" "$(project_run "$PYTHON_BIN scripts/check_knowledge_gates.py --project-dir \"$ROOT_DIR\"")"

if [[ "$SKIP_DELIVERY_SMOKE" -ne 1 ]]; then
    run_check "delivery-smoke" "$(project_run "$PYTHON_BIN scripts/check_delivery_ready.py --smoke --project-dir \"$ROOT_DIR\"")"
else
    echo "[WARN] delivery smoke skipped by --skip-delivery-smoke" | tee -a "$SUMMARY_FILE"
fi

if [[ "$SKIP_HOST_COMPAT_GATE" -ne 1 ]]; then
    run_check "host-compat-detect" "$(project_run "$PYTHON_BIN -m super_dev.cli detect --auto --json >/dev/null")"
    run_check "host-compat-gate" "$(project_run "$PYTHON_BIN scripts/check_host_compatibility.py --project-dir \"$ROOT_DIR\" --min-score 80 --min-ready-hosts 1")"
else
    echo "[WARN] host compatibility gate skipped by --skip-host-compat-gate" | tee -a "$SUMMARY_FILE"
fi

if [[ "$USE_UV" -eq 1 ]]; then
    run_check "bandit" "uvx --from bandit bandit -ll -r super_dev -f json -o $REPORT_DIR/bandit.json"
    run_check "pip-audit" "uv run $PYTHON_BIN -m pip_audit --local -f json -o $REPORT_DIR/pip-audit.json"
else
    if require_python_module "bandit"; then
        run_check "bandit" "$(project_run "$PYTHON_BIN -m bandit -ll -r super_dev -f json -o $REPORT_DIR/bandit.json")"
    else
        echo "[FAIL] bandit module not installed (pip install bandit)" | tee -a "$SUMMARY_FILE"
        FAILED=1
    fi

    if require_python_module "pip_audit"; then
        run_check "pip-audit" "$(project_run "$PYTHON_BIN -m pip_audit . -f json -o $REPORT_DIR/pip-audit.json")"
    else
        echo "[FAIL] pip_audit module not installed (pip install pip-audit)" | tee -a "$SUMMARY_FILE"
        FAILED=1
    fi
fi

if [[ "$SKIP_BENCHMARK" -ne 1 ]]; then
    run_check "benchmark" "$(project_run "$PYTHON_BIN tests/benchmark.py")"
else
    echo "[WARN] benchmark skipped by --skip-benchmark" | tee -a "$SUMMARY_FILE"
fi

if [[ "$SKIP_PACKAGE" -ne 1 ]]; then
    if [[ "$USE_UV" -eq 1 ]]; then
        run_check "build" "uv build"
        run_check "twine-check" "uvx twine check dist/*"
    else
        run_check "build" "rm -rf dist/ build/ *.egg-info && $PYTHON_BIN -m build"
        run_check "twine-check" "twine check dist/*"
    fi
else
    echo "[WARN] package checks skipped by --skip-package" | tee -a "$SUMMARY_FILE"
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "[PASS] Preflight completed successfully." | tee -a "$SUMMARY_FILE"
    echo "[INFO] Report directory: $REPORT_DIR"
    exit 0
fi

echo "[FAIL] Preflight failed. See report: $REPORT_DIR" | tee -a "$SUMMARY_FILE"
exit 1
