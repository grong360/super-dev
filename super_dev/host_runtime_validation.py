"""Shared host runtime validation state and payload builders."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .baseline_governance import inspect_baseline_governance
from .host_entry_decisions import build_host_repair_action
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from .host_registry import HostInstallMode, get_display_name, get_install_mode
from .host_runtime_probe import build_host_runtime_probe
from .host_workflow_context import build_host_workflow_context
from .review_state import (
    host_runtime_validation_file,
    load_host_runtime_validation,
    save_host_runtime_validation,
)
from .runtime_evidence import (
    HostRuntimeEvidence,
    IntegrationStatus,
    IntegrationStatusRecord,
    RuntimeStatus,
    RuntimeStatusRecord,
    competition_evidence_missing_sections,
    competition_evidence_ready,
    competition_evidence_shallow_sections,
    normalize_competition_evidence,
    serialize_host_runtime_evidence,
)
from .workflow_state import build_host_flow_probe, load_framework_playbook_summary


def load_host_runtime_validation_state(*, project_dir: Path) -> dict[str, Any]:
    payload = load_host_runtime_validation(project_dir) or {}
    if not isinstance(payload, dict):
        return {"hosts": {}, "updated_at": ""}
    hosts = payload.get("hosts", {})
    if not isinstance(hosts, dict):
        hosts = {}
    return {
        "hosts": hosts,
        "updated_at": str(payload.get("updated_at", "")).strip(),
    }


def host_runtime_status_label(status: str) -> str:
    mapping = {
        "pending": "待真人验收",
        "passed": "已真人通过",
        "failed": "真人验收失败",
    }
    return mapping.get(status, "待真人验收")


def _build_framework_coaching_summary(
    *,
    framework_focus: str,
    framework_validation_surfaces: list[str],
) -> str:
    focus = framework_focus.strip()
    if not focus:
        return ""
    surfaces = [str(item).strip() for item in framework_validation_surfaces if str(item).strip()]
    surfaces_text = "、".join(surfaces[:4]) if surfaces else "关键运行时与交付面"
    return (
        f"当前框架焦点（Framework Coaching Focus）聚焦 {focus}，重点盯住 {surfaces_text}。"
        " 这不是低层技术清单，而是在提前拦截首屏、路由切换、运行时稳定性和交付演示阶段的真实风险。"
    )


def _build_runtime_executive_summary(
    *,
    total_hosts: int,
    fully_ready_count: int,
    standard_flow_ready_count: int,
    competition_flow_ready_count: int,
    runtime_failed_count: int,
    runtime_pending_count: int,
    repo_probe_failed_count: int,
    blocking_count: int,
    workflow_context: dict[str, Any],
    baseline_governance: dict[str, Any],
    framework_coaching_summary: str,
) -> str:
    if total_hosts <= 0:
        return "当前还没有可验证宿主，无法证明 Super Dev 注入后已经具备稳定工作的基础条件。"

    status = str(workflow_context.get("workflow_status", "")).strip()
    gate = str(workflow_context.get("blocking_gate", "")).strip()
    baseline_gate = str(baseline_governance.get("entry_gate", "")).strip()

    if fully_ready_count == total_hosts:
        lead = (
            f"从宿主运行时视角看，当前 {fully_ready_count}/{total_hosts} 个宿主已经闭环，"
            "可以作为“装完即可进入主流程”的可信基础。"
        )
    else:
        lead = (
            f"从宿主运行时视角看，当前只有 {fully_ready_count}/{total_hosts} 个宿主完成完整闭环，"
            "还不能把当前状态当成“注入后即可稳定工作”。"
        )

    readiness_text = (
        f" 标准流可直接开工 {standard_flow_ready_count}/{total_hosts}，"
        f"SEEAI 比赛流可直接开工 {competition_flow_ready_count}/{total_hosts}。"
    )
    blocker_parts: list[str] = []
    if runtime_failed_count:
        blocker_parts.append(f"{runtime_failed_count} 个宿主真人 runtime 已失败")
    if runtime_pending_count:
        blocker_parts.append(f"{runtime_pending_count} 个宿主还停在真人 runtime 待验收")
    if repo_probe_failed_count:
        blocker_parts.append(f"{repo_probe_failed_count} 个宿主仓库级 probe 未通过")
    if blocking_count and not blocker_parts:
        blocker_parts.append(f"{blocking_count} 个宿主仍有阻塞项")
    blocker_text = (
        " 当前主要阻塞："
        + "；".join(blocker_parts[:3])
        + "。"
        if blocker_parts
        else ""
    )
    quality_bar_text = ""
    if fully_ready_count != total_hosts:
        quality_bar_text = (
            " 这类缺口通常不会先表现为代码报错，而是表现为团队接手不顺、宿主恢复不稳、现场演示卡壳。"
        )

    gate_text = ""
    if gate:
        gate_text = f" 当前 workflow gate={gate}。"
    elif baseline_gate:
        gate_text = f" 当前 baseline entry gate={baseline_gate}。"
    elif status:
        gate_text = f" 当前 workflow 状态={status}。"

    ui_note = (
        " 宿主矩阵通过只说明注入、入口和 runtime 链可用；真正的商业级 UI 质感仍要继续看截图级 UI gate、proof-pack 和 release-readiness。"
    )
    framework_text = f" {framework_coaching_summary}" if framework_coaching_summary else ""
    return (
        lead
        + readiness_text
        + blocker_text
        + quality_bar_text
        + gate_text
        + framework_text
        + ui_note
    )


def build_runtime_evidence_record(
    *,
    host_id: str,
    surface_ready: bool,
    runtime_entry: dict[str, Any],
) -> dict[str, Any]:
    install_mode = get_install_mode(host_id)
    if install_mode == HostInstallMode.MANUAL:
        integration_status = IntegrationStatus.MANUAL
    elif surface_ready:
        integration_status = IntegrationStatus.PROJECT_AND_GLOBAL_INSTALLED
    else:
        integration_status = IntegrationStatus.MISSING
    comment = str(runtime_entry.get("comment", "")).strip()
    competition_evidence = normalize_competition_evidence(
        runtime_entry.get("competition_evidence", {})
    )
    evidence = HostRuntimeEvidence(
        host_id=host_id,
        host_display_name=("Codex" if host_id == "codex-cli" else (get_display_name(host_id) or host_id)),
        summary="integration and runtime evidence are tracked separately",
        competition_evidence=competition_evidence,
        competition_evidence_ready=competition_evidence_ready(competition_evidence),
        competition_evidence_missing=competition_evidence_missing_sections(competition_evidence),
        integration_status=IntegrationStatusRecord(
            status=integration_status,
            evidence=("surface audit passed",) if surface_ready else ("surface gaps detected",),
            checked_at=str(runtime_entry.get("updated_at", "")).strip(),
            source="surface-audit",
            details="surface ready" if surface_ready else "surface needs repair",
        ),
        runtime_status=RuntimeStatusRecord(
            status=RuntimeStatus(str(runtime_entry.get("status", "")).strip() or "pending"),
            evidence=(comment,) if comment else (),
            checked_at=str(runtime_entry.get("updated_at", "")).strip(),
            source=str(runtime_entry.get("status_source", "")).strip() or "manual",
            details=comment,
        ),
    )
    return serialize_host_runtime_evidence(evidence)


def update_host_runtime_validation_state(
    *,
    project_dir: Path,
    host: str,
    status: str,
    comment: str,
    actor: str,
    competition_evidence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    payload = load_host_runtime_validation_state(project_dir=project_dir)
    hosts = dict(payload.get("hosts", {}))
    current = hosts.get(host, {})
    if not isinstance(current, dict):
        current = {}
    timestamp = datetime.now(timezone.utc).isoformat()
    existing_competition_evidence = normalize_competition_evidence(
        current.get("competition_evidence", {})
    )
    incoming_competition_evidence = normalize_competition_evidence(competition_evidence or {})
    merged_competition_evidence = {
        **existing_competition_evidence,
        **incoming_competition_evidence,
    }
    hosts[host] = {
        "status": status,
        "comment": comment.strip(),
        "actor": actor.strip() or "user",
        "updated_at": timestamp,
        "status_source": str(current.get("status_source", "")).strip() or "manual",
        "competition_evidence": merged_competition_evidence,
        "competition_evidence_ready": competition_evidence_ready(merged_competition_evidence),
        "competition_evidence_missing": list(
            competition_evidence_missing_sections(merged_competition_evidence)
        ),
    }
    file_path = save_host_runtime_validation(project_dir, {"hosts": hosts})
    updated = load_host_runtime_validation_state(project_dir=project_dir)
    return updated, file_path


def build_host_runtime_validation_payload(
    *,
    project_dir: Path,
    targets: list[str],
    detected_meta: dict[str, list[str]],
    report: dict[str, Any],
    usage_profiles: dict[str, dict[str, Any]],
    explain_detection_details_fn: Callable[[dict[str, list[str]]], dict[str, list[str]]],
    runtime_checklist_fn: Callable[[str, dict[str, Any], Path], list[str]],
    pass_criteria_fn: Callable[[str, dict[str, Any], Path], list[str]],
    resume_probe_prompt_fn: Callable[[str, dict[str, Any], Path], str],
    resume_checklist_fn: Callable[[str, Path], list[str]],
    entry_enricher_fn: Callable[[str, dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]
    | None = None,
) -> dict[str, Any]:
    workflow_context = build_host_workflow_context(project_dir)
    baseline_governance = inspect_baseline_governance(project_dir)
    runtime_state = load_host_runtime_validation_state(project_dir=project_dir)
    runtime_hosts = runtime_state.get("hosts", {})
    if not isinstance(runtime_hosts, dict):
        runtime_hosts = {}
    hosts = report.get("hosts", {})
    if not isinstance(hosts, dict):
        hosts = {}
    entries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_actions: list[str] = []
    framework_playbook = load_framework_playbook_summary(project_dir)
    for target in targets:
        host = hosts.get(target, {}) if isinstance(target, str) else {}
        usage = usage_profiles.get(target, {}) if isinstance(target, str) else {}
        runtime_entry = runtime_hosts.get(target, {}) if isinstance(target, str) else {}
        if not isinstance(host, dict):
            host = {}
        if not isinstance(usage, dict):
            usage = {}
        if not isinstance(runtime_entry, dict):
            runtime_entry = {}
        runtime_status = str(runtime_entry.get("status", "")).strip() or "pending"
        surface_ready = bool(host.get("ready", False))
        repo_probe = build_host_runtime_probe(
            project_dir,
            target=target,
            surface_ready=surface_ready,
        )
        repo_probe_status = str(repo_probe.get("status", "")).strip()
        competition_evidence = normalize_competition_evidence(
            runtime_entry.get("competition_evidence", {})
        )
        competition_template = usage.get("competition_evidence_template", {})
        competition_evidence_missing = list(
            competition_evidence_missing_sections(competition_evidence)
        )
        competition_evidence_shallow = list(
            competition_evidence_shallow_sections(competition_evidence, competition_template)
        )
        competition_evidence_ok = (
            competition_evidence_ready(competition_evidence)
            and not competition_evidence_shallow
        )
        competition_required = bool(competition_template)
        precondition_label = usage.get("precondition_label", "-")
        precondition_guidance = usage.get("precondition_guidance", [])
        precondition_items = usage.get("precondition_items", [])
        blocking_reason = ""
        recommended_action = ""
        blocker_type = ""
        if not surface_ready:
            blocking_reason = "宿主接入面仍存在 contract 缺口"
            recommended_action = build_host_repair_action(
                target=target,
                usage=usage,
                phase="surface",
                host_name=str(usage.get("host", "")).strip(),
            )
            blocker_type = "surface"
        elif runtime_status == "failed":
            blocking_reason = "宿主真人运行时验收失败"
            recommended_action = build_host_repair_action(
                target=target,
                usage=usage,
                phase="runtime",
                host_name=str(usage.get("host", "")).strip(),
            )
            blocker_type = "runtime"
        elif (
            competition_required and runtime_status == "passed" and not competition_evidence_ok
        ):
            if competition_evidence_shallow and not competition_evidence_missing:
                blocking_reason = "SEEAI 比赛验收证据内容过浅：" + "、".join(
                    competition_evidence_shallow
                )
            else:
                blocking_reason = "SEEAI 比赛验收证据不完整"
            recommended_action = (
                "先补齐 SEEAI 比赛验收证据：作品类型 / wow 点 / runtime checkpoint / "
                "fallback decision / demo path；补齐后再由维护面记录通过结论。"
            )
            blocker_type = "competition_evidence"
        elif runtime_status == "passed" and repo_probe_status == "failed":
            blocking_reason = str(repo_probe.get("summary", "")).strip() or "宿主仓库级 probe 未通过"
            recommended_action = str(repo_probe.get("recommended_command", "")).strip()
            if not recommended_action:
                probe_actions = repo_probe.get("next_actions", [])
                if isinstance(probe_actions, list) and probe_actions:
                    recommended_action = str(probe_actions[0]).strip()
            blocker_type = "repo_probe"
        elif runtime_status != "passed":
            blocking_reason = "宿主尚未完成真人运行时验收"
            recommended_action = build_host_repair_action(
                target=target,
                usage=usage,
                phase="validation",
                host_name=str(usage.get("host", "")).strip(),
            )
            blocker_type = "validation"

        repo_probe_blocking = runtime_status == "passed" and repo_probe_status == "failed"
        if (
            not surface_ready
            or runtime_status != "passed"
            or repo_probe_blocking
            or (
                competition_required
                and runtime_status == "passed"
                and not competition_evidence_ok
            )
        ):
            blockers.append(
                {
                    "host": target,
                    "type": blocker_type or "runtime",
                    "summary": blocking_reason,
                    "next_action": recommended_action,
                }
            )
            if recommended_action and recommended_action not in next_actions:
                next_actions.append(recommended_action)

        if isinstance(precondition_guidance, list):
            for item in precondition_guidance[:2]:
                if (
                    isinstance(item, str)
                    and item.strip()
                    and item not in next_actions
                    and runtime_status != "passed"
                ):
                    next_actions.append(item.strip())

        extra_entry = {}
        if entry_enricher_fn is not None:
            extra_entry = entry_enricher_fn(target, host, usage, runtime_entry)
            if not isinstance(extra_entry, dict):
                extra_entry = {}

        entries.append(
            {
                "host": target,
                "surface_ready": surface_ready,
                "injection_closure": (
                    dict(host.get("injection_closure", {}))
                    if isinstance(host.get("injection_closure", {}), dict)
                    else {}
                ),
                "integration_status": (
                    "project_and_global_installed" if surface_ready else "repair_needed"
                ),
                "ready_for_standard_flow": bool(
                    host.get("injection_closure", {}).get("standard_flow_ready", False)
                ),
                "ready_for_competition_flow": bool(
                    host.get("injection_closure", {}).get("competition_flow_ready", False)
                ),
                "ready_for_delivery": (
                    surface_ready
                    and runtime_status == "passed"
                    and not repo_probe_blocking
                    and (not competition_required or competition_evidence_ok)
                ),
                "blocking_reason": blocking_reason,
                "recommended_action": recommended_action,
                "runtime_status": runtime_status,
                "runtime_status_label": host_runtime_status_label(runtime_status),
                "manual_runtime_status": runtime_status,
                "manual_runtime_status_label": host_runtime_status_label(runtime_status),
                "manual_runtime_comment": str(runtime_entry.get("comment", "")).strip(),
                "manual_runtime_actor": str(runtime_entry.get("actor", "")).strip(),
                "manual_runtime_updated_at": str(runtime_entry.get("updated_at", "")).strip(),
                "repo_probe": repo_probe,
                "competition_evidence": competition_evidence,
                "competition_evidence_ready": competition_evidence_ok,
                "competition_evidence_missing": competition_evidence_missing,
                "competition_evidence_shallow": competition_evidence_shallow,
                "competition_evidence_required": competition_required,
                "runtime_evidence": build_runtime_evidence_record(
                    host_id=target,
                    surface_ready=surface_ready,
                    runtime_entry=runtime_entry,
                ),
                "final_trigger": usage.get("final_trigger", "-"),
                "standard_flow_first_prompt": build_host_standard_first_prompt(target),
                "competition_flow_first_prompt": build_host_competition_first_prompt(target),
                "usage_mode": usage.get("usage_mode", "-"),
                "primary_entry": usage.get("primary_entry", "-"),
                "host_protocol_mode": usage.get("host_protocol_mode", "-"),
                "host_protocol_summary": usage.get("host_protocol_summary", "-"),
                "certification_label": usage.get("certification_label", "-"),
                "experience_profile": usage.get("experience_profile", {}),
                "path_override": usage.get("path_override", {}),
                "adaptation_contract": usage.get("adaptation_contract", {}),
                "supports_skill_slash_entry": bool(
                    usage.get("supports_skill_slash_entry", False)
                ),
                "skill_slash_entry_command": usage.get("skill_slash_entry_command", ""),
                "precondition_label": precondition_label,
                "precondition_guidance": precondition_guidance,
                "precondition_items": (
                    precondition_items if isinstance(precondition_items, list) else []
                ),
                "smoke_test_prompt": usage.get("smoke_test_prompt", ""),
                "smoke_success_signal": usage.get("smoke_success_signal", ""),
                "host_start_playbook": build_host_start_playbook(target),
                "official_workflow_checks": build_host_official_workflow_checks(target, usage),
                "post_onboard_self_check": build_host_post_onboard_self_check(target, usage),
                "host_repair_playbook": build_host_repair_guidance(target).strip(),
                "runtime_checklist": runtime_checklist_fn(target, usage, project_dir),
                "pass_criteria": pass_criteria_fn(target, usage, project_dir),
                "flow_probe": build_host_flow_probe(target),
                "resume_probe_prompt": resume_probe_prompt_fn(target, usage, project_dir),
                "resume_checklist": resume_checklist_fn(target, project_dir),
                "framework_playbook": framework_playbook,
                **extra_entry,
            }
        )

    total_hosts = len(entries)
    surface_ready_count = sum(1 for item in entries if bool(item.get("surface_ready", False)))
    runtime_passed_count = sum(
        1 for item in entries if item.get("manual_runtime_status") == "passed"
    )
    runtime_failed_count = sum(
        1 for item in entries if item.get("manual_runtime_status") == "failed"
    )
    runtime_pending_count = sum(
        1 for item in entries if item.get("manual_runtime_status") == "pending"
    )
    repo_probe_passed_count = sum(
        1 for item in entries if str(item.get("repo_probe", {}).get("status", "")) == "passed"
    )
    repo_probe_failed_count = sum(
        1 for item in entries if str(item.get("repo_probe", {}).get("status", "")) == "failed"
    )
    repo_probe_pending_count = sum(
        1 for item in entries if str(item.get("repo_probe", {}).get("status", "")) == "pending"
    )
    fully_ready_count = sum(1 for item in entries if bool(item.get("ready_for_delivery", False)))
    project_default_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("project_default_ready", False))
    )
    explicit_user_surface_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("explicit_user_surfaces_ready", False))
    )
    user_surface_opt_in_available_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("user_surface_opt_in_available", False))
    )
    competition_project_surface_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("competition_project_surfaces_ready", False))
    )
    competition_user_surface_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("competition_user_surfaces_ready", False))
    )
    standard_flow_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("standard_flow_ready", False))
    )
    competition_flow_ready_count = sum(
        1
        for item in entries
        if bool(item.get("injection_closure", {}).get("competition_flow_ready", False))
    )
    framework_focus = str(framework_playbook.get("framework", "")).strip()
    framework_validation_surfaces = (
        list(framework_playbook.get("validation_surfaces", []))
        if isinstance(framework_playbook.get("validation_surfaces", []), list)
        else []
    )
    framework_coaching_summary = _build_framework_coaching_summary(
        framework_focus=framework_focus,
        framework_validation_surfaces=framework_validation_surfaces,
    )
    executive_runtime_summary = _build_runtime_executive_summary(
        total_hosts=total_hosts,
        fully_ready_count=fully_ready_count,
        standard_flow_ready_count=standard_flow_ready_count,
        competition_flow_ready_count=competition_flow_ready_count,
        runtime_failed_count=runtime_failed_count,
        runtime_pending_count=runtime_pending_count,
        repo_probe_failed_count=repo_probe_failed_count,
        blocking_count=len(blockers),
        workflow_context=workflow_context,
        baseline_governance=baseline_governance,
        framework_coaching_summary=framework_coaching_summary,
    )

    return {
        "project_dir": str(project_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_context": workflow_context,
        "baseline_governance": baseline_governance,
        "framework_playbook": framework_playbook,
        "runtime_state_file": str(host_runtime_validation_file(project_dir)),
        "runtime_state_updated_at": runtime_state.get("updated_at", ""),
        "detected_hosts": list(detected_meta.keys()),
        "detection_details": detected_meta,
        "detection_details_pretty": explain_detection_details_fn(detected_meta),
        "selected_targets": targets,
        "summary": {
            "overall_status": (
                "ready" if total_hosts > 0 and fully_ready_count == total_hosts else "attention"
            ),
            "total_hosts": total_hosts,
            "surface_ready_count": surface_ready_count,
            "runtime_passed_count": runtime_passed_count,
            "runtime_failed_count": runtime_failed_count,
            "runtime_pending_count": runtime_pending_count,
            "repo_probe_passed_count": repo_probe_passed_count,
            "repo_probe_failed_count": repo_probe_failed_count,
            "repo_probe_pending_count": repo_probe_pending_count,
            "project_default_ready_count": project_default_ready_count,
            "explicit_user_surface_ready_count": explicit_user_surface_ready_count,
            "user_surface_opt_in_available_count": user_surface_opt_in_available_count,
            "competition_project_surface_ready_count": competition_project_surface_ready_count,
            "competition_user_surface_ready_count": competition_user_surface_ready_count,
            "standard_flow_ready_count": standard_flow_ready_count,
            "competition_flow_ready_count": competition_flow_ready_count,
            "framework_focus": framework_focus,
            "framework_validation_surfaces": framework_validation_surfaces,
            "framework_coaching_summary": framework_coaching_summary,
            "executive_runtime_summary": executive_runtime_summary,
            "fully_ready_count": fully_ready_count,
            "blocking_count": len(blockers),
            "next_actions": next_actions,
        },
        "blockers": blockers,
        "hosts": entries,
    }
