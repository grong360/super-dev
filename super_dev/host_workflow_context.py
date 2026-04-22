"""Shared machine-readable workflow context for host-facing surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .baseline_governance import inspect_baseline_governance
from .workflow_state import build_host_action_prompt, detect_pipeline_summary


def build_host_workflow_context(
    project_dir: Path,
    *,
    summary: dict[str, Any] | None = None,
    entry_mode: str = "",
    recommended_host_action: str = "",
    recommended_host_sentence: str = "",
    target: str = "",
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    resolved_summary: dict[str, Any] = (
        summary if isinstance(summary, dict) else detect_pipeline_summary(project_dir)
    )
    baseline_payload = resolved_summary.get("baseline_governance")
    baseline: dict[str, Any] = (
        baseline_payload
        if isinstance(baseline_payload, dict)
        else inspect_baseline_governance(project_dir)
    )
    workflow_status = str(resolved_summary.get("workflow_status", "")).strip()
    checkpoint_status = workflow_status
    baseline_required = bool(baseline.get("required", False))
    baseline_audit_status = (
        "ready"
        if bool(baseline.get("audit_exists", False))
        else ("not_required" if not baseline_required else "missing")
    )
    baseline_confirmation_status = (
        str(baseline.get("confirmation_status", "")).strip()
        or ("not_required" if not baseline_required else "missing")
    )
    resume_gate_status = str(baseline.get("resume_state", "")).strip() or "clear"
    blocking_gate = workflow_status if workflow_status in {
        "missing_baseline",
        "waiting_baseline_confirmation",
        "waiting_resume_gate",
        "waiting_docs_confirmation",
        "waiting_preview_confirmation",
        "waiting_ui_revision",
        "waiting_architecture_revision",
        "waiting_quality_revision",
    } else ""
    blocking_reason = str(resolved_summary.get("blocker", "")).strip() or str(
        baseline.get("blocking_reason", "")
    ).strip()
    next_action = (
        str(recommended_host_action).strip()
        or str(baseline.get("next_host_action", "")).strip()
        or "/super-dev 继续当前流程"
    )
    next_sentence = (
        str(recommended_host_sentence).strip()
        or str(baseline.get("fallback_text_entry", "")).strip()
        or "super-dev: 继续当前流程"
    )
    resolved_target = str(target).strip()
    if resolved_target:
        action_bundle = build_host_action_prompt(
            target=resolved_target,
            action_text=next_action or next_sentence,
            flow_variant=str(resolved_summary.get("flow_variant", "")).strip() or "standard",
        )
        next_action = str(action_bundle.get("action", "")).strip() or next_action
        next_sentence = str(action_bundle.get("sentence", "")).strip() or next_sentence
    effective_entry_mode = str(entry_mode).strip() or (
        "continue" if str(resolved_summary.get("workflow_mode", "")).strip() != "start" else "start"
    )
    return {
        "entry_mode": effective_entry_mode,
        "project_work_mode": str(resolved_summary.get("work_mode", "")).strip(),
        "project_work_mode_label": str(resolved_summary.get("work_mode_label", "")).strip(),
        "workflow_status": workflow_status,
        "checkpoint_status": checkpoint_status,
        "current_stage_canonical_id": str(
            resolved_summary.get("current_stage_canonical_id", "")
        ).strip(),
        "current_stage_name": str(resolved_summary.get("current_stage_name", "")).strip(),
        "flow_variant": str(resolved_summary.get("flow_variant", "")).strip(),
        "baseline_required": baseline_required,
        "baseline_audit_status": baseline_audit_status,
        "baseline_confirmation_status": baseline_confirmation_status,
        "resume_gate_status": resume_gate_status,
        "blocking_gate": blocking_gate,
        "blocking_reason": blocking_reason,
        "recommended_workflow_command": str(
            resolved_summary.get("recommended_command", "")
        ).strip(),
        "recommended_host_action": next_action,
        "recommended_host_sentence": next_sentence,
        "can_resume": effective_entry_mode == "continue" or blocking_gate == "waiting_resume_gate",
        "can_progress": not blocking_gate and bool(baseline.get("can_enter_delta_flow", True)),
    }
