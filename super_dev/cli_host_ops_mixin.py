"""CLI host operations mixin helpers."""

from __future__ import annotations

import argparse
import contextlib
import glob
import importlib.metadata
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__
from .catalogs import (
    HOST_COMMAND_CANDIDATES,
    PRIMARY_HOST_TOOL_IDS,
    host_detection_path_candidates,
    host_display_name,
    host_path_override_guide,
    host_runtime_validation_overrides,
)
from .cli_host_report_renderers import (
    render_host_compatibility_markdown,
    render_host_hardening_markdown,
    render_host_parity_onepage_markdown,
    render_host_runtime_validation_markdown,
    render_host_surface_audit_markdown,
    write_host_compatibility_report,
    write_host_hardening_report,
    write_host_runtime_validation_report,
    write_host_surface_audit_report,
)
from .compliance_governance import collect_compliance_governance_signal
from .config import ConfigManager, ProjectConfig, get_config_manager
from .host_adapters import render_manual_install_guidance
from .host_diagnostics import build_host_compatibility_summary, collect_host_diagnostics
from .host_entry_decisions import (
    build_detected_host_decision_card,
    build_host_start_guidance,
    build_no_host_decision_card,
    build_primary_repair_action,
    host_selection_reason,
    rank_host_targets,
)
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_official_pass_criteria,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from .host_registry import HostInstallMode, get_install_mode
from .host_runtime_governance import collect_layered_runtime_governance_gap
from .host_runtime_validation import (
    build_host_runtime_validation_payload,
    build_runtime_evidence_record,
    host_runtime_status_label,
    load_host_runtime_validation_state,
    update_host_runtime_validation_state,
)
from .host_session_resume import build_session_resume_card
from .host_usage_profile import serialize_host_usage_profile
from .host_workflow_context import build_host_workflow_context
from .integrations.install_manifest import record_install_manifest
from .terminal import normalize_terminal_text, output_mode_label, output_mode_reason
from .workflow_state import (
    build_host_entry_prompts,
    detect_flow_variant,
    load_framework_playbook_summary,
)


