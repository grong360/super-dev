from __future__ import annotations

from pathlib import Path
from typing import Any

from .reviewers.architecture_drift import (
    inspect_architecture_drift_artifact,
    run_architecture_drift,
)
from .reviewers.spec_compliance import inspect_spec_compliance_artifact, run_spec_compliance
from .reviewers.uiux_compliance import inspect_uiux_compliance_artifact, run_uiux_compliance


def collect_compliance_governance_signal(
    project_dir: Path,
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    output_dir = (output_dir or project_dir / "output").resolve()

    spec_inspection = inspect_spec_compliance_artifact(project_dir, output_dir)
    spec_report = run_spec_compliance(project_dir, output_dir)
    architecture_inspection = inspect_architecture_drift_artifact(project_dir, output_dir)
    architecture_report = run_architecture_drift(project_dir, output_dir)
    uiux_inspection = inspect_uiux_compliance_artifact(project_dir, output_dir)
    uiux_report = run_uiux_compliance(project_dir, output_dir)

    signals = {
        "spec": {
            "label": "Spec Compliance",
            "artifact_status": str(spec_inspection.get("status", "")).strip() or "missing",
            "score": spec_report.score,
            "content_ready": spec_report.total_requirements <= 0 or spec_report.score >= 80,
        },
        "architecture": {
            "label": "Architecture Drift",
            "artifact_status": str(architecture_inspection.get("status", "")).strip() or "missing",
            "score": architecture_report.score,
            "content_ready": (
                (not architecture_report.declared_tech_stack and architecture_report.total_drifts == 0)
                or architecture_report.score >= 80
            ),
        },
        "uiux": {
            "label": "UIUX Compliance",
            "artifact_status": str(uiux_inspection.get("status", "")).strip() or "missing",
            "score": uiux_report.score,
            "content_ready": uiux_report.files_scanned <= 0 or uiux_report.score >= 80,
        },
    }

    source_issues = [
        f"{key}={item['artifact_status']}"
        for key, item in signals.items()
        if item["artifact_status"] != "ready"
    ]
    content_issues = [
        str(item["label"])
        for item in signals.values()
        if item["artifact_status"] == "ready" and not item["content_ready"]
    ]

    if source_issues:
        summary = "合规链当前优先卡在证据状态：" + "、".join(source_issues[:3]) + "。"
    elif content_issues:
        summary = "合规链证据已齐，但内容仍未达标：" + "、".join(content_issues[:3]) + "。"
    else:
        summary = "合规链证据与内容检查当前均已闭环。"

    return {
        "summary": summary,
        "source_issues": source_issues,
        "content_issues": content_issues,
        "signals": signals,
    }
