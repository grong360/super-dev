"""
开发：Excellent（11964948@qq.com）
功能：Super Dev CLI 主入口
作用：提供命令行界面，统一访问所有功能
创建时间：2025-12-30
最后修改：2025-01-29
"""

import argparse
import importlib.util
import json
import os
import subprocess as _subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency seam for tests/runtime
    requests = None

from . import __description__, __version__
from .baseline_governance import inspect_baseline_governance
from .catalogs import (
    CICD_PLATFORM_IDS,
    DOMAIN_IDS,
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PIPELINE_FRONTEND_TEMPLATE_IDS,
    PLATFORM_IDS,
    PRIMARY_HOST_TOOL_IDS,
    PRODUCT_HOST_TOOL_IDS,
    SPECIAL_INSTALL_HOST_TOOL_IDS,
    host_display_name,
)
from .catalogs import (
    host_path_candidates as _host_path_candidates,
)
from .cli_analysis_mixin import CliAnalysisMixin
from .cli_deploy_runtime_mixin import CliDeployRuntimeMixin
from .cli_design_mixin import CliDesignMixin
from .cli_governance_mixin import CliGovernanceMixin
from .cli_host_ops_mixin import CliHostOpsMixin
from .cli_parser_mixin import CliParserMixin
from .cli_release_quality_mixin import CliReleaseQualityMixin
from .cli_spec_mixin import CliSpecMixin
from .config import ConfigManager, ProjectConfig, get_config_manager
from .error_handler import handle_cli_error
from .evidence_identity import attach_evidence_identity
from .harness_registry import derive_operational_focus, summarize_operational_harnesses
from .hooks.manager import HookManager
from .host_runtime_probe import build_host_runtime_probe
from .host_workflow_context import build_host_workflow_context
from .review_state import (
    architecture_revision_file,
    baseline_confirmation_file,
    describe_workflow_event,
    docs_confirmation_file,
    latest_workflow_snapshot_file,
    load_architecture_revision,
    load_baseline_confirmation,
    load_docs_confirmation,
    load_preview_confirmation,
    load_quality_revision,
    load_recent_operational_timeline,
    load_recent_workflow_events,
    load_recent_workflow_snapshots,
    load_ui_revision,
    load_workflow_state,
    preview_confirmation_file,
    quality_revision_file,
    save_architecture_revision,
    save_baseline_confirmation,
    save_docs_confirmation,
    save_preview_confirmation,
    save_quality_revision,
    save_ui_revision,
    save_workflow_state,
    ui_revision_file,
    workflow_event_log_file,
    workflow_state_file,
)
from .terminal import (
    create_console,
)
from .utils import get_logger
from .workflow_guard import (
    docs_gate_status,
    preview_gate_status,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)
from .workflow_state import (
    build_host_entry_prompts,
    detect_pipeline_summary,
    load_framework_playbook_summary,
    workflow_continuity_rules,
    workflow_mode_label,
    workflow_mode_shortcuts,
)

RICH_AVAILABLE = importlib.util.find_spec("rich") is not None
host_path_candidates = _host_path_candidates
subprocess = _subprocess

CICDPlatform = Literal["github", "gitlab", "jenkins", "azure", "bitbucket", "all"]

SUPPORTED_PLATFORMS = list(PLATFORM_IDS)
SUPPORTED_PIPELINE_FRONTENDS = list(PIPELINE_FRONTEND_TEMPLATE_IDS)
SUPPORTED_INIT_FRONTENDS = list(FULL_FRONTEND_TEMPLATE_IDS)
SUPPORTED_PIPELINE_BACKENDS = list(PIPELINE_BACKEND_IDS)
SUPPORTED_DOMAINS = list(DOMAIN_IDS)
SUPPORTED_CICD = list(CICD_PLATFORM_IDS)
SUPPORTED_HOST_TOOLS = list(HOST_TOOL_IDS)
PRIMARY_SUPPORTED_HOST_TOOLS = list(PRIMARY_HOST_TOOL_IDS)
PRODUCT_SUPPORTED_HOST_TOOLS = list(PRODUCT_HOST_TOOL_IDS)
SPECIAL_INSTALL_HOST_TOOLS = list(SPECIAL_INSTALL_HOST_TOOL_IDS)


