#!/usr/bin/env python3
"""Run release-blocking mypy checks on the supported core surface."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CORE_TYPE_TARGETS = [
    "super_dev/analyzer/baseline_audit.py",
    "super_dev/baseline_governance.py",
    "super_dev/cli_deploy_runtime_mixin.py",
    "super_dev/evidence_identity.py",
    "super_dev/framework_harness.py",
    "super_dev/host_adapters.py",
    "super_dev/host_diagnostics.py",
    "super_dev/host_entry_decisions.py",
    "super_dev/host_registry.py",
    "super_dev/host_runtime_governance.py",
    "super_dev/host_runtime_probe.py",
    "super_dev/host_runtime_validation.py",
    "super_dev/host_session_resume.py",
    "super_dev/host_usage_profile.py",
    "super_dev/host_workflow_context.py",
    "super_dev/integrations/manager.py",
    "super_dev/review_state.py",
    "super_dev/web/api.py",
    "super_dev/work_mode.py",
    "super_dev/workflow_guard.py",
    "super_dev/workflow_stage_truth.py",
    "super_dev/workflow_state.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run release-blocking mypy checks on the supported core surface."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project root directory. Defaults to current directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON summary instead of plain text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()

    cmd = [sys.executable, "-m", "mypy", *CORE_TYPE_TARGETS]
    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    payload = {
        "project_dir": str(project_dir),
        "targets": CORE_TYPE_TARGETS,
        "command": cmd,
        "status": "pass" if result.returncode == 0 else "fail",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[{'PASS' if result.returncode == 0 else 'FAIL'}] type-gates "
            f"({len(CORE_TYPE_TARGETS)} targets)"
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
