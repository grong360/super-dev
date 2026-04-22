"""Extracted host report rendering functions — pure data formatting."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalogs import host_display_name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime_status_label(status: str) -> str:
    mapping = {
        "pending": "待真人验收",
        "passed": "已真人通过",
        "failed": "真人验收失败",
    }
    return mapping.get(status, "待真人验收")


def _repo_probe_status_label(status: str) -> str:
    mapping = {
        "pending": "待补齐仓库级 probe",
        "passed": "仓库级 probe 通过",
        "failed": "仓库级 probe 失败",
    }
    return mapping.get(status, "待补齐仓库级 probe")


def _host_list_text(
    items: Any,
    *,
    host_label_fn: Callable[[str], str] | None = None,
) -> str:
    if not isinstance(items, list) or not items:
        return "(none)"
    values: list[str] = []
    for item in items:
        text = str(item)
        values.append(host_label_fn(text) if host_label_fn else text)
    return ", ".join(values)


def _workflow_context_line(workflow_context: Any) -> str:
    if not isinstance(workflow_context, dict):
        return "-"
    status = str(workflow_context.get("workflow_status", "")).strip() or "-"
    gate = str(workflow_context.get("blocking_gate", "")).strip() or "clear"
    next_action = str(workflow_context.get("recommended_host_action", "")).strip() or "-"
    return f"status={status}, gate={gate}, next={next_action}"


def _baseline_governance_line(baseline: Any) -> str:
    if not isinstance(baseline, dict):
        return "-"
    status = str(baseline.get("status", "")).strip() or "-"
    ready = "true" if bool(baseline.get("ready", False)) else "false"
    entry_gate = str(baseline.get("entry_gate", "")).strip() or "clear"
    next_action = str(baseline.get("next_host_action", "")).strip() or "-"
    return f"status={status}, ready={ready}, entry_gate={entry_gate}, next={next_action}"


def _delivery_readiness_note(host: dict[str, Any]) -> str:
    if not isinstance(host, dict):
        return "-"
    if bool(host.get("ready_for_delivery", False)):
        return "当前宿主已经进入可交付态：团队可以直接在这个宿主里继续主流程，不需要额外解释接入方式。"
    blocking_reason = str(host.get("blocking_reason", "")).strip()
    if "截图" in blocking_reason or "视觉" in blocking_reason:
        return "当前先不要把这个宿主当成最终演示入口，视觉与体验风险还会直接暴露给用户。"
    if "repo" in blocking_reason.lower() or "probe" in blocking_reason.lower():
        return "当前最像“表面能用、深入就会卡住”的状态，团队接手和现场演示都还有不稳定因素。"
    if "真人运行时验收失败" in blocking_reason:
        return "当前不要把这个宿主当默认入口，真实工作流已经失败过，先修复再扩大使用范围。"
    if "真人运行时验收" in blocking_reason:
        return "当前仍缺最后一层真人验收，技术上看似就绪，但还不能证明真实团队接手会顺滑。"
    if blocking_reason:
        return "当前还不适合作为默认演示与交付入口：" + blocking_reason
    return "当前还没有形成稳定的交付态，建议先补齐阻塞项再让团队全面切换。"


def _report_header_lines(
    title: str,
    *,
    generated_at: str,
    project_dir: str,
    bullets: list[str] | None = None,
) -> list[str]:
    lines = [
        title,
        "",
        f"- Generated At (UTC): {generated_at}",
        f"- Project Dir: {project_dir}",
    ]
    if bullets:
        lines.extend(bullets)
    lines.append("")
    return lines


def _append_bullet_section(lines: list[str], title: str, bullets: list[str]) -> None:
    lines.extend([title, ""])
    lines.extend(bullets)
    lines.append("")


def _append_markdown_table(
    lines: list[str],
    *,
    headers: list[str],
    separator: str,
    rows: list[str],
) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append(separator)
    lines.extend(rows)


def _write_host_report_files(
    *,
    project_dir: Path,
    project_name: str,
    payload: dict[str, Any],
    base_name: str,
    history_dir_name: str,
    artifacts: dict[str, str],
) -> dict[str, Path]:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    history_dir = output_dir / history_dir_name
    history_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    for key, content in artifacts.items():
        suffix = "json" if key == "json" else "md"
        current_file = output_dir / f"{project_name}-{base_name}.{suffix}"
        current_file.write_text(content, encoding="utf-8")
        written[key if key != "md" else "markdown"] = current_file

        history_key = f"history_{key if key != 'md' else 'markdown'}"
        history_file = history_dir / f"{project_name}-{base_name}-{stamp}.{suffix}"
        history_file.write_text(content, encoding="utf-8")
        written[history_key] = history_file

    if "json" not in artifacts:
        json_file = output_dir / f"{project_name}-{base_name}.json"
        json_file.write_text(payload_json, encoding="utf-8")
        written["json"] = json_file
        history_json = history_dir / f"{project_name}-{base_name}-{stamp}.json"
        history_json.write_text(payload_json, encoding="utf-8")
        written["history_json"] = history_json

    return written


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------


def render_host_compatibility_markdown(
    payload: dict[str, Any],
    *,
    host_label_fn: Callable[[str], str] = host_display_name,
) -> str:
    compatibility = payload.get("compatibility", {})
    report = payload.get("report", {})
    selected_targets = payload.get("selected_targets", [])
    detected_hosts = payload.get("detected_hosts", [])
    if not isinstance(compatibility, dict):
        compatibility = {}
    if not isinstance(report, dict):
        report = {}
    if not isinstance(selected_targets, list):
        selected_targets = []
    if not isinstance(detected_hosts, list):
        detected_hosts = []

    lines = _report_header_lines(
        "# Host Compatibility Report",
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_dir=str(payload.get("project_dir", "")),
        bullets=[
            f"- Detected Hosts: {_host_list_text(detected_hosts, host_label_fn=host_label_fn)}",
            f"- Selected Targets: {_host_list_text(selected_targets, host_label_fn=host_label_fn)}",
        ],
    )
    _append_bullet_section(
        lines,
        "## Summary",
        [
            f"- Overall Score: {compatibility.get('overall_score', 0)}/100",
            f"- Ready Hosts: {compatibility.get('ready_hosts', 0)}/{compatibility.get('total_hosts', 0)}",
            f"- Enabled Checks: {', '.join(str(item) for item in compatibility.get('enabled_checks', []))}",
        ],
    )
    lines.extend(["## Per-Host Scores", ""])
    score_rows: list[str] = []

    host_scores = compatibility.get("hosts", {})
    if isinstance(host_scores, dict):
        for target in selected_targets:
            info = host_scores.get(target, {}) if isinstance(target, str) else {}
            if not isinstance(info, dict):
                info = {}
            usage_profiles = payload.get("usage_profiles", {})
            certification = "-"
            if isinstance(usage_profiles, dict):
                usage = usage_profiles.get(target, {})
                if isinstance(usage, dict):
                    certification = str(usage.get("certification_label", "-"))
            score = info.get("score", 0)
            ready = "yes" if bool(info.get("ready", False)) else "no"
            passed = int(info.get("passed", 0))
            possible = int(info.get("possible", 0))
            score_rows.append(
                f"| {host_label_fn(target)} | {certification} | {score} | {ready} | {passed}/{possible} |"
            )
    _append_markdown_table(
        lines,
        headers=["Host", "Certification", "Score", "Ready", "Passed/Total"],
        separator="|---|---|---:|---|---:|",
        rows=score_rows,
    )

    lines.extend(["", "## Usage Guidance", ""])
    usage_profiles = payload.get("usage_profiles", {})
    if isinstance(usage_profiles, dict):
        for target in selected_targets:
            usage = usage_profiles.get(target, {}) if isinstance(target, str) else {}
            if not isinstance(usage, dict):
                usage = {}
            lines.append(f"### {target}")
            lines.append(
                f"- Certification: {usage.get('certification_label', '-')} ({usage.get('certification_level', '-')})"
            )
            reason = usage.get("certification_reason", "")
            if isinstance(reason, str) and reason.strip():
                lines.append(f"- Certification Reason: {reason}")
            evidence = usage.get("certification_evidence", [])
            if isinstance(evidence, list) and evidence:
                lines.append("- Certification Evidence:")
                for item in evidence:
                    lines.append(f"  - {item}")
            lines.append(f"- Primary Entry: {usage.get('primary_entry', '-')}")
            lines.append(f"- Usage Mode: {usage.get('usage_mode', '-')}")
            lines.append(f"- Trigger Command: {usage.get('trigger_command', '-')}")
            lines.append(f"- Trigger Context: {usage.get('trigger_context', '-')}")
            lines.append(f"- Restart Required: {usage.get('restart_required_label', '-')}")
            experience = usage.get("experience_profile", {})
            if isinstance(experience, dict) and experience:
                lines.append(
                    f"- Experience Tier: {experience.get('label', '-')} ({experience.get('tier', '-')})"
                )
                best_for = str(experience.get("best_for", "")).strip()
                if best_for:
                    lines.append(f"- Best For: {best_for}")
                resume_style = str(experience.get("resume_style", "")).strip()
                if resume_style:
                    lines.append(f"- Resume Style: {resume_style}")
                market_focus = str(experience.get("market_focus", "")).strip()
                if market_focus:
                    lines.append(f"- Market Focus: {market_focus}")
                strengths = experience.get("strengths", [])
                if isinstance(strengths, list) and strengths:
                    lines.append(f"- Strengths: {' / '.join(str(item) for item in strengths[:3])}")
                preferred_entries = experience.get("preferred_entries", [])
                if isinstance(preferred_entries, list) and preferred_entries:
                    lines.append(
                        f"- Preferred Entries: {' / '.join(str(item) for item in preferred_entries[:2])}"
                    )
                native_resume = experience.get("native_resume", [])
                if isinstance(native_resume, list) and native_resume:
                    lines.append(
                        f"- Native Resume: {' / '.join(str(item) for item in native_resume[:2])}"
                    )
            adaptation = usage.get("adaptation_contract", {})
            if isinstance(adaptation, dict) and adaptation:
                lines.append(
                    f"- Adaptation Maturity: {adaptation.get('score', 0)}/100 ({adaptation.get('level', '-')})"
                )
                official_alignment = adaptation.get("official_alignment", {})
                if isinstance(official_alignment, dict) and official_alignment:
                    lines.append(
                        f"- Official Alignment: {official_alignment.get('label', '-')} ({official_alignment.get('status', '-')})"
                    )
                    alignment_summary = str(official_alignment.get("summary", "")).strip()
                    if alignment_summary:
                        lines.append(f"- Official Alignment Summary: {alignment_summary}")
                dimensions = adaptation.get("dimensions", {})
                if isinstance(dimensions, dict) and dimensions:
                    lines.append("- Adaptation Dimensions:")
                    for name, info in dimensions.items():
                        if not isinstance(info, dict):
                            continue
                        status = str(info.get("status", "missing")).strip()
                        lines.append(f"  - {name}: {status}")
                    gaps = [
                        str(gap).strip()
                        for info in dimensions.values()
                        if isinstance(info, dict)
                        for gap in info.get("gaps", [])
                        if str(gap).strip()
                    ]
                    if gaps:
                        lines.append("- Adaptation Gaps:")
                        for gap in gaps[:5]:
                            lines.append(f"  - {gap}")
            precondition_label = usage.get("precondition_label", "")
            if isinstance(precondition_label, str) and precondition_label.strip():
                lines.append(f"- Host Preconditions: {precondition_label}")
            precondition_items = usage.get("precondition_items", [])
            if isinstance(precondition_items, list) and precondition_items:
                lines.append("- Host Precondition Items:")
                for item in precondition_items:
                    if not isinstance(item, dict):
                        continue
                    item_label = str(item.get("label", "")).strip()
                    item_status = str(item.get("status", "")).strip()
                    item_text = item_label or item_status
                    if item_text:
                        lines.append(f"  - {item_text}")
            precondition_guidance = usage.get("precondition_guidance", [])
            if isinstance(precondition_guidance, list) and precondition_guidance:
                lines.append("- Host Precondition Guidance:")
                for item in precondition_guidance:
                    lines.append(f"  - {item}")
            steps = usage.get("post_onboard_steps", [])
            if isinstance(steps, list) and steps:
                lines.append("- Post Onboard Steps:")
                for step in steps:
                    lines.append(f"  - {step}")
            note = usage.get("notes", "")
            if isinstance(note, str) and note.strip():
                lines.append(f"- Notes: {note}")
            lines.append("")

    lines.extend(["## Missing Items", ""])
    hosts = report.get("hosts", {})
    if isinstance(hosts, dict):
        for target in selected_targets:
            host = hosts.get(target, {}) if isinstance(target, str) else {}
            if not isinstance(host, dict):
                continue
            missing = host.get("missing", [])
            if not isinstance(missing, list) or not missing:
                continue
            lines.append(f"### {target}")
            lines.append(f"- Missing: {', '.join(str(item) for item in missing)}")
            suggestions = host.get("suggestions", [])
            if isinstance(suggestions, list):
                for suggestion in suggestions:
                    lines.append(f"- Suggested Action: {suggestion}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_host_surface_audit_markdown(
    payload: dict[str, Any],
    *,
    host_label_fn: Callable[[str], str] = host_display_name,
) -> str:
    report = payload.get("report", {})
    compatibility = payload.get("compatibility", {})
    selected_targets = payload.get("selected_targets", [])
    detected_hosts = payload.get("detected_hosts", [])
    usage_profiles = payload.get("usage_profiles", {})
    repair_actions = payload.get("repair_actions", {})
    if not isinstance(report, dict):
        report = {}
    if not isinstance(compatibility, dict):
        compatibility = {}
    if not isinstance(selected_targets, list):
        selected_targets = []
    if not isinstance(detected_hosts, list):
        detected_hosts = []
    if not isinstance(usage_profiles, dict):
        usage_profiles = {}
    if not isinstance(repair_actions, dict):
        repair_actions = {}

    lines = _report_header_lines(
        "# Host Surface Audit Report",
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_dir=str(payload.get("project_dir", "")),
        bullets=[
            f"- Detected Hosts: {_host_list_text(detected_hosts)}",
            f"- Selected Targets: {_host_list_text(selected_targets)}",
            f"- Overall Score: {compatibility.get('overall_score', 0)}/100",
        ],
    )
    if repair_actions:
        lines.extend(["## Repair Actions", ""])
        for target, actions in repair_actions.items():
            if isinstance(actions, dict):
                action_text = ", ".join(f"{key}={value}" for key, value in actions.items())
                lines.append(f"- {target}: {action_text}")
        lines.append("")

    hosts = report.get("hosts", {})
    if not isinstance(hosts, dict):
        hosts = {}

    for target in selected_targets:
        host = hosts.get(target, {}) if isinstance(target, str) else {}
        usage = usage_profiles.get(target, {}) if isinstance(target, str) else {}
        if not isinstance(host, dict):
            host = {}
        if not isinstance(usage, dict):
            usage = {}
        checks = host.get("checks", {})
        contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
        surfaces = contract.get("surfaces", {}) if isinstance(contract, dict) else {}
        invalid_surfaces = (
            contract.get("invalid_surfaces", {}) if isinstance(contract, dict) else {}
        )
        lines.extend(
            [
                f"## {target}",
                "",
                f"- Ready: {'yes' if bool(host.get('ready', False)) else 'no'}",
                f"- Trigger: {usage.get('final_trigger', '-')}",
                f"- Protocol: {usage.get('host_protocol_summary', '-')}",
                "",
            ]
        )
        surface_rows: list[str] = []
        if isinstance(surfaces, dict):
            for surface_key, surface_info in surfaces.items():
                if not isinstance(surface_info, dict):
                    continue
                exists = "yes" if bool(surface_info.get("exists", False)) else "no"
                missing = surface_info.get("missing_markers", [])
                missing_text = (
                    ", ".join(str(item) for item in missing)
                    if isinstance(missing, list) and missing
                    else "-"
                )
                surface_rows.append(
                    f"| {surface_key} | {exists} | {missing_text} | {surface_info.get('path', '-')} |"
                )
        _append_markdown_table(
            lines,
            headers=["Surface", "Exists", "Missing Markers", "Path"],
            separator="|---|---|---|---|",
            rows=surface_rows,
        )
        suggestions = host.get("suggestions", [])
        if isinstance(invalid_surfaces, dict) and invalid_surfaces:
            lines.extend(["", "### Fix Guidance", ""])
            for surface_key, surface_info in invalid_surfaces.items():
                if not isinstance(surface_info, dict):
                    continue
                missing = surface_info.get("missing_markers", [])
                missing_text = (
                    ", ".join(str(item) for item in missing)
                    if isinstance(missing, list) and missing
                    else "-"
                )
                lines.append(f"- `{surface_key}` -> {missing_text}")
        if isinstance(suggestions, list) and suggestions:
            lines.extend(["", "### Suggested Actions", ""])
            for suggestion in suggestions:
                lines.append(f"- {suggestion}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_host_runtime_validation_markdown(
    payload: dict[str, Any],
    *,
    host_label_fn: Callable[[str], str] = host_display_name,
) -> str:
    hosts = payload.get("hosts", [])
    if not isinstance(hosts, list):
        hosts = []
    lines = _report_header_lines(
        "# Host Runtime Validation Matrix",
        generated_at=str(payload.get("generated_at", "")),
        project_dir=str(payload.get("project_dir", "")),
        bullets=[f"- Detected Hosts: {_host_list_text(payload.get('detected_hosts', []))}"],
    )
    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        framework_focus_name = str(summary.get("framework_focus", "")).strip()
        executive_runtime_summary = str(summary.get("executive_runtime_summary", "")).strip()
        framework_coaching_summary = str(summary.get("framework_coaching_summary", "")).strip()
        framework_validation_surfaces = summary.get("framework_validation_surfaces", [])
        if not framework_focus_name:
            for host in hosts:
                if not isinstance(host, dict):
                    continue
                playbook = host.get("framework_playbook", {})
                if isinstance(playbook, dict) and playbook:
                    framework_focus_name = str(playbook.get("framework", "")).strip()
                    if not isinstance(framework_validation_surfaces, list) or not framework_validation_surfaces:
                        framework_validation_surfaces = playbook.get("validation_surfaces", [])
                    break
        if executive_runtime_summary:
            lines.extend(["## Executive Runtime Summary", "", f"- {executive_runtime_summary}", ""])
        _append_bullet_section(
            lines,
            "## Summary",
            [
                f"- Overall Status: {summary.get('overall_status', '-')}",
                f"- Fully Ready: {summary.get('fully_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- Surface Ready: {summary.get('surface_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- Runtime Passed: {summary.get('runtime_passed_count', 0)}",
                f"- Runtime Failed: {summary.get('runtime_failed_count', 0)}",
                f"- Runtime Pending: {summary.get('runtime_pending_count', 0)}",
                f"- Repo Probe Passed: {summary.get('repo_probe_passed_count', 0)}",
                f"- Repo Probe Failed: {summary.get('repo_probe_failed_count', 0)}",
                f"- Repo Probe Pending: {summary.get('repo_probe_pending_count', 0)}",
                f"- Project-First Ready: {summary.get('project_default_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- Standard Flow Ready: {summary.get('standard_flow_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- SEEAI Flow Ready: {summary.get('competition_flow_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- SEEAI User Supplements Ready: {summary.get('competition_user_surface_ready_count', 0)}/{summary.get('total_hosts', 0)}",
                f"- Explicit User-Surface Ready: {summary.get('explicit_user_surface_ready_count', 0)}/{summary.get('user_surface_opt_in_available_count', 0)}",
                f"- Workflow Context: {_workflow_context_line(payload.get('workflow_context', {}))}",
                f"- Baseline Governance: {_baseline_governance_line(payload.get('baseline_governance', {}))}",
                (
                    f"- Framework Focus: {framework_focus_name}"
                    if framework_focus_name
                    else "- Framework Focus: -"
                ),
                (
                    "- Framework Validation Surfaces: "
                    + "；".join(str(item) for item in framework_validation_surfaces[:4])
                    if isinstance(framework_validation_surfaces, list) and framework_validation_surfaces
                    else "- Framework Validation Surfaces: -"
                ),
                (
                    f"- Framework Coaching Summary: {framework_coaching_summary}"
                    if framework_coaching_summary
                    else "- Framework Coaching Summary: -"
                ),
            ],
        )
    blockers = payload.get("blockers", [])
    if isinstance(blockers, list):
        lines.extend(["## Current Blockers", ""])
        if blockers:
            for item in blockers:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('host', '-')}** ({item.get('type', '-')}) {item.get('summary', '-')}"
                )
        else:
            lines.append("- 当前没有阻塞项。")
        lines.extend(["", "## Recommended Next Actions", ""])
        next_actions = summary.get("next_actions", []) if isinstance(summary, dict) else []
        if isinstance(next_actions, list) and next_actions:
            for item in next_actions:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前宿主验收中心没有额外动作。")
        lines.append("")
    summary_rows: list[str] = []
    for host in hosts:
        if not isinstance(host, dict):
            continue
        repo_probe = host.get("repo_probe", {})
        repo_probe_status = (
            str(repo_probe.get("status", "")).strip() if isinstance(repo_probe, dict) else ""
        )
        summary_rows.append(
            f"| {host.get('host', '-')} | {'yes' if bool(host.get('surface_ready', False)) else 'no'} | "
            f"{host.get('final_trigger', '-')} | {host.get('host_protocol_summary', '-')} | "
            f"{host.get('manual_runtime_status_label', '-')} | {_repo_probe_status_label(repo_probe_status)} |"
        )
    _append_markdown_table(
        lines,
        headers=[
            "Host",
            "Surface Ready",
            "Trigger",
            "Protocol",
            "Manual Runtime Status",
            "Repo Probe",
        ],
        separator="|---|---|---|---|---|---|",
        rows=summary_rows,
    )

    for host in hosts:
        if not isinstance(host, dict):
            continue
        repo_probe = host.get("repo_probe", {})
        if not isinstance(repo_probe, dict):
            repo_probe = {}
        lines.extend(
            [
                "",
                f"## {host.get('host', '-')}",
                "",
                f"- Trigger: {host.get('final_trigger', '-')}",
                f"- Protocol: {host.get('host_protocol_summary', '-')}",
                f"- Surface Ready: {'yes' if bool(host.get('surface_ready', False)) else 'no'}",
                f"- Manual Runtime Status: {host.get('manual_runtime_status_label', '-')}",
                f"- Repo Probe: {_repo_probe_status_label(str(repo_probe.get('status', '')).strip())}",
                f"- Host Preconditions: {host.get('precondition_label', '-')}",
                f"- Smoke Prompt: {host.get('smoke_test_prompt', '-')}",
                f"- Smoke Success Signal: {host.get('smoke_success_signal', '-')}",
                "",
                "### Delivery Readiness",
                "",
                f"- Standard Flow Ready: {'yes' if bool(host.get('ready_for_standard_flow', False)) else 'no'}",
                f"- SEEAI Flow Ready: {'yes' if bool(host.get('ready_for_competition_flow', False)) else 'no'}",
                f"- Delivery Ready: {'yes' if bool(host.get('ready_for_delivery', False)) else 'no'}",
                f"- Blocking Reason: {host.get('blocking_reason', '-') or '-'}",
                f"- Recommended Action: {host.get('recommended_action', '-') or '-'}",
                f"- Management View: {_delivery_readiness_note(host)}",
                "",
                "### Runtime Checklist",
                "",
            ]
        )
        repo_probe_summary = str(repo_probe.get("summary", "")).strip()
        if repo_probe_summary:
            lines.extend(["### Repo Probe Summary", "", f"- {repo_probe_summary}", ""])
        repo_probe_workflow_context = repo_probe.get("workflow_context", {})
        repo_probe_baseline = repo_probe.get("baseline_governance", {})
        repo_probe_workflow = str(repo_probe.get("workflow_status", "")).strip()
        repo_probe_stage = str(repo_probe.get("current_stage_name", "")).strip()
        repo_probe_command = str(repo_probe.get("recommended_command", "")).strip()
        repo_probe_blockers = repo_probe.get("blockers", [])
        repo_probe_actions = repo_probe.get("next_actions", [])
        if repo_probe_workflow or repo_probe_stage or repo_probe_command:
            lines.extend(["### Repo Probe Context", ""])
            if repo_probe_stage:
                lines.append(f"- Current Stage: {repo_probe_stage}")
            if repo_probe_workflow:
                lines.append(f"- Workflow Status: {repo_probe_workflow}")
            if repo_probe_command:
                lines.append(f"- Recommended Command: `{repo_probe_command}`")
            lines.append("")
        if isinstance(repo_probe_workflow_context, dict) and repo_probe_workflow_context:
            lines.extend(
                [
                    "### Workflow Context",
                    "",
                    f"- {_workflow_context_line(repo_probe_workflow_context)}",
                    "",
                ]
            )
        if isinstance(repo_probe_baseline, dict) and repo_probe_baseline:
            lines.extend(
                [
                    "### Baseline Governance",
                    "",
                    f"- {_baseline_governance_line(repo_probe_baseline)}",
                    "",
                ]
            )
        if isinstance(repo_probe_blockers, list) and repo_probe_blockers:
            lines.extend(["### Repo Probe Blockers", ""])
            for item in repo_probe_blockers:
                lines.append(f"- {item}")
            lines.append("")
        if isinstance(repo_probe_actions, list) and repo_probe_actions:
            lines.extend(["### Repo Probe Next Actions", ""])
            for item in repo_probe_actions:
                lines.append(f"- {item}")
            lines.append("")
        resume_probe = host.get("resume_probe_prompt", "")
        if isinstance(resume_probe, str) and resume_probe.strip():
            lines.extend(["### Resume Probe Prompt", "", f"- {resume_probe.strip()}", ""])
        framework_playbook = host.get("framework_playbook", {})
        if isinstance(framework_playbook, dict) and framework_playbook:
            lines.extend(
                [
                    "### Framework Playbook",
                    "",
                    f"- Framework: {framework_playbook.get('framework', '-')}",
                ]
            )
            modules = framework_playbook.get("implementation_modules", [])
            if isinstance(modules, list) and modules:
                lines.append(
                    "- Implementation Modules: " + "；".join(str(item) for item in modules[:3])
                )
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if isinstance(native_capabilities, list) and native_capabilities:
                lines.append(
                    "- Native Capabilities: "
                    + "；".join(str(item) for item in native_capabilities[:3])
                )
            validation = framework_playbook.get("validation_surfaces", [])
            if isinstance(validation, list) and validation:
                lines.append(
                    "- Validation Surfaces: " + "；".join(str(item) for item in validation[:3])
                )
            evidence = framework_playbook.get("delivery_evidence", [])
            if isinstance(evidence, list) and evidence:
                lines.append(
                    "- Delivery Evidence: " + "；".join(str(item) for item in evidence[:3])
                )
            lines.append("")
        comment = host.get("manual_runtime_comment", "")
        if isinstance(comment, str) and comment.strip():
            lines.extend(["### Runtime Validation Note", "", f"- {comment.strip()}", ""])
        competition_ready = bool(host.get("competition_evidence_ready", False))
        competition_missing = host.get("competition_evidence_missing", [])
        competition_shallow = host.get("competition_evidence_shallow", [])
        if bool(host.get("competition_evidence_required", False)):
            lines.extend(
                [
                    "### Competition Evidence",
                    "",
                    f"- Evidence Ready: {'yes' if competition_ready else 'no'}",
                ]
            )
            if isinstance(competition_missing, list) and competition_missing:
                lines.append(
                    "- Missing Sections: " + "、".join(str(item) for item in competition_missing)
                )
            if isinstance(competition_shallow, list) and competition_shallow:
                lines.append(
                    "- Shallow Sections: " + "、".join(str(item) for item in competition_shallow)
                )
                lines.append(
                    "  - 这些段落已填写，但内容过短或未覆盖模板 `required` 关键词，视为未真正验收。"
                )
            lines.append("")
        preconditions = host.get("precondition_guidance", [])
        if isinstance(preconditions, list) and preconditions:
            lines.extend(["", "### Host Precondition Guidance", ""])
            for item in preconditions:
                lines.append(f"- {item}")
        start_playbook = host.get("host_start_playbook", [])
        if isinstance(start_playbook, list) and start_playbook:
            lines.extend(["", "### Host Start Playbook", ""])
            for item in start_playbook:
                lines.append(f"- {item}")
        standard_first_prompt = str(host.get("standard_flow_first_prompt", "")).strip()
        competition_first_prompt = str(host.get("competition_flow_first_prompt", "")).strip()
        if standard_first_prompt or competition_first_prompt:
            lines.extend(["", "### First Prompts", ""])
            if standard_first_prompt:
                lines.append(f"- Standard Flow: {standard_first_prompt}")
            if competition_first_prompt:
                lines.append(f"- SEEAI Flow: {competition_first_prompt}")
        post_onboard_self_check = host.get("post_onboard_self_check", [])
        if isinstance(post_onboard_self_check, list) and post_onboard_self_check:
            lines.extend(["", "### Post-Onboard Self-Check", ""])
            for item in post_onboard_self_check:
                lines.append(f"- {item}")
        injection_closure = host.get("injection_closure", {})
        if isinstance(injection_closure, dict) and injection_closure:
            lines.extend(["", "### Injection Closure", ""])
            lines.append(f"- Scope: {injection_closure.get('scope', '-')}")
            lines.append(f"- Status: {injection_closure.get('label', '-')}")
            lines.append(f"- Summary: {injection_closure.get('summary', '-')}")
            if "standard_flow_label" in injection_closure:
                lines.append(
                    f"- Standard Flow: {injection_closure.get('standard_flow_label', '-')}"
                )
            if "competition_flow_label" in injection_closure:
                lines.append(f"- SEEAI Flow: {injection_closure.get('competition_flow_label', '-')}")
            if "competition_project_surfaces_ready" in injection_closure:
                lines.append(
                    "- SEEAI Project Supplements Ready: "
                    + (
                        "yes"
                        if bool(injection_closure.get("competition_project_surfaces_ready", False))
                        else "no"
                    )
                )
            if "competition_user_surfaces_ready" in injection_closure:
                lines.append(
                    "- SEEAI User Supplements Ready: "
                    + (
                        "yes"
                        if bool(injection_closure.get("competition_user_surfaces_ready", False))
                        else "no"
                    )
                )
            if injection_closure.get("opt_in_flag"):
                lines.append(f"- User-Surface Opt-In: {injection_closure.get('opt_in_flag')}")
            missing_optional = injection_closure.get("missing_optional_user_surfaces", [])
            if isinstance(missing_optional, list) and missing_optional:
                lines.append("- Missing Optional User Surfaces: " + " / ".join(missing_optional[:3]))
            missing_competition = injection_closure.get(
                "missing_managed_competition_project_surfaces", []
            )
            if isinstance(missing_competition, list) and missing_competition:
                lines.append(
                    "- Missing SEEAI Project Supplements: "
                    + " / ".join(str(item) for item in missing_competition[:3])
                )
            missing_competition_user = injection_closure.get(
                "missing_managed_competition_user_surfaces", []
            )
            if isinstance(missing_competition_user, list) and missing_competition_user:
                lines.append(
                    "- Missing SEEAI User Supplements: "
                    + " / ".join(str(item) for item in missing_competition_user[:3])
                )
            recommended_opt_in = str(injection_closure.get("recommended_opt_in", "")).strip()
            if recommended_opt_in:
                lines.append(f"- Opt-In Guidance: {recommended_opt_in}")
        official_workflow_checks = host.get("official_workflow_checks", [])
        if isinstance(official_workflow_checks, list) and official_workflow_checks:
            lines.extend(["", "### Official Workflow Checks", ""])
            for item in official_workflow_checks:
                lines.append(f"- {item}")
        repair_playbook = host.get("host_repair_playbook", "")
        if isinstance(repair_playbook, str) and repair_playbook.strip():
            lines.extend(["", "### Host Repair Playbook", "", f"- {repair_playbook.strip()}"])
        checklist = host.get("runtime_checklist", [])
        if isinstance(checklist, list):
            lines.extend(["", "### Runtime Checklist", ""])
            for item in checklist:
                lines.append(f"- {item}")
        lines.extend(["", "### Pass Criteria", ""])
        criteria = host.get("pass_criteria", [])
        if isinstance(criteria, list):
            for item in criteria:
                lines.append(f"- {item}")
        resume_checklist = host.get("resume_checklist", [])
        if isinstance(resume_checklist, list) and resume_checklist:
            lines.extend(["", "### Resume Checklist", ""])
            for item in resume_checklist:
                lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def render_host_hardening_markdown(
    payload: dict[str, Any],
    *,
    host_label_fn: Callable[[str], str] = host_display_name,
) -> str:
    compatibility = payload.get("compatibility", {})
    selected_targets = payload.get("selected_targets", [])
    hardening_results = payload.get("hardening_results", {})
    if not isinstance(compatibility, dict):
        compatibility = {}
    if not isinstance(selected_targets, list):
        selected_targets = []
    if not isinstance(hardening_results, dict):
        hardening_results = {}
    lines = _report_header_lines(
        "# Host System Hardening Report",
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_dir=str(payload.get("project_dir", "")),
        bullets=[
            f"- Selected Targets: {_host_list_text(selected_targets)}",
            f"- Compatibility Score: {compatibility.get('overall_score', 0)}/100",
            f"- Flow Consistency: {compatibility.get('flow_consistency_score', 0)}/100",
            f"- Official Doc Alignment: {((payload.get('official_compare_summary', {}) or {}).get('score', 0))}/100",
            f"- Host Parity: {((payload.get('host_parity_summary', {}) or {}).get('score', 0))}/100",
            f"- Host Gate Parity: {((payload.get('host_gate_summary', {}) or {}).get('score', 0))}/100",
            f"- Host Runtime Script Parity: {((payload.get('host_runtime_script_summary', {}) or {}).get('score', 0))}/100",
            f"- Host Recovery Parity: {((payload.get('host_recovery_summary', {}) or {}).get('score', 0))}/100",
        ],
    )
    for target in selected_targets:
        item = hardening_results.get(target, {}) if isinstance(target, str) else {}
        if not isinstance(item, dict):
            item = {}
        plan = item.get("plan", {})
        contract = item.get("contract", {})
        official_compare = item.get("official_compare", {})
        gate_hosts = (payload.get("host_gate_summary", {}) or {}).get("hosts", {})
        gate_info = gate_hosts.get(target, {}) if isinstance(gate_hosts, dict) else {}
        runtime_script_hosts = (payload.get("host_runtime_script_summary", {}) or {}).get(
            "hosts", {}
        )
        runtime_script_info = (
            runtime_script_hosts.get(target, {}) if isinstance(runtime_script_hosts, dict) else {}
        )
        recovery_hosts = (payload.get("host_recovery_summary", {}) or {}).get("hosts", {})
        recovery_info = recovery_hosts.get(target, {}) if isinstance(recovery_hosts, dict) else {}
        usage_profiles = payload.get("usage_profiles", {})
        usage = usage_profiles.get(target, {}) if isinstance(usage_profiles, dict) else {}
        lines.extend([f"## {target}", ""])
        lines.append(f"- Trigger: {plan.get('final_trigger', '-')}")
        lines.append(f"- Trigger Mode: {plan.get('trigger_mode', '-')}")
        lines.append(f"- Contract OK: {'yes' if bool((contract or {}).get('ok', False)) else 'no'}")
        experience = usage.get("experience_profile", {}) if isinstance(usage, dict) else {}
        if isinstance(experience, dict) and experience:
            lines.append(
                f"- Experience Tier: {experience.get('label', '-')} ({experience.get('tier', '-')})"
            )
            best_for = str(experience.get("best_for", "")).strip()
            if best_for:
                lines.append(f"- Best For: {best_for}")
            native_resume = experience.get("native_resume", [])
            if isinstance(native_resume, list) and native_resume:
                lines.append(
                    f"- Native Resume: {' / '.join(str(item) for item in native_resume[:2])}"
                )
        adaptation = usage.get("adaptation_contract", {}) if isinstance(usage, dict) else {}
        if isinstance(adaptation, dict) and adaptation:
            lines.append(
                f"- Adaptation Maturity: {adaptation.get('score', 0)}/100 ({adaptation.get('level', '-')})"
            )
            official_alignment = adaptation.get("official_alignment", {})
            if isinstance(official_alignment, dict) and official_alignment:
                lines.append(
                    f"- Official Alignment: {official_alignment.get('label', '-')} ({official_alignment.get('status', '-')})"
                )
                alignment_summary = str(official_alignment.get("summary", "")).strip()
                if alignment_summary:
                    lines.append(f"- Official Alignment Summary: {alignment_summary}")
            dimensions = adaptation.get("dimensions", {})
            if isinstance(dimensions, dict) and dimensions:
                lines.append("- Adaptation Contract:")
                for name, info in dimensions.items():
                    if not isinstance(info, dict):
                        continue
                    status = str(info.get("status", "missing")).strip()
                    lines.append(f"  - {name}: {status}")
                gaps = [
                    str(gap).strip()
                    for info in dimensions.values()
                    if isinstance(info, dict)
                    for gap in info.get("gaps", [])
                    if str(gap).strip()
                ]
                if gaps:
                    lines.append("- Adaptation Gaps:")
                    for gap in gaps[:5]:
                        lines.append(f"  - {gap}")
        if isinstance(gate_info, dict) and gate_info:
            lines.append(
                f"- Gate Parity: {'yes' if bool(gate_info.get('passed', False)) else 'no'}"
            )
        if isinstance(runtime_script_info, dict) and runtime_script_info:
            lines.append(
                f"- Runtime Script Parity: {'yes' if bool(runtime_script_info.get('passed', False)) else 'no'}"
            )
        if isinstance(recovery_info, dict) and recovery_info:
            lines.append(
                f"- Recovery Parity: {'yes' if bool(recovery_info.get('passed', False)) else 'no'}"
            )
            actions = recovery_info.get("recommended_actions", [])
            if isinstance(actions, list) and actions:
                lines.append("- Recovery Actions:")
                for action in actions:
                    lines.append(f"  - {action}")
            else:
                commands = recovery_info.get("recommended_commands", [])
                if isinstance(commands, list) and commands:
                    lines.append("- Recovery Commands:")
                    for cmd in commands:
                        lines.append(f"  - {cmd}")
        if isinstance(official_compare, dict) and official_compare:
            lines.append(
                f"- Official Compare: {official_compare.get('status', 'unknown')} "
                f"({official_compare.get('reachable_urls', 0)}/{official_compare.get('checked_urls', 0)})"
            )
        written_files = item.get("written_files", [])
        if isinstance(written_files, list) and written_files:
            lines.append("- Updated Files:")
            for path in written_files:
                lines.append(f"  - {path}")
        required_steps = plan.get("required_steps", [])
        if isinstance(required_steps, list) and required_steps:
            lines.append("- Required Steps:")
            for step in required_steps:
                lines.append(f"  - {step}")
        skill_install = item.get("skill_install", {})
        if isinstance(skill_install, dict) and bool(skill_install.get("required", False)):
            lines.append(
                f"- Skill Install: {'ok' if bool(skill_install.get('installed', False)) else 'failed'}"
            )
            if skill_install.get("path"):
                lines.append(f"  - Path: {skill_install.get('path')}")
            if skill_install.get("error"):
                lines.append(f"  - Error: {skill_install.get('error')}")
        invalid = (contract or {}).get("invalid_surfaces", {})
        if isinstance(invalid, dict) and invalid:
            lines.append("- Invalid Surfaces:")
            for surface_key in invalid.keys():
                lines.append(f"  - {surface_key}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_host_parity_onepage_markdown(
    payload: dict[str, Any],
    *,
    host_label_fn: Callable[[str], str] = host_display_name,
) -> str:
    selected_targets = payload.get("selected_targets", [])
    if not isinstance(selected_targets, list):
        selected_targets = []
    hardening_results = payload.get("hardening_results", {})
    if not isinstance(hardening_results, dict):
        hardening_results = {}
    parity_index = payload.get("host_parity_index", {})
    if not isinstance(parity_index, dict):
        parity_index = {}
    lines = _report_header_lines(
        "# Host Parity Onepage",
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_dir=str(payload.get("project_dir", "")),
        bullets=[
            f"- Host Parity Index: {parity_index.get('score', 0)}/100 "
            f"(threshold {parity_index.get('threshold', 95.0)}, "
            f"{'pass' if bool(parity_index.get('passed', False)) else 'fail'})"
        ],
    )
    official_hosts = (payload.get("official_compare_summary", {}) or {}).get("hosts", {})
    parity_hosts = (payload.get("host_parity_summary", {}) or {}).get("hosts", {})
    gate_hosts = (payload.get("host_gate_summary", {}) or {}).get("hosts", {})
    runtime_hosts = (payload.get("host_runtime_script_summary", {}) or {}).get("hosts", {})
    recovery_hosts = (payload.get("host_recovery_summary", {}) or {}).get("hosts", {})
    flow_hosts = (payload.get("compatibility", {}) or {}).get("hosts", {})
    onepage_rows: list[str] = []
    for target in selected_targets:
        item = hardening_results.get(target, {}) if isinstance(target, str) else {}
        contract = item.get("contract", {}) if isinstance(item, dict) else {}
        recovery = recovery_hosts.get(target, {}) if isinstance(recovery_hosts, dict) else {}
        recovery_actions = (
            recovery.get("recommended_actions", []) if isinstance(recovery, dict) else []
        )
        recovery_commands = (
            recovery.get("recommended_commands", []) if isinstance(recovery, dict) else []
        )
        dimensions: list[tuple[str, bool]] = []
        dimensions.append(
            ("official_compare", str((official_hosts or {}).get(target, "unknown")) == "passed")
        )
        dimensions.append(
            (
                "host_parity",
                bool(((parity_hosts or {}).get(target, {}) or {}).get("passed", False)),
            )
        )
        dimensions.append(
            ("host_gate", bool(((gate_hosts or {}).get(target, {}) or {}).get("passed", False)))
        )
        dimensions.append(
            (
                "runtime_script",
                bool(((runtime_hosts or {}).get(target, {}) or {}).get("passed", False)),
            )
        )
        dimensions.append(
            (
                "host_recovery",
                bool(((recovery_hosts or {}).get(target, {}) or {}).get("passed", False)),
            )
        )
        dimensions.append(
            (
                "flow_consistency",
                bool(((flow_hosts or {}).get(target, {}) or {}).get("flow_consistent", False)),
            )
        )
        contract_ok = bool((contract or {}).get("ok", False))
        status = "PASS" if contract_ok and all(ok for _, ok in dimensions) else "FAIL"
        failed = [name for name, ok in dimensions if not ok]
        failed_text = ", ".join(failed) if failed else "-"
        next_command = "-"
        if isinstance(recovery_commands, list) and recovery_commands:
            next_command = str(recovery_commands[0]).strip() or "-"
        elif isinstance(recovery_actions, list) and recovery_actions:
            next_command = str(recovery_actions[0]).strip() or "-"
        onepage_rows.append(f"| {target} | {status} | {failed_text} | `{next_command}` |")
    _append_markdown_table(
        lines,
        headers=["Host", "Status", "Failed Dimension", "Next Action"],
        separator="|---|---|---|---|",
        rows=onepage_rows,
    )
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------


def write_host_surface_audit_report(
    *,
    project_dir: Path,
    payload: dict[str, Any],
    resolve_project_name_fn: Callable[[Path], str],
    render_surface_audit_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Path]:
    project_name = resolve_project_name_fn(project_dir)
    return _write_host_report_files(
        project_dir=project_dir,
        project_name=project_name,
        payload=payload,
        base_name="host-surface-audit",
        history_dir_name="host-surface-audit-history",
        artifacts={
            "json": json.dumps(payload, ensure_ascii=False, indent=2),
            "md": render_surface_audit_fn(payload),
        },
    )


def write_host_hardening_report(
    *,
    project_dir: Path,
    payload: dict[str, Any],
    resolve_project_name_fn: Callable[[Path], str],
    render_hardening_fn: Callable[[dict[str, Any]], str],
    render_parity_onepage_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Path]:
    project_name = resolve_project_name_fn(project_dir)
    written = _write_host_report_files(
        project_dir=project_dir,
        project_name=project_name,
        payload=payload,
        base_name="host-hardening",
        history_dir_name="host-hardening-history",
        artifacts={
            "json": json.dumps(payload, ensure_ascii=False, indent=2),
            "md": render_hardening_fn(payload),
        },
    )
    output_dir = project_dir / "output"
    stamp = written["history_markdown"].stem.rsplit("-", 1)[-1]
    onepage_file = output_dir / f"{project_name}-host-parity-onepage.md"
    onepage_file.write_text(render_parity_onepage_fn(payload), encoding="utf-8")
    history_onepage = (
        output_dir
        / "host-hardening-history"
        / f"{project_name}-host-parity-onepage-{stamp}.md"
    )
    history_onepage.write_text(render_parity_onepage_fn(payload), encoding="utf-8")
    written["onepage_markdown"] = onepage_file
    written["history_onepage_markdown"] = history_onepage
    return written


def write_host_runtime_validation_report(
    *,
    project_dir: Path,
    payload: dict[str, Any],
    resolve_project_name_fn: Callable[[Path], str],
    render_runtime_validation_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Path]:
    project_name = resolve_project_name_fn(project_dir)
    return _write_host_report_files(
        project_dir=project_dir,
        project_name=project_name,
        payload=payload,
        base_name="host-runtime-validation",
        history_dir_name="host-runtime-validation-history",
        artifacts={
            "json": json.dumps(payload, ensure_ascii=False, indent=2),
            "md": render_runtime_validation_fn(payload),
        },
    )


def write_host_compatibility_report(
    *,
    project_dir: Path,
    payload: dict[str, Any],
    resolve_project_name_fn: Callable[[Path], str],
    render_compatibility_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Path]:
    project_name = resolve_project_name_fn(project_dir)
    return _write_host_report_files(
        project_dir=project_dir,
        project_name=project_name,
        payload=payload,
        base_name="host-compatibility",
        history_dir_name="host-compatibility-history",
        artifacts={
            "json": json.dumps(payload, ensure_ascii=False, indent=2),
            "md": render_compatibility_fn(payload),
        },
    )
