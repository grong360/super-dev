from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact_utils import latest_artifact, resolve_project_artifact_prefix
from .baseline_governance import inspect_baseline_governance
from .framework_harness import FrameworkHarnessBuilder
from .host_workflow_context import build_host_workflow_context
from .operational_harness import OperationalHarnessBuilder
from .ui_contract_governance import missing_claude_design_runtime_checks
from .workflow_harness import WorkflowHarnessBuilder
from .workflow_state import detect_pipeline_summary

_SPEC_REQUIRED_STATUSES = {
    "missing_frontend",
    "waiting_ui_revision",
    "waiting_preview_confirmation",
    "missing_backend",
    "missing_quality",
    "waiting_quality_revision",
    "missing_delivery",
    "proof_pack_incomplete",
}

_FRONTEND_RUNTIME_REQUIRED_STATUSES = {
    "waiting_ui_revision",
    "waiting_preview_confirmation",
    "missing_backend",
    "missing_quality",
    "waiting_quality_revision",
    "missing_delivery",
    "proof_pack_incomplete",
}


def _status_label(status: str) -> str:
    mapping = {
        "pending": "待补齐仓库级 probe",
        "passed": "仓库级 probe 通过",
        "failed": "仓库级 probe 失败",
    }
    return mapping.get(status, "待补齐仓库级 probe")


