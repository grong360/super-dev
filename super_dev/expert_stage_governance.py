from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .workflow_guard import load_stage_ledger
from .workflow_stage_truth import CANONICAL_WORKFLOW_STAGE_CHAIN, active_experts_for_stage

_LEDGER_STAGE_FALLBACKS: dict[str, tuple[str, ...]] = {
    "docs_confirm": ("docs_confirm", "docs"),
    "preview_confirm": ("preview_confirm", "preview"),
}


def _load_pipeline_state(project_dir: Path) -> dict[str, Any]:
    file_path = Path(project_dir).resolve() / ".super-dev" / "pipeline-state.json"
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _ledger_entry_for_stage(ledger: dict[str, Any], stage: str) -> dict[str, Any]:
    candidates = _LEDGER_STAGE_FALLBACKS.get(stage, (stage,))
    for key in candidates:
        payload = ledger.get(key, {})
        if isinstance(payload, dict) and payload:
            return payload
    return {}


def _extract_recorded_experts(payload: dict[str, Any]) -> list[str]:
    value = payload.get("active_experts", [])
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        expert_id = str(item).strip()
        if expert_id and expert_id not in result:
            result.append(expert_id)
    return result


def collect_expert_stage_governance(
    project_dir: Path,
    *,
    stage_statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    pipeline_state = _load_pipeline_state(project_dir)
    ledger = load_stage_ledger(project_dir)
    normalized_stage_statuses = {
        str(key).strip(): str(value).strip()
        for key, value in (stage_statuses or {}).items()
        if str(key).strip()
    }

    current_stage = str(pipeline_state.get("canonical_phase", "")).strip()
    current_active_experts = _extract_recorded_experts(
        {"active_experts": pipeline_state.get("active_experts", [])}
    )

    stages: list[dict[str, Any]] = []
    gaps: list[str] = []
    covered_count = 0

    for stage in CANONICAL_WORKFLOW_STAGE_CHAIN:
        stage_status = normalized_stage_statuses.get(stage, "pending")
        expected_experts = list(active_experts_for_stage(stage))
        ledger_entry = _ledger_entry_for_stage(ledger, stage)
        recorded_experts = _extract_recorded_experts(ledger_entry)
        if not recorded_experts and stage == current_stage:
            recorded_experts = list(current_active_experts)

        if stage_status == "pending":
            evidence_status = "pending"
        elif not expected_experts:
            evidence_status = "not_required"
        elif not recorded_experts:
            evidence_status = "missing"
        elif set(expected_experts).issubset(set(recorded_experts)):
            evidence_status = "recorded"
        else:
            evidence_status = "partial"

        if evidence_status == "recorded":
            covered_count += 1
        if stage_status != "pending" and evidence_status in {"missing", "partial"}:
            gaps.append(stage)

        stages.append(
            {
                "stage": stage,
                "status": stage_status,
                "expected_experts": expected_experts,
                "recorded_experts": recorded_experts,
                "evidence_status": evidence_status,
                "ledger_entry": ledger_entry,
            }
        )

    visible_stage_count = sum(
        1 for item in stages if item["status"] in {"running", "waiting", "completed"}
    )
    if gaps:
        summary = "专家阶段证据未闭环：" + "、".join(gaps[:4])
    elif visible_stage_count > 0:
        summary = f"已显式记录 {covered_count} 个阶段的专家参与证据。"
    else:
        summary = "当前还没有需要校验的阶段专家证据。"

    return {
        "current_stage": current_stage,
        "covered_count": covered_count,
        "visible_stage_count": visible_stage_count,
        "missing_stages": gaps,
        "summary": summary,
        "stages": stages,
    }