class SuperDevCLI(
    CliParserMixin,
    CliAnalysisMixin,
    CliDesignMixin,
    CliReleaseQualityMixin,
    CliDeployRuntimeMixin,
    CliHostOpsMixin,
    CliSpecMixin,
    CliGovernanceMixin,
):
    """Super Dev 命令行接口"""

    @staticmethod
    def _display_final_trigger(profile) -> str:
        if getattr(profile, "host", "") == "codex":
            return "App/Desktop: /super-dev | 回退: super-dev: 你的需求"
        if getattr(profile, "host", "") == "codex-cli":
            return "CLI: $super-dev | 回退: super-dev: 你的需求"
        return str(profile.trigger_command).replace("<需求描述>", "你的需求")

    def __init__(self):
        self.console = create_console()
        self.parser = self._create_parser()
        self.logger = get_logger("cli", level="WARNING")  # CLI只记录WARNING及以上级别

    def _public_host_targets(self, *, integration_manager) -> list[str]:
        available_targets = [item.name for item in integration_manager.list_targets()]
        public_targets = [
            target for target in PRIMARY_SUPPORTED_HOST_TOOLS if target in available_targets
        ]
        return public_targets or available_targets

    def _print_public_help(self) -> None:
        self._print_banner()
        lines = [
            "Super Dev Public Help",
            "",
            "公开终端入口:",
            "  super-dev           打开宿主安装 / 接入引导",
            "  super-dev update    更新到最新版本",
            "  super-dev uninstall 完整清理宿主接入面",
            "",
            "宿主内使用:",
            "  slash 宿主: /super-dev 你的需求",
            "  文本宿主: super-dev: 你的需求",
            "  流程继续: 在宿主里说“继续当前流程”",
            "  查询下一步: 在宿主里说“现在下一步是什么”",
            "  高级维护: /super-dev-work / /super-dev-run / /super-dev-review",
            "",
            "说明:",
            "  默认帮助只展示公开产品入口。",
            "  内部维护 / 治理命令请使用: super-dev --help-all",
        ]
        for line in lines:
            self.console.print(line)

    def run(self, args: list | None = None) -> int:
        """
        运行 CLI

        Args:
            args: 命令行参数

        Returns:
            退出码
        """
        argv = list(args) if args is not None else sys.argv[1:]

        # P1-8: 启动版本检查（非阻塞，缓存 24h，仅在有子命令时检查）
        if argv and not argv[0].startswith("-"):
            try:
                from .version_check import check_for_update

                hint = check_for_update()
                if hint:
                    self.console.print(f"[dim]{hint}[/dim]")
            except Exception:
                pass

        # 兼容 `super-dev help` / `super-dev version` 这类用户习惯输入
        if len(argv) == 1 and argv[0] == "help":
            self._print_public_help()
            return 0
        if len(argv) == 1 and argv[0] in {"--help", "-h"}:
            self._print_public_help()
            return 0
        if len(argv) == 1 and argv[0] in {"--help-all", "help-all"}:
            self._print_banner()
            self.console.print("Super Dev Internal Command Index")
            self.console.print(
                "以下命令属于内部维护 / 治理 / 高级用法，不属于普通用户公开终端入口。"
            )
            self.console.print(
                "普通用户公开终端入口仍然只有 super-dev / super-dev update / super-dev uninstall。"
            )
            self.console.print("")
            help_text = self.parser.format_help()
            filtered_help = "\n".join(
                line for line in help_text.splitlines() if "==SUPPRESS==" not in line
            )
            self.console.print(filtered_help.rstrip())
            return 0
        if len(argv) == 1 and argv[0] == "version":
            self.console.print(f"super-dev {__version__}")
            return 0

        # 未知单词命令 → 显示错误和建议
        if self._is_unknown_command(argv):
            unknown = argv[0]
            suggestions = self._suggest_commands(unknown)
            self.console.print(f"[red]未知命令: '{unknown}'[/red]")
            self.console.print(f"你是否想输入: {', '.join(suggestions)}?")
            self.console.print(
                "运行 'super-dev --help' 查看公开入口，运行 'super-dev --help-all' 查看内部维护命令。"
            )
            return 2

        # 直达入口：`super-dev <需求描述>`
        if self._is_direct_requirement_input(argv):
            try:
                description, direct_overrides = self._parse_direct_requirement_args(argv)
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 2
            return self._run_direct_requirement(description, direct_overrides)

        parsed_args = self.parser.parse_args(argv)

        # 根据 -v/--verbose / --quiet 调整日志级别
        if getattr(parsed_args, "quiet", False):
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="ERROR")
        elif getattr(parsed_args, "verbose", 0) >= 2:
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="DEBUG")
        elif getattr(parsed_args, "verbose", 0) >= 1:
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="INFO")

        if parsed_args.command is None:
            install_args = argparse.Namespace(
                host=None,
                all=False,
                auto=False,
                skill_name="super-dev",
                no_skill=False,
                skip_integrate=False,
                skip_slash=False,
                skip_doctor=False,
                force=False,
                yes=False,
            )
            return self._cmd_install(install_args)

        # 路由到对应命令
        command_name = str(parsed_args.command).replace("-", "_")
        command_handler = getattr(self, f"_cmd_{command_name}", None)
        if command_handler is None or not callable(command_handler):
            self.console.print(f"[red]未知命令: {parsed_args.command}[/red]")
            return 1

        try:
            handler = cast(Callable[[Any], int], command_handler)
            return int(handler(parsed_args))

        except Exception as e:
            # 统一错误处理 — 不向终端用户暴露 traceback
            cmd_name = str(getattr(parsed_args, "command", ""))

            # 调试模式下仍然打印 traceback
            if "--debug" in sys.argv or "-d" in sys.argv:
                self.console.print(traceback.format_exc())

            return handle_cli_error(e, command=cmd_name)

    # ==================== 命令处理器 ====================

    def _cmd_review(self, args) -> int:
        """查看或更新评审状态"""
        review_specs = {
            "baseline": {
                "title": "当前项目基线确认状态",
                "load": load_baseline_confirmation,
                "save": save_baseline_confirmation,
                "file": baseline_confirmation_file,
                "type": "baseline",
            },
            "docs": {
                "title": "三文档确认状态",
                "load": load_docs_confirmation,
                "save": save_docs_confirmation,
                "file": docs_confirmation_file,
                "type": "docs",
            },
            "ui": {
                "title": "UI 改版状态",
                "load": load_ui_revision,
                "save": save_ui_revision,
                "file": ui_revision_file,
                "type": "ui",
            },
            "preview": {
                "title": "前端预览确认状态",
                "load": load_preview_confirmation,
                "save": save_preview_confirmation,
                "file": preview_confirmation_file,
                "type": "preview",
            },
            "architecture": {
                "title": "架构返工状态",
                "load": load_architecture_revision,
                "save": save_architecture_revision,
                "file": architecture_revision_file,
                "type": "architecture",
            },
            "quality": {
                "title": "质量返工状态",
                "load": load_quality_revision,
                "save": save_quality_revision,
                "file": quality_revision_file,
                "type": "quality",
            },
        }
        if args.review_command not in review_specs:
            self.console.print(
                "[yellow]请指定 review 子命令，例如 `super-dev review baseline`、`super-dev review docs`、`super-dev review preview`、`super-dev review ui`、`super-dev review architecture` 或 `super-dev review quality`[/yellow]"
            )
            return 1

        project_dir = Path.cwd()
        spec = review_specs[args.review_command]
        review_type = str(spec["type"])
        current = cast(Callable[[Path], dict[str, Any] | None], spec["load"])(project_dir) or {}
        state_file = cast(Callable[[Path], Path], spec["file"])(project_dir)
        title = str(spec["title"])

        if review_type == "baseline" and getattr(args, "prepare", False):
            if args.status:
                self.console.print(
                    "[red]`super-dev review baseline --prepare` 不能与 `--status` 同时使用。[/red]"
                )
                return 1
            from .analyzer import BaselineAuditBuilder

            builder = BaselineAuditBuilder(project_dir)
            report = builder.build()
            files = builder.write(report)
            payload = {
                "status": "prepared",
                "project_name": report.project_name,
                "work_mode": report.work_mode,
                "work_mode_label": report.work_mode_label,
                "summary": report.summary,
                "file_path": str(files["markdown"]),
                "json_file_path": str(files["json"]),
                "next_host_action": "回到宿主里说“baseline 确认，可以继续当前流程”",
            }
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            else:
                self.console.print("[cyan]Baseline audit 草稿已生成[/cyan]")
                self.console.print(f"  模式: {report.work_mode} ({report.work_mode_label})")
                self.console.print(f"  摘要: {report.summary}")
                self.console.print(f"  Markdown: {files['markdown']}")
                self.console.print(f"  JSON: {files['json']}")
                self.console.print("  下一步: 回到宿主里说“baseline 确认，可以继续当前流程”")
            return 0

        if not args.status:
            payload = {
                "status": str(current.get("status", "")).strip() or "pending_review",
                "comment": str(current.get("comment", "")).strip(),
                "actor": str(current.get("actor", "")).strip(),
                "run_id": str(current.get("run_id", "")).strip(),
                "updated_at": str(current.get("updated_at", "")).strip(),
                "exists": bool(current),
                "file_path": str(state_file),
            }
            if review_type == "baseline":
                baseline_governance = inspect_baseline_governance(project_dir)
                payload["baseline_governance"] = baseline_governance
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            else:
                self.console.print(f"[cyan]{title}[/cyan]")
                self.console.print(
                    f"  状态: {self._review_status_label(payload['status'], review_type=review_type)}"
                )
                self.console.print(f"  备注: {payload['comment'] or '-'}")
                self.console.print(f"  操作者: {payload['actor'] or '-'}")
                self.console.print(f"  关联 Run: {payload['run_id'] or '-'}")
                self.console.print(f"  更新时间: {payload['updated_at'] or '-'}")
                self.console.print(f"  文件: {payload['file_path']}")
                if review_type == "baseline":
                    baseline_governance = cast(dict[str, Any], payload["baseline_governance"])
                    self.console.print(
                        f"  Baseline Audit: {baseline_governance.get('audit_path') or '-'}"
                    )
                    self.console.print(
                        f"  Entry Gate: {baseline_governance.get('entry_gate', '-')}"
                    )
                    self.console.print(
                        f"  下一步: {baseline_governance.get('next_host_action', '-')}"
                    )
            return 0

        save_fn = cast(Callable[[Path, dict[str, Any]], Path], spec["save"])
        load_fn = cast(Callable[[Path], dict[str, Any] | None], spec["load"])
        review_payload = {
            "status": args.status,
            "comment": args.comment.strip(),
            "actor": args.actor.strip() or "user",
            "run_id": args.run_id.strip(),
        }
        if review_type == "docs" and args.status == "confirmed":
            file_path, _ = save_bound_docs_confirmation(project_dir, review_payload)
        elif review_type == "preview" and args.status == "confirmed":
            file_path, _ = save_bound_preview_confirmation(project_dir, review_payload)
        else:
            file_path = save_fn(project_dir, review_payload)
        payload = load_fn(project_dir) or {}
        self._write_session_brief(
            project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
        )
        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        else:
            if review_type == "ui":
                action = (
                    "已确认 UI 改版通过"
                    if args.status == "confirmed"
                    else (
                        "已记录 UI 改版请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "preview":
                action = (
                    "已确认前端预览通过"
                    if args.status == "confirmed"
                    else (
                        "已记录预览返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "architecture":
                action = (
                    "已确认架构返工通过"
                    if args.status == "confirmed"
                    else (
                        "已记录架构返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "quality":
                action = (
                    "已确认质量返工通过"
                    if args.status == "confirmed"
                    else (
                        "已记录质量返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            else:
                action = (
                    "已确认三文档"
                    if args.status == "confirmed"
                    else (
                        "已记录文档修改要求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            self.console.print(f"[green]✓[/green] {action}")
            self.console.print(
                f"  状态: {self._review_status_label(args.status, review_type=review_type)}"
            )
            self.console.print(f"  备注: {payload.get('comment', '') or '-'}")
            self.console.print(f"  操作者: {payload.get('actor', '') or '-'}")
            self.console.print(f"  关联 Run: {payload.get('run_id', '') or '-'}")
            self.console.print(f"  文件: {file_path}")
            if review_type == "ui" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先更新 output/*-uiux.md，再重做前端，并重新执行 frontend runtime 与 UI review[/dim]"
                )
            elif review_type == "preview" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 继续修改前端预览，重新生成 frontend runtime 与预览页，再次提交预览确认[/dim]"
                )
            elif review_type == "architecture" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先更新 output/*-architecture.md，再调整技术方案与实现，并重新通过相关质量门禁[/dim]"
                )
            elif review_type == "quality" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先修复质量/安全问题，重新执行 quality gate，并刷新交付证据后再继续后续动作[/dim]"
                )
        return 0

        return 0

    # 阶段编号映射表
    STAGE_NUMBER_MAP: dict[str, str] = {
        "1": "research",
        "2": "prd",
        "3": "architecture",
        "4": "uiux",
        "5": "spec",
        "6": "frontend",
        "7": "backend",
        "8": "quality",
        "9": "delivery",
    }

    STAGE_LABELS: dict[str, str] = {
        "research": "同类产品研究",
        "prd": "产品需求文档",
        "architecture": "架构设计",
        "uiux": "UI/UX 设计",
        "spec": "规范与任务分解",
        "frontend": "前端开发",
        "backend": "后端开发",
        "quality": "质量检查",
        "delivery": "交付打包",
    }

    # 每个环节对应的专家角色和职责
    STAGE_EXPERTS: dict[str, dict[str, str]] = {
        "research": {
            "role": "PM + ARCHITECT",
            "title": "产品经理 + 架构师",
            "duty": "需求解析、知识库增强、同类产品研究",
        },
        "prd": {
            "role": "PM",
            "title": "产品经理",
            "duty": "需求分析、PRD 编写、用户故事、验收标准",
        },
        "architecture": {
            "role": "ARCHITECT",
            "title": "架构师",
            "duty": "系统设计、技术选型、API 设计、数据库建模",
        },
        "uiux": {
            "role": "UI + UX",
            "title": "UI/UX 设计师",
            "duty": "视觉设计、设计系统、组件规范、交互设计",
        },
        "spec": {
            "role": "PM + CODE",
            "title": "产品经理 + 代码专家",
            "duty": "需求拆解、任务分解、优先级排序",
        },
        "frontend": {
            "role": "CODE + UI",
            "title": "代码专家 + UI 设计师",
            "duty": "前端实现、组件开发、页面搭建",
        },
        "backend": {
            "role": "CODE + DBA",
            "title": "代码专家 + 数据库专家",
            "duty": "后端实现、API 开发、数据库迁移",
        },
        "quality": {
            "role": "QA + SECURITY",
            "title": "QA 专家 + 安全专家",
            "duty": "质量门禁、红队审查、测试验证",
        },
        "delivery": {
            "role": "DEVOPS + QA",
            "title": "DevOps + QA 专家",
            "duty": "CI/CD 配置、发布演练、交付打包",
        },
    }

    def _cmd_run(self, args) -> int:
        """跳转到任意环节执行/重做（支持名称或数字 1-9）"""
        if getattr(args, "status", False):
            return self._cmd_run_status(args)

        if getattr(args, "resume", False):
            return self._cmd_run_resume(args)

        confirm_phase = str(getattr(args, "confirm_phase", "") or "").strip()
        if confirm_phase:
            return self._cmd_run_confirm_phase(
                phase_name=confirm_phase,
                comment=str(getattr(args, "comment", "") or ""),
                actor=str(getattr(args, "actor", "") or "cli-user"),
            )
        jump_stage = str(getattr(args, "jump", "") or "").strip()
        if jump_stage:
            return self._cmd_run_from_stage(stage_selector=jump_stage, show_impact=True)
        phase_stage = str(getattr(args, "phase", "") or "").strip()
        if phase_stage:
            return self._cmd_run_from_stage(stage_selector=phase_stage, show_impact=False)

        stage_selector = str(getattr(args, "stage_selector", "") or "").strip()

        # 数字映射：super-dev run 1 → research, super-dev run 4 → uiux
        if stage_selector in self.STAGE_NUMBER_MAP:
            stage_selector = self.STAGE_NUMBER_MAP[stage_selector]

        if stage_selector:
            normalized = stage_selector.lower()
            label = self.STAGE_LABELS.get(normalized, normalized)

            # 专家角色映射
            expert_map = {
                "research": ("PM + ARCHITECT", "产品经理 + 架构师"),
                "prd": ("PM", "产品经理"),
                "architecture": ("ARCHITECT", "架构师"),
                "uiux": ("UI + UX", "UI/UX 设计师"),
                "spec": ("PM + CODE", "产品经理 + 代码专家"),
                "frontend": ("CODE + UI", "代码专家 + UI 设计师"),
                "backend": ("CODE + DBA", "代码专家 + 数据库专家"),
                "quality": ("QA + SECURITY", "QA 专家 + 安全专家"),
                "delivery": ("DEVOPS + QA", "DevOps + QA 专家"),
            }
            expert_role, expert_title = expert_map.get(normalized, ("CODE", "代码专家"))

            self.console.print("")
            if RICH_AVAILABLE:
                from rich.panel import Panel

                self.console.print(
                    Panel(
                        f"[bold cyan]Super Dev Run[/bold cyan]\n\n"
                        f"  [dim]环节[/dim]    {normalized} ({label})\n"
                        f"  [dim]专家[/dim]    [bold]{expert_role}[/bold] - {expert_title}",
                        border_style="cyan",
                        expand=True,
                        padding=(1, 2),
                    )
                )
            else:
                self.console.print(
                    f"Super Dev Run: {normalized} ({label}) | {expert_role} - {expert_title}"
                )
            self.console.print("")

            if normalized in {"research", "prd", "architecture", "uiux"}:
                return self._cmd_run_targeted_refresh(normalized)
            return self._cmd_run_from_stage(stage_selector=normalized, show_impact=False)

        # 没有指定阶段，显示环节菜单
        from rich.panel import Panel
        from rich.table import Table

        self.console.print("")
        table = Table(title="可用环节", expand=True, border_style="dim", title_style="bold cyan")
        table.add_column("编号", style="bold cyan", min_width=4, max_width=6, justify="center")
        table.add_column("专家", style="bold", min_width=12, ratio=1)
        table.add_column("环节", style="bold", ratio=1)
        table.add_column("说明", style="dim", ratio=3, overflow="fold")

        expert_short = {
            "research": "PM + ARCHITECT",
            "prd": "PM",
            "architecture": "ARCHITECT",
            "uiux": "UI + UX",
            "spec": "PM + CODE",
            "frontend": "CODE + UI",
            "backend": "CODE + DBA",
            "quality": "QA + SECURITY",
            "delivery": "DEVOPS + QA",
        }
        for num, name in sorted(self.STAGE_NUMBER_MAP.items()):
            table.add_row(num, expert_short.get(name, ""), name, self.STAGE_LABELS.get(name, ""))
        self.console.print(table)
        self.console.print("")
        self.console.print("[cyan]用法示例:[/cyan]")
        self.console.print("  super-dev run 4          UI/UX 设计师重新生成设计文档")
        self.console.print("  super-dev run uiux       同上")
        self.console.print("  super-dev run --resume   从上次中断处继续")
        self.console.print("  super-dev run --status   查看流程状态")
        self.console.print("")
        return 0

    def _cmd_status(self, args) -> int:
        """快捷别名：查看当前流程状态"""
        return self._cmd_run_status(args)

    def _cmd_next(self, args) -> int:
        """统一的下一步路由入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Next")
        return 0

    def _cmd_continue(self, args) -> int:
        """更自然的继续入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            payload["entrypoint"] = "continue"
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Continue")
        return 0

    def _cmd_resume(self, args) -> int:
        """更符合真实恢复场景的继续入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            payload["entrypoint"] = "resume"
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Resume")
        return 0

    def _render_next_step_payload(self, payload: dict[str, Any], *, title: str) -> None:
        action_card = (
            payload.get("action_card") if isinstance(payload.get("action_card"), dict) else {}
        )
        self.console.print(f"[cyan]{title}[/cyan]")
        workflow_mode = str(payload.get("workflow_mode", "")).strip()
        if workflow_mode:
            self.console.print(f"  动作类型: {self._workflow_mode_label(workflow_mode)}")
        self.console.print(
            f"  当前步骤: {payload.get('current_step_label', payload.get('status', '-'))}"
        )
        self.console.print(
            f"  用户下一步: {payload.get('user_next_action', payload.get('recommended_command', '-'))}"
        )
        user_action_shortcuts = (
            payload.get("user_action_shortcuts")
            if isinstance(payload.get("user_action_shortcuts"), list)
            else []
        )
        if user_action_shortcuts:
            self.console.print(
                f"  你现在可以直接说: {' / '.join(str(item) for item in user_action_shortcuts[:4])}"
            )
        preferred_host_name = str(payload.get("preferred_host_name", "")).strip()
        host_continue_prompt = str(payload.get("host_continue_prompt", "")).strip()
        if preferred_host_name and host_continue_prompt:
            self.console.print(f"  宿主第一句 ({preferred_host_name}): {host_continue_prompt}")
        host_entry_prompts = (
            payload.get("host_continue_entry_prompts")
            if isinstance(payload.get("host_continue_entry_prompts"), dict)
            else {}
        )
        host_entry_labels = (
            payload.get("host_continue_entry_labels")
            if isinstance(payload.get("host_continue_entry_labels"), dict)
            else {}
        )
        if host_entry_prompts:
            preferred_entry_label = str(
                payload.get("host_continue_preferred_entry_label", "")
            ).strip()
            if preferred_entry_label:
                self.console.print(f"  推荐入口: {preferred_entry_label}")
            for key, prompt in host_entry_prompts.items():
                prompt_text = str(prompt).strip()
                if not prompt_text:
                    continue
                label = str(host_entry_labels.get(key, key)).strip() or key
                suffix = "恢复入口" if key != "fallback" else "回退恢复入口"
                self.console.print(f"  {label} {suffix}: {prompt_text}")
        self.console.print(f"  系统建议动作: {payload.get('recommended_command', '-')}")
        examples = (
            action_card.get("examples") if isinstance(action_card.get("examples"), list) else []
        )
        if examples:
            self.console.print(f"  自然语言示例: {', '.join(str(item) for item in examples[:3])}")
        scenario_cards = (
            payload.get("scenario_cards") if isinstance(payload.get("scenario_cards"), list) else []
        )
        for item in scenario_cards[:4]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            command = str(item.get("cli_command", "")).strip()
            if title and command:
                self.console.print(f"  真实场景: {title} -> {command}")
        self.console.print(f"  当前状态: {payload.get('status', '-')}")
        self.console.print(f"  原因: {payload.get('reason', '-')}")
        if payload.get("session_brief_path"):
            self.console.print(f"  流程状态卡: {payload.get('session_brief_path')}")
        recent_snapshots = (
            payload.get("recent_snapshots")
            if isinstance(payload.get("recent_snapshots"), list)
            else []
        )
        if recent_snapshots and isinstance(recent_snapshots[0], dict):
            first = recent_snapshots[0]
            step = (
                str(first.get("current_step_label", "")).strip()
                or str(first.get("status", "")).strip()
            )
            updated_at = str(first.get("updated_at", "")).strip() or "-"
            self.console.print(f"  最近快照: {updated_at} · {step}")
        if payload.get("evidence"):
            self.console.print(f"  依据: {payload['evidence']}")

    def _workflow_mode_label(self, workflow_mode: str) -> str:
        return workflow_mode_label(workflow_mode)

    def _workflow_mode_shortcuts(
        self, workflow_mode: str, *, action_card: dict[str, Any] | None = None
    ) -> list[str]:
        if isinstance(action_card, dict):
            raw_shortcuts = action_card.get("shortcuts")
            if isinstance(raw_shortcuts, list):
                shortcuts = [str(item).strip() for item in raw_shortcuts if str(item).strip()]
                if shortcuts:
                    return shortcuts
            raw_examples = action_card.get("examples")
            examples = (
                [str(item).strip() for item in raw_examples if str(item).strip()]
                if isinstance(raw_examples, list)
                else []
            )
        else:
            examples = []
        return workflow_mode_shortcuts(workflow_mode, examples=examples)

    def _cmd_jump(self, args) -> int:
        """快捷别名：跳转到指定阶段"""
        stage = str(getattr(args, "stage", "") or "").strip()
        if not stage:
            self.console.print("[red]请指定目标阶段，例如: super-dev jump frontend[/red]")
            return 1
        return self._cmd_run_from_stage(stage_selector=stage, show_impact=True)

    def _cmd_confirm(self, args) -> int:
        """快捷别名：确认指定阶段"""
        phase_name = str(getattr(args, "phase", "") or "").strip()
        if not phase_name:
            self.console.print("[red]请指定要确认的阶段，例如: super-dev confirm docs[/red]")
            return 1
        return self._cmd_run_confirm_phase(
            phase_name=phase_name,
            comment=str(getattr(args, "comment", "") or ""),
            actor=str(getattr(args, "actor", "") or "cli-user"),
        )

    def _cmd_run_resume(self, args) -> int:
        """恢复最近一次 pipeline 运行"""

        project_dir = Path.cwd()
        run_state = self._read_pipeline_run_state(project_dir)
        if not run_state:
            self.console.print("[red]未找到最近一次 pipeline 运行记录[/red]")
            self.console.print(
                "[dim]请先运行 `super-dev` 完成宿主接入，再在宿主里用 `/super-dev` 或 `super-dev:` 启动流程[/dim]"
            )
            return 1

        status = str(run_state.get("status", "")).strip().lower()
        if status == "success":
            self.console.print("[yellow]最近一次 pipeline 已成功完成，无需恢复[/yellow]")
            return 1
        if status == "waiting_confirmation":
            if not self._docs_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在文档确认门，请先确认三文档后再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“文档确认，可以继续”[/dim]")
                return 1
            if any(
                (project_dir / "output").glob("*-frontend-runtime.json")
            ) and not self._preview_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 还缺前端预览确认，请先确认预览后再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
                return 1
            if not self._ui_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理 UI 改版请求，请先完成 UI 返工再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
                return 1
            if not self._architecture_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理架构返工请求，请先完成架构修订再恢复[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]"
                )
                return 1
            if not self._quality_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理质量返工请求，请先完成质量整改再恢复[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status == "waiting_preview_confirmation":
            if not self._preview_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在前端预览确认门，请先确认预览或继续完成前端返工[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
                return 1
        elif status == "waiting_ui_revision":
            if not self._ui_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在 UI 改版门，请先完成 UIUX 更新、前端返工与 UI review[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
                return 1
        elif status == "waiting_architecture_revision":
            if not self._architecture_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在架构返工门，请先完成 output/*-architecture.md 修订和实现同步[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status == "waiting_quality_revision":
            if not self._quality_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在质量返工门，请先完成质量整改并重新执行 quality gate[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status not in {"failed", "running"}:
            self.console.print("[yellow]最近一次 pipeline 状态不支持恢复[/yellow]")
            return 1

        raw_args = run_state.get("pipeline_args", {})
        if not isinstance(raw_args, dict):
            self.console.print("[red]运行记录损坏：缺少 pipeline 参数[/red]")
            return 1

        pipeline_args = argparse.Namespace(
            description=str(raw_args.get("description", "")).strip(),
            platform=str(raw_args.get("platform", "web")),
            frontend=str(raw_args.get("frontend", "react")),
            backend=str(raw_args.get("backend", "node")),
            domain=str(raw_args.get("domain", "")),
            name=raw_args.get("name"),
            cicd=str(raw_args.get("cicd", "all")),
            skip_redteam=bool(raw_args.get("skip_redteam", False)),
            skip_scaffold=bool(raw_args.get("skip_scaffold", False)),
            skip_quality_gate=bool(raw_args.get("skip_quality_gate", False)),
            skip_rehearsal_verify=bool(raw_args.get("skip_rehearsal_verify", False)),
            offline=bool(raw_args.get("offline", False)),
            quality_threshold=raw_args.get("quality_threshold"),
            resume=True,
        )

        if not pipeline_args.description:
            self.console.print("[red]运行记录缺少 description，无法恢复[/red]")
            return 1

        if status == "running":
            self.console.print("[yellow]检测到最近一次运行状态为 running，按中断恢复处理[/yellow]")
        self.console.print("[cyan]恢复最近一次失败/中断的 pipeline 运行...[/cyan]")
        self.console.print(f"[dim]需求: {pipeline_args.description}[/dim]")
        return self._cmd_pipeline(pipeline_args)

    def _cmd_run_status(self, args) -> int:
        project_dir = Path.cwd()
        run_state = self._read_pipeline_run_state(project_dir) or {}
        if not run_state and not self._project_has_super_dev_context(project_dir):
            if getattr(args, "json", False):
                payload = {
                    "status": "not_initialized",
                    "recommended_next": "super-dev init <项目名>",
                }
                self.console.print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0
            self.console.print("[cyan]Super Dev 流程状态: 尚未开始[/cyan]")
            self.console.print("  运行 'super-dev init <项目名>' 初始化项目")
            return 0
        # Initialized (super-dev.yaml exists) but no pipeline run yet
        if not run_state:
            try:
                cfg = get_config_manager(project_dir).config
                recent_snapshots = load_recent_workflow_snapshots(project_dir, limit=3)
                if not recent_snapshots:
                    current_snapshot = load_workflow_state(project_dir)
                    if isinstance(current_snapshot, dict) and current_snapshot:
                        recent_snapshots = [current_snapshot]
                if not recent_snapshots:
                    pipeline_summary = detect_pipeline_summary(project_dir)
                    if isinstance(pipeline_summary, dict) and pipeline_summary:
                        recent_snapshots = [pipeline_summary]
                recent_events = load_recent_workflow_events(project_dir, limit=3)
                if not recent_events and recent_snapshots:
                    first_snapshot = (
                        recent_snapshots[0] if isinstance(recent_snapshots[0], dict) else {}
                    )
                    recent_events = [
                        {
                            "event": "workflow_context_detected",
                            "phase": str(first_snapshot.get("workflow_mode", "")).strip()
                            or "continue",
                            "timestamp": str(first_snapshot.get("updated_at", "")).strip()
                            or datetime.now(timezone.utc).isoformat(),
                            "status": str(first_snapshot.get("status", "")).strip()
                            or "initialized_waiting",
                            "current_step_label": str(
                                first_snapshot.get("current_step_label", "")
                            ).strip(),
                        }
                    ]
                initialized_payload = {
                    "status": "initialized_waiting",
                    "project": cfg.name or project_dir.name,
                    "frontend": cfg.frontend or "-",
                    "backend": cfg.backend or "-",
                    "recommended_next": "在宿主中输入 /super-dev <你的需求> 开始",
                    "framework_playbook": load_framework_playbook_summary(project_dir),
                    "recent_snapshots": recent_snapshots,
                    "recent_events": recent_events,
                    "recent_hook_events": [
                        item.to_dict()
                        for item in HookManager.load_recent_history(project_dir, limit=3)
                    ],
                    "operational_harnesses": summarize_operational_harnesses(
                        project_dir, write_reports=False
                    ),
                    "operational_focus": derive_operational_focus(project_dir),
                }
                if getattr(args, "json", False):
                    sys.stdout.write(
                        json.dumps(initialized_payload, ensure_ascii=False, indent=2) + "\n"
                    )
                    return 0
                self.console.print("[cyan]Super Dev 流程状态: 已初始化，等待开始[/cyan]")
                self.console.print(f"  项目: {initialized_payload['project']}")
                self.console.print(f"  前端: {initialized_payload['frontend']}")
                self.console.print(f"  后端: {initialized_payload['backend']}")
                framework_playbook = initialized_payload.get("framework_playbook", {})
                if isinstance(framework_playbook, dict) and framework_playbook:
                    self.console.print(f"  跨平台框架: {framework_playbook.get('framework', '-')}")
                recent_snapshots = initialized_payload.get("recent_snapshots", [])
                if isinstance(recent_snapshots, list) and recent_snapshots:
                    first = recent_snapshots[0] if isinstance(recent_snapshots[0], dict) else {}
                    step = (
                        str(first.get("current_step_label", "")).strip()
                        or str(first.get("status", "")).strip()
                    )
                    updated_at = str(first.get("updated_at", "")).strip() or "-"
                    self.console.print(f"  最近快照: {updated_at} · {step}")
                harnesses = initialized_payload.get("operational_harnesses", [])
                if isinstance(harnesses, list) and harnesses:
                    self.console.print("  运行时 Harness:")
                    for item in harnesses[:3]:
                        if not isinstance(item, dict):
                            continue
                        label = (
                            str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
                        )
                        passed = bool(item.get("all_passed", False))
                        blocker = str(item.get("first_blocker", "")).strip()
                        line = f"    - {label}: {'ok' if passed else 'needs attention'}"
                        if blocker:
                            line += f" · {blocker}"
                        self.console.print(line)
                focus = initialized_payload.get("operational_focus", {})
                if isinstance(focus, dict) and str(focus.get("summary", "")).strip():
                    self.console.print(f"  当前治理焦点: {focus.get('summary')}")
                self.console.print("")
                self.console.print("  下一步: 在宿主中输入 /super-dev <你的需求> 开始")
                return 0
            except Exception:
                pass
        docs_state = self._get_docs_confirmation_state(project_dir)
        preview_state = self._get_preview_confirmation_state(project_dir)
        ui_state = self._get_ui_revision_state(project_dir)
        architecture_state = self._get_architecture_revision_state(project_dir)
        quality_state = self._get_quality_revision_state(project_dir)
        effective_status = self._effective_run_status(
            run_state=run_state,
            docs_state=docs_state,
            ui_state=ui_state,
            architecture_state=architecture_state,
            quality_state=quality_state,
        )
        phase_confirmations = {}
        if isinstance(run_state.get("phase_confirmations"), dict):
            phase_confirmations = dict(run_state.get("phase_confirmations") or {})
        payload = {
            "run_state_exists": bool(run_state),
            "status": effective_status,
            "description": str(
                (run_state.get("pipeline_args") or {}).get("description", "")
            ).strip(),
            "failed_stage": str(run_state.get("failed_stage", "")).strip(),
            "resume_from_stage": str(run_state.get("resume_from_stage", "")).strip(),
            "full_gate_passed": bool(run_state.get("full_gate_passed", False)),
            "skipped_gates": list(run_state.get("skipped_gates") or []),
            "scope_coverage_status": str(run_state.get("scope_coverage_status", "")).strip()
            or "unknown",
            "scope_coverage_rate": run_state.get("scope_coverage_rate"),
            "scope_gap_count": int(run_state.get("scope_gap_count", 0) or 0),
            "scope_high_priority_gap_count": int(
                run_state.get("scope_high_priority_gap_count", 0) or 0
            ),
            "docs_confirmation": docs_state,
            "preview_confirmation": preview_state,
            "ui_revision": ui_state,
            "architecture_revision": architecture_state,
            "quality_revision": quality_state,
            "phase_confirmations": phase_confirmations,
            "recommended_next": self._run_status_recommendation(
                run_state=run_state,
                docs_state=docs_state,
                preview_state=preview_state,
                ui_state=ui_state,
                architecture_state=architecture_state,
                quality_state=quality_state,
            ),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "recent_snapshots": load_recent_workflow_snapshots(project_dir, limit=3),
            "recent_events": load_recent_workflow_events(project_dir, limit=3),
            "recent_hook_events": [
                item.to_dict() for item in HookManager.load_recent_history(project_dir, limit=3)
            ],
            "operational_harnesses": summarize_operational_harnesses(
                project_dir, write_reports=False
            ),
            "operational_focus": derive_operational_focus(project_dir),
        }
        if getattr(args, "json", False):
            self.console.print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        self.console.print("[cyan]Super Dev 流程状态[/cyan]")
        self.console.print(f"  运行状态: {payload['status']}")
        self.console.print(f"  当前需求: {payload['description'] or '-'}")
        self.console.print(f"  失败阶段: {payload['failed_stage'] or '-'}")
        self.console.print(f"  恢复起点: {payload['resume_from_stage'] or '-'}")
        self.console.print(f"  全门禁通过: {'是' if payload['full_gate_passed'] else '否'}")
        self.console.print(
            "  跳过门禁: "
            + (", ".join(payload["skipped_gates"]) if payload["skipped_gates"] else "-")
        )
        scope_rate = payload["scope_coverage_rate"]
        scope_rate_text = (
            f"{float(scope_rate):.1f}%" if isinstance(scope_rate, int | float) else "-"
        )
        self.console.print(f"  范围覆盖状态: {payload['scope_coverage_status']}")
        self.console.print(f"  范围覆盖率: {scope_rate_text}")
        self.console.print(f"  范围缺口: {payload['scope_gap_count']}")
        self.console.print(f"  高优先级缺口: {payload['scope_high_priority_gap_count']}")
        self.console.print(f"  文档确认: {self._docs_confirmation_label(docs_state['status'])}")
        self.console.print(
            f"  UI 改版: {self._review_status_label(ui_state['status'], review_type='ui')}"
        )
        self.console.print(
            f"  架构返工: {self._review_status_label(architecture_state['status'], review_type='architecture')}"
        )
        self.console.print(
            f"  质量返工: {self._review_status_label(quality_state['status'], review_type='quality')}"
        )
        framework_playbook = payload.get("framework_playbook", {})
        if isinstance(framework_playbook, dict) and framework_playbook:
            self.console.print(f"  跨平台框架: {framework_playbook.get('framework', '-')}")
            native = framework_playbook.get("native_capabilities", [])
            validation = framework_playbook.get("validation_surfaces", [])
            if native:
                self.console.print(f"  原生能力面: {' / '.join(str(item) for item in native[:3])}")
            if validation:
                self.console.print(
                    f"  必验场景: {' / '.join(str(item) for item in validation[:3])}"
                )
        if phase_confirmations:
            self.console.print("  阶段确认:")
            for phase, item in sorted(phase_confirmations.items()):
                status = str((item or {}).get("status", "")).strip() or "pending_review"
                actor = str((item or {}).get("actor", "")).strip() or "-"
                self.console.print(f"    - {phase}: {self._review_status_label(status)} | {actor}")
        focus = payload.get("operational_focus", {})
        if isinstance(focus, dict) and str(focus.get("summary", "")).strip():
            self.console.print(f"  当前治理焦点: {focus.get('summary')}")
            action = str(focus.get("recommended_action", "")).strip()
            if action:
                self.console.print(f"  建议先做: {action}")
        recent_snapshots = payload.get("recent_snapshots", [])
        if isinstance(recent_snapshots, list) and recent_snapshots:
            first = recent_snapshots[0] if isinstance(recent_snapshots[0], dict) else {}
            step = (
                str(first.get("current_step_label", "")).strip()
                or str(first.get("status", "")).strip()
            )
            updated_at = str(first.get("updated_at", "")).strip() or "-"
            self.console.print(f"  最近快照: {updated_at} · {step}")
        recent_events = payload.get("recent_events", [])
        if isinstance(recent_events, list) and recent_events:
            first_event = recent_events[0] if isinstance(recent_events[0], dict) else {}
            event_time = str(first_event.get("timestamp", "")).strip() or "-"
            self.console.print(f"  最近事件: {event_time} · {describe_workflow_event(first_event)}")
        recent_hook_events = payload.get("recent_hook_events", [])
        if isinstance(recent_hook_events, list) and recent_hook_events:
            first_hook = recent_hook_events[0] if isinstance(recent_hook_events[0], dict) else {}
            blocked = bool(first_hook.get("blocked", False))
            success = bool(first_hook.get("success", False))
            hook_status = "blocked" if blocked else ("ok" if success else "failed")
            self.console.print(
                "  最近 Hook: "
                f"{str(first_hook.get('timestamp', '')).strip() or '-'} · "
                f"{str(first_hook.get('event', '')).strip() or '-'} / "
                f"{str(first_hook.get('phase', '')).strip() or '-'} / "
                f"{str(first_hook.get('hook_name', '')).strip() or '-'} / {hook_status}"
            )
        harnesses = payload.get("operational_harnesses", [])
        if isinstance(harnesses, list) and harnesses:
            self.console.print("  运行时 Harness:")
            for item in harnesses[:3]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
                status = "pass" if item.get("passed") else "fail"
                line = f"    - {label}: {status}"
                blocker = str(item.get("first_blocker", "")).strip()
                if blocker:
                    line += f" | {blocker}"
                self.console.print(line)
        self.console.print(f"  下一步: {payload['recommended_next']}")
        return 0

    def _cmd_run_confirm_phase(self, *, phase_name: str, comment: str, actor: str) -> int:
        project_dir = Path.cwd()
        normalized = phase_name.strip().lower()

        def _persist_phase_confirmation(phase_key: str) -> None:
            run_state = self._read_pipeline_run_state(project_dir) or {}
            phase_confirmations = run_state.get("phase_confirmations")
            if not isinstance(phase_confirmations, dict):
                phase_confirmations = {}
            if not str(run_state.get("status", "")).strip():
                run_state["status"] = "running"
            phase_confirmations[phase_key] = {
                "status": "confirmed",
                "comment": comment or f"{phase_key} 阶段确认通过",
                "actor": actor,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            run_state["phase_confirmations"] = phase_confirmations
            run_state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_pipeline_run_state(project_dir, run_state)

        if normalized in {"docs", "document", "documents"}:
            path, _ = save_bound_docs_confirmation(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "三文档确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("docs")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 docs 阶段: {path}")
            return 0
        if normalized in {"preview", "frontend", "frontend-preview"}:
            path, _ = save_bound_preview_confirmation(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "前端预览确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation(normalized)
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 preview 阶段: {path}")
            return 0
        if normalized in {"ui", "frontend-ui"}:
            path = save_ui_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "UI 阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("ui")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 ui 阶段: {path}")
            return 0
        if normalized in {"architecture", "arch"}:
            path = save_architecture_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "架构阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("architecture")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 architecture 阶段: {path}")
            return 0
        if normalized in {"quality", "qa"}:
            path = save_quality_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "质量阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("quality")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 quality 阶段: {path}")
            return 0
        _persist_phase_confirmation(normalized)
        self._write_session_brief(
            project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
        )
        self.console.print(f"[green]✓[/green] 已确认阶段: {normalized}")
        return 0

    def _cmd_run_targeted_refresh(self, target: str) -> int:
        project_dir = Path.cwd()
        config = get_config_manager(project_dir).config
        project_name = self._sanitize_project_name(config.name or project_dir.name)
        output_dir = project_dir / str(config.output_dir or "output")
        output_dir.mkdir(parents=True, exist_ok=True)
        run_state = self._read_pipeline_run_state(project_dir) or {}
        pipeline_args = run_state.get("pipeline_args") if isinstance(run_state, dict) else {}
        if not isinstance(pipeline_args, dict):
            pipeline_args = {}
        description = (
            str(pipeline_args.get("description", "")).strip()
            or str(config.description or "").strip()
            or project_name
        )
        domain = str(pipeline_args.get("domain", "")).strip() or str(config.domain or "")
        frontend = str(
            pipeline_args.get("frontend", "")
        ).strip() or self._normalize_pipeline_frontend(config.frontend)
        backend = str(pipeline_args.get("backend", "")).strip() or str(config.backend or "node")
        request_mode = (
            str((run_state.get("context") or {}).get("request_mode", "")).strip() or "feature"
        )

        if target == "research":
            import os

            from .orchestrator.knowledge import KnowledgeAugmenter

            disable_web = os.getenv("SUPER_DEV_DISABLE_WEB", "").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            augmenter = KnowledgeAugmenter(
                project_dir=project_dir,
                web_enabled=not disable_web,
                allowed_web_domains=config.knowledge_allowed_domains,
                cache_ttl_seconds=config.knowledge_cache_ttl_seconds,
            )
            bundle = augmenter.augment(requirement=description, domain=domain)
            research_file = output_dir / f"{project_name}-research.md"
            research_file.write_text(augmenter.to_markdown(bundle), encoding="utf-8")
            cache_file = augmenter.save_bundle(
                bundle=bundle,
                output_dir=output_dir,
                project_name=project_name,
                requirement=description,
                domain=domain,
            )
            self.console.print(f"[green]✓[/green] 已重跑 research: {research_file}")
            self.console.print(f"[green]✓[/green] 知识缓存: {cache_file}")
            return 0

        from .creators import DocumentGenerator

        knowledge_summary = {}
        bundle_path = output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
        if bundle_path.exists():
            try:
                knowledge_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
                if isinstance(knowledge_payload, dict):
                    knowledge_summary = dict(knowledge_payload.get("research_summary") or {})
                    enriched = str(knowledge_payload.get("enriched_requirement", "")).strip()
                    if enriched:
                        description = enriched
            except Exception:
                pass

        generator = DocumentGenerator(
            name=project_name,
            description=description,
            request_mode=request_mode,
            platform=str(config.platform or "web"),
            frontend=frontend,
            backend=backend,
            domain=domain,
            ui_library=config.ui_library,
            style_solution=config.style_solution,
            state_management=list(config.state_management or []),
            testing_frameworks=list(config.testing_frameworks or []),
            design_inspiration_slug=str(getattr(config, "design_inspiration_slug", "") or ""),
            language_preferences=list(config.language_preferences or []),
            knowledge_summary=knowledge_summary,
        )

        target_map = {
            "prd": (
                output_dir / f"{project_name}-prd.md",
                generator.generate_prd,
            ),
            "architecture": (
                output_dir / f"{project_name}-architecture.md",
                generator.generate_architecture,
            ),
            "uiux": (
                output_dir / f"{project_name}-uiux.md",
                generator.generate_uiux,
            ),
        }
        file_path, factory = target_map[target]
        file_path.write_text(factory(), encoding="utf-8")
        if target == "uiux":
            contract_path = output_dir / f"{project_name}-ui-contract.json"
            contract_path.write_text(
                json.dumps(generator.generate_ui_contract(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.console.print(f"[green]✓[/green] 已重跑 {target}: {file_path}")
        return 0

    def _cmd_run_from_stage(self, *, stage_selector: str, show_impact: bool) -> int:
        project_dir = Path.cwd()
        run_state = self._read_pipeline_run_state(project_dir)
        if not run_state:
            self.console.print("[red]未找到可恢复运行记录，无法按阶段继续[/red]")
            self.console.print(
                "[dim]请先运行一次 super-dev 完成宿主接入，然后回到宿主里触发 Super Dev 流程。[/dim]"
            )
            return 1
        stage_number = self._resolve_pipeline_stage_selector(stage_selector)
        if stage_number is None:
            self.console.print(f"[red]无法识别阶段: {stage_selector}[/red]")
            self.console.print(
                "[dim]可用阶段: research/docs/spec/frontend/backend/quality/delivery/rehearsal[/dim]"
            )
            return 1
        if show_impact:
            impact_lines = self._stage_jump_impact(stage_number)
            self.console.print(
                f"[cyan]阶段回跳影响分析（目标: {stage_selector} / 第 {stage_number} 阶段）[/cyan]"
            )
            for line in impact_lines:
                self.console.print(f"  - {line}")
        run_state["status"] = "failed"
        run_state["failed_stage"] = str(stage_number)
        run_state["resume_from_stage"] = str(stage_number)
        run_state["next_stage"] = str(stage_number)
        run_state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_pipeline_run_state(project_dir, run_state)
        self.console.print(f"[cyan]将从第 {stage_number} 阶段继续执行...[/cyan]")
        return self._cmd_run_resume(argparse.Namespace(resume=True))

    def _effective_run_status(
        self,
        *,
        run_state: dict[str, Any],
        docs_state: dict[str, Any],
        ui_state: dict[str, Any],
        architecture_state: dict[str, Any],
        quality_state: dict[str, Any],
    ) -> str:
        explicit_status = str(run_state.get("status", "")).strip().lower()
        if explicit_status:
            return explicit_status

        normalized_status = str(run_state.get("status_normalized", "")).strip().lower()
        if normalized_status and normalized_status != "unknown":
            return normalized_status

        phase_confirmations = run_state.get("phase_confirmations")
        has_phase_confirmations = isinstance(phase_confirmations, dict) and bool(
            phase_confirmations
        )
        review_states = (docs_state, ui_state, architecture_state, quality_state)
        has_review_evidence = any(
            bool(state.get("exists"))
            or str(state.get("status", "")).strip() not in {"", "pending_review"}
            for state in review_states
        )
        if has_phase_confirmations or has_review_evidence:
            return "running"
        return "unknown"

    def _run_status_recommendation(
        self,
        *,
        run_state: dict[str, Any],
        docs_state: dict[str, Any],
        preview_state: dict[str, Any],
        ui_state: dict[str, Any],
        architecture_state: dict[str, Any],
        quality_state: dict[str, Any],
    ) -> str:
        if docs_state.get("status") != "confirmed":
            return "在宿主里确认三文档；如果通过，直接说“文档确认，可以继续”"
        if preview_state.get("status") == "revision_requested":
            return "在宿主里继续修改前端；确认后直接说“前端预览确认，可以继续”"
        if ui_state.get("status") == "revision_requested":
            return "在宿主里完成 UI 改版后直接说“UI 改版已完成，继续当前流程”"
        if architecture_state.get("status") == "revision_requested":
            return "在宿主里完成架构返工后直接说“架构调整已完成，继续当前流程”"
        if quality_state.get("status") == "revision_requested":
            return "在宿主里完成质量整改后直接说“质量整改已完成，继续当前流程”"
        status = self._effective_run_status(
            run_state=run_state,
            docs_state=docs_state,
            ui_state=ui_state,
            architecture_state=architecture_state,
            quality_state=quality_state,
        )
        skipped_gates = list(run_state.get("skipped_gates") or [])
        scope_status = str(run_state.get("scope_coverage_status", "")).strip().lower() or "unknown"
        high_priority_scope_gaps = int(run_state.get("scope_high_priority_gap_count", 0) or 0)
        if scope_status in {"partial", "unknown"} or high_priority_scope_gaps > 0:
            return "在宿主里继续当前流程，并优先补齐缺失范围与高优先级功能项"
        if status == "success" and skipped_gates:
            return "按当前策略补跑被跳过的红队 / 质量 / 发布演练门禁"
        if status in {
            "failed",
            "running",
            "waiting_confirmation",
            "waiting_preview_confirmation",
            "waiting_ui_revision",
            "waiting_architecture_revision",
            "waiting_quality_revision",
        }:
            return "在宿主里说“继续当前流程，不要重新开题”"
        return "在宿主里说“继续当前流程，进入前端实现与运行验证”"

    def _current_workflow_description(self, project_dir: Path) -> str:
        run_state = self._read_pipeline_run_state(project_dir) or {}
        pipeline_args = run_state.get("pipeline_args") if isinstance(run_state, dict) else {}
        if isinstance(pipeline_args, dict):
            description = str(pipeline_args.get("description", "")).strip()
            if description:
                return description
        config = get_config_manager(project_dir).config
        return str(config.description or "").strip()

    def _session_brief_path(self, project_dir: Path) -> Path:
        return Path(project_dir).resolve() / ".super-dev" / "SESSION_BRIEF.md"

    def _workflow_state_path(self, project_dir: Path) -> Path:
        return workflow_state_file(project_dir)

    def _write_workflow_state(self, *, project_dir: Path, payload: dict[str, Any]) -> Path:
        project_dir = Path(project_dir).resolve()
        run_state = self._read_pipeline_run_state(project_dir) or {}
        docs_state = self._get_docs_confirmation_state(project_dir)
        preview_state = self._get_preview_confirmation_state(project_dir)
        ui_state = self._get_ui_revision_state(project_dir)
        architecture_state = self._get_architecture_revision_state(project_dir)
        quality_state = self._get_quality_revision_state(project_dir)
        workflow_payload = {
            "status": str(payload.get("status", "")).strip(),
            "current_step_label": str(payload.get("current_step_label", "")).strip(),
            "user_next_action": str(payload.get("user_next_action", "")).strip(),
            "recommended_command": str(payload.get("recommended_command", "")).strip(),
            "reason": str(payload.get("reason", "")).strip(),
            "evidence": str(payload.get("evidence", "")).strip(),
            "preferred_host": str(payload.get("preferred_host", "")).strip(),
            "preferred_host_name": str(payload.get("preferred_host_name", "")).strip(),
            "host_continue_prompt": str(payload.get("host_continue_prompt", "")).strip(),
            "session_brief_path": str(self._session_brief_path(project_dir)),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "continuity_rules": list(payload.get("continuity_rules") or []),
            "gates": {
                "docs_confirmation": {
                    "status": str(docs_state.get("status", "")).strip(),
                    "comment": str(docs_state.get("comment", "")).strip(),
                },
                "preview_confirmation": {
                    "status": str(preview_state.get("status", "")).strip(),
                    "comment": str(preview_state.get("comment", "")).strip(),
                },
                "ui_revision": {
                    "status": str(ui_state.get("status", "")).strip(),
                    "comment": str(ui_state.get("comment", "")).strip(),
                },
                "architecture_revision": {
                    "status": str(architecture_state.get("status", "")).strip(),
                    "comment": str(architecture_state.get("comment", "")).strip(),
                },
                "quality_revision": {
                    "status": str(quality_state.get("status", "")).strip(),
                    "comment": str(quality_state.get("comment", "")).strip(),
                },
            },
            "pipeline_run_state": {
                "status": str(run_state.get("status", "")).strip(),
                "current_stage": str(run_state.get("current_stage", "")).strip(),
                "current_stage_title": str(run_state.get("current_stage_title", "")).strip(),
                "scope_coverage_status": str(run_state.get("scope_coverage_status", "")).strip(),
                "scope_high_priority_gap_count": int(
                    run_state.get("scope_high_priority_gap_count", 0) or 0
                ),
                "skipped_gates": list(run_state.get("skipped_gates") or []),
            },
        }
        return save_workflow_state(project_dir, workflow_payload)

    def _build_session_continuity_rules(self, *, status: str) -> list[str]:
        return workflow_continuity_rules(status)

    def _build_continue_interaction_clause(self, *, status: str, current_step_label: str) -> str:
        rules = self._build_session_continuity_rules(status=status)
        leading = f"当前步骤是“{current_step_label}”。" if current_step_label else ""
        return leading + "".join(rules)

    def _write_session_brief(self, *, project_dir: Path, payload: dict[str, Any]) -> Path:
        project_dir = Path(project_dir).resolve()
        brief_path = self._session_brief_path(project_dir)
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        preferred_host_name = str(
            payload.get("preferred_host_name", "")
        ).strip() or host_display_name(
            str(payload.get("preferred_host", "")).strip()
            or self._preferred_host_target_for_project(project_dir)
        )
        host_prompt = str(payload.get("host_continue_prompt", "")).strip()
        continuity_rules = payload.get("continuity_rules") or []
        action_card = (
            payload.get("action_card") if isinstance(payload.get("action_card"), dict) else {}
        )
        if not isinstance(continuity_rules, list):
            continuity_rules = []
        lines = [
            "# Super Dev Session Brief",
            "",
            f"- 动作类型: {self._workflow_mode_label(str(payload.get('workflow_mode', '')).strip())}",
            f"- 当前步骤: {payload.get('current_step_label', payload.get('status', '-'))}",
            f"- 当前状态: {payload.get('status', '-')}",
            f"- 用户下一步: {payload.get('user_next_action', payload.get('recommended_command', '-'))}",
            f"- 系统建议动作: {payload.get('recommended_command', '-')}",
            f"- 推荐宿主: {preferred_host_name or '-'}",
            f"- 工作流状态 JSON: {self._workflow_state_path(project_dir)}",
            f"- 最新历史快照: {latest_workflow_snapshot_file(project_dir)}",
            f"- 事件日志: {workflow_event_log_file(project_dir)}",
            f"- Hook 审计日志: {HookManager.hook_history_file(project_dir)}",
        ]
        recent_snapshots = (
            payload.get("recent_snapshots")
            if isinstance(payload.get("recent_snapshots"), list)
            else []
        )
        framework_playbook = load_framework_playbook_summary(project_dir)
        if framework_playbook:
            lines.append(f"- 跨平台框架: {framework_playbook.get('framework', '-')}")
            native = framework_playbook.get("native_capabilities", [])
            validation = framework_playbook.get("validation_surfaces", [])
            if native:
                lines.append(f"- 原生能力面: {' / '.join(str(item) for item in native[:3])}")
            if validation:
                lines.append(f"- 必验场景: {' / '.join(str(item) for item in validation[:3])}")
        harness_summaries = summarize_operational_harnesses(project_dir, write_reports=False)
        if harness_summaries:
            lines.extend(["", "## 运行时 Harness 摘要"])
            for item in harness_summaries[:3]:
                label = str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
                status = "pass" if item.get("passed") else "fail"
                line = f"- {label}: {status}"
                blocker = str(item.get("first_blocker", "")).strip()
                if blocker:
                    line += f" · {blocker}"
                lines.append(line)
        user_action_shortcuts = (
            payload.get("user_action_shortcuts")
            if isinstance(payload.get("user_action_shortcuts"), list)
            else []
        )
        if user_action_shortcuts:
            lines.append(
                f"- 你现在可以直接说: {' / '.join(str(item) for item in user_action_shortcuts[:4])}"
            )
        action_examples = (
            action_card.get("examples") if isinstance(action_card.get("examples"), list) else []
        )
        if action_examples:
            lines.append(f"- 自然语言示例: {', '.join(str(item) for item in action_examples[:3])}")
        scenario_cards = (
            payload.get("scenario_cards") if isinstance(payload.get("scenario_cards"), list) else []
        )
        if scenario_cards:
            lines.extend(["", "## 现实场景怎么做"])
            for item in scenario_cards[:4]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                command = str(item.get("cli_command", "")).strip()
                description = str(item.get("description", "")).strip()
                if title and command:
                    line = f"- {title}: `{command}`"
                    if description:
                        line += f" · {description}"
                    lines.append(line)
        if host_prompt:
            lines.append(f"- 宿主第一句: {host_prompt}")
        if payload.get("reason"):
            lines.append(f"- 原因: {payload.get('reason')}")
        if payload.get("evidence"):
            lines.append(f"- 依据: {payload.get('evidence')}")
        if continuity_rules:
            lines.extend(["", "## 会话连续性规则"])
            for item in continuity_rules:
                lines.append(f"- {item}")
        self._write_workflow_state(project_dir=project_dir, payload=payload)
        if not recent_snapshots:
            recent_snapshots = load_recent_workflow_snapshots(project_dir, limit=3)
        if recent_snapshots:
            lines.extend(["", "## 最近流程快照"])
            for item in recent_snapshots[:3]:
                if not isinstance(item, dict):
                    continue
                step = (
                    str(item.get("current_step_label", "")).strip()
                    or str(item.get("status", "")).strip()
                )
                updated_at = str(item.get("updated_at", "")).strip() or "-"
                lines.append(f"- {updated_at} · {step}")
        recent_events = load_recent_workflow_events(project_dir, limit=3)
        if recent_events:
            lines.extend(["", "## 最近状态事件"])
            for item in recent_events:
                updated_at = str(item.get("timestamp", "")).strip() or "-"
                lines.append(f"- {updated_at} · {describe_workflow_event(item)}")
        recent_hook_events = HookManager.load_recent_history(project_dir, limit=3)
        if recent_hook_events:
            lines.extend(["", "## 最近 Hook 事件"])
            for item in recent_hook_events:
                status = "blocked" if item.blocked else ("ok" if item.success else "failed")
                lines.append(
                    f"- {item.timestamp} · {item.event} / {item.phase or '-'} / {item.hook_name} / {status}"
                )
        recent_timeline = load_recent_operational_timeline(project_dir, limit=5)
        if recent_timeline:
            lines.extend(["", "## 最近关键时间线"])
            for item in recent_timeline:
                title = str(item.get("title", "")).strip() or str(item.get("kind", "")).strip()
                message = str(item.get("message", "")).strip() or "-"
                updated_at = str(item.get("timestamp", "")).strip() or "-"
                lines.append(f"- {updated_at} · {title} · {message}")
        lines.extend(
            [
                "",
                "## 离开当前流程的唯一条件",
                "- 用户明确说要取消当前流程。",
                "- 用户明确说要重新开始一条新的流程。",
                "- 用户明确说要切回普通聊天，而不是继续 Super Dev。",
                "",
                "## 下次回来怎么继续",
                "- 回到宿主后，直接说“继续当前流程”。",
                "- 如果只想知道现在先做什么，就在宿主里说“现在下一步是什么”。",
            ]
        )
        brief_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return brief_path

    def _build_host_continue_prompt(
        self,
        *,
        project_dir: Path,
        target: str,
        next_payload: dict[str, Any] | None = None,
    ) -> str:
        instruction = self._build_host_continue_instruction(
            project_dir=project_dir,
            next_payload=next_payload,
        )
        entry_prompts = build_host_entry_prompts(
            target=target,
            instruction=instruction,
            supports_slash=self._supports_slash_for_prompt(target),
        )
        preferred_entry = str(entry_prompts.get("preferred_entry", "")).strip()
        prompts = entry_prompts.get("entry_prompts", {})
        if isinstance(prompts, dict) and preferred_entry:
            prompt = str(prompts.get(preferred_entry, "")).strip()
            if prompt:
                return prompt
        return self._build_host_trigger_example(target=target, idea=instruction)

    def _build_host_continue_instruction(
        self,
        *,
        project_dir: Path,
        next_payload: dict[str, Any] | None = None,
    ) -> str:
        next_payload = dict(next_payload or {})
        status = str(next_payload.get("status", "")).strip()
        current_step_label = str(next_payload.get("current_step_label", "")).strip()
        continuity_clause = self._build_continue_interaction_clause(
            status=status,
            current_step_label=current_step_label,
        )
        description = self._current_workflow_description(project_dir)
        if description:
            instruction = (
                f"继续当前项目“{description}”的 Super Dev 流程，不要当作普通聊天。"
                "先读取 .super-dev/SESSION_BRIEF.md、.super-dev/workflow-state.json、.super-dev/WORKFLOW.md、output/*、.super-dev/review-state/* 和最近的 tasks.md。"
                f"{continuity_clause}"
            )
        else:
            return (
                "继续当前项目的 Super Dev 流程，不要当作普通聊天。"
                "先读取 .super-dev/SESSION_BRIEF.md、.super-dev/workflow-state.json、.super-dev/WORKFLOW.md、output/*、.super-dev/review-state/* 和最近的 tasks.md。"
                f"{continuity_clause}"
            )
        return instruction

    def _build_host_start_prompt(self, *, project_dir: Path, target: str) -> str:
        description = self._current_workflow_description(project_dir)
        if description:
            instruction = (
                f"请用 Super Dev 流程开始处理当前项目“{description}”，不要当作普通聊天。"
                "先做 research，再产出 PRD、Architecture、UIUX 三文档，完成后停下来等我确认。"
            )
        else:
            instruction = (
                "请用 Super Dev 流程开始处理当前需求，不要当作普通聊天。"
                "先做 research，再产出 PRD、Architecture、UIUX 三文档，完成后停下来等我确认。"
            )
        return self._build_host_trigger_example(target=target, idea=instruction)

    def _supports_slash_for_prompt(self, target: str) -> bool:
        from .integrations import IntegrationManager

        return IntegrationManager.supports_slash(target)

    def _build_workflow_session_hint(self, *, project_dir: Path, target: str) -> dict[str, Any]:
        if not self._project_has_super_dev_context(project_dir):
            return {
                "session_mode": "fresh_start",
                "continue_prompt": "",
                "recommended_workflow_command": "",
                "workflow_reason": "",
                "continuity_rules": [],
                "workflow_context": {},
            }
        next_payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=next_payload)
        action_card = (
            next_payload.get("action_card")
            if isinstance(next_payload.get("action_card"), dict)
            else {}
        )
        continue_prompt = self._build_host_continue_prompt(
            project_dir=project_dir, target=target, next_payload=next_payload
        )
        recommended_workflow_command = str(
            next_payload.get("recommended_command", "")
        ).strip()
        return {
            "session_mode": "continue_super_dev",
            "continue_instruction": self._build_host_continue_instruction(
                project_dir=project_dir,
                next_payload=next_payload,
            ),
            "continue_prompt": continue_prompt,
            "recommended_workflow_command": recommended_workflow_command,
            "workflow_reason": str(next_payload.get("reason", "")).strip(),
            "workflow_status": str(next_payload.get("status", "")).strip(),
            "workflow_mode": str(next_payload.get("workflow_mode", "")).strip(),
            "action_title": str(action_card.get("title", "")).strip()
            or str(next_payload.get("current_step_label", "")).strip(),
            "action_examples": list(action_card.get("examples") or []),
            "user_action_shortcuts": list(next_payload.get("user_action_shortcuts") or []),
            "scenario_cards": list(next_payload.get("scenario_cards") or []),
            "continuity_rules": list(
                next_payload.get("continuity_rules") or action_card.get("continuity_rules") or []
            ),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "workflow_context": build_host_workflow_context(
                project_dir,
                entry_mode="continue",
                target=target,
            ),
        }

    def _auto_migrate_if_needed(self, project_dir: Path) -> None:
        """检测项目配置版本，如果低于当前 CLI 版本则自动迁移。"""
        try:
            config_path = project_dir / "super-dev.yaml"
            if not config_path.exists():
                return
            import yaml

            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            project_version = data.get("version", "")
            if project_version == __version__:
                return
            self.console.print(
                f"[yellow]检测到项目配置版本 {project_version or '未知'}，"
                f"当前 CLI 版本 {__version__}，正在自动迁移...[/yellow]"
            )
            from .migrate import migrate_project

            changes = migrate_project(project_dir)
            for change in changes:
                self.console.print(f"  [green]✓[/green] {change}")
            self.console.print("")
        except Exception:
            pass

    def _project_has_super_dev_context(self, project_dir: Path) -> bool:
        """只有当前目录有 super-dev.yaml 且不是家目录才算 Super Dev 项目。"""
        project_dir = Path(project_dir).resolve()
        if project_dir == Path.home().resolve():
            return False
        return (project_dir / "super-dev.yaml").exists()

    def _preferred_host_target_for_project(self, project_dir: Path) -> str:
        from .integrations import IntegrationManager

        project_dir = Path(project_dir).resolve()
        config = get_config_manager(project_dir).config
        available_targets = [item.name for item in IntegrationManager(project_dir).list_targets()]
        preferred_order = list(
            dict.fromkeys(("codex", "codex-cli", "claude-code", "claude", "opencode", *PRIMARY_HOST_TOOL_IDS))
        )

        def _pick_best(candidates: list[str]) -> str | None:
            for host_id in preferred_order:
                if host_id in candidates:
                    return host_id
            return candidates[0] if candidates else None

        configured_targets = [
            item for item in config.host_profile_targets if item in available_targets
        ]
        if configured_targets:
            best = _pick_best(configured_targets)
            if best:
                return best

        configured_surfaces = self._collect_configured_host_targets(
            project_dir=project_dir,
            available_targets=available_targets,
        )
        if configured_surfaces:
            best = _pick_best(configured_surfaces)
            if best:
                return best

        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        if detected_targets:
            best = _pick_best(detected_targets)
            if best:
                return best
        return "codex"

    def _describe_next_step(self, *, status: str, recommended_command: str) -> tuple[str, str]:
        status_map = {
            "not_initialized": (
                "还没完成宿主接入",
                "先把 Super Dev 装进一个宿主，并确认可以触发。",
            ),
            "missing_core_docs": (
                "三文档还没补齐",
                "先让宿主按 Super Dev 流程补齐 PRD、Architecture、UIUX 三文档。",
            ),
            "waiting_docs_confirmation": (
                "等待三文档确认",
                "先确认 PRD、Architecture、UIUX 三文档，再继续后续阶段。",
            ),
            "waiting_confirmation": (
                "等待流程确认门",
                "先处理当前确认门，再继续恢复当前流水线。",
            ),
            "waiting_ui_revision": (
                "等待 UI 改版闭环",
                "先更新 UIUX 文档并完成前端返工，再恢复流程。",
            ),
            "waiting_preview_confirmation": (
                "等待前端预览确认",
                "先评审并确认当前前端预览，再决定是否进入后端和后续阶段。",
            ),
            "waiting_architecture_revision": (
                "等待架构返工闭环",
                "先更新架构文档并同步实现，再恢复流程。",
            ),
            "waiting_quality_revision": (
                "等待质量整改闭环",
                "先完成质量整改并重新过门禁，再恢复流程。",
            ),
            "delivery_closure_incomplete": (
                "交付证据还没闭环",
                "先补齐质量与发布证据，再进入交付。",
            ),
            "product_revision_required": (
                "产品审查要求修订",
                "先处理产品审查里的高优先级问题。",
            ),
            "proof_pack_incomplete": (
                "proof-pack 还没补齐",
                "先重新生成交付证据包。",
            ),
            "ready": (
                "当前流程可以继续推进",
                "先打开状态面板确认当前阶段，再继续执行。",
            ),
        }
        if status in status_map:
            return status_map[status]

        command_map = {
            "在宿主里说“继续当前流程，不要重新开题”": (
                "当前流程可从中断点恢复",
                "先从上次中断的位置继续，不要重新开一轮。",
            ),
            "在宿主里说“继续当前流程”": (
                "当前流程需要先看状态面板",
                "先看状态面板，确认当前卡在哪一步。",
            ),
            "在宿主里继续当前流程，并补齐交付闭环与发布证据": (
                "当前卡在质量/交付闭环",
                "先跑完整质量门禁，补齐交付闭环。",
            ),
            "在宿主里先处理产品审查要求的修订项，再继续当前流程": (
                "当前卡在产品审查",
                "先重新执行产品审查并处理要求修订项。",
            ),
        }
        return command_map.get(
            recommended_command,
            ("当前流程存在待处理项", "先按推荐动作继续当前流程，不要另起一轮普通聊天。"),
        )

    def _finalize_next_step_payload(
        self, *, project_dir: Path, payload: dict[str, Any]
    ) -> dict[str, Any]:
        project_dir = Path(project_dir).resolve()
        preferred_host = self._preferred_host_target_for_project(project_dir)
        preferred_host_name = (
            "Codex" if preferred_host == "codex-cli" else host_display_name(preferred_host)
        )
        action_card = (
            payload.get("action_card") if isinstance(payload.get("action_card"), dict) else {}
        )
        current_step_label = str(action_card.get("title", "")).strip()
        user_next_action = str(action_card.get("user_action", "")).strip()
        if not current_step_label or not user_next_action:
            current_step_label, user_next_action = self._describe_next_step(
                status=str(payload.get("status", "")).strip(),
                recommended_command=str(payload.get("recommended_command", "")).strip(),
            )
        if self._project_has_super_dev_context(project_dir):
            continue_instruction = self._build_host_continue_instruction(
                project_dir=project_dir,
                next_payload={
                    **payload,
                    "current_step_label": current_step_label,
                    "user_next_action": user_next_action,
                },
            )
            host_continue_prompt = self._build_host_continue_prompt(
                project_dir=project_dir,
                target=preferred_host,
                next_payload={
                    **payload,
                    "current_step_label": current_step_label,
                    "user_next_action": user_next_action,
                },
            )
        else:
            continue_instruction = ""
            host_continue_prompt = self._build_host_start_prompt(
                project_dir=project_dir, target=preferred_host
            )
        host_entry_bundle = build_host_entry_prompts(
            target=preferred_host,
            instruction=continue_instruction or host_continue_prompt,
            supports_slash=self._supports_slash_for_prompt(preferred_host),
        )
        enriched = dict(payload)
        enriched.update(
            {
                "current_step_label": current_step_label,
                "user_next_action": user_next_action,
                "preferred_host": preferred_host,
                "preferred_host_name": preferred_host_name,
                "host_continue_prompt": host_continue_prompt,
                "host_continue_entry_prompts": (
                    host_entry_bundle.get("entry_prompts", {})
                    if isinstance(host_entry_bundle.get("entry_prompts", {}), dict)
                    else {}
                ),
                "host_continue_entry_labels": (
                    host_entry_bundle.get("entry_labels", {})
                    if isinstance(host_entry_bundle.get("entry_labels", {}), dict)
                    else {}
                ),
                "host_continue_preferred_entry": str(
                    host_entry_bundle.get("preferred_entry", "")
                ).strip(),
                "host_continue_preferred_entry_label": str(
                    host_entry_bundle.get("preferred_entry_label", "")
                ).strip(),
                "session_brief_path": str(self._session_brief_path(project_dir)),
                "workflow_state_path": str(self._workflow_state_path(project_dir)),
                "continuity_rules": self._build_session_continuity_rules(
                    status=str(payload.get("status", "")).strip()
                ),
                "workflow_mode": str(
                    action_card.get("mode", payload.get("workflow_mode", ""))
                ).strip()
                or "continue",
                "action_card": action_card,
                "user_action_shortcuts": self._workflow_mode_shortcuts(
                    str(action_card.get("mode", payload.get("workflow_mode", ""))).strip()
                    or "continue",
                    action_card=action_card,
                ),
                "recent_snapshots": load_recent_workflow_snapshots(project_dir, limit=3),
            }
        )
        return enriched

    def _build_next_step_payload(self, project_dir: Path) -> dict[str, Any]:
        project_dir = Path(project_dir).resolve()
        if not self._project_has_super_dev_context(project_dir):
            return self._finalize_next_step_payload(
                project_dir=project_dir,
                payload={
                    "status": "not_initialized",
                    "reason": "当前目录还没有进入 Super Dev 工作流。",
                    "recommended_command": "super-dev",
                    "evidence": "未检测到 super-dev.yaml / .super-dev/WORKFLOW.md / output 基础产物",
                },
            )

        summary = detect_pipeline_summary(
            project_dir, self._read_pipeline_run_state(project_dir) or {}
        )
        checkpoint_status = str(summary.get("workflow_status", "")).strip() or "ready"
        recommended_command = (
            str(summary.get("recommended_command", "")).strip() or "在宿主里说“继续当前流程”"
        )
        blocker = str(summary.get("blocker", "")).strip()
        evidence = str(summary.get("evidence", "")).strip()

        if checkpoint_status not in {"ready", "missing_quality", "missing_delivery"}:
            return self._finalize_next_step_payload(
                project_dir=project_dir,
                payload={
                    "status": checkpoint_status,
                    "reason": blocker
                    or "当前仓库存在运行态、确认门或范围门禁，需要先沿当前流程继续。",
                    "recommended_command": recommended_command,
                    "evidence": evidence or f"workflow_status={checkpoint_status}",
                    "workflow_mode": str(summary.get("workflow_mode", "")).strip(),
                    "action_card": summary.get("action_card"),
                    "scenario_cards": summary.get("scenario_cards"),
                },
            )

        readiness_path = project_dir / "output" / f"{project_dir.name}-release-readiness.json"
        if readiness_path.exists():
            try:
                readiness_payload = json.loads(readiness_path.read_text(encoding="utf-8"))
            except Exception:
                readiness_payload = {}
            failed_checks = (
                list(readiness_payload.get("failed_checks") or [])
                if isinstance(readiness_payload, dict)
                else []
            )
            if "Delivery Closure" in failed_checks:
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "delivery_closure_incomplete",
                        "reason": "发布闭环证据还没有齐。",
                        "recommended_command": "在宿主里继续当前流程，并补齐交付闭环与发布证据",
                        "evidence": "release readiness failed_checks 包含 Delivery Closure",
                    },
                )

        product_audit_path = project_dir / "output" / f"{project_dir.name}-product-audit.json"
        if product_audit_path.exists():
            try:
                product_audit_payload = json.loads(product_audit_path.read_text(encoding="utf-8"))
            except Exception:
                product_audit_payload = {}
            product_status = str(product_audit_payload.get("status", "")).strip()
            if product_status == "revision_required":
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "product_revision_required",
                        "reason": "产品审查仍然要求修订。",
                        "recommended_command": "在宿主里先处理产品审查要求的修订项，再继续当前流程",
                        "evidence": f"product_audit.status={product_status}",
                    },
                )

        proof_pack_path = project_dir / "output" / f"{project_dir.name}-proof-pack.json"
        if proof_pack_path.exists():
            try:
                proof_pack_payload = json.loads(proof_pack_path.read_text(encoding="utf-8"))
            except Exception:
                proof_pack_payload = {}
            proof_pack_status = str(proof_pack_payload.get("status", "")).strip()
            if proof_pack_status == "incomplete":
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "proof_pack_incomplete",
                        "reason": "当前交付证据包还没有齐。",
                        "recommended_command": "在宿主里继续当前流程，并补齐 proof-pack 依赖证据",
                        "evidence": f"proof_pack.status={proof_pack_status}",
                    },
                )

        return self._finalize_next_step_payload(
            project_dir=project_dir,
            payload={
                "status": "ready",
                "reason": blocker or "当前没有检测到待恢复的流程门禁，建议从状态面板继续。",
                "recommended_command": "在宿主里说“继续当前流程”",
                "evidence": evidence or "未检测到更高优先级阻断项",
                "workflow_mode": str(summary.get("workflow_mode", "")).strip(),
                "action_card": summary.get("action_card"),
                "scenario_cards": summary.get("scenario_cards"),
            },
        )

    def _resolve_pipeline_stage_selector(self, value: str) -> int | None:
        normalized = str(value).strip().lower()
        stage_map = {
            "research": 0,
            "discovery": 0,
            "docs": 1,
            "document": 1,
            "documents": 1,
            "prd": 1,
            "architecture": 1,
            "uiux": 1,
            "spec": 2,
            "frontend": 3,
            "ui": 3,
            "backend": 4,
            "implementation": 4,
            "redteam": 5,
            "quality": 6,
            "qa": 6,
            "review": 7,
            "prompt": 8,
            "cicd": 9,
            "deploy-fix": 10,
            "delivery": 11,
            "rehearsal": 12,
        }
        if normalized.isdigit():
            stage_number = int(normalized)
            if 0 <= stage_number <= 12:
                return stage_number
            return None
        return stage_map.get(normalized)

    def _stage_jump_impact(self, stage_number: int) -> list[str]:
        if stage_number <= 1:
            return [
                "将重做 research / PRD / Architecture / UIUX",
                "会使 Spec 与任务拆解重新计算",
                "后续实现与质量验证需要全量重跑",
            ]
        if stage_number == 2:
            return [
                "将重算 Spec 与 tasks",
                "前后端实现任务依赖会刷新",
                "建议在继续前确认三文档未变更",
            ]
        if stage_number == 3:
            return [
                "将重做前端实施蓝图与预览验证",
                "可能触发 UI 改版门重新确认",
            ]
        if stage_number == 4:
            return [
                "将重做宿主实现参考与任务执行",
                "后续红队与质量门禁会重新执行",
            ]
        if stage_number >= 5:
            return [
                "将从质量/交付后段开始重跑",
                "不会重建前置文档与 spec，除非门禁判定需要回退",
            ]
        return ["将按目标阶段继续执行并自动校验前置门禁"]

    def _cmd_pipeline(self, args) -> int:
        """运行完整流水线 - 从想法到部署"""
        self._print_governance_boundary_notice(
            "流水线负责生成研究、文档、门禁与交付产物；实际编码能力仍由宿主 AI 提供。"
        )
        request_mode_override = getattr(args, "mode", "feature")
        if request_mode_override not in {"feature", "bugfix"}:
            request_mode_override = "feature"
        # 确定项目名称
        project_name = args.name
        if not project_name:
            import re

            words = re.findall(r"[\w]+", args.description)
            if words:
                project_name = "-".join(words[:3]).lower()
            else:
                project_name = "my-project"
        project_name = self._sanitize_project_name(project_name)

        tech_stack = {
            "platform": args.platform,
            "frontend": args.frontend,
            "backend": args.backend,
            "domain": args.domain,
        }

        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_config = ConfigManager(project_dir).load()
        if not self._ensure_pipeline_host_ready(project_dir=project_dir, config=pipeline_config):
            return 1
        resume_requested = bool(getattr(args, "resume", False))
        from .policy import PipelinePolicyManager

        policy_manager = PipelinePolicyManager(project_dir)
        policy_violations = policy_manager.validate_pipeline_args(args=args, config=pipeline_config)
        if policy_violations:
            self.console.print("[red]流水线策略校验未通过:[/red]")
            for item in policy_violations:
                self.console.print(f"  - {item}")
            self.console.print(f"[dim]策略文件: {policy_manager.policy_path}[/dim]")
            self.console.print("[dim]请检查 .super-dev/policy.yaml 或 super-dev.yaml 中的当前治理配置[/dim]")
            return 1

        pipeline_args_snapshot: dict[str, Any] = {
            "description": args.description,
            "mode": request_mode_override,
            "platform": args.platform,
            "frontend": args.frontend,
            "backend": args.backend,
            "domain": args.domain,
            "name": args.name,
            "cicd": args.cicd,
            "skip_redteam": bool(args.skip_redteam),
            "skip_scaffold": bool(args.skip_scaffold),
            "skip_quality_gate": bool(args.skip_quality_gate),
            "skip_rehearsal_verify": bool(args.skip_rehearsal_verify),
            "offline": bool(args.offline),
            "quality_threshold": args.quality_threshold,
        }
        pipeline_policy = policy_manager.load()

        self.console.print(f"[cyan]{'=' * 60}[/cyan]")
        self.console.print("[cyan]Super Dev 完整流水线[/cyan]")
        self.console.print(f"[cyan]{'=' * 60}[/cyan]")
        self.console.print(f"[dim]项目: {project_name}[/dim]")
        self.console.print(f"[dim]请求模式: {request_mode_override}[/dim]")
        self.console.print(f"[dim]技术栈: {args.platform} | {args.frontend} | {args.backend}[/dim]")
        self.console.print("")

        from .orchestrator.contracts import PipelineContractReport
        from .orchestrator.telemetry import PipelineTelemetryReport

        telemetry = PipelineTelemetryReport(project_name=project_name)
        contract_report = PipelineContractReport(project_name=project_name)
        pipeline_started_at = time.perf_counter()
        current_stage = ""
        current_stage_title = ""
        stage_started_at = pipeline_started_at
        resume_from_stage: int | None = None
        scenario = ""
        requirements: list[dict[str, Any]] = []
        phases: list[Any] = []
        change_id = ""
        enriched_description = args.description
        scaffold_result: dict[str, list[str]] = {"frontend_files": [], "backend_files": []}
        task_execution_summary = None
        run_state = self._read_pipeline_run_state(project_dir) if resume_requested else None
        metrics_payload = self._load_pipeline_metrics_payload(
            output_dir=output_dir, project_name=project_name
        )
        run_context = self._extract_resume_context(
            run_state=run_state, metrics_payload=metrics_payload
        )

        stored_scenario = run_context.get("scenario")
        if isinstance(stored_scenario, str) and stored_scenario in {"0-1", "1-N+1"}:
            scenario = stored_scenario
        stored_requirements = run_context.get("requirements")
        requirements = self._normalize_requirements_payload(stored_requirements)
        stored_change_id = run_context.get("change_id")
        if isinstance(stored_change_id, str) and stored_change_id.strip():
            change_id = stored_change_id.strip()
        else:
            detected_change = self._detect_latest_change_id(project_dir)
            if detected_change:
                change_id = detected_change
                run_context["change_id"] = detected_change
        stored_enriched_desc = run_context.get("enriched_description")
        if isinstance(stored_enriched_desc, str) and stored_enriched_desc.strip():
            enriched_description = stored_enriched_desc

        research_file = output_dir / f"{project_name}-research.md"
        prd_file = output_dir / f"{project_name}-prd.md"
        arch_file = output_dir / f"{project_name}-architecture.md"
        uiux_file = output_dir / f"{project_name}-uiux.md"
        plan_file = output_dir / f"{project_name}-execution-plan.md"
        frontend_blueprint_file = output_dir / f"{project_name}-frontend-blueprint.md"
        resume_audit_payload: dict[str, Any] | None = None
        resume_audit_files: dict[str, Path] | None = None
        stage_output_evidence: list[str] = []
        stage_execution_state: dict[str, dict[str, Any]] = {}

        def _start_stage(stage: str, title: str) -> None:
            nonlocal current_stage, current_stage_title, stage_started_at
            current_stage = stage
            current_stage_title = title
            stage_started_at = time.perf_counter()

        def _record_stage(success: bool, details: dict[str, Any] | None = None) -> None:
            nonlocal stage_output_evidence, stage_execution_state
            if not current_stage:
                return
            normalized_details = details or {}
            stage_outputs = self._extract_stage_artifacts(normalized_details)
            stage_notes = self._extract_stage_notes(normalized_details)
            stage_execution_state[current_stage] = {
                "success": success,
                "title": current_stage_title,
                "details": normalized_details,
            }
            telemetry.record_stage(
                stage=current_stage,
                title=current_stage_title,
                success=success,
                duration_seconds=time.perf_counter() - stage_started_at,
                details=normalized_details,
            )
            contract_report.record_stage(
                stage=current_stage,
                title=current_stage_title,
                success=success,
                duration_seconds=time.perf_counter() - stage_started_at,
                inputs=list(stage_output_evidence),
                outputs=stage_outputs,
                notes=stage_notes,
            )
            stage_output_evidence = stage_outputs or stage_output_evidence

        def _write_metrics_snapshot() -> Path:
            """写入当前指标快照，供后续发布演练校验读取。"""
            snapshot_file = output_dir / f"{project_name}-pipeline-metrics.json"
            snapshot_payload = telemetry.to_dict()
            snapshot_file.write_text(
                json.dumps(snapshot_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return snapshot_file

        def _finalize_metrics(success: bool, reason: str = "") -> dict[str, Path]:
            telemetry.finalize(
                success=success,
                total_duration_seconds=time.perf_counter() - pipeline_started_at,
                failure_reason=reason,
            )
            return telemetry.write(output_dir=output_dir)

        def _finalize_contract(success: bool, reason: str = "") -> dict[str, Path]:
            contract_report.finalize(success=success, failure_reason=reason)
            return contract_report.write(output_dir=output_dir)

        def _write_contract_snapshot() -> dict[str, Path]:
            """写入当前运行中的契约快照，供发布演练等进行中校验读取。"""
            return contract_report.write(output_dir=output_dir)

        def _persist_run_state(status: str, extra: dict[str, Any] | None = None) -> None:
            payload = {
                "status": status,
                "status_normalized": self._normalize_run_status(status),
                "project_name": project_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_args": pipeline_args_snapshot,
                "context": run_context,
            }
            if extra:
                payload.update(extra)
            self._write_pipeline_run_state(project_dir, payload)

        def _update_run_context(**values: Any) -> None:
            for key, value in values.items():
                if value is None:
                    continue
                run_context[key] = value

        _update_run_context(pipeline_policy=pipeline_policy.__dict__)

        def _should_skip_for_resume(stage_num: int) -> bool:
            return resume_from_stage is not None and stage_num < resume_from_stage

        def _flush_resume_audit(status: str, failure_reason: str = "") -> None:
            nonlocal resume_audit_payload, resume_audit_files
            if not resume_audit_payload:
                return
            resume_audit_payload["status"] = status
            resume_audit_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            if failure_reason:
                resume_audit_payload["failure_reason"] = failure_reason
            resume_audit_files = self._write_resume_audit(
                output_dir=output_dir,
                project_name=project_name,
                payload=resume_audit_payload,
            )

        try:
            _persist_run_state("running")
            if resume_requested:
                run_status = (
                    str((run_state or {}).get("status", "")).strip().lower()
                    if isinstance(run_state, dict)
                    else ""
                )
                fallback_reasons: list[str] = []
                if run_status in {
                    "waiting_confirmation",
                    "waiting_preview_confirmation",
                    "waiting_ui_revision",
                    "waiting_architecture_revision",
                    "waiting_quality_revision",
                }:
                    failed_stage = None
                    resume_from_stage = None
                    if isinstance(run_state, dict):
                        resume_from_stage = self._coerce_stage_number(
                            run_state.get("resume_from_stage")
                        )
                        if resume_from_stage is None:
                            resume_from_stage = self._coerce_stage_number(
                                run_state.get("next_stage")
                            )
                    if resume_from_stage is None:
                        resume_from_stage = 2
                    initial_resume_stage = resume_from_stage
                    if run_status == "waiting_preview_confirmation":
                        self.console.print(
                            f"[cyan]恢复模式：前端预览确认已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_ui_revision":
                        self.console.print(
                            f"[cyan]恢复模式：UI 改版门已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_architecture_revision":
                        self.console.print(
                            f"[cyan]恢复模式：架构返工已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_quality_revision":
                        self.console.print(
                            f"[cyan]恢复模式：质量返工已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    else:
                        self.console.print(
                            f"[cyan]恢复模式：文档确认已完成，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                else:
                    failed_stage = None
                    if isinstance(run_state, dict):
                        failed_stage = self._coerce_stage_number(run_state.get("failed_stage"))
                    if failed_stage is None:
                        failed_stage = self._detect_failed_stage_from_metrics_payload(
                            metrics_payload
                        )
                    if failed_stage is None:
                        failed_stage = self._detect_failed_stage(
                            output_dir=output_dir, project_name=project_name
                        )

                    resume_from_stage = self._resolve_resume_start_stage(
                        failed_stage=failed_stage,
                        skip_redteam=bool(args.skip_redteam),
                    )
                    initial_resume_stage = resume_from_stage
                    adjusted_resume_stage, fallback_reasons = (
                        self._adjust_resume_stage_for_artifacts(
                            project_dir=project_dir,
                            output_dir=output_dir,
                            project_name=project_name,
                            resume_from_stage=resume_from_stage,
                        )
                    )
                    if (
                        adjusted_resume_stage != resume_from_stage
                        and adjusted_resume_stage is not None
                    ):
                        for reason in fallback_reasons:
                            self.console.print(f"[yellow]恢复校验: {reason}[/yellow]")
                        self.console.print(
                            f"[yellow]恢复起点已自动下调到第 {adjusted_resume_stage} 阶段[/yellow]"
                        )
                    resume_from_stage = adjusted_resume_stage
                    if failed_stage is None:
                        self.console.print(
                            "[yellow]未检测到可恢复的失败记录，将执行完整流水线[/yellow]"
                        )
                    elif resume_from_stage is not None:
                        self.console.print(
                            f"[cyan]恢复模式：检测到上次失败阶段 {failed_stage}，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    else:
                        self.console.print(
                            f"[yellow]上次失败发生在第 {failed_stage} 阶段，当前将执行完整流水线以确保一致性[/yellow]"
                        )
                _update_run_context(
                    resume_detected_failed_stage=failed_stage,
                    resume_from_stage=resume_from_stage,
                )
                _persist_run_state(
                    "running",
                    {
                        "failed_stage": str(failed_stage) if failed_stage is not None else "",
                        "resume_from_stage": (
                            str(resume_from_stage) if resume_from_stage is not None else ""
                        ),
                    },
                )
                resume_audit_payload = {
                    "project_name": project_name,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "finished_at": "",
                    "run_state_status": (
                        str((run_state or {}).get("status", ""))
                        if isinstance(run_state, dict)
                        else ""
                    ),
                    "detected_failed_stage": failed_stage,
                    "initial_resume_stage": initial_resume_stage,
                    "final_resume_stage": resume_from_stage,
                    "planned_skipped_stages": (
                        list(range(resume_from_stage)) if resume_from_stage is not None else []
                    ),
                    "fallback_reasons": fallback_reasons,
                }
                resume_audit_files = self._write_resume_audit(
                    output_dir=output_dir,
                    project_name=project_name,
                    payload=resume_audit_payload,
                )
                self.console.print(f"[dim]恢复审计报告: {resume_audit_files['markdown']}[/dim]")

            knowledge_dir = project_dir / "knowledge"
            knowledge_cache_file = (
                output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
            )
            knowledge_file_count = 0
            if knowledge_dir.exists():
                knowledge_file_count = sum(
                    1
                    for path in knowledge_dir.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".md", ".txt", ".yaml", ".yml"}
                )
            self.console.print(
                f"[dim]知识库扫描: knowledge 文件 {knowledge_file_count} 条 | "
                f"缓存 {'存在' if knowledge_cache_file.exists() else '不存在'}[/dim]"
            )
            _update_run_context(
                knowledge_file_count=knowledge_file_count,
                knowledge_cache_exists=knowledge_cache_file.exists(),
            )

            # 初始化 resume 跳过时可能未赋值的变量
            knowledge_bundle: dict | None = None
            cicd_files: dict[str, str] = {}
            remediation_outputs: dict = {"env_file": "", "checklist_file": "", "items_count": 0}
            migration_files: dict[str, str] = {}
            delivery_outputs: dict = {
                "manifest_file": "",
                "report_file": "",
                "archive_file": "",
                "status": "skipped",
            }
            task_execution_summary = None

            # ========== 第 0 阶段: 需求增强 ==========
            _start_stage("0", "需求增强")
            if _should_skip_for_resume(0):
                self.console.print("[yellow]第 0 阶段: 需求增强 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
                _update_run_context(enriched_description=enriched_description)
            else:
                self.console.print("[cyan]第 0 阶段: 需求增强 (联网 + 知识库)...[/cyan]")
                import os

                from .orchestrator.knowledge import KnowledgeAugmenter

                disable_web = args.offline or (
                    os.getenv("SUPER_DEV_DISABLE_WEB", "").strip().lower() in {"1", "true", "yes"}
                )
                augmenter = KnowledgeAugmenter(
                    project_dir=project_dir,
                    web_enabled=not disable_web,
                    allowed_web_domains=pipeline_config.knowledge_allowed_domains,
                    cache_ttl_seconds=pipeline_config.knowledge_cache_ttl_seconds,
                )
                knowledge_bundle = augmenter.load_cached_bundle(
                    output_dir=output_dir,
                    project_name=project_name,
                    requirement=args.description,
                    domain=args.domain or "",
                )
                cache_hit = knowledge_bundle is not None
                if knowledge_bundle is None:
                    knowledge_bundle = augmenter.augment(
                        requirement=args.description,
                        domain=args.domain or "",
                    )
                research_file = output_dir / f"{project_name}-research.md"
                research_file.write_text(augmenter.to_markdown(knowledge_bundle), encoding="utf-8")
                if cache_hit:
                    knowledge_cache_file = (
                        output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
                    )
                else:
                    knowledge_cache_file = augmenter.save_bundle(
                        bundle=knowledge_bundle,
                        output_dir=output_dir,
                        project_name=project_name,
                        requirement=args.description,
                        domain=args.domain or "",
                    )

                enriched_description = knowledge_bundle.get(
                    "enriched_requirement", args.description
                )
                self.console.print(f"  [green]✓[/green] 需求增强报告: {research_file}")
                self.console.print(f"  [green]✓[/green] 知识缓存: {knowledge_cache_file}")
                self.console.print(f"  [dim]缓存命中: {'yes' if cache_hit else 'no'}[/dim]")
                self.console.print(
                    f"  [dim]本地知识 {len(knowledge_bundle.get('local_knowledge', []))} 条 | "
                    f"联网结果 {len(knowledge_bundle.get('web_knowledge', []))} 条[/dim]"
                )
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "local_knowledge_count": len(knowledge_bundle.get("local_knowledge", [])),
                        "web_knowledge_count": len(knowledge_bundle.get("web_knowledge", [])),
                        "cache_file": str(knowledge_cache_file),
                        "cache_hit": cache_hit,
                        "knowledge_cache_ttl_seconds": pipeline_config.knowledge_cache_ttl_seconds,
                        "knowledge_allowed_domains": pipeline_config.knowledge_allowed_domains,
                        "web_filtered_out_count": (
                            (knowledge_bundle.get("metadata") or {})
                            .get("web_stats", {})
                            .get("filtered_out_count", 0)
                        ),
                    },
                )
                _update_run_context(enriched_description=enriched_description)

            # ========== 第 1 阶段: 生成文档 ==========
            _start_stage("1", "专业文档生成")
            if _should_skip_for_resume(1):
                self.console.print("[yellow]第 1 阶段: 生成专业文档 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 1 阶段: 生成专业文档...[/cyan]")
                from .creators import (
                    DocumentGenerator,
                    RequirementParser,
                )

                parser = RequirementParser()
                scenario = parser.detect_scenario(project_dir)
                request_mode = request_mode_override or parser.detect_request_mode(
                    enriched_description
                )

                doc_generator = DocumentGenerator(
                    name=project_name,
                    description=enriched_description,
                    request_mode=request_mode,
                    platform=args.platform,
                    frontend=args.frontend,
                    backend=args.backend,
                    domain=args.domain,
                    design_inspiration_slug=str(
                        getattr(pipeline_config, "design_inspiration_slug", "") or ""
                    ),
                    language_preferences=pipeline_config.language_preferences,
                    knowledge_summary=(
                        knowledge_bundle.get("research_summary", {})
                        if isinstance(knowledge_bundle, dict)
                        else {}
                    ),
                )

                # 生成文档内容
                prd_content = doc_generator.generate_prd()
                arch_content = doc_generator.generate_architecture()
                uiux_content = doc_generator.generate_uiux()

                # 写入文件
                prd_file = output_dir / f"{project_name}-prd.md"
                arch_file = output_dir / f"{project_name}-architecture.md"
                uiux_file = output_dir / f"{project_name}-uiux.md"

                prd_file.write_text(prd_content, encoding="utf-8")
                arch_file.write_text(arch_content, encoding="utf-8")
                uiux_file.write_text(uiux_content, encoding="utf-8")
                (output_dir / f"{project_name}-ui-contract.json").write_text(
                    json.dumps(doc_generator.generate_ui_contract(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                plan_file = output_dir / f"{project_name}-execution-plan.md"
                frontend_blueprint_file = output_dir / f"{project_name}-frontend-blueprint.md"
                plan_file.write_text(
                    doc_generator.generate_execution_plan(
                        scenario=scenario,
                        request_mode=request_mode,
                    ),
                    encoding="utf-8",
                )
                frontend_blueprint_file.write_text(
                    doc_generator.generate_frontend_blueprint(), encoding="utf-8"
                )

                self.console.print(f"  [green]✓[/green] PRD: {prd_file}")
                self.console.print(f"  [green]✓[/green] 架构: {arch_file}")
                self.console.print(f"  [green]✓[/green] UI/UX: {uiux_file}")
                self.console.print(f"  [green]✓[/green] 执行路线图: {plan_file}")
                self.console.print(f"  [green]✓[/green] 前端蓝图: {frontend_blueprint_file}")
                self.console.print(f"  [dim]场景识别: {scenario}[/dim]")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "scenario": scenario,
                        "docs": [
                            str(prd_file),
                            str(arch_file),
                            str(uiux_file),
                            str(plan_file),
                            str(frontend_blueprint_file),
                        ],
                    },
                )

                # 保存技术栈到配置文件（供后续阶段使用）
                self._save_tech_stack_to_config(project_dir, tech_stack, args.description)

                requirements = self._normalize_requirements_payload(
                    doc_generator.extract_requirements()
                )
                phases = parser.build_execution_phases(
                    scenario, requirements, request_mode=request_mode
                )
                _update_run_context(
                    scenario=scenario,
                    request_mode=request_mode,
                    requirements=requirements,
                )

            docs_confirmation = self._get_docs_confirmation_state(project_dir)
            _update_run_context(docs_confirmation=docs_confirmation)
            if not self._docs_confirmation_is_confirmed(project_dir):
                waiting_reason = (
                    "revision_requested"
                    if docs_confirmation["status"] == "revision_requested"
                    else "pending_review"
                )
                self.console.print("[yellow]已完成 research 与三文档，当前进入文档确认门[/yellow]")
                self.console.print(f"  [dim]研究报告: {research_file}[/dim]")
                self.console.print(f"  [dim]PRD: {prd_file}[/dim]")
                self.console.print(f"  [dim]架构: {arch_file}[/dim]")
                self.console.print(f"  [dim]UI/UX: {uiux_file}[/dim]")
                if docs_confirmation["status"] == "revision_requested":
                    self.console.print(
                        "[yellow]当前状态: 用户已要求修改文档，请先修正文档并再次确认。[/yellow]"
                    )
                else:
                    self.console.print(
                        "[yellow]当前状态: 待用户确认三文档，确认前不会创建 Spec 或开始编码。[/yellow]"
                    )
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print(
                    "  1. 在宿主中查看并修订 output/*-prd.md / *-architecture.md / *-uiux.md"
                )
                self.console.print("  2. 在宿主中明确回复：“文档确认，可以继续”")
                self.console.print("  3. 继续留在当前 Super Dev 流程内，不要切回普通聊天")
                metric_files = _finalize_metrics(success=False, reason="waiting_confirmation")
                contract_files = _finalize_contract(success=False, reason="waiting_confirmation")
                _persist_run_state(
                    "waiting_confirmation",
                    {
                        "failure_reason": waiting_reason,
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(status="waiting_confirmation", failure_reason=waiting_reason)
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            ui_revision = self._get_ui_revision_state(project_dir)
            _update_run_context(ui_revision=ui_revision)
            if ui_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在 UI 改版请求，必须先完成 UI 返工后才能继续[/yellow]"
                )
                if ui_revision["comment"]:
                    self.console.print(f"  [dim]备注: {ui_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先更新 output/*-uiux.md")
                self.console.print("  2. 重做前端并重新执行 frontend runtime 与 UI review")
                self.console.print("  3. 在宿主中明确回复：“UI 改版已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(success=False, reason="waiting_ui_revision")
                contract_files = _finalize_contract(success=False, reason="waiting_ui_revision")
                _persist_run_state(
                    "waiting_ui_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_ui_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            architecture_revision = self._get_architecture_revision_state(project_dir)
            _update_run_context(architecture_revision=architecture_revision)
            if architecture_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在架构返工请求，必须先完成架构方案修订后才能继续[/yellow]"
                )
                if architecture_revision["comment"]:
                    self.console.print(f"  [dim]备注: {architecture_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先更新 output/*-architecture.md")
                self.console.print("  2. 同步调整任务拆解与相关实现方案")
                self.console.print("  3. 在宿主中明确回复：“架构调整已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(
                    success=False, reason="waiting_architecture_revision"
                )
                contract_files = _finalize_contract(
                    success=False, reason="waiting_architecture_revision"
                )
                _persist_run_state(
                    "waiting_architecture_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_architecture_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            quality_revision = self._get_quality_revision_state(project_dir)
            _update_run_context(quality_revision=quality_revision)
            if quality_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在质量返工请求，必须先修复质量/安全问题后才能继续[/yellow]"
                )
                if quality_revision["comment"]:
                    self.console.print(f"  [dim]备注: {quality_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先修复质量门禁或安全问题")
                self.console.print("  2. 重新执行 quality gate，并刷新 proof-pack / readiness 等交付证据")
                self.console.print("  3. 在宿主中明确回复：“质量整改已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(success=False, reason="waiting_quality_revision")
                contract_files = _finalize_contract(
                    success=False, reason="waiting_quality_revision"
                )
                _persist_run_state(
                    "waiting_quality_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_quality_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            # ========== 第 2 阶段: 创建 Spec ==========
            _start_stage("2", "Spec 创建")
            if _should_skip_for_resume(2):
                self.console.print("[yellow]第 2 阶段: 创建 Spec 规范 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 2 阶段: 创建 Spec 规范...[/cyan]")
                from .creators import SpecBuilder

                spec_builder = SpecBuilder(
                    project_dir=project_dir, name=project_name, description=args.description
                )

                change_id = spec_builder.create_change(requirements, tech_stack, scenario=scenario)

                self.console.print(f"  [green]✓[/green] 变更 ID: {change_id}")
                self.console.print(f"  [green]✓[/green] Spec: .super-dev/changes/{change_id}/")
                self.console.print("")
                _record_stage(True, details={"change_id": change_id})
                _update_run_context(change_id=change_id)

            # ========== 第 3 阶段: 生成前端实施蓝图 ==========
            _start_stage("3", "前端实施蓝图与预览")
            if _should_skip_for_resume(3):
                self.console.print("[yellow]第 3 阶段: 生成前端实施蓝图与预览 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 3 阶段: 生成前端实施蓝图与预览...[/cyan]")
                from .creators import FrontendScaffoldBuilder

                frontend_builder = FrontendScaffoldBuilder(
                    project_dir=project_dir,
                    name=project_name,
                    description=args.description,
                    frontend=args.frontend,
                )
                frontend_files = frontend_builder.generate(
                    requirements=requirements,
                    phases=phases,
                    docs={
                        "prd": str(prd_file),
                        "architecture": str(arch_file),
                        "uiux": str(uiux_file),
                        "plan": str(plan_file),
                        "frontend_blueprint": str(frontend_blueprint_file),
                    },
                )
                self.console.print(f"  [green]✓[/green] 页面: {frontend_files['html']}")
                self.console.print(f"  [green]✓[/green] 样式: {frontend_files['css']}")
                self.console.print(f"  [green]✓[/green] 脚本: {frontend_files['js']}")
                frontend_runtime = self._write_frontend_runtime_validation(
                    project_dir=project_dir,
                    output_dir=output_dir,
                    project_name=project_name,
                )
                self.console.print(
                    f"  [green]✓[/green] 前端运行验证: {frontend_runtime['report_files']['markdown']}"
                )
                if frontend_runtime["preview_file"]:
                    self.console.print(
                        f"  [green]✓[/green] 预览页: {frontend_runtime['preview_file']}"
                    )
                if not frontend_runtime["passed"]:
                    raise RuntimeError("前端运行验证未通过，当前不得进入后端与交付阶段")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "files": frontend_files,
                        "frontend_runtime_report": frontend_runtime["report_files"]["json"],
                        "preview_file": frontend_runtime["preview_file"],
                    },
                )

            preview_confirmation = self._get_preview_confirmation_state(project_dir)
            _update_run_context(preview_confirmation=preview_confirmation)
            if not self._preview_confirmation_is_confirmed(project_dir):
                waiting_reason = (
                    "revision_requested"
                    if preview_confirmation["status"] == "revision_requested"
                    else "pending_review"
                )
                self.console.print("[yellow]已完成前端实施蓝图与预览，当前进入前端预览确认门[/yellow]")
                self.console.print(
                    f"  [dim]前端运行验证: {output_dir / f'{project_name}-frontend-runtime.md'}[/dim]"
                )
                preview_file = output_dir.parent / "preview.html"
                if preview_file.exists():
                    self.console.print(f"  [dim]预览页: {preview_file}[/dim]")
                if preview_confirmation["status"] == "revision_requested":
                    self.console.print(
                        "[yellow]当前状态: 用户已要求继续调整前端，请先完成预览返工并再次确认。[/yellow]"
                    )
                else:
                    self.console.print(
                        "[yellow]当前状态: 待用户确认前端预览，确认前不会进入后端、联调、质量与交付阶段。[/yellow]"
                    )
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 在宿主中查看并修订当前前端预览")
                self.console.print("  2. 在宿主中明确回复：“前端预览确认，可以继续”")
                self.console.print("  3. 继续留在当前 Super Dev 流程内，不要切回普通聊天")
                metric_files = _finalize_metrics(
                    success=False, reason="waiting_preview_confirmation"
                )
                contract_files = _finalize_contract(
                    success=False, reason="waiting_preview_confirmation"
                )
                _persist_run_state(
                    "waiting_preview_confirmation",
                    {
                        "failure_reason": waiting_reason,
                        "failed_stage": "4",
                        "next_stage": "4",
                        "resume_from_stage": "4",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_preview_confirmation", failure_reason=waiting_reason
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            # ========== 第 4 阶段: 生成宿主实现参考 ==========
            _start_stage("4", "宿主实现参考与任务执行")
            if _should_skip_for_resume(4):
                self.console.print("[yellow]第 4 阶段: 生成宿主实现参考 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                if not args.skip_scaffold:
                    self.console.print("[cyan]第 4 阶段: 生成宿主实现参考...[/cyan]")
                    from .creators import ImplementationScaffoldBuilder, SpecTaskExecutor

                    frontend_runtime = self._load_frontend_runtime_validation(
                        output_dir=output_dir,
                        project_name=project_name,
                    )
                    if not frontend_runtime.get("passed", False):
                        raise RuntimeError("前端运行验证未通过，禁止进入宿主实现参考与后端阶段")

                    implementation_builder = ImplementationScaffoldBuilder(
                        project_dir=project_dir,
                        name=project_name,
                        frontend=args.frontend,
                        backend=args.backend,
                    )
                    scaffold_result = implementation_builder.generate(requirements=requirements)
                    self.console.print(
                        f"  [green]✓[/green] 前端参考文件: {len(scaffold_result['frontend_files'])} 个"
                    )
                    self.console.print(
                        f"  [green]✓[/green] 后端参考文件: {len(scaffold_result['backend_files'])} 个"
                    )
                    task_executor = SpecTaskExecutor(
                        project_dir=project_dir, project_name=project_name
                    )
                    task_execution_summary = task_executor.execute(
                        change_id=change_id,
                        tech_stack=tech_stack,
                        max_retries=1,
                    )
                    self.console.print(
                        f"  [green]✓[/green] Spec 任务执行: {task_execution_summary.completed_tasks}/{task_execution_summary.total_tasks}"
                    )
                    self.console.print(
                        f"  [green]✓[/green] 任务报告: {task_execution_summary.report_file}"
                    )
                    if task_execution_summary.failed_tasks:
                        self.console.print(
                            f"  [yellow]未完成任务: {', '.join(task_execution_summary.failed_tasks)}[/yellow]"
                        )
                    if task_execution_summary.repaired_actions:
                        self.console.print(
                            f"  [dim]自动修复: {len(task_execution_summary.repaired_actions)} 项[/dim]"
                        )
                    self.console.print("")
                    _record_stage(
                        True,
                        details={
                            "frontend_files": len(scaffold_result["frontend_files"]),
                            "backend_files": len(scaffold_result["backend_files"]),
                            "frontend_runtime_report": str(
                                self._frontend_runtime_report_paths(
                                    output_dir=output_dir, project_name=project_name
                                )["json"]
                            ),
                            "task_completed": (
                                f"{task_execution_summary.completed_tasks}/{task_execution_summary.total_tasks}"
                                if task_execution_summary is not None
                                else "0/0"
                            ),
                            "task_failed_count": (
                                len(task_execution_summary.failed_tasks)
                                if task_execution_summary is not None
                                else 0
                            ),
                        },
                    )
                else:
                    self.console.print("[yellow]第 4 阶段: 生成宿主实现参考 (跳过)[/yellow]")
                    self.console.print("")
                    _record_stage(True, details={"skipped": True})

            # ========== 第 5 阶段: 红队审查 ==========
            _start_stage("5", "红队审查")
            redteam_report = None
            if _should_skip_for_resume(5):
                self.console.print("[yellow]第 5 阶段: 红队审查 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            elif not args.skip_redteam:
                self.console.print("[cyan]第 5 阶段: 红队审查...[/cyan]")
                from .reviewers import RedTeamReviewer

                reviewer = RedTeamReviewer(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )
                redteam_report = reviewer.review()

                # 保存红队审查报告
                redteam_file = project_dir / "output" / f"{project_name}-redteam.md"
                redteam_json_file = project_dir / "output" / f"{project_name}-redteam.json"
                redteam_file.parent.mkdir(parents=True, exist_ok=True)
                redteam_file.write_text(redteam_report.to_markdown(), encoding="utf-8")
                redteam_json_file.write_text(
                    json.dumps(redteam_report.to_dict(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                self.console.print(
                    f"  [green]✓[/green] 安全问题: {sum(1 for i in redteam_report.security_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(
                    f"  [green]✓[/green] 性能问题: {sum(1 for i in redteam_report.performance_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(
                    f"  [green]✓[/green] 架构问题: {sum(1 for i in redteam_report.architecture_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(f"  [green]✓[/green] 总分: {redteam_report.total_score}/100")
                self.console.print(f"  [green]✓[/green] 报告: {redteam_file}")
                self.console.print(f"  [green]✓[/green] JSON: {redteam_json_file}")
                self.console.print("")

                # 红队未通过时直接阻断，确保“先通过红队，再进入质量门禁”
                if not redteam_report.passed:
                    _record_stage(
                        False,
                        details={
                            "score": redteam_report.total_score,
                            "blocking_reasons": redteam_report.blocking_reasons,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False,
                        reason="redteam_failed",
                    )
                    contract_files = _finalize_contract(success=False, reason="redteam_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "redteam_failed",
                            "failed_stage": "5",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="redteam_failed")
                    self.console.print("[red]红队审查未通过，流水线终止[/red]")
                    for reason in redteam_report.blocking_reasons:
                        self.console.print(f"  - {reason}")
                    self.console.print(
                        "[dim]可使用 --skip-redteam 跳过该阶段（不推荐生产使用）[/dim]"
                    )
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                _record_stage(
                    True,
                    details={
                        "score": redteam_report.total_score,
                        "critical_count": redteam_report.critical_count,
                        "high_count": redteam_report.high_count,
                    },
                )
            else:
                self.console.print("[yellow]第 5 阶段: 红队审查 (跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True})

            # ========== 第 6 阶段: 质量门禁 ==========
            _start_stage("6", "质量门禁")
            if _should_skip_for_resume(6):
                self.console.print("[yellow]第 6 阶段: 质量门禁检查 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            elif not args.skip_quality_gate:
                self.console.print("[cyan]第 6 阶段: 质量门禁检查...[/cyan]")
                from .reviewers import QualityGateChecker

                gate_checker = QualityGateChecker(
                    project_dir=project_dir,
                    name=project_name,
                    tech_stack=tech_stack,
                    scenario_override=scenario,
                    threshold_override=args.quality_threshold,
                    host_compatibility_min_score_override=pipeline_config.host_compatibility_min_score,
                    host_compatibility_min_ready_hosts_override=pipeline_config.host_compatibility_min_ready_hosts,
                )

                gate_result = gate_checker.check(redteam_report)

                # 显示场景信息
                scenario_label = (
                    "0-1 新建项目" if gate_result.scenario == "0-1" else "1-N+1 增量开发"
                )
                self.console.print(f"  [dim]场景: {scenario_label}[/dim]")

                # 保存质量门禁报告
                gate_file = project_dir / "output" / f"{project_name}-quality-gate.md"
                gate_file.parent.mkdir(parents=True, exist_ok=True)
                if gate_checker.latest_ui_review_report is not None:
                    ui_review_file = project_dir / "output" / f"{project_name}-ui-review.md"
                    ui_review_json_file = project_dir / "output" / f"{project_name}-ui-review.json"
                    alignment_file = (
                        project_dir / "output" / f"{project_name}-ui-contract-alignment.md"
                    )
                    alignment_json_file = (
                        project_dir / "output" / f"{project_name}-ui-contract-alignment.json"
                    )
                    ui_review_file.write_text(
                        gate_checker.latest_ui_review_report.to_markdown(),
                        encoding="utf-8",
                    )
                    ui_review_json_file.write_text(
                        json.dumps(
                            attach_evidence_identity(
                                gate_checker.latest_ui_review_report.to_dict(),
                                project_dir=project_dir,
                                artifact_name="ui-review",
                                dependencies=[
                                    project_dir / "output" / f"{project_name}-ui-contract.json",
                                    project_dir / "output" / f"{project_name}-uiux.md",
                                ],
                            ),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    alignment_file.write_text(
                        gate_checker.latest_ui_review_report.alignment_markdown(),
                        encoding="utf-8",
                    )
                    alignment_json_file.write_text(
                        json.dumps(
                            attach_evidence_identity(
                                gate_checker.latest_ui_review_report.alignment_summary,
                                project_dir=project_dir,
                                artifact_name="ui-contract-alignment",
                                dependencies=[
                                    project_dir / "output" / f"{project_name}-ui-contract.json",
                                    project_dir / "output" / f"{project_name}-uiux.md",
                                ],
                            ),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    frontend_index = output_dir / "frontend" / "index.html"
                    if frontend_index.exists():
                        frontend_runtime = self._write_frontend_runtime_validation(
                            project_dir=project_dir,
                            output_dir=output_dir,
                            project_name=project_name,
                        )
                gate_result = gate_checker.check(redteam_report)
                gate_file.write_text(gate_result.to_markdown(), encoding="utf-8")
                gate_json_file = project_dir / "output" / f"{project_name}-quality-gate.json"
                gate_json_file.write_text(
                    json.dumps(
                        attach_evidence_identity(
                            gate_result.to_dict(),
                            project_dir=project_dir,
                            artifact_name="quality-gate",
                            dependencies=[
                                project_dir / "output" / f"{project_name}-ui-review.json",
                                project_dir
                                / "output"
                                / f"{project_name}-ui-contract-alignment.json",
                                project_dir / "output" / f"{project_name}-uiux.md",
                            ],
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                status = "[green]通过[/green]" if gate_result.passed else "[red]未通过[/red]"
                self.console.print(f"  {status} 总分: {gate_result.total_score}/100")
                self.console.print(f"  [dim]{gate_result.executive_summary}[/dim]")
                self.console.print(f"  [green]✓[/green] 报告: {gate_file}")
                if gate_checker.latest_ui_review_report is not None:
                    self.console.print(f"  [green]✓[/green] UI 审查: {ui_review_file}")
                    self.console.print(f"  [green]✓[/green] UI 审查 JSON: {ui_review_json_file}")
                    self.console.print(f"  [green]✓[/green] UI 契约对齐: {alignment_file}")
                self.console.print("")

                # 质量门禁未通过，停止流水线
                if not gate_result.passed:
                    _record_stage(
                        False,
                        details={
                            "score": gate_result.total_score,
                            "critical_failures": gate_result.critical_failures,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False,
                        reason="quality_gate_failed",
                    )
                    contract_files = _finalize_contract(success=False, reason="quality_gate_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "quality_gate_failed",
                            "failed_stage": "6",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="quality_gate_failed")
                    self.console.print("[red]质量门禁未通过，流水线终止[/red]")
                    self.console.print("[cyan]请修复以下问题后重新运行:[/cyan]")
                    for failure in gate_result.critical_failures:
                        self.console.print(f"  - {failure}")
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                _record_stage(
                    True,
                    details={
                        "score": gate_result.total_score,
                        "scenario": gate_result.scenario,
                    },
                )
            else:
                self.console.print("[yellow]第 6 阶段: 质量门禁检查 (跳过)[/yellow]")
                self.console.print(
                    "[dim]提示: 使用 --skip-quality-gate 跳过了质量门禁检查，建议后续补充测试和质量检查[/dim]"
                )
                self.console.print("")
                _record_stage(True, details={"skipped": True})

            # ========== 第 7 阶段: 代码审查指南 ==========
            _start_stage("7", "代码审查指南")
            if _should_skip_for_resume(7):
                self.console.print("[yellow]第 7 阶段: 代码审查指南 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 7 阶段: 生成代码审查指南...[/cyan]")
                from .reviewers import CodeReviewGenerator

                review_gen = CodeReviewGenerator(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )

                review_guide = review_gen.generate()
                review_file = project_dir / "output" / f"{project_name}-code-review.md"
                review_file.write_text(review_guide, encoding="utf-8")

                self.console.print(f"  [green]✓[/green] 代码审查指南: {review_file}")
                self.console.print("")
                _record_stage(True, details={"report": str(review_file)})

            # ========== 第 8 阶段: AI 提示词 ==========
            _start_stage("8", "AI 提示词")
            if _should_skip_for_resume(8):
                self.console.print("[yellow]第 8 阶段: AI 提示词 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 8 阶段: 生成 AI 提示词...[/cyan]")
                from .creators import AIPromptGenerator

                prompt_gen = AIPromptGenerator(project_dir=project_dir, name=project_name)

                prompt_content = prompt_gen.generate()
                prompt_file = project_dir / "output" / f"{project_name}-ai-prompt.md"
                prompt_file.write_text(prompt_content, encoding="utf-8")

                self.console.print(f"  [green]✓[/green] AI 提示词: {prompt_file}")
                self.console.print("")
                _record_stage(True, details={"prompt_file": str(prompt_file)})

            # ========== 第 9 阶段: CI/CD 配置 ==========
            _start_stage("9", "CI/CD 配置")
            if _should_skip_for_resume(9):
                self.console.print("[yellow]第 9 阶段: CI/CD 配置 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print(
                    f"[cyan]第 9 阶段: 生成 CI/CD 配置 ({args.cicd.upper()})...[/cyan]"
                )
                from .deployers import CICDGenerator

                cicd_gen = CICDGenerator(
                    project_dir=project_dir,
                    name=project_name,
                    tech_stack=tech_stack,
                    platform=self._normalize_cicd_platform(args.cicd),
                )

                cicd_files = cicd_gen.generate()

                for file_path, content in cicd_files.items():
                    full_path = project_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    self.console.print(f"  [green]✓[/green] {file_path}")

                self.console.print("")
                _record_stage(True, details={"generated_files": len(cicd_files)})

            # ========== 第 10 阶段: 部署修复模板 ==========
            _start_stage("10", "部署修复模板")
            if _should_skip_for_resume(10):
                self.console.print("[yellow]第 10 阶段: 部署修复模板 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 10 阶段: 生成部署修复模板...[/cyan]")
                remediation_outputs = self._export_deploy_remediation_templates(
                    project_dir=project_dir,
                    cicd_platform=args.cicd,
                    only_missing=True,
                )
                self.console.print(
                    f"  [green]✓[/green] 环境模板: {remediation_outputs['env_file']}"
                )
                self.console.print(
                    f"  [green]✓[/green] 检查清单: {remediation_outputs['checklist_file']}"
                )
                self.console.print(
                    f"  [dim]缺失变量条目: {remediation_outputs['items_count']}[/dim]"
                )
                if remediation_outputs.get("per_platform_files"):
                    self.console.print(
                        f"  [green]✓[/green] 平台拆分模板: {len(remediation_outputs['per_platform_files'])} 组"
                    )
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "items_count": remediation_outputs["items_count"],
                        "per_platform_groups": len(
                            remediation_outputs.get("per_platform_files") or []
                        ),
                    },
                )

            # ========== 第 11 阶段: 数据库迁移 + 项目交付包 ==========
            _start_stage("11", "迁移与交付")
            if _should_skip_for_resume(11):
                self.console.print("[yellow]第 11 阶段: 迁移与交付 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 11 阶段: 生成数据库迁移脚本 + 项目交付包...[/cyan]")
                from .deployers import DeliveryPackager, MigrationGenerator

                migration_gen = MigrationGenerator(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )

                migration_files = migration_gen.generate()

                for file_path, content in migration_files.items():
                    full_path = project_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    self.console.print(f"  [green]✓[/green] {file_path}")

                packager = DeliveryPackager(
                    project_dir=project_dir,
                    name=project_name,
                    version=__version__,
                )
                delivery_outputs = packager.package(cicd_platform=args.cicd)
                missing_required_raw = delivery_outputs.get("missing_required_count", 0)
                missing_required_count = (
                    missing_required_raw if isinstance(missing_required_raw, int) else 0
                )
                self.console.print(f"  [green]✓[/green] 清单: {delivery_outputs['manifest_file']}")
                self.console.print(f"  [green]✓[/green] 报告: {delivery_outputs['report_file']}")
                self.console.print(f"  [green]✓[/green] 交付包: {delivery_outputs['archive_file']}")
                self.console.print(
                    f"  [dim]状态: {delivery_outputs['status']} | 缺失必需项: {missing_required_count}[/dim]"
                )
                if missing_required_count > 0:
                    self.console.print(
                        "[red]  交付包标记为 incomplete，当前不得进入发布演练验证[/red]"
                    )
                    _record_stage(
                        False,
                        details={
                            "migration_files": len(migration_files),
                            "delivery_status": delivery_outputs["status"],
                            "delivery_missing_required_count": missing_required_count,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False, reason="delivery_packaging_incomplete"
                    )
                    contract_files = _finalize_contract(
                        success=False, reason="delivery_packaging_incomplete"
                    )
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "delivery_packaging_incomplete",
                            "failed_stage": "11",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(
                        status="failed", failure_reason="delivery_packaging_incomplete"
                    )
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "migration_files": len(migration_files),
                        "delivery_status": delivery_outputs["status"],
                        "delivery_missing_required_count": missing_required_count,
                    },
                )

            # ========== 第 12 阶段: 发布演练验证 ==========
            _start_stage("12", "发布演练验证")
            self.console.print("[cyan]第 12 阶段: 发布演练文档与验证...[/cyan]")
            from .deployers import LaunchRehearsalGenerator, LaunchRehearsalRunner

            rehearsal_generator = LaunchRehearsalGenerator(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            rehearsal_files = rehearsal_generator.generate(cicd_platform=args.cicd or "github")
            for relative_path, content in rehearsal_files.items():
                full_path = project_dir / relative_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                self.console.print(f"  [green]✓[/green] {relative_path}")

            if args.skip_rehearsal_verify:
                self.console.print("[yellow]发布演练验证已跳过（--skip-rehearsal-verify）[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "skip-rehearsal-verify"})
            elif args.skip_redteam or args.skip_quality_gate:
                self.console.print("[yellow]检测到上游门禁被跳过，发布演练验证自动跳过[/yellow]")
                self.console.print("[dim]提示: 建议在不跳过红队/质量门禁时执行完整发布演练[/dim]")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "skipped": True,
                        "reason": "prerequisite_skipped",
                        "skip_redteam": bool(args.skip_redteam),
                        "skip_quality_gate": bool(args.skip_quality_gate),
                    },
                )
            else:
                metrics_snapshot_file = _write_metrics_snapshot()
                _write_contract_snapshot()
                runner = LaunchRehearsalRunner(
                    project_dir=project_dir,
                    project_name=project_name,
                    cicd_platform=args.cicd or "github",
                )
                rehearsal_result = runner.run()
                rehearsal_reports = runner.write(rehearsal_result)
                status = "[green]通过[/green]" if rehearsal_result.passed else "[red]未通过[/red]"
                self.console.print(f"  {status} 分数: {rehearsal_result.score}/100")
                self.console.print(f"  [green]✓[/green] 报告: {rehearsal_reports['markdown']}")
                self.console.print(f"  [green]✓[/green] 数据: {rehearsal_reports['json']}")
                self.console.print(f"  [dim]指标快照: {metrics_snapshot_file}[/dim]")
                self.console.print("")

                if not rehearsal_result.passed:
                    _record_stage(
                        False,
                        details={
                            "score": rehearsal_result.score,
                            "failed_checks": [
                                check.name for check in rehearsal_result.failed_checks
                            ],
                        },
                    )
                    metric_files = _finalize_metrics(success=False, reason="rehearsal_failed")
                    contract_files = _finalize_contract(success=False, reason="rehearsal_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "rehearsal_failed",
                            "failed_stage": "12",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="rehearsal_failed")
                    self.console.print("[red]发布演练验证未通过，流水线终止[/red]")
                    for check in rehearsal_result.failed_checks:
                        self.console.print(f"  - {check.name}: {check.detail}")
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1

                _record_stage(
                    True,
                    details={
                        "score": rehearsal_result.score,
                        "failed_checks": len(rehearsal_result.failed_checks),
                    },
                )

            metric_files = _finalize_metrics(success=True)
            contract_files = _finalize_contract(success=True)
            from .analyzer import FeatureChecklistBuilder

            feature_checklist_builder = FeatureChecklistBuilder(project_dir)
            feature_coverage_report = feature_checklist_builder.build()
            feature_checklist_files = feature_checklist_builder.write(feature_coverage_report)
            gate_stage_ids = ("5", "6", "12")
            skipped_gates = [
                stage_execution_state[stage]["title"]
                for stage in gate_stage_ids
                if bool(
                    stage_execution_state.get(stage, {}).get("details", {}).get("skipped", False)
                )
            ]
            full_gate_passed = not skipped_gates
            scope_fully_implemented = feature_coverage_report.status == "ready"
            scope_has_high_priority_gap = feature_coverage_report.high_priority_gap_count > 0
            if full_gate_passed and scope_fully_implemented:
                completion_title = "流程完成（全门禁通过，范围完成）"
                completion_style = "green"
            elif full_gate_passed:
                completion_title = "流程完成（全门禁通过，范围存在缺口）"
                completion_style = "yellow"
            else:
                completion_title = "流程完成（存在跳过门禁）"
                completion_style = "yellow"

            # ========== 完成 ==========
            self.console.print(f"[cyan]{'=' * 60}[/cyan]")
            self.console.print(f"[{completion_style}]✓ {completion_title}[/{completion_style}]")
            self.console.print(f"[cyan]{'=' * 60}[/cyan]")
            self.console.print("")
            if full_gate_passed:
                if scope_fully_implemented:
                    self.console.print(
                        "[green]交付状态: 当前运行已完成，且红队 / 质量 / 演练门禁均已通过，当前范围覆盖率未发现显式缺口。[/green]"
                    )
                else:
                    self.console.print(
                        "[yellow]交付状态: 当前运行已完成，且门禁已通过；但这不等于 PRD 全量范围已实现完成。[/yellow]"
                    )
            else:
                self.console.print(
                    "[yellow]交付状态: 当前运行已完成，但存在跳过门禁；这不等于严格意义上的“全部通过”。[/yellow]"
                )
                self.console.print(f"[yellow]已跳过门禁: {', '.join(skipped_gates)}[/yellow]")
            coverage_text = (
                f"{feature_coverage_report.coverage_rate:.1f}%"
                if feature_coverage_report.coverage_rate is not None
                else "unknown"
            )
            self.console.print(
                f"[cyan]范围覆盖率:[/cyan] {coverage_text} | 状态: {feature_coverage_report.status} | "
                f"高优先级缺口: {feature_coverage_report.high_priority_gap_count}"
            )
            if not scope_fully_implemented or scope_has_high_priority_gap:
                self.console.print(f"[yellow]{feature_coverage_report.summary}[/yellow]")
            self.console.print("")
            self.console.print("[cyan]生成的文件:[/cyan]")
            self.console.print("  文档:")
            self.console.print(f"    - 需求增强报告: output/{project_name}-research.md")
            self.console.print(f"    - PRD: output/{project_name}-prd.md")
            self.console.print(f"    - 架构: output/{project_name}-architecture.md")
            self.console.print(f"    - UI/UX: output/{project_name}-uiux.md")
            self.console.print(f"    - 执行路线图: output/{project_name}-execution-plan.md")
            self.console.print(f"    - 前端蓝图: output/{project_name}-frontend-blueprint.md")
            if not args.skip_redteam:
                self.console.print(f"    - 红队审查: output/{project_name}-redteam.md")
            if not args.skip_quality_gate:
                self.console.print(f"    - 质量门禁: output/{project_name}-quality-gate.md")
            self.console.print(f"    - 代码审查: output/{project_name}-code-review.md")
            self.console.print(f"    - AI 提示词: output/{project_name}-ai-prompt.md")
            self.console.print("")
            self.console.print("  前端演示:")
            self.console.print("    - output/frontend/index.html")
            self.console.print("    - output/frontend/styles.css")
            self.console.print("    - output/frontend/app.js")
            self.console.print("")
            if not args.skip_scaffold:
                self.console.print("  宿主实现参考:")
                self.console.print("    - frontend/src/*")
                self.console.print("    - backend/src/*")
                self.console.print("    - backend/API_CONTRACT.md")
                self.console.print("    - backend/migrations/*.sql")
                if task_execution_summary is not None and task_execution_summary.report_file:
                    try:
                        rel = Path(str(task_execution_summary.report_file)).relative_to(project_dir)
                    except ValueError:
                        rel = Path(str(task_execution_summary.report_file)).name
                    self.console.print(f"    - {rel}")
                self.console.print("")
            self.console.print("  CI/CD:")
            for file_path in cicd_files.keys():
                self.console.print(f"    - {file_path}")
            self.console.print("")
            if remediation_outputs.get("env_file"):
                self.console.print("  部署修复模板:")
                self.console.print(f"    - {Path(remediation_outputs['env_file']).name}")
                if remediation_outputs.get("checklist_file"):
                    try:
                        self.console.print(
                            f"    - {Path(remediation_outputs['checklist_file']).relative_to(project_dir)}"
                        )
                    except ValueError:
                        self.console.print(
                            f"    - {Path(remediation_outputs['checklist_file']).name}"
                        )
            per_platform_files = remediation_outputs.get("per_platform_files")
            if isinstance(per_platform_files, list):
                for item in per_platform_files:
                    if not isinstance(item, dict):
                        continue
                    checklist_file = item.get("checklist_file")
                    if isinstance(checklist_file, str):
                        self.console.print(f"    - {Path(checklist_file).relative_to(project_dir)}")
                    env_file = item.get("env_file")
                    if isinstance(env_file, str):
                        self.console.print(f"    - {Path(env_file).relative_to(project_dir)}")
            self.console.print("")
            self.console.print("  数据库迁移:")
            for file_path in migration_files.keys():
                self.console.print(f"    - {file_path}")
            self.console.print("")
            self.console.print("  范围覆盖审计:")
            self.console.print(
                f"    - {Path(str(feature_checklist_files['markdown'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(feature_checklist_files['json'])).relative_to(project_dir)}"
            )
            self.console.print("")
            self.console.print("  项目交付包:")
            self.console.print(
                f"    - {Path(str(delivery_outputs['manifest_file'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(delivery_outputs['report_file'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(delivery_outputs['archive_file'])).relative_to(project_dir)}"
            )
            self.console.print("")
            self.console.print("  发布演练:")
            self.console.print(f"    - output/rehearsal/{project_name}-launch-rehearsal.md")
            self.console.print(f"    - output/rehearsal/{project_name}-rollback-playbook.md")
            self.console.print(f"    - output/rehearsal/{project_name}-smoke-checklist.md")
            if (
                not args.skip_rehearsal_verify
                and not args.skip_redteam
                and not args.skip_quality_gate
            ):
                self.console.print(f"    - output/rehearsal/{project_name}-rehearsal-report.md")
                self.console.print(f"    - output/rehearsal/{project_name}-rehearsal-report.json")
            self.console.print("")
            self.console.print("[cyan]下一步:[/cyan]")
            self.console.print("  1. 打开 output/frontend/index.html 评审前端实施蓝图")
            self.console.print("  2. 对照执行路线图按阶段推进开发")
            self.console.print("  3. 使用代码审查指南进行评审和修复")
            self.console.print("  4. 配置 CI/CD 平台 (设置 secrets/credentials)")
            self.console.print("  5. 运行数据库迁移脚本并推送代码触发流水线")
            self.console.print("  6. 执行并保存发布演练报告用于上线审批")
            self.console.print("  7. 使用 output/delivery/* 作为对外交付包")
            self.console.print(
                f"  8. 查看 pipeline 指标: output/{project_name}-pipeline-metrics.md"
            )
            if not full_gate_passed:
                self.console.print(
                    "  9. 若要获得严格意义上的全门禁通过，请重新执行被跳过的红队 / 质量 / 演练阶段"
                )
            elif not scope_fully_implemented:
                self.console.print(
                    "  9. 若要确认 PRD 范围是否真正实现完成，请查看 feature checklist 并补齐高优先级缺口"
                )
            self.console.print("")
            self.console.print("[cyan]可观测性:[/cyan]")
            self.console.print(f"  - 指标 JSON: {metric_files['json']}")
            self.console.print(f"  - 指标 Markdown: {metric_files['markdown']}")
            self.console.print(f"  - 契约 JSON: {contract_files['json']}")
            self.console.print(f"  - 契约 Markdown: {contract_files['markdown']}")
            if "history_json" in metric_files:
                self.console.print(f"  - 历史 JSON: {metric_files['history_json']}")
            if "history_markdown" in metric_files:
                self.console.print(f"  - 历史 Markdown: {metric_files['history_markdown']}")
            self.console.print("")
            _persist_run_state(
                "success",
                {
                    "metrics_file": str(metric_files["json"]),
                    "contract_file": str(contract_files["json"]),
                    "full_gate_passed": full_gate_passed,
                    "skipped_gates": skipped_gates,
                    "scope_coverage_status": feature_coverage_report.status,
                    "scope_coverage_rate": feature_coverage_report.coverage_rate,
                    "scope_gap_count": feature_coverage_report.missing_count
                    + feature_coverage_report.unknown_count,
                    "scope_high_priority_gap_count": feature_coverage_report.high_priority_gap_count,
                    "scope_feature_checklist_file": str(feature_checklist_files["json"]),
                },
            )
            _flush_resume_audit(status="success")
            if resume_audit_files:
                self.console.print("[cyan]恢复审计:[/cyan]")
                self.console.print(f"  - JSON: {resume_audit_files['json']}")
                self.console.print(f"  - Markdown: {resume_audit_files['markdown']}")
                self.console.print("")

        except Exception as e:
            _record_stage(False, details={"error": str(e)})
            metric_files = _finalize_metrics(success=False, reason=str(e))
            contract_files = _finalize_contract(success=False, reason=str(e))
            failed_stage_label = current_stage or "unknown"
            _persist_run_state(
                "failed",
                {
                    "failure_reason": str(e),
                    "failed_stage": failed_stage_label,
                    "metrics_file": str(metric_files["json"]),
                    "contract_file": str(contract_files["json"]),
                },
            )
            _flush_resume_audit(status="failed", failure_reason=str(e))
            self.console.print(f"[red]流水线失败: {e}[/red]")
            import traceback

            self.console.print(traceback.format_exc())
            self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
            self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
            if resume_audit_files:
                self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
            return 1

        return 0

    def _cmd_config(self, args) -> int:
        """配置管理"""
        config_manager = get_config_manager()

        if not config_manager.exists():
            self.console.print("[red]未找到项目配置[/red]")
            return 1

        if args.action == "list":
            # 列出所有配置
            config = config_manager.config
            self.console.print("[cyan]项目配置:[/cyan]")
            for key, value in config.__dict__.items():
                if not key.startswith("_"):
                    self.console.print(f"  {key}: {value}")

        elif args.action == "get":
            if not args.key:
                self.console.print("[red]请指定配置键[/red]")
                return 1
            value = config_manager.get(args.key)
            self.console.print(f"{args.key}: {value}")

        elif args.action == "set":
            if not args.key or not args.value:
                self.console.print("[red]请指定配置键和值[/red]")
                return 1
            valid_keys = {
                key
                for key in ProjectConfig.__dataclass_fields__.keys()  # type: ignore[attr-defined]
                if not key.startswith("_")
            }
            if args.key not in valid_keys:
                self.console.print(f"[red]未知配置键: {args.key}[/red]")
                self.console.print(f"[dim]可用配置键: {', '.join(sorted(valid_keys))}[/dim]")
                return 1
            try:
                updated = config_manager.update(**{args.key: args.value})
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                return 1
            actual = getattr(updated, args.key, args.value)
            self.console.print(f"[green]✓[/green] {args.key} = {actual}")

        elif args.action == "validate":
            return self._cmd_config_validate()

        return 0

    def _cmd_config_validate(self) -> int:
        """验证 super-dev.yaml 配置文件是否符合 schema 规范"""
        import yaml

        from .config.schema_validator import validate_config

        config_path = Path.cwd() / "super-dev.yaml"

        if not config_path.exists():
            self.console.print("[red]未找到 super-dev.yaml 配置文件[/red]")
            return 1

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            self.console.print(f"[red]配置文件解析失败: {exc}[/red]")
            return 1

        errors = validate_config(raw)

        if errors:
            self.console.print("[red]配置验证失败:[/red]")
            for err in errors:
                self.console.print(f"  [red]✗[/red] {err}")
            return 1

        self.console.print("[green]✓ 配置验证通过，super-dev.yaml 格式正确[/green]")
        return 0

    def _cmd_skill(self, args) -> int:
        """Skill 管理"""
        from .skills import SkillManager

        manager = SkillManager(Path.cwd())

        if args.action == "targets":
            self.console.print("[cyan]支持的 Skill 目标平台:[/cyan]")
            for target in manager.list_targets():
                self.console.print(f"  - {target}")
            return 0

        if args.action == "list":
            installed = manager.list_installed(args.target)
            if not installed:
                self.console.print(f"[dim]{args.target} 未安装任何 skill[/dim]")
                return 0

            self.console.print(f"[cyan]{args.target} 已安装 skill:[/cyan]")
            for skill_name in installed:
                self.console.print(f"  - {skill_name}")
            return 0

        if args.action == "install":
            if not args.source_or_name:
                self.console.print("[red]请提供 skill 来源（目录/git/super-dev）[/red]")
                return 1

            try:
                result = manager.install(
                    source=args.source_or_name,
                    target=args.target,
                    name=args.name,
                    force=args.force,
                )
            except Exception as e:
                self.console.print(f"[red]Skill 安装失败: {e}[/red]")
                return 1

            self.console.print("[green]✓ Skill 安装成功[/green]")
            self.console.print(f"  名称: {result.name}")
            self.console.print(f"  目标: {result.target}")
            self.console.print(f"  路径: {result.path}")
            self.console.print(f"  来源: {result.source}")
            return 0

        if args.action == "uninstall":
            if not args.source_or_name:
                self.console.print("[red]请提供要卸载的 skill 名称[/red]")
                return 1

            try:
                removed_path = manager.uninstall(args.source_or_name, args.target)
            except Exception as e:
                self.console.print(f"[red]Skill 卸载失败: {e}[/red]")
                return 1

            self.console.print("[green]✓ Skill 已卸载[/green]")
            self.console.print(f"  路径: {removed_path}")
            return 0

        self.console.print("[yellow]未知 skill 操作[/yellow]")
        return 1

    def _cmd_integrate(self, args) -> int:
        """多平台集成配置"""
        from .integrations import IntegrationManager

        manager = IntegrationManager(Path.cwd())

        if args.action == "list":
            self.console.print("[cyan]支持的集成平台:[/cyan]")
            for target in manager.list_targets():
                self.console.print(f"  - {target.name}: {target.description}")
            return 0

        if args.action == "setup":
            if args.all:
                results = manager.setup_all(force=args.force)
                self.console.print("[green]✓ 已完成所有平台集成配置[/green]")
                for platform, files in results.items():
                    if not files:
                        self.console.print(f"  {platform}: [dim]无变更[/dim]")
                        continue
                    self.console.print(f"  {platform}:")
                    for file_path in files:
                        self.console.print(f"    - {file_path}")
                return 0

            if not args.target:
                self.console.print("[red]请通过 --target 指定平台，或使用 --all[/red]")
                return 1

            files = manager.setup(args.target, force=args.force)
            if not files:
                self.console.print("[yellow]配置已存在，无需修改（可加 --force 覆盖）[/yellow]")
                return 0

            self.console.print("[green]✓ 集成配置已生成[/green]")
            for file_path in files:
                self.console.print(f"  - {file_path}")
            return 0

        if args.action == "harden":
            from .skills import SkillManager

            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            include_user_surfaces = bool(getattr(args, "with_user_surfaces", False))
            detected_meta: dict[str, list[str]] = {}
            if args.target:
                targets = [args.target]
            elif args.all:
                targets = available_targets
            else:
                targets, detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not targets:
                    targets = available_targets
            hardening_results: dict[str, Any] = {}
            skill_manager = SkillManager(project_dir)
            official_compare_enabled = bool(getattr(args, "official_compare", False)) or True
            usage_profiles: dict[str, dict[str, Any]] = {}
            for target in targets:
                profile = manager.get_adapter_profile(target)
                plan = manager.host_hardening_blueprint(
                    target,
                    include_user_surfaces=include_user_surfaces,
                )
                usage_profiles[target] = self._build_host_usage_profile(
                    integration_manager=manager,
                    target=target,
                )
                written_files = [str(path) for path in manager.setup(target=target, force=True)]
                slash_file = manager.setup_slash_command(target=target, force=True)
                if slash_file is not None:
                    written_files.append(str(slash_file))
                if include_user_surfaces:
                    global_protocol = manager.setup_global_protocol(target=target, force=True)
                    if global_protocol is not None:
                        written_files.append(str(global_protocol))
                    global_slash = manager.setup_global_slash_command(target=target, force=True)
                    if global_slash is not None:
                        written_files.append(str(global_slash))
                skill_install: dict[str, Any] = {
                    "required": manager.requires_skill(target),
                    "installed": False,
                }
                if manager.requires_skill(target):
                    try:
                        skill_path = skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=skill_manager.default_skill_name(target),
                            force=True,
                        ).path
                        skill_install = {
                            "required": True,
                            "installed": True,
                            "path": str(skill_path),
                        }
                    except Exception as exc:
                        skill_install = {
                            "required": True,
                            "installed": False,
                            "error": str(exc),
                        }
                docs_check = (
                    manager.verify_official_docs(target)
                    if bool(getattr(args, "verify_docs", False))
                    else {}
                )
                official_compare = (
                    manager.compare_official_capabilities(target, timeout_seconds=8.0)
                    if official_compare_enabled
                    else {}
                )
                hardening_results[target] = {
                    "host": target,
                    "category": profile.category,
                    "adapter_mode": profile.adapter_mode,
                    "plan": plan,
                    "written_files": written_files,
                    "skill_install": skill_install,
                    "contract": {},
                    "docs_check": docs_check,
                    "official_compare": official_compare,
                }
            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            compatibility = self._build_compatibility_summary(
                report=report,
                targets=targets,
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            hosts_report = report.get("hosts", {}) if isinstance(report, dict) else {}
            if isinstance(hosts_report, dict):
                for target in targets:
                    host_info = hosts_report.get(target, {})
                    checks = host_info.get("checks", {}) if isinstance(host_info, dict) else {}
                    contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
                    item = hardening_results.get(target, {})
                    if isinstance(item, dict):
                        item["contract"] = contract if isinstance(contract, dict) else {}
            payload = {
                "project_dir": str(project_dir),
                "detected_hosts": targets if not detected_meta else list(detected_meta.keys()),
                "detection_details": detected_meta,
                "selected_targets": targets,
                "hardening_results": hardening_results,
                "report": report,
                "compatibility": compatibility,
                "usage_profiles": usage_profiles,
            }
            official_compare_summary = self._build_official_compare_summary(
                hardening_results=hardening_results
            )
            host_parity_summary = self._build_host_parity_summary(usage_profiles=usage_profiles)
            host_gate_summary = self._build_host_gate_summary(report=report, targets=targets)
            host_runtime_script_summary = self._build_host_runtime_script_summary(
                usage_profiles=usage_profiles
            )
            host_recovery_summary = self._build_host_recovery_summary(
                targets=targets,
                usage_profiles=usage_profiles,
            )
            payload["official_compare_summary"] = official_compare_summary
            payload["host_parity_summary"] = host_parity_summary
            payload["host_gate_summary"] = host_gate_summary
            payload["host_runtime_script_summary"] = host_runtime_script_summary
            payload["host_recovery_summary"] = host_recovery_summary
            parity_index = self._build_host_parity_index(
                threshold=float(getattr(args, "parity_threshold", 95.0)),
                official_compare_summary=official_compare_summary,
                host_parity_summary=host_parity_summary,
                host_gate_summary=host_gate_summary,
                host_runtime_script_summary=host_runtime_script_summary,
                host_recovery_summary=host_recovery_summary,
                compatibility=compatibility,
            )
            payload["host_parity_index"] = parity_index
            if not bool(args.no_save):
                report_files = self._write_host_hardening_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return (
                    0
                    if bool(report.get("overall_ready", False))
                    and bool(parity_index.get("passed", False))
                    else 1
                )

            self.console.print("[cyan]Super Dev 宿主系统级深适配[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            self.console.print(
                f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
                f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]官方文档对照: {official_compare_summary.get('score', 0):.2f}/100 "
                f"({official_compare_summary.get('passed', 0)}/{official_compare_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]宿主体验一致性: {host_parity_summary.get('score', 0):.2f}/100 "
                f"({host_parity_summary.get('passed', 0)}/{host_parity_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]确认门禁一致性: {host_gate_summary.get('score', 0):.2f}/100 "
                f"({host_gate_summary.get('passed', 0)}/{host_gate_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]真人验收脚本一致性: {host_runtime_script_summary.get('score', 0):.2f}/100 "
                f"({host_runtime_script_summary.get('passed', 0)}/{host_runtime_script_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]失败恢复一致性: {host_recovery_summary.get('score', 0):.2f}/100 "
                f"({host_recovery_summary.get('passed', 0)}/{host_recovery_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]Host Parity Index: {parity_index.get('score', 0):.2f}/100 "
                f"(threshold {parity_index.get('threshold', 95.0):.2f}, "
                f"{'pass' if bool(parity_index.get('passed', False)) else 'fail'})[/cyan]"
            )
            for target in targets:
                item = hardening_results.get(target, {})
                contract = item.get("contract", {})
                ok = bool((contract or {}).get("ok", False))
                self.console.print("")
                self.console.print(
                    f"[cyan]- {target}[/cyan] "
                    f"{'[green]contract ok[/green]' if ok else '[yellow]needs review[/yellow]'}"
                )
                written_files = item.get("written_files", [])
                if isinstance(written_files, list) and written_files:
                    self.console.print("  已更新:")
                    for file_path in written_files:
                        self.console.print(f"    - {file_path}")
                skill_install = item.get("skill_install", {})
                if isinstance(skill_install, dict) and bool(skill_install.get("required", False)):
                    if bool(skill_install.get("installed", False)):
                        self.console.print(
                            f"  Skill 安装: [green]ok[/green] ({skill_install.get('path', '-')})"
                        )
                    else:
                        self.console.print(
                            f"  Skill 安装: [yellow]failed[/yellow] ({skill_install.get('error', '-')})"
                        )
                docs_check = item.get("docs_check", {})
                if isinstance(docs_check, dict) and docs_check:
                    self.console.print(
                        f"  文档在线核验: {docs_check.get('status', 'unknown')} "
                        f"({docs_check.get('reachable', 0)}/{docs_check.get('checked', 0)})"
                    )
                official_compares = payload.get("official_compares", {})
                if isinstance(official_compares, dict):
                    compare = official_compares.get(target, {})
                    if isinstance(compare, dict) and compare:
                        self.console.print(
                            f"  官方对照: {compare.get('status', 'unknown')} "
                            f"({compare.get('reachable_urls', 0)}/{compare.get('checked_urls', 0)})"
                        )
                official_compare = item.get("official_compare", {})
                if isinstance(official_compare, dict) and official_compare:
                    self.console.print(
                        f"  官方对照: {official_compare.get('status', 'unknown')} "
                        f"({official_compare.get('reachable_urls', 0)}/{official_compare.get('checked_urls', 0)})"
                    )
                invalid = (contract or {}).get("invalid_surfaces", {})
                if isinstance(invalid, dict) and invalid:
                    self.console.print("  [yellow]仍有不一致面[/yellow]:")
                    for surface_key in invalid.keys():
                        self.console.print(f"    - {surface_key}")
                else:
                    self.console.print("  [green]✓[/green] 接入面已与系统流程契约对齐")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]深适配报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            return (
                0
                if bool(report.get("overall_ready", False))
                and bool(parity_index.get("passed", False))
                else 1
            )

        if args.action == "matrix":
            targets: list[str] | None = [args.target] if args.target else None
            profiles = manager.list_adapter_profiles(targets=targets)
            docs_checks: dict[str, Any] = {}
            official_compares: dict[str, Any] = {}
            if bool(getattr(args, "verify_docs", False)):
                for profile in profiles:
                    docs_checks[profile.host] = manager.verify_official_docs(profile.host)
            if bool(getattr(args, "official_compare", False)):
                for profile in profiles:
                    official_compares[profile.host] = manager.compare_official_capabilities(
                        profile.host
                    )
            if args.json:
                payload = {
                    "profiles": [profile.to_dict() for profile in profiles],
                    "docs_checks": docs_checks,
                    "official_compares": official_compares,
                }
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主适配矩阵[/cyan]")
            verified_count = sum(1 for item in profiles if item.docs_verified)
            self.console.print(f"[dim]官方文档核验: {verified_count}/{len(profiles)}[/dim]")
            for profile in profiles:
                self.console.print(f"[cyan]- {profile.host} ({profile.category})[/cyan]")
                self.console.print(f"  适配模式: {profile.adapter_mode}")
                self.console.print(f"  使用模式: {profile.usage_mode}")
                self.console.print(f"  模型提供方: {profile.host_model_provider}")
                docs_badge = "verified" if profile.docs_verified else "pending"
                docs_url = profile.official_docs_url or "-"
                self.console.print(f"  官方文档: {docs_url} ({docs_badge})")
                if profile.official_docs_references:
                    self.console.print(f"  官方参考: {len(profile.official_docs_references)} 条")
                labels = profile.capability_labels or {}
                capability_summary = (
                    ", ".join(f"{key}={value}" for key, value in labels.items()) if labels else "-"
                )
                self.console.print(f"  能力标签: {capability_summary}")
                if profile.host in docs_checks:
                    docs_check = docs_checks[profile.host]
                    self.console.print(
                        f"  文档在线核验: {docs_check.get('status', 'unknown')} "
                        f"({docs_check.get('reachable', 0)}/{docs_check.get('checked', 0)})"
                    )
                if profile.host in official_compares:
                    compare = official_compares[profile.host]
                    self.console.print(
                        f"  官方对照: {compare.get('status', 'unknown')} "
                        f"({compare.get('reachable_urls', 0)}/{compare.get('checked_urls', 0)})"
                    )
                self.console.print(f"  主入口: {profile.primary_entry}")
                self.console.print(f"  触发命令: {profile.trigger_command}")
                self.console.print(f"  触发上下文: {profile.trigger_context}")
                self.console.print(f"  触发位置: {profile.usage_location}")
                self.console.print(f"  终端入口: {profile.terminal_entry}")
                self.console.print(f"  终端范围: {profile.terminal_entry_scope}")
                self.console.print(
                    f"  接入后重启: {'是' if profile.requires_restart_after_onboard else '否'}"
                )
                self.console.print(f"  规则文件: {', '.join(profile.integration_files)}")
                self.console.print(f"  Slash 文件: {profile.slash_command_file}")
                self.console.print(f"  Skill 目录: {profile.skill_dir}")
                commands = (
                    ", ".join(profile.detection_commands) if profile.detection_commands else "-"
                )
                paths = ", ".join(profile.detection_paths) if profile.detection_paths else "-"
                self.console.print(f"  探测命令: {commands}")
                self.console.print(f"  探测路径: {paths}")
                if profile.post_onboard_steps:
                    self.console.print("  接入后步骤:")
                    for step in profile.post_onboard_steps:
                        self.console.print(f"    - {step}")
                if profile.usage_notes:
                    self.console.print("  使用提示:")
                    for note in profile.usage_notes:
                        self.console.print(f"    - {note}")
                self.console.print(f"  Smoke Prompt: {profile.smoke_test_prompt}")
                self.console.print(f"  Smoke Signal: {profile.smoke_success_signal}")
                self.console.print(f"  备注: {profile.notes}")
            return 0

        if args.action == "smoke":
            targets: list[str] = (
                [args.target] if args.target else [item.name for item in manager.list_targets()]
            )
            profiles = manager.list_adapter_profiles(targets=targets)
            if args.json:
                payload = [
                    {
                        "host": profile.host,
                        "final_trigger": self._display_final_trigger(profile),
                        "smoke_test_prompt": profile.smoke_test_prompt,
                        "smoke_test_steps": list(profile.smoke_test_steps),
                        "smoke_success_signal": profile.smoke_success_signal,
                    }
                    for profile in profiles
                ]
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主 Smoke 验收[/cyan]")
            for profile in profiles:
                self.console.print(f"[cyan]- {profile.host}[/cyan]")
                self.console.print(f"  最终输入: {self._display_final_trigger(profile)}")
                self.console.print(f"  验收语句: {profile.smoke_test_prompt}")
                self.console.print("  验收步骤:")
                for step in profile.smoke_test_steps:
                    self.console.print(f"    - {step}")
                self.console.print(f"  通过标准: {profile.smoke_success_signal}")
            return 0

        if args.action == "audit":
            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            targets: list[str]
            detected_meta: dict[str, list[str]] = {}
            if args.target:
                targets = [args.target]
            elif args.all:
                targets = available_targets
            else:
                targets, detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not targets:
                    targets = available_targets

            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            repair_actions: dict[str, dict[str, str]] = {}
            if args.repair:
                repair_actions = self._repair_host_diagnostics(
                    project_dir=project_dir,
                    report=report,
                    skill_name="super-dev",
                    force=bool(args.force),
                    check_integrate=True,
                    check_skill=True,
                    check_slash=True,
                    include_user_surfaces=self._include_user_surfaces(args),
                )
                report = self._collect_host_diagnostics(
                    project_dir=project_dir,
                    targets=targets,
                    skill_name="super-dev",
                    check_integrate=True,
                    check_skill=True,
                    check_slash=True,
                )

            compatibility = self._build_compatibility_summary(
                report=report,
                targets=targets,
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            usage_profiles = {
                target: self._build_host_usage_profile(
                    integration_manager=manager,
                    target=target,
                )
                for target in targets
            }
            payload = {
                "project_dir": str(project_dir),
                "detected_hosts": targets if not detected_meta else list(detected_meta.keys()),
                "detection_details": detected_meta,
                "selected_targets": targets,
                "report": report,
                "compatibility": compatibility,
                "usage_profiles": usage_profiles,
                "repair_actions": repair_actions,
            }
            payload["host_parity_summary"] = self._build_host_parity_summary(
                usage_profiles=usage_profiles
            )
            payload["host_gate_summary"] = self._build_host_gate_summary(
                report=report, targets=targets
            )
            payload["host_runtime_script_summary"] = self._build_host_runtime_script_summary(
                usage_profiles=usage_profiles
            )
            payload["host_recovery_summary"] = self._build_host_recovery_summary(
                targets=targets,
                usage_profiles=usage_profiles,
            )
            if bool(getattr(args, "verify_docs", False)):
                payload["docs_checks"] = {
                    target: manager.verify_official_docs(target) for target in targets
                }
            if bool(getattr(args, "official_compare", False)):
                official_compares = {
                    target: manager.compare_official_capabilities(target, timeout_seconds=8.0)
                    for target in targets
                }
                payload["official_compares"] = official_compares
                payload["official_compare_summary"] = self._build_official_compare_summary(
                    hardening_results={
                        target: {"official_compare": official_compares.get(target, {})}
                        for target in targets
                    }
                )
            payload["host_parity_index"] = self._build_host_parity_index(
                threshold=float(getattr(args, "parity_threshold", 95.0)),
                official_compare_summary=payload.get("official_compare_summary", {}),
                host_parity_summary=payload.get("host_parity_summary", {}),
                host_gate_summary=payload.get("host_gate_summary", {}),
                host_runtime_script_summary=payload.get("host_runtime_script_summary", {}),
                host_recovery_summary=payload.get("host_recovery_summary", {}),
                compatibility=compatibility,
            )
            if not bool(args.no_save):
                report_files = self._write_host_surface_audit_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}

            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                parity_index = payload.get("host_parity_index", {})
                return (
                    0
                    if bool(report.get("overall_ready", False))
                    and bool((parity_index or {}).get("passed", False))
                    else 1
                )

            self.console.print("[cyan]Super Dev 宿主 Surface 审计[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            if detected_meta:
                self.console.print(
                    f"[cyan]自动检测到 {len(detected_meta)} 个宿主：{', '.join(self._host_label(target) for target in detected_meta)}[/cyan]"
                )
            self.console.print(
                f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
                f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            host_parity = payload.get("host_parity_summary", {})
            if isinstance(host_parity, dict) and host_parity:
                self.console.print(
                    f"[cyan]宿主体验一致性: {host_parity.get('score', 0):.2f}/100 "
                    f"({host_parity.get('passed', 0)}/{host_parity.get('total', 0)})[/cyan]"
                )
            host_gate = payload.get("host_gate_summary", {})
            if isinstance(host_gate, dict) and host_gate:
                self.console.print(
                    f"[cyan]确认门禁一致性: {host_gate.get('score', 0):.2f}/100 "
                    f"({host_gate.get('passed', 0)}/{host_gate.get('total', 0)})[/cyan]"
                )
            host_runtime_script = payload.get("host_runtime_script_summary", {})
            if isinstance(host_runtime_script, dict) and host_runtime_script:
                self.console.print(
                    f"[cyan]真人验收脚本一致性: {host_runtime_script.get('score', 0):.2f}/100 "
                    f"({host_runtime_script.get('passed', 0)}/{host_runtime_script.get('total', 0)})[/cyan]"
                )
            host_recovery = payload.get("host_recovery_summary", {})
            if isinstance(host_recovery, dict) and host_recovery:
                self.console.print(
                    f"[cyan]失败恢复一致性: {host_recovery.get('score', 0):.2f}/100 "
                    f"({host_recovery.get('passed', 0)}/{host_recovery.get('total', 0)})[/cyan]"
                )
            official_summary = payload.get("official_compare_summary", {})
            if isinstance(official_summary, dict) and official_summary:
                self.console.print(
                    f"[cyan]官方文档对照: {official_summary.get('score', 0):.2f}/100 "
                    f"({official_summary.get('passed', 0)}/{official_summary.get('total', 0)})[/cyan]"
                )
            parity_index = payload.get("host_parity_index", {})
            if isinstance(parity_index, dict) and parity_index:
                self.console.print(
                    f"[cyan]Host Parity Index: {parity_index.get('score', 0):.2f}/100 "
                    f"(threshold {parity_index.get('threshold', 95.0):.2f}, "
                    f"{'pass' if bool(parity_index.get('passed', False)) else 'fail'})[/cyan]"
                )
            if args.repair and repair_actions:
                self.console.print("[cyan]修复动作[/cyan]")
                for target, actions in repair_actions.items():
                    action_text = ", ".join(f"{key}={value}" for key, value in actions.items())
                    self.console.print(f"  - {target}: {action_text}")
            for target in targets:
                host = report["hosts"].get(target, {})
                usage = usage_profiles.get(target, {})
                ready = bool(host.get("ready", False))
                self.console.print("")
                self.console.print(
                    f"[cyan]- {target}[/cyan] {'[green]ready[/green]' if ready else '[yellow]needs repair[/yellow]'}"
                )
                self.console.print(f"  触发命令: {usage.get('final_trigger', '-')}")
                self.console.print(f"  宿主协议: {usage.get('host_protocol_summary', '-')}")
                checks = host.get("checks", {})
                contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
                invalid_surfaces = (
                    contract.get("invalid_surfaces", {}) if isinstance(contract, dict) else {}
                )
                if isinstance(invalid_surfaces, dict) and invalid_surfaces:
                    self.console.print("  [yellow]过期/缺失的接入面[/yellow]:")
                    for surface_key, surface_info in invalid_surfaces.items():
                        if not isinstance(surface_info, dict):
                            continue
                        missing_markers = surface_info.get("missing_markers", [])
                        marker_text = (
                            ", ".join(str(item) for item in missing_markers)
                            if isinstance(missing_markers, list)
                            else "-"
                        )
                        self.console.print(f"    - {surface_key}")
                        self.console.print(f"      path: {surface_info.get('path', '-')}")
                        self.console.print(f"      missing: {marker_text}")
                else:
                    self.console.print("  [green]✓[/green] 所有受管接入面契约完整")
                suggestions = host.get("suggestions", [])
                if isinstance(suggestions, list) and suggestions:
                    self.console.print("  建议修复:")
                    for suggestion in suggestions:
                        self.console.print(f"    - {suggestion}")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]审计报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            return (
                0
                if bool(report.get("overall_ready", False))
                and bool((parity_index or {}).get("passed", False))
                else 1
            )

        if args.action == "validate":
            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            detected_meta: dict[str, list[str]] = {}
            competition_evidence: dict[str, object] = {}
            if args.status and not args.target:
                self.console.print("[red]--status 仅可与 --target 一起使用[/red]")
                return 1
            if args.status and args.status not in {"pending", "passed", "failed"}:
                self.console.print("[red]无效的运行时验收状态[/red]")
                return 1
            if args.competition_evidence_json:
                try:
                    parsed_evidence = json.loads(args.competition_evidence_json)
                except json.JSONDecodeError as exc:
                    self.console.print(f"[red]比赛验收证据 JSON 无效:[/red] {exc}")
                    return 1
                if not isinstance(parsed_evidence, dict):
                    self.console.print("[red]比赛验收证据必须是 JSON object[/red]")
                    return 1
                competition_evidence = parsed_evidence
            if args.status and args.target:
                runtime_state, file_path = self._update_host_runtime_validation_state(
                    project_dir=project_dir,
                    target=args.target,
                    status=args.status,
                    comment=args.comment or "",
                    actor=args.actor or "user",
                    competition_evidence=competition_evidence,
                )
                status_label = self._host_runtime_status_label(args.status)
                if args.json:
                    host_entry = runtime_state.get("hosts", {}).get(args.target, {})
                    if not isinstance(host_entry, dict):
                        host_entry = {}
                    repo_probe = build_host_runtime_probe(
                        project_dir,
                        target=args.target,
                        surface_ready=True,
                    )
                    sys.stdout.write(
                        json.dumps(
                            {
                                "status": "success",
                                "host": args.target,
                                "manual_runtime_status": args.status,
                                "manual_runtime_status_label": status_label,
                                "comment": args.comment or "",
                                "actor": args.actor or "user",
                                "file_path": str(file_path),
                                "updated_at": str(host_entry.get("updated_at", "")).strip(),
                                "competition_evidence": host_entry.get("competition_evidence", {}),
                                "competition_evidence_ready": bool(
                                    host_entry.get("competition_evidence_ready", False)
                                ),
                                "competition_evidence_missing": list(
                                    host_entry.get("competition_evidence_missing", [])
                                ),
                                "repo_probe": repo_probe,
                                "runtime_evidence": self._build_runtime_evidence_record(
                                    host_id=args.target,
                                    surface_ready=True,
                                    runtime_entry=host_entry,
                                ),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n"
                    )
                    return 0
                self.console.print(
                    f"[green]已更新宿主真人验收状态[/green] {args.target}: {status_label}"
                )
                if args.comment:
                    self.console.print(f"[dim]备注: {args.comment}[/dim]")
                missing_competition_sections = (
                    runtime_state.get("hosts", {})
                    .get(args.target, {})
                    .get("competition_evidence_missing", [])
                )
                if isinstance(missing_competition_sections, list) and missing_competition_sections:
                    self.console.print(
                        "[yellow]SEEAI 比赛证据仍未补齐[/yellow] "
                        + "、".join(str(item) for item in missing_competition_sections)
                    )
                self.console.print(f"[dim]状态文件: {file_path}[/dim]")
                return 0

            if args.target:
                targets = [args.target]
            elif args.all:
                targets = available_targets
            else:
                targets, detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not targets:
                    targets = available_targets

            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            usage_profiles = {
                target: self._build_host_usage_profile(
                    integration_manager=manager,
                    target=target,
                )
                for target in targets
            }
            payload = self._build_host_runtime_validation_payload(
                project_dir=project_dir,
                targets=targets,
                detected_meta=detected_meta,
                report=report,
                usage_profiles=usage_profiles,
            )

            if not bool(args.no_save):
                report_files = self._write_host_runtime_validation_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}

            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主运行时验收矩阵[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            if detected_meta:
                self.console.print(
                    f"[cyan]自动检测到 {len(detected_meta)} 个宿主：{', '.join(self._host_label(target) for target in detected_meta)}[/cyan]"
                )
            summary = payload.get("summary", {})
            if isinstance(summary, dict):
                self.console.print(
                    f"[cyan]中心摘要: fully-ready {summary.get('fully_ready_count', 0)}/{summary.get('total_hosts', 0)} "
                    f"| surface-ready {summary.get('surface_ready_count', 0)}/{summary.get('total_hosts', 0)} "
                    f"| passed {summary.get('runtime_passed_count', 0)} "
                    f"| pending {summary.get('runtime_pending_count', 0)} "
                    f"| failed {summary.get('runtime_failed_count', 0)} "
                    f"| repo-probe failed {summary.get('repo_probe_failed_count', 0)}[/cyan]"
                )
            blockers = payload.get("blockers", [])
            if isinstance(blockers, list) and blockers:
                self.console.print("[yellow]当前阻塞项[/yellow]")
                for item in blockers[:8]:
                    if not isinstance(item, dict):
                        continue
                    self.console.print(f"  - {item.get('host', '-')}: {item.get('summary', '-')}")
            for host in payload.get("hosts", []):
                if not isinstance(host, dict):
                    continue
                ready_badge = (
                    "[green]surface-ready[/green]"
                    if bool(host.get("surface_ready", False))
                    else "[yellow]surface-not-ready[/yellow]"
                )
                self.console.print("")
                self.console.print(f"[cyan]- {host.get('host', '-') }[/cyan] {ready_badge}")
                self.console.print(f"  触发命令: {host.get('final_trigger', '-')}")
                self.console.print(f"  宿主协议: {host.get('host_protocol_summary', '-')}")
                self.console.print(
                    f"  人工验收状态: {host.get('manual_runtime_status_label', '-')}"
                )
                repo_probe = host.get("repo_probe", {})
                if isinstance(repo_probe, dict):
                    self.console.print(
                        f"  仓库级 probe: {repo_probe.get('status_label', '待补齐仓库级 probe')}"
                    )
                    repo_probe_summary = str(repo_probe.get("summary", "")).strip()
                    if repo_probe_summary:
                        self.console.print(f"  仓库级摘要: {repo_probe_summary}")
                if host.get("resume_probe_prompt"):
                    self.console.print("  继续当前流程:")
                    self.console.print(f"    - 宿主第一句: {host.get('resume_probe_prompt')}")
                    self.console.print(
                        f"    - 流程状态卡: {self._session_brief_path(Path(payload.get('project_dir', Path.cwd())))}"
                    )
                framework_playbook = host.get("framework_playbook", {})
                if isinstance(framework_playbook, dict) and framework_playbook:
                    self.console.print(
                        f"  跨平台框架专项: {framework_playbook.get('framework', '跨平台框架')}"
                    )
                    native_capabilities = framework_playbook.get("native_capabilities", [])
                    if isinstance(native_capabilities, list) and native_capabilities:
                        self.console.print(
                            "    - 原生能力面: "
                            + "；".join(str(item) for item in native_capabilities[:3])
                        )
                    validation_surfaces = framework_playbook.get("validation_surfaces", [])
                    if isinstance(validation_surfaces, list) and validation_surfaces:
                        self.console.print(
                            "    - 必验场景: "
                            + "；".join(str(item) for item in validation_surfaces[:3])
                        )
                if host.get("blocking_reason"):
                    self.console.print(f"  阻塞原因: {host.get('blocking_reason')}")
                if host.get("recommended_action"):
                    self.console.print(f"  建议动作: {host.get('recommended_action')}")
                if host.get("resume_probe_prompt"):
                    self.console.print(f"  恢复探针: {host.get('resume_probe_prompt')}")
                comment = host.get("manual_runtime_comment", "")
                if isinstance(comment, str) and comment.strip():
                    self.console.print(f"  验收备注: {comment.strip()}")
                self.console.print("  运行时检查清单:")
                checklist = host.get("runtime_checklist", [])
                if isinstance(checklist, list):
                    for item in checklist:
                        self.console.print(f"    - {item}")
                self.console.print("  通过标准:")
                criteria = host.get("pass_criteria", [])
                if isinstance(criteria, list):
                    for item in criteria:
                        self.console.print(f"    - {item}")
                resume_checklist = host.get("resume_checklist", [])
                if isinstance(resume_checklist, list) and resume_checklist:
                    self.console.print("  恢复检查清单:")
                    for item in resume_checklist:
                        self.console.print(f"    - {item}")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]验收矩阵报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            if isinstance(summary, dict):
                next_actions = summary.get("next_actions", [])
                if isinstance(next_actions, list) and next_actions:
                    self.console.print("")
                    self.console.print("[cyan]推荐动作[/cyan]")
                    for item in next_actions[:8]:
                        self.console.print(f"  - {item}")
            return 0

        self.console.print("[yellow]未知 integrate 操作[/yellow]")
        return 1

    _KNOWN_COMMANDS = {
        "init",
        "quality",
        "design",
        "spec",
        "task",
        "pipeline",
        "run",
        "config",
        "skill",
        "integrate",
        "onboard",
        "doctor",
        "setup",
        "install",
        "uninstall",
        "start",
        "detect",
        "update",
        "review",
        "release",
        "product-audit",
        "status",
        "next",
        "continue",
        "resume",
        "jump",
        "confirm",
        "clean",
        "generate",
        "enforce",
        "completion",
        "feedback",
        "migrate",
    }

    _SUGGESTIBLE_COMMANDS = {
        "update",
        "uninstall",
        "help",
        "version",
    }

    def _is_direct_requirement_input(self, argv: list[str]) -> bool:
        """判断是否为直达需求输入（非子命令模式）"""
        if not argv:
            return False

        first = argv[0]
        if first.startswith("-"):
            return False

        if first in self._KNOWN_COMMANDS:
            return False

        # Single ASCII-only bare word without spaces/colons looks like a mistyped
        # command, not a requirement description.  Requirement mode requires either:
        # - multiple non-flag tokens, or
        # - the text contains `:` / `：` (host trigger prefix), or
        # - the first token contains non-ASCII characters (e.g. Chinese text).
        joined = " ".join(argv)
        if ":" in joined or "：" in joined:
            return True
        # If there are extra flag-style args (--offline etc.), still treat as requirement
        non_flag_tokens = [t for t in argv if not t.startswith("-")]
        if len(non_flag_tokens) >= 2:
            return True
        # Single bare ASCII-only word → likely a mistyped command, not a requirement
        if (
            len(non_flag_tokens) == 1
            and non_flag_tokens[0].isascii()
            and non_flag_tokens[0].isidentifier()
        ):
            return False
        # Fallback: treat as requirement (includes non-ASCII single tokens)
        return True

    def _is_unknown_command(self, argv: list[str]) -> bool:
        """判断是否为未知的单词命令（非需求直达，非已知命令）"""
        if not argv:
            return False
        first = argv[0]
        if first.startswith("-"):
            return False
        if first in self._KNOWN_COMMANDS:
            return False
        # Single bare ASCII-only word that looks like a command name
        non_flag_tokens = [t for t in argv if not t.startswith("-")]
        if (
            len(non_flag_tokens) == 1
            and non_flag_tokens[0].isascii()
            and non_flag_tokens[0].isidentifier()
        ):
            return True
        return False

    def _suggest_commands(self, unknown: str) -> list[str]:
        """为未知命令提供建议（简单前缀 + 编辑距离匹配）"""
        suggestions: list[str] = []
        for cmd in sorted(self._SUGGESTIBLE_COMMANDS):
            if cmd.startswith(unknown[:2]) or unknown.startswith(cmd[:2]):
                suggestions.append(cmd)
        # Always include the most common commands as fallback
        primary = ["update", "uninstall", "help", "version"]
        if not suggestions:
            suggestions = primary
        return suggestions[:6]

    def _parse_direct_requirement_args(self, argv: list[str]) -> tuple[str, dict[str, Any]]:
        """
        解析直达模式参数。

        支持写法：
        - super-dev
        - super-dev --offline
        """
        value_flags = {
            "-p": "platform",
            "--platform": "platform",
            "-f": "frontend",
            "--frontend": "frontend",
            "-b": "backend",
            "--backend": "backend",
            "-d": "domain",
            "--domain": "domain",
            "--name": "name",
            "--cicd": "cicd",
            "--quality-threshold": "quality_threshold",
        }
        bool_flags = {
            "--skip-redteam": "skip_redteam",
            "--skip-scaffold": "skip_scaffold",
            "--skip-quality-gate": "skip_quality_gate",
            "--skip-rehearsal-verify": "skip_rehearsal_verify",
            "--offline": "offline",
        }

        description_tokens: list[str] = []
        overrides: dict[str, Any] = {}
        index = 0
        while index < len(argv):
            token = argv[index]

            if token in bool_flags:
                overrides[bool_flags[token]] = True
                index += 1
                continue

            if token in value_flags:
                if index + 1 >= len(argv):
                    raise ValueError(f"参数 {token} 缺少取值")
                raw_value = argv[index + 1]
                key = value_flags[token]
                if key == "quality_threshold":
                    if not raw_value.isdigit():
                        raise ValueError("--quality-threshold 需要整数值")
                    overrides[key] = int(raw_value)
                else:
                    overrides[key] = raw_value
                index += 2
                continue

            description_tokens.append(token)
            index += 1

        description = " ".join(description_tokens).strip()
        if not description:
            raise ValueError("请提供需求描述")
        return description, overrides

    def _review_status_label(self, status: str, *, review_type: str = "docs") -> str:
        if status == "confirmed":
            return (
                "已通过"
                if review_type in {"preview", "ui", "architecture", "quality"}
                else "已确认"
            )
        if status == "revision_requested":
            if review_type == "preview":
                return "需继续修改"
            if review_type == "ui":
                return "需改版"
            if review_type == "architecture":
                return "需返工"
            if review_type == "quality":
                return "需整改"
            return "需修改"
        return "待确认"

    def _docs_confirmation_label(self, status: str) -> str:
        return self._review_status_label(status, review_type="docs")

    def _get_docs_confirmation_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_docs_confirmation(project_dir) or {}
        gate_state = docs_gate_status(project_dir)
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(docs_confirmation_file(project_dir)),
            "confirmed": bool(gate_state.get("confirmed", False)),
            "binding_matches_current": bool(gate_state.get("binding_matches_current", False)),
        }

    def _docs_confirmation_is_confirmed(self, project_dir: Path) -> bool:
        return bool(self._get_docs_confirmation_state(project_dir)["confirmed"])

    def _get_ui_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_ui_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(ui_revision_file(project_dir)),
        }

    def _ui_revision_is_clear(self, project_dir: Path) -> bool:
        return self._get_ui_revision_state(project_dir)["status"] != "revision_requested"

    def _get_preview_confirmation_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_preview_confirmation(project_dir) or {}
        gate_state = preview_gate_status(project_dir)
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(preview_confirmation_file(project_dir)),
            "confirmed": bool(gate_state.get("confirmed", False)),
            "binding_matches_current": bool(gate_state.get("binding_matches_current", False)),
        }

    def _preview_confirmation_is_confirmed(self, project_dir: Path) -> bool:
        return bool(self._get_preview_confirmation_state(project_dir)["confirmed"])

    def _get_architecture_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_architecture_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(architecture_revision_file(project_dir)),
        }

    def _architecture_revision_is_clear(self, project_dir: Path) -> bool:
        return self._get_architecture_revision_state(project_dir)["status"] != "revision_requested"

    def _get_quality_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_quality_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(quality_revision_file(project_dir)),
        }

    def _quality_revision_is_clear(self, project_dir: Path) -> bool:
        return self._get_quality_revision_state(project_dir)["status"] != "revision_requested"

    def _has_core_docs(self, project_dir: Path) -> bool:
        output_dir = project_dir / "output"
        if not output_dir.exists():
            return False
        return (
            any(output_dir.glob("*-prd.md"))
            and any(output_dir.glob("*-architecture.md"))
            and any(output_dir.glob("*-uiux.md"))
        )

    def _ensure_docs_confirmation_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        if not self._has_core_docs(project_dir):
            return True
        if self._docs_confirmation_is_confirmed(project_dir):
            return True

        current = self._get_docs_confirmation_state(project_dir)
        self.console.print(f"[red]{action_label}前，必须先完成三文档确认[/red]")
        self.console.print(
            f"[dim]当前状态: {self._docs_confirmation_label(current['status'])}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print("[dim]先查看 output/*-prd.md、*-architecture.md、*-uiux.md[/dim]")
        self.console.print("[dim]然后回到宿主里明确回复：“文档确认，可以继续”[/dim]")
        return False

    def _ensure_ui_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_ui_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成 UI 改版返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='ui')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先更新 output/*-uiux.md，再重做前端，并重新执行 frontend runtime 与 UI review[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
        return False

    def _ensure_preview_confirmation_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        output_dir = project_dir / "output"
        frontend_ready = any(output_dir.glob("*-frontend-runtime.json"))
        if not frontend_ready:
            return True
        if self._preview_confirmation_is_confirmed(project_dir):
            return True

        current = self._get_preview_confirmation_state(project_dir)
        self.console.print(f"[red]{action_label}前，必须先完成前端预览确认[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='preview')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先评审当前前端预览；若需要继续修改，完成前端返工并重跑 frontend runtime 后再确认[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
        return False

    def _ensure_architecture_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_architecture_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成架构返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='architecture')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先更新 output/*-architecture.md，再同步调整实现方案与相关任务拆解[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]")
        return False

    def _ensure_quality_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_quality_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成质量返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='quality')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先修复质量/安全问题，重新执行 quality gate，并刷新交付证据[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]")
        return False

    def _ensure_execution_gates(self, project_dir: Path, *, action_label: str) -> bool:
        return (
            self._ensure_docs_confirmation_for_execution(project_dir, action_label=action_label)
            and self._ensure_preview_confirmation_for_execution(
                project_dir, action_label=action_label
            )
            and self._ensure_ui_revision_clear_for_execution(project_dir, action_label=action_label)
            and self._ensure_architecture_revision_clear_for_execution(
                project_dir, action_label=action_label
            )
            and self._ensure_quality_revision_clear_for_execution(
                project_dir, action_label=action_label
            )
        )

    def _cmd_task(self, args) -> int:
        """Spec 任务执行与状态查看"""
        from .creators import SpecTaskExecutor
        from .specs import ChangeManager

        project_dir = Path.cwd()
        manager = ChangeManager(project_dir)

        if args.action == "list":
            changes = manager.list_changes()
            if not changes:
                self.console.print("[dim]没有找到变更[/dim]")
                return 0
            self.console.print("[cyan]变更任务概览:[/cyan]")
            for change in changes:
                completed = sum(1 for task in change.tasks if task.status.value == "completed")
                total = len(change.tasks)
                self.console.print(
                    f"  - {change.id}: {change.status.value} | 任务 {completed}/{total}"
                )
            return 0

        if not args.change_id:
            self.console.print("[red]请提供 change_id[/red]")
            return 1

        loaded_change = manager.load_change(args.change_id)
        if not loaded_change:
            self.console.print(f"[red]变更不存在: {args.change_id}[/red]")
            return 1

        if args.action == "status":
            completed = sum(1 for task in loaded_change.tasks if task.status.value == "completed")
            in_progress = sum(
                1 for task in loaded_change.tasks if task.status.value == "in_progress"
            )
            pending = sum(1 for task in loaded_change.tasks if task.status.value == "pending")
            self.console.print(f"[cyan]任务状态: {loaded_change.id}[/cyan]")
            self.console.print(f"  标题: {loaded_change.title}")
            self.console.print(f"  状态: {loaded_change.status.value}")
            self.console.print(f"  已完成: {completed}")
            self.console.print(f"  进行中: {in_progress}")
            self.console.print(f"  待处理: {pending}")
            for task in loaded_change.tasks:
                marker = (
                    "[x]"
                    if task.status.value == "completed"
                    else "[~]" if task.status.value == "in_progress" else "[ ]"
                )
                self.console.print(f"  {marker} {task.id} {task.title}")
            return 0

        config_manager = get_config_manager()
        config_exists = config_manager.exists()
        config = config_manager.config

        tech_stack = {
            "platform": args.platform or (config.platform if config_exists else "web"),
            "frontend": args.frontend
            or (self._normalize_pipeline_frontend(config.frontend) if config_exists else "react"),
            "backend": args.backend or (config.backend if config_exists else "node"),
            "domain": (
                args.domain if args.domain is not None else (config.domain if config_exists else "")
            ),
        }

        project_name = args.project_name or (
            config.name if config_exists and config.name else args.change_id
        )

        if not self._ensure_execution_gates(project_dir, action_label="执行 Spec 任务"):
            return 1

        executor = SpecTaskExecutor(project_dir=project_dir, project_name=project_name)
        summary = executor.execute(
            change_id=args.change_id,
            tech_stack=tech_stack,
            max_retries=max(0, int(args.max_retries)),
        )

        self.console.print("[green]✓ Spec 任务执行完成[/green]")
        self.console.print(f"  变更: {summary.change_id}")
        self.console.print(f"  完成: {summary.completed_tasks}/{summary.total_tasks}")
        self.console.print(f"  报告: {summary.report_file}")
        if summary.repaired_actions:
            self.console.print(f"  自动修复: {len(summary.repaired_actions)} 项")
        if summary.failed_tasks:
            self.console.print(f"  [yellow]未完成任务: {', '.join(summary.failed_tasks)}[/yellow]")
            return 1
        return 0

    def _normalize_pipeline_frontend(self, frontend: str) -> str:
        """将 init 的前端框架映射到 pipeline 可接受值"""
        mapping = {
            "next": "react",
            "remix": "react",
            "react-vite": "react",
            "gatsby": "react",
            "nuxt": "vue",
            "vue-vite": "vue",
            "sveltekit": "svelte",
            "astro": "react",
            "solid": "react",
            "qwik": "react",
        }
        if frontend in set(SUPPORTED_PIPELINE_FRONTENDS):
            return frontend
        return mapping.get(frontend, "react")

    def _normalize_cicd_platform(self, value: str) -> CICDPlatform:
        valid = set(SUPPORTED_CICD)
        normalized = (value or "github").lower()
        if normalized not in valid:
            raise ValueError(f"不支持的 CI/CD 平台: {value}")
        return cast(CICDPlatform, normalized)

    def _validate_host_support_matrix(self) -> list[str]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        issues: list[str] = []
        integration_gaps = IntegrationManager.coverage_gaps()
        if integration_gaps.get("missing_in_targets"):
            issues.append(
                "IntegrationManager.TARGETS 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_targets"])
            )
        if integration_gaps.get("extra_in_targets"):
            issues.append(
                "IntegrationManager.TARGETS 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_targets"])
            )
        if integration_gaps.get("missing_in_slash"):
            issues.append(
                "IntegrationManager.SLASH_COMMAND_FILES 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_slash"])
            )
        if integration_gaps.get("extra_in_slash"):
            issues.append(
                "IntegrationManager.SLASH_COMMAND_FILES 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_slash"])
            )
        if integration_gaps.get("missing_in_docs_map"):
            issues.append(
                "IntegrationManager.OFFICIAL_DOCS 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_docs_map"])
            )
        if integration_gaps.get("extra_in_docs_map"):
            issues.append(
                "IntegrationManager.OFFICIAL_DOCS 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_docs_map"])
            )

        skill_gaps = SkillManager.coverage_gaps()
        if skill_gaps.get("missing_in_skill_targets"):
            issues.append(
                "SkillManager.TARGET_PATHS 缺失宿主: "
                + ", ".join(skill_gaps["missing_in_skill_targets"])
            )
        if skill_gaps.get("extra_in_skill_targets"):
            issues.append(
                "SkillManager.TARGET_PATHS 存在未声明宿主: "
                + ", ".join(skill_gaps["extra_in_skill_targets"])
            )
        return issues

    def _ensure_host_support_matrix(self) -> bool:
        issues = self._validate_host_support_matrix()
        if not issues:
            return True
        self.console.print("[red]宿主支持矩阵配置不一致，请先修复后再执行[/red]")
        for item in issues:
            self.console.print(f"  - {item}")
        return False

    def _sanitize_project_name(self, name: str) -> str:
        """清理项目名，避免路径非法字符"""
        import re

        cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name.strip())
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
        return cleaned or "my-project"

    def _pipeline_run_state_path(self, project_dir: Path) -> Path:
        return project_dir / ".super-dev" / "runs" / "last-pipeline.json"

    def _normalize_run_status(self, status: Any) -> str:
        normalized = str(status or "").strip().lower()
        if normalized in {"success", "completed"}:
            return "completed"
        if normalized in {"failed"}:
            return "failed"
        if normalized in {"cancelled"}:
            return "cancelled"
        if normalized in {
            "running",
            "cancelling",
            "waiting_confirmation",
            "waiting_preview_confirmation",
            "waiting_ui_revision",
            "waiting_architecture_revision",
            "waiting_quality_revision",
        }:
            return "running"
        if normalized in {"queued"}:
            return "queued"
        return "unknown"

    def _write_pipeline_run_state(self, project_dir: Path, payload: dict[str, Any]) -> None:
        state_file = self._pipeline_run_state_path(project_dir)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        payload_with_normalized = dict(payload)
        payload_with_normalized["status_normalized"] = self._normalize_run_status(
            payload_with_normalized.get("status")
        )
        lock_file = state_file.parent / ".runs.lock"
        lock_handle = lock_file.open("a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=state_file.parent,
                prefix=".last-pipeline.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(json.dumps(payload_with_normalized, ensure_ascii=False, indent=2))
                temp_path = Path(temp_file.name)
            os.replace(temp_path, state_file)
        finally:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
        try:
            if self._project_has_super_dev_context(project_dir):
                self._write_session_brief(
                    project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
                )
        except Exception:
            pass

    def _read_pipeline_run_state(self, project_dir: Path) -> dict[str, Any] | None:
        state_file = self._pipeline_run_state_path(project_dir)
        if not state_file.exists():
            return None
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(raw, dict):
            return None
        return raw

    def _resume_audit_paths(self, output_dir: Path, project_name: str) -> dict[str, Path]:
        return {
            "json": output_dir / f"{project_name}-resume-audit.json",
            "markdown": output_dir / f"{project_name}-resume-audit.md",
        }

    def _render_resume_audit_markdown(self, payload: dict[str, Any]) -> str:
        detected_stage = payload.get("detected_failed_stage", "")
        initial_stage = payload.get("initial_resume_stage", "")
        final_stage = payload.get("final_resume_stage", "")
        planned_skips = payload.get("planned_skipped_stages", [])
        if isinstance(planned_skips, list):
            skip_text = ", ".join(str(item) for item in planned_skips) if planned_skips else "-"
        else:
            skip_text = "-"

        lines = [
            "# Resume Audit",
            "",
            f"- Project: `{payload.get('project_name', '')}`",
            f"- Status: `{payload.get('status', '')}`",
            f"- Run state status: `{payload.get('run_state_status', '')}`",
            f"- Detected failed stage: `{detected_stage}`",
            f"- Initial resume stage: `{initial_stage}`",
            f"- Final resume stage: `{final_stage}`",
            f"- Planned skipped stages: `{skip_text}`",
            f"- Started at (UTC): `{payload.get('started_at', '')}`",
            f"- Finished at (UTC): `{payload.get('finished_at', '')}`",
        ]
        failure_reason = str(payload.get("failure_reason", "")).strip()
        if failure_reason:
            lines.append(f"- Failure reason: `{failure_reason}`")

        reasons = payload.get("fallback_reasons", [])
        lines.extend(["", "## Fallback Reasons", ""])
        if isinstance(reasons, list) and reasons:
            lines.extend([f"- {str(item)}" for item in reasons])
        else:
            lines.append("- None")

        return "\n".join(lines) + "\n"

    def _write_resume_audit(
        self,
        *,
        output_dir: Path,
        project_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        files = self._resume_audit_paths(output_dir=output_dir, project_name=project_name)
        files["json"].parent.mkdir(parents=True, exist_ok=True)
        files["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files["markdown"].write_text(self._render_resume_audit_markdown(payload), encoding="utf-8")
        return files

    def _coerce_stage_number(self, raw_stage: Any) -> int | None:
        text = str(raw_stage).strip()
        if not text.isdigit():
            return None
        return int(text)

    def _load_pipeline_metrics_payload(
        self, output_dir: Path, project_name: str
    ) -> dict[str, Any] | None:
        metrics_file = output_dir / f"{project_name}-pipeline-metrics.json"
        if not metrics_file.exists():
            return None
        try:
            payload = json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _extract_metrics_stage_details(
        self,
        metrics_payload: dict[str, Any] | None,
        stage: str,
    ) -> dict[str, Any]:
        if not isinstance(metrics_payload, dict):
            return {}
        stages = metrics_payload.get("stages", [])
        if not isinstance(stages, list):
            return {}
        for item in stages:
            if not isinstance(item, dict):
                continue
            if str(item.get("stage", "")).strip() != stage:
                continue
            details = item.get("details", {})
            if isinstance(details, dict):
                return details
            return {}
        return {}

    def _resolve_resume_start_stage(
        self, failed_stage: int | None, skip_redteam: bool
    ) -> int | None:
        """
        将失败阶段映射为安全恢复起点。

        - 0-4: 仍执行全量重跑（需要重建上下文，避免不一致）
        - 5: 直接从红队继续
        - 6: 默认回退到 5（需要 redteam_report 输入）；若本次跳过红队则可从 6 开始
        - 7-8: 直接从失败阶段恢复
        - 9-12: 统一从 9 恢复，保证后续汇总变量完整
        """
        if failed_stage is None:
            return None
        if failed_stage < 5:
            return None
        if failed_stage >= 9:
            return 9
        if failed_stage == 8:
            return 8
        if failed_stage == 7:
            return 7
        if failed_stage == 6:
            return 6 if skip_redteam else 5
        return 5

    def _stage_one_artifact_paths(self, output_dir: Path, project_name: str) -> dict[str, Path]:
        return {
            "research": output_dir / f"{project_name}-research.md",
            "prd": output_dir / f"{project_name}-prd.md",
            "architecture": output_dir / f"{project_name}-architecture.md",
            "uiux": output_dir / f"{project_name}-uiux.md",
            "execution_plan": output_dir / f"{project_name}-execution-plan.md",
            "frontend_blueprint": output_dir / f"{project_name}-frontend-blueprint.md",
        }

    def _adjust_resume_stage_for_artifacts(
        self,
        *,
        project_dir: Path,
        output_dir: Path,
        project_name: str,
        resume_from_stage: int | None,
    ) -> tuple[int | None, list[str]]:
        if resume_from_stage is None:
            return None, []

        adjusted = resume_from_stage
        reasons: list[str] = []

        # 中后段恢复依赖前置文档产物，缺失时回退到第 1 阶段重建上下文。
        if adjusted in {5, 6, 7, 8}:
            required_docs = self._stage_one_artifact_paths(
                output_dir=output_dir, project_name=project_name
            )
            missing_docs = [name for name, path in required_docs.items() if not path.exists()]
            if missing_docs:
                adjusted = 1
                reasons.append(f"缺少前置文档产物: {', '.join(missing_docs)}")

        if adjusted in {4, 5, 6, 7, 8} and not self._detect_latest_change_id(project_dir):
            adjusted = 2
            reasons.append("未检测到可用 Spec 变更目录")

        if adjusted in {4, 5, 6, 7, 8}:
            frontend_runtime_report = output_dir / f"{project_name}-frontend-runtime.json"
            if not frontend_runtime_report.exists():
                adjusted = 3
                reasons.append("缺少前端运行验证报告")

        return adjusted, reasons

    def _detect_latest_change_id(self, project_dir: Path) -> str:
        changes_dir = project_dir / ".super-dev" / "changes"
        if not changes_dir.exists():
            return ""
        change_dirs = [item for item in changes_dir.iterdir() if item.is_dir()]
        if not change_dirs:
            return ""
        latest = max(change_dirs, key=lambda item: item.stat().st_mtime)
        return latest.name

    def _extract_resume_context(
        self,
        run_state: dict[str, Any] | None,
        metrics_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if isinstance(run_state, dict):
            stored_context = run_state.get("context")
            if isinstance(stored_context, dict):
                context.update(stored_context)

        stage1_details = self._extract_metrics_stage_details(metrics_payload, "1")
        scenario = stage1_details.get("scenario")
        if "scenario" not in context and isinstance(scenario, str) and scenario in {"0-1", "1-N+1"}:
            context["scenario"] = scenario

        stage3_details = self._extract_metrics_stage_details(metrics_payload, "3")
        change_id = stage3_details.get("change_id")
        if "change_id" not in context and isinstance(change_id, str) and change_id.strip():
            context["change_id"] = change_id.strip()

        return context

    def _normalize_requirements_payload(self, raw: Any) -> list[dict[str, Any]]:
        import re

        if not isinstance(raw, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                spec_name = str(item.get("spec_name", "core")).strip() or "core"
                req_name = (
                    str(item.get("req_name") or item.get("name") or "requirement").strip()
                    or "requirement"
                )
                description = str(item.get("description", "")).strip() or req_name
                scenarios = item.get("scenarios", [])
                if not isinstance(scenarios, list):
                    scenarios = []
                normalized.append(
                    {
                        "spec_name": spec_name,
                        "req_name": req_name,
                        "description": description,
                        "scenarios": scenarios,
                    }
                )
                continue

            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                safe_name = re.sub(r"[^a-z0-9_]+", "-", text.lower()).strip("-") or "requirement"
                normalized.append(
                    {
                        "spec_name": "core",
                        "req_name": safe_name,
                        "description": text,
                        "scenarios": [],
                    }
                )

        return normalized

    def _extract_stage_artifacts(self, details: dict[str, Any]) -> list[str]:
        artifacts: list[str] = []
        seen: set[str] = set()

        def _append_if_path(value: str) -> None:
            candidate = value.strip()
            if not candidate:
                return
            path = Path(candidate)
            if not path.is_absolute():
                path = (Path.cwd() / path).resolve()
            if not path.exists():
                return
            try:
                rel = str(path.relative_to(Path.cwd()))
            except ValueError:
                rel = str(path)
            if rel in seen:
                return
            seen.add(rel)
            artifacts.append(rel)

        def _walk(value: Any) -> None:
            if isinstance(value, str):
                _append_if_path(value)
                return
            if isinstance(value, Path):
                _append_if_path(str(value))
                return
            if isinstance(value, dict):
                for item in value.values():
                    _walk(item)
                return
            if isinstance(value, list | tuple | set):
                for item in value:
                    _walk(item)

        _walk(details)
        return artifacts

    def _extract_stage_notes(self, details: dict[str, Any]) -> list[str]:
        notes: list[str] = []
        if bool(details.get("skipped", False)):
            reason = str(details.get("reason", "manual")).strip() or "manual"
            notes.append(f"skipped:{reason}")
        if "score" in details:
            notes.append(f"score={details.get('score')}")
        if "scenario" in details:
            notes.append(f"scenario={details.get('scenario')}")
        if "critical_failures" in details and isinstance(details["critical_failures"], list):
            notes.append(f"critical_failures={len(details['critical_failures'])}")
        return notes

    def _detect_failed_stage_from_metrics_payload(
        self, metrics_payload: dict[str, Any] | None
    ) -> int | None:
        if not isinstance(metrics_payload, dict):
            return None
        if bool(metrics_payload.get("success", False)):
            return None
        stages = metrics_payload.get("stages", [])
        if not isinstance(stages, list):
            return None
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if bool(stage.get("success", False)):
                continue
            parsed = self._coerce_stage_number(stage.get("stage"))
            if parsed is not None:
                return parsed
        return None

    def _detect_failed_stage(self, output_dir: Path, project_name: str) -> int | None:
        payload = self._load_pipeline_metrics_payload(
            output_dir=output_dir, project_name=project_name
        )
        return self._detect_failed_stage_from_metrics_payload(payload)

    def _run_direct_requirement(
        self, description: str, direct_overrides: dict[str, Any] | None = None
    ) -> int:
        """将 `super-dev <需求描述>` 直达路由到完整流水线"""
        if not description:
            self.console.print("[red]请提供需求描述[/red]")
            return 1

        direct_overrides = direct_overrides or {}
        config_manager = get_config_manager()
        config_exists = config_manager.exists()
        config = config_manager.config

        platform = str(
            direct_overrides.get("platform") or (config.platform if config_exists else "web")
        )
        frontend = str(
            direct_overrides.get("frontend")
            or (self._normalize_pipeline_frontend(config.frontend) if config_exists else "react")
        )
        backend = str(
            direct_overrides.get("backend") or (config.backend if config_exists else "node")
        )
        domain = str(direct_overrides.get("domain") or (config.domain if config_exists else ""))
        cicd = str(direct_overrides.get("cicd") or "all")

        if platform not in SUPPORTED_PLATFORMS:
            self.console.print(f"[red]不支持的平台: {platform}[/red]")
            return 2
        if frontend not in SUPPORTED_PIPELINE_FRONTENDS:
            self.console.print(f"[red]不支持的前端框架: {frontend}[/red]")
            return 2
        if backend not in SUPPORTED_PIPELINE_BACKENDS:
            self.console.print(f"[red]不支持的后端框架: {backend}[/red]")
            return 2
        if domain not in SUPPORTED_DOMAINS:
            self.console.print(f"[red]不支持的业务领域: {domain}[/red]")
            return 2
        if cicd not in SUPPORTED_CICD:
            self.console.print(f"[red]不支持的 CI/CD 平台: {cicd}[/red]")
            return 2

        args = argparse.Namespace(
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            name=direct_overrides.get("name"),
            cicd=cicd,
            mode=direct_overrides.get("mode", "feature"),
            skip_redteam=bool(direct_overrides.get("skip_redteam", False)),
            skip_scaffold=bool(direct_overrides.get("skip_scaffold", False)),
            skip_quality_gate=bool(direct_overrides.get("skip_quality_gate", False)),
            skip_rehearsal_verify=bool(direct_overrides.get("skip_rehearsal_verify", False)),
            offline=bool(direct_overrides.get("offline", False)),
            quality_threshold=direct_overrides.get("quality_threshold"),
            resume=False,
        )

        self.console.print("[cyan]需求直达模式：自动执行治理流水线[/cyan]")
        self._print_governance_boundary_notice(
            "该入口只负责生成治理产物与流程约束，实际编码应在宿主会话内完成。"
        )
        return self._cmd_pipeline(args)

    def _save_tech_stack_to_config(
        self, project_dir: Path, tech_stack: dict, description: str
    ) -> None:
        """保存技术栈到项目配置文件"""
        import yaml  # type: ignore[import-untyped]

        config_file = project_dir / "super-dev.yaml"

        # 读取现有配置（如果有）
        config: dict[str, Any] = {}
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        # 更新配置
        config["platform"] = tech_stack.get("platform", "web")
        config["frontend"] = tech_stack.get("frontend", "react")
        config["backend"] = tech_stack.get("backend", "node")
        config["domain"] = tech_stack.get("domain", "")
        config["description"] = description

        # 保存配置
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def _export_deploy_remediation_templates(
        self,
        project_dir: Path,
        cicd_platform: str,
        only_missing: bool = True,
    ) -> dict:
        """导出部署修复模板：环境变量示例 + secrets 检查清单。"""
        env_hints_map = {
            "github": [
                {"name": "DOCKER_USERNAME", "description": "Docker 镜像仓库用户名"},
                {"name": "DOCKER_PASSWORD", "description": "Docker 镜像仓库密码/Token"},
                {"name": "KUBE_CONFIG_DEV", "description": "开发环境 Kubernetes kubeconfig"},
                {"name": "KUBE_CONFIG_PROD", "description": "生产环境 Kubernetes kubeconfig"},
            ],
            "gitlab": [
                {"name": "CI_REGISTRY_USER", "description": "GitLab Registry 用户名"},
                {"name": "CI_REGISTRY_PASSWORD", "description": "GitLab Registry 密码/Token"},
                {"name": "KUBE_CONTEXT_DEV", "description": "开发环境 K8s 上下文"},
                {"name": "KUBE_CONTEXT_PROD", "description": "生产环境 K8s 上下文"},
            ],
            "azure": [
                {"name": "AZURE_ACR_SERVICE_CONNECTION", "description": "Azure ACR 服务连接标识"},
                {"name": "AZURE_DEV_K8S_CONNECTION", "description": "开发环境 AKS 服务连接标识"},
                {"name": "AZURE_PROD_K8S_CONNECTION", "description": "生产环境 AKS 服务连接标识"},
            ],
            "bitbucket": [
                {"name": "REGISTRY_URL", "description": "镜像仓库地址"},
                {"name": "KUBE_CONFIG_DEV", "description": "开发环境 Kubernetes kubeconfig"},
                {"name": "KUBE_CONFIG_PROD", "description": "生产环境 Kubernetes kubeconfig"},
            ],
        }
        manual_hints_map = {
            "jenkins": [
                "Jenkins Credentials: docker-credentials",
                "Jenkins Credentials: kubeconfig-dev",
                "Jenkins Credentials: kubeconfig-prod",
            ]
        }
        platform_guidance_map = {
            "github": [
                "在 GitHub Settings > Secrets and variables > Actions 配置变量。",
                "按 dev/prod 环境拆分敏感变量。",
            ],
            "gitlab": [
                "在 GitLab Settings > CI/CD > Variables 中配置变量并启用 Masked。",
            ],
            "jenkins": [
                "在 Jenkins Credentials 中创建与流水线一致的凭据 ID。",
            ],
            "azure": [
                "在 Azure DevOps 配置 Service Connection 和 Variable Group。",
            ],
            "bitbucket": [
                "在 Bitbucket Repository variables 中配置密钥。",
            ],
        }

        def _resolve_env_hints(platform: str) -> list[dict]:
            if platform == "all":
                merged = []
                seen = set()
                for item_platform in ("github", "gitlab", "azure", "bitbucket"):
                    for item in env_hints_map.get(item_platform, []):
                        if item["name"] in seen:
                            continue
                        seen.add(item["name"])
                        merged.append(item)
                return merged
            return list(env_hints_map.get(platform, []))

        def _resolve_manual_hints(platform: str) -> list[str]:
            if platform == "all":
                return list(manual_hints_map.get("jenkins", []))
            return list(manual_hints_map.get(platform, []))

        def _resolve_guidance(platform: str) -> list[str]:
            if platform == "all":
                merged = []
                seen = set()
                for item_platform in ("github", "gitlab", "jenkins", "azure", "bitbucket"):
                    for item in platform_guidance_map.get(item_platform, []):
                        if item in seen:
                            continue
                        seen.add(item)
                        merged.append(item)
                return merged
            return list(platform_guidance_map.get(platform, []))

        def _collect_items(platform: str) -> list[dict]:
            env_hints = _resolve_env_hints(platform)
            items = []
            for item in env_hints:
                name = item["name"]
                present = bool(os.getenv(name, "").strip())
                if only_missing and present:
                    continue
                items.append(
                    {
                        "name": name,
                        "description": item["description"],
                        "present": present,
                        "template": f'{name}="<value>"',
                    }
                )
            return items

        def _write_env_example(file_path: Path, platform: str, items: list[dict]) -> None:
            lines = [
                "# Super Dev Deployment Environment Template",
                f"# Platform: {platform}",
                f"# only_missing: {str(only_missing).lower()}",
                "",
            ]
            if not items:
                lines.append("# No variables to export for current filter.")
            else:
                for item in items:
                    lines.append(f"# {item['description']}")
                    lines.append(item["template"])
                    lines.append("")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        def _write_checklist(
            file_path: Path,
            platform: str,
            items: list[dict],
            manual_hints: list[str],
            platform_guidance: list[str],
        ) -> None:
            lines = [
                "# Deploy Remediation Checklist",
                "",
                f"- Platform: `{platform}`",
                f"- only_missing: `{str(only_missing).lower()}`",
                "",
                "## Environment Variables",
                "",
                "| Name | Status | Description | Template |",
                "|:---|:---:|:---|:---|",
            ]
            if items:
                for item in items:
                    status = "present" if item["present"] else "missing"
                    lines.append(
                        f"| `{item['name']}` | `{status}` | {item['description']} | `{item['template']}` |"
                    )
            else:
                lines.append("| - | - | No variables in current filter | - |")

            lines.extend(["", "## Platform Guidance", ""])
            if platform_guidance:
                lines.extend([f"- {line}" for line in platform_guidance])
            else:
                lines.append("- No guidance available.")

            lines.extend(["", "## Manual Requirements", ""])
            if manual_hints:
                lines.extend([f"- {line}" for line in manual_hints])
            else:
                lines.append("- No manual requirements.")

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        output_dir = project_dir / "output" / "deploy"
        output_dir.mkdir(parents=True, exist_ok=True)

        aggregate_items = _collect_items(cicd_platform)
        env_path = project_dir / ".env.deploy.example"
        checklist_path = output_dir / f"{cicd_platform}-secrets-checklist.md"
        _write_env_example(env_path, cicd_platform, aggregate_items)
        _write_checklist(
            checklist_path,
            cicd_platform,
            aggregate_items,
            _resolve_manual_hints(cicd_platform),
            _resolve_guidance(cicd_platform),
        )

        per_platform_files = []
        if cicd_platform == "all":
            platform_dir = output_dir / "platforms"
            for platform in ("github", "gitlab", "jenkins", "azure", "bitbucket"):
                platform_items = _collect_items(platform)
                platform_env = platform_dir / f".env.deploy.{platform}.example"
                platform_checklist = platform_dir / f"{platform}-secrets-checklist.md"
                _write_env_example(platform_env, platform, platform_items)
                _write_checklist(
                    platform_checklist,
                    platform,
                    platform_items,
                    _resolve_manual_hints(platform),
                    _resolve_guidance(platform),
                )
                per_platform_files.append(
                    {
                        "platform": platform,
                        "env_file": str(platform_env),
                        "checklist_file": str(platform_checklist),
                        "items_count": len(platform_items),
                    }
                )

        return {
            "env_file": str(env_path),
            "checklist_file": str(checklist_path),
            "items_count": len(aggregate_items),
            "per_platform_files": per_platform_files,
        }

    def _print_banner(self) -> None:
        """打印欢迎横幅"""
        if self.console:
            from rich.panel import Panel
            from rich.text import Text

            banner = Text()
            banner.append("Super Dev ", style="bold cyan")
            banner.append(f"v{__version__}\n", style="dim")
            banner.append(__description__, style="white")
            banner.append("\n宿主负责编码，Super Dev 负责治理与交付标准", style="dim")

            self.console.print(Panel.fit(banner, title="Super Dev", border_style="cyan"))

    def _print_governance_boundary_notice(self, message: str) -> None:
        if not self.console:
            return
        self.console.print(f"[dim]治理边界: {message} 宿主负责模型调用、工具使用与代码产出。[/dim]")


def main() -> int:
    """主入口"""
    from .utils.structured_logging import setup_structured_logging

    setup_structured_logging()
    cli = SuperDevCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
