"""Shared host usage profile serialization helpers."""

from __future__ import annotations

from typing import Any

from .catalogs import host_path_override_guide
from .host_adaptation_contract import build_host_adaptation_contract
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_experience_profile,
    build_host_official_pass_criteria,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from .integrations.manager import HostAdapterProfile
from .workflow_state import build_host_flow_contract, build_host_flow_probe


def serialize_host_usage_profile(
    *,
    profile: HostAdapterProfile,
    target: str,
    final_trigger: str,
    managed_competition_project_surfaces: list[str] | None = None,
    managed_competition_user_surfaces: list[str] | None = None,
    host_value: str | None = None,
    include_host_id: bool = False,
    include_capability_labels: bool = False,
    include_docs_fields: bool = False,
    skill_slash_entry_host_id: str | None = None,
    skill_slash_entry_note: str = "",
    flow_host_id: str | None = None,
) -> dict[str, Any]:
    host_id = str(flow_host_id or profile.host or target)
    skill_host_id = str(skill_slash_entry_host_id or target)
    usage_context = {
        "host": host_value if host_value is not None else profile.host,
        "host_protocol_mode": profile.host_protocol_mode,
        "official_project_surfaces": list(profile.official_project_surfaces),
        "official_user_surfaces": list(profile.official_user_surfaces),
        "managed_competition_project_surfaces": list(managed_competition_project_surfaces or []),
        "managed_competition_user_surfaces": list(managed_competition_user_surfaces or []),
    }
    skill_slash_command_map = {
        "codex": "/super-dev",
        "kimi-code": "/skill:super-dev",
    }
    skill_slash_note_map = {
        "codex": "表示 Codex App/Desktop `/` 列表里的已启用 Skill 入口，不代表项目支持自定义 slash 文件。",
        "kimi-code": "表示 Kimi Code 官方显式 Skill 入口，不代表项目支持自定义 `/super-dev` slash 文件。",
    }
    payload: dict[str, Any] = {
        "host": host_value if host_value is not None else profile.host,
        "category": profile.category,
        "certification_level": profile.certification_level,
        "certification_label": profile.certification_label,
        "certification_reason": profile.certification_reason,
        "certification_evidence": list(profile.certification_evidence),
        "host_protocol_mode": profile.host_protocol_mode,
        "host_protocol_summary": profile.host_protocol_summary,
        "official_project_surfaces": list(profile.official_project_surfaces),
        "official_user_surfaces": list(profile.official_user_surfaces),
        "optional_project_surfaces": list(profile.optional_project_surfaces),
        "optional_user_surfaces": list(profile.optional_user_surfaces),
        "managed_competition_project_surfaces": list(managed_competition_project_surfaces or []),
        "managed_competition_user_surfaces": list(managed_competition_user_surfaces or []),
        "observed_compatibility_surfaces": list(profile.observed_compatibility_surfaces),
        "usage_mode": profile.usage_mode,
        "primary_entry": profile.primary_entry,
        "trigger_command": profile.trigger_command,
        "final_trigger": final_trigger,
        "entry_variants": list(profile.entry_variants),
        "trigger_context": profile.trigger_context,
        "usage_location": profile.usage_location,
        "requires_restart_after_onboard": profile.requires_restart_after_onboard,
        "restart_required_label": "是" if profile.requires_restart_after_onboard else "否",
        "post_onboard_steps": list(profile.post_onboard_steps),
        "usage_notes": list(profile.usage_notes),
        "smoke_test_prompt": profile.smoke_test_prompt,
        "smoke_test_steps": list(profile.smoke_test_steps),
        "smoke_success_signal": profile.smoke_success_signal,
        "competition_smoke_test_prompt": profile.competition_smoke_test_prompt,
        "competition_smoke_test_steps": list(profile.competition_smoke_test_steps),
        "competition_smoke_success_signal": profile.competition_smoke_success_signal,
        "competition_smoke_suite": list(profile.competition_smoke_suite),
        "competition_acceptance_gates": list(profile.competition_acceptance_gates),
        "competition_evidence_template": dict(profile.competition_evidence_template),
        "standard_flow_first_prompt": build_host_standard_first_prompt(target),
        "competition_flow_first_prompt": build_host_competition_first_prompt(target),
        "host_start_playbook": build_host_start_playbook(target),
        "host_resume_guidance": build_host_resume_guidance(target),
        "post_onboard_self_check": build_host_post_onboard_self_check(target, usage_context),
        "official_workflow_checks": build_host_official_workflow_checks(target, usage_context),
        "official_pass_criteria": build_host_official_pass_criteria(target, usage_context),
        "host_repair_playbook": build_host_repair_guidance(target).strip(),
        "supports_skill_slash_entry": skill_host_id in skill_slash_command_map,
        "skill_slash_entry_command": skill_slash_command_map.get(skill_host_id, ""),
        "skill_slash_entry_note": (
            skill_slash_entry_note
            if skill_slash_entry_note and skill_host_id == "codex"
            else skill_slash_note_map.get(skill_host_id, "")
        ),
        "flow_contract": build_host_flow_contract(host_id),
        "flow_probe": build_host_flow_probe(host_id),
        "path_override": host_path_override_guide(target),
        "experience_profile": build_host_experience_profile(target),
        "precondition_status": profile.precondition_status,
        "precondition_label": profile.precondition_label,
        "precondition_guidance": list(profile.precondition_guidance),
        "precondition_signals": dict(profile.precondition_signals),
        "precondition_items": list(profile.precondition_items),
        "notes": profile.notes,
        "adaptation_contract": build_host_adaptation_contract(
            profile,
            host_id=host_id,
            supports_slash=bool(profile.slash_command_file),
        ),
    }
    if include_host_id:
        payload["host_id"] = profile.host
    if include_capability_labels:
        payload["capability_labels"] = dict(profile.capability_labels)
    if include_docs_fields:
        payload["official_docs_url"] = profile.official_docs_url
        payload["official_docs_references"] = list(profile.official_docs_references)
        payload["docs_check_status"] = profile.docs_check_status
        payload["docs_check_summary"] = profile.docs_check_summary
    return payload
