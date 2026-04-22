"""Shared host entry decision helpers for CLI and Web surfaces."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .host_diagnostics import build_host_injection_closure
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_experience_profile,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from .skills.manager import SkillManager


def _compact_profile_list(profile: dict[str, Any], key: str, *, limit: int = 3) -> list[str]:
    values = profile.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _host_entry_example(usage: dict[str, Any]) -> str:
    experience = (
        dict(usage.get("experience_profile", {}))
        if isinstance(usage.get("experience_profile", {}), dict)
        else {}
    )
    preferred_entries = _compact_profile_list(experience, "preferred_entries", limit=1)
    if preferred_entries:
        return preferred_entries[0]
    trigger = str(usage.get("trigger_command", "")).strip()
    if trigger:
        return trigger.replace("<需求描述>", "你的需求")
    return str(usage.get("primary_entry", "")).strip() or "super-dev: 你的需求"


def _host_resume_example(usage: dict[str, Any]) -> str:
    experience = (
        dict(usage.get("experience_profile", {}))
        if isinstance(usage.get("experience_profile", {}), dict)
        else {}
    )
    native_resume = _compact_profile_list(experience, "native_resume", limit=1)
    if native_resume:
        return native_resume[0]
    preferred_entries = _compact_profile_list(experience, "preferred_entries", limit=1)
    if preferred_entries:
        return preferred_entries[0]
    trigger = str(usage.get("trigger_command", "")).strip()
    if trigger:
        return trigger.replace("<需求描述>", "继续当前流程")
    return "super-dev: 继续当前流程"


def build_host_start_guidance(
    *,
    target: str,
    usage: dict[str, Any],
    include_resume_hint: bool = False,
) -> str:
    host_name = str(usage.get("host", "")).strip() or target
    entry = _host_entry_example(usage)
    if not include_resume_hint:
        return f"{host_name}: 优先从 {entry} 开始"
    resume = _host_resume_example(usage)
    return f"{host_name}: 优先从 {entry} 开始；恢复优先 {resume}"


def build_host_action_examples(*, target: str, usage: dict[str, Any]) -> list[str]:
    entry = _host_entry_example(usage)
    host_name = str(usage.get("host", "")).strip() or target
    examples = [
        entry.replace("你的需求", "做一个新项目"),
        entry.replace("你的需求", "在当前项目里新增一个商业模块"),
        entry.replace("你的需求", "修复当前项目里的关键问题"),
    ]
    deduped: list[str] = []
    for item in examples:
        text = str(item).strip()
        if not text or text in deduped:
            continue
        deduped.append(text)
    if deduped:
        return deduped
    return [
        f"{host_name}: 开始这个项目",
        f"{host_name}: 在当前项目里新增功能",
        f"{host_name}: 修复当前项目里的问题",
    ]


def _build_candidate_injection_closure(*, integration_manager: Any, target: str) -> dict[str, Any]:
    skill_name = SkillManager.default_skill_name(target)
    surface_sets = integration_manager.readiness_surface_sets(
        target=target,
        skill_name=skill_name,
    )
    managed_competition_project_paths = [
        integration_manager.project_dir / relative
        for relative in integration_manager.managed_competition_project_surfaces(target)
    ]
    managed_competition_user_paths = [
        integration_manager._resolve_surface_declaration(target=target, surface=relative)
        for relative in integration_manager.managed_competition_user_surfaces(target)
    ]
    return build_host_injection_closure(
        host_ready=True,
        surface_sets=surface_sets,
        managed_competition_project_paths=managed_competition_project_paths,
        managed_competition_user_paths=managed_competition_user_paths,
    )


def build_host_repair_action(
    *,
    target: str,
    usage: dict[str, Any],
    phase: str,
    host_name: str = "",
) -> str:
    host_label = host_name or str(usage.get("host", "")).strip() or target
    entry = _host_entry_example(usage)
    resume = _host_resume_example(usage)
    repair_guidance = build_host_repair_guidance(target)
    if phase == "surface":
        action = (
            f"先重新运行 super-dev 修复 {host_label} 接入面；必要时再用 super-dev update 同步版本。"
            f"完成后重开宿主，并先用 {entry} 回到当前流程。"
        )
        return f"{action}{repair_guidance}" if repair_guidance else action
    if phase == "runtime":
        action = (
            f"先在 {host_label} 当前会话重新完成真人验收；"
            f"通过后优先用 {resume} 继续当前流程。"
        )
        return f"{action}{repair_guidance}" if repair_guidance else action
    if phase == "validation":
        action = (
            f"先在 {host_label} 当前会话完成真人验收，确认 research 和三文档真实落盘；"
            f"然后用 {resume} 继续当前流程。"
        )
        return f"{action}{repair_guidance}" if repair_guidance else action
    action = f"先在 {host_label} 里处理当前问题，然后用 {resume} 继续当前流程。"
    return f"{action}{repair_guidance}" if repair_guidance else action


def host_selection_sort_key(*, integration_manager: Any, target: str) -> tuple[int, int, int, str]:
    profile = integration_manager.get_adapter_profile(target)
    certification_rank = (
        0
        if profile.certification_level == "certified"
        else (1 if profile.certification_level == "compatible" else 2)
    )
    category_rank = {"cli": 0, "assistant": 1, "ide": 2}.get(str(profile.category), 3)
    return (
        certification_rank,
        0 if integration_manager.supports_slash(target) else 1,
        category_rank,
        target,
    )


def rank_host_targets(*, integration_manager: Any, targets: list[str]) -> list[str]:
    return sorted(
        targets,
        key=lambda target: host_selection_sort_key(
            integration_manager=integration_manager,
            target=target,
        ),
    )


def host_selection_reason(*, integration_manager: Any, target: str) -> str:
    profile = integration_manager.get_adapter_profile(target)
    experience = build_host_experience_profile(target)
    flagship = isinstance(experience, dict) and str(experience.get("tier", "")).strip() == "flagship"
    best_for = str(experience.get("best_for", "")).strip() if isinstance(experience, dict) else ""
    protocol_mode = str(getattr(profile, "host_protocol_mode", "") or "").strip()
    fit_suffix = f" 更适合做“{best_for}”这类工作。" if best_for else ""
    protocol_suffix = f" 当前走 {protocol_mode} 协议面。" if protocol_mode else ""
    if profile.certification_level == "certified" and integration_manager.supports_slash(target):
        base = (
            "它当前是已检测宿主里认证等级最高、触发入口最直接的旗舰宿主。"
            if flagship
            else "它当前是已检测宿主里认证等级最高、触发入口最直接的一项。"
        )
        return base + fit_suffix + protocol_suffix
    if profile.certification_level == "certified":
        base = (
            "它当前是已检测宿主里认证等级最高的旗舰宿主。"
            if flagship
            else "它当前是已检测宿主里认证等级最高的一项。"
        )
        return base + fit_suffix + protocol_suffix
    if integration_manager.supports_slash(target):
        base = (
            "它当前触发入口最直接，且属于旗舰宿主，适合作为默认宿主。"
            if flagship
            else "它当前触发入口最直接，适合作为默认宿主。"
        )
        return base + fit_suffix + protocol_suffix
    base = (
        "它当前在已检测宿主里综合优先级最高，且体验成熟度更适合做默认宿主。"
        if flagship
        else "它当前在已检测宿主里综合优先级最高。"
    )
    return base + fit_suffix + protocol_suffix


def build_no_host_decision_card(
    *,
    workflow_mode_label: str,
    action_examples: list[str],
    first_action: str,
    secondary_actions: list[str],
    path_override_hint: str,
    path_override_examples: list[dict[str, Any]],
    lines: list[str],
    user_action_shortcuts: list[str] | None = None,
    recommended_hosts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scenario": "no-host-detected",
        "workflow_mode": "start",
        "workflow_mode_label": workflow_mode_label,
        "workflow_context": {},
        "action_title": "先完成宿主安装与接入",
        "action_examples": action_examples,
        "title": "未检测到可用宿主",
        "summary": "当前机器上没有命中受支持宿主，或宿主不在默认路径与当前 PATH 中。",
        "recommended_reason": "先保证机器上至少有一个正式支持的宿主可用，再进入接入流程。",
        "first_action": first_action,
        "secondary_actions": secondary_actions,
        "path_override_hint": path_override_hint,
        "path_override_examples": path_override_examples,
        "next_actions": [first_action, *secondary_actions],
        "lines": lines,
    }
    if user_action_shortcuts is not None:
        payload["user_action_shortcuts"] = user_action_shortcuts
    if recommended_hosts is not None:
        payload["recommended_hosts"] = recommended_hosts
    return payload


def build_detected_host_decision_card(
    *,
    project_dir: Path,
    integration_manager: Any,
    detected_targets: list[str],
    detected_meta: dict[str, list[str]],
    preferred_targets: list[str] | None,
    usage_profile_fn: Callable[[str], dict[str, Any]],
    session_resume_card_fn: Callable[[Path, str], dict[str, Any]],
    explain_detection_details_fn: Callable[[dict[str, list[str]]], dict[str, list[str]]],
    workflow_mode_label_fn: Callable[[str], str],
    candidate_trigger_fn: Callable[[str, dict[str, Any], Any], str],
    first_action_fn: Callable[[str, dict[str, Any], Any, dict[str, Any]], str],
    first_suggestion_text_fn: Callable[[str, list[dict[str, Any]]], str],
    default_action_examples: list[str],
    user_action_shortcuts_fn: Callable[[str, list[str]], list[str]] | None = None,
    no_host_card_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    candidate_targets = list(dict.fromkeys([*(preferred_targets or []), *detected_targets]))
    if not candidate_targets:
        return no_host_card_fn()

    candidate_display_limit = 3
    ranked_targets = rank_host_targets(
        integration_manager=integration_manager,
        targets=candidate_targets,
    )
    preferred_set = {target for target in (preferred_targets or []) if target}
    if preferred_set:
        ranked_targets = sorted(
            ranked_targets,
            key=lambda target: (0 if target in preferred_set else 1, ranked_targets.index(target)),
        )

    selected_host = ranked_targets[0]
    selected_usage = usage_profile_fn(selected_host)
    selected_profile = integration_manager.get_adapter_profile(selected_host)
    session_resume_card = session_resume_card_fn(project_dir, selected_host)
    workflow_context = (
        dict(session_resume_card.get("workflow_context", {}))
        if isinstance(session_resume_card.get("workflow_context", {}), dict)
        else {}
    )
    recommended_reason = host_selection_reason(
        integration_manager=integration_manager,
        target=selected_host,
    )
    workflow_mode = "continue" if session_resume_card.get("enabled") else "start"
    action_title = (
        str(session_resume_card.get("action_title", "")).strip()
        if session_resume_card.get("enabled")
        else f"在 {selected_usage['host']} 里启动 Super Dev"
    )
    action_examples = (
        list(session_resume_card.get("action_examples") or [])
        if session_resume_card.get("enabled")
        else build_host_action_examples(target=selected_host, usage=selected_usage)
    )
    baseline_summary = str(session_resume_card.get("baseline_summary", "")).strip()
    baseline_audit_path = str(session_resume_card.get("baseline_audit_path", "")).strip()
    baseline_reuse_surfaces = [
        str(item).strip()
        for item in (session_resume_card.get("baseline_reuse_surfaces") or [])
        if str(item).strip()
    ]
    first_action = first_action_fn(
        selected_host,
        selected_usage,
        selected_profile,
        session_resume_card,
    )

    candidates: list[dict[str, Any]] = []
    for target in ranked_targets:
        profile = integration_manager.get_adapter_profile(target)
        usage = usage_profile_fn(target)
        candidate_closure = _build_candidate_injection_closure(
            integration_manager=integration_manager,
            target=target,
        )
        candidate_standard_label = str(candidate_closure.get("standard_flow_label", "")).strip()
        candidate_competition_label = str(
            candidate_closure.get("competition_flow_label", "")
        ).strip()
        candidate_first_action = (
            build_host_start_guidance(
                target=target,
                usage=usage,
                include_resume_hint=False,
            )
            if bool(candidate_closure.get("standard_flow_ready", False))
            else (
                f"先运行 super-dev 为 {usage['host']} 完成项目级接入，再回宿主从 "
                f"{_host_entry_example(usage)} 开始。"
            )
        )
        candidates.append(
            {
                "id": target,
                "name": usage["host"],
                "certification_label": profile.certification_label,
                "certification_level": profile.certification_level,
                "usage_mode": usage.get("usage_mode", ""),
                "primary_entry": usage.get("primary_entry", ""),
                "precondition_label": usage.get("precondition_label", ""),
                "experience_profile": dict(usage.get("experience_profile", {}))
                if isinstance(usage.get("experience_profile", {}), dict)
                else {},
                "injection_closure": candidate_closure,
                "ready_for_standard_flow": bool(candidate_closure.get("standard_flow_ready", False)),
                "ready_for_competition_flow": bool(
                    candidate_closure.get("competition_flow_ready", False)
                ),
                "standard_flow_label": candidate_standard_label,
                "competition_flow_label": candidate_competition_label,
                "readiness_summary": " / ".join(
                    item for item in [candidate_standard_label, candidate_competition_label] if item
                ),
                "first_action": candidate_first_action,
                "post_onboard_self_check": build_host_post_onboard_self_check(target, usage),
                "start_playbook": build_host_start_playbook(target),
                "resume_guidance": build_host_resume_guidance(target),
                "official_workflow_checks": build_host_official_workflow_checks(target, usage),
                "repair_playbook": build_host_repair_guidance(target).strip(),
                "standard_flow_first_prompt": build_host_standard_first_prompt(target),
                "competition_flow_first_prompt": build_host_competition_first_prompt(target),
                "adaptation_contract": dict(usage.get("adaptation_contract", {}))
                if isinstance(usage.get("adaptation_contract", {}), dict)
                else {},
                "official_alignment": dict(
                    usage.get("adaptation_contract", {}).get("official_alignment", {})
                )
                if isinstance(usage.get("adaptation_contract", {}), dict)
                and isinstance(
                    usage.get("adaptation_contract", {}).get("official_alignment", {}),
                    dict,
                )
                else {},
                "recommended": target == selected_host,
                "recommended_reason": host_selection_reason(
                    integration_manager=integration_manager,
                    target=target,
                ),
                "reasons": explain_detection_details_fn({target: detected_meta.get(target, [])}).get(
                    target, []
                ),
                "trigger": candidate_trigger_fn(target, usage, profile),
                "path_override": usage["path_override"],
            }
        )

    display_candidates = candidates[:candidate_display_limit]
    remaining_candidate_count = max(0, len(candidates) - len(display_candidates))
    selection_source = "explicit" if preferred_set else "detected"
    lines = [
        f"动作类型: {workflow_mode_label_fn(workflow_mode)}",
        f"当前动作: {action_title}",
        f"先做这一步: {first_action}",
        f"默认推荐先用 {selected_usage['host']}，{recommended_reason}",
        f"当前建议入口: {selected_usage['primary_entry']}",
        "公开主路径: 普通开发留在宿主里；已有项目先 baseline，中断后默认先 resume。",
    ]
    experience_profile = (
        dict(selected_usage.get("experience_profile", {}))
        if isinstance(selected_usage.get("experience_profile", {}), dict)
        else {}
    )
    if experience_profile:
        tier_label = str(experience_profile.get("label", "")).strip()
        best_for = str(experience_profile.get("best_for", "")).strip()
        resume_style = str(experience_profile.get("resume_style", "")).strip()
        if tier_label or best_for:
            lines.append(
                "宿主体验画像: "
                + " / ".join(
                    item
                    for item in [
                        tier_label,
                        best_for,
                        f"resume={resume_style}" if resume_style else "",
                    ]
                    if item
                )
            )
        strengths = _compact_profile_list(experience_profile, "strengths")
        if strengths:
            lines.append(f"宿主强项: {' / '.join(strengths)}")
        preferred_entries = _compact_profile_list(experience_profile, "preferred_entries", limit=2)
        if preferred_entries:
            lines.append(f"推荐入口变体: {' / '.join(preferred_entries)}")
        native_resume = _compact_profile_list(experience_profile, "native_resume", limit=2)
        if native_resume:
            lines.append(f"推荐恢复方式: {' / '.join(native_resume)}")
        start_playbook = build_host_start_playbook(selected_host)
        if start_playbook:
            lines.extend(start_playbook[:2])
        lines.append(f"标准流第一句: {build_host_standard_first_prompt(selected_host)}")
        lines.append(f"比赛流第一句: {build_host_competition_first_prompt(selected_host)}")
        post_onboard_self_check = build_host_post_onboard_self_check(selected_host, selected_usage)
        if post_onboard_self_check:
            lines.append(f"接入后先验: {' / '.join(post_onboard_self_check[:2])}")
        official_checks = build_host_official_workflow_checks(selected_host, selected_usage)
        if official_checks:
            lines.append(f"官方补充检查: {official_checks[-1]}")
        selected_adaptation = (
            dict(selected_usage.get("adaptation_contract", {}))
            if isinstance(selected_usage.get("adaptation_contract", {}), dict)
            else {}
        )
        official_alignment = (
            dict(selected_adaptation.get("official_alignment", {}))
            if isinstance(selected_adaptation.get("official_alignment", {}), dict)
            else {}
        )
        if official_alignment:
            alignment_label = str(official_alignment.get("label", "")).strip()
            alignment_summary = str(official_alignment.get("summary", "")).strip()
            if alignment_label or alignment_summary:
                lines.append(
                    "官方对齐: "
                    + " / ".join(item for item in [alignment_label, alignment_summary] if item)
                )
    selected_injection_closure = _build_candidate_injection_closure(
        integration_manager=integration_manager,
        target=selected_host,
    )
    if selected_injection_closure:
        lines.append(
            "当前准备度: "
            + " / ".join(
                item
                for item in [
                    str(selected_injection_closure.get("standard_flow_label", "")).strip(),
                    str(selected_injection_closure.get("competition_flow_label", "")).strip(),
                ]
                if item
            )
        )
    if selection_source == "explicit":
        lines.insert(3, f"当前模式: 仅围绕 {selected_usage['host']} 给出建议。")
    if action_examples:
        lines.append(f"自然语言示例: {', '.join(str(item) for item in action_examples[:3])}")
    candidate_summary = "、".join(
        f"{item['name']} [{item['certification_label']}]" for item in display_candidates
    )
    if candidate_summary:
        lines.append(f"优先候选: {candidate_summary}")
    if display_candidates:
        lines.append(
            "候选准备度: "
            + "；".join(
                f"{item['name']}({item['readiness_summary']})"
                for item in display_candidates
                if str(item.get("readiness_summary", "")).strip()
            )
        )
    if remaining_candidate_count:
        lines.append(f"另外还有 {remaining_candidate_count} 个候选已折叠，默认不建议先看。")
    if baseline_summary:
        lines.append(f"Baseline 已识别: {baseline_summary}")
    if baseline_reuse_surfaces:
        lines.append(f"复用面: {' / '.join(baseline_reuse_surfaces[:3])}")
    if session_resume_card.get("enabled"):
        lines.append(f"继续当前流程第一句: {session_resume_card.get('host_first_sentence')}")
    elif candidates:
        lines.append(f"第一句建议: {first_suggestion_text_fn(selected_host, candidates)}")

    payload: dict[str, Any] = {
        "scenario": "multi-host-detected" if len(candidate_targets) > 1 else "single-host-detected",
        "selection_source": selection_source,
        "workflow_mode": workflow_mode,
        "workflow_mode_label": workflow_mode_label_fn(workflow_mode),
        "workflow_context": workflow_context,
        "action_title": action_title,
        "action_examples": action_examples,
        "title": "已检测到宿主",
        "summary": (
            f"当前已按你指定的宿主给出默认建议，共纳入 {len(candidate_targets)} 个候选。"
            if selection_source == "explicit"
            else f"当前检测到 {len(detected_targets)} 个宿主，已按优先级给出默认推荐。"
        ),
        "recommended_reason": recommended_reason,
        "first_action": first_action,
        "secondary_actions": [
            *(
                build_host_start_playbook(selected_host)[:1]
                if not session_resume_card.get("enabled")
                else []
            ),
            "如果当前是重开宿主后的第一轮输入，先不要普通聊天起手，直接用建议入口。",
            *(
                build_host_start_playbook(selected_host)[1:2]
                if not session_resume_card.get("enabled")
                else []
            ),
            "如果命令/技能还没刷新，先关闭旧宿主会话再开新会话。",
            "如果这是已有项目的新增、派生或修复，先让宿主完成 baseline，不要先回终端手工跳阶段。",
        ],
        "selected_host": selected_host,
        "selected_host_name": selected_usage["host"],
        "selected_path_override": selected_usage["path_override"],
        "baseline_summary": baseline_summary,
        "baseline_audit_path": baseline_audit_path,
        "baseline_reuse_surfaces": baseline_reuse_surfaces,
        "selected_host_injection_closure": selected_injection_closure,
        "selected_host_ready_for_standard_flow": bool(
            selected_injection_closure.get("standard_flow_ready", False)
        ),
        "selected_host_ready_for_competition_flow": bool(
            selected_injection_closure.get("competition_flow_ready", False)
        ),
        "selected_host_standard_flow_label": str(
            selected_injection_closure.get("standard_flow_label", "")
        ).strip(),
        "selected_host_competition_flow_label": str(
            selected_injection_closure.get("competition_flow_label", "")
        ).strip(),
        "selected_host_start_playbook": build_host_start_playbook(selected_host),
        "selected_host_resume_guidance": build_host_resume_guidance(selected_host),
        "selected_host_standard_flow_first_prompt": build_host_standard_first_prompt(selected_host),
        "selected_host_competition_flow_first_prompt": build_host_competition_first_prompt(
            selected_host
        ),
        "selected_host_post_onboard_self_check": build_host_post_onboard_self_check(
            selected_host, selected_usage
        ),
        "selected_host_official_workflow_checks": build_host_official_workflow_checks(
            selected_host, selected_usage
        ),
        "selected_host_official_alignment": (
            dict(selected_usage.get("adaptation_contract", {}).get("official_alignment", {}))
            if isinstance(selected_usage.get("adaptation_contract", {}), dict)
            and isinstance(
                selected_usage.get("adaptation_contract", {}).get("official_alignment", {}),
                dict,
            )
            else {}
        ),
        "selected_host_repair_playbook": build_host_repair_guidance(selected_host).strip(),
        "candidate_count": len(candidates),
        "remaining_candidate_count": remaining_candidate_count,
        "candidates": display_candidates,
        "session_resume_card": session_resume_card,
        "lines": lines,
    }
    if user_action_shortcuts_fn is not None:
        payload["user_action_shortcuts"] = user_action_shortcuts_fn(workflow_mode, action_examples)
    return payload


def build_primary_repair_action(
    *,
    report: dict[str, Any],
    targets: list[str],
    host_label_fn: Callable[[str], str],
    usage_profile_fn: Callable[[str], dict[str, Any]] | None = None,
    decision_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hosts = report.get("hosts", {})
    if isinstance(decision_card, dict) and decision_card.get("scenario") == "no-host-detected":
        first_action = str(decision_card.get("first_action", "")).strip()
        if first_action:
            decision_secondary_actions = decision_card.get("secondary_actions", [])
            return {
                "host": "当前机器",
                "reason": str(decision_card.get("summary", "")).strip(),
                "command": first_action,
                "secondary_actions": (
                    decision_secondary_actions
                    if isinstance(decision_secondary_actions, list)
                    else []
                ),
            }
    if not isinstance(hosts, dict):
        return {"host": "", "reason": "", "command": "", "secondary_actions": []}
    for target in targets:
        host = hosts.get(target, {})
        if not isinstance(host, dict) or bool(host.get("ready", False)):
            continue
        diagnosis = host.get("diagnosis", {})
        if not isinstance(diagnosis, dict):
            continue
        command = str(diagnosis.get("suggested_command", "")).strip()
        usage = (
            usage_profile_fn(target)
            if usage_profile_fn is not None
            else {"host": host_label_fn(target), "trigger_command": ""}
        )
        if not isinstance(usage, dict):
            usage = {"host": host_label_fn(target), "trigger_command": ""}
        host_name = host_label_fn(target)
        command = build_host_repair_action(
            target=target,
            usage=usage,
            phase="surface",
            host_name=host_name,
        ) or command
        if not command:
            continue
        reason = str(diagnosis.get("blocker_summary", "")).strip()
        suggestions = host.get("suggestions", [])
        secondary_actions: list[str] = []
        if isinstance(suggestions, list):
            for item in suggestions:
                text = str(item).strip()
                if not text or text == command or text in secondary_actions:
                    continue
                secondary_actions.append(text)
                if len(secondary_actions) >= 2:
                    break
        return {
            "host": host_name,
            "reason": reason,
            "command": command,
            "secondary_actions": secondary_actions,
        }
    return {"host": "", "reason": "", "command": "", "secondary_actions": []}
