"""Shared session resume card builders for CLI and Web surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline_governance import inspect_baseline_governance
from .harness_registry import derive_operational_focus, summarize_operational_harnesses
from .hooks.manager import HookManager
from .review_state import (
    describe_workflow_event,
    load_recent_operational_timeline,
    load_recent_workflow_events,
    load_recent_workflow_snapshots,
    workflow_event_log_file,
    workflow_state_file,
)
from .workflow_state import build_host_entry_prompts, load_framework_playbook_summary

GENERIC_CONTINUE_RULE = (
    "用户说“改一下 / 补充 / 继续改 / 确认 / 通过”时，仍然留在当前 Super Dev 流程。"
)
GENERIC_EXIT_RULE = "只有用户明确说取消当前流程、重新开始或切回普通聊天，才允许离开流程。"


def _normalize_string_list(values: list[Any] | None) -> list[str]:
    return [str(item).strip() for item in values or [] if str(item).strip()]


def _collect_session_resume_context(project_dir: Path) -> dict[str, Any]:
    recent_hook_events = HookManager.load_recent_history(project_dir, limit=3)
    return {
        "session_brief_path": str((project_dir / ".super-dev" / "SESSION_BRIEF.md").resolve()),
        "workflow_state_path": str(workflow_state_file(project_dir).resolve()),
        "workflow_event_log_path": str(workflow_event_log_file(project_dir).resolve()),
        "hook_history_path": str(HookManager.hook_history_file(project_dir).resolve()),
        "framework_playbook": load_framework_playbook_summary(project_dir),
        "recent_snapshots": load_recent_workflow_snapshots(project_dir, limit=3),
        "recent_events": load_recent_workflow_events(project_dir, limit=3),
        "recent_hook_events": recent_hook_events,
        "recent_hook_event_dicts": [item.to_dict() for item in recent_hook_events],
        "recent_timeline": load_recent_operational_timeline(project_dir, limit=5),
        "operational_harnesses": summarize_operational_harnesses(project_dir, write_reports=False),
        "operational_focus": derive_operational_focus(project_dir),
    }


def _load_baseline_snapshot(project_dir: Path) -> tuple[dict[str, Any], str, str, list[str]]:
    governance = inspect_baseline_governance(project_dir)
    audit_path = str(
        governance.get("audit_json_path")
        or governance.get("audit_markdown_path")
        or governance.get("audit_path")
        or ""
    ).strip()
    baseline_summary = ""
    reuse_surfaces: list[str] = []
    audit_json_path = str(governance.get("audit_json_path", "")).strip()
    if audit_json_path:
        try:
            payload = json.loads(Path(audit_json_path).read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            current_state = payload.get("current_state")
            if isinstance(current_state, dict):
                baseline_summary = str(current_state.get("summary", "")).strip()
            delta_scope = payload.get("delta_scope")
            if isinstance(delta_scope, dict):
                reuse_surfaces = _normalize_string_list(delta_scope.get("reuse_surfaces"))
    return governance, baseline_summary, audit_path, reuse_surfaces


def _build_session_resume_lines(
    *,
    target: str,
    workflow_mode_label: str,
    action_title: str,
    line_host_first_sentence: str,
    session_brief_path: str,
    workflow_state_path: str,
    specific_rules: list[str],
    framework_playbook: dict[str, Any],
    recent_snapshots: list[dict[str, Any]],
    recent_events: list[dict[str, Any]],
    recent_hook_events: list[Any],
    recent_timeline: list[dict[str, Any]],
    operational_harnesses: list[dict[str, Any]],
    operational_focus: dict[str, Any],
    user_action_shortcuts: list[str],
    action_examples: list[str],
    scenario_cards: list[dict[str, Any]],
    recommended_workflow_command: str,
    preferred_entry_label: str,
    entry_prompts: dict[str, str],
    entry_labels: dict[str, str],
    baseline_summary: str,
    baseline_reuse_surfaces: list[str],
    include_workflow_state_line: bool,
    include_entry_prompt_lines: bool,
) -> list[str]:
    primary_rule = str(specific_rules[0]).strip() if specific_rules else ""
    exit_rule = str(specific_rules[1]).strip() if len(specific_rules) > 1 else ""
    lines = [
        f"动作类型: {workflow_mode_label}" if workflow_mode_label else "",
        f"当前动作: {action_title}" if action_title else "",
        f"宿主第一句: {line_host_first_sentence}",
        f"流程状态卡: {session_brief_path}",
        f"工作流状态 JSON: {workflow_state_path}" if include_workflow_state_line else "",
        f"继续规则: {GENERIC_CONTINUE_RULE}",
        (
            f"当前门禁规则: {primary_rule}"
            if primary_rule and primary_rule != GENERIC_CONTINUE_RULE
            else ""
        ),
        f"退出条件: {GENERIC_EXIT_RULE}",
        (
            f"当前门禁退出条件: {exit_rule}"
            if exit_rule and exit_rule != GENERIC_EXIT_RULE
            else ""
        ),
    ]
    if framework_playbook:
        lines.append(f"框架专项: {framework_playbook.get('framework', '-')}")
        native = framework_playbook.get("native_capabilities", [])
        validation = framework_playbook.get("validation_surfaces", [])
        if native:
            lines.append(f"原生能力面: {' / '.join(str(item) for item in native[:3])}")
        if validation:
            lines.append(f"必验场景: {' / '.join(str(item) for item in validation[:3])}")
    if recent_snapshots:
        first = recent_snapshots[0]
        step = str(first.get("current_step_label", "")).strip() or str(first.get("status", "")).strip()
        updated_at = str(first.get("updated_at", "")).strip() or "-"
        lines.append(f"最近一次: {updated_at} · {step}")
    if recent_events:
        latest_event = recent_events[0]
        event_time = str(latest_event.get("timestamp", "")).strip() or "-"
        lines.append(f"最近事件: {event_time} · {describe_workflow_event(latest_event)}")
    if recent_hook_events:
        latest_hook = recent_hook_events[0]
        hook_status = "blocked" if latest_hook.blocked else ("ok" if latest_hook.success else "failed")
        lines.append(
            f"最近 Hook: {latest_hook.timestamp} · {latest_hook.event} / "
            f"{latest_hook.phase or '-'} / {latest_hook.hook_name} / {hook_status}"
        )
    if recent_timeline:
        latest_timeline = recent_timeline[0]
        timeline_time = str(latest_timeline.get("timestamp", "")).strip() or "-"
        timeline_title = str(latest_timeline.get("title", "")).strip() or str(
            latest_timeline.get("kind", "")
        ).strip()
        timeline_message = str(latest_timeline.get("message", "")).strip() or "-"
        lines.append(f"关键时间线: {timeline_time} · {timeline_title} · {timeline_message}")
    if baseline_summary:
        lines.append(f"Baseline 摘要: {baseline_summary}")
    if baseline_reuse_surfaces:
        lines.append(f"复用面: {' / '.join(baseline_reuse_surfaces[:3])}")
    if operational_harnesses:
        for item in operational_harnesses[:3]:
            label = str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
            status = "pass" if item.get("passed") else "fail"
            line = f"{label}: {status}"
            blocker = str(item.get("first_blocker", "")).strip()
            if blocker:
                line += f" · {blocker}"
            lines.append(line)
    focus_summary = str(operational_focus.get("summary", "")).strip()
    focus_action = str(operational_focus.get("recommended_action", "")).strip()
    if focus_summary:
        lines.append(f"当前治理焦点: {focus_summary}")
    if focus_action:
        lines.append(f"建议先做: {focus_action}")
    if user_action_shortcuts:
        lines.insert(2, f"你现在可以直接说: {' / '.join(user_action_shortcuts[:4])}")
    if action_examples:
        lines.insert(
            3 if user_action_shortcuts else 2,
            f"自然语言示例: {', '.join(action_examples[:3])}",
        )
    if scenario_cards:
        insert_at = 4 if user_action_shortcuts and action_examples else 3 if (
            user_action_shortcuts or action_examples
        ) else 2
        scenario_lines: list[str] = []
        for item in scenario_cards[:4]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            command = str(item.get("cli_command", "")).strip()
            if title and command:
                scenario_lines.append(f"真实场景: {title} -> {command}")
        for offset, line in enumerate(scenario_lines):
            lines.insert(insert_at + offset, line)
    if include_entry_prompt_lines and entry_prompts:
        if preferred_entry_label:
            lines.append(f"推荐入口: {preferred_entry_label}")
        for key, prompt in entry_prompts.items():
            prompt_text = str(prompt).strip()
            if not prompt_text:
                continue
            label = str(entry_labels.get(key, key)).strip() or key
            suffix = "恢复入口" if key != "fallback" else "回退恢复入口"
            lines.append(f"{label} {suffix}: {prompt_text}")
    if recommended_workflow_command:
        lines.append(f"系统建议动作: {recommended_workflow_command}")
    return [line for line in lines if line]


def build_session_resume_card(
    *,
    project_dir: Path,
    target: str,
    enabled: bool,
    host_first_sentence: str,
    line_host_first_sentence: str | None = None,
    continue_instruction: str = "",
    workflow_mode: str = "",
    workflow_mode_label: str = "",
    action_title: str = "",
    action_examples: list[Any] | None = None,
    user_action_shortcuts: list[Any] | None = None,
    scenario_cards: list[Any] | None = None,
    specific_rules: list[Any] | None = None,
    recommended_workflow_command: str = "",
    supports_slash: bool = False,
    flow_variant: str = "",
    workflow_context: dict[str, Any] | None = None,
    include_workflow_state_line: bool = False,
    include_entry_prompt_lines: bool = False,
    prefer_payload_entry_prompt: bool = False,
) -> dict[str, Any]:
    enabled = bool(enabled and str(host_first_sentence).strip())
    action_examples_list = _normalize_string_list(action_examples)
    user_action_shortcuts_list = _normalize_string_list(user_action_shortcuts)
    specific_rules_list = _normalize_string_list(specific_rules)
    scenario_cards_list = [item for item in scenario_cards or [] if isinstance(item, dict)]
    line_host_first_sentence = str(line_host_first_sentence or host_first_sentence).strip()
    host_first_sentence = str(host_first_sentence).strip()

    entry_prompts: dict[str, str] = {}
    entry_labels: dict[str, str] = {}
    preferred_entry = ""
    preferred_entry_label = ""
    if enabled:
        entry_bundle = build_host_entry_prompts(
            target=target,
            instruction=str(continue_instruction or line_host_first_sentence).strip(),
            supports_slash=supports_slash,
            flow_variant=flow_variant,
        )
        raw_entry_prompts = entry_bundle.get("entry_prompts", {})
        if isinstance(raw_entry_prompts, dict):
            entry_prompts = {
                str(key): str(value).strip()
                for key, value in raw_entry_prompts.items()
                if str(value).strip()
            }
        raw_entry_labels = entry_bundle.get("entry_labels", {})
        if isinstance(raw_entry_labels, dict):
            entry_labels = {
                str(key): str(value).strip()
                for key, value in raw_entry_labels.items()
                if str(value).strip()
            }
        preferred_entry = str(entry_bundle.get("preferred_entry", "")).strip()
        preferred_entry_label = str(entry_bundle.get("preferred_entry_label", "")).strip()
        if prefer_payload_entry_prompt and preferred_entry:
            preferred_prompt = str(entry_prompts.get(preferred_entry, "")).strip()
            if preferred_prompt:
                host_first_sentence = preferred_prompt

    if enabled:
        context = _collect_session_resume_context(project_dir)
        baseline_governance, baseline_summary, baseline_audit_path, baseline_reuse_surfaces = (
            _load_baseline_snapshot(project_dir)
        )
        lines = _build_session_resume_lines(
            target=target,
            workflow_mode_label=workflow_mode_label,
            action_title=str(action_title).strip(),
            line_host_first_sentence=line_host_first_sentence,
            session_brief_path=str(context["session_brief_path"]),
            workflow_state_path=str(context["workflow_state_path"]),
            specific_rules=specific_rules_list,
            framework_playbook=dict(context["framework_playbook"]),
            recent_snapshots=list(context["recent_snapshots"]),
            recent_events=list(context["recent_events"]),
            recent_hook_events=list(context["recent_hook_events"]),
            recent_timeline=list(context["recent_timeline"]),
            operational_harnesses=list(context["operational_harnesses"]),
            operational_focus=dict(context["operational_focus"]),
            user_action_shortcuts=user_action_shortcuts_list,
            action_examples=action_examples_list,
            scenario_cards=scenario_cards_list,
            recommended_workflow_command=str(recommended_workflow_command).strip(),
            preferred_entry_label=preferred_entry_label,
            entry_prompts=entry_prompts,
            entry_labels=entry_labels,
            baseline_summary=baseline_summary,
            baseline_reuse_surfaces=baseline_reuse_surfaces,
            include_workflow_state_line=include_workflow_state_line,
            include_entry_prompt_lines=include_entry_prompt_lines,
        )
    else:
        context = {
            "session_brief_path": "",
            "workflow_state_path": "",
            "workflow_event_log_path": "",
            "hook_history_path": "",
            "framework_playbook": {},
            "recent_snapshots": [],
            "recent_events": [],
            "recent_hook_event_dicts": [],
            "recent_timeline": [],
            "operational_harnesses": [],
            "operational_focus": {},
        }
        baseline_governance = {}
        baseline_summary = ""
        baseline_audit_path = ""
        baseline_reuse_surfaces = []
        lines = []

    return {
        "enabled": enabled,
        "workflow_mode": str(workflow_mode).strip() if enabled else "",
        "workflow_mode_label": str(workflow_mode_label).strip() if enabled else "",
        "action_title": str(action_title).strip() if enabled else "",
        "action_examples": action_examples_list if enabled else [],
        "user_action_shortcuts": user_action_shortcuts_list if enabled else [],
        "scenario_cards": scenario_cards_list if enabled else [],
        "host_first_sentence": host_first_sentence if enabled else "",
        "preferred_entry": preferred_entry if enabled else "",
        "preferred_entry_label": preferred_entry_label if enabled else "",
        "entry_prompts": entry_prompts if enabled else {},
        "entry_labels": entry_labels if enabled else {},
        "session_brief_path": str(context["session_brief_path"]) if enabled else "",
        "workflow_state_path": str(context["workflow_state_path"]) if enabled else "",
        "workflow_event_log_path": str(context["workflow_event_log_path"]) if enabled else "",
        "hook_history_path": str(context["hook_history_path"]) if enabled else "",
        "rules": (
            [GENERIC_CONTINUE_RULE, *specific_rules_list, GENERIC_EXIT_RULE] if enabled else []
        ),
        "recommended_workflow_command": str(recommended_workflow_command).strip() if enabled else "",
        "workflow_context": dict(workflow_context or {}) if enabled else {},
        "baseline_governance": dict(baseline_governance) if enabled else {},
        "baseline_summary": baseline_summary if enabled else "",
        "baseline_audit_path": baseline_audit_path if enabled else "",
        "baseline_reuse_surfaces": baseline_reuse_surfaces if enabled else [],
        "framework_playbook": dict(context["framework_playbook"]) if enabled else {},
        "operational_harnesses": list(context["operational_harnesses"]) if enabled else [],
        "operational_focus": dict(context["operational_focus"]) if enabled else {},
        "recent_snapshots": list(context["recent_snapshots"]) if enabled else [],
        "recent_events": list(context["recent_events"]) if enabled else [],
        "recent_hook_events": list(context["recent_hook_event_dicts"]) if enabled else [],
        "recent_timeline": list(context["recent_timeline"]) if enabled else [],
        "lines": lines,
    }
