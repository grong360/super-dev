"""
Super Dev CLI 集成测试
"""

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from super_dev import __version__ as _super_dev_version
from super_dev.analyzer import BaselineAuditBuilder
from super_dev.catalogs import PRIMARY_HOST_TOOL_IDS
from super_dev.cli import SuperDevCLI
from super_dev.evidence_identity import build_evidence_identity
from super_dev.hooks.manager import HookManager
from super_dev.integrations import IntegrationManager
from super_dev.review_state import (
    save_baseline_confirmation,
    save_docs_confirmation,
    save_host_runtime_validation,
    save_ui_revision,
    save_workflow_state,
)
from super_dev.skills import SkillManager
from super_dev.specs.generator import SpecGenerator
from super_dev.workflow_guard import save_bound_docs_confirmation, save_bound_preview_confirmation


def _confirm_docs(temp_project_dir: Path) -> None:
    save_docs_confirmation(
        temp_project_dir,
        {
            "status": "confirmed",
            "comment": "测试中预先确认三文档",
            "actor": "pytest",
            "run_id": "test-run",
        },
    )


def _prepare_workflow_context(project_dir: Path) -> None:
    (project_dir / "output").mkdir(parents=True, exist_ok=True)
    (project_dir / ".super-dev" / "review-state").mkdir(parents=True, exist_ok=True)
    (project_dir / "super-dev.yaml").write_text(
        "name: demo\ndescription: 商业级官网\n", encoding="utf-8"
    )
    (project_dir / ".super-dev" / "WORKFLOW.md").write_text("# workflow\n", encoding="utf-8")
    (project_dir / "output" / f"{project_dir.name}-prd.md").write_text("# prd\n", encoding="utf-8")
    (project_dir / "output" / f"{project_dir.name}-architecture.md").write_text(
        "# arch\n", encoding="utf-8"
    )
    (project_dir / "output" / f"{project_dir.name}-uiux.md").write_text(
        "# uiux\n", encoding="utf-8"
    )
    (project_dir / "output" / f"{project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "framework_playbook": {
                    "framework": "uni-app",
                    "implementation_modules": [
                        "自定义导航栏高度、状态栏占位、胶囊按钮区域必须独立建模"
                    ],
                    "platform_constraints": ["自定义导航启用后必须显式处理 status bar 与安全区"],
                    "execution_guardrails": [
                        "先冻结 pages.json / navigationStyle / provider 配置，再开始页面实现"
                    ],
                    "native_capabilities": ["登录/支付/分享 provider 必须按端隔离并显式验收"],
                    "validation_surfaces": ["微信小程序导航/支付/触控与包体策略"],
                    "delivery_evidence": ["三端差异说明与条件编译点清单"],
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    hook_history = HookManager.hook_history_file(project_dir)
    hook_history.parent.mkdir(parents=True, exist_ok=True)
    hook_history.write_text(
        json.dumps(
            {
                "hook_name": "python3 scripts/check.py",
                "event": "WorkflowEvent",
                "success": True,
                "output": "",
                "error": "",
                "duration_ms": 11.2,
                "blocked": False,
                "phase": "docs_confirmation_saved",
                "source": "config",
                "timestamp": "2026-04-06T01:02:03+00:00",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_baseline_audit(project_dir: Path, *, work_mode: str = "variant") -> None:
    (project_dir / "app").mkdir(parents=True, exist_ok=True)
    (project_dir / "components").mkdir(parents=True, exist_ok=True)
    (project_dir / "backend").mkdir(parents=True, exist_ok=True)
    package_json = project_dir / "package.json"
    if not package_json.exists():
        package_json.write_text(
            json.dumps(
                {
                    "name": project_dir.name,
                    "dependencies": {"react": "^19.0.0", "next": "^15.0.0"},
                }
            ),
            encoding="utf-8",
        )
    builder = BaselineAuditBuilder(project_dir)
    report = builder.build(work_mode_override=work_mode)
    builder.write(report)


def _prepare_release_ready_project(project_dir: Path) -> None:
    (project_dir / "super_dev").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)
    (project_dir / ".super-dev" / "changes" / "release-hardening-finalization").mkdir(
        parents=True,
        exist_ok=True,
    )
    (project_dir / "pyproject.toml").write_text(
        f'[project]\nversion = "{_super_dev_version}"\n[project.scripts]\nsuper-dev = "super_dev.cli:main"\n',
        encoding="utf-8",
    )
    (project_dir / ".gitignore").write_text(
        "\n".join(
            [
                "output/",
                "artifacts/",
                ".super-dev/runs/",
                ".super-dev/review-state/",
                "/.agent/",
                "/.claude/",
                "/.codebuddy/",
                "/.cursor/",
                "/.gemini/",
                "/.iflow/",
                "/.kimi/",
                "/.kiro/",
                "/.opencode/",
                "/.qoder/",
                "/.trae/",
                "/.factory/",
                "/.windsurf/",
                "/GEMINI.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "super_dev" / "__init__.py").write_text(
        f'__version__ = "{_super_dev_version}"\n', encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        f"当前版本：`{_super_dev_version}`\nuv tool install super-dev\n/super-dev\nsuper-dev:\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "README_EN.md").write_text(
        f"Current version: `{_super_dev_version}`\nuv tool install super-dev\n/super-dev\nsuper-dev:\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "INSTALL_OPTIONS.md").write_text(
        "uv tool install super-dev\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "HOST_USAGE_GUIDE.md").write_text(
        "Smoke\n/super-dev\nsuper-dev:\n", encoding="utf-8"
    )
    (project_dir / "docs" / "HOST_CAPABILITY_AUDIT.md").write_text(
        "官方依据\nintegrate smoke / validate\n", encoding="utf-8"
    )
    (project_dir / "docs" / "HOST_RUNTIME_VALIDATION.md").write_text(
        "host runtime validation\nresearch\nsuper-dev review docs\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "HOST_INSTALL_SURFACES.md").write_text(
        "Codex CLI\nsuper-dev:\n继续当前流程\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "README.md").write_text("用户文档\n维护者文档\n", encoding="utf-8")
    (project_dir / "docs" / "WORKFLOW_GUIDE.md").write_text(
        "super-dev review docs\n继续当前流程\n", encoding="utf-8"
    )
    (project_dir / "docs" / "WORKFLOW_GUIDE_EN.md").write_text(
        "super-dev review docs\ncontinue current workflow\n", encoding="utf-8"
    )
    (project_dir / "docs" / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
    )
    (project_dir / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    for name in ("change.yaml", "proposal.md", "tasks.md"):
        (
            project_dir / ".super-dev" / "changes" / "release-hardening-finalization" / name
        ).write_text("ok\n", encoding="utf-8")
    (project_dir / "output" / f"{project_dir.name}-redteam.json").write_text(
        json.dumps(
            {
                "project_name": project_dir.name,
                "pass_threshold": 70,
                "critical_count": 0,
                "high_count": 0,
                "total_score": 92,
                "passed": True,
                "blocking_reasons": [],
                "security_issues": [],
                "performance_issues": [],
                "architecture_issues": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-quality-gate.md").write_text(
        "# 质量门禁报告\n\n**状态**: <span style='color:green'>通过</span>\n**总分**: 90/100\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-task-execution.md").write_text(
        (
            "# Spec 任务执行报告\n\n"
            "## 执行期验证摘要\n\n"
            "- build ok\n\n"
            "## 宿主补充自检（交付前必做）\n\n"
            "- 新增函数、方法、字段、模块都已接入真实调用链\n"
        ),
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-product-audit.json").write_text(
        json.dumps({"status": "ready", "score": 90}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output_dir = project_dir / "output"
    (output_dir / f"governance-report-{project_dir.name}.md").write_text(
        "# Governance Report\n\nvalidation=PASSED\n命中率: 100%\n",
        encoding="utf-8",
    )
    (output_dir / "knowledge-cache").mkdir(parents=True, exist_ok=True)
    (output_dir / "knowledge-cache" / f"{project_dir.name}-knowledge-bundle.json").write_text(
        json.dumps(
            {"local_knowledge": [], "web_knowledge": [], "research_summary": "fixture"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "knowledge-tracking-report.md").write_text(
        "# Knowledge Tracking Report\n\n- local refs: ok\n- web refs: ok\n",
        encoding="utf-8",
    )
    (output_dir / "metrics-history").mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics-history" / f"{project_dir.name}-metrics.json").write_text(
        json.dumps(
            {"project_name": project_dir.name, "success_rate": 100}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-validation-results.json").write_text(
        json.dumps({"passed": True, "errors": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project_dir / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs" / "adr" / "ADR-001.md").write_text(
        "# ADR-001: 选择 PostgreSQL\n\n## 决策\n使用 PostgreSQL。\n",
        encoding="utf-8",
    )
    (project_dir / ".super-dev" / "decisions").mkdir(parents=True, exist_ok=True)
    (project_dir / ".super-dev" / "decisions" / "ADR-001.md").write_text(
        "# ADR-001: Delivery Closure\n\n选择 proof-pack + release readiness 作为发布闭环。\n",
        encoding="utf-8",
    )
    (output_dir / f"validation-report-{project_dir.name}.md").write_text(
        "# Validation Report\n\n- rules: passed\n",
        encoding="utf-8",
    )
    (output_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (output_dir / f"{project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "style_direction": "Editorial workspace",
                "typography": {"heading": "Space Grotesk", "body": "Inter"},
                "icon_system": "lucide-react",
                "emoji_policy": {
                    "allowed_in_ui": False,
                    "allowed_as_icon": False,
                    "allowed_during_development": False,
                },
                "ui_library_preference": {
                    "preferred": "shadcn/ui + Radix + Tailwind",
                    "strict": False,
                    "final_selected": "shadcn/ui + Radix + Tailwind",
                },
                "design_tokens": {"color": {"primary": "#0f172a"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "frontend" / "design-tokens.css").write_text(
        ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-ui-review.json").write_text(
        json.dumps({"score": 92, "critical_count": 0}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-ui-contract-alignment.json").write_text(
        json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-quality-gate.json").write_text(
        json.dumps(
            {
                "passed": True,
                "total_score": 90,
                "summary": {"executive_summary": "quality gate passed"},
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="quality-gate",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-review.json",
                        output_dir / f"{project_dir.name}-ui-contract-alignment.json",
                        output_dir / f"{project_dir.name}-uiux.md",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-frontend-runtime.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": {
                    "ui_contract_json": True,
                    "output_frontend_design_tokens": True,
                    "ui_contract_alignment": True,
                    "ui_theme_entry": True,
                    "ui_navigation_shell": True,
                    "ui_component_imports": True,
                    "ui_banned_patterns": True,
                },
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="frontend-runtime",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-contract.json",
                        output_dir / f"{project_dir.name}-ui-contract-alignment.json",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _prepare_proof_pack_project(project_dir: Path) -> None:
    _prepare_release_ready_project(project_dir)
    output_dir = project_dir / "output"
    (output_dir / "delivery").mkdir(parents=True, exist_ok=True)
    (output_dir / "rehearsal").mkdir(parents=True, exist_ok=True)
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output_dir / f"{project_dir.name}-{suffix}.md").write_text("# ok\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-frontend-runtime.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": {
                    "output_frontend_index": True,
                    "output_frontend_styles": True,
                    "output_frontend_design_tokens": True,
                    "output_frontend_script": True,
                    "preview_html": True,
                    "ui_contract_json": True,
                    "ui_contract_alignment": True,
                    "ui_theme_entry": True,
                    "ui_navigation_shell": True,
                    "ui_component_imports": True,
                    "ui_banned_patterns": True,
                },
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="frontend-runtime",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-contract.json",
                        output_dir / f"{project_dir.name}-ui-contract-alignment.json",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "style_direction": "Editorial workspace",
                "typography": {"heading": "Space Grotesk", "body": "Inter"},
                "icon_system": "lucide-react",
                "emoji_policy": {
                    "allowed_in_ui": False,
                    "allowed_as_icon": False,
                    "allowed_during_development": False,
                },
                "ui_library_preference": {
                    "preferred": "shadcn/ui + Radix + Tailwind",
                    "strict": False,
                    "final_selected": "shadcn/ui + Radix + Tailwind",
                },
                "design_tokens": {"color": {"primary": "#0f172a"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (output_dir / "frontend" / "design-tokens.css").write_text(
        ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-ui-review.json").write_text(
        json.dumps(
            {
                "score": 92,
                "critical_count": 0,
                "alignment_summary": {},
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="ui-review",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-contract.json",
                        output_dir / f"{project_dir.name}-uiux.md",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-ui-contract-alignment.json").write_text(
        json.dumps(
            {
                "ui_contract": {
                    "label": "UI 契约文件",
                    "passed": True,
                    "expected": "output/*-ui-contract.json",
                    "observed": "present",
                },
                "icon_system": {
                    "label": "图标系统",
                    "passed": True,
                    "expected": "lucide-react",
                    "observed": "lucide-react",
                },
                "font_pair": {
                    "label": "字体组合",
                    "passed": True,
                    "expected": "Space Grotesk / Inter",
                    "observed": "space grotesk, inter",
                },
                "component_ecosystem": {
                    "label": "组件生态",
                    "passed": True,
                    "expected": "shadcn/ui + Radix + Tailwind",
                    "observed": "@radix-ui, tailwindcss",
                },
                "component_imports": {
                    "label": "组件导入路径",
                    "passed": True,
                    "expected": "@/components/ui, /components/ui/, components/ui/, @radix-ui",
                    "observed": "@/components/ui/button",
                },
                "design_tokens": {
                    "label": "Design Token 接入",
                    "passed": True,
                    "expected": "design-tokens.css",
                    "observed": "wired",
                },
                "token_usage": {
                    "label": "冻结 Token 使用率",
                    "passed": True,
                    "expected": "--color-primary",
                    "observed": "--color-primary",
                },
                "theme_entry": {
                    "label": "主题入口",
                    "passed": True,
                    "expected": "全局主题入口或 design token 入口已接入",
                    "observed": "theme provider / design tokens wired",
                },
                "navigation_shell": {
                    "label": "导航骨架",
                    "passed": True,
                    "expected": "源码或预览中存在导航 / header / sidebar / breadcrumb 等骨架信号",
                    "observed": "sections=4 | nav_links=3",
                },
                "banned_patterns": {
                    "label": "反模式约束",
                    "passed": True,
                    "expected": "无 emoji 图标、无 Claude 聊天壳层、无模板化渐变/关键词",
                    "observed": "",
                },
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="ui-contract-alignment",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-contract.json",
                        output_dir / f"{project_dir.name}-uiux.md",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-quality-gate.md").write_text(
        "# quality gate\npassed\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-quality-gate.json").write_text(
        json.dumps(
            {
                "passed": True,
                "total_score": 90,
                "summary": {"executive_summary": "quality gate passed"},
                "evidence_identity": build_evidence_identity(
                    project_dir,
                    artifact_name="quality-gate",
                    dependencies=[
                        output_dir / f"{project_dir.name}-ui-review.json",
                        output_dir / f"{project_dir.name}-ui-contract-alignment.json",
                        output_dir / f"{project_dir.name}-uiux.md",
                    ],
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    # Ensure the ready fixture reflects one coherent artifact generation round.
    base_time = time.time() + 1
    for index, artifact_name in enumerate(
        (
            f"{project_dir.name}-ui-review.json",
            f"{project_dir.name}-ui-contract-alignment.json",
            f"{project_dir.name}-frontend-runtime.json",
            f"{project_dir.name}-quality-gate.md",
            f"{project_dir.name}-quality-gate.json",
        )
    ):
        ts = base_time + index
        os.utime(output_dir / artifact_name, (ts, ts))
    (output_dir / f"{project_dir.name}-redteam.json").write_text(
        json.dumps(
            {
                "project_name": project_dir.name,
                "pass_threshold": 70,
                "critical_count": 0,
                "high_count": 0,
                "total_score": 93,
                "passed": True,
                "blocking_reasons": [],
                "security_issues": [],
                "performance_issues": [],
                "architecture_issues": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-task-execution.md").write_text(
        (
            "# Spec 任务执行报告\n\n"
            "## 执行期验证摘要\n\n"
            "- build ok\n\n"
            "## 宿主补充自检（交付前必做）\n\n"
            "- 新增函数、方法、字段、模块都已接入真实调用链\n"
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-product-audit.json").write_text(
        json.dumps({"status": "ready", "score": 91}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "style_direction": "Editorial workspace",
                "typography": {"heading": "Space Grotesk", "body": "Inter"},
                "icon_system": "lucide-react",
                "emoji_policy": {
                    "allowed_in_ui": False,
                    "allowed_as_icon": False,
                    "allowed_during_development": False,
                },
                "ui_library_preference": {
                    "preferred": "shadcn/ui + Radix + Tailwind",
                    "strict": False,
                    "final_selected": "shadcn/ui + Radix + Tailwind",
                },
                "design_tokens": {"color": {"primary": "#0f172a"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (output_dir / "frontend" / "design-tokens.css").write_text(
        ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-frontend-runtime.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": {
                    "output_frontend_index": True,
                    "output_frontend_styles": True,
                    "output_frontend_design_tokens": True,
                    "output_frontend_script": True,
                    "preview_html": True,
                    "ui_contract_json": True,
                    "ui_contract_alignment": True,
                    "ui_theme_entry": True,
                    "ui_navigation_shell": True,
                    "ui_component_imports": True,
                    "ui_banned_patterns": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-prd.md").write_text(
        "\n".join(
            [
                "# PRD",
                "",
                "## 2. 功能范围",
                "",
                "### 用户登录",
                "- 支持邮箱密码登录",
                "",
                "### 运营看板",
                "- 提供运营数据概览",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "delivery" / f"{project_dir.name}-delivery-manifest.json").write_text(
        json.dumps({"status": "ready"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "rehearsal" / f"{project_dir.name}-rehearsal-report.json").write_text(
        json.dumps({"passed": True, "score": 95}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_docs_confirmation(
        project_dir,
        {
            "status": "confirmed",
            "comment": "proof pack docs confirmed",
            "actor": "pytest",
            "run_id": "proof-pack-run",
        },
    )
    save_ui_revision(
        project_dir,
        {
            "status": "confirmed",
            "comment": "ui revision closed",
            "actor": "pytest",
            "run_id": "proof-pack-run",
        },
    )
    generator = SpecGenerator(project_dir)
    generator.init_sdd()
    change = generator.create_change(
        change_id="proof-quality",
        title="Proof Quality",
        description="proof pack spec quality",
    )
    generator.scaffold_change_artifacts(change.id)
    (project_dir / ".super-dev" / "changes" / change.id / "tasks.md").write_text(
        "# Tasks\n\n- [x] 支持邮箱密码登录\n- [x] 提供运营数据概览\n",
        encoding="utf-8",
    )
    final_base_time = time.time() + 5
    for index, artifact_name in enumerate(
        (
            f"{project_dir.name}-ui-contract.json",
            f"{project_dir.name}-ui-review.json",
            f"{project_dir.name}-ui-contract-alignment.json",
            f"{project_dir.name}-frontend-runtime.json",
            f"{project_dir.name}-quality-gate.md",
        )
    ):
        ts = final_base_time + index
        os.utime(output_dir / artifact_name, (ts, ts))


class TestCLIInit:
    """测试 init 命令"""

    def test_init_creates_config(self, temp_project_dir: Path):
        """测试 init 命令创建配置文件"""
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            cli = SuperDevCLI()
            result = cli.run(["init", "test-project", "-p", "web", "-f", "next", "-b", "node"])

            assert result == 0
            config_path = temp_project_dir / "super-dev.yaml"
            assert config_path.exists()
            assert (temp_project_dir / ".super-dev" / "WORKFLOW.md").exists()
            assert (temp_project_dir / "output" / "test-project-bootstrap.md").exists()

            with open(config_path) as f:
                config = yaml.safe_load(f)
                assert config["name"] == "test-project"
                assert config["platform"] == "web"
        finally:
            os.chdir(original_cwd)

    def test_init_already_initialized(self, temp_project_dir: Path):
        """测试重复初始化"""
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            # 创建现有配置
            (Path.cwd() / "super-dev.yaml").write_text("name: existing")

            cli = SuperDevCLI()
            result = cli.run(["init", "another-project"])

            assert result == 0  # 应该优雅处理
        finally:
            os.chdir(original_cwd)


class TestCLIConfig:
    """测试 config 命令"""

    def test_config_list(self, temp_project_dir: Path, sample_config):
        """测试列出配置"""
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            # 创建配置文件 (使用当前目录的 super-dev.yaml)
            config_data = {
                "name": sample_config.name,
                "platform": sample_config.platform,
                "frontend": sample_config.frontend,
                "backend": sample_config.backend,
            }
            config_path = Path.cwd() / "super-dev.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            cli = SuperDevCLI()
            result = cli.run(["config", "list"])

            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_config_get(self, temp_project_dir: Path, sample_config):
        """测试获取配置"""
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            config_data = {"name": sample_config.name, "quality_gate": 85}
            config_path = Path.cwd() / "super-dev.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            cli = SuperDevCLI()
            result = cli.run(["config", "get", "quality_gate"])

            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_config_set(self, temp_project_dir: Path):
        """测试设置配置"""
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            config_data = {"name": "test"}
            config_path = Path.cwd() / "super-dev.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            cli = SuperDevCLI()
            result = cli.run(["config", "set", "quality_gate", "90"])

            assert result == 0

            # 验证配置已更新
            with open(config_path) as f:
                config = yaml.safe_load(f)
                assert config["quality_gate"] == 90
        finally:
            os.chdir(original_cwd)

    def test_config_set_unknown_key(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            config_path = Path.cwd() / "super-dev.yaml"
            with open(config_path, "w") as f:
                yaml.dump({"name": "test"}, f)

            cli = SuperDevCLI()
            result = cli.run(["config", "set", "unknown_key", "value"])
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_config_set_rejects_invalid_value(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            config_path = Path.cwd() / "super-dev.yaml"
            with open(config_path, "w") as f:
                yaml.dump({"name": "test"}, f)

            cli = SuperDevCLI()
            result = cli.run(["config", "set", "host_compatibility_min_score", "120"])
            assert result == 1
        finally:
            os.chdir(original_cwd)


class TestCLINextAndAudit:
    def test_next_command_json_for_uninitialized_project(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["next", "--json"])
            payload = json.loads(capsys.readouterr().out)
            assert result == 0
            assert payload["status"] == "not_initialized"
            assert payload["recommended_command"] == "super-dev"
            assert payload["current_step_label"] == "还没完成宿主接入"
            assert payload["user_next_action"] == "先把 Super Dev 装进一个宿主，并确认可以触发。"
            assert payload["preferred_host_name"]
            assert payload["host_continue_prompt"]
        finally:
            os.chdir(original_cwd)

    def test_product_audit_command(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            (temp_project_dir / "docs").mkdir(parents=True, exist_ok=True)
            (temp_project_dir / "docs" / "QUICKSTART.md").write_text(
                "super-dev update\n/super-dev 你的需求\n继续当前流程\n",
                encoding="utf-8",
            )
            (temp_project_dir / "docs" / "HOST_USAGE_GUIDE.md").write_text(
                "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n",
                encoding="utf-8",
            )
            (temp_project_dir / "docs" / "WORKFLOW_GUIDE.md").write_text(
                "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
                encoding="utf-8",
            )
            (temp_project_dir / "docs" / "PRODUCT_AUDIT.md").write_text(
                "super-dev product-audit\nproof-pack\nrelease readiness\n",
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(["product-audit"])
            assert result in (0, 1)
            assert any((temp_project_dir / "output").glob("*-product-audit.md"))
            assert any((temp_project_dir / "output").glob("*-product-audit.json"))
        finally:
            os.chdir(original_cwd)


class TestCLIReview:
    """测试 review docs 命令"""

    def test_review_docs_defaults_to_pending(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["review", "docs"])

            assert result == 0
            output = capsys.readouterr().out
            assert "三文档确认状态" in output
            assert "状态: 待确认" in output
            assert "document-confirmation.json" in output
        finally:
            os.chdir(original_cwd)

    def test_review_docs_json_persists_confirmation(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "review",
                    "docs",
                    "--status",
                    "confirmed",
                    "--comment",
                    "文档已确认，可以进入 Spec 阶段",
                    "--run-id",
                    "run-123",
                    "--actor",
                    "tester",
                    "--json",
                ]
            )

            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "confirmed"
            assert payload["comment"] == "文档已确认，可以进入 Spec 阶段"
            assert payload["run_id"] == "run-123"
            assert payload["actor"] == "tester"
            assert payload["updated_at"]

            state_file = (
                temp_project_dir / ".super-dev" / "review-state" / "document-confirmation.json"
            )
            assert state_file.exists()
            persisted = json.loads(state_file.read_text(encoding="utf-8"))
            assert persisted["status"] == "confirmed"
            assert persisted["comment"] == "文档已确认，可以进入 Spec 阶段"
            assert persisted["run_id"] == "run-123"
            assert persisted["actor"] == "tester"
        finally:
            os.chdir(original_cwd)

    def test_review_ui_defaults_to_pending(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["review", "ui"])

            assert result == 0
            output = capsys.readouterr().out
            assert "UI 改版状态" in output
            assert "状态: 待确认" in output
            assert "ui-revision.json" in output
        finally:
            os.chdir(original_cwd)

    def test_review_baseline_json_persists_confirmation(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "review",
                    "baseline",
                    "--status",
                    "confirmed",
                    "--comment",
                    "当前项目 baseline 已确认",
                    "--run-id",
                    "run-base-123",
                    "--actor",
                    "tester",
                    "--json",
                ]
            )

            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "confirmed"
            assert payload["comment"] == "当前项目 baseline 已确认"
            assert payload["run_id"] == "run-base-123"
            assert payload["actor"] == "tester"
            assert payload["updated_at"]

            state_file = (
                temp_project_dir / ".super-dev" / "review-state" / "baseline-confirmation.json"
            )
            assert state_file.exists()
            persisted = json.loads(state_file.read_text(encoding="utf-8"))
            assert persisted["status"] == "confirmed"
        finally:
            os.chdir(original_cwd)

    def test_review_baseline_prepare_generates_audit_artifacts(
        self, temp_project_dir: Path, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            (temp_project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "demo",
                        "dependencies": {"react": "^19.0.0", "next": "^15.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (temp_project_dir / "components").mkdir(parents=True, exist_ok=True)
            (temp_project_dir / "app").mkdir(parents=True, exist_ok=True)
            save_workflow_state(
                temp_project_dir,
                {
                    "status": "missing_baseline",
                    "workflow_mode": "continue",
                    "work_mode": "evolve",
                    "current_step_label": "先建立当前项目 baseline",
                    "recommended_command": "先做 baseline scan",
                },
            )

            cli = SuperDevCLI()
            result = cli.run(["review", "baseline", "--prepare", "--json"])

            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "prepared"
            assert payload["work_mode"] == "evolve"
            assert "baseline" in payload["summary"]
            assert Path(payload["file_path"]).exists()
            assert Path(payload["json_file_path"]).exists()
        finally:
            os.chdir(original_cwd)

    def test_review_ui_json_persists_revision_request(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "review",
                    "ui",
                    "--status",
                    "revision_requested",
                    "--comment",
                    "Hero 太空，需要重做首屏",
                    "--run-id",
                    "run-ui-123",
                    "--actor",
                    "tester",
                    "--json",
                ]
            )

            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "revision_requested"
            assert payload["comment"] == "Hero 太空，需要重做首屏"
            assert payload["run_id"] == "run-ui-123"
            assert payload["actor"] == "tester"
            assert payload["updated_at"]

            state_file = temp_project_dir / ".super-dev" / "review-state" / "ui-revision.json"
            assert state_file.exists()
            persisted = json.loads(state_file.read_text(encoding="utf-8"))
            assert persisted["status"] == "revision_requested"
        finally:
            os.chdir(original_cwd)

    def test_review_architecture_defaults_to_pending(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["review", "architecture"])

            assert result == 0
            output = capsys.readouterr().out
            assert "架构返工状态" in output
            assert "状态: 待确认" in output
            assert "architecture-revision.json" in output
        finally:
            os.chdir(original_cwd)

    def test_review_quality_json_persists_revision_request(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "review",
                    "quality",
                    "--status",
                    "revision_requested",
                    "--comment",
                    "质量门禁未通过，需要修复安全和质量问题",
                    "--run-id",
                    "run-quality-123",
                    "--actor",
                    "tester",
                    "--json",
                ]
            )

            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "revision_requested"
            assert payload["comment"] == "质量门禁未通过，需要修复安全和质量问题"
            state_file = temp_project_dir / ".super-dev" / "review-state" / "quality-revision.json"
            assert state_file.exists()
        finally:
            os.chdir(original_cwd)

    def test_quality_redteam_generates_reports(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            (temp_project_dir / "super-dev.yaml").write_text(
                yaml.safe_dump(
                    {
                        "name": "demo",
                        "platform": "web",
                        "frontend": "react",
                        "backend": "node",
                        "domain": "",
                    }
                ),
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(["quality", "--type", "redteam"])

            assert result in (0, 1)
            assert (temp_project_dir / "output" / "demo-redteam.md").exists()
            assert (temp_project_dir / "output" / "demo-redteam.json").exists()
        finally:
            os.chdir(original_cwd)


class TestCLIQuality:
    """测试 quality 命令"""

    def test_quality_document_check(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "demo-prd.md").write_text("# PRD", encoding="utf-8")

            cli = SuperDevCLI()
            result = cli.run(["quality", "--type", "prd"])
            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_quality_all_generates_report(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["quality", "--type", "all"])
            assert result in (0, 1)
            assert any((temp_project_dir / "output").glob("*-quality-gate.md"))
            assert any((temp_project_dir / "output").glob("*-ui-review.md"))
            assert any((temp_project_dir / "output").glob("*-ui-review.json"))
        finally:
            os.chdir(original_cwd)

    def test_quality_ui_review_generates_report(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "demo-uiux.md").write_text(
                "# demo\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n",
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            result = cli.run(["quality", "--type", "ui-review"])
            assert result in (0, 1)
            assert any((temp_project_dir / "output").glob("*-ui-review.md"))
            assert any((temp_project_dir / "output").glob("*-ui-review.json"))
        finally:
            os.chdir(original_cwd)


class TestCLIDesignInspiration:
    def test_design_list_outputs_curated_inspirations(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["design", "list", "--frontend", "react", "-n", "5"])
            assert result == 0
            output = capsys.readouterr().out
            assert "设计灵感锚点" in output
            assert "Linear" in output or "Vercel" in output
        finally:
            os.chdir(original_cwd)

    def test_design_recommend_uses_project_context(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            with open(temp_project_dir / "super-dev.yaml", "w", encoding="utf-8") as f:
                yaml.dump(
                    {
                        "name": "ops-suite",
                        "description": "构建一个企业协作 SaaS 工作台",
                        "platform": "web",
                        "frontend": "react",
                        "backend": "python",
                    },
                    f,
                    allow_unicode=True,
                )
            cli = SuperDevCLI()
            result = cli.run(["design", "recommend"])
            assert result == 0
            output = capsys.readouterr().out
            assert "设计灵感推荐" in output
            assert "Linear" in output
        finally:
            os.chdir(original_cwd)

    def test_design_recommend_accepts_minimal_config_without_schema_warning(
        self, temp_project_dir: Path, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            with open(temp_project_dir / "super-dev.yaml", "w", encoding="utf-8") as f:
                yaml.dump(
                    {
                        "name": "minimal-site",
                        "description": "商业级 SaaS 官网",
                        "frontend": "react",
                        "backend": "node",
                        "platform": "web",
                    },
                    f,
                    allow_unicode=True,
                )
            cli = SuperDevCLI()
            result = cli.run(["design", "recommend"])
            assert result == 0
            output = capsys.readouterr().out
            assert "Config schema validation warnings" not in output
            assert "设计灵感推荐" in output
        finally:
            os.chdir(original_cwd)

    def test_design_apply_updates_config_and_regenerates_uiux(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            with open(temp_project_dir / "super-dev.yaml", "w", encoding="utf-8") as f:
                yaml.dump(
                    {
                        "name": "brand-site",
                        "description": "为一个商业级 SaaS 产品生成官方网站和产品页",
                        "platform": "web",
                        "frontend": "react",
                        "backend": "node",
                    },
                    f,
                    allow_unicode=True,
                )
            cli = SuperDevCLI()
            result = cli.run(["design", "apply", "vercel"])
            assert result == 0

            config = yaml.safe_load((temp_project_dir / "super-dev.yaml").read_text(encoding="utf-8"))
            assert config["design_inspiration_slug"] == "vercel"

            output_dir = temp_project_dir / "output"
            uiux_path = output_dir / "brand-site-uiux.md"
            contract_path = output_dir / "brand-site-ui-contract.json"
            inspiration_path = output_dir / "brand-site-design-inspiration.json"

            assert uiux_path.exists()
            assert contract_path.exists()
            assert inspiration_path.exists()

            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            assert contract["selected_design_reference"]["slug"] == "vercel"
            assert contract["design_references"][0]["slug"] == "vercel"
        finally:
            os.chdir(original_cwd)


class TestCLISkillAndIntegrate:
    """测试 skill 和 integrate 命令"""

    def test_public_help_hides_retired_legacy_entrypoints(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["--help"])
            assert result == 0

            output = capsys.readouterr().out
            assert "Super Dev Public Help" in output
            assert "super-dev           打开宿主安装 / 接入引导" in output
            assert "super-dev update    更新到最新版本" in output
            assert "super-dev uninstall 完整清理宿主接入面" in output
            assert "内部维护 / 治理命令请使用: super-dev --help-all" in output
            assert "可用命令:" not in output
            for legacy_entry in ("create", "fix", "workflow", "bootstrap", "generate", "enforce"):
                assert legacy_entry not in output
        finally:
            os.chdir(original_cwd)

    def test_skill_targets(self):
        cli = SuperDevCLI()
        result = cli.run(["skill", "targets"])
        assert result == 0

    def test_help_all_internalizes_maintenance_command_index(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["--help-all"])
            assert result == 0

            output = capsys.readouterr().out
            assert "Super Dev Internal Command Index" in output
            assert "内部维护命令索引" in output
            assert "普通用户公开终端入口仍然只有 super-dev / super-dev update / super-dev" in output
            assert "uninstall" in output
            assert "setup               内部维护：一步接入安装" in output
            assert "detect              内部维护：宿主探测与兼容性报告" in output
            assert "resume              回到当前仓库的 Super Dev 流程" in output
            for hidden_entry in ("generate", "enforce", "config", "completion", "feedback", "migrate"):
                assert f"{hidden_entry} " not in output
        finally:
            os.chdir(original_cwd)

    def test_integrate_setup_qoder(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "setup", "--target", "qoder", "--force"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (temp_project_dir / ".qoder" / "rules" / "super-dev.md").exists()
            assert (temp_project_dir / ".qoder" / "skills" / "super-dev" / "SKILL.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_integrate_setup_antigravity(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "setup", "--target", "antigravity", "--force"])
            assert result == 0
            assert (temp_project_dir / "GEMINI.md").exists()
            assert (temp_project_dir / ".agent" / "workflows" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_integrate_matrix_text(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "matrix", "--target", "codex-cli"])
            assert result == 0
            output = capsys.readouterr().out
            assert "codex-cli" in output
            assert "适配模式" in output
            assert "使用模式" in output
            assert "触发命令" in output
            assert "官方文档" in output
        finally:
            os.chdir(original_cwd)

    def test_integrate_matrix_json(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "matrix", "--target", "qoder", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert isinstance(payload, dict)
            assert "profiles" in payload
            assert "docs_checks" in payload
            assert len(payload["profiles"]) == 1
            row = payload["profiles"][0]
            assert row["host"] == "qoder"
            assert row["adapter_mode"] == "native-ide-rule-file"
            assert "official_docs_url" in row
        finally:
            os.chdir(original_cwd)

    def test_integrate_harden_json(self, temp_project_dir: Path, capsys, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "harden", "--target", "codex-cli", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert isinstance(payload, dict)
            assert payload["selected_targets"] == ["codex-cli"]
            assert "hardening_results" in payload
            item = payload["hardening_results"]["codex-cli"]
            assert item["plan"]["trigger_mode"] == "text"
            assert "skill_install" in item
            assert "official_compare" in item
            assert "compatibility" in payload
            assert "official_compare_summary" in payload
            assert "host_parity_summary" in payload
            assert "host_gate_summary" in payload
            assert "host_runtime_script_summary" in payload
            assert "host_recovery_summary" in payload
            assert "host_parity_index" in payload
            assert payload["host_parity_summary"]["total"] == 1
            assert payload["host_gate_summary"]["total"] == 1
            assert payload["host_runtime_script_summary"]["total"] == 1
            assert payload["host_recovery_summary"]["total"] == 1
            assert payload["host_parity_index"]["passed"] is True
            gate = payload["host_gate_summary"]["hosts"]["codex-cli"]
            assert gate["passed"] is True
            runtime_script = payload["host_runtime_script_summary"]["hosts"]["codex-cli"]
            assert runtime_script["passed"] is True
            recovery = payload["host_recovery_summary"]["hosts"]["codex-cli"]
            assert recovery["passed"] is True
            assert recovery["recommended_commands"][0] == "super-dev"
            assert "super-dev update" in recovery["recommended_commands"]
            assert any(
                cmd.startswith("$super-dev ")
                or cmd.startswith("/super-dev ")
                or cmd.startswith("super-dev:")
                for cmd in recovery["recommended_commands"]
            )
            assert all(
                all(
                    marker not in cmd
                    for marker in ("integrate ", "skill install", "onboard --host")
                )
                for cmd in recovery["recommended_commands"]
            )
            assert "report_files" in payload
            report_files = payload["report_files"]
            for key in (
                "json",
                "markdown",
                "history_json",
                "history_markdown",
                "onepage_markdown",
                "history_onepage_markdown",
            ):
                assert Path(report_files[key]).exists()
            assert Path(report_files["history_json"]).parent.name == "host-hardening-history"
            assert Path(report_files["history_markdown"]).parent.name == "host-hardening-history"
            assert (
                Path(report_files["history_onepage_markdown"]).parent.name
                == "host-hardening-history"
            )
            assert (
                Path(report_files["json"]).read_text(encoding="utf-8")
                == Path(report_files["history_json"]).read_text(encoding="utf-8")
            )
            assert (
                Path(report_files["markdown"]).read_text(encoding="utf-8")
                == Path(report_files["history_markdown"]).read_text(encoding="utf-8")
            )
            hardening_markdown = Path(report_files["markdown"]).read_text(encoding="utf-8")
            assert "Adaptation Maturity:" in hardening_markdown
            assert "$super-dev 继续当前流程" in hardening_markdown
            assert not (fake_home / ".codex" / "AGENTS.md").exists()

            onepage_lines = Path(report_files["onepage_markdown"]).read_text(
                encoding="utf-8"
            ).splitlines()
            history_onepage_lines = Path(report_files["history_onepage_markdown"]).read_text(
                encoding="utf-8"
            ).splitlines()
            assert onepage_lines[0] == "# Host Parity Onepage"
            assert history_onepage_lines[0] == "# Host Parity Onepage"
            assert any("| codex-cli |" in line for line in onepage_lines)
            assert [
                line for line in onepage_lines if not line.startswith("- Generated At (UTC): ")
            ] == [
                line
                for line in history_onepage_lines
                if not line.startswith("- Generated At (UTC): ")
            ]
        finally:
            os.chdir(original_cwd)

    def test_integrate_harden_with_user_surfaces_writes_codex_global_agents(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "integrate",
                    "harden",
                    "--target",
                    "codex-cli",
                    "--with-user-surfaces",
                    "--json",
                ]
            )
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            item = payload["hardening_results"]["codex-cli"]
            assert "~/.codex/AGENTS.md" in item["plan"]["required_user_surfaces"]
            assert (fake_home / ".codex" / "AGENTS.md").exists()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.parametrize(
        "target, expected_file",
        [
            (name, config.files[0])
            for name, config in IntegrationManager.TARGETS.items()
            if config.files
        ],
    )
    def test_integrate_setup_each_target(
        self, temp_project_dir: Path, target: str, expected_file: str
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "setup", "--target", target, "--force"])
            assert result == 0
            assert (temp_project_dir / expected_file).exists()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.parametrize(
        "target",
        list(SkillManager.TARGET_PATHS.keys()),
    )
    def test_skill_builtin_install_each_target(
        self, temp_project_dir: Path, target: str, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            install_result = cli.run(
                [
                    "skill",
                    "install",
                    "super-dev",
                    "--target",
                    target,
                    "--name",
                    "super-dev",
                    "--force",
                ]
            )
            assert install_result == 0

            list_result = cli.run(["skill", "list", "--target", target])
            assert list_result == 0

            uninstall_result = cli.run(["skill", "uninstall", "super-dev", "--target", target])
            assert uninstall_result == 0
        finally:
            os.chdir(original_cwd)

    def test_onboard_single_host_installs_all_components(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "CLAUDE.md").exists()
            assert (temp_project_dir / ".claude" / "CLAUDE.md").exists()
            assert (temp_project_dir / ".claude" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (temp_project_dir / ".claude" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
            assert (fake_home / ".claude" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (fake_home / ".claude" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
            assert not (fake_home / ".claude" / "CLAUDE.md").exists()
            assert (temp_project_dir / ".claude" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".claude" / "commands" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / ".claude-plugin" / "marketplace.json").exists()
            assert (
                temp_project_dir / "plugins" / "super-dev-claude" / ".claude-plugin" / "plugin.json"
            ).exists()
        finally:
            os.chdir(original_cwd)

    def test_uninstall_single_host_removes_installed_surfaces(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "claude-code", "--force", "--yes"]) == 0
            assert (temp_project_dir / ".claude" / "commands" / "super-dev.md").exists()
            assert (fake_home / ".claude" / "skills" / "super-dev" / "SKILL.md").exists()

            result = cli.run(["uninstall", "--host", "claude-code", "--yes"])
            assert result == 0
            assert not (temp_project_dir / ".claude" / "commands" / "super-dev.md").exists()
            assert not (fake_home / ".claude" / "skills" / "super-dev" / "SKILL.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_uninstall_single_host_dry_run_keeps_installed_surfaces(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "claude-code", "--force", "--yes"]) == 0
            capsys.readouterr()

            result = cli.run(["uninstall", "--host", "claude-code", "--yes", "--dry-run", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "preview"
            assert payload["dry_run"] is True
            assert Path(payload["report_path"]).exists()
            assert (temp_project_dir / ".claude" / "commands" / "super-dev.md").exists()
            assert (fake_home / ".claude" / "skills" / "super-dev" / "SKILL.md").exists()
            target_payload = payload["targets"][0]
            assert target_payload["planned_surface_paths"]
            assert "super-dev" in target_payload["planned_skill_names"]
        finally:
            os.chdir(original_cwd)

    def test_uninstall_json_writes_cleanup_report(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "claude-code", "--force", "--yes"]) == 0
            capsys.readouterr()

            result = cli.run(["uninstall", "--host", "claude-code", "--yes", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            report_path = Path(payload["report_path"])
            assert report_path.exists()
            assert Path(payload["report_files"]["markdown"]).exists()
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            assert report_payload["status"] == "ok"
            assert report_payload["report_path"] == str(report_path)
            assert report_payload["report_files"]["markdown"].endswith(".md")
            assert report_payload["removed_path_count"] >= 1
        finally:
            os.chdir(original_cwd)

    def test_onboard_antigravity_defaults_to_project_surfaces_and_skill(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "antigravity", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "GEMINI.md").exists()
            assert (temp_project_dir / ".agent" / "workflows" / "super-dev.md").exists()
            assert (temp_project_dir / ".gemini" / "commands" / "super-dev.toml").exists()
            assert not (fake_home / ".gemini" / "GEMINI.md").exists()
            assert not (fake_home / ".gemini" / "commands" / "super-dev.toml").exists()
            assert (fake_home / ".gemini" / "skills" / "super-dev" / "SKILL.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_opencode_auto_refreshes_stale_contract_without_force(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert not (fake_home / ".config" / "opencode" / "AGENTS.md").exists()
            capsys.readouterr()

            stale_file = temp_project_dir / ".opencode" / "commands" / "super-dev.md"
            stale_file.write_text("# stale\n/super-dev\n", encoding="utf-8")

            result = cli.run(["onboard", "--host", "opencode", "--yes"])
            assert result == 0

            output = capsys.readouterr().out
            assert "已自动刷新" in output
            content = stale_file.read_text(encoding="utf-8")
            assert "SUPER_DEV_FLOW_CONTRACT_V1" in content
            assert "DOC_CONFIRM_GATE: required" in content
        finally:
            os.chdir(original_cwd)

    def test_onboard_trae_installs_project_rules_and_host_skill(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae").mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae" / "skills").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "trae", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / ".trae" / "project_rules.md").exists()
            assert (temp_project_dir / ".trae" / "rules.md").exists()
            assert not (fake_home / ".trae" / "user_rules.md").exists()
            assert not (fake_home / ".trae" / "rules.md").exists()
            assert (fake_home / ".trae" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".trae" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_trae_skips_compat_skill_when_surface_missing(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "trae", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / ".trae" / "project_rules.md").exists()
            assert (temp_project_dir / ".trae" / "rules.md").exists()
            assert not (fake_home / ".trae" / "user_rules.md").exists()
            assert not (fake_home / ".trae" / "rules.md").exists()
            assert not (fake_home / ".trae" / "skills" / "super-dev" / "SKILL.md").exists()
            output = capsys.readouterr().out
            assert "未检测到官方或兼容 Skill 目录" in output
        finally:
            os.chdir(original_cwd)

    def test_onboard_kimi_code_installs_agents_and_skills(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "kimi-code", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (temp_project_dir / ".kimi" / "AGENTS.md").exists()
            assert (temp_project_dir / ".kimi" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (fake_home / ".kimi" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".kimi" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_trae_solo_installs_rules_commands_and_skill(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae" / "skills").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "trae-solo", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (temp_project_dir / ".trae" / "rules" / "super-dev.md").exists()
            assert (temp_project_dir / ".trae" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".trae" / "skills" / "super-dev" / "SKILL.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_codex_cli_skips_slash_mapping(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (temp_project_dir / ".agents" / "plugins" / "marketplace.json").exists()
            assert (
                temp_project_dir / "plugins" / "super-dev-codex" / ".codex-plugin" / "plugin.json"
            ).exists()
            assert not (fake_home / ".codex" / "AGENTS.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".codex" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_codex_cli_preserves_existing_root_agents(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        agents = temp_project_dir / "AGENTS.md"
        agents.write_text(
            "# Existing Project Rules\n\n- Keep current behavior.\n", encoding="utf-8"
        )
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert result == 0
            content = agents.read_text(encoding="utf-8")
            assert "# Existing Project Rules" in content
            assert "BEGIN SUPER DEV CODEX" in content
            assert "super-dev:" in content
        finally:
            os.chdir(original_cwd)

    def test_onboard_kiro_defaults_to_project_steering_and_skill(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "kiro", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / ".kiro" / "steering" / "super-dev.md").exists()
            assert (temp_project_dir / ".kiro" / "steering" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / ".kiro" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (temp_project_dir / ".kiro" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
            assert not (fake_home / ".kiro" / "steering" / "super-dev.md").exists()
            assert (fake_home / ".kiro" / "skills" / "super-dev" / "SKILL.md").exists()
            assert (fake_home / ".kiro" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_with_user_surfaces_writes_codex_global_agents(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "onboard",
                    "--host",
                    "codex-cli",
                    "--force",
                    "--yes",
                    "--with-user-surfaces",
                ]
            )
            assert result == 0
            assert (fake_home / ".codex" / "AGENTS.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_onboard_prints_host_specific_next_steps(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "kiro-cli", "--force", "--yes"])
            assert result == 0

            output = capsys.readouterr().out
            assert "接下来这样用" in output
            assert "Kiro CLI" in output
            assert "/super-dev 你的需求" in output
            assert "比赛流第一句" in output
        finally:
            os.chdir(original_cwd)

    def test_onboard_default_output_is_compact(self, temp_project_dir: Path, monkeypatch, capsys):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert result == 0
            output = capsys.readouterr().out
            assert "集成规则:" in output
            assert "集成规则: /" not in output
            assert str(temp_project_dir / "CLAUDE.md") not in output
        finally:
            os.chdir(original_cwd)

    def test_onboard_writes_smoke_guide_reports(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert result == 0
            output = capsys.readouterr().out
            assert "Onboard smoke guide:" in output
            report_dir = temp_project_dir / "output" / "maintenance"
            json_reports = sorted(report_dir.glob("host-onboard-smoke-*.json"))
            markdown_reports = sorted(report_dir.glob("host-onboard-smoke-*.md"))
            assert json_reports
            assert markdown_reports
            payload = json.loads(json_reports[-1].read_text(encoding="utf-8"))
            assert payload["status"] == "ok"
            assert payload["targets"][0]["standard_flow_first_prompt"]
            assert payload["targets"][0]["post_onboard_self_check"]
            markdown = markdown_reports[-1].read_text(encoding="utf-8")
            assert "Host Onboard Smoke Guide" in markdown
            assert "Official Workflow Checks" in markdown
        finally:
            os.chdir(original_cwd)

    def test_onboard_smoke_guide_includes_framework_coaching(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{temp_project_dir.name}-ui-contract.json").write_text(
            json.dumps(
                {
                    "framework_playbook": {
                        "framework": "expo",
                        "implementation_modules": ["app router", "native auth"],
                        "native_capabilities": ["camera", "push notifications"],
                        "validation_surfaces": ["ios preview", "android preview"],
                        "delivery_evidence": ["expo preview", "device screenshots"],
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert result == 0
            _ = capsys.readouterr().out
            report_dir = temp_project_dir / "output" / "maintenance"
            markdown_reports = sorted(report_dir.glob("host-onboard-smoke-*.md"))
            json_reports = sorted(report_dir.glob("host-onboard-smoke-*.json"))
            assert markdown_reports and json_reports
            markdown = markdown_reports[-1].read_text(encoding="utf-8")
            payload = json.loads(json_reports[-1].read_text(encoding="utf-8"))
            assert "## 框架焦点（Framework Coaching Focus）" in markdown
            assert "### Framework Coaching" in markdown
            assert "Framework: expo" in markdown
            assert payload["framework_playbook"]["framework"] == "expo"
            assert payload["targets"][0]["framework_playbook"]["framework"] == "expo"
        finally:
            os.chdir(original_cwd)

    def test_onboard_detail_output_includes_written_paths(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--host", "claude-code", "--force", "--yes", "--detail"])
            assert result == 0
            output = capsys.readouterr().out
            assert "集成规则:" in output
            assert str(temp_project_dir / "CLAUDE.md") in output
            assert str(temp_project_dir / ".claude" / "skills" / "super-dev" / "SKILL.md") in output
        finally:
            os.chdir(original_cwd)

    def test_onboard_yes_defaults_to_all_targets(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["onboard", "--yes", "--force", "--skip-skill"])
            assert result == 0
            assert (temp_project_dir / "GEMINI.md").exists()
            assert (temp_project_dir / ".agent" / "workflows" / "super-dev.md").exists()
            assert (temp_project_dir / ".gemini" / "commands" / "super-dev.toml").exists()
            assert (temp_project_dir / ".gemini" / "commands" / "super-dev-seeai.toml").exists()
            assert (temp_project_dir / "CLAUDE.md").exists()
            assert (temp_project_dir / ".claude" / "CLAUDE.md").exists()
            assert (temp_project_dir / ".claude-plugin" / "marketplace.json").exists()
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (temp_project_dir / ".qoder" / "rules" / "super-dev.md").exists()
            assert (temp_project_dir / ".qoder" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".qoder" / "commands" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / ".kiro" / "steering" / "super-dev.md").exists()
            assert (temp_project_dir / ".kiro" / "steering" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / "CODEBUDDY.md").exists()
            assert (temp_project_dir / ".codebuddy" / "rules" / "super-dev" / "RULE.mdc").exists()
            assert (temp_project_dir / ".claude" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".claude" / "commands" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / ".github" / "copilot-instructions.md").exists()
            assert (temp_project_dir / ".cursor" / "rules" / "super-dev.mdc").exists()
            assert (temp_project_dir / ".cursor" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".windsurf" / "rules" / "super-dev.md").exists()
            assert (temp_project_dir / ".windsurf" / "workflows" / "super-dev.md").exists()
            assert (temp_project_dir / ".windsurf" / "workflows" / "super-dev-seeai.md").exists()
            assert (temp_project_dir / ".opencode" / "commands" / "super-dev.md").exists()
            assert (temp_project_dir / ".kimi" / "AGENTS.md").exists()
            assert (temp_project_dir / ".trae" / "commands" / "super-dev.md").exists()
            assert not (temp_project_dir / ".kimi" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_detect_host_targets_uses_windows_env_candidates(
        self, temp_project_dir: Path, monkeypatch
    ):
        localapp = temp_project_dir / "LocalAppData"
        target = localapp / "Programs" / "Trae" / "Trae.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        monkeypatch.setenv("LOCALAPPDATA", str(localapp))

        cli = SuperDevCLI()
        detected, details = cli._detect_host_targets(available_targets=["trae"])
        assert detected == ["trae"]
        assert any(item.startswith("path:") for item in details["trae"])

    def test_detect_host_targets_uses_explicit_host_path_override(
        self, temp_project_dir: Path, monkeypatch
    ):
        custom_dir = temp_project_dir / "custom-hosts"
        target = custom_dir / "CodexCustom.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        monkeypatch.setenv("SUPER_DEV_HOST_PATH_CODEX_CLI", str(target))

        cli = SuperDevCLI()
        detected, details = cli._detect_host_targets(available_targets=["codex-cli"])
        assert detected == ["codex-cli"]
        assert any(item.startswith("env:") for item in details["codex-cli"])

    def test_onboard_auto_detects_targets_from_path(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["onboard", "--auto", "--yes", "--force"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".codex" / "commands" / "super-dev.md").exists()
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_doctor_reports_not_ready_then_ready(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            before = cli.run(["doctor", "--host", "claude-code"])
            assert before == 1

            onboard = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert onboard == 0

            after = cli.run(["doctor", "--host", "claude-code"])
            assert after == 0
        finally:
            os.chdir(original_cwd)

    def test_doctor_prints_usage_guidance_for_codex_cli(self, temp_project_dir: Path, capsys):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(fake_home)
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["doctor", "--host", "codex-cli", "--repair", "--force", "--detail"])
            assert result == 0

            output = capsys.readouterr().out
            assert "主入口" in output
            assert "super-dev: <需求描述>" in output
            assert "使用模式: agents-and-skill" in output
            assert "触发位置" in output
            assert "接入后重启: 是" in output
            assert "Smoke 验收语句" in output
            assert "SMOKE_OK" in output
            assert "系统建议动作:" in output
            assert "重开后第一句直接复制 $super-dev " in output
            assert "如果你是在继续已有流程" in output
            assert "宿主第一句: $super-dev " in output
            assert "CLI 恢复入口:" in output
            assert "流程状态卡: " in output
            assert (
                "系统建议动作: 在宿主里确认三文档；如果通过，直接说“文档确认，可以继续”" in output
            )
        finally:
            if original_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_home
            os.chdir(original_cwd)

    def test_doctor_prints_multiple_host_precondition_items_for_codex(
        self, temp_project_dir: Path, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(fake_home)
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["doctor", "--host", "codex-cli", "--repair", "--force", "--detail"])
            assert result == 0

            output = capsys.readouterr().out
            assert "宿主前置条件" in output
            assert "接入后需重开宿主会话" in output
            assert "需在目标项目/工作区内触发" in output
            assert "关闭旧会话并新开一个宿主会话" in output
        finally:
            if original_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_home
            os.chdir(original_cwd)

    def test_doctor_json_includes_runtime_install_health(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli,
                "_collect_runtime_install_health",
                lambda: {
                    "healthy": False,
                    "current_version": "2.1.6",
                    "current_module_path": "/tmp/super_dev/__init__.py",
                    "installed_dist_version": "2.1.6",
                    "warnings": ["检测到多个 editable 安装记录并存: 2.0.12, 2.1.6"],
                    "remediation": [
                        "清理旧的 __editable__.super_dev-*.pth 和 finder 文件后重新安装。"
                    ],
                },
            )
            result = cli.run(["doctor", "--host", "codex-cli", "--repair", "--force", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["runtime_install_health"]["healthy"] is False
            assert payload["runtime_install_health"]["current_version"] == "2.1.6"
            assert payload["runtime_install_health"]["warnings"]
            assert payload["hosts"]["codex-cli"]["diagnosis"]["suggested_command"]
            assert payload["decision_card"]["scenario"] in {
                "no-host-detected",
                "single-host-detected",
                "multi-host-detected",
            }
            assert payload["primary_repair_action"]["command"]
            assert isinstance(payload["primary_repair_action"]["secondary_actions"], list)
        finally:
            os.chdir(original_cwd)

    def test_doctor_surfaces_runtime_governance_summary_when_layered_gap_exists(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            save_workflow_state(
                temp_project_dir,
                {
                    "status": "missing_frontend",
                    "workflow_mode": "continue",
                    "current_step_label": "先做前端与运行验证",
                    "recommended_command": "继续当前流程，进入前端实现与运行验证",
                },
            )
            save_host_runtime_validation(
                temp_project_dir,
                {
                    "hosts": {
                        "codex-cli": {
                            "status": "passed",
                            "comment": "manual accepted",
                            "actor": "pytest",
                        }
                    }
                },
            )

            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
            capsys.readouterr()

            result = cli.run(["doctor", "--host", "codex-cli", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            runtime_governance = payload["runtime_governance_summary"]
            assert "codex-cli" in runtime_governance["summary"]
            assert "continuity / harness / runtime 证据仍未闭环" in runtime_governance["summary"]
            assert runtime_governance["next_actions"]

            result = cli.run(["doctor", "--host", "codex-cli", "--detail"])
            assert result == 0
            output = capsys.readouterr().out
            assert "运行治理提示" in output
            assert "codex-cli" in output
            assert "建议先做:" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_surfaces_compliance_governance_summary_when_artifact_gap_exists(
        self, temp_project_dir: Path, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            (temp_project_dir / "output" / "demo-prd.md").write_text(
                "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            assert cli.run(["doctor", "--host", "claude-code", "--json"]) == 1
            payload = json.loads(capsys.readouterr().out)
            compliance_governance = payload["compliance_governance_summary"]
            assert "spec=missing" in compliance_governance["summary"]

            result = cli.run(["doctor", "--host", "claude-code", "--detail"])
            assert result == 1
            output = capsys.readouterr().out
            assert "合规治理提示" in output
            assert "spec=missing" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_auto_json_is_valid_json_without_preamble(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = f"{bin_dir}:{original_path}"

            cli = SuperDevCLI()
            result = cli.run(["doctor", "--auto", "--json"])
            assert result == 1
            payload = json.loads(capsys.readouterr().out)
            assert "compatibility" in payload
            assert "codex-cli" in payload["hosts"]
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_doctor_auto_json_prefers_install_action_when_no_host_detected(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            monkeypatch.setenv("PATH", str(temp_project_dir / "empty-bin"))
            monkeypatch.setattr(cli, "_detect_host_targets", lambda available_targets: ([], {}))

            result = cli.run(["doctor", "--auto", "--json"])
            assert result == 1

            payload = json.loads(capsys.readouterr().out)
            assert payload["decision_card"]["scenario"] == "no-host-detected"
            assert payload["primary_repair_action"]["host"] == "当前机器"
            assert (
                payload["primary_repair_action"]["command"]
                == payload["decision_card"]["first_action"]
            )
            assert (
                payload["primary_repair_action"]["secondary_actions"]
                == payload["decision_card"]["secondary_actions"]
            )
            assert payload["decision_card"]["next_actions"][0] == payload["decision_card"][
                "first_action"
            ]
            assert payload["decision_card"]["secondary_actions"] == payload["decision_card"][
                "next_actions"
            ][1:]
        finally:
            os.chdir(original_cwd)

    def test_doctor_default_output_is_compact(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["doctor", "--host", "claude-code"])
            assert result == 1
            output = capsys.readouterr().out
            assert ("已检测到宿主" in output) or ("未检测到可用宿主" in output)
            assert "兼容性评分" in output
            assert "使用 --detail 查看路径、协议、前置条件与逐项建议" in output
            assert "认证分布" not in output
            assert "宿主前置条件" not in output
            assert "官方 commands + subagents" not in output
            assert "原因:" in output
            assert "建议动作:" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_default_output_explains_runtime_env_mismatch(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli,
                "_collect_runtime_install_health",
                lambda: {
                    "healthy": False,
                    "current_version": "2.1.6",
                    "current_module_path": "/tmp/super_dev/__init__.py",
                    "installed_dist_version": "2.1.6",
                    "warnings": ["检测到多个 super-dev dist-info 版本并存: 2.1.2, 2.1.6"],
                    "remediation": ["清理旧的 super_dev-*.dist-info 残留，只保留当前版本。"],
                },
            )
            result = cli.run(["doctor", "--host", "claude-code"])
            assert result == 1
            output = capsys.readouterr().out
            assert "通常不是必须和 Python 装在同一盘" in output
            assert "Python 不在同一环境" in output
            assert "加 --detail 可查看模块路径、残留版本与修复建议" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_detail_output_expands_sections(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["doctor", "--host", "claude-code", "--detail"])
            assert result == 1
            output = capsys.readouterr().out
            assert "认证分布" in output
            assert "宿主前置条件" in output
            assert "宿主协议" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_accepts_global_slash_mapping_when_project_slash_missing(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            fake_home = temp_project_dir / "fake-home"
            fake_home.mkdir(parents=True, exist_ok=True)
            monkeypatch.setenv("HOME", str(fake_home))

            cli = SuperDevCLI()
            onboard = cli.run(
                ["onboard", "--host", "claude-code", "--force", "--yes", "--with-user-surfaces"]
            )
            assert onboard == 0

            project_slash = temp_project_dir / ".claude" / "commands" / "super-dev.md"
            assert project_slash.exists()
            project_slash.unlink()

            global_slash = fake_home / ".claude" / "commands" / "super-dev.md"
            assert global_slash.exists()

            result = cli.run(["doctor", "--host", "claude-code"])
            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_doctor_accepts_codex_compatibility_skill_when_official_skill_missing(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert onboard == 0

            official_skill = fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md"
            assert official_skill.exists()
            # Codex mirror removed — only official path should exist
            compatibility_skill = fake_home / ".codex" / "skills" / "super-dev" / "SKILL.md"
            assert not compatibility_skill.exists()
            official_skill.unlink()

            result = cli.run(["doctor", "--host", "codex-cli"])
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_doctor_repair_fixes_host_issues(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            before = cli.run(["doctor", "--host", "codex-cli"])
            assert before == 1

            repaired = cli.run(["doctor", "--host", "codex-cli", "--repair", "--force"])
            assert repaired == 0

            assert (temp_project_dir / "AGENTS.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".codex" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_doctor_flags_stale_contract_content(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "claude-code", "--force", "--yes"])
            assert onboard == 0

            stale_file = temp_project_dir / ".claude" / "commands" / "super-dev.md"
            stale_file.write_text("# stale\n/super-dev\n", encoding="utf-8")

            result = cli.run(["doctor", "--host", "claude-code"])
            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_detect_json_outputs_compatibility_summary(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["detect", "--json", "--auto"])
            assert result == 0

            out = capsys.readouterr().out
            payload = json.loads(out)
            assert "detected_hosts" in payload
            assert "selected_targets" in payload
            assert "compatibility" in payload
            assert "codex-cli" in payload["detected_hosts"]
            assert "命令命中" in payload["detection_details_pretty"]["codex-cli"][0]
            assert payload["decision_card"]["scenario"] in {
                "single-host-detected",
                "multi-host-detected",
            }
            assert payload["decision_card"]["selection_source"] == "detected"
            assert payload["decision_card"]["selected_host"] == "codex-cli"
            assert payload["decision_card"]["recommended_reason"]
            assert payload["decision_card"]["first_action"]
            assert payload["decision_card"]["candidates"][0]["id"] == "codex-cli"
            assert payload["decision_card"]["candidates"][0]["recommended"] is True
            assert payload["decision_card"]["candidates"][0]["adaptation_contract"]["level"] == "elite"
            assert payload["decision_card"]["candidates"][0]["primary_entry"]
            assert payload["decision_card"]["candidates"][0]["usage_mode"] == "agents-and-skill"
            assert payload["compatibility"]["total_hosts"] >= 1
            assert "flow_consistent_hosts" in payload["compatibility"]
            assert "flow_consistency_score" in payload["compatibility"]
            assert payload["usage_profiles"]["codex-cli"]["usage_mode"] == "agents-and-skill"
            assert payload["usage_profiles"]["codex-cli"]["certification_level"] == "certified"
            assert payload["usage_profiles"]["codex-cli"]["certification_label"] == "Certified"
            assert (
                payload["usage_profiles"]["codex-cli"]["path_override"]["env_key"]
                == "SUPER_DEV_HOST_PATH_CODEX_CLI"
            )
            assert (
                payload["usage_profiles"]["codex-cli"]["trigger_command"] == "super-dev: <需求描述>"
            )
            assert (
                payload["usage_profiles"]["codex-cli"]["final_trigger"]
                == "CLI: $super-dev | 回退: super-dev: 你的需求"
            )
            assert payload["usage_profiles"]["codex-cli"]["entry_variants"][0]["entry"] == "$super-dev"
            assert any(
                item["entry"] == "super-dev: <需求描述>"
                for item in payload["usage_profiles"]["codex-cli"]["entry_variants"]
            )
            assert payload["usage_profiles"]["codex-cli"]["host_protocol_mode"] == "official-skill"
            assert (
                payload["usage_profiles"]["codex-cli"]["host_protocol_summary"]
                == "官方 AGENTS.md + Skills + CLI $skill entry"
            )
            assert (
                payload["usage_profiles"]["codex-cli"]["flow_contract"]["consistent_flow_required"]
                is True
            )
            assert payload["usage_profiles"]["codex-cli"]["flow_contract"][
                "preferred_entry_order"
            ] == ["cli", "fallback"]
            assert (
                "同一条 Super Dev 流程"
                in payload["usage_profiles"]["codex-cli"]["flow_contract"]["summary"]
            )
            assert payload["usage_profiles"]["codex-cli"]["flow_probe"]["enabled"] is True
            assert payload["usage_profiles"]["codex-cli"]["adaptation_contract"]["level"] == "elite"
            assert (
                payload["usage_profiles"]["codex-cli"]["adaptation_contract"][
                    "supports_slash_entry"
                ]
                is False
            )
            assert payload["adaptation_contracts"]["codex-cli"]["level"] == "elite"
            assert payload["selected_host_adaptation"]["level"] == "elite"
            assert len(payload["usage_profiles"]["codex-cli"]["flow_probe"]["steps"]) >= 3
            assert (
                ".agents/plugins/marketplace.json"
                in payload["usage_profiles"]["codex-cli"]["optional_project_surfaces"]
            )
            assert (
                "plugins/super-dev-codex/.codex-plugin/plugin.json"
                in payload["usage_profiles"]["codex-cli"]["optional_project_surfaces"]
            )
            assert "SMOKE_OK" in payload["usage_profiles"]["codex-cli"]["smoke_test_prompt"]
            assert (
                "SEEAI_SMOKE_OK"
                in payload["usage_profiles"]["codex-cli"]["competition_smoke_test_prompt"]
            )
            assert len(payload["usage_profiles"]["codex-cli"]["competition_smoke_suite"]) >= 4
            assert payload["usage_profiles"]["codex-cli"]["competition_smoke_suite"][0][
                "trigger"
            ].startswith("$super-dev-seeai")
            assert any(
                "12 分钟内是否出现第一个可见" in item
                for item in payload["usage_profiles"]["codex-cli"]["competition_acceptance_gates"]
            )
            assert (
                payload["usage_profiles"]["codex-cli"]["competition_evidence_template"][
                    "first_response"
                ]["required"][0]
                == "作品类型"
            )
            assert payload["usage_profiles"]["codex-cli"]["smoke_test_steps"]
            assert payload["session_resume_cards"]["codex-cli"]["enabled"] is False
            assert (
                payload["report"]["hosts"]["codex-cli"]["usage_profile"][
                    "requires_restart_after_onboard"
                ]
                is True
            )
            assert payload["report"]["hosts"]["codex-cli"]["usage_profile"]["certification_reason"]
            assert "report_files" in payload
            report_files = payload["report_files"]
            assert Path(report_files["json"]).exists()
            assert Path(report_files["markdown"]).exists()
            assert Path(report_files["history_json"]).exists()
            assert Path(report_files["history_markdown"]).exists()
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_detect_prints_human_detection_source_for_override(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            custom_dir = temp_project_dir / "custom-hosts"
            target = custom_dir / "CodexCustom.exe"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            monkeypatch.setenv("PATH", str(temp_project_dir / "empty-bin"))
            monkeypatch.setenv("SUPER_DEV_HOST_PATH_CODEX_CLI", str(target))

            cli = SuperDevCLI()
            result = cli.run(["detect", "--auto", "--no-save"])
            assert result == 0

            output = capsys.readouterr().out
            assert "自定义路径覆盖" in output
            assert "Codex" in output
        finally:
            os.chdir(original_cwd)

    def test_detect_no_save_skips_report_files(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["detect", "--json", "--no-save"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert "report_files" not in payload
            assert not any((temp_project_dir / "output").glob("*-host-compatibility.json"))
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_detect_save_profile_updates_super_dev_yaml(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["detect", "--json", "--save-profile", "--auto"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload.get("host_profile_updated") is True

            config_file = temp_project_dir / "super-dev.yaml"
            assert config_file.exists()
            config_data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            assert config_data.get("host_profile_enforce_selected") is True
            assert "codex-cli" in config_data.get("host_profile_targets", [])
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_detect_prints_usage_guidance_for_detected_host(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["detect", "--auto", "--no-save"])
            assert result == 0

            output = capsys.readouterr().out
            assert "已检测到宿主" in output
            assert "主入口" in output
            assert "适配成熟度:" in output
            assert "适配维度:" in output
            assert "官方 AGENTS.md + Skills + CLI $skill entry" in output
            assert "触发命令: super-dev: <需求描述>" in output
            assert "触发位置" in output
            assert "接入后重启: 是" in output
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_detect_with_workflow_context_exposes_resume_card(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_cmd = bin_dir / "codex"
            codex_cmd.write_text("#!/usr/bin/env sh\necho codex\n", encoding="utf-8")
            codex_cmd.chmod(0o755)
            os.environ["PATH"] = str(bin_dir)

            cli = SuperDevCLI()
            result = cli.run(["detect", "--json", "--auto", "--no-save"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            decision_card = payload["decision_card"]
            resume_card = payload["session_resume_cards"]["codex-cli"]
            workflow_context = payload["workflow_context"]
            assert decision_card["selected_host"] == "codex-cli"
            assert decision_card["workflow_mode"] == "continue"
            assert workflow_context == decision_card["workflow_context"]
            assert decision_card["session_resume_card"]["enabled"] is True
            assert (
                decision_card["session_resume_card"]["host_first_sentence"]
                == resume_card["host_first_sentence"]
            )
            assert decision_card["action_title"] == resume_card["action_title"]
            assert decision_card["action_examples"] == resume_card["action_examples"]
            assert decision_card["first_action"].endswith(resume_card["host_first_sentence"])
            assert any(
                line == f"继续当前流程第一句: {resume_card['host_first_sentence']}"
                for line in decision_card["lines"]
            )
            assert resume_card["enabled"] is True
            assert resume_card["workflow_mode"] == "revise"
            assert resume_card["workflow_mode_label"] == "返工/补充当前流程"
            assert "这里补一下" in resume_card["action_examples"]
            assert "这里补一下" in resume_card["user_action_shortcuts"]
            assert resume_card["preferred_entry"] == "cli"
            assert resume_card["preferred_entry_label"] == "CLI"
            assert resume_card["host_first_sentence"].startswith("$super-dev ")
            assert resume_card["entry_prompts"]["cli"].startswith("$super-dev ")
            assert resume_card["entry_prompts"]["fallback"].startswith("super-dev:")
            assert "super-dev create" not in resume_card["host_first_sentence"]
            assert "super-dev fix" not in resume_card["host_first_sentence"]
            assert "super-dev workflow" not in resume_card["host_first_sentence"]
            assert ".super-dev/SESSION_BRIEF.md" in resume_card["session_brief_path"]
            assert ".super-dev/workflow-state.json" in resume_card["workflow_state_path"]
            assert ".super-dev/workflow-events.jsonl" in resume_card["workflow_event_log_path"]
            assert ".super-dev/hook-history.jsonl" in resume_card["hook_history_path"]
            assert resume_card["recommended_workflow_command"]
            scenario_ids = [item["id"] for item in resume_card["scenario_cards"]]
            assert scenario_ids[:2] == ["resume_workday", "know_next"]
            assert "existing_project_baseline" in scenario_ids
            assert "current_gate_or_stage" in scenario_ids
            assert any(
                item["cli_command"] == "回到宿主里说“继续当前流程，不要重新开题”"
                for item in resume_card["scenario_cards"]
            )
            assert resume_card["framework_playbook"]["framework"] == "uni-app"
            assert resume_card["operational_harnesses"]
            assert resume_card["operational_focus"]["status"] == "needs_attention"
            assert resume_card["operational_focus"]["kind"] == "framework"
            assert {item["kind"] for item in resume_card["operational_harnesses"]} == {
                "workflow",
                "framework",
                "hooks",
            }
            assert resume_card["recent_snapshots"]
            assert resume_card["recent_events"]
            assert resume_card["recent_hook_events"]
            assert resume_card["recent_snapshots"][0]["current_step_label"] == "等待三文档确认"
            assert any(
                "provider" in item
                for item in resume_card["framework_playbook"]["native_capabilities"]
            )
            assert any("框架专项: uni-app" in line for line in resume_card["lines"])
            assert any("最近一次:" in line for line in resume_card["lines"])
            assert any("最近事件:" in line for line in resume_card["lines"])
            assert any("最近 Hook:" in line for line in resume_card["lines"])
            assert any("Workflow Continuity:" in line for line in resume_card["lines"])
            assert any("当前治理焦点:" in line for line in resume_card["lines"])
            assert any("建议先做:" in line for line in resume_card["lines"])
            assert all("super-dev create" not in item for item in resume_card["action_examples"])
            assert all("super-dev fix" not in item for item in resume_card["action_examples"])
            assert all("super-dev workflow" not in item for item in resume_card["action_examples"])
            baseline_card = next(
                item for item in resume_card["scenario_cards"] if item["id"] == "existing_project_baseline"
            )
            assert baseline_card["title"] == "当前项目不是从零开始，先做 baseline"
            assert "1-N+1" in baseline_card["when"]
            assert "建立 baseline" in baseline_card["cli_command"]
            assert resume_card["workflow_context"]["baseline_required"] is False
            assert resume_card["workflow_context"]["baseline_audit_status"] == "not_required"
            assert resume_card["workflow_context"]["baseline_confirmation_status"] == "not_required"
            assert resume_card["workflow_context"]["blocking_gate"] == "waiting_docs_confirmation"
            assert resume_card["workflow_context"]["recommended_host_action"] == "$super-dev 继续当前流程"
            assert resume_card["workflow_context"]["recommended_host_sentence"] == "super-dev: 继续当前流程"
            assert resume_card["workflow_context"]["can_resume"] is True
            assert resume_card["workflow_context"]["can_progress"] is False
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_doctor_with_baseline_confirmation_context_exposes_mature_resume_language(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            _write_baseline_audit(temp_project_dir, work_mode="variant")
            save_workflow_state(temp_project_dir, {"work_mode": "variant"})
            save_baseline_confirmation(
                temp_project_dir,
                {
                    "status": "pending_review",
                    "comment": "先确认当前项目边界和差量计划",
                    "actor": "pytest",
                },
            )

            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
            capsys.readouterr()

            result = cli.run(["doctor", "--host", "codex-cli", "--json"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            decision_card = payload["decision_card"]
            card = decision_card["session_resume_card"]
            assert decision_card["workflow_mode"] == "continue"
            assert "继续当前流程第一句:" in "\n".join(decision_card["lines"])
            assert any("先确认 baseline" in line for line in decision_card["lines"])
            assert any("Baseline 已识别:" in line for line in decision_card["lines"])
            assert any("复用面:" in line for line in decision_card["lines"])
            assert "baseline 确认" in decision_card["first_action"]
            assert decision_card["workflow_context"] == card["workflow_context"]
            assert decision_card["baseline_summary"] == card["baseline_summary"]
            assert decision_card["baseline_audit_path"] == card["baseline_audit_path"]
            assert decision_card["baseline_reuse_surfaces"] == card["baseline_reuse_surfaces"]
            assert card["baseline_summary"]
            assert card["baseline_audit_path"].endswith("-baseline-audit.json")
            assert card["baseline_reuse_surfaces"]
            assert card["workflow_context"]["baseline_required"] is True
            assert card["workflow_context"]["baseline_audit_status"] == "ready"
            assert card["workflow_context"]["baseline_confirmation_status"] == "pending_review"
            assert card["workflow_context"]["blocking_gate"] == "waiting_baseline_confirmation"
            assert (
                card["workflow_context"]["recommended_host_action"]
                == "$super-dev baseline 确认，可以继续当前流程"
            )
            assert (
                card["workflow_context"]["recommended_host_sentence"]
                == "super-dev: baseline 确认，可以继续当前流程"
            )
            assert card["workflow_context"]["can_progress"] is False
        finally:
            os.chdir(original_cwd)

    def test_integrate_smoke_outputs_codex_acceptance(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["integrate", "smoke", "--target", "codex-cli"])
            assert result == 0

            output = capsys.readouterr().out
            assert "Super Dev 宿主 Smoke 验收" in output
            assert "codex-cli" in output
            assert "SMOKE_OK" in output
            assert "最终输入:" in output
            assert "CLI: $super-dev" in output
            assert "$super-dev" in output
        finally:
            os.chdir(original_cwd)

    def test_integrate_audit_flags_stale_surface(self, temp_project_dir: Path, monkeypatch, capsys):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert onboard == 0
            capsys.readouterr()

            agents_file = temp_project_dir / "AGENTS.md"
            agents_file.write_text("# stale\nsuper-dev:\n", encoding="utf-8")

            result = cli.run(["integrate", "audit", "--target", "codex-cli"])
            assert result == 1

            output = capsys.readouterr().out
            assert "Super Dev 宿主 Surface 审计" in output
            assert "codex-cli" in output
            assert "过期/缺失的接入面" in output
            assert "project:AGENTS.md" in output
        finally:
            os.chdir(original_cwd)

    def test_integrate_audit_json_repairs_and_writes_report(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(
                ["integrate", "audit", "--target", "codex-cli", "--repair", "--force", "--json"]
            )
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["report"]["overall_ready"] is True
            assert payload["compatibility"]["hosts"]["codex-cli"]["ready"] is True
            assert (
                payload["usage_profiles"]["codex-cli"]["final_trigger"]
                == "CLI: $super-dev | 回退: super-dev: 你的需求"
            )
            report_files = payload["report_files"]
            assert report_files["json"].endswith("-host-surface-audit.json")
            assert Path(report_files["json"]).exists()
            assert Path(report_files["markdown"]).exists()
            assert Path(report_files["history_json"]).exists()
            assert Path(report_files["history_markdown"]).exists()
            assert Path(report_files["history_json"]).parent.name == "host-surface-audit-history"
            assert (
                Path(report_files["json"]).read_text(encoding="utf-8")
                == Path(report_files["history_json"]).read_text(encoding="utf-8")
            )
            markdown = Path(report_files["markdown"]).read_text(encoding="utf-8")
            history_markdown = Path(report_files["history_markdown"]).read_text(
                encoding="utf-8"
            )
            assert markdown == history_markdown
            assert markdown.startswith("# Host Surface Audit Report\n")
            assert "codex-cli" in markdown
        finally:
            os.chdir(original_cwd)

    def test_integrate_audit_repair_refreshes_stale_contract_content(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert onboard == 0
            capsys.readouterr()

            agents_file = temp_project_dir / "AGENTS.md"
            agents_file.write_text("# stale\nsuper-dev:\n", encoding="utf-8")

            result = cli.run(
                ["integrate", "audit", "--target", "codex-cli", "--repair", "--force", "--json"]
            )
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["report"]["hosts"]["codex-cli"]["ready"] is True
            refreshed = agents_file.read_text(encoding="utf-8")
            assert "research" in refreshed
            assert "output/*-prd.md" in refreshed
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_json_emits_runtime_matrix(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert onboard == 0
            capsys.readouterr()

            result = cli.run(["integrate", "validate", "--target", "codex-cli", "--json"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_targets"] == ["codex-cli"]
            report_files = payload["report_files"]
            assert report_files["json"].endswith("-host-runtime-validation.json")
            assert Path(report_files["json"]).exists()
            assert Path(report_files["markdown"]).exists()
            assert Path(report_files["history_json"]).exists()
            assert Path(report_files["history_markdown"]).exists()
            assert (
                Path(report_files["history_json"]).parent.name
                == "host-runtime-validation-history"
            )
            assert (
                Path(report_files["json"]).read_text(encoding="utf-8")
                == Path(report_files["history_json"]).read_text(encoding="utf-8")
            )
            assert (
                Path(report_files["markdown"]).read_text(encoding="utf-8")
                == Path(report_files["history_markdown"]).read_text(encoding="utf-8")
            )
            assert len(payload["hosts"]) == 1
            host = payload["hosts"][0]
            assert host["host"] == "codex-cli"
            assert host["surface_ready"] is True
            assert (
                host["final_trigger"]
                == "CLI: $super-dev | 回退: super-dev: 你的需求"
            )
            assert (
                host["host_protocol_summary"]
                == "官方 AGENTS.md + Skills + CLI $skill entry"
            )
            assert host["manual_runtime_status"] == "pending"
            assert host["repo_probe"]["status"] == "pending"
            assert host["competition_evidence_ready"] is False
            assert "first_response" in host["competition_evidence_missing"]
            assert (
                host["runtime_evidence"]["integration_status"]["status"]
                == "project_and_global_installed"
            )
            assert host["runtime_evidence"]["runtime_status"]["status"] == "pending"
            assert host["runtime_checklist"]
            assert host["pass_criteria"]
            assert host["checks"]["plugin_enhancement"]["ok"] is True
            assert any("重开 codex" in item for item in host["runtime_checklist"])
            assert any(".agents/skills/super-dev" in item for item in host["runtime_checklist"])
            assert any(
                ".agents/plugins/marketplace.json" in item for item in host["runtime_checklist"]
            )
            assert any(
                "Codex CLI 当前终端就在目标项目目录" in item for item in host["runtime_checklist"]
            )
            assert any(
                "12 分钟内先跑出第一个可见、可点击、可截图的界面" in item
                for item in host["runtime_checklist"]
            )
            assert any("$super-dev" in item for item in host["runtime_checklist"])
            assert any(".agents/skills/super-dev" in item for item in host["pass_criteria"])
            assert any("官方 Skills" in item for item in host["pass_criteria"])
            assert any("$super-dev" in item for item in host["pass_criteria"])
            assert any("回退栈" in item for item in host["pass_criteria"])
            assert host["flow_probe"]["enabled"] is True
            assert any("$super-dev" in item for item in host["flow_probe"]["steps"])
            assert host["resume_probe_prompt"] == ""
            assert host["resume_checklist"]
            assert payload["summary"]["repo_probe_pending_count"] == 1
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_with_workflow_context_emits_resume_probe_prompt(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
            capsys.readouterr()

            assert cli.run(["integrate", "validate", "--target", "codex-cli", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            host = payload["hosts"][0]
            assert ".super-dev/SESSION_BRIEF.md" in host["resume_probe_prompt"]
            assert host["resume_probe_prompt"].startswith("$super-dev ")
            assert any("新会话里恢复" in item for item in host["resume_checklist"])
            assert any("同一条 Super Dev 流程" in item for item in host["resume_checklist"])
            assert host["framework_playbook"]["framework"] == "uni-app"
            assert any(
                "provider" in item for item in host["framework_playbook"]["native_capabilities"]
            )
            assert any("uni-app playbook" in item for item in host["runtime_checklist"])
            assert any("框架专项原生能力面" in item for item in host["runtime_checklist"])
            assert any("框架专项必验场景" in item for item in host["runtime_checklist"])
            assert any("跨平台框架专项能力" in item for item in host["pass_criteria"])
            assert any("uni-app 的专项 playbook" in item for item in host["resume_checklist"])
            assert payload["workflow_context"]["blocking_gate"] == "waiting_docs_confirmation"
            assert payload["baseline_governance"]["entry_gate"] == "ready"
            assert host["repo_probe"]["workflow_context"]["blocking_gate"] == "waiting_docs_confirmation"
            assert host["repo_probe"]["workflow_context"]["recommended_host_action"] == "$super-dev 继续当前流程"
            assert host["repo_probe"]["baseline_governance"]["entry_gate"] == "ready"
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_codebuddy_exposes_seeai_runtime_validation(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "codebuddy", "--force", "--yes"]) == 0
            capsys.readouterr()
            assert cli.run(["integrate", "validate", "--target", "codebuddy", "--json"]) == 0
            host = json.loads(capsys.readouterr().out)["hosts"][0]
            assert any(
                "/super-dev-seeai" in item or "super-dev-seeai:" in item
                for item in host["runtime_checklist"]
            )
            assert any("30 分钟比赛链路" in item for item in host["runtime_checklist"])
            assert any(
                "12 分钟内先跑出第一个可见、可点击、可截图的界面" in item
                for item in host["runtime_checklist"]
            )
            assert any("SEEAI" in item for item in host["pass_criteria"])
            assert any("回退栈" in item for item in host["pass_criteria"])
            assert host["flow_probe"]["enabled"] is True
            assert any("/super-dev-seeai" in item for item in host["flow_probe"]["steps"])
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_marks_repo_probe_failure_as_delivery_blocker(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            save_workflow_state(
                temp_project_dir,
                {
                    "status": "waiting_docs_confirmation",
                    "workflow_mode": "continue",
                    "current_step_label": "等待三文档确认",
                    "recommended_command": "文档确认，可以继续",
                },
            )
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
            capsys.readouterr()

            assert (
                cli.run(
                    [
                        "integrate",
                        "validate",
                        "--target",
                        "opencode",
                        "--status",
                        "passed",
                        "--comment",
                        "manual accepted",
                        "--competition-evidence-json",
                        json.dumps(
                            {
                                "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
                                "runtime_checkpoint": {
                                    "summary": "12 分钟内首个可见界面 + 主路径首个点击动作 + 真实启动模块"
                                },
                                "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
                                "demo_path": {
                                    "summary": "30-60 秒主演示路径 + 结果页/结束态 + wow 点截图"
                                },
                            },
                            ensure_ascii=False,
                        ),
                        "--json",
                    ]
                )
                == 0
            )
            capsys.readouterr()

            assert cli.run(["integrate", "validate", "--target", "opencode", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            host = payload["hosts"][0]
            assert host["repo_probe"]["status"] == "failed"
            assert host["ready_for_delivery"] is False
            assert "所需仓库级连续性证据不完整" in host["blocking_reason"]
            assert "确认三文档" in host["recommended_action"] or "review docs" in host["recommended_action"]
            assert payload["summary"]["repo_probe_failed_count"] == 1
            assert payload["summary"]["fully_ready_count"] == 0
            assert payload["blockers"][0]["type"] == "repo_probe"

            markdown = Path(payload["report_files"]["markdown"]).read_text(encoding="utf-8")
            assert "Repo Probe Failed: 1" in markdown
            assert "Repo Probe: 仓库级 probe 失败" in markdown
            assert "### Repo Probe Blockers" in markdown
            assert "### Repo Probe Next Actions" in markdown
        finally:
            os.chdir(original_cwd)

    @pytest.mark.parametrize(
        ("host_id", "expected_runtime_hint", "expected_resume_hint"),
        [
            (
                "antigravity",
                "当前 Antigravity Prompt / Agent Chat 绑定的是目标项目",
                "重新打开的 Prompt / Agent Chat",
            ),
            (
                "codebuddy-cli",
                "当前 CodeBuddy CLI 会话就在目标项目目录中",
                "重新加载 `.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/` 与 `.codebuddy/agents/`",
            ),
            (
                "kiro-cli",
                "当前 Kiro CLI 会话就在目标项目目录",
                "再次加载 AGENTS.md、`.kiro/steering/` 与 skills",
            ),
            (
                "qoder-cli",
                "当前 Qoder CLI 会话就在目标项目目录",
                "再次加载 `.qoder/rules/`、commands 与 skills",
            ),
            ("cline", "当前 Cline 聊天面板绑定的是目标工作区", "重新读取 `.clinerules/`"),
            (
                "trae",
                "当前 Trae Agent Chat 绑定的是目标项目工作区",
                "重新读取 `.trae/project_rules.md`",
            ),
        ],
    )
    def test_integrate_validate_more_hosts_expose_host_specific_recovery_checks(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
        host_id: str,
        expected_runtime_hint: str,
        expected_resume_hint: str,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", host_id, "--force", "--yes"]) == 0
            capsys.readouterr()

            assert cli.run(["integrate", "validate", "--target", host_id, "--json"]) == 0
            host = json.loads(capsys.readouterr().out)["hosts"][0]
            assert any(expected_runtime_hint in item for item in host["runtime_checklist"])
            assert ".super-dev/SESSION_BRIEF.md" in host["resume_probe_prompt"]
            assert any(expected_resume_hint in item for item in host["resume_checklist"])
        finally:
            os.chdir(original_cwd)

    @pytest.mark.parametrize(
        ("host_id", "expected_start_line"),
        [
            ("kimi-code", "起手建议: 中文项目优先用 /skill:super-dev"),
            ("droid-cli", "起手建议: 优先留在当前 Factory session"),
            ("claude-code", "起手建议: 优先在当前 Claude Code 会话里直接用 /super-dev"),
        ],
    )
    def test_integrate_validate_flagship_hosts_expose_host_specific_start_playbook(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
        host_id: str,
        expected_start_line: str,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", host_id, "--force", "--yes"]) == 0
            capsys.readouterr()

            assert cli.run(["integrate", "validate", "--target", host_id, "--json"]) == 0
            host = json.loads(capsys.readouterr().out)["hosts"][0]
            assert any(expected_start_line in item for item in host["runtime_checklist"])
            assert host["injection_closure"]["scope"] == "project-first"
            assert host["injection_closure"]["project_default_ready"] is True
            assert host["ready_for_standard_flow"] is True
            if host_id == "kimi-code":
                assert (
                    host["injection_closure"]["status"]
                    == "project_default_ready_with_user_opt_in_available"
                )
                assert host["ready_for_competition_flow"] is True
                assert any("/skill:super-dev" in item for item in host["runtime_checklist"])
                assert any("官方工作流面" in item for item in host["pass_criteria"])
            if host_id == "droid-cli":
                assert (
                    host["injection_closure"]["status"]
                    == "project_default_ready_with_user_opt_in_available"
                )
                assert host["ready_for_competition_flow"] is True
                assert any(".factory/rules" in item for item in host["runtime_checklist"])
                assert any("官方工作流面" in item for item in host["pass_criteria"])
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_status_roundtrip(self, temp_project_dir: Path, monkeypatch, capsys):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"])
            assert onboard == 0
            capsys.readouterr()

            result = cli.run(
                [
                    "integrate",
                    "validate",
                    "--target",
                    "codex-cli",
                    "--status",
                    "passed",
                    "--comment",
                    "首轮先进入 research，三文档已真实落盘",
                    "--json",
                ]
            )
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["manual_runtime_status"] == "passed"
            assert payload["manual_runtime_status_label"] == "已真人通过"
            assert payload["repo_probe"]["status"] == "pending"
            assert payload["runtime_evidence"]["runtime_status"]["status"] == "passed"
            assert payload["competition_evidence_ready"] is False
            assert "first_response" in payload["competition_evidence_missing"]
            assert payload["updated_at"]

            result = cli.run(["integrate", "validate", "--target", "codex-cli", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            host = payload["hosts"][0]
            assert host["integration_status"] == "project_and_global_installed"
            assert host["runtime_status"] == "passed"
            assert host["runtime_status_label"] == "已真人通过"
            assert host["manual_runtime_status"] == "passed"
            assert host["manual_runtime_status_label"] == "已真人通过"
            assert host["manual_runtime_comment"] == "首轮先进入 research，三文档已真实落盘"
            assert host["manual_runtime_updated_at"]
            assert host["repo_probe"]["status"] == "pending"
            assert host["competition_evidence_ready"] is False
            assert "first_response" in host["competition_evidence_missing"]
            assert host["ready_for_delivery"] is False
            assert host["blocking_reason"] == "SEEAI 比赛验收证据不完整"
            assert (
                host["runtime_evidence"]["integration_status"]["status"]
                == "project_and_global_installed"
            )
            assert host["runtime_evidence"]["runtime_status"]["status"] == "passed"
            assert host["runtime_evidence"]["competition_evidence_ready"] is False
            assert (temp_project_dir / ".super-dev" / "install-manifest.json").exists()

            result = cli.run(
                [
                    "integrate",
                    "validate",
                    "--target",
                    "codex-cli",
                    "--status",
                    "passed",
                    "--comment",
                    "补齐比赛验收证据",
                    "--competition-evidence-json",
                    json.dumps(
                        {
                            "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
                            "runtime_checkpoint": {
                                "summary": "12 分钟内首个可见界面 + 主路径首个点击动作 + 真实启动模块"
                            },
                            "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
                            "demo_path": {
                                "summary": "30-60 秒主演示路径 + 结果页/结束态 + wow 点截图"
                            },
                        },
                        ensure_ascii=False,
                    ),
                    "--json",
                ]
            )
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["competition_evidence_ready"] is True

            result = cli.run(["integrate", "validate", "--target", "codex-cli", "--json"])
            assert result == 0
            payload = json.loads(capsys.readouterr().out)
            host = payload["hosts"][0]
            assert host["competition_evidence_ready"] is True
            assert host["competition_evidence_missing"] == []
            assert host["ready_for_delivery"] is True
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_text_writes_runtime_matrix_report(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae").mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae" / "skills").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            onboard = cli.run(["onboard", "--host", "trae", "--force", "--yes"])
            assert onboard == 0
            capsys.readouterr()

            result = cli.run(["integrate", "validate", "--target", "trae"])
            assert result == 0

            output = capsys.readouterr().out
            assert "Super Dev 宿主运行时验收矩阵" in output
            assert "trae" in output
            assert "运行时检查清单" in output
            assert "通过标准" in output
            assert "验收矩阵报告" in output

            json_reports = list(
                (temp_project_dir / "output").glob("*-host-runtime-validation.json")
            )
            md_reports = list((temp_project_dir / "output").glob("*-host-runtime-validation.md"))
            assert json_reports
            assert md_reports
        finally:
            os.chdir(original_cwd)

    def test_integrate_validate_text_with_workflow_context_prints_resume_probe(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
            capsys.readouterr()

            assert cli.run(["integrate", "validate", "--target", "opencode"]) == 0
            output = capsys.readouterr().out
            assert "继续当前流程:" in output
            assert "流程状态卡: " in output
            assert "恢复探针:" in output
            assert ".super-dev/SESSION_BRIEF.md" in output
            assert "跨平台框架专项: uni-app" in output
            assert "原生能力面:" in output
            assert "必验场景:" in output
            assert "恢复检查清单" in output
            md_reports = list((temp_project_dir / "output").glob("*-host-runtime-validation.md"))
            assert md_reports
            markdown = md_reports[0].read_text(encoding="utf-8")
            assert "Workflow Context:" in markdown
            assert "Baseline Governance:" in markdown
            assert "### Framework Playbook" in markdown
            assert "- Framework: uni-app" in markdown
            assert "### Workflow Context" in markdown
            assert "### Baseline Governance" in markdown
            assert "Native Capabilities:" in markdown
            assert "Validation Surfaces:" in markdown
        finally:
            os.chdir(original_cwd)

    def test_start_json_prefers_certified_slash_host(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for command in ("claude", "codex"):
                cmd_file = bin_dir / command
                cmd_file.write_text("#!/usr/bin/env sh\necho host\n", encoding="utf-8")
                cmd_file.chmod(0o755)
            os.environ["PATH"] = f"{bin_dir}:{original_path}"

            cli = SuperDevCLI()
            result = cli.run(
                [
                    "start",
                    "--json",
                    "--skip-onboard",
                    "--idea",
                    "做一个商业级官网",
                ]
            )
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_host"] == "claude-code"
            assert payload["decision_card"]["scenario"] == "multi-host-detected"
            assert payload["decision_card"]["selection_source"] == "explicit"
            assert any("起手建议:" in item for item in payload["decision_card"]["lines"])
            assert any("官方补充检查:" in item for item in payload["decision_card"]["lines"])
            assert payload["selected_host_experience"]["start_playbook"]
            assert payload["selected_host_post_onboard_self_check"]
            assert payload["selected_host_start_playbook"]
            assert payload["selected_host_standard_flow_first_prompt"]
            assert payload["selected_host_competition_flow_first_prompt"]
            assert payload["selected_host_resume_guidance"]
            assert payload["selected_host_injection_closure"]
            assert payload["selected_host_ready_for_standard_flow"] is False
            assert payload["selected_host_ready_for_competition_flow"] is False
            assert payload["selected_host_standard_flow_label"]
            assert payload["selected_host_competition_flow_label"]
            assert payload["selected_host_official_workflow_checks"]
            assert payload["selected_host_repair_playbook"]
            assert any(
                "super-dev-seeai" in item
                for item in payload["selected_host_post_onboard_self_check"]
            )
            assert payload["decision_card"]["selected_host"] == "claude-code"
            assert payload["decision_card"]["recommended_reason"]
            assert payload["decision_card"]["first_action"]
            assert payload["decision_card"]["secondary_actions"]
            assert payload["decision_card"]["selected_host_standard_flow_first_prompt"]
            assert payload["decision_card"]["selected_host_competition_flow_first_prompt"]
            assert (
                payload["decision_card"]["selected_path_override"]["env_key"]
                == "SUPER_DEV_HOST_PATH_CLAUDE_CODE"
            )
            assert payload["decision_card"]["candidates"][0]["id"] == "claude-code"
            assert payload["decision_card"]["candidates"][0]["recommended"] is True
            assert (
                payload["decision_card"]["candidates"][0]["path_override"]["env_key"]
                == "SUPER_DEV_HOST_PATH_CLAUDE_CODE"
            )
            assert len(payload["decision_card"]["candidates"]) >= 2
            assert payload["usage_profile"]["certification_level"] == "certified"
            assert payload["usage_profile"]["host_protocol_mode"] == "official-skill"
            assert payload["selected_host_experience"]["tier"] == "flagship"
            assert payload["selected_host_experience"]["native_resume"]
            assert (
                payload["usage_profile"]["host_protocol_summary"]
                == "官方 CLAUDE.md + settings + project/user skills + subagents"
            )
            assert payload["usage_profile"]["final_trigger"] == "/super-dev 你的需求"
            assert payload["recommended_trigger"].startswith("/super-dev ")

            config_data = yaml.safe_load(
                (temp_project_dir / "super-dev.yaml").read_text(encoding="utf-8")
            )
            assert config_data["host_profile_targets"] == ["claude-code"]
            assert config_data["host_profile_enforce_selected"] is True
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_start_json_exposes_framework_coaching_focus(
        self, temp_project_dir: Path, capsys
    ):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{temp_project_dir.name}-ui-contract.json").write_text(
                json.dumps(
                    {
                        "framework_playbook": {
                            "framework": "tauri",
                            "implementation_modules": ["desktop shell", "ipc bridge"],
                            "validation_surfaces": ["macOS windowing", "Windows signing"],
                            "delivery_evidence": ["desktop screenshots", "signed bundle notes"],
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            cmd_file = bin_dir / "claude"
            cmd_file.write_text("#!/usr/bin/env sh\necho host\n", encoding="utf-8")
            cmd_file.chmod(0o755)
            os.environ["PATH"] = f"{bin_dir}:{original_path}"

            cli = SuperDevCLI()
            result = cli.run(["start", "--json", "--skip-onboard", "--idea", "做一个桌面工具"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_host_framework_playbook"]["framework"] == "tauri"
            assert "当前项目框架焦点：tauri" in payload["quick_start"]
            assert "macOS windowing" in payload["quick_start"]
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_start_json_trims_candidate_preview_for_multi_host_detection(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli,
                "_detect_host_targets",
                lambda available_targets: (
                    ["claude-code", "codex-cli", "opencode", "cursor", "gemini-cli"],
                    {
                        "claude-code": ["cmd:claude"],
                        "codex-cli": ["cmd:codex"],
                        "opencode": ["cmd:opencode"],
                        "cursor": ["path:/Applications/Cursor.app"],
                        "gemini-cli": ["cmd:gemini"],
                    },
                ),
            )

            result = cli.run(["start", "--json", "--skip-onboard"])
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            decision_card = payload["decision_card"]
            assert decision_card["scenario"] == "multi-host-detected"
            assert decision_card["candidate_count"] == 5
            assert len(decision_card["candidates"]) == 3
            assert decision_card["remaining_candidate_count"] == 2
            assert decision_card["candidates"][0]["recommended"] is True
            assert decision_card["candidates"][0]["injection_closure"]
            assert decision_card["candidates"][0]["ready_for_standard_flow"] is False
            assert decision_card["candidates"][0]["ready_for_competition_flow"] is False
            assert decision_card["candidates"][0]["standard_flow_label"]
            assert decision_card["candidates"][0]["competition_flow_label"]
            assert decision_card["candidates"][0]["readiness_summary"]
            assert decision_card["candidates"][0]["first_action"]
            assert decision_card["candidates"][0]["start_playbook"]
            assert decision_card["candidates"][0]["standard_flow_first_prompt"]
            assert decision_card["candidates"][0]["competition_flow_first_prompt"]
            assert decision_card["candidates"][0]["resume_guidance"]
            assert decision_card["candidates"][0]["official_workflow_checks"]
            assert decision_card["candidates"][0]["repair_playbook"]
            assert any("候选准备度:" in item for item in decision_card["lines"])
            assert payload["selected_host_experience"]["tier"]
        finally:
            os.chdir(original_cwd)

    def test_start_json_reports_recommended_hosts_when_none_detected(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            monkeypatch.setenv("PATH", str(temp_project_dir / "empty-bin"))
            monkeypatch.setattr(
                "super_dev.cli_host_ops_mixin.host_detection_path_candidates",
                lambda _target: [],
            )
            cli = SuperDevCLI()
            result = cli.run(["start", "--json", "--skip-onboard"])
            assert result == 1

            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "error"
            assert payload["reason"] == "no-host-detected"
            assert "SUPER_DEV_HOST_PATH_CODEX_CLI" in payload["path_override_hint"]
            assert payload["decision_card"]["scenario"] == "no-host-detected"
            assert payload["decision_card"]["recommended_reason"]
            assert payload["decision_card"]["first_action"]
            assert payload["decision_card"]["next_actions"]
            assert payload["decision_card"]["next_actions"][0] == payload["decision_card"][
                "first_action"
            ]
            assert payload["decision_card"]["secondary_actions"] == payload["decision_card"][
                "next_actions"
            ][1:]
            assert payload["decision_card"]["path_override_examples"][0]["env_key"]
            recommended_ids = {item["id"] for item in payload["recommended_hosts"]}
            assert {"claude-code", "codex-cli"}.issubset(recommended_ids)
        finally:
            os.chdir(original_cwd)

    def test_update_check_reports_latest_version(self, capsys, monkeypatch):
        cli = SuperDevCLI()

        class DummyResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"info": {"version": "2.1.1"}}

        monkeypatch.setattr("super_dev.cli.requests.get", lambda *args, **kwargs: DummyResponse())

        result = cli.run(["update", "--check"])
        assert result == 0
        output = capsys.readouterr().out
        assert "当前版本" in output
        assert "PyPI 最新版本" in output
        assert "2.1.1" in output

    def test_update_uses_uv_when_requested(self, capsys, monkeypatch):
        cli = SuperDevCLI()
        calls: list[list[str]] = []

        class DummyResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"info": {"version": "2.1.1"}}

        monkeypatch.setattr("super_dev.cli.requests.get", lambda *args, **kwargs: DummyResponse())

        def fake_run(command, check=False):
            calls.append(command)
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr("super_dev.cli.subprocess.run", fake_run)

        result = cli.run(["update", "--method", "uv"])
        assert result == 0
        assert calls[0] == ["uv", "tool", "upgrade", "super-dev"]
        assert calls[1] == ["super-dev", "migrate"]
        output = capsys.readouterr().out
        assert "升级方式" in output
        assert "uv" in output

    def test_update_uses_pip_when_requested(self, capsys, monkeypatch):
        cli = SuperDevCLI()
        calls: list[list[str]] = []

        class DummyResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"info": {"version": "2.1.1"}}

        monkeypatch.setattr("super_dev.cli.requests.get", lambda *args, **kwargs: DummyResponse())

        def fake_run(command, check=False):
            calls.append(command)
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr("super_dev.cli.subprocess.run", fake_run)

        result = cli.run(["update", "--method", "pip"])
        assert result == 0
        assert calls[0] == [os.sys.executable, "-m", "pip", "install", "-U", "super-dev"]
        assert calls[1] == ["super-dev", "migrate"]

    def test_setup_host_runs_onboard_and_doctor(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["setup", "--host", "codex-cli", "--force"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".codex" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_install_host_runs_setup_flow(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["install", "--host", "codex-cli", "--force", "--yes"])
            assert result == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert (fake_home / ".agents" / "skills" / "super-dev" / "SKILL.md").exists()
            assert not (temp_project_dir / ".codex" / "commands" / "super-dev.md").exists()
        finally:
            os.chdir(original_cwd)


class TestCLITask:
    """测试 task 命令"""

    def test_task_run_status_and_list(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            changes_dir = temp_project_dir / ".super-dev" / "changes" / "demo-change"
            changes_dir.mkdir(parents=True, exist_ok=True)
            (changes_dir / "change.yaml").write_text(
                (
                    "id: demo-change\n"
                    "title: Demo Change\n"
                    "status: proposed\n"
                    "created_at: 2026-03-02T00:00:00\n"
                    "updated_at: 2026-03-02T00:00:00\n"
                ),
                encoding="utf-8",
            )
            (changes_dir / "tasks.md").write_text(
                (
                    "# Tasks\n\n"
                    "## 1. Frontend\n\n"
                    "- [ ] **1.1: 实现 auth 前端模块**\n\n"
                    "## 2. Backend\n\n"
                    "- [ ] **2.1: 实现 auth 后端能力**\n\n"
                    "## 4. Testing\n\n"
                    "- [ ] **4.1: 执行质量门禁前检查**\n"
                ),
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            run_result = cli.run(["task", "run", "demo-change", "--backend", "python"])
            assert run_result == 0
            assert (temp_project_dir / "output" / "demo-change-task-execution.md").exists()

            status_result = cli.run(["task", "status", "demo-change"])
            assert status_result == 0

            list_result = cli.run(["task", "list"])
            assert list_result == 0
        finally:
            os.chdir(original_cwd)


class TestCLIPipeline:
    """测试完整流水线关键产物"""

    def test_no_args_enters_install_guide(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            called: dict[str, bool] = {"value": False}

            def fake_cmd_install(args):
                called["value"] = True
                return 0

            monkeypatch.setattr(cli, "_cmd_install", fake_cmd_install)
            assert cli.run([]) == 0
            assert called["value"] is True
        finally:
            os.chdir(original_cwd)

    def test_no_args_in_initialized_project_routes_to_install(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            (temp_project_dir / "super-dev.yaml").write_text(
                "name: demo\nversion: 2.3.4\n", encoding="utf-8"
            )
            cli = SuperDevCLI()
            called: dict[str, bool] = {"value": False}

            def fake_cmd_install(args):
                called["value"] = True
                return 0

            monkeypatch.setattr(cli, "_cmd_install", fake_cmd_install)
            assert cli.run([]) == 0
            assert called["value"] is True
        finally:
            os.chdir(original_cwd)

    def test_resume_command_routes_to_resume_handler(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            called: dict[str, bool] = {"value": False}

            def fake_cmd_resume(args):
                called["value"] = True
                return 0

            monkeypatch.setattr(cli, "_cmd_resume", fake_cmd_resume)
            assert cli.run(["resume"]) == 0
            assert called["value"] is True
        finally:
            os.chdir(original_cwd)

    def test_install_command_renders_intro_then_runs_setup(
        self, temp_project_dir: Path, capsys, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()

            def fake_cmd_setup(args):
                return 0

            monkeypatch.setattr(cli, "_cmd_setup", fake_cmd_setup)
            result = cli.run(["install", "--host", "claude-code", "--yes"])
            assert result == 0
            output = capsys.readouterr().out
            assert "Super Dev" in output
            assert "/super-dev 你的需求" in output
            assert "super-dev:" in output
            assert "text 宿主" in output
        finally:
            os.chdir(original_cwd)

    def test_install_command_for_droid_cli_runs_setup_with_factory_surfaces(
        self,
        temp_project_dir: Path,
        capsys,
        monkeypatch,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()

            setup_called: list[bool] = []

            def fake_setup(_args):
                setup_called.append(True)
                return 0

            monkeypatch.setattr(cli, "_cmd_setup", fake_setup)
            result = cli.run(["install", "--host", "droid-cli", "--yes"])
            assert result == 0
            assert setup_called, "setup should run for droid-cli"
            output = capsys.readouterr().out
            assert "Droid CLI" in output
            assert "/super-dev 你的需求" in output
            assert "super-dev:" in output
        finally:
            os.chdir(original_cwd)

    def test_install_command_for_workbuddy_runs_setup(
        self,
        temp_project_dir: Path,
        capsys,
        monkeypatch,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()

            setup_called: list[bool] = []

            def fake_setup(_args):
                setup_called.append(True)
                return 0

            monkeypatch.setattr(cli, "_cmd_setup", fake_setup)
            result = cli.run(["install", "--host", "workbuddy", "--yes"])
            assert result == 0
            assert setup_called, "setup should run for workbuddy (now a PRIMARY_IDE host)"
            output = capsys.readouterr().out
            assert "WorkBuddy" in output
        finally:
            os.chdir(original_cwd)

    def test_doctor_default_targets_use_current_primary_host_scope(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            captured: dict[str, list[str]] = {}

            def fake_collect_host_diagnostics(
                *, project_dir, targets, skill_name, check_integrate, check_skill, check_slash
            ):
                captured["targets"] = list(targets)
                return {
                    "overall_ready": True,
                    "hosts": {
                        target: {
                            "ready": True,
                            "checks": {
                                "integrate": {"ok": True},
                                "skill": {"ok": True},
                                "slash": {"ok": True},
                            },
                            "missing": [],
                            "suggestions": [],
                            "diagnosis": {},
                        }
                        for target in targets
                    },
                }

            monkeypatch.setattr(cli, "_collect_host_diagnostics", fake_collect_host_diagnostics)
            monkeypatch.setattr(
                cli,
                "_build_compatibility_summary",
                lambda **_kwargs: {
                    "overall_score": 100.0,
                    "ready_hosts": len(captured.get("targets", [])),
                    "total_hosts": len(captured.get("targets", [])),
                    "flow_consistency_score": 100.0,
                    "flow_consistent_hosts": len(captured.get("targets", [])),
                },
            )
            monkeypatch.setattr(
                cli,
                "_collect_runtime_install_health",
                lambda: {
                    "healthy": True,
                    "current_version": "2.1.6",
                    "current_module_path": "/tmp/super_dev/__init__.py",
                    "installed_dist_version": "2.1.6",
                    "warnings": [],
                    "remediation": [],
                },
            )

            assert cli.run(["doctor"]) == 0
            assert captured["targets"] == list(PRIMARY_HOST_TOOL_IDS)
            assert "droid-cli" in captured["targets"]
        finally:
            os.chdir(original_cwd)

    def test_install_command_warns_when_runtime_install_health_is_unhealthy(
        self,
        temp_project_dir: Path,
        capsys,
        monkeypatch,
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()

            def fake_cmd_setup(args):
                return 0

            monkeypatch.setattr(cli, "_cmd_setup", fake_cmd_setup)
            monkeypatch.setattr(
                cli,
                "_collect_runtime_install_health",
                lambda: {
                    "healthy": False,
                    "current_version": "2.1.6",
                    "current_module_path": "/tmp/super_dev/__init__.py",
                    "installed_dist_version": "2.1.6",
                    "warnings": ["检测到多个 super-dev dist-info 版本并存: 2.1.2, 2.1.6"],
                    "remediation": ["清理旧的 super_dev-*.dist-info 残留，只保留当前版本。"],
                },
            )

            result = cli.run(["install", "--host", "codex-cli", "--yes"])
            assert result == 0
            output = capsys.readouterr().out
            assert "检测到旧版本残留，正在自动清理" in output
        finally:
            os.chdir(original_cwd)

    def test_setup_runs_doctor_in_repair_mode(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            seen: list[bool] = []

            def fake_cmd_onboard(args):
                args._selected_targets = ["opencode"]
                return 0

            def fake_cmd_doctor(args):
                seen.append(bool(args.repair))
                return 0

            monkeypatch.setattr(cli, "_cmd_onboard", fake_cmd_onboard)
            monkeypatch.setattr(cli, "_cmd_doctor", fake_cmd_doctor)
            result = cli.run(["setup", "--host", "opencode", "--yes"])
            assert result == 0
            assert seen == [True]
        finally:
            os.chdir(original_cwd)

    def test_start_runs_setup_flow_when_onboard_enabled(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        original_path = os.environ.get("PATH", "")
        os.chdir(temp_project_dir)
        try:
            bin_dir = temp_project_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            claude_cmd = bin_dir / "claude"
            claude_cmd.write_text("#!/usr/bin/env sh\necho host\n", encoding="utf-8")
            claude_cmd.chmod(0o755)
            os.environ["PATH"] = f"{bin_dir}:{original_path}"

            cli = SuperDevCLI()
            called: dict[str, bool] = {"value": False}

            def fake_cmd_setup(args):
                called["value"] = True
                return 0

            monkeypatch.setattr(cli, "_cmd_setup", fake_cmd_setup)
            result = cli.run(["start", "--host", "claude-code", "--json"])
            assert result == 0
            assert called["value"] is True
        finally:
            os.environ["PATH"] = original_path
            os.chdir(original_cwd)

    def test_start_opencode_auto_refreshes_stale_contract_without_force(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
            assert (temp_project_dir / "AGENTS.md").exists()
            assert not (fake_home / ".config" / "opencode" / "AGENTS.md").exists()
            capsys.readouterr()

            stale_file = temp_project_dir / ".opencode" / "commands" / "super-dev.md"
            stale_file.write_text("# stale\n/super-dev\n", encoding="utf-8")

            result = cli.run(
                ["start", "--host", "opencode", "--json", "--idea", "做一个商业级官网"]
            )
            assert result == 0

            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_host"] == "opencode"
            assert payload["selected_host_name"] == "OpenCode"
            assert payload["onboard_performed"] is True
            assert "OpenCode 最短路径" in payload["quick_start"]
            assert "标准流第一句：" in payload["quick_start"]
            assert "比赛流第一句：" in payload["quick_start"]
            content = stale_file.read_text(encoding="utf-8")
            assert "SUPER_DEV_FLOW_CONTRACT_V1" in content
            assert "DOC_CONFIRM_GATE: required" in content
        finally:
            os.chdir(original_cwd)

    def test_start_codex_json_exposes_display_name_and_priority_notes(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert (
                cli.run(["start", "--host", "codex-cli", "--json", "--idea", "做一个商业级官网"])
                == 0
            )
            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_host"] == "codex-cli"
            assert payload["selected_host_name"] == "Codex CLI"
            assert "Codex CLI 最短路径" in payload["quick_start"]
            assert "标准流第一句：" in payload["quick_start"]
            assert "比赛流第一句：" in payload["quick_start"]
            assert "$super-dev" in payload["quick_start"]
            assert "CLI" in payload["quick_start"]
        finally:
            os.chdir(original_cwd)

    def test_start_json_includes_runtime_install_health(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli,
                "_collect_runtime_install_health",
                lambda: {
                    "healthy": True,
                    "current_version": "2.1.6",
                    "current_module_path": "/tmp/super_dev/__init__.py",
                    "installed_dist_version": "2.1.6",
                    "warnings": [],
                    "remediation": [],
                },
            )
            assert (
                cli.run(["start", "--host", "codex-cli", "--json", "--idea", "做一个商业级官网"])
                == 0
            )
            payload = json.loads(capsys.readouterr().out)
            assert payload["runtime_install_health"]["healthy"] is True
            assert payload["runtime_install_health"]["current_version"] == "2.1.6"
        finally:
            os.chdir(original_cwd)

    def test_start_json_includes_onboard_smoke_report_paths(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["start", "--host", "claude-code", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            report_paths = payload["onboard_smoke_report_paths"]
            assert report_paths["json"].endswith(".json")
            assert report_paths["markdown"].endswith(".md")
            assert Path(report_paths["json"]).exists()
            assert Path(report_paths["markdown"]).exists()
        finally:
            os.chdir(original_cwd)

    def test_start_existing_workflow_context_enters_continue_mode(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["start", "--host", "codex", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            decision_card = payload["decision_card"]
            resume_card = payload["session_resume_card"]
            assert payload["session_mode"] == "continue_super_dev"
            assert "继续当前项目" in payload["continue_prompt"]
            assert "Super Dev 流程" in payload["continue_prompt"]
            assert payload["recommended_workflow_command"]
            assert decision_card["workflow_mode"] == "continue"
            assert decision_card["session_resume_card"]["enabled"] is True
            assert decision_card["session_resume_card"]["host_first_sentence"] == resume_card[
                "host_first_sentence"
            ]
            assert decision_card["action_title"] == resume_card["action_title"]
            assert decision_card["action_examples"] == resume_card["action_examples"]
            assert decision_card["first_action"].endswith(resume_card["host_first_sentence"])
            assert any(
                line == f"继续当前流程第一句: {resume_card['host_first_sentence']}"
                for line in decision_card["lines"]
            )
            assert resume_card["enabled"] is True
            assert resume_card["preferred_entry"] == "app_desktop"
            assert resume_card["host_first_sentence"].startswith("/super-dev ")
            assert (
                ".super-dev/SESSION_BRIEF.md"
                in resume_card["session_brief_path"]
            )
            assert (
                ".super-dev/workflow-state.json"
                in resume_card["workflow_state_path"]
            )
            assert (
                ".super-dev/workflow-events.jsonl"
                in resume_card["workflow_event_log_path"]
            )
            assert resume_card["operational_harnesses"]
            assert resume_card["recent_snapshots"]
            assert resume_card["recent_events"]
            assert resume_card["recent_timeline"]
            assert resume_card["scenario_cards"]
            assert resume_card["scenario_cards"][0]["id"] == "resume_workday"
            assert "继续仓库里已有的 Super Dev 流程" in payload["quick_start"]
            assert ".super-dev/SESSION_BRIEF.md" in payload["quick_start"]
            assert "只有用户明确说取消当前流程" in payload["quick_start"]
        finally:
            os.chdir(original_cwd)

    def test_onboard_existing_workflow_context_prints_continue_first_sentence(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "codex", "--force", "--yes"]) == 0
            output = capsys.readouterr().out
            assert "接下来这样用" in output
            assert "重开后第一句直接复制 /super-dev " in output
            assert "如果你是在继续已有流程" in output
            assert "流程状态卡: " in output
            assert "继续规则: 用户说“改一下 / 补充 / 继续改 / 确认 / 通过”时" in output
            brief = (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").read_text(
                encoding="utf-8"
            )
            assert ".super-dev/SESSION_BRIEF.md" in brief
            assert ".super-dev/hook-history.jsonl" in brief
            assert "## 运行时 Harness 摘要" in brief
            assert "## 最近 Hook 事件" in brief
            assert "## 最近关键时间线" in brief
        finally:
            os.chdir(original_cwd)

    def test_onboard_kimi_prints_host_specific_post_onboard_self_check(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["onboard", "--host", "kimi-code", "--force", "--yes"]) == 0
            output = capsys.readouterr().out
            assert "终端到此为止，真正开发回到宿主里。" in output
            assert "Kimi Code: 回宿主到 Kimi Code" in output
            assert "标准流第一句" in output
            assert "比赛流第一句" in output
            assert "先做：" in output
            assert "Kimi Code" in output
            assert "接入后先确认入口可用" in output
            assert "SEEAI 项目补充面已写入" in output
            assert "super-dev-seeai" in output
            assert "/skill:super-dev" in output
            assert "再按 smoke guide 验收" in output
        finally:
            os.chdir(original_cwd)

    def test_next_existing_workflow_context_renders_continue_card(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli, "_preferred_host_target_for_project", lambda project_dir: "codex-cli"
            )
            assert cli.run(["next", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["current_step_label"] == "等待三文档确认"
            assert payload["preferred_host"] == "codex-cli"
            assert payload["preferred_host_name"] == "Codex"
            assert payload["host_continue_prompt"].startswith("$super-dev ")
            assert ".super-dev/SESSION_BRIEF.md" in payload["host_continue_prompt"]
            assert ".super-dev/workflow-state.json" in payload["host_continue_prompt"]
            assert ".super-dev/workflow-state.json" in payload["workflow_state_path"]
            assert "修改、补充、重写" in payload["host_continue_prompt"]
            assert "继续围绕 PRD、Architecture、UIUX 修改或确认" in payload["user_next_action"]
            brief = (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").read_text(
                encoding="utf-8"
            )
            workflow_state = json.loads(
                (temp_project_dir / ".super-dev" / "workflow-state.json").read_text(
                    encoding="utf-8"
                )
            )
            latest_snapshot = temp_project_dir / ".super-dev" / "workflow-history" / "latest.json"
            assert "当前步骤: 等待三文档确认" in brief
            assert ".super-dev/workflow-state.json" in brief
            assert ".super-dev/workflow-history/latest.json" in brief
            assert "会话连续性规则" in brief
            assert "下次回来怎么继续" in brief
            assert "回到宿主后，直接说“继续当前流程”。" in brief
            assert latest_snapshot.exists()
            latest_payload = json.loads(latest_snapshot.read_text(encoding="utf-8"))
            assert workflow_state["status"] == "waiting_docs_confirmation"
            assert workflow_state["current_step_label"] == "等待三文档确认"
            assert latest_payload["status"] == "waiting_docs_confirmation"
            assert latest_payload["current_step_label"] == "等待三文档确认"
        finally:
            os.chdir(original_cwd)

    def test_next_existing_workflow_context_prefers_kimi_skill_resume_entry(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli, "_preferred_host_target_for_project", lambda project_dir: "kimi-code"
            )
            assert cli.run(["next", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["preferred_host"] == "kimi-code"
            assert payload["host_continue_prompt"].startswith("/skill:super-dev ")
            assert payload["host_continue_entry_prompts"]["skill"].startswith("/skill:super-dev ")
            assert payload["host_continue_entry_prompts"]["flow"].startswith("/flow:super-dev ")
            assert payload["host_continue_entry_prompts"]["fallback"].startswith("super-dev:")
            assert payload["host_continue_preferred_entry_label"] == "Skill"
        finally:
            os.chdir(original_cwd)

    def test_next_existing_workflow_context_exposes_droid_headless_resume_entry(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli, "_preferred_host_target_for_project", lambda project_dir: "droid-cli"
            )
            assert cli.run(["next", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["preferred_host"] == "droid-cli"
            assert payload["host_continue_prompt"].startswith("/super-dev ")
            assert payload["host_continue_entry_prompts"]["slash"].startswith("/super-dev ")
            assert "droid exec --session-id" in payload["host_continue_entry_prompts"]["headless"]
            assert payload["host_continue_preferred_entry_label"] == "Slash"
        finally:
            os.chdir(original_cwd)

    def test_run_status_json_with_workflow_context_exposes_operational_harnesses(
        self,
        temp_project_dir: Path,
        monkeypatch,
        capsys,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert cli.run(["run", "--status", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["framework_playbook"]["framework"] == "uni-app"
            assert payload["recent_snapshots"]
            assert payload["recent_events"]
            assert payload["recent_hook_events"]
            assert payload["operational_harnesses"]
            assert payload["operational_focus"]["status"] == "needs_attention"
            assert payload["operational_focus"]["kind"] == "framework"
            assert {item["kind"] for item in payload["operational_harnesses"]} == {
                "workflow",
                "framework",
                "hooks",
            }
        finally:
            os.chdir(original_cwd)

    def test_next_existing_frontend_context_waits_for_preview_confirmation(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            _confirm_docs(temp_project_dir)
            change_dir = temp_project_dir / ".super-dev" / "changes" / "preview-demo"
            change_dir.mkdir(parents=True, exist_ok=True)
            (change_dir / "proposal.md").write_text("# proposal\n", encoding="utf-8")
            (change_dir / "tasks.md").write_text("- [ ] frontend\n", encoding="utf-8")
            output_dir = temp_project_dir / "output"
            (output_dir / f"{temp_project_dir.name}-frontend-runtime.json").write_text(
                json.dumps({"passed": True, "summary": "frontend ready"}, ensure_ascii=False),
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli, "_preferred_host_target_for_project", lambda project_dir: "codex-cli"
            )
            assert cli.run(["next", "--json"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["status"] == "waiting_preview_confirmation"
            assert payload["workflow_mode"] == "revise"
            assert payload["current_step_label"] == "等待前端预览确认"
            assert (
                payload["recommended_command"]
                == "在宿主里确认前端预览；如果通过，直接说\u201c前端预览确认，可以继续\u201d"
            )
            assert "继续改前端或确认预览" in payload["user_next_action"]
            assert payload["user_action_shortcuts"]
            assert "继续调 UI" in payload["user_action_shortcuts"]
            assert payload["action_card"]["mode"] == "revise"
            assert "继续调 UI" in payload["action_card"]["examples"]
            assert payload["recent_snapshots"]
            assert payload["recent_snapshots"][0]["current_step_label"] == "等待前端预览确认"
            workflow_state = json.loads(
                (temp_project_dir / ".super-dev" / "workflow-state.json").read_text(
                    encoding="utf-8"
                )
            )
            latest_snapshot = temp_project_dir / ".super-dev" / "workflow-history" / "latest.json"
            assert workflow_state["status"] == "waiting_preview_confirmation"
            assert workflow_state["gates"]["preview_confirmation"]["status"] == "pending_review"
            assert latest_snapshot.exists()
            latest_payload = json.loads(latest_snapshot.read_text(encoding="utf-8"))
            assert latest_payload["status"] == "waiting_preview_confirmation"
            event_log = temp_project_dir / ".super-dev" / "workflow-events.jsonl"
            assert event_log.exists()
            event_lines = [
                line for line in event_log.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            assert event_lines
            last_event = json.loads(event_lines[-1])
            assert last_event["status"] == "waiting_preview_confirmation"
            brief = (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").read_text(
                encoding="utf-8"
            )
            assert "## 最近流程快照" in brief
            assert "## 最近状态事件" in brief
            assert "等待前端预览确认" in brief
        finally:
            os.chdir(original_cwd)

    def test_continue_command_prints_host_first_sentence(
        self, temp_project_dir: Path, monkeypatch, capsys
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            monkeypatch.setattr(
                cli, "_preferred_host_target_for_project", lambda project_dir: "codex-cli"
            )
            assert cli.run(["continue"]) == 0
            output = capsys.readouterr().out
            assert "Super Dev Continue" in output
            assert "动作类型: 返工/补充当前流程" in output
            assert "当前步骤: 等待三文档确认" in output
            assert "你现在可以直接说:" in output
            assert "宿主第一句 (Codex): $super-dev " in output
            assert "CLI 恢复入口:" in output
            assert "自然语言示例: 这里补一下" in output
            assert "真实场景: 第二天回来继续开发 -> 回到宿主里说“继续当前流程”" in output
            assert "真实场景: 我只想知道现在先做什么 -> 回到宿主里说“现在下一步是什么”" in output
            assert "流程状态卡:" in output
            assert (
                "系统建议动作: 在宿主里确认三文档；如果通过，直接说“文档确认，可以继续”" in output
            )
        finally:
            os.chdir(original_cwd)

    def test_review_docs_updates_session_brief_for_continuity(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            cli = SuperDevCLI()
            assert (
                cli.run(
                    [
                        "review",
                        "docs",
                        "--status",
                        "revision_requested",
                        "--comment",
                        "补充首页信息架构",
                    ]
                )
                == 0
            )
            brief = (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").read_text(
                encoding="utf-8"
            )
            assert "动作类型: 返工/补充当前流程" in brief
            assert "当前步骤: 等待三文档确认" in brief
            assert "你现在可以直接说:" in brief
            assert "自然语言示例: 这里补一下" in brief
            assert "## 现实场景怎么做" in brief
            assert "- 第二天回来继续开发: `回到宿主里说“继续当前流程”`" in brief
            assert "- 我只想知道现在先做什么: `回到宿主里说“现在下一步是什么”`" in brief
            assert "修改、补充、重写、继续完善" in brief
            assert "只有用户明确表达“确认/通过/进入下一阶段”" in brief
        finally:
            os.chdir(original_cwd)

    def test_start_accepts_host_alias_codex(self, temp_project_dir: Path, monkeypatch, capsys):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert (
                cli.run(["start", "--host", "codex", "--json", "--idea", "做一个商业级官网"]) == 0
            )
            payload = json.loads(capsys.readouterr().out)
            assert payload["selected_host"] == "codex"
            assert payload["selected_host_name"] == "Codex"
            assert ("第一句直接输入" in payload["quick_start"]) or (
                "重开宿主后第一句直接复制" in payload["quick_start"]
            )
        finally:
            os.chdir(original_cwd)

    def test_spec_init_also_writes_bootstrap_artifacts(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            (temp_project_dir / "super-dev.yaml").write_text(
                yaml.safe_dump(
                    {
                        "name": "demo",
                        "platform": "web",
                        "frontend": "next",
                        "backend": "node",
                    }
                ),
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(["spec", "init"])
            assert result == 0
            assert (temp_project_dir / ".super-dev" / "WORKFLOW.md").exists()
            assert (temp_project_dir / "output" / "demo-bootstrap.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_help_and_version_alias_do_not_trigger_pipeline(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            assert cli.run(["help"]) == 0
            assert cli.run(["version"]) == 0
            assert not (temp_project_dir / "output").exists()
        finally:
            os.chdir(original_cwd)

    def test_pipeline_requires_ready_host_without_override(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        # 使用隔离的假 HOME 避免真实宿主安装影响检测
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")
        monkeypatch.delenv("SUPER_DEV_ALLOW_NO_HOST", raising=False)

        try:
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台"])
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_direct_requirement_entry_generates_docs_artifacts_and_pauses_for_confirmation(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            cli = SuperDevCLI()
            result = cli.run(["构建一个支持登录和看板的平台"])
            assert result == 0

            output_dir = temp_project_dir / "output"
            assert any(output_dir.glob("*-research.md"))
            assert any(output_dir.glob("*-prd.md"))
            assert any(output_dir.glob("*-architecture.md"))
            assert any(output_dir.glob("*-uiux.md"))
            assert any(output_dir.glob("*-execution-plan.md"))
            assert any(output_dir.glob("*-frontend-blueprint.md"))
            assert any(output_dir.glob("*-pipeline-metrics.json"))
            assert any(output_dir.glob("*-pipeline-metrics.md"))
            assert any(output_dir.glob("*-pipeline-contract.md"))
            assert not any(output_dir.glob("*-quality-gate.md"))
            assert not any(output_dir.glob("*-frontend-runtime.json"))
            assert not any(output_dir.glob("*-frontend-runtime.md"))
            assert any(output_dir.glob("*-ui-contract.json"))
            assert not (temp_project_dir / "preview.html").exists()
            assert not (temp_project_dir / "frontend").exists()
            assert not (temp_project_dir / "backend").exists()

            workflow_state_file = temp_project_dir / ".super-dev" / "workflow-state.json"
            workflow_state = json.loads(workflow_state_file.read_text(encoding="utf-8"))
            assert workflow_state["status"] == "waiting_docs_confirmation"
            assert workflow_state["current_step_label"] == "等待三文档确认"
        finally:
            os.chdir(original_cwd)

    def test_frontend_runtime_fails_fast_when_preview_contains_emoji(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "index.html").write_text(
            "<!doctype html><html><body><button>✨ 保存</button></body></html>",
            encoding="utf-8",
        )
        (frontend_dir / "styles.css").write_text(
            "body { color: var(--color-primary); }", encoding="utf-8"
        )
        (frontend_dir / "app.js").write_text("console.log('preview');", encoding="utf-8")
        (output_dir / "emoji-demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "Editorial workspace",
                    "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},
                    "icon_system": "lucide-react",
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                    },
                    "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},
                    "design_tokens": {"css_variables": ":root { --color-primary: #0f172a; }"},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(
            ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
        )

        cli = SuperDevCLI()
        payload = cli._write_frontend_runtime_validation(
            project_dir=temp_project_dir,
            output_dir=output_dir,
            project_name="emoji-demo",
        )

        assert payload["ui_alignment_available"] is False
        assert payload["checks"]["ui_banned_patterns"] is False
        assert payload["passed"] is False
        assert "✨" in payload["ui_banned_pattern_probe"]["emoji_hits"]

    def test_frontend_runtime_captures_claude_design_execution_protocol(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "index.html").write_text(
            (
                "<!doctype html><html><body>"
                "<section>North Star Hero</section>"
                "<section>hero</section>"
                "<section>客户案例</section>"
                "<section>tokens theme.ts single source prototype</section>"
                "<section>preview output/frontend/index.html no emoji</section>"
                "</body></html>"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "styles.css").write_text(
            "body { color: var(--color-primary); }", encoding="utf-8"
        )
        (frontend_dir / "app.js").write_text(
            (
                "const notes = ['信息密度', 'persist tweak decisions into the same prototype', "
                "'src/components'];"
            ),
            encoding="utf-8",
        )
        (output_dir / "recipe-demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "Editorial workspace",
                    "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},
                    "icon_system": "lucide-react",
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                    },
                    "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},
                    "design_tokens": {"css_variables": ":root { --color-primary: #0f172a; }"},
                    "screen_recipes": [
                        {
                            "label": "North Star Hero",
                            "section_order": ["hero"],
                            "trust_modules": ["客户案例"],
                            "required_states": ["loading"],
                        }
                    ],
                    "design_context_protocol": {
                        "preferred_import_order": ["tokens"],
                        "github_import_targets": ["theme.ts", "src/components"],
                        "single_source_rule": "single source prototype",
                    },
                    "tweak_strategy": {
                        "mode": "single-source prototype",
                        "default_controls": ["信息密度"],
                        "persistence_rule": "persist tweak decisions into the same prototype",
                    },
                    "verification_handoff": {
                        "verification_order": ["preview"],
                        "required_artifacts": ["output/frontend/index.html"],
                        "acceptance_checks": ["no emoji"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(
            ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
        )

        cli = SuperDevCLI()
        payload = cli._write_frontend_runtime_validation(
            project_dir=temp_project_dir,
            output_dir=output_dir,
            project_name="recipe-demo",
        )

        assert payload["checks"]["ui_screen_recipes"] is True
        assert payload["checks"]["ui_design_context_protocol"] is True
        assert payload["checks"]["ui_tweak_strategy"] is True
        assert payload["checks"]["ui_verification_handoff"] is True

    def test_direct_requirement_supports_pipeline_flags(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "构建一个支持登录和看板的平台",
                    "--offline",
                    "--domain",
                    "saas",
                    "--backend",
                    "python",
                    "--name",
                    "direct-flags-demo",
                ]
            )
            assert result == 0

            output_dir = temp_project_dir / "output"
            assert (output_dir / "direct-flags-demo-prd.md").exists()
            assert (output_dir / "direct-flags-demo-architecture.md").exists()
            assert (output_dir / "direct-flags-demo-uiux.md").exists()
            assert (output_dir / "direct-flags-demo-execution-plan.md").exists()
            assert not (output_dir / "direct-flags-demo-quality-gate.md").exists()
            assert not (output_dir / "direct-flags-demo-frontend-runtime.json").exists()

            config_data = yaml.safe_load(
                (temp_project_dir / "super-dev.yaml").read_text(encoding="utf-8")
            )
            assert config_data["domain"] == "saas"
            assert config_data["backend"] == "python"
            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_generates_docs_artifacts_and_pauses_for_confirmation(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台"])
            assert result == 0

            output_dir = temp_project_dir / "output"
            assert any(output_dir.glob("*-research.md"))
            assert any(output_dir.glob("*-prd.md"))
            assert any(output_dir.glob("*-architecture.md"))
            assert any(output_dir.glob("*-uiux.md"))
            assert any(output_dir.glob("*-execution-plan.md"))
            assert any(output_dir.glob("*-frontend-blueprint.md"))
            assert any(output_dir.glob("*-pipeline-metrics.json"))
            assert any(output_dir.glob("*-pipeline-metrics.md"))
            assert any(output_dir.glob("*-pipeline-contract.md"))
            assert not any(output_dir.glob("*-frontend-runtime.md"))
            assert not any(output_dir.glob("*-frontend-runtime.json"))
            assert not any(output_dir.glob("*-quality-gate.md"))
            assert not (temp_project_dir / "preview.html").exists()
            assert not (temp_project_dir / "frontend").exists()
            assert not (temp_project_dir / "backend").exists()
            assert not (temp_project_dir / "output" / "deploy").exists()
            assert not (temp_project_dir / "output" / "delivery").exists()
            assert not (temp_project_dir / "output" / "rehearsal").exists()

            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
            assert payload["status_normalized"] == "running"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_supports_explicit_bugfix_mode(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "优化登录体验并补充回归验证", "--mode", "bugfix"])
            assert result == 0

            output_dir = temp_project_dir / "output"
            plan_files = list(output_dir.glob("*-execution-plan.md"))
            assert plan_files
            plan = max(plan_files, key=lambda item: item.stat().st_mtime).read_text(
                encoding="utf-8"
            )
            assert "> **请求模式**: bugfix" in plan
            assert "问题复现与影响分析" in plan
        finally:
            os.chdir(original_cwd)

    def test_pipeline_skip_rehearsal_verify(self, temp_project_dir: Path, monkeypatch, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            policy_dir = temp_project_dir / ".super-dev"
            policy_dir.mkdir(parents=True, exist_ok=True)
            (policy_dir / "policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "require_redteam": True,
                        "require_quality_gate": True,
                        "require_rehearsal_verify": False,
                        "min_quality_threshold": 80,
                        "allowed_cicd_platforms": ["all"],
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(
                ["pipeline", "构建一个支持登录和看板的平台", "--skip-rehearsal-verify"]
            )
            assert result == 0
            output = capsys.readouterr().out
            assert "已完成 research 与三文档，当前进入文档确认门" in output
            assert not any((temp_project_dir / "output").glob("*-frontend-runtime.json"))
            rehearsal_dir = temp_project_dir / "output" / "rehearsal"
            assert not any(rehearsal_dir.glob("*-rehearsal-report.md"))
            assert not any(rehearsal_dir.glob("*-rehearsal-report.json"))
            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_supports_saas_domain(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台", "--domain", "saas"])
            assert result == 0
            assert any((temp_project_dir / "output").glob("*-prd.md"))
            assert not any((temp_project_dir / "output").glob("*-frontend-runtime.json"))
            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_fails_when_delivery_package_is_incomplete(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            cli = SuperDevCLI()

            from super_dev.deployers.delivery import DeliveryPackager

            original_package = DeliveryPackager.package

            def fake_package(self, cicd_platform="all"):
                payload = original_package(self, cicd_platform=cicd_platform)
                return {
                    **payload,
                    "status": "incomplete",
                    "missing_required_count": 1,
                    "missing_required": [
                        {"path": "output/demo-frontend-runtime.json", "reason": "missing"}
                    ],
                }

            monkeypatch.setattr(DeliveryPackager, "package", fake_package)

            result = cli.run(["pipeline", "构建一个支持登录和看板的平台"])
            assert result == 0

            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
            assert payload["status_normalized"] == "running"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_pauses_at_docs_confirmation_gate(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台"])
            assert result == 0

            output_dir = temp_project_dir / "output"
            assert any(output_dir.glob("*-research.md"))
            assert any(output_dir.glob("*-prd.md"))
            assert any(output_dir.glob("*-architecture.md"))
            assert any(output_dir.glob("*-uiux.md"))
            assert not any((temp_project_dir / ".super-dev" / "changes").glob("*/tasks.md"))

            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_confirmation"
            assert payload["resume_from_stage"] == "2"
            assert payload["status_normalized"] == "running"
        finally:
            os.chdir(original_cwd)

    def test_pipeline_resume_pauses_at_preview_confirmation_gate(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            cli = SuperDevCLI()
            assert cli.run(["pipeline", "构建一个支持登录和看板的平台", "--offline"]) == 0
            save_bound_docs_confirmation(
                temp_project_dir,
                {
                    "status": "confirmed",
                    "comment": "测试中预先确认三文档",
                    "actor": "pytest",
                    "run_id": "test-run",
                },
            )

            result = cli.run(["run", "--resume"])
            assert result == 0

            output_dir = temp_project_dir / "output"
            assert any(output_dir.glob("*-frontend-runtime.json"))
            assert (temp_project_dir / "preview.html").exists()

            run_state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
            payload = json.loads(run_state_file.read_text(encoding="utf-8"))
            assert payload["status"] == "waiting_preview_confirmation"
            assert payload["resume_from_stage"] == "4"
            assert payload["status_normalized"] == "running"
        finally:
            os.chdir(original_cwd)


class TestCLIRunControl:
    """测试 run 控制命令（恢复）"""

    def test_write_pipeline_run_state_creates_lock_file(self, temp_project_dir: Path):
        cli = SuperDevCLI()
        cli._write_pipeline_run_state(
            temp_project_dir,
            {"status": "running", "project_name": "demo"},
        )
        lock_file = temp_project_dir / ".super-dev" / "runs" / ".runs.lock"
        assert lock_file.exists()
        state_file = temp_project_dir / ".super-dev" / "runs" / "last-pipeline.json"
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        assert payload["status_normalized"] == "running"

    def test_run_resume_returns_error_for_corrupted_state_file(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            (run_state_dir / "last-pipeline.json").write_text("{invalid-json", encoding="utf-8")

            cli = SuperDevCLI()
            result = cli.run(["run", "--resume"])
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_run_resume_replays_failed_pipeline(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            (run_state_dir / "last-pipeline.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "project_name": "resume-demo",
                        "pipeline_args": {
                            "description": "构建一个支持登录和看板的平台",
                            "platform": "web",
                            "frontend": "react",
                            "backend": "python",
                            "domain": "saas",
                            "name": "resume-demo",
                            "cicd": "all",
                            "skip_redteam": False,
                            "skip_scaffold": False,
                            "skip_quality_gate": False,
                            "skip_rehearsal_verify": False,
                            "offline": True,
                            "quality_threshold": None,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            captured: dict[str, object] = {}

            def _fake_pipeline(pipeline_args):
                captured["args"] = pipeline_args
                return 0

            monkeypatch.setattr(cli, "_cmd_pipeline", _fake_pipeline)
            result = cli.run(["run", "--resume"])
            assert result == 0
            assert "args" in captured
            pipeline_args = captured["args"]
            assert getattr(pipeline_args, "resume") is True
            assert getattr(pipeline_args, "name") == "resume-demo"
            assert getattr(pipeline_args, "description") == "构建一个支持登录和看板的平台"
        finally:
            os.chdir(original_cwd)

    def test_run_resume_supports_interrupted_running_state(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            (run_state_dir / "last-pipeline.json").write_text(
                json.dumps(
                    {
                        "status": "running",
                        "project_name": "resume-demo",
                        "pipeline_args": {
                            "description": "构建一个支持登录和看板的平台",
                            "platform": "web",
                            "frontend": "react",
                            "backend": "python",
                            "domain": "saas",
                            "name": "resume-demo",
                            "cicd": "all",
                            "skip_redteam": False,
                            "skip_scaffold": False,
                            "skip_quality_gate": False,
                            "skip_rehearsal_verify": False,
                            "offline": True,
                            "quality_threshold": None,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            captured: dict[str, object] = {}

            def _fake_pipeline(pipeline_args):
                captured["args"] = pipeline_args
                return 0

            monkeypatch.setattr(cli, "_cmd_pipeline", _fake_pipeline)
            result = cli.run(["run", "--resume"])
            assert result == 0
            assert "args" in captured
            pipeline_args = captured["args"]
            assert getattr(pipeline_args, "resume") is True
            assert getattr(pipeline_args, "name") == "resume-demo"
        finally:
            os.chdir(original_cwd)

    def test_run_resume_supports_waiting_confirmation_state(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            (run_state_dir / "last-pipeline.json").write_text(
                json.dumps(
                    {
                        "status": "waiting_confirmation",
                        "project_name": "resume-demo",
                        "resume_from_stage": "2",
                        "pipeline_args": {
                            "description": "构建一个支持登录和看板的平台",
                            "platform": "web",
                            "frontend": "react",
                            "backend": "python",
                            "domain": "saas",
                            "name": "resume-demo",
                            "cicd": "all",
                            "skip_redteam": False,
                            "skip_scaffold": False,
                            "skip_quality_gate": False,
                            "skip_rehearsal_verify": False,
                            "offline": True,
                            "quality_threshold": None,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            for suffix in ("prd", "architecture", "uiux"):
                (output_dir / f"resume-demo-{suffix}.md").write_text("# ok", encoding="utf-8")
            save_bound_docs_confirmation(
                temp_project_dir,
                {
                    "status": "confirmed",
                    "comment": "三文档已确认",
                    "actor": "pytest",
                    "run_id": "resume-demo",
                },
            )

            cli = SuperDevCLI()
            captured: dict[str, object] = {}

            def _fake_pipeline(pipeline_args):
                captured["args"] = pipeline_args
                return 0

            monkeypatch.setattr(cli, "_cmd_pipeline", _fake_pipeline)
            result = cli.run(["run", "--resume"])
            assert result == 0
            pipeline_args = captured["args"]
            assert getattr(pipeline_args, "resume") is True
            assert getattr(pipeline_args, "name") == "resume-demo"
        finally:
            os.chdir(original_cwd)

    def test_run_resume_supports_waiting_preview_confirmation_state(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "resume-demo-frontend-runtime.json").write_text(
                json.dumps({"passed": True}, ensure_ascii=False),
                encoding="utf-8",
            )
            (output_dir / "resume-demo-ui-contract.json").write_text(
                json.dumps({"screen_recipes": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            (run_state_dir / "last-pipeline.json").write_text(
                json.dumps(
                    {
                        "status": "waiting_preview_confirmation",
                        "project_name": "resume-demo",
                        "resume_from_stage": "5",
                        "pipeline_args": {
                            "description": "构建一个支持登录和看板的平台",
                            "platform": "web",
                            "frontend": "react",
                            "backend": "python",
                            "domain": "saas",
                            "name": "resume-demo",
                            "cicd": "all",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            save_bound_preview_confirmation(
                temp_project_dir,
                {
                    "status": "confirmed",
                    "comment": "预览已确认",
                    "actor": "pytest",
                    "run_id": "resume-demo",
                },
            )

            cli = SuperDevCLI()
            captured: dict[str, object] = {}

            def _fake_pipeline(pipeline_args):
                captured["args"] = pipeline_args
                return 0

            monkeypatch.setattr(cli, "_cmd_pipeline", _fake_pipeline)
            result = cli.run(["run", "--resume"])
            assert result == 0
            pipeline_args = captured["args"]
            assert getattr(pipeline_args, "resume") is True
            assert getattr(pipeline_args, "name") == "resume-demo"
        finally:
            os.chdir(original_cwd)

    def test_run_resume_blocks_when_ui_revision_requested(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            run_state_dir = temp_project_dir / ".super-dev" / "runs"
            run_state_dir.mkdir(parents=True, exist_ok=True)
            (run_state_dir / "last-pipeline.json").write_text(
                json.dumps(
                    {
                        "status": "waiting_ui_revision",
                        "project_name": "resume-demo",
                        "resume_from_stage": "2",
                        "pipeline_args": {
                            "description": "重做官网",
                            "platform": "web",
                            "frontend": "react",
                            "backend": "python",
                            "domain": "saas",
                            "name": "resume-demo",
                            "cicd": "all",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            save_ui_revision(
                temp_project_dir,
                {
                    "status": "revision_requested",
                    "comment": "Hero 太空，重做首屏",
                    "actor": "pytest",
                    "run_id": "resume-demo",
                },
            )

            cli = SuperDevCLI()
            result = cli.run(["run", "--resume"])

            assert result == 1
            output = capsys.readouterr().out
            assert "UI 改版门" in output
            assert "UI 改版已完成" in output or "UI review" in output
        finally:
            os.chdir(original_cwd)

    def test_spec_propose_blocks_when_ui_revision_requested(self, temp_project_dir: Path, capsys):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            output_dir = temp_project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            for suffix in ("prd", "architecture", "uiux"):
                (output_dir / f"demo-{suffix}.md").write_text("# ok", encoding="utf-8")
            save_bound_docs_confirmation(
                temp_project_dir,
                {
                    "status": "confirmed",
                    "comment": "三文档已确认",
                    "actor": "pytest",
                    "run_id": "spec-demo",
                },
            )
            save_ui_revision(
                temp_project_dir,
                {
                    "status": "revision_requested",
                    "comment": "需要重做 UI",
                    "actor": "pytest",
                    "run_id": "spec-demo",
                },
            )

            cli = SuperDevCLI()
            result = cli.run(
                [
                    "spec",
                    "propose",
                    "demo-change",
                    "--title",
                    "demo",
                    "--description",
                    "demo desc",
                ]
            )

            assert result == 1
            output = capsys.readouterr().out
            assert "必须先完成 UI 改版返工" in output
            assert "UI 改版已完成" in output or "UI review" in output
        finally:
            os.chdir(original_cwd)

    def test_run_resume_requires_state(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["run", "--resume"])
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_pipeline_knowledge_cache_contains_signature(self, temp_project_dir: Path, monkeypatch):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            _confirm_docs(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台"])
            assert result == 0

            cache_files = list(
                (temp_project_dir / "output" / "knowledge-cache").glob("*-knowledge-bundle.json")
            )
            assert cache_files
            content = cache_files[0].read_text(encoding="utf-8")
            assert '"cache_signature"' in content
            assert '"cache_ttl_seconds"' in content
        finally:
            os.chdir(original_cwd)

    def test_pipeline_knowledge_settings_from_project_config(
        self, temp_project_dir: Path, monkeypatch
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        monkeypatch.setenv("SUPER_DEV_DISABLE_WEB", "1")

        try:
            (temp_project_dir / "super-dev.yaml").write_text(
                (
                    "name: demo\n"
                    "platform: web\n"
                    "frontend: react\n"
                    "backend: node\n"
                    "knowledge_allowed_domains:\n"
                    "  - openai.com\n"
                    "  - python.org\n"
                    "knowledge_cache_ttl_seconds: 120\n"
                ),
                encoding="utf-8",
            )

            cli = SuperDevCLI()
            result = cli.run(["pipeline", "构建一个支持登录和看板的平台", "--name", "demo"])
            assert result == 0

            cache_file = (
                temp_project_dir / "output" / "knowledge-cache" / "demo-knowledge-bundle.json"
            )
            assert cache_file.exists()
            cache_payload = json.loads(cache_file.read_text(encoding="utf-8"))
            assert cache_payload.get("cache_ttl_seconds") == 120
            metadata = cache_payload.get("metadata", {})
            assert metadata.get("allowed_web_domains") == ["openai.com", "python.org"]

            metrics_file = temp_project_dir / "output" / "demo-pipeline-metrics.json"
            assert metrics_file.exists()
            metrics_payload = json.loads(metrics_file.read_text(encoding="utf-8"))
            stages = metrics_payload.get("stages", [])
            stage0 = next((item for item in stages if item.get("stage") == "0"), {})
            details = stage0.get("details", {})
            assert details.get("knowledge_cache_ttl_seconds") == 120
            assert details.get("knowledge_allowed_domains") == ["openai.com", "python.org"]
        finally:
            os.chdir(original_cwd)

    def test_release_readiness_command_is_not_routed_as_direct_requirement(
        self, temp_project_dir: Path
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_release_ready_project(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["release", "readiness"])

            assert result in {0, 1}
            assert (
                temp_project_dir / "output" / f"{temp_project_dir.name}-release-readiness.md"
            ).exists()
            assert (
                temp_project_dir / "output" / f"{temp_project_dir.name}-release-readiness.json"
            ).exists()
        finally:
            os.chdir(original_cwd)

    def test_release_readiness_command_json_output(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_release_ready_project(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["release", "readiness", "--json"])

            assert result in {0, 1}
            payload = json.loads(
                (
                    temp_project_dir / "output" / f"{temp_project_dir.name}-release-readiness.json"
                ).read_text(encoding="utf-8")
            )
            assert payload["passed"] is True
            assert set(payload["failed_checks"]).issubset(
                {"Host Coverage Depth", "Expert Stage Governance"}
            )
            checks = {check["name"]: check for check in payload["checks"]}
            assert checks["Delivery Closure"]["passed"] is True
            assert any(check["name"] == "Spec Quality" for check in payload["checks"])
        finally:
            os.chdir(original_cwd)

    def test_release_proof_pack_command_json_output(self, temp_project_dir: Path):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_proof_pack_project(temp_project_dir)
            cli = SuperDevCLI()
            result = cli.run(["release", "proof-pack", "--json"])

            assert result in {0, 1}
            payload = json.loads(
                (
                    temp_project_dir / "output" / f"{temp_project_dir.name}-proof-pack.json"
                ).read_text(encoding="utf-8")
            )
            blocking_names = {artifact["name"] for artifact in payload["blocking_artifacts"]}
            assert "Release Readiness" in blocking_names
            assert any(artifact["name"] == "Spec Quality" for artifact in payload["artifacts"])
            assert any(artifact["name"] == "Scope Coverage" for artifact in payload["artifacts"])
            assert any(artifact["name"] == "Repo Map" for artifact in payload["artifacts"])
            assert any(artifact["name"] == "Dependency Graph" for artifact in payload["artifacts"])
            assert any(artifact["name"] == "Impact Analysis" for artifact in payload["artifacts"])
            assert any(artifact["name"] == "Regression Guard" for artifact in payload["artifacts"])
            assert any(
                artifact["name"] == "UI Contract" and artifact["status"] == "ready"
                for artifact in payload["artifacts"]
            )
            assert any(
                artifact["name"] == "UI Contract Alignment" and artifact["status"] == "ready"
                for artifact in payload["artifacts"]
            )
            assert any(
                artifact["name"] == "Frontend Runtime"
                and artifact["status"] in {"ready", "pending"}
                for artifact in payload["artifacts"]
            )
            assert (
                temp_project_dir / "output" / f"{temp_project_dir.name}-proof-pack-summary.md"
            ).exists()
        finally:
            os.chdir(original_cwd)

    def test_release_proof_pack_marks_rehearsal_artifact_ready_when_report_exists(
        self, temp_project_dir: Path
    ):
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_proof_pack_project(temp_project_dir)
            (
                temp_project_dir
                / "output"
                / "rehearsal"
                / f"{temp_project_dir.name}-rehearsal-report.json"
            ).write_text(
                json.dumps({"passed": False, "score": 35}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(["release", "proof-pack", "--json"])

            # rehearsal passed=False -> proof-pack 有 blocker，命令可能返回 1
            assert result in (0, 1)
            payload = json.loads(
                (
                    temp_project_dir / "output" / f"{temp_project_dir.name}-proof-pack.json"
                ).read_text(encoding="utf-8")
            )
            rehearsal = next(
                item for item in payload["artifacts"] if item["name"] == "Release Rehearsal"
            )
            assert rehearsal["status"] == "pending"  # passed=False -> pending
            assert "passed=False" in rehearsal["summary"]
        finally:
            os.chdir(original_cwd)


class TestCLIClean:
    def test_clean_empty_output(self, temp_project_dir):
        original = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            cli = SuperDevCLI()
            result = cli.run(["clean"])
            assert result == 0
        finally:
            os.chdir(original)

    def test_clean_dry_run(self, temp_project_dir):
        original = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            out = temp_project_dir / "output"
            out.mkdir()
            (out / "test-prd.md").write_text("x")
            (out / "test-architecture.md").write_text("x")
            cli = SuperDevCLI()
            result = cli.run(["clean", "--dry-run"])
            assert result == 0
            assert (out / "test-prd.md").exists()
            assert (out / "test-architecture.md").exists()
        finally:
            os.chdir(original)

    def test_clean_all(self, temp_project_dir):
        original = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            out = temp_project_dir / "output"
            out.mkdir()
            (out / "test-prd.md").write_text("x")
            (out / "test-architecture.md").write_text("x")
            cli = SuperDevCLI()
            result = cli.run(["clean", "--all"])
            assert result == 0
            remaining = list(out.glob("*"))
            assert len(remaining) == 0
        finally:
            os.chdir(original)

    def test_clean_keep_default(self, temp_project_dir):
        original = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            out = temp_project_dir / "output"
            out.mkdir()
            (out / "test-prd.md").write_text("x")
            (out / "test-architecture.md").write_text("x")
            import time

            time.sleep(0.05)
            (out / "test-uiux.md").write_text("y")
            cli = SuperDevCLI()
            result = cli.run(["clean"])
            assert result == 0
        finally:
            os.chdir(original)
