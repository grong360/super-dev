from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

WorkMode = Literal["new", "evolve", "variant", "patch", "resume"]

WORK_MODE_LABELS: dict[str, str] = {
    "new": "从 0 到 1",
    "evolve": "已有项目增量迭代",
    "variant": "版本派生 / 1-N+1",
    "patch": "缺陷修复",
    "resume": "恢复当前流程",
}


def normalize_work_mode(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in WORK_MODE_LABELS:
        return normalized
    return "new"


def detect_work_mode(project_dir: Path, workflow_payload: dict[str, Any] | None = None) -> str:
    payload = workflow_payload or {}
    explicit = normalize_work_mode(str(payload.get("work_mode", "")).strip() or None)
    if str(payload.get("work_mode", "")).strip():
        return explicit

    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    review_state_dir = project_dir / ".super-dev" / "review-state"

    if (review_state_dir / "resume-gate.json").exists():
        return "resume"
    if any(output_dir.glob("*-variant-contract.json")):
        return "variant"
    if any(output_dir.glob("*-patch-scope.json")):
        return "patch"
    if any(output_dir.glob("*-baseline-audit.md")) or any(output_dir.glob("*-baseline-audit.json")):
        return "evolve"
    return "new"


def work_mode_requires_baseline(work_mode: str) -> bool:
    return normalize_work_mode(work_mode) in {"evolve", "variant", "patch"}


def work_mode_label(work_mode: str) -> str:
    normalized = normalize_work_mode(work_mode)
    return WORK_MODE_LABELS.get(normalized, normalized)
