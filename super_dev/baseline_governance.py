from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact_utils import latest_artifact, resolve_project_artifact_prefix
from .protocols.output_schemas import OutputValidator
from .review_state import (
    baseline_confirmation_file,
    load_baseline_confirmation,
    load_resume_gate,
    load_workflow_state,
    resume_gate_file,
)
from .work_mode import detect_work_mode, work_mode_label, work_mode_requires_baseline


def inspect_baseline_governance(
    project_dir: Path,
    *,
    workflow_payload: dict[str, Any] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    output_dir = output_dir or (project_dir / "output")
    payload = workflow_payload if isinstance(workflow_payload, dict) else (load_workflow_state(project_dir) or {})
    project_name = resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)
    work_mode = detect_work_mode(project_dir, payload)
    required = work_mode_requires_baseline(work_mode)

    markdown_path = latest_artifact(
        output_dir,
        "*-baseline-audit.md",
        preferred_prefix=project_name,
    )
    json_path = latest_artifact(
        output_dir,
        "*-baseline-audit.json",
        preferred_prefix=project_name,
    )
    audit_json_schema_valid = False
    audit_json_schema_errors: list[str] = []
    if json_path is not None and json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            audit_json_schema_errors = [f"invalid baseline audit json: {exc}"]
        else:
            if isinstance(payload, dict):
                audit_json_schema_valid, audit_json_schema_errors = OutputValidator().validate(
                    payload,
                    "baseline_audit",
                )
            else:
                audit_json_schema_errors = ["baseline audit json must be an object"]
    audit_path = markdown_path or json_path
    audit_exists = audit_path is not None and audit_path.exists()

    confirmation_payload = load_baseline_confirmation(project_dir) or {}
    confirmation_exists = bool(confirmation_payload)
    confirmation_status = (
        str(confirmation_payload.get("status", "")).strip() if confirmation_payload else ""
    )
    confirmation_path = baseline_confirmation_file(project_dir)
    resume_payload = load_resume_gate(project_dir) or {}
    resume_status = (
        str(resume_payload.get("status", "")).strip() if resume_payload else ""
    ) or "clear"
    resume_path = resume_gate_file(project_dir)

    if not required:
        baseline_state = "not_required"
        ready = True
        summary = "baseline confirmation not required for current work mode"
        blocker = ""
        recommended_command = ""
    elif not audit_exists:
        baseline_state = "missing_audit"
        ready = False
        summary = "baseline audit missing"
        blocker = "当前是已有项目模式，但 baseline audit 还没生成。"
        recommended_command = "在宿主里先扫描当前项目并建立 baseline，再继续当前流程"
    elif not confirmation_exists:
        baseline_state = "missing_confirmation"
        ready = False
        summary = "baseline confirmation missing"
        blocker = "baseline 已生成，但还没确认当前项目边界、复用面和差量计划。"
        recommended_command = "在宿主里先确认 baseline；如果通过，直接说“baseline 确认，可以继续当前流程”"
    elif confirmation_status == "confirmed":
        baseline_state = "confirmed"
        ready = True
        summary = "baseline confirmed"
        blocker = ""
        recommended_command = "在宿主里说“继续当前流程”"
    elif confirmation_status == "revision_requested":
        baseline_state = "revision_requested"
        ready = False
        summary = "baseline confirmation revision_requested"
        blocker = "当前项目基线已被要求返工，必须先修正 baseline 审计和差量范围。"
        recommended_command = "在宿主里继续修正 baseline；确认后直接说“baseline 确认，可以继续当前流程”"
    else:
        normalized = confirmation_status or "pending_review"
        baseline_state = "pending_confirmation"
        ready = False
        summary = f"baseline confirmation {normalized}"
        blocker = "已有项目已完成 baseline，但当前必须先确认基线边界、影响范围和差量计划。"
        recommended_command = "在宿主里先确认 baseline；如果通过，直接说“baseline 确认，可以继续当前流程”"

    if resume_status not in {"clear", "confirmed"}:
        entry_gate = "waiting_resume_gate"
        entry_gate_open = False
        can_enter_delta_flow = False
        blocking_reason = "当前存在恢复门，必须先明确恢复点，再继续当前流程。"
        recommended_command = "在宿主里先确认恢复点；如果通过，直接说“恢复点确认，可以继续当前流程”"
        host_guidance_summary = "当前先处理 resume gate，明确从哪个阶段恢复，再继续当前流程。"
        next_host_action = "/super-dev-run resume"
        fallback_text_entry = "super-dev-run: resume"
    elif baseline_state in {"revision_requested", "missing_confirmation", "pending_confirmation"}:
        entry_gate = "waiting_baseline_confirmation"
        entry_gate_open = False
        can_enter_delta_flow = False
        blocking_reason = blocker
        host_guidance_summary = "已有项目先 baseline，再确认 baseline，之后才继续差量文档与实现。"
        next_host_action = "/super-dev-review baseline confirm"
        fallback_text_entry = "super-dev-review: baseline confirm"
    elif baseline_state == "missing_audit":
        entry_gate = "missing_baseline"
        entry_gate_open = False
        can_enter_delta_flow = False
        blocking_reason = blocker
        host_guidance_summary = "已有项目必须先做 baseline 扫描，确认现状和差量范围后再继续。"
        next_host_action = "/super-dev 在当前项目里继续当前流程，先做 baseline"
        fallback_text_entry = "super-dev: 先扫描当前项目并建立 baseline，再继续当前流程"
    else:
        entry_gate = "ready"
        entry_gate_open = True
        can_enter_delta_flow = True
        blocking_reason = ""
        host_guidance_summary = (
            "baseline / resume 入口门已闭环，可以继续当前流程。"
            if required
            else "当前模式不需要 baseline，可以直接继续当前流程。"
        )
        next_host_action = "/super-dev 继续当前流程"
        fallback_text_entry = "super-dev: 继续当前流程"

    return {
        "work_mode": work_mode,
        "work_mode_label": work_mode_label(work_mode),
        "required": required,
        "ready": ready,
        "status": baseline_state,
        "baseline_state": baseline_state,
        "summary": summary,
        "blocker": blocker,
        "recommended_command": recommended_command,
        "audit_exists": audit_exists,
        "audit_path": str(audit_path) if audit_path else "",
        "audit_markdown_path": str(markdown_path) if markdown_path else "",
        "audit_json_path": str(json_path) if json_path else "",
        "audit_json_schema_valid": audit_json_schema_valid,
        "audit_json_schema_errors": audit_json_schema_errors,
        "confirmation_exists": confirmation_exists,
        "confirmation_status": confirmation_status or ("confirmed" if ready and required else ""),
        "confirmation_path": str(confirmation_path),
        "confirmation": confirmation_payload,
        "resume_state": resume_status,
        "resume_gate_path": str(resume_path),
        "resume_gate": resume_payload,
        "entry_gate": entry_gate,
        "entry_gate_open": entry_gate_open,
        "can_enter_delta_flow": can_enter_delta_flow,
        "blocking_reason": blocking_reason,
        "host_guidance_summary": host_guidance_summary,
        "next_host_action": next_host_action,
        "fallback_text_entry": fallback_text_entry,
    }
