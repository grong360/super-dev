"""
Super Dev Web API 集成测试
"""

import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import super_dev.web.api as web_api
from super_dev import __version__ as _super_dev_version
from super_dev.analyzer import BaselineAuditBuilder
from super_dev.catalogs import PRIMARY_HOST_TOOL_IDS
from super_dev.cli import SuperDevCLI
from super_dev.evidence_identity import build_evidence_identity
from super_dev.integrations import IntegrationManager
from super_dev.orchestrator import Phase, PhaseResult
from super_dev.review_state import (
    save_baseline_confirmation,
    save_docs_confirmation,
    save_resume_gate,
    save_ui_revision,
    save_workflow_state,
)
from super_dev.reviewers.architecture_drift import (
    _report_dependencies as architecture_drift_dependencies,
)
from super_dev.reviewers.spec_compliance import _report_dependencies as spec_compliance_dependencies
from super_dev.reviewers.uiux_compliance import _report_dependencies as uiux_compliance_dependencies
from super_dev.skills import SkillManager
from super_dev.specs.generator import SpecGenerator
from super_dev.workflow_guard import (
    record_stage_progress,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)

# Fixed API key for all integration tests
_TEST_API_KEY = "test-integration-key-super-dev-2026"
_TEST_HEADERS = {"X-Super-Dev-Key": _TEST_API_KEY}


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Set a known API key and disable rate limiting for integration tests."""
    monkeypatch.setenv("SUPER_DEV_API_KEY", _TEST_API_KEY)
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    yield


def _make_client() -> TestClient:
    """Create a TestClient with API key default headers."""
    tc = TestClient(web_api.app, headers=_TEST_HEADERS)
    return tc


@pytest.fixture(autouse=True)
def clear_run_store():
    web_api._RUN_STORE.clear()
    yield
    web_api._RUN_STORE.clear()


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


def _hydrate_release_governance_artifacts(project_dir: Path) -> None:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_name = project_dir.name

    prd_path = output_dir / f"{project_name}-prd.md"
    if not prd_path.exists():
        prd_path.write_text(
            "# PRD\n\n## Requirements\n\n- 支持邮箱密码登录并展示运营看板。\n",
            encoding="utf-8",
        )
    architecture_path = output_dir / f"{project_name}-architecture.md"
    if not architecture_path.exists():
        architecture_path.write_text(
            "# Architecture\n\n## Module: Web App\n- React\n## Module: Backend\n- Python\n",
            encoding="utf-8",
        )
    uiux_path = output_dir / f"{project_name}-uiux.md"
    if not uiux_path.exists():
        uiux_path.write_text(
            (
                "# UIUX\n\n"
                "icon library: lucide\n"
                "font-family: Space Grotesk\n"
                "token: --color-primary\n"
            ),
            encoding="utf-8",
        )

    app_dir = project_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "page.tsx").write_text(
        (
            "import { Sparkles } from 'lucide-react';\n"
            "export default function Page() {\n"
            "  return (\n"
            "    <main style={{ color: 'var(--color-primary)' }}>\n"
            "      <header><nav><a href=\"#hero\">Hero</a></nav></header>\n"
            "      <section id=\"hero\"><Sparkles />Launch</section>\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    ui_contract_path = output_dir / f"{project_name}-ui-contract.json"
    ui_review_path = output_dir / f"{project_name}-ui-review.json"
    ui_alignment_path = output_dir / f"{project_name}-ui-contract-alignment.json"
    frontend_runtime_path = output_dir / f"{project_name}-frontend-runtime.json"
    os.utime(ui_contract_path, None)

    ui_review_payload = json.loads(ui_review_path.read_text(encoding="utf-8"))
    ui_review_payload["evidence_identity"] = build_evidence_identity(
        project_dir,
        artifact_name="ui-review",
        dependencies=[ui_contract_path, uiux_path],
    )
    ui_review_path.write_text(
        json.dumps(ui_review_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ui_alignment_payload = json.loads(ui_alignment_path.read_text(encoding="utf-8"))
    ui_alignment_payload["evidence_identity"] = build_evidence_identity(
        project_dir,
        artifact_name="ui-contract-alignment",
        dependencies=[ui_contract_path, uiux_path],
    )
    ui_alignment_path.write_text(
        json.dumps(ui_alignment_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    frontend_runtime_payload = json.loads(frontend_runtime_path.read_text(encoding="utf-8"))
    frontend_runtime_payload["evidence_identity"] = build_evidence_identity(
        project_dir,
        artifact_name="frontend-runtime",
        dependencies=[ui_contract_path, ui_alignment_path],
    )
    frontend_runtime_path.write_text(
        json.dumps(frontend_runtime_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    quality_gate_payload = {
        "passed": True,
        "total_score": 92,
        "summary": {
            "executive_summary": "当前质量门禁已通过，UI 阶段与合规链证据当前均已闭环。"
        },
        "evidence_identity": build_evidence_identity(
            project_dir,
            artifact_name="quality-gate",
            dependencies=[ui_review_path, ui_alignment_path, uiux_path],
        ),
    }
    (output_dir / f"{project_name}-quality-gate.json").write_text(
        json.dumps(quality_gate_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    spec_payload = {
        "project_name": project_name,
        "total_requirements": 1,
        "found": 1,
        "partial": 0,
        "missing": 0,
        "score": 98,
        "matches": [],
        "evidence_identity": build_evidence_identity(
            project_dir,
            artifact_name="spec-compliance",
            dependencies=spec_compliance_dependencies(project_dir, output_dir),
        ),
    }
    (output_dir / f"{project_name}-spec-compliance.json").write_text(
        json.dumps(spec_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    architecture_payload = {
        "project_name": project_name,
        "declared_modules": ["Web App", "Backend"],
        "actual_modules": ["Web App", "Backend"],
        "declared_tech_stack": ["React", "Python"],
        "actual_tech_stack": ["React", "Python"],
        "drifts": [],
        "score": 96,
        "evidence_identity": build_evidence_identity(
            project_dir,
            artifact_name="architecture-drift",
            dependencies=architecture_drift_dependencies(project_dir, output_dir),
        ),
    }
    (output_dir / f"{project_name}-architecture-drift.json").write_text(
        json.dumps(architecture_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    uiux_payload = {
        "project_name": project_name,
        "declared_icon_library": "lucide",
        "declared_typography": ["Space Grotesk"],
        "declared_tokens": ["--color-primary"],
        "violations": [],
        "score": 97,
        "files_scanned": 1,
        "evidence_identity": build_evidence_identity(
            project_dir,
            artifact_name="uiux-compliance",
            dependencies=uiux_compliance_dependencies(project_dir, output_dir),
        ),
    }
    (output_dir / f"{project_name}-uiux-compliance.json").write_text(
        json.dumps(uiux_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
                "/.kiro/",
                "/.opencode/",
                "/.qoder/",
                "/.trae/",
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
        "Codex CLI\nsuper-dev:\n继续当前流程\n维护者再补 runtime 验收\n",
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
                "screen_recipes": [
                    {
                        "label": "North Star Hero",
                        "section_order": ["hero", "proof", "cta"],
                        "trust_modules": ["proof"],
                        "required_states": ["loading", "empty"],
                    }
                ],
                "design_context_protocol": {
                    "preferred_import_order": ["tokens", "components"],
                    "github_import_targets": ["theme.ts", "design-tokens.css"],
                    "single_source_rule": "single source",
                },
                "tweak_strategy": {
                    "mode": "single-source prototype",
                    "default_controls": ["density", "tone"],
                    "persistence_rule": "persist edits",
                },
                "verification_handoff": {
                    "verification_order": ["preview", "runtime"],
                    "required_artifacts": ["output/frontend/index.html"],
                    "acceptance_checks": ["no emoji", "token aligned"],
                },
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
        json.dumps(
            {
                "score": 92,
                "critical_count": 0,
                "alignment_summary": {
                    "runtime_claude_design_protocol": {
                        "passed": True,
                        "observed": "runtime aligned",
                    },
                    "source_claude_design_protocol": {
                        "passed": True,
                        "observed": "source aligned",
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-ui-contract-alignment.json").write_text(
        json.dumps(
            {
                "screen_recipes": {"passed": True, "observed": "hero/proof/cta"},
                "design_context_protocol": {"passed": True, "observed": "tokens/components"},
                "tweak_strategy": {"passed": True, "observed": "density/tone"},
                "verification_handoff": {"passed": True, "observed": "preview/runtime"},
                "theme_entry": {"passed": True, "observed": "theme provider"},
                "navigation_shell": {"passed": True, "observed": "header/nav/cta"},
                "component_imports": {"passed": True, "observed": "@/components/ui/button"},
                "banned_patterns": {"passed": True, "observed": ""},
                "design_tokens": {"passed": True, "observed": "--color-primary"},
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
                    "ui_screen_recipes": True,
                    "ui_design_context_protocol": True,
                    "ui_tweak_strategy": True,
                    "ui_verification_handoff": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    record_stage_progress(project_dir, stage="research", status="completed")
    record_stage_progress(project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(project_dir, {"status": "confirmed", "actor": "pytest"})
    record_stage_progress(project_dir, stage="spec", status="completed")
    record_stage_progress(project_dir, stage="frontend", status="completed")
    save_bound_preview_confirmation(project_dir, {"status": "confirmed", "actor": "pytest"})
    record_stage_progress(project_dir, stage="quality", status="completed")
    record_stage_progress(project_dir, stage="delivery", status="completed")
    _hydrate_release_governance_artifacts(project_dir)


def _prepare_proof_pack_project(project_dir: Path) -> None:
    _prepare_release_ready_project(project_dir)
    output_dir = project_dir / "output"
    (output_dir / "delivery").mkdir(parents=True, exist_ok=True)
    (output_dir / "rehearsal").mkdir(parents=True, exist_ok=True)
    for suffix in ("research", "architecture", "uiux"):
        (output_dir / f"{project_dir.name}-{suffix}.md").write_text("# ok\n", encoding="utf-8")
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
                "screen_recipes": [
                    {
                        "label": "North Star Hero",
                        "section_order": ["hero", "proof", "cta"],
                        "trust_modules": ["proof"],
                        "required_states": ["loading", "empty"],
                    }
                ],
                "design_context_protocol": {
                    "preferred_import_order": ["tokens", "components"],
                    "github_import_targets": ["theme.ts", "design-tokens.css"],
                    "single_source_rule": "single source",
                },
                "tweak_strategy": {
                    "mode": "single-source prototype",
                    "default_controls": ["density", "tone"],
                    "persistence_rule": "persist edits",
                },
                "verification_handoff": {
                    "verification_order": ["preview", "runtime"],
                    "required_artifacts": ["output/frontend/index.html"],
                    "acceptance_checks": ["no emoji", "token aligned"],
                },
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
                "score": 91,
                "critical_count": 0,
                "alignment_summary": {
                    "runtime_claude_design_protocol": {
                        "passed": True,
                        "observed": "runtime aligned",
                    },
                    "source_claude_design_protocol": {
                        "passed": True,
                        "observed": "source aligned",
                    },
                },
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
                "screen_recipes": {
                    "label": "页面配方冻结",
                    "passed": True,
                    "expected": "hero/proof/cta",
                    "observed": "hero/proof/cta",
                },
                "design_context_protocol": {
                    "label": "设计上下文协议",
                    "passed": True,
                    "expected": "tokens/components",
                    "observed": "tokens/components",
                },
                "tweak_strategy": {
                    "label": "Tweaks 变体策略",
                    "passed": True,
                    "expected": "density/tone",
                    "observed": "density/tone",
                },
                "verification_handoff": {
                    "label": "验证与交付协议",
                    "passed": True,
                    "expected": "preview/runtime",
                    "observed": "preview/runtime",
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
                    "ui_screen_recipes": True,
                    "ui_design_context_protocol": True,
                    "ui_tweak_strategy": True,
                    "ui_verification_handoff": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-quality-gate.md").write_text(
        "# 质量门禁报告\n\n**状态**: <span style='color:green'>通过</span>\n**总分**: 90/100\n",
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-quality-gate.md").write_text(
        "# quality gate\npassed\n", encoding="utf-8"
    )
    # Ensure the ready fixture reflects one coherent artifact generation round.
    base_time = time.time() + 1
    for index, artifact_name in enumerate(
        (
        f"{project_dir.name}-ui-review.json",
        f"{project_dir.name}-ui-contract-alignment.json",
        f"{project_dir.name}-frontend-runtime.json",
        f"{project_dir.name}-quality-gate.md",
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
    (output_dir / f"{project_dir.name}-repo-map.md").write_text(
        "# Repo Map\n\nok\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-repo-map.json").write_text(
        json.dumps({"project_name": project_dir.name}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-dependency-graph.md").write_text(
        "# Dependency Graph\n\nok\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-dependency-graph.json").write_text(
        json.dumps(
            {"project_name": project_dir.name, "node_count": 4, "edge_count": 3},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-impact-analysis.md").write_text(
        "# Change Impact Analysis\n\nok\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-impact-analysis.json").write_text(
        json.dumps(
            {"project_name": project_dir.name, "risk_level": "medium"}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_dir.name}-regression-guard.md").write_text(
        "# Regression Guard\n\nok\n", encoding="utf-8"
    )
    (output_dir / f"{project_dir.name}-regression-guard.json").write_text(
        json.dumps(
            {"project_name": project_dir.name, "risk_level": "medium"}, ensure_ascii=False, indent=2
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
        json.dumps({"passed": True, "score": 94}, ensure_ascii=False, indent=2),
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
    _hydrate_release_governance_artifacts(project_dir)


class TestWebAPI:
    def test_health_endpoint(self):
        client = _make_client()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "healthy"

    def test_health_endpoint_alias(self):
        """K8s probes and load balancers use /health directly."""
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "healthy"

    def test_v1_health_endpoint(self):
        """Versioned /api/v1/ prefix should return same result as /api/."""
        client = _make_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_v1_phases_endpoint(self):
        client = _make_client()
        resp = client.get("/api/v1/phases")
        assert resp.status_code == 200
        assert "phases" in resp.json()

    def test_v1_experts_endpoint(self):
        client = _make_client()
        resp = client.get("/api/v1/experts")
        assert resp.status_code == 200
        assert "experts" in resp.json()

    def test_init_and_get_config(self, temp_project_dir: Path):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-demo",
                "description": "api demo project",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "auth",
            },
        )
        assert init_resp.status_code == 200

        config_resp = client.get(
            "/api/config",
            params={"project_dir": str(temp_project_dir)},
        )
        assert config_resp.status_code == 200
        payload = config_resp.json()
        assert payload["name"] == "api-demo"
        assert payload["frontend"] == "react"
        assert payload["language_preferences"] == []
        assert payload["host_compatibility_min_score"] == 80
        assert payload["host_compatibility_min_ready_hosts"] == 1

    def test_policy_get_and_update(self, temp_project_dir: Path):
        client = _make_client()

        preset_resp = client.get("/api/policy/presets")
        assert preset_resp.status_code == 200
        preset_ids = {item["id"] for item in preset_resp.json()["presets"]}
        assert {"default", "balanced", "enterprise"}.issubset(preset_ids)

        get_resp = client.get(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        default_payload = get_resp.json()
        assert default_payload["require_redteam"] is True
        assert default_payload["require_quality_gate"] is True
        assert default_payload["require_rehearsal_verify"] is True
        assert default_payload["min_quality_threshold"] == 80
        assert default_payload["enforce_required_hosts_ready"] is False
        assert default_payload["min_required_host_score"] == 80
        assert default_payload["policy_exists"] is False

        update_resp = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={
                "preset": "enterprise",
                "min_quality_threshold": 88,
                "allowed_cicd_platforms": ["github", "gitlab"],
                "require_rehearsal_verify": True,
                "required_hosts": ["codex-cli", "claude-code"],
                "enforce_required_hosts_ready": True,
                "min_required_host_score": 86,
            },
        )
        assert update_resp.status_code == 200
        updated_payload = update_resp.json()
        assert updated_payload["min_quality_threshold"] == 88
        assert updated_payload["allowed_cicd_platforms"] == ["github", "gitlab"]
        assert updated_payload["require_rehearsal_verify"] is True
        assert updated_payload["require_host_profile"] is True
        assert set(updated_payload["required_hosts"]) == {"codex-cli", "claude-code"}
        assert updated_payload["enforce_required_hosts_ready"] is True
        assert updated_payload["min_required_host_score"] == 86
        assert updated_payload["policy_exists"] is True

        policy_path = temp_project_dir / ".super-dev" / "policy.yaml"
        assert policy_path.exists()

        get_after_resp = client.get(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_after_resp.status_code == 200
        get_after_payload = get_after_resp.json()
        assert get_after_payload["min_quality_threshold"] == 88
        assert set(get_after_payload["required_hosts"]) == {"codex-cli", "claude-code"}

    def test_policy_update_rejects_invalid_values(self, temp_project_dir: Path):
        client = _make_client()
        invalid_threshold = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={"min_quality_threshold": 101},
        )
        assert invalid_threshold.status_code == 400

        invalid_cicd = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={"allowed_cicd_platforms": ["github", "unknown"]},
        )
        assert invalid_cicd.status_code == 400

        invalid_host = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={"required_hosts": ["codex-cli", "not-a-host"]},
        )
        assert invalid_host.status_code == 400

        invalid_required_score = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={"min_required_host_score": 101},
        )
        assert invalid_required_score.status_code == 400

        invalid_preset = client.put(
            "/api/policy",
            params={"project_dir": str(temp_project_dir)},
            json={"preset": "not-exists"},
        )
        assert invalid_preset.status_code == 400

    def test_workflow_run_and_status(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-workflow",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )
        assert init_resp.status_code == 200

        async def fake_run(self, phases=None, context=None, **kwargs):
            return {
                Phase.DISCOVERY: PhaseResult(
                    phase=Phase.DISCOVERY,
                    success=True,
                    duration=0.01,
                    quality_score=90.0,
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["discovery"]},
        )
        assert run_resp.status_code == 200
        run_payload = run_resp.json()
        assert run_payload["status"] == "started"
        run_id = run_payload["run_id"]
        assert run_id

        status_resp = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        status_payload = status_resp.json()
        assert status_payload["run_id"] == run_id
        assert status_payload["status"] in {
            "completed",
            "failed",
            "running",
            "queued",
            "cancelling",
            "cancelled",
        }
        assert status_payload["status_normalized"] in {
            "completed",
            "failed",
            "running",
            "queued",
            "cancelled",
            "unknown",
        }
        assert "progress" in status_payload
        assert "pipeline_summary" in status_payload
        assert status_payload["pipeline_summary"]["current_stage_id"] in {
            "research",
            "core_docs",
            "confirmation_gate",
            "spec",
            "frontend",
            "backend",
            "quality",
            "delivery",
        }

        # 持久化文件存在
        persisted = temp_project_dir / ".super-dev" / "runs" / f"{run_id}.json"
        assert persisted.exists()
        persisted_payload = json.loads(persisted.read_text(encoding="utf-8"))
        assert persisted_payload["status_normalized"] in {
            "completed",
            "failed",
            "running",
            "queued",
            "cancelled",
            "unknown",
        }

        # 模拟进程重启后仍可从磁盘读取
        web_api._RUN_STORE.clear()
        status_resp_2 = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp_2.status_code == 200
        assert status_resp_2.json()["run_id"] == run_id

    def test_workflow_status_returns_404_for_corrupted_run_state_file(self, temp_project_dir: Path):
        client = _make_client()
        runs_dir = temp_project_dir / ".super-dev" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_id = "broken-run"
        (runs_dir / f"{run_id}.json").write_text("{invalid-json", encoding="utf-8")

        status_resp = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 404

    def test_store_run_state_creates_lock_file(self, temp_project_dir: Path):
        run_id = "lock-check"
        web_api._store_run_state(
            run_id,
            persist_dir=temp_project_dir,
            status="queued",
            message="lock",
            progress=0,
        )
        lock_file = temp_project_dir / ".super-dev" / "runs" / ".runs.lock"
        assert lock_file.exists()

    def test_workflow_status_marks_confirmation_gate_waiting(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-research.md").write_text("# research", encoding="utf-8")
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")

        web_api._store_run_state(
            "pipewait01",
            persist_dir=temp_project_dir,
            status="running",
            message="waiting docs confirm",
            requested_phases=["discovery", "intelligence", "drafting"],
            completed_phases=["discovery", "intelligence", "drafting"],
            progress=60,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/pipewait01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["pipeline_summary"]["current_stage_id"] == "confirmation_gate"
        assert "等待用户确认" in payload["pipeline_summary"]["current_stage_name"]
        assert "等待用户确认" in payload["pipeline_summary"]["blocker"]
        confirmation_stage = next(
            item
            for item in payload["pipeline_summary"]["stages"]
            if item["id"] == "confirmation_gate"
        )
        assert confirmation_stage["status"] == "waiting"

    @pytest.mark.parametrize("work_mode", ["evolve", "variant", "patch"])
    def test_workflow_status_blocks_existing_project_without_baseline(
        self,
        temp_project_dir: Path,
        work_mode: str,
    ):
        client = _make_client()

        (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "workflow-state.json").write_text(
            json.dumps({"work_mode": work_mode}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        web_api._store_run_state(
            f"{work_mode}-baseline01",
            persist_dir=temp_project_dir,
            status="running",
            message="existing project baseline required",
            requested_phases=["discovery"],
            completed_phases=[],
            progress=5,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            f"/api/workflow/status/{work_mode}-baseline01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        summary = resp.json()["pipeline_summary"]
        assert summary["work_mode"] == work_mode
        assert summary["workflow_status"] == "missing_baseline"
        assert summary["artifacts"]["baseline_required"] is True
        assert summary["artifacts"]["baseline"] is False
        assert summary["current_stage_canonical_id"] == "baseline"
        assert summary["baseline_governance"]["required"] is True
        assert summary["baseline_governance"]["status"] == "missing_audit"
        assert summary["baseline_governance"]["entry_gate"] == "missing_baseline"
        assert summary["baseline_governance"]["ready"] is False
        assert summary["baseline_governance"]["can_enter_delta_flow"] is False
        assert (
            summary["baseline_governance"]["recommended_command"]
            == "在宿主里先扫描当前项目并建立 baseline，再继续当前流程"
        )

    def test_workflow_status_waits_for_baseline_confirmation_after_audit(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "output").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "workflow-state.json").write_text(
            json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (temp_project_dir / "output" / f"{temp_project_dir.name}-baseline-audit.md").write_text(
            "# baseline\n",
            encoding="utf-8",
        )
        save_baseline_confirmation(
            temp_project_dir,
            {
                "status": "pending_review",
                "comment": "先确认当前项目边界和差量计划",
                "actor": "pytest",
            },
        )

        web_api._store_run_state(
            "baseline-confirm01",
            persist_dir=temp_project_dir,
            status="running",
            message="baseline confirmation pending",
            requested_phases=["discovery"],
            completed_phases=[],
            progress=10,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/baseline-confirm01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        summary = resp.json()["pipeline_summary"]
        assert summary["workflow_status"] == "waiting_baseline_confirmation"
        assert summary["artifacts"]["baseline_required"] is True
        assert summary["artifacts"]["baseline"] is True
        assert summary["current_stage_canonical_id"] == "baseline"
        assert "baseline 确认" in summary["recommended_command"]
        assert summary["baseline_governance"]["status"] == "pending_confirmation"
        assert summary["baseline_governance"]["entry_gate"] == "waiting_baseline_confirmation"
        assert summary["baseline_governance"]["confirmation_status"] == "pending_review"
        assert summary["baseline_governance"]["ready"] is False
        assert summary["baseline_governance"]["can_enter_delta_flow"] is False
        assert (
            summary["baseline_governance"]["recommended_command"]
            == "在宿主里先确认 baseline；如果通过，直接说“baseline 确认，可以继续当前流程”"
        )

    def test_workflow_status_prioritizes_resume_gate_over_missing_baseline(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "workflow-state.json").write_text(
            json.dumps({"work_mode": "variant"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        save_resume_gate(
            temp_project_dir,
            {
                "status": "pending_review",
                "comment": "先确认从哪里恢复",
                "actor": "pytest",
            },
        )

        web_api._store_run_state(
            "resume-gate01",
            persist_dir=temp_project_dir,
            status="running",
            message="resume gate pending",
            requested_phases=["discovery"],
            completed_phases=[],
            progress=5,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/resume-gate01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        summary = resp.json()["pipeline_summary"]
        assert summary["work_mode"] == "variant"
        assert summary["workflow_status"] == "waiting_resume_gate"
        assert summary["resume_gate"]["status"] == "pending_review"
        assert summary["artifacts"]["baseline_required"] is True
        assert summary["artifacts"]["baseline"] is False
        assert summary["baseline_governance"]["entry_gate"] == "waiting_resume_gate"
        assert summary["baseline_governance"]["resume_state"] == "pending_review"
        assert summary["baseline_governance"]["can_enter_delta_flow"] is False
        assert (
            summary["baseline_governance"]["blocking_reason"]
            == "当前存在恢复门，必须先明确恢复点，再继续当前流程。"
        )
        assert (
            summary["baseline_governance"]["recommended_command"]
            == "在宿主里先确认恢复点；如果通过，直接说“恢复点确认，可以继续当前流程”"
        )

    def test_workflow_status_requires_frontend_runtime_report(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-research.md").write_text("# research", encoding="utf-8")
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (frontend_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        (frontend_dir / "styles.css").write_text("body{}", encoding="utf-8")
        (frontend_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")

        (temp_project_dir / ".super-dev" / "changes" / "demo-change").mkdir(
            parents=True, exist_ok=True
        )
        (temp_project_dir / ".super-dev" / "changes" / "demo-change" / "proposal.md").write_text(
            "# proposal", encoding="utf-8"
        )
        (temp_project_dir / ".super-dev" / "changes" / "demo-change" / "tasks.md").write_text(
            "# tasks", encoding="utf-8"
        )

        save_docs_confirmation(
            temp_project_dir,
            {"status": "confirmed", "comment": "ok", "actor": "test", "run_id": "front01"},
        )

        web_api._store_run_state(
            "front01",
            persist_dir=temp_project_dir,
            status="running",
            message="frontend pending validation",
            requested_phases=["delivery"],
            completed_phases=["discovery", "intelligence", "drafting"],
            progress=55,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/front01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        summary = resp.json()["pipeline_summary"]
        frontend_stage = next(item for item in summary["stages"] if item["id"] == "frontend")
        assert frontend_stage["status"] in {"running", "pending"}
        assert summary["artifacts"]["frontend"] is False
        assert summary["artifacts"]["frontend_runtime_report"] == ""

    def test_workflow_status_requires_ready_delivery_manifest_and_rehearsal_report(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        rehearsal_dir = output_dir / "rehearsal"
        rehearsal_dir.mkdir(parents=True, exist_ok=True)
        delivery_dir = output_dir / "delivery"
        delivery_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "demo-research.md").write_text("# research", encoding="utf-8")
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-quality-gate.md").write_text("# qa", encoding="utf-8")
        (output_dir / "demo-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
        (temp_project_dir / ".super-dev" / "changes" / "demo-change").mkdir(
            parents=True, exist_ok=True
        )
        (temp_project_dir / ".super-dev" / "changes" / "demo-change" / "proposal.md").write_text(
            "# proposal", encoding="utf-8"
        )
        (temp_project_dir / ".super-dev" / "changes" / "demo-change" / "tasks.md").write_text(
            "# tasks", encoding="utf-8"
        )
        (temp_project_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
        (delivery_dir / "demo-delivery-manifest.json").write_text(
            '{"status": "ready"}', encoding="utf-8"
        )
        (rehearsal_dir / "demo-rehearsal-report.json").write_text(
            '{"passed": false}', encoding="utf-8"
        )

        save_docs_confirmation(
            temp_project_dir,
            {"status": "confirmed", "comment": "ok", "actor": "test", "run_id": "delivery01"},
        )

        web_api._store_run_state(
            "delivery01",
            persist_dir=temp_project_dir,
            status="running",
            message="delivery pending rehearsal",
            requested_phases=["deployment"],
            completed_phases=["discovery", "intelligence", "drafting", "redteam", "qa"],
            progress=88,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/delivery01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        summary = resp.json()["pipeline_summary"]
        delivery_stage = next(item for item in summary["stages"] if item["id"] == "delivery")
        assert delivery_stage["status"] in {"running", "pending"}
        assert summary["artifacts"]["delivery"] is False
        assert summary["artifacts"]["delivery_manifest_ready"] is True
        assert summary["artifacts"]["rehearsal_report_passed"] is False
        assert "发布演练验证" in summary["blocker"]

    def test_workflow_status_includes_knowledge_summary(self, temp_project_dir: Path):
        client = _make_client()

        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            json.dumps(
                {
                    "local_knowledge": [
                        {
                            "source": "knowledge/development/frontend-engineering-complete.md",
                            "title": "frontend",
                        },
                        {"source": "knowledge/design/ux-system-deep-dive.md", "title": "ux"},
                    ],
                    "web_knowledge": [
                        {"source": "web", "title": "example"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        web_api._store_run_state(
            "knowledge01",
            persist_dir=temp_project_dir,
            status="running",
            message="knowledge",
            requested_phases=["discovery"],
            completed_phases=[],
            progress=10,
            project_dir=str(temp_project_dir),
            results=[],
        )

        resp = client.get(
            "/api/workflow/status/knowledge01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        payload = resp.json()["pipeline_summary"]["knowledge"]
        assert payload["cache_exists"] is True
        assert payload["local_hits"] == 2
        assert payload["web_hits"] == 1
        assert payload["top_local_sources"]

    def test_workflow_docs_confirmation_roundtrip(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")

        web_api._store_run_state(
            "confirm01",
            persist_dir=temp_project_dir,
            status="running",
            message="docs ready",
            requested_phases=["drafting"],
            completed_phases=["drafting"],
            progress=50,
            project_dir=str(temp_project_dir),
            results=[],
        )

        update_resp = client.post(
            "/api/workflow/docs-confirmation",
            params={"project_dir": str(temp_project_dir), "run_id": "confirm01"},
            json={"status": "confirmed", "comment": "文档已确认", "actor": "user"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "confirmed"
        assert update_resp.json()["artifact_binding"]["stage"] == "docs"
        assert update_resp.json()["artifact_binding"]["file_count"] == 3
        assert update_resp.json()["artifact_binding"]["digest"]
        assert update_resp.json()["ledger_entry"]["status"] == "confirmed"
        assert update_resp.json()["binding_matches_current"] is True

        get_resp = client.get(
            "/api/workflow/docs-confirmation",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "confirmed"
        assert get_resp.json()["comment"] == "文档已确认"
        assert get_resp.json()["artifact_binding"]["digest"]
        assert get_resp.json()["ledger_entry"]["artifact_binding"]["digest"]
        assert get_resp.json()["binding_matches_current"] is True

        status_resp = client.get(
            "/api/workflow/status/confirm01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["docs_confirmation"]["status"] == "confirmed"
        confirmation_stage = next(
            item for item in summary["stages"] if item["id"] == "confirmation_gate"
        )
        assert confirmation_stage["status"] == "completed"

    def test_workflow_baseline_confirmation_roundtrip(self, temp_project_dir: Path):
        client = _make_client()
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "review-state").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "workflow-state.json").write_text(
            json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
            "# baseline\n", encoding="utf-8"
        )

        update_resp = client.post(
            "/api/workflow/baseline-confirmation",
            params={"project_dir": str(temp_project_dir), "run_id": "baseline01"},
            json={"status": "confirmed", "comment": "baseline 已确认", "actor": "user"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "confirmed"
        assert update_resp.json()["baseline_governance"]["status"] == "confirmed"
        assert update_resp.json()["workflow_context"]["workflow_status"] in {
            "missing_core_docs",
            "waiting_docs_confirmation",
            "missing_research",
            "missing_spec",
            "ready",
        }

        get_resp = client.get(
            "/api/workflow/baseline-confirmation",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "confirmed"
        assert get_resp.json()["comment"] == "baseline 已确认"
        assert get_resp.json()["baseline_governance"]["status"] == "confirmed"
        assert get_resp.json()["workflow_context"]["baseline_confirmation_status"] == "confirmed"

        web_api._store_run_state(
            "baseline01",
            persist_dir=temp_project_dir,
            status="running",
            message="baseline confirmed",
            requested_phases=["discovery"],
            completed_phases=[],
            progress=20,
            project_dir=str(temp_project_dir),
            results=[],
        )
        status_resp = client.get(
            "/api/workflow/status/baseline01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["baseline_confirmation"]["status"] == "confirmed"
        assert summary["baseline_governance"]["status"] == "confirmed"
        assert summary["baseline_governance"]["entry_gate"] == "ready"
        assert summary["baseline_governance"]["ready"] is True
        assert summary["baseline_governance"]["can_enter_delta_flow"] is True
        assert summary["baseline_governance"]["recommended_command"] == "在宿主里说“继续当前流程”"

    def test_workflow_ui_revision_roundtrip(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-quality-gate.md").write_text("# quality", encoding="utf-8")

        web_api._store_run_state(
            "ui-revision01",
            persist_dir=temp_project_dir,
            status="running",
            message="quality ready",
            requested_phases=["qa"],
            completed_phases=["drafting", "qa"],
            progress=75,
            project_dir=str(temp_project_dir),
            results=[],
        )

        update_resp = client.post(
            "/api/workflow/ui-revision",
            params={"project_dir": str(temp_project_dir), "run_id": "ui-revision01"},
            json={
                "status": "revision_requested",
                "comment": "Hero 太空，需要重做",
                "actor": "user",
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "revision_requested"

        get_resp = client.get(
            "/api/workflow/ui-revision",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "revision_requested"
        assert get_resp.json()["comment"] == "Hero 太空，需要重做"

        status_resp = client.get(
            "/api/workflow/status/ui-revision01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["ui_revision"]["status"] == "revision_requested"
        assert "UI 改版请求" in summary["blocker"]

    def test_workflow_preview_confirmation_roundtrip(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps({"passed": True, "summary": "frontend ready"}, ensure_ascii=False),
            encoding="utf-8",
        )
        change_dir = temp_project_dir / ".super-dev" / "changes" / "preview-demo"
        change_dir.mkdir(parents=True, exist_ok=True)
        (change_dir / "proposal.md").write_text("# proposal", encoding="utf-8")
        (change_dir / "tasks.md").write_text("- [ ] frontend", encoding="utf-8")
        save_bound_docs_confirmation(
            temp_project_dir,
            {
                "status": "confirmed",
                "comment": "文档已确认",
                "actor": "pytest",
                "run_id": "preview01",
            },
        )

        web_api._store_run_state(
            "preview01",
            persist_dir=temp_project_dir,
            status="running",
            message="frontend ready",
            requested_phases=["delivery"],
            completed_phases=["drafting"],
            progress=68,
            project_dir=str(temp_project_dir),
            results=[],
        )

        pending_resp = client.get(
            "/api/workflow/status/preview01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert pending_resp.status_code == 200
        pending_summary = pending_resp.json()["pipeline_summary"]
        assert pending_summary["workflow_status"] == "waiting_preview_confirmation"
        assert pending_summary["workflow_mode"] == "revise"
        assert pending_summary["preview_confirmation"]["status"] == "pending_review"
        assert pending_summary["action_card"]["mode"] == "revise"
        assert (
            pending_summary["action_card"]["machine_action"]
            == "在宿主里确认前端预览；如果通过，直接说\u201c前端预览确认，可以继续\u201d"
        )
        preview_stage = next(
            item for item in pending_summary["stages"] if item["id"] == "preview_gate"
        )
        assert preview_stage["status"] == "waiting"

        update_resp = client.post(
            "/api/workflow/preview-confirmation",
            params={"project_dir": str(temp_project_dir), "run_id": "preview01"},
            json={"status": "revision_requested", "comment": "预览还需要调一下", "actor": "user"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "revision_requested"
        assert update_resp.json()["artifact_binding"]["stage"] == "preview"
        assert update_resp.json()["artifact_binding"]["file_count"] >= 1
        assert update_resp.json()["artifact_binding"]["digest"]
        assert update_resp.json()["ledger_entry"]["status"] == "revision_requested"
        assert update_resp.json()["binding_matches_current"] is True

        get_resp = client.get(
            "/api/workflow/preview-confirmation",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "revision_requested"
        assert get_resp.json()["comment"] == "预览还需要调一下"
        assert get_resp.json()["artifact_binding"]["digest"]
        assert get_resp.json()["binding_matches_current"] is True

        status_resp = client.get(
            "/api/workflow/status/preview01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["preview_confirmation"]["status"] == "revision_requested"
        assert "预览确认" in summary["blocker"] or "预览评审" in summary["blocker"]
        assert summary["action_card"]["mode"] == "revise"
        assert "继续调 UI" in summary["action_card"]["examples"]

    def test_workflow_architecture_revision_roundtrip(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")

        web_api._store_run_state(
            "architecture-revision01",
            persist_dir=temp_project_dir,
            status="running",
            message="drafting ready",
            requested_phases=["drafting"],
            completed_phases=["drafting"],
            progress=55,
            project_dir=str(temp_project_dir),
            results=[],
        )

        update_resp = client.post(
            "/api/workflow/architecture-revision",
            params={"project_dir": str(temp_project_dir), "run_id": "architecture-revision01"},
            json={
                "status": "revision_requested",
                "comment": "架构分层不清晰，需要重构模块边界",
                "actor": "user",
            },
        )
        assert update_resp.status_code == 200

        get_resp = client.get(
            "/api/workflow/architecture-revision",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "revision_requested"

        status_resp = client.get(
            "/api/workflow/status/architecture-revision01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["architecture_revision"]["status"] == "revision_requested"
        assert "架构返工请求" in summary["blocker"]

    def test_workflow_quality_revision_roundtrip(self, temp_project_dir: Path):
        client = _make_client()

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-quality-gate.md").write_text("# quality", encoding="utf-8")

        web_api._store_run_state(
            "quality-revision01",
            persist_dir=temp_project_dir,
            status="running",
            message="qa ready",
            requested_phases=["qa"],
            completed_phases=["drafting", "qa"],
            progress=78,
            project_dir=str(temp_project_dir),
            results=[],
        )

        update_resp = client.post(
            "/api/workflow/quality-revision",
            params={"project_dir": str(temp_project_dir), "run_id": "quality-revision01"},
            json={
                "status": "revision_requested",
                "comment": "质量门禁未通过，需要修复安全问题",
                "actor": "user",
            },
        )
        assert update_resp.status_code == 200

        get_resp = client.get(
            "/api/workflow/quality-revision",
            params={"project_dir": str(temp_project_dir)},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "revision_requested"

        status_resp = client.get(
            "/api/workflow/status/quality-revision01",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        summary = status_resp.json()["pipeline_summary"]
        assert summary["quality_revision"]["status"] == "revision_requested"
        assert "质量返工请求" in summary["blocker"]

    def test_workflow_run_passes_request_context(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-context",
                "description": "from-init",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )
        assert init_resp.status_code == 200

        observed: dict[str, str] = {}

        async def fake_run(self, phases=None, context=None, **kwargs):
            assert context is not None
            observed["name"] = context.user_input.get("name")
            observed["description"] = context.user_input.get("description")
            observed["platform"] = context.user_input.get("platform")
            observed["frontend"] = context.user_input.get("frontend")
            observed["backend"] = context.user_input.get("backend")
            observed["domain"] = context.user_input.get("domain")
            observed["language_preferences"] = context.user_input.get("language_preferences")
            observed["cicd"] = context.user_input.get("cicd")
            return {
                Phase.DISCOVERY: PhaseResult(
                    phase=Phase.DISCOVERY,
                    success=True,
                    duration=0.01,
                    quality_score=90.0,
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={
                "phases": ["discovery"],
                "name": "override-name",
                "description": "override-desc",
                "platform": "mobile",
                "frontend": "vue",
                "backend": "python",
                "domain": "medical",
                "language_preferences": ["python", "typescript", "rust"],
                "cicd": "gitlab",
            },
        )
        assert run_resp.status_code == 200
        assert observed == {
            "name": "override-name",
            "description": "override-desc",
            "platform": "mobile",
            "frontend": "vue",
            "backend": "python",
            "domain": "medical",
            "language_preferences": ["python", "typescript", "rust"],
            "cicd": "gitlab",
        }

    def test_workflow_status_includes_redteam_output(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-redteam",
                "platform": "web",
                "frontend": "react",
                "backend": "python",
            },
        )
        assert init_resp.status_code == 200

        async def fake_run(self, phases=None, context=None, **kwargs):
            return {
                Phase.REDTEAM: PhaseResult(
                    phase=Phase.REDTEAM,
                    success=True,
                    duration=0.02,
                    quality_score=86.0,
                    output={
                        "status": "redteam_complete",
                        "score": 86,
                        "critical_count": 0,
                        "high_count": 1,
                        "issues": {
                            "security": [
                                {
                                    "severity": "high",
                                    "category": "命令执行",
                                    "description": "检测到高风险代码模式: app.py:12",
                                    "recommendation": "避免 shell=True",
                                    "file_path": str(temp_project_dir / "app.py"),
                                    "line": 12,
                                }
                            ]
                        },
                    },
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert run_resp.status_code == 409
        payload = run_resp.json()["detail"]
        assert payload["gate"] == "docs_confirmation"
        assert payload["action"] == "workflow_run"
        assert payload["details"]["requested_phases"] == ["redteam"]

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "api-redteam-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "api-redteam-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "api-redteam-uiux.md").write_text("# uiux", encoding="utf-8")
        save_docs_confirmation(
            temp_project_dir,
            {
                "status": "confirmed",
                "comment": "legacy confirmation",
                "actor": "pytest",
                "run_id": "legacy-confirmed",
            },
        )

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert run_resp.status_code == 409
        legacy_detail = run_resp.json()["detail"]
        assert legacy_detail["gate"] == "docs_confirmation"
        assert legacy_detail["details"]["binding_matches_current"] is False

        confirm_resp = client.post(
            "/api/workflow/docs-confirmation",
            params={"project_dir": str(temp_project_dir), "run_id": "redteam-bound"},
            json={"status": "confirmed", "comment": "文档确认", "actor": "user"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["binding_matches_current"] is True

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert run_resp.status_code == 200
        run_id = run_resp.json()["run_id"]

        status_resp = client.get(f"/api/workflow/status/{run_id}", params={"project_dir": str(temp_project_dir)})
        assert status_resp.status_code == 200
        payload = status_resp.json()
        assert payload["status"] in {
            "completed",
            "failed",
            "running",
            "queued",
            "cancelling",
            "cancelled",
        }
        assert payload["results"]
        redteam_result = payload["results"][0]
        assert redteam_result["phase"] == "redteam"
        assert redteam_result["output"]["issues"]["security"][0]["line"] == 12

        (output_dir / "api-redteam-uiux.md").write_text("# uiux v2", encoding="utf-8")
        rerun_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert rerun_resp.status_code == 409
        rerun_detail = rerun_resp.json()["detail"]
        assert rerun_detail["details"]["binding_matches_current"] is False

    def test_workflow_run_requires_preview_confirmation_for_late_phases(
        self, temp_project_dir: Path, monkeypatch
    ):
        client = _make_client()
        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-preview",
                "platform": "web",
                "frontend": "react",
                "backend": "python",
            },
        )
        assert init_resp.status_code == 200
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "api-preview-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "api-preview-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "api-preview-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "api-preview-ui-contract.json").write_text(
            json.dumps({"style_direction": "clean"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "api-preview-ui-contract-alignment.json").write_text(
            json.dumps({"design_tokens": {"passed": True}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "api-preview-frontend-runtime.json").write_text(
            json.dumps({"passed": True, "summary": "frontend ready"}, ensure_ascii=False),
            encoding="utf-8",
        )

        save_bound_docs_confirmation(
            temp_project_dir,
            {
                "status": "confirmed",
                "comment": "文档已确认",
                "actor": "pytest",
                "run_id": "preview-gate-docs",
            },
        )

        async def fake_run(self, phases=None, context=None, **kwargs):
            return {
                Phase.REDTEAM: PhaseResult(
                    phase=Phase.REDTEAM,
                    success=True,
                    duration=0.01,
                    quality_score=90.0,
                    output={"status": "ok"},
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        blocked_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert blocked_resp.status_code == 409
        detail = blocked_resp.json()["detail"]
        assert detail["gate"] == "preview_confirmation"
        assert detail["details"]["binding_matches_current"] is False

        confirm_resp = client.post(
            "/api/workflow/preview-confirmation",
            params={"project_dir": str(temp_project_dir), "run_id": "preview-bound"},
            json={"status": "confirmed", "comment": "预览确认", "actor": "user"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["binding_matches_current"] is True

        allowed_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert allowed_resp.status_code == 200

        (output_dir / "api-preview-frontend-runtime.json").write_text(
            json.dumps({"passed": True, "summary": "frontend ready v2"}, ensure_ascii=False),
            encoding="utf-8",
        )
        stale_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["redteam"]},
        )
        assert stale_resp.status_code == 409
        stale_detail = stale_resp.json()["detail"]
        assert stale_detail["gate"] == "preview_confirmation"
        assert stale_detail["details"]["binding_matches_current"] is False

    def test_workflow_run_invalid_phase(self, temp_project_dir: Path):
        client = _make_client()
        client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-invalid-phase",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["not-a-phase"]},
        )
        assert run_resp.status_code == 400

    def test_workflow_run_accepts_canonical_phase_name(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()
        client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-canonical-phase",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )

        captured = {}

        async def fake_run(self, phases=None, context=None, **kwargs):
            captured["phases"] = [phase.value for phase in (phases or [])]
            return {
                Phase.DISCOVERY: PhaseResult(
                    phase=Phase.DISCOVERY,
                    success=True,
                    duration=0.01,
                    quality_score=90.0,
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["research"]},
        )
        assert run_resp.status_code == 200
        assert captured["phases"] == ["discovery", "intelligence"]

    def test_init_rejects_invalid_host_compatibility_threshold(self, temp_project_dir: Path):
        client = _make_client()
        resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-invalid-threshold",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "host_compatibility_min_score": 120,
            },
        )
        assert resp.status_code in (400, 422)

    def test_workflow_status_not_found(self):
        client = _make_client()
        status_resp = client.get("/api/workflow/status/does-not-exist")
        assert status_resp.status_code == 404

    def test_workflow_runs_history(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={"name": "api-history", "platform": "web", "frontend": "react", "backend": "node"},
        )
        assert init_resp.status_code == 200

        async def fake_run(self, phases=None, context=None, **kwargs):
            return {
                Phase.DISCOVERY: PhaseResult(
                    phase=Phase.DISCOVERY,
                    success=True,
                    duration=0.01,
                    quality_score=90.0,
                )
            }

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["discovery"]},
        )
        assert run_resp.status_code == 200

        history_resp = client.get(
            "/api/workflow/runs",
            params={"project_dir": str(temp_project_dir), "limit": 10},
        )
        assert history_resp.status_code == 200
        payload = history_resp.json()
        assert payload["count"] >= 1
        assert isinstance(payload["runs"], list)
        assert "pipeline_summary" in payload["runs"][0]

        bad_limit_resp = client.get(
            "/api/workflow/runs",
            params={"project_dir": str(temp_project_dir), "limit": 0},
        )
        assert bad_limit_resp.status_code == 400

    def test_workflow_artifacts_list_and_archive(self, temp_project_dir: Path):
        client = _make_client()
        run_id = "artifact001"
        web_api._store_run_state(
            run_id,
            persist_dir=temp_project_dir,
            status="completed",
            project_dir=str(temp_project_dir),
            requested_phases=["discovery", "deployment"],
            completed_phases=["discovery", "deployment"],
            progress=100,
            message="完成",
            cancel_requested=False,
            started_at=web_api._utc_now(),
            finished_at=web_api._utc_now(),
            results=[],
        )

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text("# demo", encoding="utf-8")
        (temp_project_dir / ".env.deploy.example").write_text("FOO=bar", encoding="utf-8")

        list_resp = client.get(
            f"/api/workflow/artifacts/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["run_id"] == run_id
        assert payload["count"] >= 2
        relative_paths = {item["relative_path"] for item in payload["items"]}
        assert "output/demo-prd.md" in relative_paths
        assert ".env.deploy.example" in relative_paths

        archive_resp = client.get(
            f"/api/workflow/artifacts/{run_id}/archive",
            params={"project_dir": str(temp_project_dir)},
        )
        assert archive_resp.status_code == 200
        assert archive_resp.headers.get("content-type", "").startswith("application/zip")
        disposition = archive_resp.headers.get("content-disposition", "")
        assert f"workflow-{run_id}-artifacts.zip" in disposition
        assert len(archive_resp.content) > 0

    def test_workflow_artifacts_not_found(self, temp_project_dir: Path):
        client = _make_client()
        list_resp = client.get(
            "/api/workflow/artifacts/not-exists",
            params={"project_dir": str(temp_project_dir)},
        )
        assert list_resp.status_code == 404

        archive_resp = client.get(
            "/api/workflow/artifacts/not-exists/archive",
            params={"project_dir": str(temp_project_dir)},
        )
        assert archive_resp.status_code == 404

    def test_workflow_ui_review_summary_and_screenshot(self, temp_project_dir: Path):
        client = _make_client()
        run_id = "uireview01"
        web_api._store_run_state(
            run_id,
            persist_dir=temp_project_dir,
            status="completed",
            project_dir=str(temp_project_dir),
            requested_phases=["qa"],
            completed_phases=["qa"],
            progress=100,
            message="完成",
            cancel_requested=False,
            started_at=web_api._utc_now(),
            finished_at=web_api._utc_now(),
            results=[],
        )

        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps(
                {
                    "project_name": "demo",
                    "score": 88,
                    "critical_count": 0,
                    "high_count": 1,
                    "medium_count": 2,
                    "passed": True,
                    "findings": [
                        {
                            "level": "high",
                            "title": "CTA 层级不足",
                            "description": "首屏 CTA 不够突出",
                            "recommendation": "增强 CTA 层级",
                            "evidence": [],
                        }
                    ],
                    "strengths": ["结构完整"],
                    "notes": [],
                    "alignment_summary": {
                        "runtime_claude_design_protocol": {
                            "passed": False,
                            "observed": "mismatch=screen_recipes",
                        },
                        "source_claude_design_protocol": {
                            "passed": True,
                            "observed": "source aligned",
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "Editorial workspace",
                    "screen_recipes": [{"label": "North Star Hero"}],
                    "design_context_protocol": {"single_source_rule": "single source"},
                    "tweak_strategy": {"mode": "single-source prototype"},
                    "verification_handoff": {"verification_order": ["preview"]},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_screen_recipes": True,
                        "ui_design_context_protocol": True,
                        "ui_tweak_strategy": True,
                        "ui_verification_handoff": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.md").write_text("# ui review", encoding="utf-8")
        screenshot_dir = output_dir / "ui-review"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (40, 30), "#ffffff").save(screenshot_dir / "demo-preview-desktop.png")

        resp = client.get(
            f"/api/workflow/ui-review/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["run_id"] == run_id
        assert payload["summary"]["score"] == 88
        assert payload["frontend_governance_summary"]["state"] == "source_runtime_drift"
        assert payload["runtime_claude_design_protocol"]["observed"] == "mismatch=screen_recipes"
        assert payload["source_claude_design_protocol"]["observed"] == "source aligned"
        assert payload["screenshot"]["exists"] is True
        assert payload["report_path"].endswith("demo-ui-review.md")

        screenshot_resp = client.get(
            f"/api/workflow/ui-review/{run_id}/screenshot",
            params={"project_dir": str(temp_project_dir)},
        )
        assert screenshot_resp.status_code == 200
        assert screenshot_resp.headers.get("content-type", "").startswith("image/png")

    def test_workflow_cancel_not_found(self):
        client = _make_client()
        cancel_resp = client.post("/api/workflow/cancel/does-not-exist")
        assert cancel_resp.status_code == 404

    def test_workflow_cancel_queued(self, temp_project_dir: Path):
        client = _make_client()
        run_id = "queued001"
        web_api._store_run_state(
            run_id,
            persist_dir=temp_project_dir,
            status="queued",
            project_dir=str(temp_project_dir),
            requested_phases=["discovery"],
            completed_phases=[],
            progress=0,
            message="工作流排队中",
            cancel_requested=False,
            started_at=web_api._utc_now(),
            finished_at=None,
            results=[],
        )

        cancel_resp = client.post(
            f"/api/workflow/cancel/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert cancel_resp.status_code == 200
        payload = cancel_resp.json()
        assert payload["status"] == "cancelled"

        status_resp = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "cancelled"

    def test_workflow_cancel_running(self, temp_project_dir: Path):
        client = _make_client()
        run_id = "running001"
        web_api._store_run_state(
            run_id,
            persist_dir=temp_project_dir,
            status="running",
            project_dir=str(temp_project_dir),
            requested_phases=["discovery", "qa"],
            completed_phases=["discovery"],
            progress=50,
            message="工作流运行中",
            cancel_requested=False,
            started_at=web_api._utc_now(),
            finished_at=None,
            results=[],
        )

        cancel_resp = client.post(
            f"/api/workflow/cancel/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert cancel_resp.status_code == 200
        payload = cancel_resp.json()
        assert payload["status"] == "cancelling"

        status_resp = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        status_payload = status_resp.json()
        assert status_payload["status"] == "cancelling"
        assert status_payload["cancel_requested"] is True

    def test_workflow_cancel_requested_keeps_cancelled_when_background_errors(
        self, temp_project_dir: Path, monkeypatch
    ):
        client = _make_client()

        init_resp = client.post(
            "/api/init",
            params={"project_dir": str(temp_project_dir)},
            json={
                "name": "api-cancel-error",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )
        assert init_resp.status_code == 200

        async def fake_run(self, phases=None, context=None, **kwargs):
            for current_run_id, run in list(web_api._RUN_STORE.items()):
                if run.get("status") in {"queued", "running", "cancelling"}:
                    web_api._store_run_state(
                        current_run_id,
                        persist_dir=temp_project_dir,
                        cancel_requested=True,
                        status="cancelling",
                        message="工作流取消中",
                    )
            raise RuntimeError("boom")

        monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)

        run_resp = client.post(
            "/api/workflow/run",
            params={"project_dir": str(temp_project_dir)},
            json={"phases": ["discovery"]},
        )
        assert run_resp.status_code == 200
        run_id = run_resp.json()["run_id"]
        assert run_id

        status_resp = client.get(
            f"/api/workflow/status/{run_id}",
            params={"project_dir": str(temp_project_dir)},
        )
        assert status_resp.status_code == 200
        status_payload = status_resp.json()
        assert status_payload["status"] == "cancelled"
        assert status_payload["message"] == "工作流已取消"
        assert status_payload["cancel_requested"] is True

    def test_expert_catalog_endpoint(self, temp_project_dir: Path):
        client = _make_client()

        experts_resp = client.get("/api/experts")
        assert experts_resp.status_code == 200
        expert_ids = {item["id"] for item in experts_resp.json()["experts"]}
        assert "PM" in expert_ids
        assert "RCA" in expert_ids

    def test_catalogs_endpoint(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()

        platform_ids = {item["id"] for item in payload["platforms"]}
        assert {"web", "mobile", "wechat", "desktop"}.issubset(platform_ids)

        frontend_ids = {item["id"] for item in payload["frontends"]}
        assert {"react", "vue", "angular", "svelte", "none"}.issubset(frontend_ids)

        backend_ids = {item["id"] for item in payload["backends"]}
        assert {"node", "python", "rust", "csharp", "dart", "none"}.issubset(backend_ids)

        domain_ids = {item["id"] for item in payload["domains"]}
        assert {"", "fintech", "auth", "content", "saas"}.issubset(domain_ids)

        cicd_platform_ids = {item["id"] for item in payload["cicd_platforms"]}
        assert {"all", "github", "gitlab", "jenkins", "azure", "bitbucket"}.issubset(
            cicd_platform_ids
        )

        host_tool_ids = {item["id"] for item in payload["host_tools"]}
        assert {
            "antigravity",
            "claude-code",
            "droid-cli",
            "codebuddy-cli",
            "codebuddy",
            "codex-cli",
            "cursor-cli",
            "windsurf",
            "gemini-cli",
            "kimi-code",
            "kiro-cli",
            "opencode",
            "qoder-cli",
            "cursor",
            "kiro",
            "qoder",
            "trae",
            "trae-solo",
            "trae-solocn",
            "workbuddy",
        }.issubset(host_tool_ids)
        for host in payload["host_tools"]:
            if host["id"] not in PRIMARY_HOST_TOOL_IDS:
                continue
            assert host["standard_flow_first_prompt"]
            assert "super-dev" in host["standard_flow_first_prompt"].lower()
            assert host["competition_flow_first_prompt"]
            assert "seeai" in host["competition_flow_first_prompt"].lower()
            assert host["host_start_playbook"]
            assert host["post_onboard_self_check"]
            assert host["official_workflow_checks"]
            assert host["official_pass_criteria"]
            assert host["host_repair_playbook"]
        antigravity_host = next(
            item for item in payload["host_tools"] if item["id"] == "antigravity"
        )
        assert antigravity_host["category"] == "ide"
        assert "GEMINI.md" in antigravity_host["integration_files"]
        assert ".agent/workflows/super-dev.md" in antigravity_host["integration_files"]
        assert antigravity_host["slash_command_file"] == ".gemini/commands/super-dev.toml"
        assert antigravity_host["usage_mode"] == "native-slash"
        assert antigravity_host["host_protocol_mode"] == "recommended-gemini-workflow"
        assert antigravity_host["commands"]["trigger"].startswith("/super-dev")
        claude_host = next(item for item in payload["host_tools"] if item["id"] == "claude-code")
        assert claude_host["category"] == "cli"
        assert claude_host["install_mode"] == "hybrid"
        assert "CLAUDE.md" in claude_host["integration_files"]
        assert ".claude/CLAUDE.md" in claude_host["integration_files"]
        assert ".claude/skills/super-dev/SKILL.md" in claude_host["integration_files"]
        assert claude_host["slash_command_file"] == ".claude/commands/super-dev.md"
        assert claude_host["usage_mode"] == "native-slash-and-skill"
        assert claude_host["commands"]["trigger"].startswith("/super-dev")
        assert claude_host["maintenance_commands"]["setup"].startswith(
            "super-dev setup --host claude-code"
        )
        assert (
            claude_host["maintenance_commands"]["audit"]
            == "super-dev integrate audit --target claude-code"
        )
        assert (
            claude_host["maintenance_commands"]["smoke"]
            == "super-dev integrate smoke --target claude-code"
        )
        assert claude_host["competition_mode"]["enabled"] is True
        assert claude_host["competition_mode"]["timebox_minutes"] == 30
        assert claude_host["competition_mode"]["trigger"].startswith("/super-dev-seeai")
        assert "SEEAI_SMOKE_OK" in claude_host["competition_smoke_test_prompt"]
        assert any("半小时比赛链路" in item for item in claude_host["competition_smoke_test_steps"])
        assert any(
            "12 分钟内先跑出第一个可见界面" in item
            for item in claude_host["competition_smoke_test_steps"]
        )

        language_ids = {item["id"] for item in payload["languages"]}
        assert {"python", "typescript", "rust", "sql", "assembly"}.issubset(language_ids)

    def test_hosts_doctor_endpoint(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "claude-code",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "success"
        assert payload["selected_targets"] == ["claude-code"]
        assert "report" in payload
        assert "compatibility" in payload
        assert payload["decision_card"]["scenario"] in {
            "no-host-detected",
            "single-host-detected",
            "multi-host-detected",
        }
        assert payload["decision_card"]["selection_source"] == "explicit"
        assert payload["decision_card"]["workflow_mode"] == "start"
        assert payload["decision_card"]["workflow_mode_label"] == "开始新流程"
        assert payload["decision_card"]["action_title"]
        assert payload["decision_card"]["action_examples"]
        assert payload["decision_card"]["user_action_shortcuts"]
        assert payload["decision_card"]["recommended_reason"]
        assert payload["decision_card"]["first_action"]
        assert payload["decision_card"]["lines"]
        assert any("官方补充检查:" in item for item in payload["decision_card"]["lines"])
        assert payload["decision_card"]["selected_host_post_onboard_self_check"]
        assert payload["decision_card"]["selected_host_start_playbook"]
        assert payload["decision_card"]["selected_host_standard_flow_first_prompt"]
        assert payload["decision_card"]["selected_host_competition_flow_first_prompt"]
        assert payload["decision_card"]["selected_host_resume_guidance"]
        assert payload["decision_card"]["selected_host_injection_closure"]
        assert payload["decision_card"]["selected_host_ready_for_standard_flow"] is False
        assert payload["decision_card"]["selected_host_ready_for_competition_flow"] is False
        assert payload["decision_card"]["selected_host_standard_flow_label"]
        assert payload["decision_card"]["selected_host_competition_flow_label"]
        assert payload["decision_card"]["selected_host_official_workflow_checks"]
        assert payload["decision_card"]["selected_host_repair_playbook"]
        assert any(
            "super-dev-seeai" in item
            for item in payload["decision_card"]["selected_host_post_onboard_self_check"]
        )
        assert isinstance(payload["primary_repair_action"]["secondary_actions"], list)
        assert payload["decision_card"]["selected_host"] == "claude-code"
        assert (
            payload["decision_card"]["selected_path_override"]["env_key"]
            == "SUPER_DEV_HOST_PATH_CLAUDE_CODE"
        )
        assert payload["adaptation_contracts"]["claude-code"]["level"] == "elite"
        assert payload["selected_host_adaptation"]["level"] == "elite"
        assert payload["usage_profiles"]["claude-code"]["usage_mode"] == "native-slash-and-skill"
        assert payload["usage_profiles"]["claude-code"]["certification_level"] == "certified"
        assert payload["usage_profiles"]["claude-code"]["host_id"] == "claude-code"
        assert payload["usage_profiles"]["claude-code"]["capability_labels"]["slash"] == "native"
        assert payload["usage_profiles"]["claude-code"]["official_docs_url"].startswith("https://")
        assert payload["usage_profiles"]["claude-code"]["official_docs_references"]
        assert (
            payload["usage_profiles"]["claude-code"]["path_override"]["env_key"]
            == "SUPER_DEV_HOST_PATH_CLAUDE_CODE"
        )
        assert payload["usage_profiles"]["claude-code"]["trigger_command"].startswith("/super-dev")
        assert payload["usage_profiles"]["claude-code"]["final_trigger"] == "/super-dev 你的需求"
        assert "SMOKE_OK" in payload["usage_profiles"]["claude-code"]["smoke_test_prompt"]
        host = payload["report"]["hosts"]["claude-code"]
        assert host["ready"] is False
        assert {"integrate", "skill"}.issubset(set(host["missing"]))
        assert "slash" not in host["missing"]
        assert "plugin_enhancement" in host["optional_missing"]
        assert host["checks"]["contract"]["ok"] is True
        assert host["checks"]["contract"]["surfaces"]
        assert host["checks"]["contract"]["invalid_surfaces"] == {}
        assert host["checks"]["slash"]["scope"] == "not-required"
        assert host["checks"]["slash"]["ok"] is True
        assert host["usage_profile"]["usage_mode"] == "native-slash-and-skill"
        assert host["usage_profile"]["certification_label"] == "Certified"
        assert host["usage_profile"]["requires_restart_after_onboard"] is False

    def test_hosts_doctor_default_targets_follow_primary_product_scope(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir)},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["selected_targets"] == list(PRIMARY_HOST_TOOL_IDS)
        assert "openclaw" not in payload["selected_targets"]

    def test_public_host_targets_prefers_primary_product_scope(self, temp_project_dir: Path):
        integration_manager = IntegrationManager(temp_project_dir)

        targets = web_api._public_host_targets(integration_manager=integration_manager)

        assert targets == list(PRIMARY_HOST_TOOL_IDS)

    def test_hosts_validate_default_targets_follow_primary_product_scope(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir)},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["selected_targets"] == list(PRIMARY_HOST_TOOL_IDS)
        assert "openclaw" not in payload["selected_targets"]

    def test_hosts_runtime_validation_default_targets_follow_primary_product_scope(
        self, temp_project_dir: Path
    ):
        client = _make_client()

        resp = client.get(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir)},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["selected_targets"] == list(PRIMARY_HOST_TOOL_IDS)
        assert "openclaw" not in payload["selected_targets"]

    def test_hosts_doctor_codex_exposes_restart_and_context_preconditions(
        self, temp_project_dir: Path
    ):
        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "codex-cli",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        usage = payload["usage_profiles"]["codex-cli"]
        assert payload["adaptation_contracts"]["codex-cli"]["supports_slash_entry"] is False
        assert payload["selected_host_adaptation"]["supports_slash_entry"] is False
        assert usage["host_id"] == "codex-cli"
        assert usage["capability_labels"]["skills"] == "official"
        assert usage["official_docs_url"].startswith("https://")
        assert usage["official_docs_references"]
        assert usage["precondition_status"] == "session-restart-required"
        assert any(
            item["status"] == "session-restart-required" for item in usage["precondition_items"]
        )
        assert any(
            item["status"] == "project-context-required" for item in usage["precondition_items"]
        )
        host = payload["report"]["hosts"]["codex-cli"]
        assert host["preconditions"]["status"] == "session-restart-required"
        assert any("关闭旧宿主会话" in item for item in host["suggestions"])

    def test_detect_host_targets_uses_windows_env_candidates(
        self, temp_project_dir: Path, monkeypatch
    ):
        localapp = temp_project_dir / "LocalAppData"
        target = localapp / "Programs" / "Trae" / "Trae.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        monkeypatch.setenv("LOCALAPPDATA", str(localapp))

        detected, details = web_api._detect_host_targets(["trae"])
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

        detected, details = web_api._detect_host_targets(["codex-cli"])
        assert detected == ["codex-cli"]
        assert any(item.startswith("env:") for item in details["codex-cli"])

    def test_hosts_doctor_exposes_human_detection_details(
        self, temp_project_dir: Path, monkeypatch
    ):
        custom_dir = temp_project_dir / "custom-hosts"
        target = custom_dir / "CodexCustom.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        monkeypatch.setenv("SUPER_DEV_HOST_PATH_CODEX_CLI", str(target))
        client = _make_client()

        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "auto": "true"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert any(
            "自定义路径覆盖" in item for item in payload["detection_details_pretty"]["codex-cli"]
        )
        assert payload["session_resume_cards"]["codex-cli"]["enabled"] is False
        assert payload["decision_card"]["scenario"] in {
            "single-host-detected",
            "multi-host-detected",
        }
        assert payload["decision_card"]["workflow_mode"] == "start"
        assert payload["decision_card"]["workflow_mode_label"] == "开始新流程"
        assert payload["decision_card"]["action_title"]
        assert payload["decision_card"]["action_examples"]
        assert payload["decision_card"]["user_action_shortcuts"]
        assert payload["decision_card"]["recommended_reason"]
        assert payload["decision_card"]["first_action"]
        assert payload["decision_card"]["secondary_actions"]
        assert payload["decision_card"]["lines"]
        assert (
            payload["decision_card"]["candidates"][0]["id"]
            == payload["decision_card"]["selected_host"]
        )
        assert payload["decision_card"]["candidates"][0]["recommended"] is True
        expected_env_key = f"SUPER_DEV_HOST_PATH_{payload['decision_card']['selected_host'].upper().replace('-', '_')}"
        assert (
            payload["decision_card"]["candidates"][0]["path_override"]["env_key"]
            == expected_env_key
        )
        assert payload["decision_card"]["candidates"][0]["adaptation_contract"]["score"] >= 0
        assert payload["decision_card"]["candidates"][0]["experience_profile"]["tier"]
        assert payload["decision_card"]["candidates"][0]["primary_entry"]
        assert payload["decision_card"]["candidates"][0]["usage_mode"]
        assert payload["selected_host_experience"]["tier"]
        assert payload["selected_host_experience"]["start_playbook"]
        assert payload["selected_host_post_onboard_self_check"]
        assert payload["selected_host_start_playbook"]
        assert payload["selected_host_standard_flow_first_prompt"]
        assert payload["selected_host_competition_flow_first_prompt"]
        assert payload["selected_host_resume_guidance"]
        assert payload["selected_host_official_workflow_checks"]
        assert payload["selected_host_repair_playbook"]
        assert any("起手建议:" in item for item in payload["decision_card"]["lines"])
        assert payload["experience_profiles"][payload["decision_card"]["selected_host"]]["tier"]

    def test_hosts_doctor_prefers_install_action_when_no_host_detected(
        self, temp_project_dir: Path, monkeypatch
    ):
        client = _make_client()
        monkeypatch.setattr(web_api, "_detect_host_targets", lambda available_targets: ([], {}))

        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "auto": "true"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["decision_card"]["scenario"] == "no-host-detected"
        assert payload["decision_card"]["workflow_mode"] == "start"
        assert payload["decision_card"]["workflow_mode_label"] == "开始新流程"
        assert payload["decision_card"]["action_title"] == "先完成宿主安装与接入"
        assert payload["decision_card"]["action_examples"]
        assert payload["decision_card"]["user_action_shortcuts"]
        assert payload["decision_card"]["lines"]
        assert payload["primary_repair_action"]["host"] == "当前机器"
        assert (
            payload["primary_repair_action"]["command"] == payload["decision_card"]["first_action"]
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
        assert payload["decision_card"]["path_override_examples"][0]["env_key"]

    def test_hosts_validate_exposes_human_detection_details(
        self, temp_project_dir: Path, monkeypatch
    ):
        custom_dir = temp_project_dir / "custom-hosts"
        target = custom_dir / "CodexCustom.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        monkeypatch.setenv("SUPER_DEV_HOST_PATH_CODEX_CLI", str(target))
        client = _make_client()

        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "auto": "true"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert any(
            "自定义路径覆盖" in item for item in payload["detection_details_pretty"]["codex-cli"]
        )
        assert any(
            "自定义路径覆盖" in item
            for item in payload["report"]["detection_details_pretty"]["codex-cli"]
        )
        assert payload["session_resume_cards"]["codex-cli"]["enabled"] is False
        assert payload["decision_card"]["scenario"] in {
            "single-host-detected",
            "multi-host-detected",
        }
        assert payload["decision_card"]["workflow_mode"] == "start"
        assert payload["decision_card"]["workflow_mode_label"] == "开始新流程"
        assert payload["decision_card"]["action_title"]
        assert payload["decision_card"]["action_examples"]
        assert payload["decision_card"]["user_action_shortcuts"]
        assert payload["decision_card"]["recommended_reason"]
        assert payload["decision_card"]["first_action"]
        assert payload["decision_card"]["secondary_actions"]
        assert payload["decision_card"]["lines"]
        assert (
            payload["decision_card"]["candidates"][0]["id"]
            == payload["decision_card"]["selected_host"]
        )
        assert payload["decision_card"]["candidates"][0]["recommended"] is True
        expected_env_key = f"SUPER_DEV_HOST_PATH_{payload['decision_card']['selected_host'].upper().replace('-', '_')}"
        assert (
            payload["decision_card"]["candidates"][0]["path_override"]["env_key"]
            == expected_env_key
        )
        assert payload["decision_card"]["candidates"][0]["adaptation_contract"]["score"] >= 0
        assert payload["decision_card"]["candidates"][0]["primary_entry"]
        assert payload["decision_card"]["candidates"][0]["usage_mode"]

    def test_hosts_validate_trims_candidate_preview_for_multi_host_detection(
        self, temp_project_dir: Path, monkeypatch
    ):
        client = _make_client()
        monkeypatch.setattr(
            web_api,
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

        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "auto": "true"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        decision_card = payload["decision_card"]
        assert decision_card["scenario"] == "multi-host-detected"
        assert decision_card["workflow_mode"] == "start"
        assert decision_card["workflow_mode_label"] == "开始新流程"
        assert decision_card["action_title"]
        assert decision_card["action_examples"]
        assert decision_card["user_action_shortcuts"]
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
        assert decision_card["candidates"][0]["experience_profile"]["label"]
        assert decision_card["lines"]

    def test_hosts_doctor_trae_uses_compat_skill_and_skips_slash(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae").mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae" / "skills").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".trae").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".trae" / "project_rules.md").write_text("rules", encoding="utf-8")
        (temp_project_dir / ".trae" / "rules.md").write_text("rules", encoding="utf-8")
        (fake_home / ".trae" / "user_rules.md").write_text("rules", encoding="utf-8")
        (fake_home / ".trae" / "rules.md").write_text("rules", encoding="utf-8")
        monkeypatch.setenv("HOME", str(fake_home))
        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "trae",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        host = payload["report"]["hosts"]["trae"]
        assert host["ready"] is False
        assert "contract" in host["missing"]
        assert "skill" not in host["missing"]
        assert "slash" not in host["missing"]
        assert host["checks"]["slash"]["ok"] is True
        assert host["checks"]["slash"]["mode"] == "rules-only"
        assert host["checks"]["contract"]["ok"] is False
        assert host["checks"]["skill"]["ok"] is True
        assert host["checks"]["skill"]["mode"] == "compatibility-surface-unavailable"
        assert payload["usage_profiles"]["trae"]["usage_mode"] == "rules-and-skill"
        assert payload["usage_profiles"]["trae"]["certification_level"] == "compatible"
        assert host["usage_profile"]["trigger_command"] == "super-dev: <需求描述>"
        assert str(fake_home / ".trae" / "skills") in host["checks"]["skill"]["file"]
        assert (
            str((temp_project_dir / ".trae" / "project_rules.md").resolve())
            in host["checks"]["integrate"]["files"]
        )
        assert (
            str((temp_project_dir / ".trae" / "rules.md").resolve())
            not in host["checks"]["integrate"]["files"]
        )
        assert any(
            item == ".trae/rules.md" or item.endswith("/.trae/rules.md")
            for item in payload["usage_profiles"]["trae"]["observed_compatibility_surfaces"]
        )
        assert payload["usage_profiles"]["trae"]["usage_location"]
        assert payload["usage_profiles"]["trae"]["usage_notes"]

    def test_hosts_doctor_trae_skips_missing_compat_surface(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".trae").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".trae" / "project_rules.md").write_text("rules", encoding="utf-8")
        (temp_project_dir / ".trae" / "rules.md").write_text("rules", encoding="utf-8")
        (fake_home / ".trae").mkdir(parents=True, exist_ok=True)
        (fake_home / ".trae" / "user_rules.md").write_text("rules", encoding="utf-8")
        (fake_home / ".trae" / "rules.md").write_text("rules", encoding="utf-8")
        monkeypatch.setenv("HOME", str(fake_home))
        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "trae",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        host = payload["report"]["hosts"]["trae"]
        assert "contract" in host["missing"]
        assert "skill" not in host["missing"]
        assert host["checks"]["skill"]["surface_available"] is False
        assert host["checks"]["skill"]["mode"] == "compatibility-surface-unavailable"

    def test_codex_host_catalog_is_skill_only(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        codex_host = next(item for item in payload["host_tools"] if item["id"] == "codex-cli")
        assert codex_host["supports_slash"] is False
        assert codex_host["adaptation_contract"]["supports_slash"] is False
        assert codex_host["adaptation_contract"]["supports_slash_entry"] is False
        assert codex_host["adaptation_contract"]["dimensions"]["entry_experience"]["status"] == "ready"
        assert codex_host["slash_command_file"] == ""
        assert codex_host["certification_level"] == "certified"
        assert codex_host["certification_label"] == "Certified"
        assert codex_host["usage_mode"] == "agents-and-skill"
        assert codex_host["host_protocol_mode"] == "official-skill"
        assert (
            codex_host["host_protocol_summary"]
            == "官方 AGENTS.md + Skills + CLI $skill entry"
        )
        assert "$super-dev" in codex_host["primary_entry"]
        assert any(item["entry"] == "$super-dev" for item in codex_host["entry_variants"])
        assert any(item["entry"] == "super-dev: <需求描述>" for item in codex_host["entry_variants"])
        assert codex_host["usage_location"]
        assert codex_host["usage_notes"]
        assert codex_host["requires_restart_after_onboard"] is True
        assert any("重启 codex" in step for step in codex_host["post_onboard_steps"])
        assert codex_host["commands"]["slash"] == ""
        assert codex_host["commands"]["skill_slash"] == ""
        assert codex_host["commands"]["skill"] == "$super-dev"
        assert codex_host["supports_skill_slash_entry"] is False
        assert codex_host["skill_slash_entry_command"] == ""
        assert codex_host["flow_contract"]["consistent_flow_required"] is True
        assert codex_host["flow_contract"]["preferred_entry_order"] == ["cli", "fallback"]
        assert "同一条 Super Dev 流程" in codex_host["flow_contract"]["summary"]
        assert codex_host["flow_probe"]["enabled"] is True
        assert len(codex_host["flow_probe"]["steps"]) >= 3
        assert ".agents/skills/super-dev/SKILL.md" in codex_host["official_project_surfaces"]
        assert "~/.agents/skills/super-dev/SKILL.md" in codex_host["official_user_surfaces"]
        assert "~/.codex/AGENTS.md" in codex_host["optional_user_surfaces"]
        assert codex_host["default_install_scope"] == "project-first"
        assert codex_host["user_surface_opt_in_available"] is True
        assert codex_host["user_surface_opt_in_flag"] == "--with-user-surfaces"
        assert ".agents/plugins/marketplace.json" in codex_host["optional_project_surfaces"]
        assert (
            "plugins/super-dev-codex/.codex-plugin/plugin.json"
            in codex_host["optional_project_surfaces"]
        )
        assert "~/.codex/skills/super-dev/SKILL.md" in codex_host["observed_compatibility_surfaces"]
        assert (
            codex_host["commands"]["trigger"]
            == "CLI: $super-dev | 回退: super-dev: 你的需求"
        )
        assert (
            codex_host["final_trigger"]
            == "CLI: $super-dev | 回退: super-dev: 你的需求"
        )
        assert "SMOKE_OK" in codex_host["smoke_test_prompt"]

    def test_claude_host_catalog_uses_official_subagent_surfaces(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        claude_host = next(item for item in payload["host_tools"] if item["id"] == "claude-code")
        assert claude_host["supports_slash"] is True
        assert claude_host["host_protocol_mode"] == "official-skill"
        assert (
            claude_host["host_protocol_summary"]
            == "官方 CLAUDE.md + settings + project/user skills + subagents"
        )
        assert "CLAUDE.md" in claude_host["official_project_surfaces"]
        assert ".claude/CLAUDE.md" in claude_host["official_project_surfaces"]
        assert ".claude/skills/super-dev/SKILL.md" in claude_host["official_project_surfaces"]
        assert ".claude/agents/super-dev.md" in claude_host["official_project_surfaces"]
        assert "~/.claude/skills/super-dev/SKILL.md" in claude_host["official_user_surfaces"]
        assert "~/.claude/agents/super-dev.md" in claude_host["official_user_surfaces"]
        assert ".claude/settings.json" in claude_host["optional_project_surfaces"]
        assert "~/.claude/settings.json" in claude_host["optional_user_surfaces"]
        assert ".claude/commands/super-dev.md" in claude_host["optional_project_surfaces"]
        assert ".claude-plugin/marketplace.json" in claude_host["optional_project_surfaces"]
        assert (
            "plugins/super-dev-claude/.claude-plugin/plugin.json"
            in claude_host["optional_project_surfaces"]
        )
        assert "~/.claude/commands/super-dev.md" in claude_host["optional_user_surfaces"]
        assert claude_host["observed_compatibility_surfaces"] == []
        assert claude_host["commands"]["skill"] == ""

    def test_qoder_host_catalog_is_native_slash(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        qoder_host = next(item for item in payload["host_tools"] if item["id"] == "qoder")
        assert qoder_host["supports_slash"] is True
        assert qoder_host["host_protocol_mode"] == "official-skill"
        assert qoder_host["slash_command_file"] == ".qoder/commands/super-dev.md"
        assert qoder_host["usage_mode"] == "native-slash"
        assert qoder_host["commands"]["slash"] == "/super-dev 你的需求"
        assert qoder_host["commands"]["trigger"] == "/super-dev 你的需求"
        assert qoder_host["final_trigger"] == "/super-dev 你的需求"
        assert "AGENTS.md" in qoder_host["integration_files"]
        assert ".qoder/rules/super-dev.md" in qoder_host["integration_files"]
        assert ".qoder/agents/super-dev.md" in qoder_host["integration_files"]
        assert ".qoder/commands/super-dev.md" in qoder_host["official_project_surfaces"]
        assert ".qoder/rules/super-dev.md" in qoder_host["official_project_surfaces"]
        assert ".qoder/skills/super-dev/SKILL.md" in qoder_host["official_project_surfaces"]
        assert ".qoder/agents/super-dev.md" in qoder_host["optional_project_surfaces"]
        assert "~/.qoder/commands/super-dev.md" in qoder_host["official_user_surfaces"]
        assert "~/.qoder/skills/super-dev/SKILL.md" in qoder_host["official_user_surfaces"]
        assert "~/.qoder/AGENTS.md" in qoder_host["official_user_surfaces"]
        assert "~/.qoder/agents/super-dev.md" in qoder_host["optional_user_surfaces"]
        assert qoder_host["observed_compatibility_surfaces"] == []

    def test_codebuddy_and_droid_cli_catalogs_expose_competition_mode(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()

        codebuddy_host = next(item for item in payload["host_tools"] if item["id"] == "codebuddy")
        assert codebuddy_host["competition_mode"]["enabled"] is True
        assert codebuddy_host["competition_mode"]["trigger"] == "/super-dev-seeai 比赛需求"
        assert codebuddy_host["competition_mode"]["agent_team"][0] == "rapid_researcher"
        assert codebuddy_host["competition_mode"]["research_priorities"][0].startswith(
            "先判断题型和复杂度"
        )
        assert any(
            "交互" in item or "技术风险" in item
            for item in codebuddy_host["competition_mode"]["default_search_queries"]
        )
        assert codebuddy_host["competition_mode"]["first_response_template"][0] == "作品类型"
        assert (
            codebuddy_host["competition_mode"]["timebox_breakdown"][0] == "0-4 分钟：fast research"
        )
        assert "官网类" in codebuddy_host["competition_mode"]["archetype_detection_hints"][0]
        assert "Wow 点" in codebuddy_host["competition_mode"]["compact_doc_sections"]["research"]
        assert any("wow 点" in item for item in codebuddy_host["competition_mode"]["quality_floor"])
        assert (
            codebuddy_host["competition_mode"]["archetype_playbooks"]["landing_page"][
                "default_stack"
            ]
            == "React/Vite 或 Next.js + Tailwind + Framer Motion"
        )
        assert codebuddy_host["competition_mode"]["archetype_playbooks"]["landing_page"][
            "runtime_checkpoint"
        ].startswith("12 分钟内")
        assert (
            codebuddy_host["competition_mode"]["archetype_playbooks"]["mini_game"]["sprint_plan"][0]
            == "主循环可玩"
        )
        assert "arena_neon" in codebuddy_host["competition_mode"]["design_packs"]
        assert any(
            "初始化失败一次后" in item
            for item in codebuddy_host["competition_mode"]["failure_protocol"]
        )
        assert any(
            "12 分钟内必须跑出第一个可见" in item
            for item in codebuddy_host["competition_mode"]["execution_guardrails"]
        )
        assert any(
            "真实启动" in item for item in codebuddy_host["competition_mode"]["module_truth_rules"]
        )
        assert any(
            "demo slice" in item
            for item in codebuddy_host["competition_mode"]["complexity_reduction_rules"]
        )
        assert any(
            item["pattern"] == "系统/桌面/操作系统/IDE/复杂软件复刻"
            for item in codebuddy_host["competition_mode"]["complexity_patterns"]
        )
        assert "真实启动、真实交互" in codebuddy_host["competition_mode"]["module_activation_gate"]
        assert len(codebuddy_host["competition_mode"]["smoke_scenarios"]) >= 4
        assert (
            codebuddy_host["competition_mode"]["smoke_scenarios"][0]["id"] == "system_retro_shell"
        )
        assert any(
            "demo slice" in item for item in codebuddy_host["competition_mode"]["acceptance_gates"]
        )
        assert any(
            "3 秒第一印象" in item for item in codebuddy_host["competition_mode"]["judge_checklist"]
        )
        assert any("P0/P1/P2" in tip for tip in codebuddy_host["competition_mode"]["host_tips"])
        assert "SEEAI_SMOKE_OK" in codebuddy_host["competition_smoke_test_prompt"]
        assert any("P0/P1/P2" in item for item in codebuddy_host["competition_smoke_test_steps"])
        assert any("作品类型" in item for item in codebuddy_host["competition_smoke_test_steps"])
        assert any(
            "12 分钟内先跑出首个可见界面" in item
            for item in codebuddy_host["competition_smoke_test_steps"]
        )
        assert any(
            "真实启动并进入主演示路径" in item
            for item in codebuddy_host["competition_smoke_test_steps"]
        )
        assert len(codebuddy_host["competition_smoke_suite"]) >= 4
        assert codebuddy_host["competition_smoke_suite"][0]["trigger"].startswith(
            "/super-dev-seeai"
        )
        assert any("demo slice" in item for item in codebuddy_host["competition_acceptance_gates"])
        assert (
            codebuddy_host["competition_evidence_template"]["runtime_checkpoint"]["required"][0]
            == "12 分钟内首个可见界面"
        )

        droid_host = next(item for item in payload["host_tools"] if item["id"] == "droid-cli")
        assert ".factory/commands/super-dev-seeai.md" in droid_host["official_project_surfaces"]
        assert "~/.factory/commands/super-dev-seeai.md" in droid_host["optional_user_surfaces"]
        assert droid_host["adaptation_contract"]["level"] == "elite"
        assert droid_host["adaptation_contract"]["dimensions"]["competition"]["status"] == "ready"
        assert droid_host["competition_mode"]["enabled"] is True
        assert droid_host["competition_mode"]["trigger"] == "/super-dev-seeai 比赛需求"
        assert any("droid exec --session-id" in tip for tip in droid_host["competition_mode"]["host_tips"])
        assert "SEEAI_SMOKE_OK" in droid_host["competition_smoke_test_prompt"]
        assert any(
            "/super-dev-seeai" in item for item in droid_host["competition_smoke_test_steps"]
        )
        assert any("作品类型" in item for item in droid_host["competition_smoke_test_steps"])
        assert any(
            "12 分钟内先跑出首个可见界面" in item
            for item in droid_host["competition_smoke_test_steps"]
        )

        qoder_host = next(item for item in payload["host_tools"] if item["id"] == "qoder")
        assert (
            ".qoder/skills/super-dev-seeai/SKILL.md"
            in qoder_host["managed_competition_project_surfaces"]
        )
        assert qoder_host["standard_flow_first_prompt"]
        assert qoder_host["competition_flow_first_prompt"]
        assert qoder_host["post_onboard_self_check"]
        assert qoder_host["host_start_playbook"]
        assert qoder_host["host_repair_playbook"]
        assert any("SEEAI 项目补充面" in item for item in qoder_host["official_workflow_checks"])

        trae_solo_host = next(item for item in payload["host_tools"] if item["id"] == "trae-solo")
        assert (
            ".trae/skills/super-dev-seeai/SKILL.md"
            in trae_solo_host["managed_competition_project_surfaces"]
        )

        workbuddy_host = next(item for item in payload["host_tools"] if item["id"] == "workbuddy")
        assert workbuddy_host["install_mode"] == "hybrid"
        assert workbuddy_host["competition_mode"]["enabled"] is True
        assert workbuddy_host["competition_mode"]["trigger"] == "super-dev-seeai: 比赛需求"
        assert workbuddy_host["host_protocol_mode"] == "manual-task-workbench-mcp"
        assert "Skills" in workbuddy_host["host_protocol_summary"]
        assert (
            "~/.workbuddy/skills/super-dev-seeai/SKILL.md"
            in workbuddy_host["managed_competition_user_surfaces"]
        )
        assert any("MCP" in item for item in workbuddy_host["official_workflow_checks"])
        assert any(
            "super-dev-seeai:" in item for item in workbuddy_host["competition_smoke_test_steps"]
        )
        assert any("作品类型" in item for item in workbuddy_host["competition_smoke_test_steps"])
        assert any(
            "12 分钟内先跑出首个可见界面" in item
            for item in workbuddy_host["competition_smoke_test_steps"]
        )

    def test_cursor_host_catalog_exposes_agents_compatibility(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "cursor")
        assert host["host_protocol_mode"] == "official-context"
        assert host["host_protocol_summary"] == "官方 Agent Chat + AGENTS.md + rules (+ beta commands)"
        assert "AGENTS.md" in host["official_project_surfaces"]
        assert "CLAUDE.md" in host["optional_project_surfaces"]

    def test_gemini_host_catalog_exposes_global_command_surface(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "gemini-cli")
        assert host["host_protocol_mode"] == "official-context"
        assert host["host_protocol_summary"] == "官方 GEMINI.md + settings + custom commands"
        assert ".gemini/settings.json" in host["optional_project_surfaces"]
        assert "~/.gemini/commands/super-dev.toml" in host["optional_user_surfaces"]
        assert "~/.gemini/settings.json" in host["optional_user_surfaces"]

    def test_kimi_code_host_catalog_exposes_skill_and_resume_surfaces(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "kimi-code")
        assert host["supports_slash"] is False
        assert host["supports_skill_slash_entry"] is True
        assert host["skill_slash_entry_command"] == "/skill:super-dev"
        assert host["host_protocol_mode"] == "official-agents-entry"
        assert ".kimi/AGENTS.md" in host["integration_files"]
        assert "~/.kimi/skills/super-dev/SKILL.md" in host["optional_user_surfaces"]
        assert "/skill:super-dev <需求描述>" in host["primary_entry"]
        assert any(
            variant["entry"] == "/flow:super-dev <需求描述>" for variant in host["entry_variants"]
        )

    def test_copilot_cli_host_catalog_exposes_agents_as_official_surface(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "copilot-cli")
        assert host["host_protocol_mode"] == "official-context"
        assert host["host_protocol_summary"] == "官方 copilot-instructions + AGENTS.md + skills + agents"
        assert "AGENTS.md" in host["official_project_surfaces"]
        assert ".github/copilot-instructions.md" in host["official_project_surfaces"]
        assert ".github/agents/super-dev.md" in host["official_project_surfaces"]
        assert "~/.copilot/copilot-instructions.md" in host["official_user_surfaces"]
        assert "~/.copilot/agents/super-dev.md" in host["official_user_surfaces"]
        assert "AGENTS.md" not in host["observed_compatibility_surfaces"]

    def test_qwen_code_host_catalog_exposes_user_level_qwen_context_surface(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "qwen-code")
        assert host["host_protocol_mode"] == "official-context"
        assert host["host_protocol_summary"] == "官方 QWEN.md + settings + commands + skills + agents + /resume"
        assert "QWEN.md" in host["official_project_surfaces"]
        assert ".qwen/agents/super-dev.md" in host["official_project_surfaces"]
        assert "~/.qwen/QWEN.md" in host["official_user_surfaces"]
        assert "~/.qwen/commands/super-dev.md" in host["official_user_surfaces"]
        assert "~/.qwen/agents/super-dev.md" in host["official_user_surfaces"]

    def test_antigravity_host_catalog_uses_gemini_and_workflow_surfaces(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "antigravity")
        assert host["supports_slash"] is True
        assert host["usage_mode"] == "native-slash"
        assert host["host_protocol_mode"] == "recommended-gemini-workflow"
        assert (
            host["host_protocol_summary"]
            == "当前推荐接入模型: GEMINI.md + custom commands + optional workflows"
        )
        assert "GEMINI.md" in host["official_project_surfaces"]
        assert ".agent/workflows/super-dev.md" in host["optional_project_surfaces"]
        assert "~/.gemini/skills/super-dev/SKILL.md" in host["observed_compatibility_surfaces"]
        assert "~/.gemini/GEMINI.md" in host["optional_user_surfaces"]
        assert host["commands"]["trigger"] == "/super-dev 你的需求"
        assert host["final_trigger"] == "/super-dev 你的需求"
        assert host["standard_flow_first_prompt"] == "/super-dev 你的需求"
        assert host["competition_flow_first_prompt"] == "/super-dev-seeai 比赛需求"
        assert host["requires_restart_after_onboard"] is True

    def test_kiro_host_catalog_uses_global_steering_surface(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        kiro_host = next(item for item in payload["host_tools"] if item["id"] == "kiro")
        assert kiro_host["supports_slash"] is True
        assert kiro_host["usage_mode"] == "native-slash"
        assert kiro_host["host_protocol_mode"] == "official-steering"
        assert kiro_host["host_protocol_summary"] == "官方 AGENTS.md + steering + skills + agent continuity"
        assert kiro_host["slash_command_file"] == ".kiro/steering/super-dev.md"
        assert kiro_host["commands"]["trigger"] == "/super-dev 你的需求"
        assert kiro_host["final_trigger"] == "/super-dev 你的需求"
        assert "AGENTS.md" in kiro_host["official_project_surfaces"]
        assert ".kiro/steering/super-dev.md" in kiro_host["official_project_surfaces"]
        assert ".kiro/skills/super-dev/SKILL.md" in kiro_host["official_project_surfaces"]
        assert "~/.kiro/skills/super-dev/SKILL.md" in kiro_host["official_user_surfaces"]
        assert "~/.kiro/steering/super-dev.md" in kiro_host["optional_user_surfaces"]
        assert "~/.kiro/steering/AGENTS.md" in kiro_host["optional_user_surfaces"]

    @pytest.mark.parametrize(
        ("host_id", "slash_file"),
        [
            ("antigravity", ".gemini/commands/super-dev.toml"),
            ("codebuddy", ".codebuddy/commands/super-dev.md"),
            ("cursor", ".cursor/commands/super-dev.md"),
            ("kiro", ".kiro/steering/super-dev.md"),
            ("kiro-cli", ".kiro/steering/super-dev.md"),
            ("windsurf", ".windsurf/workflows/super-dev.md"),
            ("gemini-cli", ".gemini/commands/super-dev.toml"),
            ("opencode", ".opencode/commands/super-dev.md"),
            ("qoder", ".qoder/commands/super-dev.md"),
            ("trae-solo", ".trae/commands/super-dev.md"),
        ],
    )
    def test_verified_slash_hosts_catalog_keeps_native_entry(self, host_id: str, slash_file: str):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == host_id)
        assert host["supports_slash"] is True
        if host_id == "trae-solo":
            assert host["usage_mode"] == "workspace-rules-slash-skill"
        else:
            assert host["usage_mode"] == "native-slash"
        assert host["slash_command_file"] == slash_file
        if host_id == "gemini-cli":
            assert host["host_protocol_mode"] == "official-context"
            assert host["host_protocol_summary"] == "官方 GEMINI.md + settings + custom commands"
            assert "GEMINI.md" in host["official_project_surfaces"]
            assert "~/.gemini/GEMINI.md" in host["optional_user_surfaces"]
        assert host["commands"]["trigger"] == "/super-dev 你的需求"
        assert host["final_trigger"] == "/super-dev 你的需求"

    def test_kiro_cli_catalog_uses_slash_trigger_with_steering_and_skills(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "kiro-cli")
        assert host["supports_slash"] is True
        assert host["usage_mode"] == "native-slash"
        assert host["host_protocol_mode"] == "official-steering"
        assert host["host_protocol_summary"] == "官方 AGENTS.md + steering + skills + native resume"
        assert host["slash_command_file"] == ".kiro/steering/super-dev.md"
        assert host["final_trigger"] == "/super-dev 你的需求"
        assert "AGENTS.md" in host["official_project_surfaces"]
        assert ".kiro/steering/super-dev.md" in host["official_project_surfaces"]
        assert ".kiro/skills/super-dev/SKILL.md" in host["official_project_surfaces"]
        assert "~/.kiro/steering/super-dev.md" in host["optional_user_surfaces"]
        assert "~/.kiro/steering/AGENTS.md" in host["optional_user_surfaces"]
        assert "~/.kiro/skills/super-dev/SKILL.md" in host["official_user_surfaces"]

    def test_hosts_doctor_endpoint_ready_after_files_present(
        self, temp_project_dir: Path, monkeypatch
    ):
        client = _make_client()
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = IntegrationManager(temp_project_dir)
        manager.setup("claude-code", force=True)
        manager.setup_global_protocol("claude-code", force=True)
        manager.setup_slash_command("claude-code", force=True)
        SkillManager(temp_project_dir).install(
            "super-dev", "claude-code", name="super-dev", force=True
        )

        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "claude-code",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["report"]["hosts"]["claude-code"]["ready"] is True
        assert payload["report"]["hosts"]["claude-code"]["checks"]["contract"]["ok"] is True
        assert payload["compatibility"]["hosts"]["claude-code"]["score"] == 100.0

    def test_hosts_doctor_endpoint_flags_stale_contract(self, temp_project_dir: Path, monkeypatch):
        client = _make_client()
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = IntegrationManager(temp_project_dir)
        manager.setup("claude-code", force=True)
        manager.setup_global_protocol("claude-code", force=True)
        manager.setup_slash_command("claude-code", force=True)
        SkillManager(temp_project_dir).install(
            "super-dev", "claude-code", name="super-dev", force=True
        )
        stale_file = temp_project_dir / ".claude" / "commands" / "super-dev.md"
        stale_file.write_text("# stale\n/super-dev\n", encoding="utf-8")

        resp = client.get(
            "/api/hosts/doctor",
            params={
                "project_dir": str(temp_project_dir),
                "host": "claude-code",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        host = payload["report"]["hosts"]["claude-code"]
        assert host["ready"] is True
        assert "contract" not in host["missing"]
        assert "contract_optional_surfaces" in host["optional_missing"]
        assert host["checks"]["contract"]["ok"] is True
        invalid_surfaces = host["checks"]["contract"]["invalid_optional_surfaces"]
        assert invalid_surfaces
        assert any(
            ".claude/commands/super-dev.md" in str(item.get("path", ""))
            for item in invalid_surfaces.values()
        )

    def test_release_readiness_endpoint(self, temp_project_dir: Path):
        _prepare_release_ready_project(temp_project_dir)
        client = _make_client()

        resp = client.get(
            "/api/release/readiness",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["passed"] is True
        assert payload["score"] >= 90
        assert payload["persisted"] is False
        assert payload["report_file"] == ""
        assert payload["json_file"] == ""
        assert any(check["name"] == "Spec Quality" for check in payload["checks"])
        assert payload["frontend_governance_summary"]["state"] in {"ready", "unknown"}
        assert payload["compliance_governance_summary"]["state"] in {"ready", "unknown"}

    def test_release_proof_pack_endpoint(self, temp_project_dir: Path):
        _prepare_proof_pack_project(temp_project_dir)
        client = _make_client()

        resp = client.get(
            "/api/release/proof-pack",
            params={"project_dir": str(temp_project_dir)},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ready"
        assert payload["ready_count"] == payload["total_count"]
        assert payload["persisted"] is False
        assert payload["report_file"] == ""
        assert payload["json_file"] == ""
        assert payload["summary_file"] == ""
        assert payload["summary"]["blocking_count"] == 0
        assert any(artifact["name"] == "Spec Quality" for artifact in payload["artifacts"])
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
        assert payload["frontend_governance_summary"]["state"] in {"ready", "unknown"}
        assert payload["compliance_governance_summary"]["state"] in {"ready", "unknown"}

    def test_release_endpoints_persist_only_when_requested(self, temp_project_dir: Path):
        _prepare_proof_pack_project(temp_project_dir)
        client = _make_client()

        readiness_resp = client.get(
            "/api/release/readiness",
            params={"project_dir": str(temp_project_dir), "persist": True},
        )
        assert readiness_resp.status_code == 200
        readiness_payload = readiness_resp.json()
        assert readiness_payload["persisted"] is True
        assert Path(readiness_payload["report_file"]).exists()
        assert Path(readiness_payload["json_file"]).exists()

        proof_resp = client.get(
            "/api/release/proof-pack",
            params={"project_dir": str(temp_project_dir), "persist": True},
        )
        assert proof_resp.status_code == 200
        proof_payload = proof_resp.json()
        assert proof_payload["persisted"] is True
        assert Path(proof_payload["report_file"]).exists()
        assert Path(proof_payload["json_file"]).exists()
        assert Path(proof_payload["summary_file"]).exists()

    def test_hosts_validate_endpoint(self, temp_project_dir: Path):
        client = _make_client()

        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": "kiro-cli"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["selected_targets"] == ["kiro-cli"]
        assert payload["report"]["hosts"][0]["host"] == "kiro-cli"
        assert payload["report"]["hosts"][0]["manual_runtime_status_label"] == "待真人验收"
        assert payload["report"]["hosts"][0]["repo_probe"]["status"] == "pending"
        assert (
            payload["report"]["hosts"][0]["runtime_evidence"]["integration_status"]["status"]
            == "missing"
        )
        assert (
            payload["report"]["hosts"][0]["runtime_evidence"]["runtime_status"]["status"]
            == "pending"
        )
        assert payload["report"]["hosts"][0]["competition_evidence_ready"] is False
        assert "first_response" in payload["report"]["hosts"][0]["competition_evidence_missing"]
        assert payload["report"]["summary"]["total_hosts"] == 1
        assert payload["report"]["summary"]["repo_probe_pending_count"] == 1
        assert payload["report"]["summary"]["blocking_count"] >= 1
        assert payload["report"]["blockers"][0]["host"] == "kiro-cli"

    def test_hosts_validate_codex_uses_host_specific_runtime_checklist(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": "codex-cli"},
        )
        assert resp.status_code == 200
        host = resp.json()["report"]["hosts"][0]
        assert host["checks"]["plugin_enhancement"]["ok"] is True
        assert any("重开 codex" in item for item in host["runtime_checklist"])
        assert any(".agents/skills/super-dev" in item for item in host["runtime_checklist"])
        assert any(".agents/plugins/marketplace.json" in item for item in host["runtime_checklist"])
        assert any("当前终端就在目标项目目录" in item for item in host["runtime_checklist"])
        assert any(
            "12 分钟内先跑出第一个可见、可点击、可截图的界面" in item
            for item in host["runtime_checklist"]
        )
        assert any(".agents/skills/super-dev" in item for item in host["pass_criteria"])
        assert any("官方 Skills" in item for item in host["pass_criteria"])
        assert any("$super-dev" in item for item in host["pass_criteria"])
        assert any("回退栈" in item for item in host["pass_criteria"])
        assert host["flow_probe"]["enabled"] is True
        assert any("$super-dev" in item for item in host["flow_probe"]["steps"])

    def test_hosts_validate_opencode_uses_host_specific_runtime_checklist(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": "opencode"},
        )
        assert resp.status_code == 200
        host = resp.json()["report"]["hosts"][0]
        assert any(
            "当前 OpenCode 会话就是目标项目目录" in item for item in host["runtime_checklist"]
        )
        assert any("AGENTS.md、commands、skills" in item for item in host["runtime_checklist"])
        assert any("当前 OpenCode 会话真实读取" in item for item in host["pass_criteria"])

    def test_hosts_validate_codebuddy_seeai_runtime_validation(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            assert cli.run(["onboard", "--host", "codebuddy", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": "codebuddy"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["adaptation_contracts"]["codebuddy"]["score"] >= 75
        assert payload["selected_host_adaptation"]["score"] >= 75
        host = payload["report"]["hosts"][0]
        assert host["adaptation_contract"]["score"] >= 75
        assert host["usage_mode"] == "native-slash"
        assert host["primary_entry"]
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

    def test_catalog_droid_cli_flow_probe_exposes_seeai_session_validation(self):
        client = _make_client()
        resp = client.get("/api/catalogs")
        assert resp.status_code == 200
        payload = resp.json()
        host = next(item for item in payload["host_tools"] if item["id"] == "droid-cli")
        assert host["flow_probe"]["enabled"] is True
        assert any("/super-dev-seeai" in item for item in host["flow_probe"]["steps"])
        assert any("droid exec --session-id" in item for item in host["flow_probe"]["steps"])

    def test_hosts_validate_with_workflow_context_exposes_resume_probe_prompt(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": "opencode"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        decision_card = payload["decision_card"]
        host = payload["report"]["hosts"][0]
        resume_card = payload["session_resume_cards"]["opencode"]
        workflow_context = payload["workflow_context"]
        assert ".super-dev/SESSION_BRIEF.md" in host["resume_probe_prompt"]
        assert "/super-dev " in host["resume_probe_prompt"]
        assert any("当前项目会话里恢复" in item for item in host["resume_checklist"])
        assert host["framework_playbook"]["framework"] == "uni-app"
        assert any("provider" in item for item in host["framework_playbook"]["native_capabilities"])
        assert any("uni-app playbook" in item for item in host["runtime_checklist"])
        assert any("框架专项原生能力面" in item for item in host["runtime_checklist"])
        assert any("框架专项必验场景" in item for item in host["runtime_checklist"])
        assert any("跨平台框架专项能力" in item for item in host["pass_criteria"])
        assert any("uni-app 的专项 playbook" in item for item in host["resume_checklist"])
        assert decision_card["selected_host"] == "opencode"
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
        assert resume_card["workflow_mode"] == "revise"
        assert resume_card["workflow_mode_label"] == "返工/补充当前流程"
        assert resume_card["action_title"]
        assert resume_card["action_examples"]
        assert resume_card["user_action_shortcuts"]
        assert "super-dev create" not in resume_card["host_first_sentence"]
        assert "super-dev fix" not in resume_card["host_first_sentence"]
        assert "super-dev workflow" not in resume_card["host_first_sentence"]
        assert all("super-dev create" not in item for item in resume_card["action_examples"])
        assert all("super-dev fix" not in item for item in resume_card["action_examples"])
        assert all("super-dev workflow" not in item for item in resume_card["action_examples"])
        baseline_card = next(
            item for item in resume_card["scenario_cards"] if item["id"] == "existing_project_baseline"
        )
        assert baseline_card["title"] == "当前项目不是从零开始，先做 baseline"
        assert "1-N+1" in baseline_card["when"]
        assert "建立 baseline" in baseline_card["cli_command"]
        assert (
            ".super-dev/SESSION_BRIEF.md"
            in resume_card["session_brief_path"]
        )
        assert resume_card["recommended_workflow_command"]
        assert workflow_context == payload["decision_card"]["workflow_context"]
        assert workflow_context["baseline_required"] is False
        assert workflow_context["baseline_audit_status"] == "not_required"
        assert workflow_context["baseline_confirmation_status"] == "not_required"
        assert workflow_context["blocking_gate"] == "waiting_docs_confirmation"
        assert workflow_context["recommended_host_action"] == "/super-dev 继续当前流程"
        assert workflow_context["recommended_host_sentence"] == "super-dev: 继续当前流程"
        assert workflow_context["can_resume"] is True
        assert workflow_context["can_progress"] is False

    def test_hosts_doctor_with_workflow_context_exposes_resume_card(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "host": "codex-cli"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        decision_card = payload["decision_card"]
        card = payload["session_resume_cards"]["codex-cli"]
        assert card["enabled"] is True
        assert card["workflow_mode"] == "revise"
        assert card["workflow_mode_label"] == "返工/补充当前流程"
        assert card["action_title"]
        assert card["action_examples"]
        assert card["user_action_shortcuts"]
        assert card["preferred_entry"] == "cli"
        assert card["preferred_entry_label"] == "CLI"
        assert card["host_first_sentence"].startswith("$super-dev ")
        assert decision_card["selected_host"] == "codex-cli"
        assert decision_card["workflow_mode"] == "continue"
        assert decision_card["session_resume_card"]["enabled"] is True
        assert decision_card["session_resume_card"]["host_first_sentence"] == card[
            "host_first_sentence"
        ]
        assert decision_card["action_title"] == card["action_title"]
        assert decision_card["action_examples"] == card["action_examples"]
        assert decision_card["first_action"].endswith(card["host_first_sentence"])
        assert any(
            line == f"继续当前流程第一句: {card['host_first_sentence']}"
            for line in decision_card["lines"]
        )
        assert card["entry_prompts"]["cli"].startswith("$super-dev ")
        assert card["entry_prompts"]["fallback"].startswith("super-dev:")
        assert card["workflow_event_log_path"].endswith(".super-dev/workflow-events.jsonl")
        assert card["hook_history_path"].endswith(".super-dev/hook-history.jsonl")
        assert card["operational_harnesses"]
        assert card["operational_focus"]["status"] == "needs_attention"
        assert card["operational_focus"]["kind"] == "framework"
        scenario_ids = [item["id"] for item in card["scenario_cards"]]
        assert scenario_ids[:2] == ["resume_workday", "know_next"]
        assert "current_gate_or_stage" in scenario_ids
        assert any(
            item["cli_command"] == "回到宿主里说“继续当前流程，不要重新开题”"
            for item in card["scenario_cards"]
        )
        assert {item["kind"] for item in card["operational_harnesses"]} == {
            "workflow",
            "framework",
            "hooks",
        }
        assert card["recent_snapshots"]
        assert card["recent_events"]
        assert isinstance(card["recent_hook_events"], list)
        assert card["recent_timeline"]
        assert card["recent_snapshots"][0]["current_step_label"] == "等待三文档确认"
        assert any(
            "真实场景: 第二天回来继续开发 -> 回到宿主里说“继续当前流程”" == line
            for line in card["lines"]
        )
        assert any("最近一次:" in line for line in card["lines"])
        assert any("最近事件:" in line for line in card["lines"])
        if card["recent_hook_events"]:
            assert any("最近 Hook:" in line for line in card["lines"])
        assert any("关键时间线:" in line for line in card["lines"])
        assert any("Workflow Continuity:" in line for line in card["lines"])
        assert any("当前治理焦点:" in line for line in card["lines"])
        assert any("建议先做:" in line for line in card["lines"])
        assert ".super-dev/SESSION_BRIEF.md" in card["session_brief_path"]
        assert card["recommended_workflow_command"]
        assert card["framework_playbook"]["framework"] == "uni-app"
        assert any("provider" in item for item in card["framework_playbook"]["native_capabilities"])
        assert any("框架专项: uni-app" in line for line in card["lines"])
        assert payload["decision_card"]["selection_source"] == "explicit"
        assert decision_card["workflow_context"] == card["workflow_context"]
        assert card["workflow_context"]["baseline_required"] is False
        assert card["workflow_context"]["baseline_audit_status"] == "not_required"
        assert card["workflow_context"]["blocking_gate"] == "waiting_docs_confirmation"
        assert card["workflow_context"]["recommended_host_action"] == "$super-dev 继续当前流程"
        assert card["workflow_context"]["can_progress"] is False

    def test_hosts_doctor_with_kimi_context_exposes_skill_and_flow_resume_entries(
        self, temp_project_dir: Path
    ):
        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", "kimi-code", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "host": "kimi-code"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        card = payload["session_resume_cards"]["kimi-code"]
        assert card["enabled"] is True
        assert card["preferred_entry"] == "skill"
        assert card["preferred_entry_label"] == "Skill"
        assert card["entry_labels"]["skill"] == "Skill"
        assert card["entry_prompts"]["skill"].startswith("/skill:super-dev ")
        assert card["entry_prompts"]["flow"].startswith("/flow:super-dev ")
        assert card["entry_prompts"]["fallback"].startswith("super-dev:")
        assert card["workflow_context"]["recommended_host_action"].startswith("/skill:super-dev ")
        assert card["workflow_context"]["recommended_host_sentence"].startswith("super-dev:")

    def test_hosts_doctor_with_droid_context_exposes_headless_resume_entry(
        self, temp_project_dir: Path
    ):
        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", "droid-cli", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "host": "droid-cli"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        card = payload["session_resume_cards"]["droid-cli"]
        assert card["enabled"] is True
        assert card["preferred_entry"] == "slash"
        assert card["preferred_entry_label"] == "Slash"
        assert card["entry_labels"]["headless"] == "Headless"
        assert card["entry_prompts"]["slash"].startswith("/super-dev ")
        assert "droid exec --session-id" in card["entry_prompts"]["headless"]

    @pytest.mark.parametrize(
        ("host_id", "expected_resume_line", "expected_start_line"),
        [
            (
                "kimi-code",
                "原生恢复: kimi --continue / kimi --session <id>",
                "起手建议: 中文项目优先用 /skill:super-dev",
            ),
            (
                "droid-cli",
                "原生恢复: droid exec --session-id <id> / /super-dev 继续当前流程",
                "起手建议: 优先留在当前 Factory session",
            ),
        ],
    )
    def test_hosts_validate_flagship_hosts_expose_native_resume_guidance(
        self,
        temp_project_dir: Path,
        host_id: str,
        expected_resume_line: str,
        expected_start_line: str,
    ):
        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", host_id, "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": host_id},
        )
        assert resp.status_code == 200
        host = resp.json()["report"]["hosts"][0]
        assert any(expected_resume_line in item for item in host["resume_checklist"])
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

    def test_hosts_doctor_with_baseline_confirmation_context_exposes_baseline_resume_language(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
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
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/doctor",
            params={"project_dir": str(temp_project_dir), "host": "codex-cli"},
        )
        assert resp.status_code == 200
        card = resp.json()["session_resume_cards"]["codex-cli"]
        baseline_card = next(
            item for item in card["scenario_cards"] if item["id"] == "baseline_confirmation"
        )
        assert baseline_card["title"] == "已有项目先确认 baseline 再继续"
        assert "差量计划" in baseline_card["when"]
        assert "先确认 baseline" in baseline_card["cli_command"]
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

    @pytest.mark.parametrize(
        ("host_id", "expected_runtime_hint", "expected_resume_hint"),
        [
            ("claude-code", "当前 Claude Code 会话就在目标项目目录", "不能绕过当前确认门或返工门"),
            ("cursor-cli", "当前 Cursor CLI 终端就在目标项目目录", "当前终端目录仍是目标项目"),
            ("gemini-cli", "当前 Gemini CLI 会话就在目标项目目录", "再次读取了 `GEMINI.md`"),
            (
                "codebuddy",
                "当前 CodeBuddy Agent Chat 绑定的是目标项目",
                "继续当前确认门而不是重新开题",
            ),
            (
                "windsurf",
                "当前 Windsurf Agent Chat / Workflow 入口绑定的是目标项目工作区",
                "rules、workflow 与 skills",
            ),
            (
                "vscode-copilot",
                "当前 VS Code Copilot Chat 绑定的是目标项目工作区",
                "重新读取 `.github/copilot-instructions.md`",
            ),
            ("qoder", "当前 Qoder IDE Agent Chat 绑定的是目标项目", "继续当前确认门"),
            ("roo-code", "当前 Roo Code 聊天位于目标项目工作区", "重新加载 `.roo/` 规则与命令"),
            (
                "kilo-code",
                "当前 Kilo Code 聊天面板绑定的是目标工作区",
                "重新读取 `.kilocode/rules/`",
            ),
        ],
    )
    def test_hosts_validate_core_hosts_expose_host_specific_recovery_checks(
        self,
        temp_project_dir: Path,
        monkeypatch,
        host_id: str,
        expected_runtime_hint: str,
        expected_resume_hint: str,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            _prepare_workflow_context(temp_project_dir)
            assert cli.run(["onboard", "--host", host_id, "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        resp = client.get(
            "/api/hosts/validate",
            params={"project_dir": str(temp_project_dir), "host": host_id},
        )
        assert resp.status_code == 200
        host = resp.json()["report"]["hosts"][0]
        assert any(expected_runtime_hint in item for item in host["runtime_checklist"])
        assert ".super-dev/SESSION_BRIEF.md" in host["resume_probe_prompt"]
        assert any(expected_resume_hint in item for item in host["resume_checklist"])

    def test_hosts_runtime_validation_roundtrip(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        (fake_home / ".codex").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        cli = SuperDevCLI()
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            assert cli.run(["onboard", "--host", "codex-cli", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()

        update = client.post(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir)},
            json={
                "host": "codex-cli",
                "status": "passed",
                "comment": "首轮先进入 research，三文档已真实落盘",
                "actor": "user",
            },
        )
        assert update.status_code == 200
        update_payload = update.json()
        assert update_payload["manual_runtime_status"] == "passed"
        assert update_payload["manual_runtime_status_label"] == "已真人通过"
        assert update_payload["repo_probe"]["status"] == "pending"
        assert update_payload["runtime_evidence"]["runtime_status"]["status"] == "passed"
        assert update_payload["competition_evidence_ready"] is False
        assert "first_response" in update_payload["competition_evidence_missing"]
        assert update_payload["updated_at"]
        state_file = Path(update_payload["file_path"])
        assert state_file.exists()
        assert state_file.name == "host-runtime-validation.json"
        stored_state = json.loads(state_file.read_text(encoding="utf-8"))
        stored_host = stored_state["hosts"]["codex-cli"]
        assert stored_host["status"] == "passed"
        assert stored_host["comment"] == "首轮先进入 research，三文档已真实落盘"
        assert stored_host["actor"] == "user"
        assert stored_host["competition_evidence_ready"] is False
        assert "first_response" in stored_host["competition_evidence_missing"]

        resp = client.get(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir), "host": "codex-cli"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        host = payload["report"]["hosts"][0]
        assert host["integration_status"] == "project_and_global_installed"
        assert host["runtime_status"] == "passed"
        assert host["runtime_status_label"] == "已真人通过"
        assert host["manual_runtime_status"] == "passed"
        assert host["manual_runtime_status_label"] == "已真人通过"
        assert host["manual_runtime_comment"] == "首轮先进入 research，三文档已真实落盘"
        assert host["manual_runtime_updated_at"]
        assert host["repo_probe"]["status"] == "pending"
        assert host["competition_evidence_ready"] is False
        assert host["ready_for_delivery"] is False
        assert host["blocking_reason"] == "SEEAI 比赛验收证据不完整"
        assert "first_response" in host["competition_evidence_missing"]
        assert (
            host["runtime_evidence"]["integration_status"]["status"]
            == "project_and_global_installed"
        )
        assert host["runtime_evidence"]["runtime_status"]["status"] == "passed"
        assert host["runtime_evidence"]["competition_evidence_ready"] is False
        assert host["runtime_evidence"]["host_display_name"] == "Codex"

        evidence_update = client.post(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir)},
            json={
                "host": "codex-cli",
                "status": "passed",
                "comment": "补齐比赛验收证据",
                "actor": "user",
                "competition_evidence": {
                    "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
                    "runtime_checkpoint": {
                        "summary": "12 分钟内首个可见界面 + 主路径首个点击动作 + 真实启动模块"
                    },
                    "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
                    "demo_path": {"summary": "30-60 秒主演示路径 + 结果页/结束态 + wow 点截图"},
                },
            },
        )
        assert evidence_update.status_code == 200
        evidence_payload = evidence_update.json()
        assert evidence_payload["competition_evidence_ready"] is True
        stored_state = json.loads(state_file.read_text(encoding="utf-8"))
        stored_host = stored_state["hosts"]["codex-cli"]
        assert stored_host["comment"] == "补齐比赛验收证据"
        assert stored_host["competition_evidence_ready"] is True
        assert stored_host["competition_evidence_missing"] == []
        assert stored_host["competition_evidence"]["demo_path"]["summary"].startswith("30-60 秒主演示路径")

        ready_resp = client.get(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir), "host": "codex-cli"},
        )
        ready_host = ready_resp.json()["report"]["hosts"][0]
        assert ready_host["competition_evidence_ready"] is True
        assert ready_host["competition_evidence_missing"] == []
        assert ready_host["ready_for_delivery"] is True

    def test_hosts_runtime_validation_marks_repo_probe_failure_as_delivery_blocker(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

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
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)
        try:
            assert cli.run(["onboard", "--host", "opencode", "--force", "--yes"]) == 0
        finally:
            os.chdir(original_cwd)

        client = _make_client()
        update = client.post(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir)},
            json={
                "host": "opencode",
                "status": "passed",
                "comment": "manual accepted",
                "actor": "user",
                "competition_evidence": {
                    "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
                    "runtime_checkpoint": {
                        "summary": "12 分钟内首个可见界面 + 主路径首个点击动作 + 真实启动模块"
                    },
                    "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
                    "demo_path": {"summary": "30-60 秒主演示路径 + 结果页/结束态 + wow 点截图"},
                },
            },
        )
        assert update.status_code == 200
        assert update.json()["repo_probe"]["status"] == "failed"

        resp = client.get(
            "/api/hosts/runtime-validation",
            params={"project_dir": str(temp_project_dir), "host": "opencode"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        host = payload["report"]["hosts"][0]
        assert host["repo_probe"]["status"] == "failed"
        assert host["ready_for_delivery"] is False
        assert "所需仓库级连续性证据不完整" in host["blocking_reason"]
        assert "确认三文档" in host["recommended_action"] or "review docs" in host["recommended_action"]
        assert payload["report"]["summary"]["repo_probe_failed_count"] == 1
        assert payload["report"]["summary"]["fully_ready_count"] == 0
        assert payload["report"]["blockers"][0]["type"] == "repo_probe"