class CliHostOpsMixin:
    @staticmethod
    def _cleanup_report_paths(project_dir: Path) -> dict[str, Path]:
        report_dir = project_dir / "output" / "maintenance"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base = report_dir / f"host-cleanup-{stamp}"
        return {
            "json": base.with_suffix(".json"),
            "markdown": base.with_suffix(".md"),
        }

    @staticmethod
    def _onboard_smoke_report_paths(project_dir: Path) -> dict[str, Path]:
        report_dir = project_dir / "output" / "maintenance"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base = report_dir / f"host-onboard-smoke-{stamp}"
        return {
            "json": base.with_suffix(".json"),
            "markdown": base.with_suffix(".md"),
        }

    @staticmethod
    def _stringify_existing_paths(paths: list[Path]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key in seen or not path.exists():
                continue
            seen.add(key)
            deduped.append(key)
        return sorted(deduped)

    def _collect_uninstall_target_preview(
        self,
        *,
        integration_manager,
        skill_manager,
        target: str,
    ) -> dict[str, Any]:
        managed_surfaces = integration_manager.collect_managed_surface_paths(target=target)
        planned_surface_paths = self._stringify_existing_paths(list(managed_surfaces.values()))
        missing_surface_paths = sorted(
            {
                str(path)
                for path in managed_surfaces.values()
                if not path.exists()
            }
        )

        planned_skill_names: list[str] = []
        planned_skill_paths: list[str] = []
        planned_legacy_skill_aliases: list[str] = []
        planned_legacy_skill_paths: list[str] = []
        if skill_manager.skill_surface_available(target):
            for skill_name in skill_manager.managed_builtin_skill_names(target):
                existing_paths = self._stringify_existing_paths(
                    skill_manager.managed_skill_cleanup_paths(target, skill_name)
                )
                if not existing_paths:
                    continue
                planned_skill_names.append(skill_name)
                planned_skill_paths.extend(existing_paths)

            legacy_paths = self._stringify_existing_paths(skill_manager.legacy_skill_cleanup_paths(target))
            if legacy_paths:
                planned_legacy_skill_aliases = skill_manager.legacy_cleanup_skill_names()
                planned_legacy_skill_paths = legacy_paths

        return {
            "target": target,
            "planned_surface_paths": planned_surface_paths,
            "planned_skill_names": planned_skill_names,
            "planned_skill_paths": sorted(set(planned_skill_paths)),
            "planned_legacy_skill_aliases": planned_legacy_skill_aliases,
            "planned_legacy_skill_paths": planned_legacy_skill_paths,
            "missing_surface_paths": missing_surface_paths,
        }

    def _write_onboard_smoke_report(
        self,
        *,
        project_dir: Path,
        integration_manager,
        include_user_surfaces: bool,
        target_results: list[dict[str, Any]],
        status: str,
    ) -> dict[str, str]:
        report_paths = self._onboard_smoke_report_paths(project_dir)
        generated_at = datetime.now(timezone.utc).isoformat()
        targets_payload: list[dict[str, Any]] = []
        markdown_lines = [
            "# Host Onboard Smoke Guide",
            "",
            f"- Generated At: {generated_at}",
            f"- Project: {project_dir}",
            f"- Install Scope: {'project + user surfaces' if include_user_surfaces else 'project surfaces only'}",
            f"- Status: {status}",
            "",
        ]
        framework_playbook = load_framework_playbook_summary(project_dir)
        if isinstance(framework_playbook, dict) and framework_playbook:
            markdown_lines.extend(
                [
                    "## 框架焦点（Framework Coaching Focus）",
                    "",
                    f"- Framework: {framework_playbook.get('framework', '-')}",
                ]
            )
            modules = framework_playbook.get("implementation_modules", [])
            if isinstance(modules, list) and modules:
                markdown_lines.append(
                    "- Implementation Modules: " + "；".join(str(item) for item in modules[:4])
                )
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if isinstance(native_capabilities, list) and native_capabilities:
                markdown_lines.append(
                    "- Native Capabilities: "
                    + "；".join(str(item) for item in native_capabilities[:4])
                )
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if isinstance(validation_surfaces, list) and validation_surfaces:
                markdown_lines.append(
                    "- Validation Surfaces: "
                    + "；".join(str(item) for item in validation_surfaces[:4])
                )
            delivery_evidence = framework_playbook.get("delivery_evidence", [])
            if isinstance(delivery_evidence, list) and delivery_evidence:
                markdown_lines.append(
                    "- Delivery Evidence: "
                    + "；".join(str(item) for item in delivery_evidence[:4])
                )
            markdown_lines.append("")
        for item in target_results:
            target = str(item.get("target", "")).strip()
            if not target:
                continue
            usage = self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
            standard_first_prompt = build_host_standard_first_prompt(target)
            competition_first_prompt = build_host_competition_first_prompt(target)
            post_onboard_self_check = build_host_post_onboard_self_check(target, usage)
            official_workflow_checks = build_host_official_workflow_checks(target, usage)
            official_pass_criteria = build_host_official_pass_criteria(target, usage)
            start_playbook = build_host_start_playbook(target)
            resume_guidance = build_host_resume_guidance(target)
            adaptation_contract = (
                dict(usage.get("adaptation_contract", {}))
                if isinstance(usage.get("adaptation_contract", {}), dict)
                else {}
            )
            target_payload = {
                "target": target,
                "host_name": self._host_label(target),
                "status": "ready" if not item.get("errors") else "partial",
                "include_user_surfaces": include_user_surfaces,
                "standard_flow_first_prompt": standard_first_prompt,
                "competition_flow_first_prompt": competition_first_prompt,
                "post_onboard_self_check": post_onboard_self_check,
                "official_workflow_checks": official_workflow_checks,
                "official_pass_criteria": official_pass_criteria,
                "start_playbook": start_playbook,
                "resume_guidance": resume_guidance,
                "repair_playbook": str(usage.get("repair_playbook", "")).strip(),
                "managed_competition_project_surfaces": list(
                    usage.get("managed_competition_project_surfaces", [])
                )
                if isinstance(usage.get("managed_competition_project_surfaces", []), list)
                else [],
                "managed_competition_user_surfaces": list(
                    usage.get("managed_competition_user_surfaces", [])
                )
                if isinstance(usage.get("managed_competition_user_surfaces", []), list)
                else [],
                "framework_playbook": framework_playbook if isinstance(framework_playbook, dict) else {},
                "manifest_paths": list(item.get("manifest_paths", [])),
                "contract_failures": list(item.get("contract_failures", [])),
                "auto_repair_actions": dict(item.get("auto_repair_actions", {}))
                if isinstance(item.get("auto_repair_actions", {}), dict)
                else {},
                "adaptation_contract": adaptation_contract,
            }
            targets_payload.append(target_payload)

            markdown_lines.extend(
                [
                    f"## {self._host_label(target)}",
                    "",
                    f"- Status: {target_payload['status']}",
                    f"- Standard Flow First Prompt: `{standard_first_prompt}`",
                    f"- Competition Flow First Prompt: `{competition_first_prompt}`",
                    f"- Install Scope: {'project + user surfaces' if include_user_surfaces else 'project surfaces only'}",
                    "",
                    "### Start Playbook",
                ]
            )
            if start_playbook:
                markdown_lines.extend(f"- {line}" for line in start_playbook)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Post-Onboard Self-Check"])
            if post_onboard_self_check:
                markdown_lines.extend(f"- {line}" for line in post_onboard_self_check)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Official Workflow Checks"])
            if official_workflow_checks:
                markdown_lines.extend(f"- {line}" for line in official_workflow_checks)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Official Pass Criteria"])
            if official_pass_criteria:
                markdown_lines.extend(f"- {line}" for line in official_pass_criteria)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Resume Guidance"])
            if resume_guidance:
                markdown_lines.extend(f"- {line}" for line in resume_guidance)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Repair Playbook"])
            repair_playbook = target_payload["repair_playbook"]
            markdown_lines.append(repair_playbook or "-")
            if target_payload["managed_competition_project_surfaces"]:
                markdown_lines.extend(["", "### SEEAI Project Supplements"])
                markdown_lines.extend(
                    f"- `{line}`"
                    for line in target_payload["managed_competition_project_surfaces"]
                )
            if target_payload["managed_competition_user_surfaces"]:
                markdown_lines.extend(["", "### SEEAI User Supplements"])
                markdown_lines.extend(
                    f"- `{line}`"
                    for line in target_payload["managed_competition_user_surfaces"]
                )
            if isinstance(target_payload["framework_playbook"], dict) and target_payload["framework_playbook"]:
                markdown_lines.extend(["", "### Framework Coaching"])
                markdown_lines.append(
                    f"- Framework: {target_payload['framework_playbook'].get('framework', '-')}"
                )
                modules = target_payload["framework_playbook"].get("implementation_modules", [])
                if isinstance(modules, list) and modules:
                    markdown_lines.append(
                        "- Implementation Modules: " + "；".join(str(line) for line in modules[:4])
                    )
                validation = target_payload["framework_playbook"].get("validation_surfaces", [])
                if isinstance(validation, list) and validation:
                    markdown_lines.append(
                        "- Validation Surfaces: " + "；".join(str(line) for line in validation[:4])
                    )
                evidence = target_payload["framework_playbook"].get("delivery_evidence", [])
                if isinstance(evidence, list) and evidence:
                    markdown_lines.append(
                        "- Delivery Evidence: " + "；".join(str(line) for line in evidence[:4])
                    )
            if target_payload["manifest_paths"]:
                markdown_lines.extend(["", "### Written Surfaces"])
                markdown_lines.extend(f"- `{line}`" for line in target_payload["manifest_paths"])
            if target_payload["contract_failures"]:
                markdown_lines.extend(["", "### Contract Failures"])
                markdown_lines.extend(f"- {line}" for line in target_payload["contract_failures"])
            markdown_lines.append("")

        payload = {
            "generated_at": generated_at,
            "project_dir": str(project_dir),
            "status": status,
            "install_scope": "project+user-surfaces" if include_user_surfaces else "project-only",
            "framework_playbook": framework_playbook if isinstance(framework_playbook, dict) else {},
            "targets": targets_payload,
            "report_files": {name: str(path) for name, path in report_paths.items()},
        }
        report_paths["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report_paths["markdown"].write_text("\n".join(markdown_lines).rstrip() + "\n", encoding="utf-8")
        return {name: str(path) for name, path in report_paths.items()}

    def _write_cleanup_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        report_paths = self._cleanup_report_paths(project_dir)
        report_paths["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_lines = [
            "# Host Cleanup Report",
            "",
            f"- Generated At: {payload.get('timestamp', '-')}",
            f"- Status: {payload.get('status', '-')}",
            f"- Dry Run: {'yes' if payload.get('dry_run', False) else 'no'}",
            f"- Summary: {payload.get('summary', '-')}",
            "",
        ]
        for item in payload.get("targets", []):
            if not isinstance(item, dict):
                continue
            target = str(item.get("target", "")).strip() or "-"
            markdown_lines.extend([f"## {self._host_label(target)}", ""])
            planned_surface_paths = list(item.get("planned_surface_paths", []))
            planned_skill_names = list(item.get("planned_skill_names", []))
            planned_legacy_skill_aliases = list(item.get("planned_legacy_skill_aliases", []))
            removed_paths = list(item.get("removed_paths", []))
            removed_skills = list(item.get("removed_skills", []))
            removed_legacy_skill_aliases = list(item.get("removed_legacy_skill_aliases", []))
            missing_surface_paths = list(item.get("missing_surface_paths", []))
            errors = list(item.get("errors", []))
            if payload.get("dry_run", False):
                markdown_lines.append(f"- Planned Surface Cleanup: {len(planned_surface_paths)}")
                markdown_lines.append(f"- Planned Skill Cleanup: {', '.join(planned_skill_names) or '-'}")
                markdown_lines.append(
                    f"- Planned Legacy Alias Cleanup: {', '.join(planned_legacy_skill_aliases) or '-'}"
                )
            else:
                markdown_lines.append(f"- Removed Surface Paths: {len(removed_paths)}")
                markdown_lines.append(f"- Removed Skills: {', '.join(removed_skills) or '-'}")
                markdown_lines.append(
                    f"- Removed Legacy Aliases: {', '.join(removed_legacy_skill_aliases) or '-'}"
                )
            if planned_surface_paths:
                markdown_lines.extend(["", "### Planned Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in planned_surface_paths)
            if item.get("planned_skill_paths"):
                markdown_lines.extend(["", "### Planned Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["planned_skill_paths"])
            if item.get("planned_legacy_skill_paths"):
                markdown_lines.extend(["", "### Planned Legacy Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["planned_legacy_skill_paths"])
            if removed_paths:
                markdown_lines.extend(["", "### Removed Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in removed_paths)
            if item.get("removed_skill_paths"):
                markdown_lines.extend(["", "### Removed Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["removed_skill_paths"])
            if item.get("removed_legacy_skill_paths"):
                markdown_lines.extend(["", "### Removed Legacy Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["removed_legacy_skill_paths"])
            if missing_surface_paths:
                markdown_lines.extend(["", "### Missing Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in missing_surface_paths)
            if errors:
                markdown_lines.extend(["", "### Errors"])
                markdown_lines.extend(f"- {line}" for line in errors)
            markdown_lines.append("")
        report_paths["markdown"].write_text(
            "\n".join(markdown_lines).rstrip() + "\n",
            encoding="utf-8",
        )
        return {name: str(path) for name, path in report_paths.items()}

    @staticmethod
    def _include_user_surfaces(args) -> bool:
        return bool(getattr(args, "with_user_surfaces", False))

    @staticmethod
    def _display_final_trigger_for_profile(profile) -> str:
        if getattr(profile, "host", "") == "codex":
            return "App/Desktop: /super-dev | 回退: super-dev: 你的需求"
        if getattr(profile, "host", "") == "codex-cli":
            return "CLI: $super-dev | 回退: super-dev: 你的需求"
        return str(profile.trigger_command).replace("<需求描述>", "你的需求")

    def _is_manual_install_host(self, target: str | None) -> bool:
        return bool(target) and get_install_mode(target) == HostInstallMode.MANUAL

    def _print_manual_install_host_guidance(self, *, target: str, command_name: str) -> int:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        docs = list(getattr(integration_manager, "OFFICIAL_DOCS_INDEX", {}).get(target, ()))
        host_name = self._host_label(target)
        guidance = render_manual_install_guidance(
            host_id=target,
            command_name=command_name,
            docs=docs,
        )
        if guidance is None:
            return 0
        if not RICH_AVAILABLE:
            self.console.print(f"{host_name} 不走 super-dev {command_name} 统一安装流。")
            plain = str(guidance.get("plain_fallback", "")).strip()
            if plain:
                self.console.print(plain)
            return 0
        panel_kwargs: dict[str, Any] = {
            "title": str(guidance.get("title", f"{host_name} 手动安装")),
            "border_style": str(guidance.get("border_style", "yellow")),
        }
        self.console.print(
            Panel(
                "\n".join(guidance.get("lines", [])),
                **panel_kwargs,
            )
        )
        return 0

    def _collect_runtime_install_health(self) -> dict[str, Any]:
        current_module_path = Path(sys.modules[__name__.rsplit(".", 1)[0]].__file__).resolve()
        installed_dist_version = ""
        metadata_error = ""
        try:
            installed_dist_version = importlib.metadata.version("super-dev")
        except importlib.metadata.PackageNotFoundError:
            installed_dist_version = ""
        except Exception as exc:
            metadata_error = str(exc)

        site_packages_entries = [
            Path(entry).resolve()
            for entry in sys.path
            if isinstance(entry, str) and "site-packages" in entry
        ]
        stale_package_dirs: list[str] = []
        dist_info_versions: list[str] = []
        editable_versions: list[str] = []
        dist_info_pattern = re.compile(r"super_dev-(?P<version>.+)\.dist-info$")
        editable_pattern = re.compile(r"__editable__\.super_dev-(?P<version>.+)\.pth$")
        for site_packages in site_packages_entries:
            package_dir = site_packages / "super_dev"
            if package_dir.exists():
                init_file = package_dir / "__init__.py"
                if init_file.exists() and init_file.resolve() != current_module_path:
                    stale_package_dirs.append(str(package_dir))
            for dist_info in site_packages.glob("super_dev-*.dist-info"):
                match = dist_info_pattern.search(dist_info.name)
                if match:
                    dist_info_versions.append(match.group("version"))
            for editable in site_packages.glob("__editable__.super_dev-*.pth"):
                match = editable_pattern.search(editable.name)
                if match:
                    editable_versions.append(match.group("version"))

        dist_info_versions = sorted(set(dist_info_versions))
        editable_versions = sorted(set(editable_versions))
        warnings: list[str] = []
        remediation: list[str] = []

        if stale_package_dirs:
            warnings.append("检测到 site-packages 中残留的 super_dev 实体目录，可能覆盖当前版本。")
            remediation.append("删除旧的 site-packages/super_dev 目录后重新执行 pip install -e .")
        if len(dist_info_versions) > 1:
            warnings.append(
                "检测到多个 super-dev dist-info 版本并存: " + ", ".join(dist_info_versions)
            )
            remediation.append("清理旧的 super_dev-*.dist-info 残留，只保留当前版本。")
        if len(editable_versions) > 1:
            warnings.append("检测到多个 editable 安装记录并存: " + ", ".join(editable_versions))
            remediation.append("清理旧的 __editable__.super_dev-*.pth 和 finder 文件后重新安装。")
        if installed_dist_version and installed_dist_version != __version__:
            warnings.append(
                f"包元数据版本 {installed_dist_version} 与当前运行版本 {__version__} 不一致。"
            )
            remediation.append("重新安装 super-dev，确保脚本与导入版本一致。")
        if metadata_error:
            warnings.append(f"读取安装元数据失败: {metadata_error}")

        return {
            "healthy": not warnings,
            "current_version": __version__,
            "current_module_path": str(current_module_path),
            "installed_dist_version": installed_dist_version,
            "stale_package_dirs": stale_package_dirs,
            "dist_info_versions": dist_info_versions,
            "editable_versions": editable_versions,
            "warnings": warnings,
            "remediation": remediation,
        }

    def _print_runtime_install_health(
        self, runtime_health: dict[str, Any], *, indent: str = ""
    ) -> None:
        status = (
            "[green]正常[/green]"
            if runtime_health.get("healthy", False)
            else "[yellow]异常[/yellow]"
        )
        self.console.print(
            f"{indent}[cyan]运行时安装[/cyan]: {status} 版本 {runtime_health.get('current_version', '-')}"
        )
        self.console.print(
            f"{indent}[dim]模块路径: {runtime_health.get('current_module_path', '-')}[/dim]"
        )
        installed_dist_version = runtime_health.get("installed_dist_version", "")
        if installed_dist_version:
            self.console.print(f"{indent}[dim]安装元数据版本: {installed_dist_version}[/dim]")
        for warning in runtime_health.get("warnings", []):
            self.console.print(f"{indent}[yellow]- {warning}[/yellow]")
        for action in runtime_health.get("remediation", []):
            self.console.print(f"{indent}[dim]修复: {action}[/dim]")

    def _auto_fix_runtime_install(self, runtime_health: dict[str, Any]) -> None:
        """自动清理旧版本残留并重新安装。"""
        import shutil

        fixed: list[str] = []
        failed: list[str] = []
        current_version = runtime_health.get("current_version", __version__)

        # 1. 删除旧的 super_dev 实体目录
        for stale_dir in runtime_health.get("stale_package_dirs", []):
            try:
                shutil.rmtree(stale_dir)
                fixed.append(f"已删除残留目录: {stale_dir}")
            except Exception as exc:
                failed.append(f"无法删除 {stale_dir}: {exc}")

        # 2. 清理多余的 editable pth 文件（只保留当前版本）
        editable_versions = runtime_health.get("editable_versions", [])
        if len(editable_versions) > 1:
            site_packages_entries = [
                Path(entry).resolve()
                for entry in sys.path
                if isinstance(entry, str) and "site-packages" in entry
            ]
            for site_packages in site_packages_entries:
                for pth_file in site_packages.glob("__editable__.super_dev-*.pth"):
                    if current_version not in pth_file.name:
                        try:
                            pth_file.unlink()
                            fixed.append(f"已删除旧 pth: {pth_file.name}")
                        except Exception as exc:
                            failed.append(f"无法删除 {pth_file.name}: {exc}")

        # 3. 清理多余的 dist-info（只保留当前版本）
        dist_info_versions = runtime_health.get("dist_info_versions", [])
        if len(dist_info_versions) > 1:
            site_packages_entries = [
                Path(entry).resolve()
                for entry in sys.path
                if isinstance(entry, str) and "site-packages" in entry
            ]
            for site_packages in site_packages_entries:
                for dist_info in site_packages.glob("super_dev-*.dist-info"):
                    if current_version not in dist_info.name:
                        try:
                            shutil.rmtree(dist_info)
                            fixed.append(f"已删除旧 dist-info: {dist_info.name}")
                        except Exception as exc:
                            failed.append(f"无法删除 {dist_info.name}: {exc}")

        if fixed:
            for msg in fixed:
                self.console.print(f"  [green]✓[/green] {msg}")
        if failed:
            for msg in failed:
                self.console.print(f"  [red]✗[/red] {msg}")
        if not fixed and not failed:
            self.console.print("  [dim]未发现需要清理的文件。[/dim]")
        elif fixed and not failed:
            self.console.print("  [green]修复完成。[/green]")

    def _host_label(self, target: str) -> str:
        return host_display_name(target)

    def _host_path_override_key(self, target: str) -> str:
        return str(host_path_override_guide(target).get("env_key", ""))

    def _custom_host_path_override_hint(self, target: str | None = None) -> str:
        if target:
            return str(host_path_override_guide(target).get("hint", ""))
        return str(host_path_override_guide("codex-cli").get("hint", ""))

    def _format_detection_reason(self, reason: str) -> str:
        source, _, value = str(reason).partition(":")
        source_labels = {
            "cmd": "命令命中",
            "path": "默认安装路径",
            "env": "自定义路径覆盖",
            "registry": "Windows 注册信息",
            "shim": "Windows shim / 包管理器目录",
        }
        label = source_labels.get(source, source or "检测来源")
        return f"{label}: {value}" if value else label

    def _explain_detection_details(
        self, detected_meta: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        explained: dict[str, list[str]] = {}
        for host, reasons in detected_meta.items():
            explained[host] = [self._format_detection_reason(item) for item in reasons]
        return explained

    def _host_runtime_checklist(
        self, *, target: str, usage: dict[str, Any], project_dir: Path | None = None
    ) -> list[str]:
        lead = [
            build_host_start_guidance(target=target, usage=usage, include_resume_hint=False),
            *build_host_start_playbook(target),
            *build_host_official_workflow_checks(target, usage),
        ]
        trigger = str(usage.get("final_trigger", "")).strip() or "-"
        common = [
            f"在宿主中使用最终触发命令进入 Super Dev 流水线：{trigger}",
            "确认首轮响应明确进入 research，而不是直接开始编码。",
            "确认真实写入 output/*-research.md、output/*-prd.md、output/*-architecture.md、output/*-uiux.md。",
            "确认三文档完成后暂停等待用户确认，而不是直接继续实现。",
            "确认文档确认后能继续进入 Spec、前端运行验证、后端与交付阶段。",
        ]
        if project_dir is not None:
            framework_playbook = load_framework_playbook_summary(project_dir)
            if framework_playbook:
                common.extend(
                    [
                        f"确认当前项目按 {framework_playbook.get('framework', '跨平台框架')} playbook 执行，而不是按普通 Web 假设实现。",
                        "确认宿主已落实框架专项原生能力面，而不是只完成通用页面实现。",
                        "确认宿主已按框架专项必验场景完成真实验证，并沉淀交付证据。",
                    ]
                )
        overrides = host_runtime_validation_overrides(target)
        return [*lead, *overrides.get("runtime_checklist", []), *common]

    def _host_runtime_pass_criteria(
        self, *, target: str, usage: dict[str, Any], project_dir: Path | None = None
    ) -> list[str]:
        common = [
            "首轮响应符合 Super Dev 首轮契约。",
            "关键文档真实落盘到项目目录。",
            "确认门真实生效。",
            "后续恢复路径可用。",
        ]
        if project_dir is not None and load_framework_playbook_summary(project_dir):
            common.append("跨平台框架专项能力、必验场景与交付证据均已通过真人验收。")
        overrides = host_runtime_validation_overrides(target)
        return [
            *build_host_official_pass_criteria(target, usage),
            *overrides.get("pass_criteria", []),
            *common,
        ]

    def _host_resume_checklist(self, *, target: str, project_dir: Path | None = None) -> list[str]:
        common = [
            "重开宿主或新开会话后，使用恢复探针而不是普通闲聊进入当前流程。",
            "确认宿主先读取 `.super-dev/SESSION_BRIEF.md`，并继续当前流程而不是重新开始。",
            "确认用户继续说“改一下 / 补充 / 继续改 / 确认 / 通过”时，宿主仍然留在当前 Super Dev 流程内。",
        ]
        if project_dir is not None:
            framework_playbook = load_framework_playbook_summary(project_dir)
            if framework_playbook:
                common.append(
                    f"恢复后继续实现或返工时，仍然遵守 {framework_playbook.get('framework', '跨平台框架')} 的专项 playbook。"
                )
        overrides = host_runtime_validation_overrides(target)
        return [
            *build_host_resume_guidance(target),
            *overrides.get("resume_checklist", []),
            *common,
        ]

    def _host_resume_probe_prompt(self, *, project_dir: Path, target: str) -> str:
        if not self._project_has_super_dev_context(project_dir):
            return ""
        return self._build_host_continue_prompt(project_dir=project_dir, target=target)

    def _resolve_onboard_targets(
        self,
        *,
        available_targets: list[str],
        host: str | None,
        all_targets: bool,
        non_interactive: bool,
    ) -> list[str]:
        targets: list[str] = []
        if all_targets:
            return available_targets
        if host:
            return [host]
        if non_interactive:
            return available_targets

        interactive_targets = self._interactive_host_selector(available_targets=available_targets)
        if interactive_targets is not None:
            return interactive_targets

        self._render_host_selection_guide(available_targets=available_targets)
        raw = input("宿主选择: ").strip()
        if not raw:
            return available_targets
        try:
            selected_indices = [int(item.strip()) for item in raw.split(",") if item.strip()]
        except ValueError:
            raise ValueError("输入无效，请输入数字编号（如 1,3）")
        for index in selected_indices:
            if index < 1 or index > len(available_targets):
                raise ValueError(f"编号超出范围: {index}")

        seen = set()
        for index in selected_indices:
            target = available_targets[index - 1]
            if target in seen:
                continue
            seen.add(target)
            targets.append(target)
        return targets

    def _super_dev_ascii_banner(self) -> str:
        return (
            "  ____                        ____             \n"
            " / ___| _   _ _ __   ___ _ __|  _ \\  _____   __\n"
            " \\___ \\| | | | '_ \\ / _ \\ '__| | | |/ _ \\ \\ / /\n"
            "  ___) | |_| | |_) |  __/ |  | |_| |  __/\\ V / \n"
            " |____/ \\__,_| .__/ \\___|_|  |____/ \\___| \\_/  \n"
            "             |_|                               "
        )

    def _read_single_key(self) -> str:
        if os.name == "nt":
            import msvcrt

            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                special = msvcrt.getwch()
                return {
                    "H": "UP",
                    "P": "DOWN",
                }.get(special, special)
            if key == "\r":
                return "ENTER"
            if key == " ":
                return "SPACE"
            if key == "\x1b":
                return "ESC"
            return key

        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            first = sys.stdin.read(1)
            if first == "\x1b":
                second = sys.stdin.read(1)
                if second == "[":
                    third = sys.stdin.read(1)
                    return {
                        "A": "UP",
                        "B": "DOWN",
                    }.get(third, "ESC")
                return "ESC"
            if first in ("\r", "\n"):
                return "ENTER"
            if first == " ":
                return "SPACE"
            return first
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _interactive_host_selector(self, *, available_targets: list[str]) -> list[str] | None:
        from .integrations import IntegrationManager

        if not RICH_AVAILABLE:
            return None
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None

        integration_manager = IntegrationManager(Path.cwd())
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        selected: set[str] = set(detected_targets)
        cursor = 0
        status_message = ""

        def renderable() -> Group:
            # 获取终端高度，计算可显示的行数
            try:
                term_height = self.console.size.height
            except Exception:
                term_height = 24
            try:
                term_width = self.console.size.width
            except Exception:
                term_width = 80
            max_visible = max(5, term_height - 10)
            compact = term_width < 100

            subtitle = "Space 勾选  Enter 安装  U 卸载  ↑↓ 移动  A 全选  R 清空  Esc 取消"
            header = Panel(
                normalize_terminal_text(subtitle),
                title="Super Dev",
                expand=True,
                padding=(0, 1),
            )

            table = Table(show_header=True, header_style="bold cyan", expand=True, padding=(0, 1))
            table.add_column("", max_width=3, justify="center")
            table.add_column("#", max_width=3, style="cyan", justify="center")
            table.add_column("宿主", style="bold", ratio=3)
            table.add_column("认证", ratio=2)
            if not compact:
                table.add_column("触发", ratio=2)

            # 滚动窗口：只显示光标附��的 max_visible 行
            total = len(available_targets)
            if total <= max_visible:
                start, end = 0, total
            else:
                half = max_visible // 2
                start = max(0, cursor - half)
                end = start + max_visible
                if end > total:
                    end = total
                    start = max(0, end - max_visible)

            for idx in range(start, end):
                target = available_targets[idx]
                profile = integration_manager.get_adapter_profile(target)
                is_manual = self._is_manual_install_host(target)
                selected_mark = "[✓]" if target in selected else "[○]"
                pointer = " > " if idx == cursor else "   "
                host_label = Text()
                host_label.append(
                    f"{selected_mark} ", style="green" if target in selected else "dim"
                )
                display_name = self._host_label(target)
                if is_manual:
                    display_name += " (手动)"
                host_label.append(display_name, style="bold white" if idx == cursor else "bold")
                row: list[object] = [pointer, str(idx + 1), host_label, profile.certification_label]
                if not compact:
                    trigger = (
                        "/super-dev" if integration_manager.supports_slash(target) else "super-dev:"
                    )
                    row.append(trigger)
                table.add_row(*row)

            # 滚动指示器
            scroll_info = ""
            if total > max_visible:
                if start > 0:
                    scroll_info += f"  ↑ {start}"
                if end < total:
                    scroll_info += f"  ↓ {total - end}"

            selected_names = [self._host_label(t) for t in available_targets if t in selected]
            selected_text = ", ".join(selected_names) if selected_names else "未选择"
            footer = Text()
            footer.append(f"已选 ({len(selected)}/{total}): ", style="cyan")
            footer.append(selected_text, style="bold white")
            if scroll_info:
                footer.append(scroll_info, style="dim")

            parts: list[object] = [header, table, footer]
            if status_message:
                parts.append(Text(status_message, style="yellow"))
            return Group(*parts)

        with Live(
            renderable(),
            console=self.console,
            refresh_per_second=8,
            transient=True,
            auto_refresh=False,
        ) as live:
            while True:
                key = self._read_single_key()
                status_message = ""
                if key == "UP":
                    cursor = (cursor - 1) % len(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key == "DOWN":
                    cursor = (cursor + 1) % len(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key == "SPACE":
                    target = available_targets[cursor]
                    if target in selected:
                        selected.remove(target)
                    else:
                        selected.add(target)
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("a", "A"):
                    selected = set(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("c", "C"):
                    selected = {
                        target
                        for target in available_targets
                        if integration_manager.get_adapter_profile(target).category == "cli"
                    }
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("i", "I"):
                    selected = {
                        target
                        for target in available_targets
                        if integration_manager.get_adapter_profile(target).category == "ide"
                    }
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("r", "R"):
                    selected.clear()
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("u", "U"):
                    if not selected:
                        status_message = "请先选中要卸载的宿主"
                        live.update(renderable(), refresh=True)
                        continue
                    # 卸载选中宿主的 super-dev 集成
                    from .skills import SkillManager

                    skill_manager = SkillManager(Path.cwd())
                    uninstalled_count = 0
                    for target in sorted(selected):
                        try:
                            removed = integration_manager.remove(target=target)
                            if removed:
                                uninstalled_count += len(removed)
                        except Exception:
                            pass
                        try:
                            if skill_manager.skill_surface_available(target):
                                for skill_name in skill_manager.managed_builtin_skill_names(target):
                                    try:
                                        skill_manager.uninstall(skill_name, target)
                                        uninstalled_count += 1
                                    except FileNotFoundError:
                                        continue
                                uninstalled_count += len(
                                    skill_manager.cleanup_legacy_skill_aliases(target)
                                )
                        except Exception:
                            pass
                    status_message = (
                        f"已从 {len(selected)} 个宿主卸载 Super Dev（{uninstalled_count} 个文件）"
                    )
                    selected.clear()
                    live.update(renderable(), refresh=True)
                    continue
                if key == "ENTER":
                    chosen = [target for target in available_targets if target in selected]
                    if chosen:
                        return chosen
                    status_message = "请至少选择一个宿主"
                    live.update(renderable(), refresh=True)
                    continue
                if key == "ESC":
                    raise ValueError("已取消宿主选择")
                live.update(renderable(), refresh=True)

    def _build_install_summary(self, *, available_targets: list[str]) -> str:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        codex_hosts = [target for target in available_targets if target in {"codex", "codex-cli"}]
        slash_hosts = [
            target
            for target in available_targets
            if integration_manager.supports_slash(target) and target not in codex_hosts
        ]
        text_hosts = [
            target
            for target in available_targets
            if not integration_manager.supports_slash(target) and target not in codex_hosts
        ]
        parts: list[str] = []
        if slash_hosts:
            parts.append(
                f"slash 宿主 ({len(slash_hosts)}): "
                + ", ".join(self._host_label(target) for target in slash_hosts)
            )
        if codex_hosts:
            parts.append(
                f"Codex skill 宿主 ({len(codex_hosts)}): "
                + ", ".join(self._host_label(target) for target in codex_hosts)
                + "（App/Desktop 用 `/super-dev`，CLI 用 `$super-dev`）"
            )
        if text_hosts:
            parts.append(
                f"text 宿主 ({len(text_hosts)}): "
                + ", ".join(self._host_label(target) for target in text_hosts)
            )
        return "\n".join(parts)

    def _render_host_selection_guide(self, *, available_targets: list[str]) -> None:
        from .integrations import IntegrationManager

        if not RICH_AVAILABLE:
            self.console.print("[cyan]请选择宿主 AI Coding 工具（可多选）:[/cyan]")
            for idx, target in enumerate(available_targets, 1):
                self.console.print(f"  {idx}. {self._host_label(target)}")
            self.console.print("[dim]输入编号（逗号分隔），直接回车表示全部[/dim]")
            return

        integration_manager = IntegrationManager(Path.cwd())
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        width = self.console.width
        narrow = width < 60
        compact = width < 100

        intro = (
            f"当前版本内置 {len(available_targets)} 个宿主适配。\n"
            "slash 宿主: /super-dev  |  text 宿主: super-dev:  |  Codex: $super-dev"
        )
        self.console.print(Panel(intro, title="Super Dev 安装向导", padding=(0, 1), expand=True))

        table = Table(show_header=True, header_style="bold cyan", expand=True, padding=(0, 1))
        table.add_column("#", style="cyan", max_width=3, justify="center")
        table.add_column("宿主", style="bold", ratio=3)
        table.add_column("认证", ratio=2)
        if not narrow:
            table.add_column("触发", ratio=2)
        if not compact:
            table.add_column("检测", max_width=6, justify="center")

        for idx, target in enumerate(available_targets, 1):
            profile = integration_manager.get_adapter_profile(target)
            is_manual = self._is_manual_install_host(target)
            if target == "codex-cli":
                trigger = "$super-dev"
            elif target == "codex":
                trigger = "/super-dev"
            else:
                trigger = (
                    "/super-dev" if integration_manager.supports_slash(target) else "super-dev:"
                )
            label = self._host_label(target)
            if is_manual:
                label = f"{label} [yellow](手动)[/yellow]"
            row: list[str] = [str(idx), label, profile.certification_label]
            if not narrow:
                row.append(trigger)
            if not compact:
                detected = "✓" if target in detected_targets else ""
                row.append(detected)
            table.add_row(*row)
        self.console.print(table)
        self.console.print("[dim]输入编号（逗号分隔），直接回车表示全部[/dim]")

    def _render_install_intro(self, *, args) -> None:
        from .integrations import IntegrationManager

        runtime_health = self._collect_runtime_install_health()
        if not RICH_AVAILABLE:
            self.console.print("[cyan]Super Dev 安装入口[/cyan]")
            self.console.print("宿主负责编码与模型调用；Super Dev 负责流程、门禁、审计与交付标准。")
            self.console.print("终端只负责接入；真正开发回宿主里，复制第一句并按 smoke guide 验收。")
            self.console.print(
                "接入完成后，slash 宿主优先输入 /super-dev；非 slash 宿主输入 super-dev: 或 super-dev："
            )
            self.console.print("默认只写当前项目内接入面；如需用户级协议面，请显式加 --with-user-surfaces。")
            if not runtime_health.get("healthy", False):
                self.console.print(
                    "[yellow]检测到 super-dev 运行时安装残留，建议先执行 doctor 检查。[/yellow]"
                )
            return

        integration_manager = IntegrationManager(Path.cwd())
        available_targets = self._public_host_targets(integration_manager=integration_manager)
        lines = [
            "[bold]标准模式[/bold]  /super-dev 你的需求  |  super-dev: 你的需求",
            "[bold]赛事模式[/bold]  /super-dev-seeai 你的需求  |  super-dev-seeai: 你的需求",
            "",
            self._build_install_summary(available_targets=available_targets),
            "终端只负责接入；真正开发回宿主里，复制第一句并按 smoke guide 验收。",
            "默认只写当前项目内接入面；如需跨项目共用用户级协议面，再显式加 --with-user-surfaces。",
        ]
        if getattr(args, "auto", False):
            lines.append("当前模式: 自动检测宿主。")
        elif getattr(args, "host", None):
            lines.append(f"当前模式: 仅接入 {self._host_label(args.host)}。")
        elif getattr(args, "all", False):
            lines.append("当前模式: 接入全部宿主。")
        self.console.print(Panel("\n".join(lines), title="Super Dev", padding=(1, 1), expand=True))
        if not runtime_health.get("healthy", False):
            self.console.print("[yellow]检测到旧版本残留，正在自动清理...[/yellow]")
            self._auto_fix_runtime_install(runtime_health)
            self.console.print("")

        # After runtime health fix, clean up legacy skills globally + refresh outdated
        try:
            from .skills import SkillManager

            cleaned = SkillManager.cleanup_all_legacy()
            if cleaned:
                for path in cleaned:
                    self.console.print(f"  [green]✓[/green] 已清理旧 Skill: {path}")
        except Exception:
            pass
        self._auto_refresh_outdated_skills()

    def _auto_refresh_outdated_skills(self) -> None:
        """Silently refresh any installed skills that have outdated versions."""
        from .skills import SkillManager

        try:
            skill_manager = SkillManager(Path.cwd())
            for target, path_str in {
                **SkillManager.OFFICIAL_TARGET_PATHS,
                **SkillManager.OBSERVED_TARGET_PATHS,
            }.items():
                target_path = Path(path_str).expanduser()
                skill_md = target_path / "super-dev" / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8")
                    if f"version: {__version__}" not in content:
                        try:
                            skill_manager.install(source="super-dev", target=target, force=True)
                        except Exception:
                            pass
        except Exception:
            pass

    def _detect_host_targets(
        self,
        *,
        available_targets: list[str],
    ) -> tuple[list[str], dict[str, list[str]]]:
        detected: list[str] = []
        details: dict[str, list[str]] = {}

        for target in available_targets:
            reasons: list[str] = []

            for command in HOST_COMMAND_CANDIDATES.get(target, []):
                if shutil.which(command):
                    reasons.append(f"cmd:{command}")
                    break

            for source, candidate in host_detection_path_candidates(target):
                if glob.glob(candidate):
                    reasons.append(f"{source}:{candidate}")
                    break

            if reasons:
                detected.append(target)
                details[target] = reasons

        return detected, details

    # Families where IDE and CLI targets share the same config directories.
    # When both are detected, prefer the CLI variant (more complete integration).
    _HOST_FAMILIES: list[tuple[str, str]] = [
        ("cursor-cli", "cursor"),
        ("kiro-cli", "kiro"),
        ("qoder-cli", "qoder"),
        ("codebuddy-cli", "codebuddy"),
    ]

    def _deduplicate_host_family(self, detected: list[str]) -> list[str]:
        """When both CLI and IDE variants of the same host are detected, keep only CLI."""
        result = list(detected)
        for cli_variant, ide_variant in self._HOST_FAMILIES:
            if cli_variant in result and ide_variant in result:
                result.remove(ide_variant)
        return result

    def _collect_configured_host_targets(
        self,
        *,
        project_dir: Path,
        available_targets: list[str],
    ) -> list[str]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        configured: list[str] = []
        skill_manager = SkillManager(project_dir)
        for target in available_targets:
            integration_files = IntegrationManager.TARGETS[target].files

            has_integration = any(
                (project_dir / relative).exists() for relative in integration_files
            )
            if IntegrationManager.supports_slash(target):
                project_slash_exists = IntegrationManager.resolve_slash_command_path(
                    target=target,
                    scope="project",
                    project_dir=project_dir,
                ).exists()
                global_slash_exists = IntegrationManager.resolve_slash_command_path(
                    target=target,
                    scope="global",
                ).exists()
            else:
                project_slash_exists = False
                global_slash_exists = False
            has_slash = project_slash_exists or global_slash_exists
            has_skill = False
            if IntegrationManager.requires_skill(target):
                try:
                    installed = set(skill_manager.list_installed(target))
                    managed = set(skill_manager.managed_builtin_skill_names(target))
                    has_skill = bool(installed & managed)
                except ValueError:
                    has_skill = False
            if has_integration or has_slash or has_skill:
                configured.append(target)
        return configured

    def _is_env_truthy(self, key: str) -> bool:
        value = os.getenv(key, "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _ensure_pipeline_host_ready(self, *, project_dir: Path, config: ProjectConfig) -> bool:
        from .integrations import IntegrationManager

        if self._is_env_truthy("SUPER_DEV_ALLOW_NO_HOST"):
            self.console.print("[dim]检测到 SUPER_DEV_ALLOW_NO_HOST=1，跳过宿主硬门禁[/dim]")
            return True

        available_targets = [item.name for item in IntegrationManager(project_dir).list_targets()]
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        configured_targets = self._collect_configured_host_targets(
            project_dir=project_dir,
            available_targets=available_targets,
        )

        if config.host_profile_enforce_selected and config.host_profile_targets:
            candidate_targets = [
                item for item in config.host_profile_targets if item in available_targets
            ]
        else:
            candidate_targets = sorted(set(configured_targets))

        candidate_targets = [
            target for target in candidate_targets if not self._is_manual_install_host(target)
        ]

        if not candidate_targets:
            self.console.print("[red]流水线宿主校验失败：未检测到可用宿主[/red]")
            self.console.print("[dim]请先执行: super-dev install --auto --force --yes[/dim]")
            self.console.print(
                "[dim]或手动接入: super-dev setup --host codex-cli --force --yes[/dim]"
            )
            return False

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=candidate_targets,
            skill_name="super-dev",
            check_integrate=True,
            check_skill=True,
            check_slash=True,
        )
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=candidate_targets,
            check_integrate=True,
            check_skill=True,
            check_slash=True,
        )

        host_scores = compatibility.get("hosts", {})
        if not isinstance(host_scores, dict):
            host_scores = {}
        ready_targets = [
            target
            for target in candidate_targets
            if bool((host_scores.get(target) or {}).get("ready", False))
        ]
        ready_detected_targets = [target for target in ready_targets if target in detected_targets]

        if ready_detected_targets:
            self.console.print(
                "[dim]宿主硬门禁通过: "
                + ", ".join(self._host_label(target) for target in ready_detected_targets)
                + "[/dim]"
            )
            return True

        self.console.print("[red]流水线宿主校验失败：未找到 ready 的已检测宿主[/red]")
        if ready_targets:
            self.console.print(
                "[yellow]检测到已接入宿主但未识别到本机可执行宿主: "
                + ", ".join(self._host_label(target) for target in ready_targets)
                + "[/yellow]"
            )

        hosts_report = report.get("hosts", {})
        if isinstance(hosts_report, dict):
            for target in candidate_targets:
                host = hosts_report.get(target, {})
                if not isinstance(host, dict):
                    continue
                suggestions = host.get("suggestions", [])
                if isinstance(suggestions, list):
                    for item in suggestions:
                        self.console.print(f"[dim]- {item}[/dim]")

        self.console.print("[dim]建议先执行: super-dev detect --auto --save-profile[/dim]")
        return False

    def _collect_host_diagnostics(
        self,
        *,
        project_dir: Path,
        targets: list[str],
        skill_name: str,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
    ) -> dict[str, Any]:
        from .skills import SkillManager

        skill_manager = SkillManager(project_dir)
        return collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=skill_name,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            build_usage_profile_fn=(
                lambda integration_manager, target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
            ),
            build_diagnosis_fn=(
                lambda target, host_report, integration_manager: self._build_host_diagnosis(
                    target=target,
                    host_report=host_report,
                    integration_manager=integration_manager,
                )
            ),
            skill_primary_file_fn=(
                lambda target, skill_files, optional_skill_files, compatibility_skill_files: (
                    (skill_files or optional_skill_files or compatibility_skill_files)[0]
                    if (skill_files or optional_skill_files or compatibility_skill_files)
                    else (skill_manager._target_dir(target) / skill_name / "SKILL.md")
                )
            ),
            integrate_no_project_note="no project files for this host",
        )

    def _build_compatibility_summary(
        self,
        *,
        report: dict[str, Any],
        targets: list[str],
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
    ) -> dict[str, Any]:
        return build_host_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            include_flow_metrics=True,
        )

    def _build_host_diagnosis(
        self,
        *,
        target: str,
        host_report: dict[str, Any],
        integration_manager,
    ) -> dict[str, str]:
        profile = integration_manager.get_adapter_profile(target)
        missing = host_report.get("missing", [])
        preconditions = (
            host_report.get("preconditions", {}) if isinstance(host_report, dict) else {}
        )
        precondition_status = str(preconditions.get("status", "")).strip()
        precondition_label = str(preconditions.get("label", "")).strip()
        suggestions = host_report.get("suggestions", [])
        suggested_command = ""
        if isinstance(suggestions, list):
            for item in suggestions:
                if isinstance(item, str) and item.strip():
                    suggested_command = item
                    break
        if not suggested_command and suggestions:
            first = suggestions[0]
            if isinstance(first, str):
                suggested_command = first

        primary_reason = str(profile.certification_reason or "").strip()
        blocker_summary = "当前还缺少关键接入项。"

        if "contract" in missing:
            blocker_summary = "已存在宿主接入文件，但内容版本过旧或缺少当前流水线契约。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，补齐并刷新当前宿主接入面。"
        elif "integrate" in missing:
            blocker_summary = "当前项目里还没有写入该宿主需要的接入文件。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，把当前项目需要的宿主接入文件补齐。"
        elif "skill" in missing:
            blocker_summary = "宿主级 Skill 目录存在，但 Super Dev Skill 还没装进去。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，确保当前宿主需要的 Skill 已安装到用户目录。"
        elif "slash" in missing:
            blocker_summary = "宿主命令映射还没写入，所以宿主里还不能直接触发 `/super-dev`。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，确保当前宿主可直接触发 /super-dev。"
        elif precondition_status == "host-auth-required":
            blocker_summary = precondition_label or "宿主鉴权还没完成。"
        elif precondition_status == "session-restart-required":
            blocker_summary = precondition_label or "接入完成后还需要重开宿主会话。"
        elif precondition_status == "project-context-required":
            blocker_summary = precondition_label or "当前会话还没绑定到目标项目。"

        return {
            "certification_reason": primary_reason,
            "blocker_summary": blocker_summary,
            "suggested_command": suggested_command,
        }

    def _build_runtime_governance_summary(
        self,
        *,
        project_dir: Path,
        targets: list[str],
    ) -> dict[str, Any]:
        return collect_layered_runtime_governance_gap(project_dir, targets=targets)

    def _build_compliance_governance_summary(self, *, project_dir: Path) -> dict[str, Any]:
        return collect_compliance_governance_signal(project_dir, output_dir=project_dir / "output")

    def _build_official_compare_summary(
        self, *, hardening_results: dict[str, Any]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        partial = 0
        unknown = 0
        failed = 0
        per_host: dict[str, str] = {}
        for host, item in hardening_results.items():
            total += 1
            status = "unknown"
            if isinstance(item, dict):
                official_compare = item.get("official_compare", {})
                if isinstance(official_compare, dict):
                    status = str(official_compare.get("status", "unknown")).strip() or "unknown"
            per_host[str(host)] = status
            if status == "passed":
                passed += 1
            elif status == "partial":
                partial += 1
            elif status == "failed":
                failed += 1
            else:
                unknown += 1
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "unknown": unknown,
            "score": score,
            "hosts": per_host,
        }

    def _build_host_parity_summary(
        self, *, usage_profiles: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        per_host: dict[str, dict[str, Any]] = {}
        required_keys = ("slash", "rules", "skills", "trigger")
        for host, usage in usage_profiles.items():
            total += 1
            labels = usage.get("capability_labels", {}) if isinstance(usage, dict) else {}
            trigger_command = (
                str(usage.get("trigger_command", "")) if isinstance(usage, dict) else ""
            )
            smoke_prompt = (
                str(usage.get("smoke_test_prompt", "")) if isinstance(usage, dict) else ""
            )
            smoke_signal = (
                str(usage.get("smoke_success_signal", "")) if isinstance(usage, dict) else ""
            )
            protocol_mode = (
                str(usage.get("host_protocol_mode", "")).strip() if isinstance(usage, dict) else ""
            )
            slash_label = str((labels or {}).get("slash", "")).strip()
            trigger_ok = (
                trigger_command.startswith("/super-dev")
                if slash_label == "native"
                else trigger_command.startswith("super-dev:")
            )
            checks = {
                "trigger": trigger_ok,
                "smoke_prompt": "SMOKE_OK" in smoke_prompt,
                "smoke_signal": "SMOKE_OK" in smoke_signal,
                "protocol_mode": bool(protocol_mode),
                "capability_labels": all(key in labels for key in required_keys),
            }
            check_total = len(checks)
            check_passed = sum(1 for item in checks.values() if bool(item))
            host_pass = check_passed == check_total
            if host_pass:
                passed += 1
            per_host[str(host)] = {
                "passed": host_pass,
                "score": round((check_passed / check_total) * 100, 2) if check_total else 100.0,
                "checks": checks,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": per_host,
        }

    def _build_host_recovery_summary(
        self,
        *,
        targets: list[str],
        usage_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        for target in targets:
            total += 1
            usage = usage_profiles.get(target, {}) if isinstance(usage_profiles, dict) else {}
            preferred_prompt = ""
            if isinstance(usage, dict):
                entry_bundle = build_host_entry_prompts(
                    target=target,
                    instruction="继续当前流程",
                    supports_slash=bool(usage.get("supports_slash", False)),
                    flow_variant="standard",
                )
                preferred_key = str(entry_bundle.get("preferred_entry", "")).strip()
                entry_prompts = entry_bundle.get("entry_prompts", {})
                if isinstance(entry_prompts, dict):
                    preferred_prompt = str(entry_prompts.get(preferred_key, "")).strip()
                    if not preferred_prompt:
                        preferred_prompt = next(
                            (
                                str(value).strip()
                                for value in entry_prompts.values()
                                if str(value).strip()
                            ),
                            "",
                        )
            commands = ["super-dev", "super-dev update"]
            if preferred_prompt:
                commands.append(preferred_prompt)
            if isinstance(usage, dict):
                entry_prompts = entry_bundle.get("entry_prompts", {})
                fallback_prompt = ""
                if isinstance(entry_prompts, dict):
                    fallback_prompt = str(entry_prompts.get("fallback", "")).strip()
                if fallback_prompt and fallback_prompt not in commands:
                    commands.append(fallback_prompt)
            actions = [
                "先运行 `super-dev`，补齐当前宿主的接入面并刷新安装注入状态。",
                "如果宿主规则或 Skill 模板需要同步到最新版本，再运行 `super-dev update`。",
            ]
            if preferred_prompt:
                actions.append(
                    f"修复完成后回到宿主里继续，第一句优先直接使用 `{preferred_prompt}`。"
                )
            else:
                actions.append("修复完成后回到宿主里继续当前流程。")
            checks = {
                "has_primary_repair": commands[0] == "super-dev",
                "has_update_path": any(cmd == "super-dev update" for cmd in commands),
                "has_host_resume_prompt": bool(preferred_prompt),
                "avoids_retired_low_level_commands": not any(
                    any(marker in cmd for marker in ("integrate ", "skill install", "onboard --host"))
                    for cmd in commands
                ),
            }
            host_pass = all(bool(item) for item in checks.values())
            if host_pass:
                passed += 1
            hosts[target] = {
                "passed": host_pass,
                "checks": checks,
                "recommended_commands": commands,
                "recommended_actions": actions,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_gate_summary(
        self, *, report: dict[str, Any], targets: list[str]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        report_hosts = report.get("hosts", {}) if isinstance(report, dict) else {}
        if not isinstance(report_hosts, dict):
            report_hosts = {}
        for target in targets:
            total += 1
            host = report_hosts.get(target, {})
            checks = host.get("checks", {}) if isinstance(host, dict) else {}
            contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
            surfaces = contract.get("surfaces", {}) if isinstance(contract, dict) else {}
            docs_confirm_ok = True
            preview_confirm_ok = True
            if isinstance(surfaces, dict):
                for surface in surfaces.values():
                    if not isinstance(surface, dict):
                        continue
                    if not bool(surface.get("exists", False)):
                        continue
                    missing = surface.get("missing_markers", [])
                    if not isinstance(missing, list):
                        continue
                    if "confirmation" in missing:
                        docs_confirm_ok = False
                    if "flow" in missing:
                        preview_confirm_ok = False
            host_pass = docs_confirm_ok and preview_confirm_ok
            if host_pass:
                passed += 1
            hosts[target] = {
                "passed": host_pass,
                "checks": {
                    "docs_confirm_gate": docs_confirm_ok,
                    "preview_confirm_gate": preview_confirm_ok,
                },
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_runtime_script_summary(
        self, *, usage_profiles: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        for host, usage in usage_profiles.items():
            total += 1
            if not isinstance(usage, dict):
                usage = {}
            smoke_steps = usage.get("smoke_test_steps", [])
            competition_smoke_steps = usage.get("competition_smoke_test_steps", [])
            post_steps = usage.get("post_onboard_steps", [])
            checks = {
                "has_final_trigger": bool(str(usage.get("final_trigger", "")).strip()),
                "has_smoke_prompt": "SMOKE_OK" in str(usage.get("smoke_test_prompt", "")),
                "has_smoke_signal": "SMOKE_OK" in str(usage.get("smoke_success_signal", "")),
                "has_smoke_steps": isinstance(smoke_steps, list) and len(smoke_steps) > 0,
                "has_competition_smoke_prompt": "SEEAI_SMOKE_OK"
                in str(usage.get("competition_smoke_test_prompt", "")),
                "has_competition_smoke_signal": "SEEAI_SMOKE_OK"
                in str(usage.get("competition_smoke_success_signal", "")),
                "has_competition_smoke_steps": isinstance(competition_smoke_steps, list)
                and len(competition_smoke_steps) > 0,
                "has_post_onboard_steps": isinstance(post_steps, list) and len(post_steps) > 0,
            }
            host_pass = all(bool(item) for item in checks.values())
            if host_pass:
                passed += 1
            hosts[str(host)] = {
                "passed": host_pass,
                "checks": checks,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_parity_index(
        self,
        *,
        threshold: float,
        official_compare_summary: dict[str, Any] | None,
        host_parity_summary: dict[str, Any] | None,
        host_gate_summary: dict[str, Any] | None,
        host_runtime_script_summary: dict[str, Any] | None,
        host_recovery_summary: dict[str, Any] | None,
        compatibility: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metrics: dict[str, float] = {}
        mapping: list[tuple[str, dict[str, Any] | None]] = [
            ("official_compare", official_compare_summary),
            ("host_parity", host_parity_summary),
            ("host_gate", host_gate_summary),
            ("runtime_script", host_runtime_script_summary),
            ("host_recovery", host_recovery_summary),
        ]
        for name, summary in mapping:
            if isinstance(summary, dict):
                if name == "official_compare":
                    total = int(summary.get("total", 0) or 0)
                    passed = int(summary.get("passed", 0) or 0)
                    partial = int(summary.get("partial", 0) or 0)
                    failed = int(summary.get("failed", 0) or 0)
                    if total <= 0 or (passed + partial + failed) <= 0:
                        continue
                try:
                    metrics[name] = float(summary.get("score", 0))
                except Exception:
                    metrics[name] = 0.0
        if isinstance(compatibility, dict):
            try:
                metrics["flow_consistency"] = float(compatibility.get("flow_consistency_score", 0))
            except Exception:
                metrics["flow_consistency"] = 0.0
        if metrics:
            score = round(sum(metrics.values()) / len(metrics), 2)
        else:
            score = 0.0
        limit = float(threshold)
        return {
            "score": score,
            "threshold": limit,
            "passed": score >= limit,
            "metrics": metrics,
        }

    def _repair_host_diagnostics(
        self,
        *,
        project_dir: Path,
        report: dict[str, Any],
        skill_name: str,
        force: bool,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
        include_user_surfaces: bool,
    ) -> dict[str, dict[str, str]]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        actions: dict[str, dict[str, str]] = {}

        hosts = report.get("hosts", {})
        if not isinstance(hosts, dict):
            return actions

        for target, host in hosts.items():
            if not isinstance(target, str) or not isinstance(host, dict):
                continue
            missing = host.get("missing", [])
            if not isinstance(missing, list):
                continue

            host_actions: dict[str, str] = {}
            contract_needs_repair = "contract" in missing
            user_surfaces_need_repair = include_user_surfaces and "user_surfaces" in missing
            effective_skill_name = SkillManager.default_skill_name(target)

            if contract_needs_repair:
                try:
                    integration_manager.setup(target=target, force=True)
                    if include_user_surfaces:
                        integration_manager.setup_global_protocol(target=target, force=True)
                        integration_manager.setup_global_agent_surfaces(target=target, force=True)
                    if integration_manager.supports_slash(target):
                        integration_manager.setup_slash_command(target=target, force=True)
                        if include_user_surfaces:
                            integration_manager.setup_global_slash_command(target=target, force=True)
                    if (
                        check_skill
                        and IntegrationManager.requires_skill(target)
                        and skill_manager.skill_surface_available(target)
                    ):
                        skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=effective_skill_name,
                            force=True,
                        )
                    host_actions["contract"] = "refreshed"
                except Exception as exc:
                    host_actions["contract"] = f"failed: {exc}"

            try:
                if check_integrate and "integrate" in missing and not contract_needs_repair:
                    integration_manager.setup(target=target, force=force)
                    host_actions["integrate"] = "fixed"
            except Exception as exc:
                host_actions["integrate"] = f"failed: {exc}"

            try:
                if user_surfaces_need_repair and not contract_needs_repair:
                    repaired_any = False
                    if integration_manager.resolve_global_protocol_path(target) is not None:
                        integration_manager.setup_global_protocol(target=target, force=True)
                        repaired_any = True
                    if integration_manager.managed_user_agent_surfaces(target):
                        integration_manager.setup_global_agent_surfaces(target=target, force=True)
                        repaired_any = True
                    if (
                        check_skill
                        and IntegrationManager.requires_skill(target)
                        and skill_manager.skill_surface_available(target)
                    ):
                        skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=effective_skill_name,
                            force=True,
                        )
                        repaired_any = True
                    if repaired_any:
                        host_actions["user_surfaces"] = "fixed"
            except Exception as exc:
                host_actions["user_surfaces"] = f"failed: {exc}"

            try:
                if (
                    check_skill
                    and IntegrationManager.requires_skill(target)
                    and "skill" in missing
                    and not contract_needs_repair
                ):
                    skill_manager.install(
                        source="super-dev",
                        target=target,
                        name=effective_skill_name,
                        force=force,
                    )
                    host_actions["skill"] = "fixed"
            except Exception as exc:
                host_actions["skill"] = f"failed: {exc}"

            try:
                if (
                    check_slash
                    and integration_manager.supports_slash(target)
                    and not contract_needs_repair
                ):
                    integration_manager.setup_slash_command(target=target, force=force)
                    if include_user_surfaces:
                        integration_manager.setup_global_slash_command(target=target, force=force)
                    if "slash" in missing:
                        host_actions["slash"] = "fixed"
            except Exception as exc:
                host_actions["slash"] = f"failed: {exc}"

            if host_actions:
                actions[target] = host_actions

        return actions

    def _cmd_onboard(self, args) -> int:
        """首次接入向导：宿主选择 + 集成 + skill + slash"""
        from .integrations import IntegrationManager
        from .skills import SkillManager

        if not self._ensure_host_support_matrix():
            return 1
        include_user_surfaces = self._include_user_surfaces(args)
        if self._is_manual_install_host(getattr(args, "host", None)):
            return self._print_manual_install_host_guidance(
                target=str(args.host), command_name="onboard"
            )

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        detail = bool(getattr(args, "detail", False))

        available_targets = self._public_host_targets(integration_manager=integration_manager)
        targets: list[str]
        detected_meta: dict[str, list[str]] = {}

        if args.host:
            targets = [args.host]
        elif args.all:
            targets = available_targets
        elif args.auto:
            targets, detected_meta = self._detect_host_targets(available_targets=available_targets)
            targets = self._deduplicate_host_family(targets)
            if not targets:
                self.console.print("[red]未检测到可用宿主，请改用 --host 指定或使用 --all[/red]")
                self.console.print(f"[dim]{self._custom_host_path_override_hint()}[/dim]")
                return 1
            self.console.print(
                f"[cyan]自动检测到 {len(targets)} 个宿主：{', '.join(self._host_label(target) for target in targets)}[/cyan]"
            )
            for target in targets:
                reasons = ", ".join(
                    self._format_detection_reason(item) for item in detected_meta.get(target, [])
                )
                if reasons:
                    self.console.print(f"[dim]  - {self._host_label(target)}: {reasons}[/dim]")
        else:
            try:
                targets = self._resolve_onboard_targets(
                    available_targets=available_targets,
                    host=args.host,
                    all_targets=bool(args.all),
                    non_interactive=bool(args.yes),
                )
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 1

        if not targets:
            self.console.print("[red]未选择任何宿主工具[/red]")
            return 1

        if getattr(args, "stable_only", False):
            stable_targets = []
            for t in targets:
                profile = integration_manager.get_adapter_profile(t)
                cert = profile.certification_label.lower()
                if cert.startswith("certified") or cert.startswith("compatible"):
                    stable_targets.append(t)
            if not stable_targets:
                self.console.print("[yellow]未找到 Certified 或 Compatible 级别的宿主[/yellow]")
                return 1
            skipped = set(targets) - set(stable_targets)
            if skipped:
                self.console.print(
                    f"[dim]跳过 Experimental 宿主: {', '.join(self._host_label(target) for target in sorted(skipped))}[/dim]"
                )
            targets = stable_targets

        setattr(args, "_selected_targets", list(targets))

        self.console.print("")
        from rich.panel import Panel
        from rich.rule import Rule

        self.console.print(
            Panel(
                f"[bold cyan]Super Dev Onboard[/bold cyan]\n\n"
                f"  [dim]项目[/dim]      {project_dir.name}\n"
                f"  [dim]目标宿主[/dim]  {len(targets)} 个\n"
                f"  [dim]版本[/dim]      {__version__}",
                border_style="cyan",
                expand=True,
                padding=(1, 2),
            )
        )
        self.console.print("")
        has_error = False
        target_results: list[dict[str, Any]] = []
        for idx, target in enumerate(targets, 1):
            protocol = integration_manager._protocol_profile(target=target)
            protocol_summary = protocol.get("summary", "") if isinstance(protocol, dict) else ""
            self.console.print(
                Rule(
                    f"[bold cyan] {idx}/{len(targets)} [/bold cyan] [bold]{self._host_label(target)}[/bold]  [dim]{protocol_summary}[/dim]",
                    style="dim cyan",
                )
            )
            self.console.print("")

            profile = integration_manager.get_adapter_profile(target)
            manifest_paths: list[str] = []
            has_project_surface = False
            has_global_surface = False
            has_runtime_surface = False
            target_errors: list[str] = []

            if getattr(args, "dry_run", False):
                surfaces = integration_manager.collect_managed_surface_paths(
                    target=target,
                    include_user_surfaces=include_user_surfaces,
                )
                self.console.print("  [dim]将写入以下文件:[/dim]")
                for key, path in surfaces.items():
                    exists = path.exists()
                    status = "[dim]已存在[/dim]" if exists else "[cyan]新建[/cyan]"
                    self.console.print(f"    {status} {path}")
                self.console.print("")
                continue

            # Check whether this host has integration files to write
            target_config = integration_manager.TARGETS.get(target)
            has_integrate_files = bool(target_config and target_config.files)

            if not args.skip_integrate and has_integrate_files:
                try:
                    written_files = integration_manager.setup(target=target, force=args.force)
                    integrate_written_count = len(written_files)
                    if written_files:
                        has_project_surface = True
                        manifest_paths.extend(str(item) for item in written_files)
                    if written_files:
                        if detail:
                            for item in written_files:
                                self.console.print(
                                    f"  [green]✓[/green] 集成规则: {item}",
                                    soft_wrap=True,
                                )
                        else:
                            self.console.print(
                                f"  [green]✓[/green] 集成规则: {integrate_written_count} 项"
                            )
                    else:
                        self.console.print("  [dim]- 集成规则已存在（可加 --force 覆盖）[/dim]")
                    if include_user_surfaces:
                        global_protocol = integration_manager.setup_global_protocol(
                            target=target, force=args.force
                        )
                        if global_protocol is not None:
                            has_global_surface = True
                            manifest_paths.append(str(global_protocol))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] 宿主协议: {global_protocol}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] 宿主协议: 已写入")
                        global_agent_surfaces = integration_manager.setup_global_agent_surfaces(
                            target=target,
                            force=args.force,
                        )
                        if global_agent_surfaces:
                            has_global_surface = True
                            manifest_paths.extend(str(item) for item in global_agent_surfaces)
                            if detail:
                                for item in global_agent_surfaces:
                                    self.console.print(
                                        f"  [green]✓[/green] 用户级 Agent 面: {item}",
                                        soft_wrap=True,
                                    )
                            else:
                                self.console.print(
                                    f"  [green]✓[/green] 用户级 Agent 面: {len(global_agent_surfaces)} 项"
                                )
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"integrate: {exc}")
                    self.console.print(f"  [yellow]⚠[/yellow] 集成规则写入失败: {exc}")
            elif not args.skip_integrate and not has_integrate_files:
                self.console.print("  [dim]- 该宿主无项目级集成文件，跳过集成规则[/dim]")
                # Still attempt global protocol even for hosts without project files
                try:
                    if include_user_surfaces:
                        global_protocol = integration_manager.setup_global_protocol(
                            target=target, force=args.force
                        )
                        if global_protocol is not None:
                            has_global_surface = True
                            manifest_paths.append(str(global_protocol))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] 宿主协议: {global_protocol}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] 宿主协议: 已写入")
                        global_agent_surfaces = integration_manager.setup_global_agent_surfaces(
                            target=target,
                            force=args.force,
                        )
                        if global_agent_surfaces:
                            has_global_surface = True
                            manifest_paths.extend(str(item) for item in global_agent_surfaces)
                            if detail:
                                for item in global_agent_surfaces:
                                    self.console.print(
                                        f"  [green]✓[/green] 用户级 Agent 面: {item}",
                                        soft_wrap=True,
                                    )
                            else:
                                self.console.print(
                                    f"  [green]✓[/green] 用户级 Agent 面: {len(global_agent_surfaces)} 项"
                                )
                except Exception as exc:
                    target_errors.append(f"global integrate: {exc}")
                    self.console.print(f"  [yellow]⚠[/yellow] 宿主协议写入失败: {exc}")

            if not args.skip_skill and IntegrationManager.requires_skill(target):
                try:
                    if not skill_manager.skill_surface_available(target):
                        self.console.print(
                            "  [dim]- 未检测到官方或兼容 Skill 目录，已跳过宿主级 Skill 安装[/dim]"
                        )
                    else:
                        target_skill_name = SkillManager.default_skill_name(target)
                        installed = set(skill_manager.list_installed(target))
                        if target_skill_name in installed and not args.force:
                            self.console.print(
                                f"  [dim]- Skill 已存在: {target_skill_name}（可加 --force 重装）[/dim]"
                            )
                        else:
                            install_result = skill_manager.install(
                                source="super-dev",
                                target=target,
                                name=target_skill_name,
                                force=args.force,
                            )
                            manifest_paths.append(str(install_result.path))
                            if str(install_result.path).startswith(str(Path.home())):
                                has_global_surface = True
                            else:
                                has_project_surface = True
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] Skill: {install_result.path}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] Skill: 已安装")
                        legacy_removed = skill_manager.cleanup_legacy_skill_aliases(target)
                        if legacy_removed:
                            self.console.print(
                                "  [green]✓[/green] 已清理旧版 Super Dev 技能残留"
                            )
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"skill: {exc}")
                    self.console.print(f"  [red]✗[/red] Skill 安装失败: {exc}")
            elif not args.skip_skill:
                self.console.print("  [dim]- 该宿主默认按项目规则运行，已跳过 Skill 安装[/dim]")

            # Clean up legacy skill-alias agent files
            legacy_agent_files: list[Path] = []
            legacy_agent_name = "super-dev" + "-core.md"
            if target == "claude-code":
                legacy_agent_files = [
                    Path.home() / ".claude" / "agents" / legacy_agent_name,
                    project_dir / ".claude" / "agents" / legacy_agent_name,
                ]
            elif target in ("codebuddy", "codebuddy-cli"):
                legacy_agent_files = [
                    project_dir / ".codebuddy" / "agents" / legacy_agent_name,
                    Path.home() / ".codebuddy" / "agents" / legacy_agent_name,
                ]
            for legacy_path in legacy_agent_files:
                if legacy_path.exists():
                    try:
                        legacy_path.unlink()
                        self.console.print(f"  [green]✓[/green] 已清理旧版: {legacy_path.name}")
                    except Exception:
                        pass

            if not args.skip_slash:
                try:
                    if integration_manager.supports_slash(target):
                        slash_file = integration_manager.setup_slash_command(
                            target=target,
                            force=args.force,
                        )
                        if slash_file is None:
                            self.console.print(
                                "  [dim]- /super-dev 映射已存在（可加 --force 覆盖）[/dim]"
                            )
                        else:
                            has_project_surface = True
                            manifest_paths.append(str(slash_file))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] /super-dev 映射: {slash_file}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] /super-dev 映射: 已写入")
                        if include_user_surfaces:
                            global_slash_file = integration_manager.setup_global_slash_command(
                                target=target,
                                force=args.force,
                            )
                            if global_slash_file is None:
                                self.console.print(
                                    "  [dim]- 全局 /super-dev 映射已存在（可加 --force 覆盖）[/dim]"
                                )
                            elif (
                                slash_file is None
                                or global_slash_file.resolve() != slash_file.resolve()
                            ):
                                has_global_surface = True
                                manifest_paths.append(str(global_slash_file))
                                if detail:
                                    self.console.print(
                                        f"  [green]✓[/green] 全局 /super-dev 映射: {global_slash_file}",
                                        soft_wrap=True,
                                    )
                                else:
                                    self.console.print(
                                        "  [green]✓[/green] 全局 /super-dev 映射: 已写入"
                                    )
                        seeai_slash_file = integration_manager.setup_seeai_slash_command(
                            target=target,
                            force=args.force,
                        )
                        if seeai_slash_file is None:
                            self.console.print(
                                "  [dim]- /super-dev-seeai 映射已存在（可加 --force 覆盖）[/dim]"
                            )
                        else:
                            has_project_surface = True
                            manifest_paths.append(str(seeai_slash_file))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] /super-dev-seeai 映射: {seeai_slash_file}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print(
                                    "  [green]✓[/green] /super-dev-seeai 映射: 已写入"
                                )
                        if include_user_surfaces:
                            global_seeai_slash_file = (
                                integration_manager.setup_global_seeai_slash_command(
                                    target=target,
                                    force=args.force,
                                )
                            )
                            if global_seeai_slash_file is None:
                                self.console.print(
                                    "  [dim]- 全局 /super-dev-seeai 映射已存在（可加 --force 覆盖）[/dim]"
                                )
                            elif (
                                seeai_slash_file is None
                                or global_seeai_slash_file.resolve() != seeai_slash_file.resolve()
                            ):
                                has_global_surface = True
                                manifest_paths.append(str(global_seeai_slash_file))
                                if detail:
                                    self.console.print(
                                        f"  [green]✓[/green] 全局 /super-dev-seeai 映射: {global_seeai_slash_file}",
                                        soft_wrap=True,
                                    )
                                else:
                                    self.console.print(
                                        "  [green]✓[/green] 全局 /super-dev-seeai 映射: 已写入"
                                    )
                    else:
                        self.console.print(
                            "  [dim]- 该宿主不支持 /super-dev 或 /super-dev-seeai，已跳过 slash 映射[/dim]"
                        )
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"slash: {exc}")
                    self.console.print(f"  [red]✗[/red] slash 映射失败: {exc}")

            self.console.print(f"  [cyan]主入口[/cyan]: {profile.primary_entry}")
            if profile.requires_restart_after_onboard:
                self.console.print("  [yellow]注意[/yellow]: 接入完成后需要重启宿主")
            if detail:
                for step in profile.post_onboard_steps:
                    self.console.print(f"  [dim]- {step}[/dim]")
            elif profile.post_onboard_steps:
                self.console.print(f"  [dim]- {profile.post_onboard_steps[0]}[/dim]")

            contract_failures = self._collect_onboard_contract_failures(
                integration_manager=integration_manager,
                target=target,
                skill_name=args.skill_name,
                skip_skill=bool(args.skip_skill),
                include_user_surfaces=include_user_surfaces,
            )
            if contract_failures and not args.force:
                refreshed = self._refresh_onboard_contract_surfaces(
                    integration_manager=integration_manager,
                skill_manager=skill_manager,
                target=target,
                skill_name=args.skill_name,
                skip_skill=bool(args.skip_skill),
                include_user_surfaces=include_user_surfaces,
            )
                if refreshed:
                    self.console.print(
                        f"  [yellow]![/yellow] 检测到旧版接入文件，已自动刷新: {', '.join(refreshed)}"
                    )
                    contract_failures = self._collect_onboard_contract_failures(
                        integration_manager=integration_manager,
                        target=target,
                        skill_name=args.skill_name,
                        skip_skill=bool(args.skip_skill),
                        include_user_surfaces=include_user_surfaces,
                    )
            auto_repair_actions = self._auto_repair_onboard_target(
                project_dir=project_dir,
                target=target,
                skill_name=args.skill_name,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
                include_user_surfaces=include_user_surfaces,
            )
            if auto_repair_actions:
                action_text = ", ".join(f"{k}={v}" for k, v in auto_repair_actions.items())
                self.console.print(
                    f"  [yellow]![/yellow] 检测到安装残留，已自动修复: {action_text}"
                )
                contract_failures = self._collect_onboard_contract_failures(
                    integration_manager=integration_manager,
                    target=target,
                    skill_name=args.skill_name,
                    skip_skill=bool(args.skip_skill),
                    include_user_surfaces=include_user_surfaces,
                )
            if contract_failures:
                has_error = True
                target_errors.extend(contract_failures)
                self.console.print("  [red]✗[/red] 宿主契约校验失败:")
                for item in contract_failures[:6]:
                    self.console.print(f"  [dim]- {item}[/dim]")
            else:
                self.console.print("  [green]✓[/green] 宿主契约校验通过")
                if not manifest_paths:
                    managed_surfaces = integration_manager.collect_managed_surface_paths(
                        target=target,
                        skill_name=args.skill_name,
                        include_user_surfaces=include_user_surfaces,
                    )
                    for surface_path in managed_surfaces.values():
                        if surface_path.exists():
                            manifest_paths.append(str(surface_path))
                            if str(surface_path).startswith(str(Path.home())):
                                has_global_surface = True
                            else:
                                has_project_surface = True
                if target == "claude-code" and any(
                    path.endswith(".claude/settings.local.json")
                    or path.endswith(".claude/settings.json")
                    for path in manifest_paths
                ):
                    has_runtime_surface = True
                try:
                    record_install_manifest(
                        project_dir,
                        host=target,
                        family=integration_manager.host_family(target),
                        scopes={
                            "project": has_project_surface,
                            "global": has_global_surface,
                            "runtime": has_runtime_surface,
                        },
                        paths=manifest_paths,
                    )
                except Exception:
                    pass
            target_results.append(
                {
                    "target": target,
                    "manifest_paths": sorted(set(manifest_paths)),
                    "contract_failures": contract_failures,
                    "auto_repair_actions": auto_repair_actions,
                    "errors": target_errors,
                }
            )

        self.console.print("")
        if args.dry_run:
            self.console.print(
                Panel(
                    "[bold cyan]Dry Run 完成[/bold cyan]\n\n"
                    "  以上为预览，未实际写入任何文件\n"
                    "  去掉 --dry-run 参数执行实际安装",
                    border_style="cyan",
                    expand=True,
                    padding=(1, 2),
                )
            )
            return 0
        smoke_report_paths = self._write_onboard_smoke_report(
            project_dir=project_dir,
            integration_manager=integration_manager,
            include_user_surfaces=include_user_surfaces,
            target_results=target_results,
            status="partial" if has_error else "ok",
        )
        setattr(args, "_smoke_report_paths", smoke_report_paths)
        if has_error:
            self.console.print(
                Panel(
                    "[bold red]Onboard 完成（部分失败）[/bold red]\n\n"
                    "  先不要继续开发，也先不要回宿主里试错。\n"
                    "  先在终端运行 [cyan]super-dev doctor --host <host> --repair --force[/cyan]\n"
                    "  需要看完整落点时再加 [cyan]--detail[/cyan]",
                    border_style="red",
                    expand=True,
                    padding=(1, 2),
                )
            )
            self.console.print(
                f"[dim]Onboard smoke guide: {smoke_report_paths.get('markdown', '')}[/dim]"
            )
            return 1

        next_steps = self._build_onboard_next_steps(targets=targets)
        steps_text = "\n".join(f"  [green]>[/green] {line}" for line in next_steps)
        resume_lines = (
            self._build_session_resume_card_lines(project_dir=project_dir, target=targets[0])
            if targets
            else []
        )
        resume_text = ""
        if resume_lines:
            resume_text = "\n\n[bold]如果你是在继续已有流程:[/bold]\n\n" + "\n".join(
                f"  [cyan]>[/cyan] {line}" for line in resume_lines
            )
        self.console.print(
            Panel(
                f"[bold green]Onboard 完成[/bold green]\n\n"
                f"[bold]终端到此为止，真正开发回到宿主里。[/bold]\n\n"
                f"[bold]接下来这样用:[/bold]\n\n{steps_text}{resume_text}\n\n"
                f"[dim]Smoke guide: {smoke_report_paths.get('markdown', '')}[/dim]\n"
                f"[dim]提示: 先看 smoke guide 里的框架焦点、必验场景和交付证据，再复制第一句。[/dim]\n"
                f"[dim]只有没进入 research -> 三文档 -> 等待确认，才回终端运行 doctor。[/dim]",
                border_style="green",
                expand=True,
                padding=(1, 2),
            )
        )
        self.console.print(
            f"[dim]Onboard smoke guide: {smoke_report_paths.get('markdown', '')}[/dim]"
        )
        return 0

    def _collect_onboard_contract_failures(
        self,
        *,
        integration_manager,
        target: str,
        skill_name: str,
        skip_skill: bool,
        include_user_surfaces: bool,
    ) -> list[str]:
        contract_surfaces = integration_manager.collect_managed_surface_paths(
            target=target,
            skill_name=skill_name,
            include_user_surfaces=include_user_surfaces,
        )
        surface_classification = integration_manager.managed_surface_classification(
            target=target,
            skill_name=skill_name,
        )
        contract_failures: list[str] = []
        for surface_key, surface_path in contract_surfaces.items():
            if surface_key.startswith("skill:") and skip_skill:
                continue
            if not surface_path.exists():
                continue
            try:
                content = surface_path.read_text(encoding="utf-8")
            except Exception:
                surface_meta = surface_classification.get(surface_key, {})
                if bool(surface_meta.get("required", False)):
                    contract_failures.append(str(surface_path))
                continue
            missing_markers = integration_manager.audit_surface_contract(
                target, surface_key, surface_path, content
            )
            surface_meta = surface_classification.get(surface_key, {})
            if missing_markers and bool(surface_meta.get("required", False)):
                contract_failures.append(str(surface_path))
        return contract_failures

    def _refresh_onboard_contract_surfaces(
        self,
        *,
        integration_manager,
        skill_manager,
        target: str,
        skill_name: str,
        skip_skill: bool,
        include_user_surfaces: bool,
    ) -> list[str]:
        from .integrations import IntegrationManager

        refreshed: list[str] = []
        integration_manager.setup(target=target, force=True)
        refreshed.append("integrate")
        if include_user_surfaces:
            integration_manager.setup_global_protocol(target=target, force=True)
            if integration_manager.setup_global_agent_surfaces(target=target, force=True):
                refreshed.append("user-agents")
            refreshed.append("user-surfaces")

        if integration_manager.supports_slash(target):
            integration_manager.setup_slash_command(target=target, force=True)
            refreshed.append("slash")
            if include_user_surfaces:
                integration_manager.setup_global_slash_command(target=target, force=True)
                refreshed.append("user-slash")

        if (
            not skip_skill
            and IntegrationManager.requires_skill(target)
            and skill_manager.skill_surface_available(target)
        ):
            skill_manager.install(
                source="super-dev",
                target=target,
                name=skill_name,
                force=True,
            )
            refreshed.append("skill")

        return refreshed

    def _auto_repair_onboard_target(
        self,
        *,
        project_dir: Path,
        target: str,
        skill_name: str,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
        include_user_surfaces: bool,
    ) -> dict[str, str]:
        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=[target],
            skill_name=skill_name,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
        )
        host_report = (report.get("hosts", {}) or {}).get(target, {})
        if not isinstance(host_report, dict) or bool(host_report.get("ready", False)):
            return {}

        repair_actions = self._repair_host_diagnostics(
            project_dir=project_dir,
            report=report,
            skill_name=skill_name,
            force=True,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            include_user_surfaces=include_user_surfaces,
        )
        return repair_actions.get(target, {}) if isinstance(repair_actions, dict) else {}

    def _cmd_doctor(self, args) -> int:
        """诊断宿主接入状态"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1

        detail = bool(getattr(args, "detail", False))

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        detected_targets: list[str] = []
        detected_meta: dict[str, list[str]] = {}
        if self._is_manual_install_host(getattr(args, "host", None)):
            targets = [str(args.host)]
        else:
            available_targets = self._public_host_targets(integration_manager=integration_manager)
            detected_targets, detected_meta = self._detect_host_targets(
                available_targets=available_targets
            )
            targets: list[str]
        if args.host:
            targets = [args.host]
        elif args.auto:
            if not detected_targets:
                if not args.json:
                    self.console.print("[yellow]未检测到可用宿主，已回退为诊断全部目标[/yellow]")
                    self.console.print(f"[dim]{self._custom_host_path_override_hint()}[/dim]")
                targets = available_targets
            else:
                targets = detected_targets
                if not args.json:
                    self.console.print(
                        f"[cyan]自动检测到 {len(targets)} 个宿主：{', '.join(self._host_label(target) for target in targets)}[/cyan]"
                    )
                    for target in targets:
                        reasons = ", ".join(
                            self._format_detection_reason(item)
                            for item in detected_meta.get(target, [])
                        )
                        if reasons:
                            self.console.print(
                                f"[dim]  - {self._host_label(target)}: {reasons}[/dim]"
                            )
        elif args.all:
            targets = available_targets
        else:
            targets = available_targets

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=args.skill_name,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        runtime_health = self._collect_runtime_install_health()
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        repair_actions: dict[str, dict[str, str]] = {}
        if args.repair:
            repair_actions = self._repair_host_diagnostics(
                project_dir=project_dir,
                report=report,
                skill_name=args.skill_name,
                force=bool(args.force),
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
                include_user_surfaces=self._include_user_surfaces(args),
            )
            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=targets,
                skill_name=args.skill_name,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
            )
            compatibility = self._build_compatibility_summary(
                report=report,
                targets=targets,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
            )
            report["repair_actions"] = repair_actions
        decision_card = (
            self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=detected_targets,
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            )
            if detected_targets
            else self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=[],
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            )
        )
        workflow_context = (
            dict(decision_card.get("workflow_context", {}))
            if isinstance(decision_card.get("workflow_context", {}), dict)
            else {}
        )
        report["compatibility"] = compatibility
        report["runtime_install_health"] = runtime_health
        report["selected_targets"] = targets
        report["detected_hosts"] = detected_targets
        report["detection_details_pretty"] = self._explain_detection_details(detected_meta)
        report["workflow_context"] = workflow_context
        report["decision_card"] = decision_card
        report["primary_repair_action"] = self._build_primary_repair_action(
            report=report,
            targets=targets,
            decision_card=decision_card,
        )
        report["runtime_governance_summary"] = self._build_runtime_governance_summary(
            project_dir=project_dir,
            targets=targets,
        )
        report["compliance_governance_summary"] = self._build_compliance_governance_summary(
            project_dir=project_dir
        )

        # --fix: auto-repair common issues
        if getattr(args, "fix", False) and not bool(report.get("overall_ready", False)):
            fix_actions: list[str] = []
            claude_code_missing = False
            skill_missing = False
            for target, host_report in report.get("hosts", {}).items():
                checks = host_report.get("checks", {})
                if not checks.get("integrate", {}).get("ok", True):
                    claude_code_missing = True
                if not checks.get("skill", {}).get("ok", True):
                    skill_missing = True
            if claude_code_missing or skill_missing:
                try:
                    setup_args = argparse.Namespace(
                        host=None,
                        target=None,
                        all=True,
                        auto=False,
                        skill_name=args.skill_name,
                        skip_integrate=False,
                        skip_skill=False,
                        skip_slash=False,
                        skip_doctor=True,
                        yes=True,
                        force=True,
                        detail=False,
                    )
                    self._cmd_setup(setup_args)
                    fix_actions.append("setup (集成规则 + Skill 安装)")
                except Exception as exc:
                    fix_actions.append(f"setup 失败: {exc}")

            if fix_actions:
                self.console.print("[cyan]--fix 自动修复执行结果:[/cyan]")
                for action in fix_actions:
                    self.console.print(f"  [green]✓[/green] {action}")
                self.console.print("")
                # Re-collect diagnostics after fix
                report = self._collect_host_diagnostics(
                    project_dir=project_dir,
                    targets=targets,
                    skill_name=args.skill_name,
                    check_integrate=not args.skip_integrate,
                    check_skill=not args.skip_skill,
                    check_slash=not args.skip_slash,
                )
                runtime_health = self._collect_runtime_install_health()
                compatibility = self._build_compatibility_summary(
                    report=report,
                    targets=targets,
                    check_integrate=not args.skip_integrate,
                    check_skill=not args.skip_skill,
                    check_slash=not args.skip_slash,
                )
                report["compatibility"] = compatibility
                report["runtime_install_health"] = runtime_health

        if args.json:
            sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            return 0 if bool(report.get("overall_ready", False)) else 1

        self.console.print("[cyan]Super Dev Doctor[/cyan]")
        self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
        if isinstance(decision_card, dict) and decision_card.get("lines"):
            self.console.print(f"[cyan]{decision_card.get('title', '宿主决策')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")
            self.console.print("")
        self.console.print(
            f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
            f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
        )
        runtime_governance = report.get("runtime_governance_summary", {})
        if isinstance(runtime_governance, dict) and runtime_governance.get("summary"):
            self.console.print("[yellow]运行治理提示[/yellow]")
            self.console.print(f"[dim]- {runtime_governance.get('summary')}[/dim]")
            next_actions = runtime_governance.get("next_actions", [])
            if isinstance(next_actions, list) and next_actions:
                self.console.print(f"[dim]- 建议先做: {next_actions[0]}[/dim]")
        compliance_governance = report.get("compliance_governance_summary", {})
        if isinstance(compliance_governance, dict) and compliance_governance.get("summary"):
            self.console.print("[yellow]合规治理提示[/yellow]")
            self.console.print(f"[dim]- {compliance_governance.get('summary')}[/dim]")
        if not runtime_health.get("healthy", False):
            self.console.print(
                "[yellow]运行时安装异常[/yellow]: 通常不是必须和 Python 装在同一盘，"
                "而是 `super-dev` 命令与当前 Python 不在同一环境。"
            )
            if not detail:
                self.console.print("[dim]加 --detail 可查看模块路径、残留版本与修复建议[/dim]")
        if detail:
            self.console.print(
                f"[dim]终端输出: {output_mode_label()} ({output_mode_reason()})[/dim]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            certified_count = sum(
                1
                for t in targets
                if integration_manager.get_adapter_profile(t)
                .certification_label.lower()
                .startswith("certified")
            )
            compatible_count = sum(
                1
                for t in targets
                if integration_manager.get_adapter_profile(t)
                .certification_label.lower()
                .startswith("compatible")
            )
            experimental_count = len(targets) - certified_count - compatible_count
            self.console.print(
                f"[cyan]认证分布: Certified {certified_count} / Compatible {compatible_count} / Experimental {experimental_count}[/cyan]"
            )
        self.console.print("")
        if detail:
            self._print_runtime_install_health(runtime_health)
            self.console.print("")
        ready_targets = [
            target
            for target in targets
            if bool((report.get("hosts", {}).get(target) or {}).get("ready", False))
        ]
        if ready_targets:
            self.console.print("[green]终端到此为止，回宿主这样开始[/green]")
            for line in self._build_onboard_next_steps(targets=ready_targets[:3]):
                self.console.print(f"[green]>[/green] {line}")
            self.console.print("[dim]- 先看 smoke guide 与框架焦点，再复制第一句。[/dim]")
            resume_lines = self._build_session_resume_card_lines(
                project_dir=project_dir, target=ready_targets[0]
            )
            if resume_lines:
                self.console.print("[cyan]如果你是在继续已有流程[/cyan]")
                for line in resume_lines:
                    self.console.print(f"[dim]- {line}[/dim]")
            self.console.print("")
        if args.repair:
            self.console.print("[cyan]Repair 模式已执行[/cyan]")
            if repair_actions:
                for target, actions in repair_actions.items():
                    action_text = ", ".join(f"{k}={v}" for k, v in actions.items())
                    self.console.print(f"[dim]- {self._host_label(target)}: {action_text}[/dim]")
            else:
                self.console.print("[dim]- 无需修复或未执行修复动作[/dim]")
            self.console.print("")
        if not detail:
            primary_repair = report.get("primary_repair_action", {})
            if isinstance(primary_repair, dict) and primary_repair.get("command"):
                self.console.print("[cyan]主修复动作[/cyan]")
                self.console.print(f"[dim]- 宿主: {primary_repair.get('host', '-')}[/dim]")
                if primary_repair.get("reason"):
                    self.console.print(f"[dim]- 原因: {primary_repair.get('reason')}[/dim]")
                self.console.print(f"[dim]- 先执行: {primary_repair.get('command')}[/dim]")
                secondary_actions = primary_repair.get("secondary_actions", [])
                if isinstance(secondary_actions, list) and secondary_actions:
                    self.console.print("[dim]- 备选动作:[/dim]")
                    for item in secondary_actions[:2]:
                        self.console.print(f"[dim]  • {item}[/dim]")
                self.console.print("")
            self.console.print("[dim]使用 --detail 查看路径、协议、前置条件与逐项建议[/dim]")
            self.console.print("")
        # 摘要表格
        from rich.table import Table

        summary_table = Table(
            title="宿主接入状态",
            expand=True,
            show_lines=False,
            border_style="dim",
            title_style="bold cyan",
        )
        summary_table.add_column("宿主", style="bold", min_width=18)
        summary_table.add_column("状态", justify="center", min_width=8)
        summary_table.add_column("集成规则", justify="center")
        summary_table.add_column("Skill", justify="center")
        summary_table.add_column("Slash", justify="center")
        summary_table.add_column("认证", justify="center", min_width=12)
        if detail:
            summary_table.add_column("协议", style="dim")

        for target in targets:
            host = report["hosts"][target]
            protocol = integration_manager._protocol_profile(target=target)
            protocol_summary = protocol.get("summary", "") if isinstance(protocol, dict) else ""

            status = "[green]已就绪[/green]" if host["ready"] else "[red]未安装[/red]"

            integrate_ok = bool(host.get("checks", {}).get("integrate", {}).get("ok", True))
            skill_ok = bool(host.get("checks", {}).get("skill", {}).get("ok", True))
            slash_ok = bool(host.get("checks", {}).get("slash", {}).get("ok", True))

            integrate_text = "[green]已安装[/green]" if integrate_ok else "[red]未安装[/red]"
            skill_text = (
                "[green]已安装[/green]"
                if skill_ok
                else (
                    "[dim]不适用[/dim]"
                    if not IntegrationManager.requires_skill(target)
                    else "[red]未安装[/red]"
                )
            )
            slash_text = (
                "[green]已安装[/green]"
                if slash_ok
                else (
                    "[dim]不适用[/dim]"
                    if not integration_manager.supports_slash(target)
                    else "[red]未安装[/red]"
                )
            )

            profile = integration_manager.get_adapter_profile(target)
            cert_label = profile.certification_label
            if "certified" in cert_label.lower():
                cert_text = f"[bold green]{cert_label}[/bold green]"
            elif "compatible" in cert_label.lower():
                cert_text = f"[cyan]{cert_label}[/cyan]"
            else:
                cert_text = f"[yellow]{cert_label}[/yellow]"

            row = [
                self._host_label(target),
                status,
                integrate_text,
                skill_text,
                slash_text,
                cert_text,
            ]
            if detail:
                row.append(protocol_summary)
            summary_table.add_row(*row)

        self.console.print(summary_table)
        self.console.print("")

        for target in targets:
            host = report["hosts"][target]
            if detail:
                if host["ready"]:
                    self.console.print(f"[green]✓ {self._host_label(target)}[/green] ready")
                else:
                    self.console.print(f"[red]✗ {self._host_label(target)}[/red] [red]未安装[/red]")
                    for check_name in host.get("missing", []):
                        self.console.print(f"  [red]- 缺失: {check_name}[/red]")
                    for suggestion in host.get("suggestions", []):
                        self.console.print(f"  [dim]建议: {suggestion}[/dim]")
                self._print_host_usage_guidance(
                    integration_manager=integration_manager,
                    target=target,
                    indent="  ",
                )
            elif not host["ready"]:
                missing = ", ".join(host.get("missing", []))
                self.console.print(f"[red]✗ {self._host_label(target)}[/red] 缺失: {missing}")
                diagnosis = host.get("diagnosis", {})
                suggested_command = ""
                if isinstance(diagnosis, dict):
                    blocker_summary = str(diagnosis.get("blocker_summary", "")).strip()
                    certification_reason = str(diagnosis.get("certification_reason", "")).strip()
                    suggested_command = str(diagnosis.get("suggested_command", "")).strip()
                    if blocker_summary:
                        self.console.print(f"[dim]  原因: {blocker_summary}[/dim]")
                    if certification_reason:
                        self.console.print(f"[dim]  适配说明: {certification_reason}[/dim]")
                    if suggested_command:
                        self.console.print(f"[dim]  建议动作: {suggested_command}[/dim]")
                suggestions = host.get("suggestions", [])
                if suggestions:
                    first_suggestion = str(suggestions[0]).strip()
                    if not suggested_command or first_suggestion != suggested_command:
                        self.console.print(f"[dim]  建议: {first_suggestion}[/dim]")

        self.console.print("")
        if bool(report.get("overall_ready", False)):
            self.console.print("[green]✓ Doctor 通过：所有宿主接入完整[/green]")
            return 0
        self.console.print("[red]Doctor 未通过：请按建议修复后重试[/red]")
        return 1

    def _cmd_setup(self, args) -> int:
        """一步接入：onboard + doctor"""
        # 支持 `super-dev setup claude-code` 位置参数
        target = getattr(args, "target", None)
        if target and not getattr(args, "host", None):
            args.host = target
        if self._is_manual_install_host(getattr(args, "host", None)):
            return self._print_manual_install_host_guidance(
                target=str(args.host), command_name="setup"
            )
        setup_all = bool(args.all or (bool(args.yes) and not args.host and not args.auto))
        onboard_args = argparse.Namespace(
            host=args.host,
            all=setup_all,
            auto=bool(args.auto and not args.host and not args.all),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.skip_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            yes=bool(args.yes),
            force=bool(args.force),
            dry_run=False,
            stable_only=False,
            detail=bool(getattr(args, "detail", False)),
        )
        onboard_result = self._cmd_onboard(onboard_args)
        if onboard_result != 0:
            return onboard_result
        onboard_smoke_report_paths = getattr(onboard_args, "_smoke_report_paths", None)
        if isinstance(onboard_smoke_report_paths, dict) and onboard_smoke_report_paths:
            setattr(args, "_smoke_report_paths", onboard_smoke_report_paths)

        if args.skip_doctor:
            return 0

        selected_targets = getattr(onboard_args, "_selected_targets", None)
        if isinstance(selected_targets, list) and selected_targets:
            final_code = 0
            for target in selected_targets:
                doctor_args = argparse.Namespace(
                    host=target,
                    all=False,
                    auto=False,
                    skill_name=args.skill_name,
                    skip_integrate=bool(args.skip_integrate),
                    skip_skill=bool(args.skip_skill),
                    skip_slash=bool(args.skip_slash),
                    with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
                    json=False,
                    repair=True,
                    force=bool(args.force),
                    detail=bool(getattr(args, "detail", False)),
                )
                result = self._cmd_doctor(doctor_args)
                if result != 0:
                    final_code = result
            return final_code

        doctor_args = argparse.Namespace(
            host=args.host,
            all=setup_all,
            auto=bool(args.auto and not args.host and not args.all),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.skip_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            json=False,
            repair=True,
            force=bool(args.force),
            detail=bool(getattr(args, "detail", False)),
        )
        return self._cmd_doctor(doctor_args)

    def _cmd_install(self, args) -> int:
        """面向 PyPI 用户的一键安装入口"""
        self._render_install_intro(args=args)
        if self._is_manual_install_host(getattr(args, "host", None)):
            return self._print_manual_install_host_guidance(
                target=str(args.host), command_name="install"
            )
        setup_args = argparse.Namespace(
            host=args.host,
            all=bool(args.all),
            auto=bool(args.auto),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.no_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            skip_doctor=bool(args.skip_doctor),
            force=bool(args.force),
            yes=bool(args.yes),
        )
        return self._cmd_setup(setup_args)

    def _cmd_uninstall(self, args) -> int:
        """面向 PyPI 用户的一键卸载入口。"""
        from .integrations import IntegrationManager
        from .skills import SkillManager

        if not self._ensure_host_support_matrix():
            return 1

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        dry_run = bool(getattr(args, "dry_run", False))
        available_targets = self._public_host_targets(integration_manager=integration_manager)

        if getattr(args, "host", None):
            targets = [args.host]
        elif getattr(args, "all", False):
            targets = available_targets
        elif getattr(args, "auto", False):
            detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
            targets = self._deduplicate_host_family(detected_targets)
        else:
            try:
                targets = self._resolve_onboard_targets(
                    available_targets=available_targets,
                    host=getattr(args, "host", None),
                    all_targets=bool(getattr(args, "all", False)),
                    non_interactive=bool(getattr(args, "yes", False)),
                )
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 1

        if not targets:
            message = "未检测到可清理的宿主，请改用 --host 指定或使用 --all。"
            if getattr(args, "json", False):
                sys.stdout.write(
                    json.dumps(
                        {
                            "status": "error",
                            "reason": "no-host-detected",
                            "message": message,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                )
            else:
                self.console.print(f"[yellow]{message}[/yellow]")
            return 1

        cleaned_targets: list[dict[str, Any]] = []
        for target in targets:
            preview = self._collect_uninstall_target_preview(
                integration_manager=integration_manager,
                skill_manager=skill_manager,
                target=target,
            )
            removed_paths: list[str] = []
            removed_skills: list[str] = []
            removed_skill_paths: list[str] = []
            removed_legacy_skill_aliases: list[str] = []
            removed_legacy_skill_paths: list[str] = []
            errors: list[str] = []

            if not dry_run:
                try:
                    removed = integration_manager.remove(target=target)
                    removed_paths.extend(str(item) for item in removed)
                except Exception as exc:
                    errors.append(f"surface cleanup failed: {exc}")

                if skill_manager.skill_surface_available(target):
                    for skill_name in skill_manager.managed_builtin_skill_names(target):
                        existing_paths = self._stringify_existing_paths(
                            skill_manager.managed_skill_cleanup_paths(target, skill_name)
                        )
                        try:
                            skill_manager.uninstall(skill_name, target)
                            removed_skills.append(skill_name)
                            removed_skill_paths.extend(existing_paths)
                        except FileNotFoundError:
                            continue
                        except Exception as exc:
                            errors.append(f"skill {skill_name} cleanup failed: {exc}")
                    legacy_paths = self._stringify_existing_paths(
                        skill_manager.legacy_skill_cleanup_paths(target)
                    )
                    try:
                        removed_legacy_skill_aliases.extend(
                            skill_manager.cleanup_legacy_skill_aliases(target)
                        )
                        if removed_legacy_skill_aliases:
                            removed_legacy_skill_paths.extend(legacy_paths)
                    except Exception as exc:
                        errors.append(f"legacy skill cleanup failed: {exc}")

            target_payload = {
                "target": target,
                "planned_surface_paths": preview["planned_surface_paths"],
                "planned_skill_names": preview["planned_skill_names"],
                "planned_skill_paths": preview["planned_skill_paths"],
                "planned_legacy_skill_aliases": preview["planned_legacy_skill_aliases"],
                "planned_legacy_skill_paths": preview["planned_legacy_skill_paths"],
                "missing_surface_paths": preview["missing_surface_paths"],
                "removed_paths": sorted(set(removed_paths)),
                "removed_skills": removed_skills,
                "removed_skill_paths": sorted(set(removed_skill_paths)),
                "removed_legacy_skill_aliases": removed_legacy_skill_aliases,
                "removed_legacy_skill_paths": sorted(set(removed_legacy_skill_paths)),
                "errors": errors,
            }
            cleaned_targets.append(target_payload)

        removed_path_count = sum(
            len(item["planned_surface_paths"] if dry_run else item["removed_paths"])
            for item in cleaned_targets
        )
        removed_skill_count = sum(
            len(item["planned_skill_names"] if dry_run else item["removed_skills"])
            for item in cleaned_targets
        )
        legacy_skill_count = sum(
            len(
                item["planned_legacy_skill_aliases"]
                if dry_run
                else item["removed_legacy_skill_aliases"]
            )
            for item in cleaned_targets
        )
        error_count = sum(len(item["errors"]) for item in cleaned_targets)
        payload = {
            "status": "preview" if dry_run else ("ok" if error_count == 0 else "partial"),
            "dry_run": dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "targets": cleaned_targets,
            "removed_path_count": removed_path_count,
            "removed_skill_count": removed_skill_count,
            "removed_legacy_skill_count": legacy_skill_count,
            "error_count": error_count,
            "summary": (
                (
                    f"预演 {len(cleaned_targets)} 个宿主，"
                    f"将清理 {removed_path_count} 个接入面路径，"
                    f"{removed_skill_count} 个技能目录，"
                    f"{legacy_skill_count} 个旧技能别名"
                )
                if dry_run
                else (
                    f"已处理 {len(cleaned_targets)} 个宿主，"
                    f"清理 {removed_path_count} 个接入面路径，"
                    f"{removed_skill_count} 个技能目录，"
                    f"{legacy_skill_count} 个旧技能别名"
                )
            ),
        }
        report_files = self._write_cleanup_report(project_dir=project_dir, payload=payload)
        payload["report_files"] = report_files
        payload["report_path"] = report_files["json"]
        Path(report_files["json"]).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0 if error_count == 0 else 1

        style = "green" if error_count == 0 else "yellow"
        self.console.print(f"[{style}]✓ {payload['summary']}[/{style}]")
        for item in cleaned_targets:
            self.console.print(f"  - {self._host_label(item['target'])}")
            surface_count = len(item["planned_surface_paths"] if dry_run else item["removed_paths"])
            skill_names = item["planned_skill_names"] if dry_run else item["removed_skills"]
            legacy_names = (
                item["planned_legacy_skill_aliases"]
                if dry_run
                else item["removed_legacy_skill_aliases"]
            )
            if surface_count:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'}接入面: {surface_count} 项"
                )
            if skill_names:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'} Skill: {', '.join(skill_names)}"
                )
            if legacy_names:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'}旧技能别名: {', '.join(legacy_names)}"
                )
            if item["errors"]:
                for error in item["errors"]:
                    self.console.print(f"    [yellow]⚠ {error}[/yellow]")
        self.console.print(f"[dim]Cleanup report: {report_files['json']}[/dim]")
        self.console.print(f"[dim]Cleanup summary: {report_files['markdown']}[/dim]")
        self.console.print("")
        if dry_run:
            self.console.print(
                Panel(
                    "[bold cyan]卸载预演完成[/bold cyan]\n\n"
                    "  这次只是预演，不会删除任何接入面。\n"
                    "  先看 cleanup report，再决定是否真的清理。",
                    border_style="cyan",
                    expand=True,
                    padding=(1, 2),
                )
            )
        elif error_count == 0:
            self.console.print(
                Panel(
                    "[bold green]卸载完成[/bold green]\n\n"
                    "  当前项目里的 Super Dev 接入面已经清理完成。\n"
                    "  如果之后还要继续用，回到项目目录重新运行 `super-dev` 即可。",
                    border_style="green",
                    expand=True,
                    padding=(1, 2),
                )
            )
        else:
            self.console.print(
                Panel(
                    "[bold yellow]卸载完成（部分异常）[/bold yellow]\n\n"
                    "  大部分接入面已处理，但还有少量清理异常。\n"
                    "  先看 cleanup report；如果要继续排查，再运行 `super-dev uninstall --dry-run` 对照核查。",
                    border_style="yellow",
                    expand=True,
                    padding=(1, 2),
                )
            )
        return 0 if error_count == 0 else 1

    def _cmd_start(self, args) -> int:
        """面向非技术用户的起步入口：自动选宿主、接入并输出最短试用路径。"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1
        if self._is_manual_install_host(getattr(args, "host", None)):
            return self._print_manual_install_host_guidance(
                target=str(args.host), command_name="start"
            )

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        available_targets = self._public_host_targets(integration_manager=integration_manager)
        detected_targets, detected_meta = self._detect_host_targets(
            available_targets=available_targets
        )
        detected_targets = self._deduplicate_host_family(detected_targets)

        target = args.host
        selection_reason = "manual"
        if not target:
            if detected_targets:
                target = self._select_best_start_host(
                    integration_manager=integration_manager,
                    targets=detected_targets,
                )
                selection_reason = "auto-detected"
            else:
                decision_card = self._build_no_host_decision_card(
                    integration_manager=integration_manager
                )
                payload = {
                    "status": "error",
                    "reason": "no-host-detected",
                    "message": "未检测到可用宿主，请先安装受支持宿主后重试。",
                    "path_override_hint": decision_card["path_override_hint"],
                    "recommended_hosts": decision_card["recommended_hosts"],
                    "decision_card": decision_card,
                }
                if args.json:
                    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                else:
                    self.console.print("[red]未检测到可用宿主[/red]")
                    self.console.print(f"[dim]{decision_card['summary']}[/dim]")
                    for line in decision_card["lines"]:
                        self.console.print(f"[dim]- {line}[/dim]")
                    self.console.print("[cyan]优先建议安装这些宿主:[/cyan]")
                    for host in decision_card["recommended_hosts"]:
                        self.console.print(f"  - {host['name']} [{host['certification_label']}]")
                return 1

        usage = self._build_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        framework_playbook = load_framework_playbook_summary(project_dir)
        onboard_smoke_report_paths: dict[str, Any] = {}

        onboard_performed = False
        if not bool(args.skip_onboard):
            setup_args = argparse.Namespace(
                host=target,
                all=False,
                auto=False,
                skill_name="super-dev",
                skip_integrate=False,
                skip_skill=False,
                skip_slash=False,
                with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
                skip_doctor=False,
                yes=True,
                force=bool(args.force),
            )
            if args.json:
                with contextlib.redirect_stdout(io.StringIO()):
                    onboard_result = self._cmd_setup(setup_args)
            else:
                onboard_result = self._cmd_setup(setup_args)
            onboard_performed = True
            if onboard_result != 0:
                return onboard_result
            if isinstance(getattr(setup_args, "_smoke_report_paths", {}), dict):
                onboard_smoke_report_paths = dict(getattr(setup_args, "_smoke_report_paths", {}))

        profile_saved = False
        profile_save_error = ""
        if not bool(args.no_save_profile):
            try:
                ConfigManager(project_dir).update(
                    host_profile_targets=[target],
                    host_profile_enforce_selected=True,
                )
                profile_saved = True
            except Exception as exc:
                profile_save_error = str(exc)

        session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
        session_resume_card = self._build_session_resume_card(
            project_dir=project_dir, target=target
        )
        decision_card = self._build_detected_host_decision_card(
            project_dir=project_dir,
            integration_manager=integration_manager,
            detected_targets=detected_targets,
            detected_meta=detected_meta,
            preferred_targets=[target],
        )
        quick_start = self._build_host_quick_start_text(
            host_profile=usage,
            host_id=target,
            host_name=self._host_label(target),
            idea=args.idea,
            session_hint=session_hint,
            framework_playbook=framework_playbook,
        )
        payload = {
            "status": "success",
            "project_dir": str(project_dir),
            "selected_host": target,
            "selected_host_name": self._host_label(target),
            "selection_reason": selection_reason,
            "detected_hosts": detected_targets,
            "detection_details": detected_meta,
            "detection_details_pretty": self._explain_detection_details(detected_meta),
            "onboard_performed": onboard_performed,
            "profile_saved": profile_saved,
            "profile_save_error": profile_save_error,
            "usage_profile": usage,
            "selected_host_experience": dict(usage.get("experience_profile", {}))
            if isinstance(usage.get("experience_profile", {}), dict)
            else {},
            "selected_host_post_onboard_self_check": (
                list(decision_card.get("selected_host_post_onboard_self_check", []))
                if isinstance(
                    decision_card.get("selected_host_post_onboard_self_check", []),
                    list,
                )
                else []
            ),
            "selected_host_start_playbook": (
                list(decision_card.get("selected_host_start_playbook", []))
                if isinstance(decision_card.get("selected_host_start_playbook", []), list)
                else []
            ),
            "selected_host_standard_flow_first_prompt": str(
                decision_card.get("selected_host_standard_flow_first_prompt", "")
            ).strip(),
            "selected_host_competition_flow_first_prompt": str(
                decision_card.get("selected_host_competition_flow_first_prompt", "")
            ).strip(),
            "selected_host_resume_guidance": (
                list(decision_card.get("selected_host_resume_guidance", []))
                if isinstance(decision_card.get("selected_host_resume_guidance", []), list)
                else []
            ),
            "selected_host_injection_closure": (
                dict(decision_card.get("selected_host_injection_closure", {}))
                if isinstance(decision_card.get("selected_host_injection_closure", {}), dict)
                else {}
            ),
            "selected_host_ready_for_standard_flow": bool(
                decision_card.get("selected_host_ready_for_standard_flow", False)
            ),
            "selected_host_ready_for_competition_flow": bool(
                decision_card.get("selected_host_ready_for_competition_flow", False)
            ),
            "selected_host_standard_flow_label": str(
                decision_card.get("selected_host_standard_flow_label", "")
            ).strip(),
            "selected_host_competition_flow_label": str(
                decision_card.get("selected_host_competition_flow_label", "")
            ).strip(),
            "selected_host_official_workflow_checks": (
                list(decision_card.get("selected_host_official_workflow_checks", []))
                if isinstance(
                    decision_card.get("selected_host_official_workflow_checks", []),
                    list,
                )
                else []
            ),
            "selected_host_repair_playbook": str(
                decision_card.get("selected_host_repair_playbook", "")
            ).strip(),
            "selected_host_adaptation": dict(usage.get("adaptation_contract", {}))
            if isinstance(usage.get("adaptation_contract", {}), dict)
            else {},
            "selected_host_framework_playbook": framework_playbook,
            "session_mode": session_hint.get("session_mode", "fresh_start"),
            "continue_prompt": session_hint.get("continue_prompt", ""),
            "recommended_workflow_command": session_hint.get("recommended_workflow_command", ""),
            "workflow_reason": session_hint.get("workflow_reason", ""),
            "workflow_context": (
                dict(decision_card.get("workflow_context", {}))
                if isinstance(decision_card.get("workflow_context", {}), dict)
                else {}
            ),
            "session_resume_card": session_resume_card,
            "decision_card": decision_card,
            "runtime_install_health": self._collect_runtime_install_health(),
            "recommended_trigger": self._build_host_trigger_example(target=target, idea=args.idea),
            "quick_start": quick_start,
            "onboard_smoke_report_paths": onboard_smoke_report_paths,
        }

        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        profile = integration_manager.get_adapter_profile(target)
        self.console.print("[cyan]Super Dev Start[/cyan]")
        self.console.print(f"[cyan]已选择宿主[/cyan]: {self._host_label(target)}")
        self.console.print(
            f"[cyan]认证等级[/cyan]: {profile.certification_label} ({profile.certification_level})"
        )
        experience = payload.get("selected_host_experience", {})
        if isinstance(experience, dict) and experience:
            self.console.print(
                f"[cyan]宿主画像[/cyan]: {experience.get('label', '-')} / "
                f"{experience.get('best_for', '-')}"
            )
            native_resume = experience.get("native_resume", [])
            if isinstance(native_resume, list) and native_resume:
                self.console.print(
                    f"[dim]推荐恢复: {' / '.join(str(item) for item in native_resume[:2])}[/dim]"
                )
        if isinstance(framework_playbook, dict) and framework_playbook:
            self.console.print(
                f"[cyan]框架教练焦点[/cyan]: {framework_playbook.get('framework', '-')}"
            )
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if isinstance(validation_surfaces, list) and validation_surfaces:
                self.console.print(
                    "[dim]必验场景: "
                    + "；".join(str(item) for item in validation_surfaces[:4])
                    + "[/dim]"
                )
        standard_prompt = str(payload.get("selected_host_standard_flow_first_prompt", "")).strip()
        competition_prompt = str(
            payload.get("selected_host_competition_flow_first_prompt", "")
        ).strip()
        if standard_prompt:
            self.console.print(f"[cyan]标准流第一句[/cyan]: {standard_prompt}")
        if competition_prompt:
            self.console.print(f"[cyan]比赛流第一句[/cyan]: {competition_prompt}")
        if selection_reason == "auto-detected":
            reasons = ", ".join(detected_meta.get(target, []))
            if reasons:
                self.console.print(f"[dim]自动选择依据: {reasons}[/dim]")
        if decision_card.get("scenario") == "multi-host-detected":
            self.console.print(f"[cyan]{decision_card.get('title', '已检测到宿主')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")
        self.console.print(f"[dim]{profile.certification_reason}[/dim]")
        if profile_saved:
            self.console.print("[green]✓[/green] 已写入宿主画像到 super-dev.yaml")
        elif profile_save_error:
            self.console.print(f"[yellow]宿主画像写入失败: {profile_save_error}[/yellow]")
        self.console.print("")
        onboard_report_paths = payload.get("onboard_smoke_report_paths", {})
        if isinstance(onboard_report_paths, dict) and onboard_report_paths.get("markdown"):
            self.console.print(f"[dim]Onboard smoke guide: {onboard_report_paths['markdown']}[/dim]")
        self.console.print(quick_start)
        return 0

    def _cmd_detect(self, args) -> int:
        """宿主探测 + 接入兼容性评分"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        if self._is_manual_install_host(getattr(args, "host", None)):
            targets = [str(args.host)]
            available_targets = targets
        else:
            available_targets = self._public_host_targets(integration_manager=integration_manager)
        detected_targets, detected_meta = self._detect_host_targets(
            available_targets=available_targets
        )

        if args.host:
            targets = [args.host]
        elif args.all:
            targets = available_targets
        else:
            targets = detected_targets

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=args.skill_name,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )

        payload: dict[str, Any] = {
            "project_dir": str(project_dir),
            "detected_hosts": detected_targets,
            "detection_details": detected_meta,
            "detection_details_pretty": self._explain_detection_details(detected_meta),
            "selected_targets": targets,
            "decision_card": self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=detected_targets,
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            ),
            "report": report,
            "compatibility": compatibility,
            "session_resume_cards": {
                target: self._build_session_resume_card(project_dir=project_dir, target=target)
                for target in targets
            },
            "usage_profiles": {
                target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
                for target in targets
            },
        }
        payload["adaptation_contracts"] = {
            target: dict(usage.get("adaptation_contract", {}))
            for target, usage in payload["usage_profiles"].items()
            if isinstance(usage, dict) and isinstance(usage.get("adaptation_contract", {}), dict)
        }
        payload["experience_profiles"] = {
            target: dict(usage.get("experience_profile", {}))
            for target, usage in payload["usage_profiles"].items()
            if isinstance(usage, dict) and isinstance(usage.get("experience_profile", {}), dict)
        }
        selected_host = str(payload["decision_card"].get("selected_host", "")).strip()
        payload["selected_host_adaptation"] = (
            dict(payload["adaptation_contracts"].get(selected_host, {}))
            if selected_host in payload["adaptation_contracts"]
            else {}
        )
        payload["selected_host_experience"] = (
            dict(payload["experience_profiles"].get(selected_host, {}))
            if selected_host in payload["experience_profiles"]
            else {}
        )
        payload["selected_host_post_onboard_self_check"] = (
            list(payload["decision_card"].get("selected_host_post_onboard_self_check", []))
            if isinstance(
                payload["decision_card"].get("selected_host_post_onboard_self_check", []),
                list,
            )
            else []
        )
        payload["selected_host_start_playbook"] = (
            list(payload["decision_card"].get("selected_host_start_playbook", []))
            if isinstance(payload["decision_card"].get("selected_host_start_playbook", []), list)
            else []
        )
        payload["selected_host_standard_flow_first_prompt"] = str(
            payload["decision_card"].get("selected_host_standard_flow_first_prompt", "")
        ).strip()
        payload["selected_host_competition_flow_first_prompt"] = str(
            payload["decision_card"].get("selected_host_competition_flow_first_prompt", "")
        ).strip()
        payload["selected_host_resume_guidance"] = (
            list(payload["decision_card"].get("selected_host_resume_guidance", []))
            if isinstance(payload["decision_card"].get("selected_host_resume_guidance", []), list)
            else []
        )
        payload["selected_host_injection_closure"] = (
            dict(payload["decision_card"].get("selected_host_injection_closure", {}))
            if isinstance(payload["decision_card"].get("selected_host_injection_closure", {}), dict)
            else {}
        )
        payload["selected_host_ready_for_standard_flow"] = bool(
            payload["decision_card"].get("selected_host_ready_for_standard_flow", False)
        )
        payload["selected_host_ready_for_competition_flow"] = bool(
            payload["decision_card"].get("selected_host_ready_for_competition_flow", False)
        )
        payload["selected_host_standard_flow_label"] = str(
            payload["decision_card"].get("selected_host_standard_flow_label", "")
        ).strip()
        payload["selected_host_competition_flow_label"] = str(
            payload["decision_card"].get("selected_host_competition_flow_label", "")
        ).strip()
        payload["selected_host_official_workflow_checks"] = (
            list(payload["decision_card"].get("selected_host_official_workflow_checks", []))
            if isinstance(
                payload["decision_card"].get("selected_host_official_workflow_checks", []),
                list,
            )
            else []
        )
        payload["selected_host_repair_playbook"] = str(
            payload["decision_card"].get("selected_host_repair_playbook", "")
        ).strip()
        payload["workflow_context"] = (
            dict(payload["decision_card"].get("workflow_context", {}))
            if isinstance(payload["decision_card"].get("workflow_context", {}), dict)
            else {}
        )
        if not bool(args.no_save):
            report_files = self._write_host_compatibility_report(
                project_dir=project_dir, payload=payload
            )
            payload["report_files"] = {name: str(path) for name, path in report_files.items()}

        if bool(args.save_profile):
            try:
                config_manager = ConfigManager(project_dir)
                config_manager.update(
                    host_profile_targets=targets,
                    host_profile_enforce_selected=True,
                )
                payload["host_profile_updated"] = True
            except Exception as exc:
                payload["host_profile_updated"] = False
                payload["host_profile_update_error"] = str(exc)

        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self.console.print("[cyan]Super Dev Host Detect[/cyan]")
        self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
        if detected_targets:
            self.console.print(
                f"[cyan]自动检测到 {len(detected_targets)} 个宿主：{', '.join(self._host_label(target) for target in detected_targets)}[/cyan]"
            )
            for target in detected_targets:
                reasons = ", ".join(
                    self._format_detection_reason(item) for item in detected_meta.get(target, [])
                )
                if reasons:
                    self.console.print(f"[dim]  - {self._host_label(target)}: {reasons}[/dim]")
        else:
            self.console.print("[yellow]未检测到宿主（可用 --all 查看全部兼容评分）[/yellow]")
        decision_card = payload.get("decision_card", {})
        if isinstance(decision_card, dict) and decision_card.get("lines"):
            self.console.print("")
            self.console.print(f"[cyan]{decision_card.get('title', '宿主决策')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")

        self.console.print("")
        self.console.print(
            f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
            f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
        )
        self.console.print(
            f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
            f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
        )
        for target in targets:
            host_compat = compatibility["hosts"].get(target, {})
            score = host_compat.get("score", 0.0)
            ready = bool(host_compat.get("ready", False))
            badge = "[green]ready[/green]" if ready else "[yellow]not-ready[/yellow]"
            self.console.print(f"  - {self._host_label(target)}: {score:.2f}/100 {badge}")
        if targets:
            guidance_target = self._select_best_start_host(
                integration_manager=integration_manager,
                targets=targets,
            )
            resume_card = self._build_session_resume_card(
                project_dir=project_dir, target=guidance_target
            )
            if bool(resume_card.get("enabled", False)):
                self.console.print("")
                self.console.print("[cyan]如果你是在继续已有流程[/cyan]")
                for line in resume_card.get("lines", []):
                    self.console.print(f"[dim]- {line}[/dim]")
            self._print_host_usage_guidance(
                integration_manager=integration_manager,
                target=guidance_target,
                indent="    ",
            )
        if not bool(args.no_save):
            saved_report_files = payload.get("report_files", {})
            if isinstance(saved_report_files, dict):
                json_file = saved_report_files.get("json")
                md_file = saved_report_files.get("markdown")
                if isinstance(json_file, str) and isinstance(md_file, str):
                    self.console.print(f"[dim]报告: {md_file}[/dim]")
                    self.console.print(f"[dim]数据: {json_file}[/dim]")
        if bool(args.save_profile):
            if bool(payload.get("host_profile_updated", False)):
                self.console.print(
                    "[green]✓[/green] 已更新宿主画像: host_profile_targets + host_profile_enforce_selected"
                )
            else:
                err = payload.get("host_profile_update_error", "")
                self.console.print(f"[yellow]宿主画像更新失败: {err}[/yellow]")

        # --auto: 检测完成后自动安装 skill + rules + hooks 到检测到的主要宿主
        if getattr(args, "auto", False) and detected_targets:
            auto_install_targets = [t for t in detected_targets if t in PRIMARY_HOST_TOOL_IDS]
            if not auto_install_targets:
                auto_install_targets = detected_targets[:3]
            self.console.print("")
            self.console.print("[cyan]自动安装到检测到的宿主...[/cyan]")
            for target in auto_install_targets:
                try:
                    written = integration_manager.setup(target=target, force=True)
                    if written:
                        self.console.print(
                            f"  [green]✓[/green] {self._host_label(target)}: "
                            f"已写入 {len(written)} 个文件"
                        )
                except Exception as exc:
                    self.console.print(f"  [yellow]⚠[/yellow] {self._host_label(target)}: {exc}")
            # 自动安装 enforcement hooks (仅 claude-code)
            try:
                from .enforcement import HostHooksConfigurator

                configurator = HostHooksConfigurator(project_dir)
                for target in auto_install_targets:
                    if target in ("claude-code",):
                        configurator.install_hooks(target)
                        self.console.print(
                            f"  [green]✓[/green] {self._host_label(target)}: "
                            "enforcement hooks 已安装"
                        )
            except Exception:
                pass  # enforcement 模块可选
            self.console.print("[green]自动安装完成[/green]")

        return 0

    def _cmd_clean(self, args) -> int:
        """清理历史产物文件"""
        project_dir = Path.cwd()
        output_dir = project_dir / get_config_manager(project_dir).config.output_dir

        if not output_dir.exists():
            self.console.print("[yellow]output/ 目录不存在，无需清理[/yellow]")
            return 0

        # 收集所有产物文件（按修改时间排序）
        artifact_extensions = {".md", ".json", ".html", ".css", ".js", ".tar.gz", ".zip"}
        all_files: list[Path] = []
        for f in output_dir.rglob("*"):
            if f.is_file() and (f.suffix in artifact_extensions or ".tar" in f.name):
                all_files.append(f)

        if not all_files:
            self.console.print("[green]output/ 目录已是干净状态[/green]")
            return 0

        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        if args.all:
            files_to_delete = all_files
        else:
            # 按项目名分组，每组保留最近 keep 个文件
            import re as _re
            from collections import defaultdict

            # 已知的产物后缀模式
            artifact_suffixes = [
                "-prd",
                "-architecture",
                "-uiux",
                "-research",
                "-execution-plan",
                "-frontend-blueprint",
                "-redteam",
                "-quality-gate",
                "-code-review",
                "-ai-prompt",
                "-release-readiness",
                "-pipeline-metrics",
                "-ui-review",
                "-proof-pack",
                "-contract-report",
                "-knowledge-bundle",
                "-frontend-runtime",
                "-repo-map",
                "-dependency-graph",
                "-feature-checklist",
                "-resume-audit",
                "-rehearsal-report",
            ]

            groups: dict[str, list[Path]] = defaultdict(list)
            for f in all_files:
                name = f.stem
                matched = False
                for suffix in artifact_suffixes:
                    if name.endswith(suffix):
                        name = name[: -len(suffix)]
                        matched = True
                        break
                if not matched:
                    # 尝试正则提取（处理未知后缀）
                    m = _re.match(r"^(.+?)(?:-[a-z]+-[a-z]+)$", name)
                    if m:
                        name = m.group(1)
                groups[name].append(f)

            files_to_delete = []
            for _group_name, group_files in groups.items():
                group_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                keep_count = args.keep
                if len(group_files) > keep_count:
                    files_to_delete.extend(group_files[keep_count:])

        if not files_to_delete:
            self.console.print(f"[green]无需清理（当前保留最近 {args.keep} 次运行的产物）[/green]")
            return 0

        self.console.print(f"[cyan]将清理 {len(files_to_delete)} 个文件：[/cyan]")
        for f in files_to_delete[:20]:
            try:
                rel = f.relative_to(project_dir)
            except ValueError:
                rel = f.name
            self.console.print(f"  [dim]{rel}[/dim]")
        if len(files_to_delete) > 20:
            self.console.print(f"  [dim]... 及其他 {len(files_to_delete) - 20} 个文件[/dim]")

        if args.dry_run:
            self.console.print("[yellow]--dry-run 模式，未实际删除[/yellow]")
            return 0

        deleted = 0
        for f in files_to_delete:
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass

        # 清理空目录
        for d in sorted(output_dir.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError:
                    pass

        self.console.print(f"[green]已清理 {deleted} 个文件[/green]")
        return 0

    def _cmd_update(self, args) -> int:
        latest_version = self._fetch_latest_pypi_version()
        if latest_version is None:
            self.console.print("[red]无法获取 PyPI 最新版本信息，请检查网络后重试[/red]")
            return 1

        current_version = __version__
        self.console.print(f"[cyan]当前版本[/cyan]: {current_version}")
        self.console.print(f"[cyan]PyPI 最新版本[/cyan]: {latest_version}")

        method = self._resolve_update_method(args.method)
        if args.check:
            if self._is_version_newer(latest_version, current_version):
                self.console.print(
                    "[yellow]发现新版本，可执行 `super-dev update` 完成升级[/yellow]"
                )
            elif self._version_key(current_version) > self._version_key(latest_version):
                self.console.print(
                    "[yellow]当前本地版本高于 PyPI 最新版本，可能是尚未发布的开发版本[/yellow]"
                )
            else:
                self.console.print("[green]✓ 当前已是最新版本[/green]")
            return 0

        if self._version_key(current_version) > self._version_key(latest_version):
            self.console.print(
                "[yellow]当前本地版本高于 PyPI 最新版本，将继续执行升级命令以刷新当前安装[/yellow]"
            )
        elif not self._is_version_newer(latest_version, current_version):
            self.console.print(
                "[green]当前版本已与 PyPI 一致，将继续执行升级命令以确保安装状态最新[/green]"
            )

        self.console.print(f"[cyan]升级方式[/cyan]: {method}")
        command = self._build_update_command(method=method)
        self.console.print(f"[dim]执行命令: {' '.join(command)}[/dim]")

        # Windows 下 uv tool upgrade 可能因文件锁定失败，提供重试机制
        max_retries = 3 if sys.platform == "win32" and method == "uv" else 1
        completed = None
        for attempt in range(max_retries):
            try:
                from . import cli as cli_module

                completed = cli_module.subprocess.run(command, check=False)
                if completed.returncode == 0:
                    break
                if attempt < max_retries - 1 and sys.platform == "win32":
                    self.console.print(
                        f"[yellow]升级失败（尝试 {attempt + 1}/{max_retries}），"
                        "Windows 下文件可能被占用，等待 2 秒后重试...[/yellow]"
                    )
                    import time

                    time.sleep(2)
            except FileNotFoundError:
                self.console.print(f"[red]未找到升级工具: {method}[/red]")
                return 1

        if completed is None or completed.returncode != 0:
            if sys.platform == "win32" and method == "uv":
                self.console.print("")
                self.console.print(
                    "[red]升级失败：Windows 下 super-dev.exe 可能被其他进程占用[/red]\n"
                    "[yellow]请按以下步骤操作：[/yellow]\n"
                    "  1. 关闭所有使用 super-dev 的终端窗口\n"
                    "  2. 打开新的终端\n"
                    "  3. 执行: uv tool upgrade super-dev\n"
                    "  [dim]如果仍然失败，尝试: uv tool install super-dev --force --reinstall[/dim]"
                )
            else:
                self.console.print("[red]升级失败，请根据上面的命令手动执行[/red]")
            return completed.returncode if completed else 1

        from rich.panel import Panel

        self.console.print("")
        self.console.print("[green]✓ 升级完成[/green]")

        # 升级后自动清理旧版本残留
        runtime_health = self._collect_runtime_install_health()
        if not runtime_health.get("healthy", False):
            self.console.print("[cyan]正在清理旧版本残留...[/cyan]")
            self._auto_fix_runtime_install(runtime_health)

        # Auto-migrate using the newly installed version (new process)
        self.console.print("[cyan]正在自动迁移宿主配置到新版...[/cyan]")
        try:
            from . import cli as cli_module

            migrate_result = cli_module.subprocess.run(["super-dev", "migrate"], check=False)
            if migrate_result.returncode == 0:
                self.console.print("[green]✓ 宿主配置已迁移到新版[/green]")
            else:
                self.console.print("[yellow]自动迁移未完成，可手动执行: super-dev migrate[/yellow]")
        except Exception:
            self.console.print("[yellow]自动迁移未执行，可手动执行: super-dev migrate[/yellow]")

        # After migrate, refresh all installed skills to current version
        self.console.print("[cyan]正在刷新已安装的宿主 Skills...[/cyan]")
        try:
            from .skills import SkillManager

            skill_manager = SkillManager(Path.cwd())
            refreshed = skill_manager.refresh_all_installed()
            if refreshed:
                self.console.print(f"[green]✓ 已刷新 {len(refreshed)} 个宿主的 Skills[/green]")
        except Exception:
            self.console.print(
                "[yellow]Skills 刷新未完成，可手动执行: super-dev setup --all --force[/yellow]"
            )

        self.console.print("")
        self.console.print(
            Panel(
                "[bold green]升级完成[/bold green]\n\n"
                "  [dim]当前终端进程仍可能加载旧版代码。[/dim]\n"
                "  [dim]下一步：重开终端，先执行 super-dev --version。[/dim]\n"
                "  [dim]如果宿主后续没有进入 research -> 三文档 -> 等待确认，再回终端运行 doctor。[/dim]",
                border_style="green",
                expand=True,
                padding=(1, 2),
            )
        )
        return 0

    def _fetch_latest_pypi_version(self) -> str | None:
        try:
            from . import cli as cli_module

            if cli_module.requests is None:
                return None
            response = cli_module.requests.get("https://pypi.org/pypi/super-dev/json", timeout=10)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return None
        info = payload.get("info", {})
        version = info.get("version")
        return version if isinstance(version, str) and version.strip() else None

    def _resolve_update_method(self, preferred: str) -> str:
        if preferred in {"pip", "uv"}:
            return preferred
        uv_binary = shutil.which("uv")
        runtime_markers = [
            sys.executable,
            shutil.which("super-dev") or "",
            os.environ.get("UV_TOOL_BIN_DIR", ""),
            os.environ.get("PATH", ""),
        ]
        if uv_binary and any(
            ".local/share/uv" in marker or "/uv/tools/" in marker for marker in runtime_markers
        ):
            return "uv"
        return "uv" if uv_binary and "uv" in sys.executable.lower() else "pip"

    def _build_update_command(self, *, method: str) -> list[str]:
        if method == "uv":
            return ["uv", "tool", "upgrade", "super-dev"]
        return [sys.executable, "-m", "pip", "install", "-U", "super-dev"]

    def _is_version_newer(self, latest: str, current: str) -> bool:
        return self._version_key(latest) > self._version_key(current)

    def _version_key(self, version: str) -> tuple[int, ...]:
        parts = []
        for part in version.replace("-", ".").split("."):
            digits = "".join(ch for ch in part if ch.isdigit())
            parts.append(int(digits or 0))
        return tuple(parts)

    def _print_host_usage_guidance(
        self,
        *,
        integration_manager,
        target: str,
        indent: str = "",
    ) -> None:
        usage = self._build_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        self.console.print(f"{indent}[cyan]主入口[/cyan]: {usage['primary_entry']}")
        self.console.print(
            f"{indent}认证等级: {usage['certification_label']} ({usage['certification_level']})"
        )
        self.console.print(f"{indent}使用模式: {usage['usage_mode']}")
        adaptation = usage.get("adaptation_contract", {})
        if isinstance(adaptation, dict) and adaptation:
            score = adaptation.get("score", 0)
            level = adaptation.get("level", "")
            self.console.print(f"{indent}适配成熟度: {score}/100 ({level})")
            official_alignment = adaptation.get("official_alignment", {})
            if isinstance(official_alignment, dict) and official_alignment:
                alignment_label = str(official_alignment.get("label", "")).strip()
                alignment_summary = str(official_alignment.get("summary", "")).strip()
                if alignment_label or alignment_summary:
                    text = " / ".join(
                        item for item in [alignment_label, alignment_summary] if item
                    )
                    self.console.print(f"{indent}官方对齐: {text}")
            dimensions = adaptation.get("dimensions", {})
            if isinstance(dimensions, dict) and dimensions:
                dimension_summary = ", ".join(
                    f"{name}={str(info.get('status', 'missing')).strip()}"
                    for name, info in dimensions.items()
                    if isinstance(info, dict)
                )
                if dimension_summary:
                    self.console.print(f"{indent}适配维度: {dimension_summary}")
                gaps = [
                    str(gap).strip()
                    for info in dimensions.values()
                    if isinstance(info, dict)
                    for gap in info.get("gaps", [])
                    if str(gap).strip()
                ]
                if gaps:
                    self.console.print(f"{indent}主要缺口: {'; '.join(gaps[:3])}")
        experience = usage.get("experience_profile", {})
        if isinstance(experience, dict) and experience:
            self.console.print(
                f"{indent}宿主画像: {experience.get('label', '-')} / {experience.get('best_for', '-')}"
            )
            resume_style = str(experience.get("resume_style", "")).strip()
            if resume_style:
                self.console.print(f"{indent}恢复风格: {resume_style}")
            strengths = experience.get("strengths", [])
            if isinstance(strengths, list) and strengths:
                self.console.print(
                    f"{indent}宿主强项: {' / '.join(str(item) for item in strengths[:3])}"
                )
            preferred_entries = experience.get("preferred_entries", [])
            if isinstance(preferred_entries, list) and preferred_entries:
                self.console.print(
                    f"{indent}推荐入口变体: {' / '.join(str(item) for item in preferred_entries[:2])}"
                )
            native_resume = experience.get("native_resume", [])
            if isinstance(native_resume, list) and native_resume:
                self.console.print(
                    f"{indent}推荐恢复方式: {' / '.join(str(item) for item in native_resume[:2])}"
                )
        protocol_mode = str(usage.get("host_protocol_mode", "")).strip()
        protocol_summary = str(usage.get("host_protocol_summary", "")).strip()
        if protocol_mode or protocol_summary:
            protocol_text = protocol_summary or protocol_mode
            if protocol_mode and protocol_summary and protocol_mode != protocol_summary:
                protocol_text = f"{protocol_summary} ({protocol_mode})"
            self.console.print(f"{indent}宿主协议: {protocol_text}")
        self.console.print(f"{indent}触发命令: {usage['trigger_command']}")
        self.console.print(f"{indent}触发上下文: {usage['trigger_context']}")
        self.console.print(f"{indent}触发位置: {usage['usage_location']}")
        self.console.print(f"{indent}接入后重启: {usage['restart_required_label']}")
        precondition_label = usage.get("precondition_label", "")
        if isinstance(precondition_label, str) and precondition_label.strip():
            self.console.print(f"{indent}宿主前置条件: {precondition_label}")
        precondition_items = usage.get("precondition_items", [])
        if isinstance(precondition_items, list) and precondition_items:
            self.console.print(f"{indent}前置条件项:")
            for item in precondition_items:
                if not isinstance(item, dict):
                    continue
                item_label = str(item.get("label", "")).strip()
                item_status = str(item.get("status", "")).strip()
                item_text = item_label or item_status
                if item_text:
                    self.console.print(f"{indent}  - {item_text}")
        precondition_guidance = usage.get("precondition_guidance", [])
        if isinstance(precondition_guidance, list) and precondition_guidance:
            self.console.print(f"{indent}前置条件说明:")
            for item in precondition_guidance:
                self.console.print(f"{indent}  - {item}")
        if usage.get("certification_reason"):
            self.console.print(f"{indent}认证说明: {usage['certification_reason']}")
        official_project = usage.get("official_project_surfaces", [])
        if isinstance(official_project, list) and official_project:
            self.console.print(f"{indent}官方项目级接入面:")
            for item in official_project:
                self.console.print(f"{indent}  - {item}")
        official_user = usage.get("official_user_surfaces", [])
        if isinstance(official_user, list) and official_user:
            self.console.print(f"{indent}默认用户级 Skill 面:")
            for item in official_user:
                self.console.print(f"{indent}  - {item}")
        optional_project = usage.get("optional_project_surfaces", [])
        if isinstance(optional_project, list) and optional_project:
            self.console.print(f"{indent}可选项目增强面:")
            for item in optional_project:
                self.console.print(f"{indent}  - {item}")
        optional_user = usage.get("optional_user_surfaces", [])
        if isinstance(optional_user, list) and optional_user:
            self.console.print(f"{indent}显式用户级增强面 (--with-user-surfaces):")
            for item in optional_user:
                self.console.print(f"{indent}  - {item}")
        observed_surfaces = usage.get("observed_compatibility_surfaces", [])
        if isinstance(observed_surfaces, list) and observed_surfaces:
            self.console.print(f"{indent}兼容增强路径:")
            for item in observed_surfaces:
                self.console.print(f"{indent}  - {item}")
        steps = usage.get("post_onboard_steps", [])
        if isinstance(steps, list) and steps:
            self.console.print(f"{indent}接入后步骤:")
            for step in steps:
                self.console.print(f"{indent}  - {step}")
        notes = usage.get("usage_notes", [])
        if isinstance(notes, list) and notes:
            self.console.print(f"{indent}使用提示:")
            for note in notes:
                self.console.print(f"{indent}  - {note}")
        smoke_prompt = usage.get("smoke_test_prompt", "")
        if isinstance(smoke_prompt, str) and smoke_prompt:
            self.console.print(f"{indent}Smoke 验收语句: {smoke_prompt}")
        smoke_steps = usage.get("smoke_test_steps", [])
        if isinstance(smoke_steps, list) and smoke_steps:
            self.console.print(f"{indent}Smoke 验收步骤:")
            for step in smoke_steps:
                self.console.print(f"{indent}  - {step}")
        smoke_signal = usage.get("smoke_success_signal", "")
        if isinstance(smoke_signal, str) and smoke_signal:
            self.console.print(f"{indent}Smoke 通过标准: {smoke_signal}")

    def _host_certification_rank(self, level: str) -> int:
        order = {"certified": 0, "compatible": 1, "experimental": 2}
        return order.get(level, 3)

    def _host_selection_sort_key(
        self, *, integration_manager, target: str
    ) -> tuple[int, int, int, str]:
        profile = integration_manager.get_adapter_profile(target)
        return (
            self._host_certification_rank(profile.certification_level),
            0 if integration_manager.supports_slash(target) else 1,
            0 if profile.category == "cli" else 1,
            target,
        )

    def _rank_host_targets(self, *, integration_manager, targets: list[str]) -> list[str]:
        return rank_host_targets(integration_manager=integration_manager, targets=targets)

    def _select_best_start_host(self, *, integration_manager, targets: list[str]) -> str:
        deduplicated = self._deduplicate_host_family(targets)
        return self._rank_host_targets(
            integration_manager=integration_manager,
            targets=deduplicated,
        )[0]

    def _recommended_start_hosts(self, *, integration_manager) -> list[dict[str, str]]:
        from .integrations import IntegrationManager

        items: list[dict[str, str]] = []
        for target in sorted(IntegrationManager.TARGETS):
            profile = integration_manager.get_adapter_profile(target)
            if profile.certification_level != "certified":
                continue
            items.append(
                {
                    "id": target,
                    "name": self._host_label(target),
                    "certification_label": profile.certification_label,
                    "path_override_env": str(host_path_override_guide(target).get("env_key", "")),
                }
            )
        return items

    def _build_no_host_decision_card(self, *, integration_manager) -> dict[str, Any]:
        recommended_hosts = self._recommended_start_hosts(integration_manager=integration_manager)
        action_examples = ["先装 Codex", "我先用 Claude Code", "先把宿主接好再开始"]
        next_actions = [
            "先安装一个受支持宿主，优先 Claude Code 或 Codex。",
            "如果宿主装在自定义目录，先设置对应的 SUPER_DEV_HOST_PATH_* 环境变量。",
            "安装后重新运行 super-dev，完成接入后直接回宿主里触发 /super-dev 或 super-dev:。",
        ]
        first_action = next_actions[0]
        return build_no_host_decision_card(
            workflow_mode_label=self._workflow_mode_label("start"),
            action_examples=action_examples,
            first_action=first_action,
            secondary_actions=next_actions[1:],
            path_override_hint=self._custom_host_path_override_hint(),
            path_override_examples=[
                {
                    "id": item["id"],
                    "name": item["name"],
                    "env_key": str(host_path_override_guide(item["id"]).get("env_key", "")),
                    "unix_example": str(
                        host_path_override_guide(item["id"]).get("unix_example", "")
                    ),
                    "windows_example": str(
                        host_path_override_guide(item["id"]).get("windows_example", "")
                    ),
                }
                for item in recommended_hosts[:2]
            ],
            recommended_hosts=recommended_hosts,
            lines=[
                f"先做这一步: {first_action}",
                "当前机器上未命中受支持宿主。",
                self._custom_host_path_override_hint(),
                "优先安装 Claude Code 或 Codex；接入完成后普通开发直接回宿主，不要停留在终端维护命令里。",
            ],
        )

    def _host_selection_reason(self, *, integration_manager, target: str) -> str:
        return host_selection_reason(integration_manager=integration_manager, target=target)

    def _build_detected_host_decision_card(
        self,
        *,
        project_dir: Path,
        integration_manager,
        detected_targets: list[str],
        detected_meta: dict[str, list[str]],
        preferred_targets: list[str] | None = None,
    ) -> dict[str, Any]:
        return build_detected_host_decision_card(
            project_dir=project_dir,
            integration_manager=integration_manager,
            detected_targets=detected_targets,
            detected_meta=detected_meta,
            preferred_targets=preferred_targets,
            usage_profile_fn=lambda target: self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            ),
            session_resume_card_fn=(
                lambda current_project_dir, target: self._build_session_resume_card(
                    project_dir=current_project_dir,
                    target=target,
                )
            ),
            explain_detection_details_fn=self._explain_detection_details,
            workflow_mode_label_fn=self._workflow_mode_label,
            candidate_trigger_fn=lambda target, usage, _profile: build_host_start_guidance(
                target=target,
                usage=usage,
                include_resume_hint=False,
            ),
            first_action_fn=(
                lambda target, usage, profile, session_resume_card: (
                    str(session_resume_card.get("workflow_context", {}).get("recommended_host_action", "")).strip()
                    if session_resume_card.get("enabled")
                    and isinstance(session_resume_card.get("workflow_context", {}), dict)
                    and str(
                        session_resume_card.get("workflow_context", {}).get("blocking_gate", "")
                    ).strip()
                    in {
                        "waiting_baseline_confirmation",
                        "missing_baseline",
                        "waiting_resume_gate",
                    }
                    and str(
                        session_resume_card.get("workflow_context", {}).get(
                            "recommended_host_action", ""
                        )
                    ).strip()
                    else (
                        f"重开后第一句直接复制 {session_resume_card.get('host_first_sentence')}"
                        if session_resume_card.get("enabled")
                        else build_host_start_guidance(
                            target=target,
                            usage=usage,
                            include_resume_hint=False,
                        )
                    )
                )
            ),
            first_suggestion_text_fn=lambda _selected_host, candidates: str(candidates[0]["trigger"]),
            default_action_examples=[
                "在宿主里开始这个项目",
                "在宿主里说“继续当前流程”",
                "在宿主里说“现在下一步是什么”",
            ],
            no_host_card_fn=lambda: self._build_no_host_decision_card(
                integration_manager=integration_manager
            ),
        )

    def _build_primary_repair_action(
        self,
        *,
        report: dict[str, Any],
        targets: list[str],
        decision_card: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        action = build_primary_repair_action(
            report=report,
            targets=targets,
            host_label_fn=self._host_label,
            usage_profile_fn=(
                lambda target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
            ),
            decision_card=decision_card,
        )
        if action.get("command"):
            return action
        runtime_health = report.get("runtime_install_health", {})
        if isinstance(runtime_health, dict) and not bool(runtime_health.get("healthy", True)):
            remediation = runtime_health.get("remediation", [])
            primary = ""
            secondary_actions: list[str] = []
            if isinstance(remediation, list):
                for item in remediation:
                    text = str(item).strip()
                    if not text:
                        continue
                    if not primary:
                        primary = text
                    elif text not in secondary_actions:
                        secondary_actions.append(text)
                    if len(secondary_actions) >= 2:
                        break
            if primary:
                warnings = runtime_health.get("warnings", [])
                reason = ""
                if isinstance(warnings, list):
                    reason = "；".join(str(item).strip() for item in warnings if str(item).strip())
                return {
                    "host": "当前运行时",
                    "reason": reason,
                    "command": primary,
                    "secondary_actions": secondary_actions,
                }
        return {"host": "", "reason": "", "command": "", "secondary_actions": []}

    def _build_host_trigger_example(self, *, target: str, idea: str | None) -> str:
        from .integrations import IntegrationManager

        if not idea:
            return ""
        if target == "codex":
            return f"/super-dev {idea}"
        if target == "codex-cli":
            return f"/super-dev {idea}"
        if target == "trae":
            return f"{IntegrationManager.TEXT_TRIGGER_PREFIX} {idea}"
        if IntegrationManager.supports_slash(target):
            return f"/super-dev {idea}"
        return f"{IntegrationManager.TEXT_TRIGGER_PREFIX} {idea}"

    def _build_onboard_next_steps(self, *, targets: list[str]) -> list[str]:
        from .integrations import IntegrationManager

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        lines: list[str] = []
        for target in targets:
            profile = integration_manager.get_adapter_profile(target)
            usage = self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
            session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
            continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
            continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
            if continue_mode and continue_prompt:
                line = f"{self._host_label(target)}: 重开后第一句直接复制 {continue_prompt}"
            else:
                standard_prompt = build_host_standard_first_prompt(target)
                competition_prompt = build_host_competition_first_prompt(target)
                self_check = build_host_post_onboard_self_check(target, usage)
                prompt_summary = f"标准流第一句：{standard_prompt}；比赛流第一句：{competition_prompt}"
                if self_check:
                    line = (
                        f"{self._host_label(target)}: 回宿主到 {usage.get('trigger_context', '-')}；"
                        f"{prompt_summary}；先做：{' / '.join(self_check[:2])}；"
                        "再按 smoke guide 验收"
                    )
                else:
                    line = (
                        f"{self._host_label(target)}: 回宿主到 {usage.get('trigger_context', '-')}；"
                        f"{prompt_summary}；再按 smoke guide 验收"
                    )
            if profile.requires_restart_after_onboard:
                line += "（先重启宿主）"
            lines.append(line)
        return lines

    def _build_session_resume_card_lines(self, *, project_dir: Path, target: str) -> list[str]:
        return self._build_session_resume_card(project_dir=project_dir, target=target).get("lines", [])

    def _build_session_resume_card(self, *, project_dir: Path, target: str) -> dict[str, Any]:
        session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
        continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
        continue_instruction = str(session_hint.get("continue_instruction", "") or "").strip()
        continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
        enabled = bool(continue_mode and continue_prompt)
        workflow_mode = str(session_hint.get("workflow_mode", "") or "").strip()
        workflow_context = (
            dict(session_hint.get("workflow_context", {}))
            if isinstance(session_hint.get("workflow_context", {}), dict)
            else (
                build_host_workflow_context(
                    project_dir,
                    entry_mode="continue" if continue_mode else "start",
                    target=target,
                )
                if enabled
                else {}
            )
        )
        return build_session_resume_card(
            project_dir=project_dir,
            target=target,
            enabled=enabled,
            host_first_sentence=continue_prompt,
            line_host_first_sentence=continue_prompt,
            continue_instruction=continue_instruction or continue_prompt,
            workflow_mode=workflow_mode,
            workflow_mode_label=self._workflow_mode_label(workflow_mode) if workflow_mode else "",
            action_title=str(session_hint.get("action_title", "") or "").strip(),
            action_examples=(
                session_hint.get("action_examples")
                if isinstance(session_hint.get("action_examples"), list)
                else []
            ),
            user_action_shortcuts=(
                session_hint.get("user_action_shortcuts")
                if isinstance(session_hint.get("user_action_shortcuts"), list)
                else []
            ),
            scenario_cards=(
                session_hint.get("scenario_cards")
                if isinstance(session_hint.get("scenario_cards"), list)
                else []
            ),
            specific_rules=(
                session_hint.get("continuity_rules")
                if isinstance(session_hint.get("continuity_rules"), list)
                else []
            ),
            recommended_workflow_command=str(
                session_hint.get("recommended_workflow_command", "") or ""
            ).strip(),
            supports_slash=self._supports_slash_for_prompt(target),
            flow_variant=detect_flow_variant(project_dir),
            workflow_context=workflow_context,
            include_entry_prompt_lines=True,
            prefer_payload_entry_prompt=True,
        )

    def _build_host_quick_start_text(
        self,
        *,
        host_profile: dict[str, Any],
        host_id: str,
        host_name: str,
        idea: str | None,
        session_hint: dict[str, Any] | None = None,
        framework_playbook: dict[str, Any] | None = None,
    ) -> str:
        trigger_text = self._build_host_trigger_example(target=host_id, idea=idea)
        if not trigger_text:
            trigger_text = str(
                host_profile.get("final_trigger", "") or host_profile.get("primary_entry", "-")
            )
        experience = (
            dict(host_profile.get("experience_profile", {}))
            if isinstance(host_profile.get("experience_profile", {}), dict)
            else {}
        )
        preferred_entries = [
            str(item).strip()
            for item in experience.get("preferred_entries", [])
            if str(item).strip()
        ]
        native_resume = [
            str(item).strip() for item in experience.get("native_resume", []) if str(item).strip()
        ]
        if host_id == "codex":
            trigger_text = "App/Desktop 从 `/` 列表选 super-dev；自然语言回退是 `super-dev: 你的需求`"
        elif host_id == "codex-cli":
            trigger_text = "App/Desktop 从 `/` 列表选 super-dev；CLI 输入 `$super-dev`；自然语言回退是 `super-dev: 你的需求`"
        elif host_id == "claude-code":
            trigger_text = "优先 `/super-dev 你的需求`；需要文本回退时用 `super-dev: 你的需求`"
        elif host_id == "kimi-code":
            trigger_text = "优先 `/skill:super-dev 你的需求`；也可 `/flow:super-dev 你的需求`；文本回退是 `super-dev: 你的需求`"
        elif host_id == "droid-cli":
            trigger_text = "优先 `/super-dev 你的需求`；headless 续跑用 `droid exec --session-id <id> \"continue with next steps\"`；文本回退是 `super-dev: 你的需求`"
        elif host_id == "trae-solo":
            trigger_text = "当前工作区优先 `/super-dev 你的需求`；文本回退是 `super-dev: 你的需求`"
        elif host_id == "trae-solocn":
            trigger_text = "当前工作区优先 `super-dev: 你的需求`；比赛模式用 `super-dev-seeai: 比赛需求`"
        session_hint = session_hint or {}
        continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
        continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
        workflow_reason = str(session_hint.get("workflow_reason", "") or "").strip()
        recommended_workflow_command = str(
            session_hint.get("recommended_workflow_command", "") or ""
        ).strip()
        standard_first_prompt = build_host_standard_first_prompt(host_id)
        competition_first_prompt = build_host_competition_first_prompt(host_id)
        framework_playbook = (
            dict(framework_playbook)
            if isinstance(framework_playbook, dict)
            else {}
        )
        framework_name = str(framework_playbook.get("framework", "")).strip()
        framework_validation = (
            list(framework_playbook.get("validation_surfaces", []))
            if isinstance(framework_playbook.get("validation_surfaces", []), list)
            else []
        )
        framework_evidence = (
            list(framework_playbook.get("delivery_evidence", []))
            if isinstance(framework_playbook.get("delivery_evidence", []), list)
            else []
        )

        if host_id in {
            "codex",
            "codex-cli",
            "opencode",
            "claude-code",
            "kimi-code",
            "droid-cli",
            "trae-solo",
            "trae-solocn",
        }:
            entry_variants = host_profile.get("entry_variants", [])
            variant_lines: list[str] = []
            if host_id in {"codex", "codex-cli"} and isinstance(entry_variants, list):
                for item in entry_variants:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label", "")).strip()
                    entry = str(item.get("entry", "")).strip()
                    notes = str(item.get("notes", "")).strip()
                    if not label or not entry:
                        continue
                    line = f"{label}: {entry}"
                    if notes:
                        line += f"；{notes}"
                    variant_lines.append(line)
            if preferred_entries:
                variant_lines.extend(f"推荐入口: {entry}" for entry in preferred_entries[:3])
            if continue_mode and native_resume:
                variant_lines.extend(f"恢复方式: {entry}" for entry in native_resume[:2])
            lines = [
                f"{host_name} 最短路径",
                "",
                "终端到此为止，真正开发回到宿主里。",
                (
                    "当前会话目标：继续仓库里已有的 Super Dev 流程"
                    if continue_mode
                    else "当前会话目标：启动一次新的 Super Dev 流程"
                ),
                "",
                "现在只做这四步",
                f"1. 进入这里：{host_profile.get('trigger_context', '-')}",
                (
                    f"2. 重开宿主后第一句直接复制：{continue_prompt}"
                    if continue_mode and continue_prompt
                    else f"2. 直接复制第一句：{trigger_text}"
                ),
                "3. 先看 smoke guide；如果 guide 里出现框架焦点、必验场景、交付证据，先按它执行",
                "4. 按 smoke guide 验收，确认宿主进入 research -> 三文档 -> 等待确认",
                "",
                f"标准流第一句：{standard_first_prompt}",
                f"比赛流第一句：{competition_first_prompt}",
                "已有项目先 baseline，并确认 baseline 后再继续；窗口关闭或第二天回来时默认先 resume。",
            ]
            if framework_name:
                lines.extend(
                    [
                        "",
                        f"当前项目框架焦点：{framework_name}",
                    ]
                )
                if framework_validation:
                    lines.append(
                        "必验场景：" + "；".join(str(item) for item in framework_validation[:4])
                    )
                if framework_evidence:
                    lines.append(
                        "交付证据：" + "；".join(str(item) for item in framework_evidence[:4])
                )
            lines.extend(
                [
                    "验收重点：先看框架焦点，再按 smoke guide 的必验场景走一遍。",
                    "只有宿主真的进入 research -> 三文档 -> 等待确认，才算接入成功。",
                ]
            )
            if variant_lines:
                lines.extend(["", "官方入口"])
                lines.extend(f"- {line}" for line in variant_lines)
            if continue_mode:
                lines.extend(
                    [
                        "流程状态卡：.super-dev/SESSION_BRIEF.md",
                        "继续规则：用户说“改一下 / 补充 / 继续改 / 确认 / 通过”时，仍然留在当前 Super Dev 流程。",
                        "退出条件：只有用户明确说取消当前流程、重新开始或切回普通聊天，才允许离开流程。",
                    ]
                )
            lines.extend(
                [
                    "",
                    "成功标志",
                    "1. 第一轮回复明确说当前阶段是 research",
                    "2. 会先读 knowledge/ 与 knowledge bundle，再做同类产品研究",
                    "3. 三份核心文档完成后会停下来等你确认",
                ]
            )
            if continue_mode and workflow_reason:
                lines.extend(["", f"当前流程说明：{workflow_reason}"])
            if continue_mode and recommended_workflow_command:
                lines.extend(["", f"机器侧对应动作：{recommended_workflow_command}"])
            priority_notes = self._build_host_priority_notes(host_id=host_id)
            if priority_notes:
                lines.extend(["", "最关键的提醒"])
                for index, note in enumerate(priority_notes, start=1):
                    lines.append(f"{index}. {note}")
            lines.extend(
                [
                    "",
                    "如果没进入正确流程，再回终端",
                    f"super-dev setup --host {host_id} --force --yes",
                    f"super-dev doctor --host {host_id} --repair --force",
                ]
            )
            return "\n".join(lines)

        lines = [
            f"{host_name} 最短路径",
            "",
            "终端到此为止，真正开发回到宿主里。",
            (
                "当前会话目标：继续已有流程"
                if continue_mode
                else "当前会话目标：启动新的 Super Dev 流程"
            ),
            "",
            "现在只做这四步",
            "1. 确认当前会话就在目标项目里。",
            f"2. {'先重启宿主，再' if host_profile.get('restart_required_label', '-') == '是' else ''}打开正确入口：{host_profile.get('trigger_context', '-')}",
            f"3. {'重开宿主后第一句直接复制' if continue_mode and continue_prompt else '直接复制第一句'}：{continue_prompt if continue_mode and continue_prompt else trigger_text}",
            "4. 先看 smoke guide；如果 guide 里出现框架焦点、必验场景、交付证据，先按它执行",
            "",
            f"标准流第一句：{standard_first_prompt}",
            f"比赛流第一句：{competition_first_prompt}",
            "已有项目先 baseline，并确认 baseline 后再继续；窗口关闭或第二天回来时默认先 resume。",
        ]
        next_index = 5
        if framework_name:
            lines.append(f"{next_index}. 当前项目框架焦点：{framework_name}")
            next_index += 1
            lines.append(
                (
                    f"{next_index}. 必验场景："
                    + "；".join(str(item) for item in framework_validation[:4])
                )
                if framework_validation
                else f"{next_index}. 必验场景：按宿主 smoke guide 和框架焦点执行。"
            )
            next_index += 1
            if framework_evidence:
                lines.append(
                    f"{next_index}. 交付证据："
                    + "；".join(str(item) for item in framework_evidence[:4])
                )
                next_index += 1
        lines.extend(
            [
                f"{next_index}. 验收重点：按 smoke guide 确认宿主进入 research -> 三文档 -> 等待确认。",
                f"{next_index + 1}. 只有这条主线成立，才开始真实需求。",
            ]
        )
        next_index += 2
        if continue_mode:
            lines.extend(
                [
                    f"{next_index}. 流程状态卡：.super-dev/SESSION_BRIEF.md",
                    f"{next_index + 1}. 用户说“改一下 / 补充 / 继续改 / 确认 / 通过”时，仍然留在当前 Super Dev 流程。",
                    f"{next_index + 2}. 只有用户明确说取消当前流程、重新开始或切回普通聊天，才允许离开流程。",
                ]
            )
        lines.extend(
            [
                "",
                "看到下面两点就算接入成功：",
                "1. 第一轮回复明确说当前阶段是 research",
                "2. 会先读 knowledge/ 与 knowledge bundle，再做同类产品研究",
                "3. 三份核心文档完成后会停下来等你确认",
                "",
                f"认证等级：{host_profile.get('certification_label', '-')}"
                f" ({host_profile.get('certification_level', '-')})",
                f"主入口：{host_profile.get('primary_entry', '-')}",
                f"使用模式：{host_profile.get('usage_mode', '-')}",
            ]
        )
        priority_notes = self._build_host_priority_notes(host_id=host_id)
        if priority_notes:
            lines.extend(["", "这个宿主最关键的提醒"])
            for index, note in enumerate(priority_notes, start=1):
                lines.append(f"{index}. {note}")
        reason = host_profile.get("certification_reason", "")
        if isinstance(reason, str) and reason.strip():
            lines.extend(["", "为什么推荐这个宿主", reason])
        if continue_mode and workflow_reason:
            lines.extend(["", "当前流程说明", workflow_reason])
        if continue_mode and recommended_workflow_command:
            lines.extend(["", f"机器侧对应动作：{recommended_workflow_command}"])
        steps = host_profile.get("post_onboard_steps", [])
        if isinstance(steps, list) and steps:
            lines.extend(["", "如果还是没生效，按这个顺序排查"])
            for index, step in enumerate(steps, start=1):
                lines.append(f"{index}. {step}")
        lines.extend(
            [
                "",
                "如果没进入正确流程，再回终端",
                f"super-dev setup --host {host_id} --force --yes",
                f"super-dev doctor --host {host_id} --repair --force",
            ]
        )
        return "\n".join(lines)

    def _build_host_priority_notes(self, *, host_id: str) -> list[str]:
        if host_id == "codex":
            return [
                "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；这是已启用 Skill 的官方入口。",
                "如果你已经在自然语言上下文里继续当前流程，也可以直接输入 `super-dev: 你的需求`。",
                "接入完成后建议彻底重开 Codex App/Desktop，会话才会重新加载 AGENTS.md 和 Skill。",
                "先确认当前会话已经绑定到目标项目，再开始新流程。",
            ]
        if host_id == "codex-cli":
            return [
                "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；这是已启用 Skill 的官方入口。",
                "Codex CLI 优先显式输入 `$super-dev`。",
                "如果你已经在自然语言上下文里继续当前流程，也可以直接输入 `super-dev: 你的需求`。",
                "接入完成后必须彻底重开 `codex`，旧会话不会重新加载 AGENTS.md 和 Skill。",
                "先确认当前终端就在目标项目目录里，再开始新会话。",
            ]
        if host_id == "claude-code":
            return [
                "Claude Code 优先直接用 `/super-dev`，不要先普通聊天开题。",
                "如果 slash 刷新异常，再回退到 `super-dev: 你的需求`。",
                "重开窗口后先说“继续当前流程”，不要重新描述项目背景。",
            ]
        if host_id == "kimi-code":
            return [
                "Kimi Code 优先走 `/skill:super-dev`，这样最稳定。",
                "如果你在 Flow 入口里组织多阶段工作，可以改用 `/flow:super-dev`。",
                "中断恢复优先 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，再回到当前流程。",
            ]
        if host_id == "droid-cli":
            return [
                "Droid CLI 优先在当前 session 用 `/super-dev` 开始，不要先普通对话探路。",
                "需要 headless 续跑时，优先 `droid exec --session-id <id> \"continue with next steps\"`。",
                "Factory rules / skills 更新后，先重开当前 session 再继续；`.factory/commands/` 只作为 legacy compatibility 排查。",
            ]
        if host_id == "trae-solo":
            return [
                "Trae SOLO 优先在当前 workspace 用 `/super-dev` 开题。",
                "确保当前 workspace 就是目标项目，别在错误目录里继续流程。",
                "slash 和文本回退都要汇入同一条 Super Dev 流程，不要分成两套会话。",
            ]
        if host_id == "trae-solocn":
            return [
                "Trae SOLOCN 当前默认以自然语言入口 `super-dev:` 最稳。",
                "如果你在用内建 `/plan` / `/spec`，要确保它们仍围绕同一条 Super Dev 流程服务。",
                "恢复时先回当前工作区，再说“继续当前流程”，不要重新开题。",
            ]
        if host_id == "opencode":
            return [
                "直接在 OpenCode 会话里输入 `/super-dev 你的需求`。",
                "通常不需要重启；如果命令列表没有刷新，关掉当前会话再重开一次。",
                "优先保留项目级 `.opencode/commands/super-dev.md`，不要只依赖全局命令目录。",
            ]
        return []

    def _build_host_usage_profile(
        self,
        *,
        integration_manager,
        target: str,
    ) -> dict[str, Any]:
        profile = integration_manager.get_adapter_profile(target)
        return serialize_host_usage_profile(
            profile=profile,
            target=target,
            final_trigger=self._display_final_trigger_for_profile(profile),
            managed_competition_project_surfaces=integration_manager.managed_competition_project_surfaces(
                target
            ),
            managed_competition_user_surfaces=integration_manager.managed_competition_user_surfaces(
                target
            ),
            host_value=self._host_label(profile.host),
            include_host_id=True,
            include_capability_labels=True,
            include_docs_fields=True,
            skill_slash_entry_host_id=profile.host,
            skill_slash_entry_note=(
                "表示 Codex App/Desktop `/` 列表里的已启用 Skill 入口，不代表项目支持自定义 slash 文件。"
            ),
            flow_host_id=profile.host,
        )

    def _load_host_runtime_validation_state(self, *, project_dir: Path) -> dict[str, Any]:
        return load_host_runtime_validation_state(project_dir=project_dir)

    def _host_runtime_status_label(self, status: str) -> str:
        return host_runtime_status_label(status)

    def _build_runtime_evidence_record(
        self,
        *,
        host_id: str,
        surface_ready: bool,
        runtime_entry: dict[str, Any],
    ) -> dict[str, Any]:
        return build_runtime_evidence_record(
            host_id=host_id,
            surface_ready=surface_ready,
            runtime_entry=runtime_entry,
        )

    def _update_host_runtime_validation_state(
        self,
        *,
        project_dir: Path,
        target: str,
        status: str,
        comment: str,
        actor: str,
        competition_evidence: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Path]:
        return update_host_runtime_validation_state(
            project_dir=project_dir,
            host=target,
            status=status,
            comment=comment,
            actor=actor,
            competition_evidence=competition_evidence,
        )

    def _resolve_report_project_name(self, project_dir: Path) -> str:
        try:
            config = ConfigManager(project_dir).load()
            raw = config.name or project_dir.name
        except Exception:
            raw = project_dir.name
        return self._sanitize_project_name(raw)

    def _render_host_compatibility_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_compatibility_markdown(payload, host_label_fn=self._host_label)

    def _render_host_surface_audit_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_surface_audit_markdown(payload, host_label_fn=self._host_label)

    def _build_host_runtime_validation_payload(
        self,
        *,
        project_dir: Path,
        targets: list[str],
        detected_meta: dict[str, list[str]],
        report: dict[str, Any],
        usage_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return build_host_runtime_validation_payload(
            project_dir=project_dir,
            targets=targets,
            detected_meta=detected_meta,
            report=report,
            usage_profiles=usage_profiles,
            explain_detection_details_fn=self._explain_detection_details,
            runtime_checklist_fn=(
                lambda target, usage, project_dir: self._host_runtime_checklist(
                    target=target,
                    usage=usage,
                    project_dir=project_dir,
                )
            ),
            pass_criteria_fn=(
                lambda target, usage, project_dir: self._host_runtime_pass_criteria(
                    target=target,
                    usage=usage,
                    project_dir=project_dir,
                )
            ),
            resume_probe_prompt_fn=(
                lambda target, usage, project_dir: self._host_resume_probe_prompt(
                    project_dir=project_dir,
                    target=target,
                )
            ),
            resume_checklist_fn=(
                lambda target, project_dir: self._host_resume_checklist(
                    target=target,
                    project_dir=project_dir,
                )
            ),
            entry_enricher_fn=(
                lambda target, host, usage, runtime_entry: {
                    "checks": (
                        host.get("checks", {})
                        if isinstance(host.get("checks", {}), dict)
                        else {}
                    ),
                }
            ),
        )

    def _render_host_runtime_validation_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_runtime_validation_markdown(payload, host_label_fn=self._host_label)

    def _write_host_report(
        self,
        *,
        writer,
        project_dir: Path,
        payload: dict[str, Any],
        renderers: dict[str, Any],
    ) -> dict[str, Path]:
        return writer(
            project_dir=project_dir,
            payload=payload,
            resolve_project_name_fn=self._resolve_report_project_name,
            **renderers,
        )

    def _write_host_surface_audit_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_surface_audit_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_surface_audit_fn": self._render_host_surface_audit_markdown,
            },
        )

    def _render_host_hardening_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_hardening_markdown(payload, host_label_fn=self._host_label)

    def _render_host_parity_onepage_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_parity_onepage_markdown(payload, host_label_fn=self._host_label)

    def _write_host_hardening_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_hardening_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_hardening_fn": self._render_host_hardening_markdown,
                "render_parity_onepage_fn": self._render_host_parity_onepage_markdown,
            },
        )

    def _write_host_runtime_validation_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_runtime_validation_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_runtime_validation_fn": self._render_host_runtime_validation_markdown,
            },
        )

    def _write_host_compatibility_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_compatibility_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_compatibility_fn": self._render_host_compatibility_markdown,
            },
        )
