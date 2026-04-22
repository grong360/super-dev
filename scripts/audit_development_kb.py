#!/usr/bin/env python3
"""兼容旧 preflight 入口的知识库审计包装器。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        str(project_dir / "scripts" / "check_knowledge_gates.py"),
        "--project-dir",
        str(project_dir),
    ]
    completed = subprocess.run(command)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
