"""Shared host diagnostics and compatibility summary builders."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .integrations.manager import IntegrationManager


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def build_host_injection_closure(
    *,
    host_ready: bool,
    surface_sets: dict[str, list[Path]],
    managed_competition_project_paths: list[Path] | None = None,
    managed_competition_user_paths: list[Path] | None = None,
) -> dict[str, Any]:
    project_default_paths = _dedupe_paths(
        [
            *surface_sets.get("official_project", []),
            *surface_sets.get("required_slash", []),
        ]
    )
    fallback_user_default_paths = _dedupe_paths(
        [
            *surface_sets.get("official_user", []),
            *surface_sets.get("official_skill", []),
            *surface_sets.get("required_slash", []),
        ]
    )
    if project_default_paths:
        scope = "project-first"
        default_paths = project_default_paths
        scope_label = "项目优先接入"
    else:
        scope = "user-skill-default"
        default_paths = fallback_user_default_paths
        scope_label = "用户级 Skill 默认接入"
    optional_user_paths = _dedupe_paths(
        [
            *surface_sets.get("optional_user", []),
            *surface_sets.get("optional_slash", []),
        ]
    )
    competition_project_paths = _dedupe_paths(list(managed_competition_project_paths or []))
    competition_user_paths = _dedupe_paths(list(managed_competition_user_paths or []))
    missing_default = [str(path) for path in default_paths if not path.exists()]
    missing_optional_user = [str(path) for path in optional_user_paths if not path.exists()]
    missing_competition_project = [
        str(path) for path in competition_project_paths if not path.exists()
    ]
    missing_competition_user = [str(path) for path in competition_user_paths if not path.exists()]
    default_ready = not missing_default
    optional_user_available = bool(optional_user_paths)
    explicit_user_surfaces_ready = optional_user_available and not missing_optional_user
    competition_project_available = bool(competition_project_paths)
    competition_user_available = bool(competition_user_paths)
    competition_project_surfaces_ready = (
        competition_project_available and not missing_competition_project
    )
    competition_user_surfaces_ready = competition_user_available and not missing_competition_user
    standard_flow_ready = default_ready
    competition_flow_ready = default_ready and (
        not competition_project_available or competition_project_surfaces_ready
    ) and (
        not competition_user_available or competition_user_surfaces_ready
    )

    if not default_ready:
        status = "project_default_incomplete"
        label = f"{scope_label}未闭环"
        summary = f"当前宿主的{scope_label}还未闭环，先补齐默认接入面。"
        user_surface_scope = "blocked"
    elif explicit_user_surfaces_ready:
        status = "project_default_ready_with_user_opt_in_enabled"
        label = f"{scope_label}已闭环，且显式用户级增强面已启用"
        summary = f"当前宿主已完成{scope_label}，显式用户级增强面也已就绪。"
        user_surface_scope = "enabled"
    elif optional_user_available:
        status = "project_default_ready_with_user_opt_in_available"
        label = f"{scope_label}已闭环，可按需启用用户级增强面"
        summary = f"当前宿主已完成{scope_label}；如需跨项目共享统一宿主心智，可再显式启用用户级增强面。"
        user_surface_scope = "available-not-enabled"
    else:
        status = "project_default_ready"
        label = f"{scope_label}已闭环"
        summary = f"当前宿主已完成{scope_label}。"
        user_surface_scope = "not-applicable"

    competition_gap_labels: list[str] = []
    if competition_project_available and not competition_project_surfaces_ready:
        competition_gap_labels.append("SEEAI 项目补充面")
    if competition_user_available and not competition_user_surfaces_ready:
        competition_gap_labels.append("SEEAI 用户级补充面")

    if default_ready and competition_gap_labels:
        status = f"{status}_competition_incomplete"
        gap_text = (
            competition_gap_labels[0]
            if len(competition_gap_labels) == 1
            else "与".join(competition_gap_labels)
        )
        label = f"{label}；{gap_text}待补齐"
        summary = f"{summary.rstrip('。')}；{gap_text}还未闭环。"

    recommended_opt_in = (
        "如需跨项目共享统一宿主心智，再显式加 --with-user-surfaces 重新运行 super-dev。"
        if optional_user_available and not explicit_user_surfaces_ready
        else ""
    )

    return {
        "scope": scope,
        "status": status,
        "label": label,
        "summary": summary,
        "standard_flow_ready": standard_flow_ready,
        "standard_flow_label": (
            "标准流可直接开工" if standard_flow_ready else "标准流待补齐默认接入面"
        ),
        "competition_flow_ready": competition_flow_ready,
        "competition_flow_label": (
            "SEEAI 比赛模式可直接开工"
            if competition_flow_ready
            else "SEEAI 比赛模式待补齐项目与用户级补充面"
            if competition_project_available and competition_user_available
            else "SEEAI 比赛模式待补齐项目补充面"
            if competition_project_available
            else "SEEAI 比赛模式待补齐用户级补充面"
            if competition_user_available
            else "SEEAI 比赛模式未配置补充面"
        ),
        "project_default_ready": default_ready,
        "user_surface_scope": user_surface_scope,
        "user_surface_opt_in_available": optional_user_available,
        "explicit_user_surfaces_ready": explicit_user_surfaces_ready,
        "default_required_surfaces": [str(path) for path in default_paths],
        "missing_default_surfaces": missing_default,
        "optional_user_surfaces": [str(path) for path in optional_user_paths],
        "missing_optional_user_surfaces": missing_optional_user,
        "managed_competition_project_surfaces": [str(path) for path in competition_project_paths],
        "competition_project_surfaces_ready": competition_project_surfaces_ready,
        "missing_managed_competition_project_surfaces": missing_competition_project,
        "managed_competition_user_surfaces": [str(path) for path in competition_user_paths],
        "competition_user_surfaces_ready": competition_user_surfaces_ready,
        "missing_managed_competition_user_surfaces": missing_competition_user,
        "opt_in_flag": "--with-user-surfaces" if optional_user_available else "",
        "recommended_opt_in": recommended_opt_in,
    }


def collect_host_diagnostics(
    *,
    project_dir: Path,
    targets: list[str],
    skill_name: str,
    check_integrate: bool,
    check_skill: bool,
    check_slash: bool,
    build_usage_profile_fn: Callable[[IntegrationManager, str], dict[str, Any]],
    build_diagnosis_fn: Callable[[str, dict[str, Any], IntegrationManager], dict[str, str]] | None = None,
    skill_primary_file_fn: Callable[[str, list[Path], list[Path], list[Path]], Path | None] | None = None,
    integrate_no_project_note: str | None = None,
) -> dict[str, Any]:
    integration_manager = IntegrationManager(project_dir)

    report: dict[str, Any] = {"hosts": {}, "overall_ready": True}
    for target in targets:
        host_report: dict[str, Any] = {
            "ready": True,
            "checks": {},
            "missing": [],
            "optional_missing": [],
            "suggestions": [],
        }
        surface_groups = integration_manager.readiness_surface_sets(
            target=target,
            skill_name=skill_name,
        )
        surface_classification = integration_manager.managed_surface_classification(
            target=target,
            skill_name=skill_name,
        )

        surface_audit: dict[str, dict[str, Any]] = {}
        for surface_key, surface_path in integration_manager.collect_managed_surface_paths(
            target=target,
            skill_name=skill_name,
        ).items():
            surface_meta = surface_classification.get(surface_key, {})
            exists = surface_path.exists()
            audit_entry: dict[str, Any] = {
                "path": str(surface_path),
                "exists": exists,
                "group": str(surface_meta.get("group", "unclassified")),
                "required": bool(surface_meta.get("required", False)),
                "missing_markers": [],
            }
            if exists:
                try:
                    content = surface_path.read_text(encoding="utf-8")
                except Exception as exc:
                    audit_entry["read_error"] = str(exc)
                    audit_entry["missing_markers"] = ["unreadable"]
                else:
                    audit_entry["missing_markers"] = integration_manager.audit_surface_contract(
                        target,
                        surface_key,
                        surface_path,
                        content,
                    )
            surface_audit[surface_key] = audit_entry

        invalid_required_surfaces = {
            key: value
            for key, value in surface_audit.items()
            if value.get("exists") and value.get("required") and value.get("missing_markers")
        }
        invalid_optional_surfaces = {
            key: value
            for key, value in surface_audit.items()
            if value.get("exists") and not value.get("required") and value.get("missing_markers")
        }
        host_report["checks"]["contract"] = {
            "ok": not invalid_required_surfaces,
            "surfaces": surface_audit,
            "invalid_surfaces": invalid_required_surfaces,
            "invalid_optional_surfaces": invalid_optional_surfaces,
        }
        if invalid_required_surfaces:
            host_report["ready"] = False
            host_report["missing"].append("contract")
            host_report["suggestions"].append(
                "重新运行 super-dev，补齐并刷新当前宿主接入面，然后回到宿主里继续当前流程。"
            )
        if invalid_optional_surfaces:
            host_report["optional_missing"].append("contract_optional_surfaces")

        if check_integrate:
            integrate_files = surface_groups["official_project"]
            optional_integrate_files = surface_groups["optional_project"]
            if not integrate_files and integrate_no_project_note is not None:
                host_report["checks"]["integrate"] = {
                    "ok": True,
                    "files": [],
                    "optional_files": [str(item) for item in optional_integrate_files],
                    "note": integrate_no_project_note,
                }
            else:
                integrate_ok = all(path.exists() for path in integrate_files)
                host_report["checks"]["integrate"] = {
                    "ok": integrate_ok,
                    "files": [str(item) for item in integrate_files],
                    "optional_files": [str(item) for item in optional_integrate_files],
                }
                if integrate_files and not integrate_ok:
                    host_report["ready"] = False
                    host_report["missing"].append("integrate")
                    host_report["suggestions"].append(
                        "重新运行 super-dev，把当前项目需要的宿主接入文件补齐。"
                    )
            user_surface_files = surface_groups["official_user"]
            optional_user_surface_files = surface_groups["optional_user"]
            user_surfaces_ok = all(path.exists() for path in user_surface_files)
            host_report["checks"]["user_surfaces"] = {
                "ok": user_surfaces_ok,
                "files": [str(item) for item in user_surface_files],
                "optional_files": [str(item) for item in optional_user_surface_files],
                "required": False,
            }
            if user_surface_files and not user_surfaces_ok:
                host_report["optional_missing"].append("user_surfaces")
                host_report["suggestions"].append(
                    "如需跨项目复用统一宿主心智，再显式启用用户级接入面；默认项目内接入已足够。"
                )

        if check_skill and IntegrationManager.requires_skill(target):
            skill_files = surface_groups["official_skill"]
            optional_skill_files = surface_groups["optional_skill"]
            compatibility_skill_files = surface_groups["compatibility_skill"]
            all_skill_files = skill_files or optional_skill_files or compatibility_skill_files
            primary_skill_file = (
                skill_primary_file_fn(
                    target,
                    skill_files,
                    optional_skill_files,
                    compatibility_skill_files,
                )
                if skill_primary_file_fn is not None
                else (all_skill_files[0] if all_skill_files else None)
            )
            skill_path = str(primary_skill_file) if primary_skill_file is not None else ""
            surface_available = bool(skill_files)
            skill_ok = all(path.exists() for path in skill_files) if surface_available else True
            host_report["checks"]["skill"] = {
                "ok": skill_ok,
                "file": skill_path,
                "files": (
                    [str(item) for item in skill_files]
                    if skill_files
                    else ([skill_path] if skill_path else [])
                ),
                "optional_files": [str(item) for item in optional_skill_files],
                "compatibility_files": [str(item) for item in compatibility_skill_files],
                "surface_available": surface_available,
                "mode": (
                    "official-project-and-user-skill-surface"
                    if surface_available
                    else "compatibility-surface-unavailable"
                ),
            }
            if surface_available and not skill_ok:
                host_report["ready"] = False
                host_report["missing"].append("skill")
                host_report["suggestions"].append(
                    "重新运行 super-dev，确保当前宿主需要的 Super Dev Skill 已同步到用户目录。"
                )

        if target == "codex-cli":
            plugin_marketplace = project_dir / ".agents" / "plugins" / "marketplace.json"
            plugin_manifest = (
                project_dir / "plugins" / "super-dev-codex" / ".codex-plugin" / "plugin.json"
            )
            plugin_ok = plugin_marketplace.exists() and plugin_manifest.exists()
            host_report["checks"]["plugin_enhancement"] = {
                "ok": plugin_ok,
                "marketplace_file": str(plugin_marketplace),
                "plugin_manifest": str(plugin_manifest),
                "mode": "repo-marketplace-plugin-enhancement",
                "required": False,
            }
            if not plugin_ok:
                host_report["optional_missing"].append("plugin_enhancement")
        if target == "claude-code":
            plugin_marketplace = project_dir / ".claude-plugin" / "marketplace.json"
            plugin_manifest = (
                project_dir / "plugins" / "super-dev-claude" / ".claude-plugin" / "plugin.json"
            )
            plugin_ok = plugin_marketplace.exists() and plugin_manifest.exists()
            host_report["checks"]["plugin_enhancement"] = {
                "ok": plugin_ok,
                "marketplace_file": str(plugin_marketplace),
                "plugin_manifest": str(plugin_manifest),
                "mode": "repo-marketplace-plugin-enhancement",
                "required": False,
            }
            if not plugin_ok:
                host_report["optional_missing"].append("plugin_enhancement")

        if check_slash:
            required_slash_files = surface_groups["required_slash"]
            optional_slash_files = surface_groups["optional_slash"]
            compatibility_slash_files = surface_groups["compatibility_slash"]
            tracked_slash_files = (
                required_slash_files or optional_slash_files or compatibility_slash_files
            )
            if tracked_slash_files:
                project_slash_file = next(
                    (
                        path
                        for path in tracked_slash_files
                        if str(path).startswith(str(project_dir))
                    ),
                    None,
                )
                global_slash_file = next(
                    (
                        path
                        for path in tracked_slash_files
                        if not str(path).startswith(str(project_dir))
                    ),
                    None,
                )
                project_ok = bool(project_slash_file and project_slash_file.exists())
                global_ok = bool(global_slash_file and global_slash_file.exists())
                slash_ok = (
                    all(path.exists() for path in required_slash_files)
                    if required_slash_files
                    else True
                )
                if required_slash_files:
                    scope = "project" if project_ok else ("global" if global_ok else "missing")
                elif project_ok or global_ok:
                    scope = "optional"
                else:
                    scope = "not-required"
                host_report["checks"]["slash"] = {
                    "ok": slash_ok,
                    "scope": scope,
                    "project_file": str(project_slash_file) if project_slash_file else "",
                    "global_file": str(global_slash_file) if global_slash_file else "",
                    "required_files": [str(item) for item in required_slash_files],
                    "optional_files": [str(item) for item in optional_slash_files],
                    "compatibility_files": [str(item) for item in compatibility_slash_files],
                }
                if required_slash_files and not slash_ok:
                    host_report["ready"] = False
                    host_report["missing"].append("slash")
                    host_report["suggestions"].append(
                        "重新运行 super-dev，确保当前宿主的 /super-dev 入口已经写入。"
                    )
            else:
                host_report["checks"]["slash"] = {
                    "ok": True,
                    "scope": "n/a",
                    "project_file": "",
                    "global_file": "",
                    "mode": "rules-only",
                }

        host_report["injection_closure"] = build_host_injection_closure(
            host_ready=bool(host_report.get("ready", False)),
            surface_sets=surface_groups,
            managed_competition_project_paths=[
                project_dir / relative
                for relative in integration_manager.managed_competition_project_surfaces(target)
            ],
            managed_competition_user_paths=[
                integration_manager._resolve_surface_declaration(target=target, surface=relative)
                for relative in integration_manager.managed_competition_user_surfaces(target)
            ],
        )
        injection_closure = host_report["injection_closure"]
        if bool(injection_closure.get("managed_competition_project_surfaces")):
            host_report["checks"]["competition_project_surfaces"] = {
                "ok": bool(injection_closure.get("competition_project_surfaces_ready", False)),
                "files": list(injection_closure.get("managed_competition_project_surfaces", [])),
                "required": False,
            }
            if not bool(injection_closure.get("competition_project_surfaces_ready", False)):
                host_report["optional_missing"].append("competition_project_surfaces")
                host_report["suggestions"].append(
                    "如需启用 SEEAI 比赛模式，先重新运行 super-dev，补齐当前项目的 SEEAI 补充面。"
                )
        if bool(injection_closure.get("managed_competition_user_surfaces")):
            host_report["checks"]["competition_user_surfaces"] = {
                "ok": bool(injection_closure.get("competition_user_surfaces_ready", False)),
                "files": list(injection_closure.get("managed_competition_user_surfaces", [])),
                "required": False,
            }
            if not bool(injection_closure.get("competition_user_surfaces_ready", False)):
                host_report["optional_missing"].append("competition_user_surfaces")
                host_report["suggestions"].append(
                    "如需启用 SEEAI 比赛模式，先补齐当前宿主的 Super Dev SEEAI 用户级 Skill 或补充面。"
                )

        host_report["usage_profile"] = build_usage_profile_fn(integration_manager, target)
        usage_profile = host_report["usage_profile"]
        if isinstance(usage_profile, dict):
            precondition_status = str(usage_profile.get("precondition_status", "")).strip()
            precondition_label = str(usage_profile.get("precondition_label", "")).strip()
            precondition_guidance = usage_profile.get("precondition_guidance", [])
            precondition_signals = usage_profile.get("precondition_signals", {})
            precondition_items = usage_profile.get("precondition_items", [])
            host_report["preconditions"] = {
                "status": precondition_status,
                "label": precondition_label,
                "guidance": (
                    precondition_guidance if isinstance(precondition_guidance, list) else []
                ),
                "signals": precondition_signals if isinstance(precondition_signals, dict) else {},
                "items": precondition_items if isinstance(precondition_items, list) else [],
            }
            if precondition_status == "host-auth-required":
                host_report["suggestions"].append(
                    "若宿主报 Invalid API key provided，请先在宿主内完成 /auth 或更新宿主 API key 配置。"
                )
            if precondition_status == "session-restart-required":
                host_report["suggestions"].append("接入后先关闭旧宿主会话，再开一个新会话后重试。")
            if precondition_status == "project-context-required":
                host_report["suggestions"].append(
                    "确认当前聊天/终端绑定的是目标项目，再重新触发 Super Dev。"
                )

        if build_diagnosis_fn is not None:
            host_report["diagnosis"] = build_diagnosis_fn(target, host_report, integration_manager)

        report["hosts"][target] = host_report
        if not host_report["ready"]:
            report["overall_ready"] = False

    return report


def build_host_compatibility_summary(
    *,
    report: dict[str, Any],
    targets: list[str],
    check_integrate: bool,
    check_skill: bool,
    check_slash: bool,
    include_flow_metrics: bool = False,
) -> dict[str, Any]:
    enabled_checks = ["contract"]
    if check_integrate:
        enabled_checks.append("integrate")
    if check_skill and any(IntegrationManager.requires_skill(target) for target in targets):
        enabled_checks.append("skill")
    if check_slash and any(IntegrationManager.supports_slash(target) for target in targets):
        enabled_checks.append("slash")

    per_host: dict[str, dict[str, Any]] = {}
    total_passed = 0
    total_possible = 0
    ready_hosts = 0
    flow_consistent_hosts = 0
    project_default_ready_hosts = 0
    explicit_user_surface_ready_hosts = 0
    user_surface_opt_in_available_hosts = 0
    hosts = report.get("hosts", {})
    if not isinstance(hosts, dict):
        hosts = {}

    for target in targets:
        host = hosts.get(target, {})
        checks = host.get("checks", {}) if isinstance(host, dict) else {}
        if not isinstance(checks, dict):
            checks = {}
        passed = 0
        possible = len(enabled_checks)
        for check_name in enabled_checks:
            check_value = checks.get(check_name, {})
            if isinstance(check_value, dict) and bool(check_value.get("ok", False)):
                passed += 1
        score = round((passed / possible) * 100, 2) if possible > 0 else 100.0
        host_summary = {
            "score": score,
            "passed": passed,
            "possible": possible,
            "ready": bool(host.get("ready", False)) if isinstance(host, dict) else False,
        }
        if include_flow_metrics:
            flow_consistent = True
            contract_check = checks.get("contract", {})
            if not isinstance(contract_check, dict):
                flow_consistent = False
            else:
                surfaces = contract_check.get("surfaces", {})
                if isinstance(surfaces, dict):
                    for item in surfaces.values():
                        if not isinstance(item, dict):
                            continue
                        missing_markers = item.get("missing_markers", [])
                        if isinstance(missing_markers, list) and "flow" in missing_markers:
                            flow_consistent = False
                            break
            host_summary["flow_consistent"] = flow_consistent
            if flow_consistent:
                flow_consistent_hosts += 1
        per_host[target] = host_summary
        total_passed += passed
        total_possible += possible
        if bool(host.get("ready", False)) if isinstance(host, dict) else False:
            ready_hosts += 1
        injection_closure = host.get("injection_closure", {}) if isinstance(host, dict) else {}
        if isinstance(injection_closure, dict):
            if bool(injection_closure.get("project_default_ready", False)):
                project_default_ready_hosts += 1
            if bool(injection_closure.get("explicit_user_surfaces_ready", False)):
                explicit_user_surface_ready_hosts += 1
            if bool(injection_closure.get("user_surface_opt_in_available", False)):
                user_surface_opt_in_available_hosts += 1

    overall_score = round((total_passed / total_possible) * 100, 2) if total_possible > 0 else 100.0
    summary = {
        "overall_score": overall_score,
        "ready_hosts": ready_hosts,
        "project_default_ready_hosts": project_default_ready_hosts,
        "explicit_user_surface_ready_hosts": explicit_user_surface_ready_hosts,
        "user_surface_opt_in_available_hosts": user_surface_opt_in_available_hosts,
        "total_hosts": len(targets),
        "enabled_checks": enabled_checks,
        "hosts": per_host,
    }
    if include_flow_metrics:
        summary["flow_consistent_hosts"] = flow_consistent_hosts
        summary["flow_consistency_score"] = (
            round((flow_consistent_hosts / len(targets)) * 100, 2) if targets else 100.0
        )
    return summary