def build_host_runtime_probe(
    project_dir: Path,
    *,
    target: str,
    surface_ready: bool,
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    session_brief_path = project_dir / ".super-dev" / "SESSION_BRIEF.md"
    workflow_state_path = project_dir / ".super-dev" / "workflow-state.json"

    pipeline_summary = detect_pipeline_summary(project_dir)
    workflow_harness = WorkflowHarnessBuilder(project_dir).build()
    framework_harness = FrameworkHarnessBuilder(project_dir).build()
    operational_harness = OperationalHarnessBuilder(project_dir).build()
    output_dir = project_dir / "output"
    project_name = resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)

    artifacts = pipeline_summary.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}

    workflow_status = str(pipeline_summary.get("workflow_status", "")).strip()
    current_stage_name = str(pipeline_summary.get("current_stage_name", "")).strip()
    recommended_command = str(pipeline_summary.get("recommended_command", "")).strip()
    baseline_governance = inspect_baseline_governance(project_dir, output_dir=output_dir)

    docs_present = bool(artifacts.get("prd")) and bool(artifacts.get("architecture")) and bool(
        artifacts.get("uiux")
    )
    spec_present = bool(artifacts.get("spec"))
    frontend_runtime_state = artifacts.get("frontend_runtime_state", {})
    frontend_runtime_current = bool(artifacts.get("frontend")) and not bool(
        isinstance(frontend_runtime_state, dict) and frontend_runtime_state.get("stale", False)
    )
    ui_contract_path = latest_artifact(
        output_dir, "*-ui-contract.json", preferred_prefix=project_name
    )
    frontend_runtime_path = latest_artifact(
        output_dir, "*-frontend-runtime.json", preferred_prefix=project_name
    )
    ui_contract_payload: dict[str, Any] = {}
    frontend_runtime_payload: dict[str, Any] = {}
    if ui_contract_path is not None:
        try:
            loaded_contract = json.loads(ui_contract_path.read_text(encoding="utf-8"))
            if isinstance(loaded_contract, dict):
                ui_contract_payload = loaded_contract
        except Exception:
            ui_contract_payload = {}
    if frontend_runtime_path is not None:
        try:
            loaded_runtime = json.loads(frontend_runtime_path.read_text(encoding="utf-8"))
            if isinstance(loaded_runtime, dict):
                frontend_runtime_payload = loaded_runtime
        except Exception:
            frontend_runtime_payload = {}
    missing_protocol_checks = missing_claude_design_runtime_checks(
        frontend_runtime_payload.get("checks", {})
        if isinstance(frontend_runtime_payload.get("checks"), dict)
        else {},
        ui_contract_payload,
    )
    ui_execution_protocol_current = not missing_protocol_checks

    active_context = (
        session_brief_path.exists()
        or workflow_state_path.exists()
        or workflow_harness.enabled
        or any(
            [
                bool(
                    isinstance(pipeline_summary.get("docs_confirmation"), dict)
                    and pipeline_summary["docs_confirmation"].get("exists")
                ),
                bool(
                    isinstance(pipeline_summary.get("preview_confirmation"), dict)
                    and pipeline_summary["preview_confirmation"].get("exists")
                ),
                bool(
                    isinstance(pipeline_summary.get("ui_revision"), dict)
                    and pipeline_summary["ui_revision"].get("exists")
                ),
                bool(
                    isinstance(pipeline_summary.get("architecture_revision"), dict)
                    and pipeline_summary["architecture_revision"].get("exists")
                ),
                bool(
                    isinstance(pipeline_summary.get("quality_revision"), dict)
                    and pipeline_summary["quality_revision"].get("exists")
                ),
            ]
        )
    )

    checks = {
        "surface_ready": surface_ready,
        "session_brief_present": session_brief_path.exists(),
        "workflow_state_present": workflow_state_path.exists(),
        "baseline_ready": True if not baseline_governance.get("required") else bool(baseline_governance.get("ready")),
        "core_docs_present": docs_present,
        "spec_present": True if workflow_status not in _SPEC_REQUIRED_STATUSES else spec_present,
        "frontend_runtime_current": (
            True
            if workflow_status not in _FRONTEND_RUNTIME_REQUIRED_STATUSES
            else frontend_runtime_current
        ),
        "ui_execution_protocol_current": (
            True
            if workflow_status not in _FRONTEND_RUNTIME_REQUIRED_STATUSES
            else ui_execution_protocol_current
        ),
        "workflow_harness_passed": True if not active_context else workflow_harness.passed,
        "framework_harness_passed": True if not framework_harness.enabled else framework_harness.passed,
        "operational_harness_passed": (
            True if not operational_harness.enabled else operational_harness.passed
        ),
    }

    blockers: list[str] = []
    next_actions: list[str] = []
    if active_context:
        if not checks["session_brief_present"]:
            blockers.append("SESSION_BRIEF.md 缺失，宿主恢复缺少当前步骤摘要")
        if not checks["workflow_state_present"]:
            blockers.append("workflow-state.json 缺失，宿主恢复缺少机器可读状态")
        if baseline_governance.get("required") and not checks["baseline_ready"]:
            blockers.append(str(baseline_governance.get("blocker", "")).strip() or "baseline governance 未闭环")
            if str(baseline_governance.get("recommended_command", "")).strip():
                next_actions.append(str(baseline_governance.get("recommended_command", "")).strip())
        if not checks["workflow_harness_passed"]:
            blockers.extend(workflow_harness.blockers[:2] or ["workflow continuity harness 未通过"])
            next_actions.extend(workflow_harness.next_actions[:2])
        if workflow_status not in {"missing_research", "missing_core_docs", "waiting_docs_confirmation"}:
            if not checks["core_docs_present"]:
                blockers.append("当前活动流程缺少完整三文档真源")
        if workflow_status in _SPEC_REQUIRED_STATUSES and not checks["spec_present"]:
            blockers.append("当前阶段缺少 Spec proposal / tasks 真源")
        if (
            workflow_status in _FRONTEND_RUNTIME_REQUIRED_STATUSES
            and not checks["frontend_runtime_current"]
        ):
            blockers.append("当前阶段前端 runtime 证据缺失或已过期")
        elif (
            workflow_status in _FRONTEND_RUNTIME_REQUIRED_STATUSES
            and not checks["ui_execution_protocol_current"]
        ):
            blockers.append(
                "当前阶段 frontend runtime 未证明 Claude-Design 风格 UI 执行协议已落地: "
                + ",".join(missing_protocol_checks)
            )
        if framework_harness.enabled and not checks["framework_harness_passed"]:
            blockers.extend(framework_harness.blockers[:1] or ["framework harness 未通过"])
            next_actions.extend(framework_harness.next_actions[:1])
        if operational_harness.enabled and not checks["operational_harness_passed"]:
            blockers.extend(operational_harness.blockers[:1] or ["operational harness 未通过"])
            next_actions.extend(operational_harness.next_actions[:1])

    if not active_context:
        status = "pending"
        summary = "尚未检测到活动 workflow continuity，当前 probe 仅提供仓库级提示"
        if recommended_command:
            next_actions.append(recommended_command)
    elif blockers:
        status = "failed"
        summary = f"{current_stage_name or workflow_status or target} 所需仓库级连续性证据不完整"
        if recommended_command:
            next_actions.append(recommended_command)
    else:
        status = "passed"
        summary = f"{current_stage_name or workflow_status or target} 的仓库级连续性证据已满足恢复要求"

    deduped_actions: list[str] = []
    for item in next_actions:
        text = str(item).strip()
        if text and text not in deduped_actions:
            deduped_actions.append(text)

    return {
        "status": status,
        "status_label": _status_label(status),
        "summary": summary,
        "active_context": active_context,
        "workflow_status": workflow_status,
        "current_stage_name": current_stage_name,
        "recommended_command": recommended_command,
        "checks": checks,
        "blockers": blockers,
        "next_actions": deduped_actions,
        "baseline_governance": baseline_governance,
        "workflow_context": build_host_workflow_context(
            project_dir,
            summary=pipeline_summary,
            entry_mode="continue" if active_context else "start",
            recommended_host_action=str(baseline_governance.get("next_host_action", "")).strip(),
            recommended_host_sentence=str(
                baseline_governance.get("fallback_text_entry", "")
            ).strip(),
            target=target,
        ),
        "source_files": {
            "session_brief": str(session_brief_path),
            "workflow_state": str(workflow_state_path),
        },
        "workflow_harness": {
            "enabled": workflow_harness.enabled,
            "passed": workflow_harness.passed,
        },
        "framework_harness": {
            "enabled": framework_harness.enabled,
            "passed": framework_harness.passed,
        },
        "operational_harness": {
            "enabled": operational_harness.enabled,
            "passed": operational_harness.passed,
        },
    }
