import json
from pathlib import Path

from super_dev import __version__
from super_dev.evidence_identity import build_evidence_identity
from super_dev.hooks.manager import HookManager
from super_dev.release_readiness import (
    ReleaseReadinessCheck,
    ReleaseReadinessEvaluator,
    ReleaseReadinessReport,
)
from super_dev.review_state import (
    save_baseline_confirmation,
    save_host_runtime_validation,
    save_workflow_state,
    workflow_event_log_file,
)
from super_dev.reviewers.architecture_drift import (
    _report_dependencies as _architecture_drift_dependencies,
)
from super_dev.reviewers.spec_compliance import (
    _report_dependencies as _spec_compliance_dependencies,
)
from super_dev.reviewers.uiux_compliance import (
    _report_dependencies as _uiux_compliance_dependencies,
)
from super_dev.specs.generator import SpecGenerator
from super_dev.workflow_guard import (
    record_stage_progress,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)


def _prepare_release_ready_project(project_dir: Path) -> None:
    (project_dir / "super_dev").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)
    (project_dir / ".super-dev" / "changes" / "release-hardening-finalization").mkdir(
        parents=True,
        exist_ok=True,
    )
    (project_dir / "pyproject.toml").write_text(f'[project]\nversion = "{__version__}"\n[project.scripts]\nsuper-dev = "super_dev.cli:main"\n', encoding="utf-8")
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
                "/.windsurf/",
                "/GEMINI.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "super_dev" / "__init__.py").write_text(f'__version__ = "{__version__}"\n', encoding="utf-8")
    (project_dir / "README.md").write_text(
        f"当前版本：`{__version__}`\nuv tool install super-dev\n/super-dev\nsuper-dev:\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "README_EN.md").write_text(
        f"Current version: `{__version__}`\nuv tool install super-dev\n/super-dev\nsuper-dev:\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "INSTALL_OPTIONS.md").write_text(
        "uv tool install super-dev\nsuper-dev update\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "HOST_USAGE_GUIDE.md").write_text(
        "Smoke\n/super-dev\nsuper-dev:\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "HOST_CAPABILITY_AUDIT.md").write_text(
        "官方依据\nintegrate smoke / validate\n",
        encoding="utf-8",
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
        "super-dev review docs\n继续当前流程\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "WORKFLOW_GUIDE_EN.md").write_text(
        "super-dev review docs\ncontinue current workflow\n",
        encoding="utf-8",
    )
    (project_dir / "docs" / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n",
        encoding="utf-8",
    )
    (project_dir / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    for name in ("change.yaml", "proposal.md", "tasks.md"):
        (project_dir / ".super-dev" / "changes" / "release-hardening-finalization" / name).write_text(
            "ok\n",
            encoding="utf-8",
        )
    (project_dir / "output" / f"{project_dir.name}-redteam.json").write_text(
        (
            "{\n"
            f'  "project_name": "{project_dir.name}",\n'
            '  "pass_threshold": 70,\n'
            '  "critical_count": 0,\n'
            '  "high_count": 0,\n'
            '  "total_score": 92,\n'
            '  "passed": true,\n'
            '  "blocking_reasons": [],\n'
            '  "security_issues": [],\n'
            '  "performance_issues": [],\n'
            '  "architecture_issues": []\n'
            "}\n"
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
            "- 构建检查已完成\n\n"
            "## 宿主补充自检（交付前必做）\n\n"
            "- 新增函数、方法、字段、模块都已接入真实调用链\n"
        ),
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-product-audit.json").write_text(
        '{\n  "status": "ready",\n  "score": 90\n}\n',
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-ui-contract.json").write_text(
        (
            "{\n"
            '  "style_direction": "Editorial workspace",\n'
            '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
            '  "icon_system": "lucide-react",\n'
            '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
            '  "ui_library_preference": {\n'
            '    "preferred": "shadcn/ui + Radix + Tailwind",\n'
            '    "strict": false,\n'
            '    "final_selected": "shadcn/ui + Radix + Tailwind"\n'
            "  },\n"
            '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
            '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero", "proof-strip"], "trust_modules": ["客户案例"], "required_states": ["loading", "empty"]}],\n'
            '  "design_context_protocol": {"preferred_import_order": ["tokens", "sections"], "github_import_targets": ["theme.ts", "src/components"], "single_source_rule": "single source prototype"},\n'
            '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度", "信任模块"], "persistence_rule": "persist tweak decisions into the same prototype"},\n'
            '  "verification_handoff": {"verification_order": ["preview", "ui-review"], "required_artifacts": ["output/frontend/index.html", "output/frontend/app.js"], "acceptance_checks": ["no emoji", "recipe visible"]}\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-ui-contract-alignment.json").write_text(
        json.dumps(
            {
                "theme_entry": {"passed": True},
                "screen_recipes": {"passed": True},
                "design_context_protocol": {"passed": True},
                "tweak_strategy": {"passed": True},
                "verification_handoff": {"passed": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-ui-review.json").write_text(
        json.dumps({"score": 92, "critical_count": 0}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    quality_gate_identity = build_evidence_identity(
        project_dir,
        artifact_name="quality-gate",
        dependencies=[
            project_dir / "output" / f"{project_dir.name}-ui-review.json",
            project_dir / "output" / f"{project_dir.name}-ui-contract-alignment.json",
            project_dir / "output" / f"{project_dir.name}-uiux.md",
        ],
    )
    (project_dir / "output" / f"{project_dir.name}-quality-gate.json").write_text(
        json.dumps(
            {
                "passed": True,
                "total_score": 90,
                "summary": {"executive_summary": "quality gate passed"},
                "evidence_identity": quality_gate_identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    frontend_identity = build_evidence_identity(
        project_dir,
        artifact_name="frontend-runtime",
        dependencies=[
            project_dir / "output" / f"{project_dir.name}-ui-contract.json",
            project_dir / "output" / f"{project_dir.name}-ui-contract-alignment.json",
        ],
    )
    (project_dir / "output" / "frontend").mkdir(parents=True, exist_ok=True)
    (project_dir / "output" / "frontend" / "design-tokens.css").write_text(
        ":root { --color-primary: #0f172a; }\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-frontend-runtime.json").write_text(
        (
            "{\n"
            '  "passed": true,\n'
            '  "checks": {\n'
            '    "output_frontend_index": true,\n'
            '    "output_frontend_styles": true,\n'
            '    "output_frontend_design_tokens": true,\n'
            '    "output_frontend_script": true,\n'
            '    "preview_html": true,\n'
            '    "ui_contract_json": true,\n'
            '    "ui_contract_alignment": true,\n'
            '    "ui_theme_entry": true,\n'
            '    "ui_navigation_shell": true,\n'
            '    "ui_component_imports": true,\n'
            '    "ui_banned_patterns": true,\n'
            '    "ui_screen_recipes": true,\n'
            '    "ui_design_context_protocol": true,\n'
            '    "ui_tweak_strategy": true,\n'
            '    "ui_verification_handoff": true\n'
            "  },\n"
            f'  "evidence_identity": {json.dumps(frontend_identity, ensure_ascii=False)}\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    # 治理证据 mock（确保治理检查项通过）
    (project_dir / "output" / "governance-report-test.md").write_text(
        "# Pipeline 治理报告\n\n**状态**: PASSED\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-knowledge-references.json").write_text(
        '{"referenced_files": 5, "hit_rate": 0.65}\n',
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-metrics.json").write_text(
        '{"quality_gate_score": 90}\n',
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-validation-results.json").write_text(
        '{"passed": true, "score": 95}\n',
        encoding="utf-8",
    )
    (project_dir / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs" / "adr" / "ADR-001.md").write_text(
        "# ADR-001: 选择 PostgreSQL\n\n## 决策\n使用 PostgreSQL。\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-research.md").write_text(
        "# Research\n\n- similar products\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-prd.md").write_text(
        "# PRD\n\n- delivery workflow\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-architecture.md").write_text(
        "# Architecture\n\n- host-governed pipeline\n",
        encoding="utf-8",
    )
    (project_dir / "output" / f"{project_dir.name}-uiux.md").write_text(
        "# UIUX\n\n- frozen shell\n",
        encoding="utf-8",
    )
    record_stage_progress(project_dir, stage="research", status="completed")
    record_stage_progress(project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(project_dir, {"status": "confirmed", "actor": "pytest"})
    record_stage_progress(project_dir, stage="spec", status="completed")
    record_stage_progress(project_dir, stage="frontend", status="completed")
    save_bound_preview_confirmation(project_dir, {"status": "confirmed", "actor": "pytest"})
    record_stage_progress(project_dir, stage="quality", status="completed")

    ui_contract_path = project_dir / "output" / f"{project_dir.name}-ui-contract.json"
    ui_contract_payload = json.loads(ui_contract_path.read_text(encoding="utf-8"))
    ui_contract_path.write_text(
        json.dumps(ui_contract_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    quality_gate_identity = build_evidence_identity(
        project_dir,
        artifact_name="quality-gate",
        dependencies=[
            project_dir / "output" / f"{project_dir.name}-ui-review.json",
            project_dir / "output" / f"{project_dir.name}-ui-contract-alignment.json",
            project_dir / "output" / f"{project_dir.name}-uiux.md",
        ],
    )
    (project_dir / "output" / f"{project_dir.name}-quality-gate.json").write_text(
        json.dumps(
            {
                "passed": True,
                "total_score": 90,
                "summary": {"executive_summary": "quality gate passed"},
                "evidence_identity": quality_gate_identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    frontend_identity = build_evidence_identity(
        project_dir,
        artifact_name="frontend-runtime",
        dependencies=[
            project_dir / "output" / f"{project_dir.name}-ui-contract.json",
            project_dir / "output" / f"{project_dir.name}-ui-contract-alignment.json",
        ],
    )
    runtime_path = project_dir / "output" / f"{project_dir.name}-frontend-runtime.json"
    runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime_payload["evidence_identity"] = frontend_identity
    runtime_path.write_text(
        json.dumps(runtime_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    spec_identity = build_evidence_identity(
        project_dir,
        artifact_name="spec-compliance",
        dependencies=_spec_compliance_dependencies(project_dir, project_dir / "output"),
    )
    (project_dir / "output" / f"{project_dir.name}-spec-compliance.json").write_text(
        json.dumps(
            {
                "project_name": project_dir.name,
                "total_requirements": 0,
                "found": 0,
                "partial": 0,
                "missing": 0,
                "score": 100,
                "coverage_percent": 100.0,
                "matches": [],
                "evidence_identity": spec_identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    architecture_identity = build_evidence_identity(
        project_dir,
        artifact_name="architecture-drift",
        dependencies=_architecture_drift_dependencies(project_dir, project_dir / "output"),
    )
    (project_dir / "output" / f"{project_dir.name}-architecture-drift.json").write_text(
        json.dumps(
            {
                "project_name": project_dir.name,
                "declared_modules": [],
                "actual_modules": [],
                "declared_tech_stack": [],
                "actual_tech_stack": [],
                "drifts": [],
                "score": 100,
                "evidence_identity": architecture_identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    uiux_identity = build_evidence_identity(
        project_dir,
        artifact_name="uiux-compliance",
        dependencies=_uiux_compliance_dependencies(project_dir, project_dir / "output"),
    )
    (project_dir / "output" / f"{project_dir.name}-uiux-compliance.json").write_text(
        json.dumps(
            {
                "project_name": project_dir.name,
                "declared_icon_library": "lucide",
                "declared_typography": ["Space Grotesk", "Inter"],
                "declared_tokens": [],
                "violations": [],
                "score": 100,
                "files_scanned": 1,
                "evidence_identity": uiux_identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _prepare_spec_quality_change(project_dir: Path, change_id: str = "add-proof-ready") -> None:
    generator = SpecGenerator(project_dir)
    generator.init_sdd()
    change = generator.create_change(
        change_id=change_id,
        title="Add Proof Ready",
        description="用于发布前 spec 质量验证",
    )
    generator.scaffold_change_artifacts(change.id)


def test_release_readiness_detects_missing_docs(temp_project_dir: Path) -> None:
    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    assert report.passed is False
    assert "Documentation Coverage" in report.failed_checks or any(
        check.name == "Documentation Coverage" and not check.passed for check in report.checks
    )


def test_release_readiness_passes_when_required_artifacts_exist(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    _prepare_spec_quality_change(temp_project_dir)

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)
    files = evaluator.write(report)

    failed = {check.name: check for check in report.checks if not check.passed}
    assert failed == {}
    assert files["markdown"].exists()
    assert files["json"].exists()
    delivery_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert delivery_check.passed is True
    operational_check = next(
        check for check in report.checks if check.name == "Operational Harness Trail"
    )
    assert operational_check.passed is True
    assert operational_check.detail in {
        "operational harness clean across 3/3 enabled harnesses",
        "no operational harness evidence required",
    }


def test_release_readiness_flags_missing_expert_stage_governance(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text("arch", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    expert_check = next(check for check in report.checks if check.name == "Expert Stage Governance")
    assert expert_check.passed is False
    assert "research" in expert_check.detail
    assert "docs" in expert_check.detail


def test_release_readiness_passes_when_expert_stage_governance_is_recorded(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text("arch", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")

    record_stage_progress(temp_project_dir, stage="research", status="completed")
    record_stage_progress(temp_project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(temp_project_dir, {"status": "confirmed", "actor": "pytest"})

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    expert_check = next(check for check in report.checks if check.name == "Expert Stage Governance")
    assert expert_check.passed is True
    assert "3/3" in expert_check.detail


def test_release_readiness_fails_when_latest_spec_quality_is_weak(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    generator = SpecGenerator(temp_project_dir)
    generator.init_sdd()
    change = generator.create_change(
        change_id="weak-change",
        title="Weak Change",
        description="弱规格",
    )
    change_dir = temp_project_dir / ".super-dev" / "changes" / change.id
    (change_dir / "tasks.md").write_text("# Tasks\n\n", encoding="utf-8")

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    spec_check = next(check for check in report.checks if check.name == "Spec Quality")
    assert spec_check.passed is False
    assert "weak-change" in spec_check.detail


def test_release_readiness_fails_when_host_runtime_validation_repo_probe_breaks(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
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

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    runtime_check = next(check for check in report.checks if check.name == "Host Runtime Validation")
    assert runtime_check.passed is False
    assert "repo_probe_failed=codex-cli" in runtime_check.detail
    assert "codex-cli 已人工通过，但仓库级 repo probe 仍未通过" in report.executive_summary
    markdown = report.to_markdown()
    assert "## Executive Summary" in markdown
    assert "codex-cli 已人工通过，但仓库级 repo probe 仍未通过" in markdown


def test_release_readiness_fails_when_compliance_closure_detects_spec_gap(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    (temp_project_dir / "output" / f"{temp_project_dir.name}-prd.md").write_text(
        "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    compliance_check = next(check for check in report.checks if check.name == "Compliance Closure")
    assert compliance_check.passed is False
    assert "spec compliance artifact identity_mismatch" in compliance_check.detail
    assert "spec compliance score=0" in compliance_check.detail
    assert "合规链当前优先卡在证据状态：spec=identity_mismatch" in report.executive_summary
    assert "管理侧现在还不该做最终验收签字" in report.executive_summary
    assert report.passed is False


def test_release_readiness_executive_summary_exposes_workflow_and_baseline_context() -> None:
    report = ReleaseReadinessReport(
        project_name="demo",
        checks=[],
        workflow_context={
            "workflow_status": "waiting_baseline_confirmation",
            "blocking_gate": "waiting_baseline_confirmation",
            "recommended_host_action": "/super-dev-review baseline confirm",
        },
        baseline_governance={
            "status": "pending_confirmation",
            "entry_gate": "waiting_baseline_confirmation",
            "ready": False,
            "next_host_action": "/super-dev-review baseline confirm",
        },
    )
    assert "当前流程状态为 waiting_baseline_confirmation" in report.executive_summary
    assert "baseline 还没确认" in report.executive_summary
    assert "还停在正式确认门之前" in report.executive_summary
    payload = report.to_dict()
    assert payload["workflow_context"]["blocking_gate"] == "waiting_baseline_confirmation"
    assert payload["baseline_governance"]["status"] == "pending_confirmation"
    markdown = report.to_markdown()
    assert "## Workflow Context" in markdown
    assert "## Baseline Governance" in markdown


def test_release_readiness_fails_when_delivery_closure_is_incomplete(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    (temp_project_dir / "output" / f"{temp_project_dir.name}-task-execution.md").unlink()

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "task execution missing" in closure_check.detail


def test_release_readiness_fails_when_ui_contract_closure_is_incomplete(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    (temp_project_dir / "output" / f"{temp_project_dir.name}-ui-contract.json").unlink()

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "ui contract missing" in closure_check.detail


def test_release_readiness_fails_when_frontend_runtime_structural_ui_checks_fail(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    runtime_file = temp_project_dir / "output" / f"{temp_project_dir.name}-frontend-runtime.json"
    runtime_file.write_text(
        (
            "{\n"
            '  "passed": true,\n'
            '  "checks": {\n'
            '    "output_frontend_index": true,\n'
            '    "output_frontend_styles": true,\n'
            '    "output_frontend_design_tokens": true,\n'
            '    "output_frontend_script": true,\n'
            '    "preview_html": true,\n'
            '    "ui_contract_json": true,\n'
            '    "ui_contract_alignment": true,\n'
            '    "ui_theme_entry": false,\n'
            '    "ui_navigation_shell": true,\n'
            '    "ui_component_imports": true,\n'
            '    "ui_banned_patterns": true\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "frontend runtime ui contract alignment missing" in closure_check.detail


def test_release_readiness_fails_when_frontend_runtime_missing_claude_design_execution(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    runtime_file = temp_project_dir / "output" / f"{temp_project_dir.name}-frontend-runtime.json"
    runtime_file.write_text(
        (
            "{\n"
            '  "passed": true,\n'
            '  "checks": {\n'
            '    "output_frontend_index": true,\n'
            '    "output_frontend_styles": true,\n'
            '    "output_frontend_design_tokens": true,\n'
            '    "output_frontend_script": true,\n'
            '    "preview_html": true,\n'
            '    "ui_contract_json": true,\n'
            '    "ui_contract_alignment": true,\n'
            '    "ui_theme_entry": true,\n'
            '    "ui_navigation_shell": true,\n'
            '    "ui_component_imports": true,\n'
            '    "ui_banned_patterns": true,\n'
            '    "ui_screen_recipes": false,\n'
            '    "ui_design_context_protocol": true,\n'
            '    "ui_tweak_strategy": true,\n'
            '    "ui_verification_handoff": false\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "frontend runtime claude-design execution missing" in closure_check.detail
    assert "ui_screen_recipes" in closure_check.detail
    assert "ui_verification_handoff" in closure_check.detail


def test_release_readiness_fails_when_ui_review_runtime_protocol_drift(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    output_dir = temp_project_dir / "output"
    (output_dir / f"{temp_project_dir.name}-ui-review.json").write_text(
        json.dumps(
            {
                "alignment_summary": {
                    "runtime_claude_design_protocol": {
                        "passed": False,
                        "observed": "mismatch=screen_recipes, verification_handoff",
                    },
                    "source_claude_design_protocol": {
                        "passed": True,
                        "observed": "screen_recipes, design_context_protocol, tweak_strategy, verification_handoff",
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "ui review/runtime claude-design mismatch" in closure_check.detail
    assert "source/runtime 证据漂移" in report.executive_summary


def test_release_readiness_fails_when_screenshot_visual_judge_fails(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    output_dir = temp_project_dir / "output"
    (output_dir / f"{temp_project_dir.name}-ui-review.json").write_text(
        json.dumps(
            {
                "alignment_summary": {
                    "runtime_claude_design_protocol": {
                        "passed": True,
                        "observed": "aligned with frontend-runtime",
                    },
                    "source_claude_design_protocol": {
                        "passed": True,
                        "observed": "screen_recipes, design_context_protocol, tweak_strategy, verification_handoff",
                    },
                    "screenshot_visual_judge": {
                        "passed": False,
                        "observed": "blank=0.82, contrast=0.09, dominant=0.91",
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "ui review screenshot visual judge failed" in closure_check.detail
    assert "截图级视觉验收未通过" in report.executive_summary
    assert "商业质感不足或像半成品" in report.executive_summary
    assert "blank=0.82, contrast=0.09, dominant=0.91" in report.executive_summary


def test_release_readiness_executive_summary_exposes_framework_playbook_gap() -> None:
    report = ReleaseReadinessReport(
        project_name="demo",
        checks=[
            ReleaseReadinessCheck(
                name="Framework Harness Trail",
                passed=False,
                detail="uni-app harness has 2 blockers",
                recommendation="补齐 framework playbook：implementation modules、platform constraints、execution guardrails、native capabilities、validation surfaces、delivery evidence。",
            )
        ],
    )

    assert "跨平台框架专项当前卡在 uni-app playbook/执行闭环" in report.executive_summary
    assert "跨端体验稳定性、专项验收效率和上线节奏" in report.executive_summary
    assert "补齐 framework playbook" in report.executive_summary


def test_release_readiness_executive_summary_speaks_in_release_decision_language() -> None:
    report = ReleaseReadinessReport(
        project_name="demo",
        checks=[
            ReleaseReadinessCheck(
                name="Host Runtime Validation",
                passed=False,
                detail="repo probe blocked",
                severity="high",
            )
        ],
    )

    assert "从发布决策视角看" in report.executive_summary
    assert "不适合直接做最终客户演示、上线签字或对外交付" in report.executive_summary


def test_release_readiness_fails_when_cross_platform_runtime_missing_framework_execution(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    contract_file = temp_project_dir / "output" / f"{temp_project_dir.name}-ui-contract.json"
    payload = json.loads(contract_file.read_text(encoding="utf-8"))
    payload["analysis"] = {"frontend": "uni-app"}
    payload["framework_playbook"] = {
        "framework": "uni-app",
        "implementation_modules": ["自定义导航栏高度"],
        "platform_constraints": ["status bar 与安全区"],
        "execution_guardrails": ["先冻结 navigationStyle"],
        "native_capabilities": ["登录 provider"],
        "validation_surfaces": ["微信小程序导航"],
        "delivery_evidence": ["三端差异说明"],
    }
    contract_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    runtime_file = temp_project_dir / "output" / f"{temp_project_dir.name}-frontend-runtime.json"
    runtime_file.write_text(
        (
            "{\n"
            '  "passed": false,\n'
            '  "checks": {\n'
            '    "output_frontend_index": true,\n'
            '    "output_frontend_styles": true,\n'
            '    "output_frontend_design_tokens": true,\n'
            '    "output_frontend_script": true,\n'
            '    "preview_html": true,\n'
            '    "ui_contract_json": true,\n'
            '    "ui_contract_alignment": true,\n'
            '    "ui_theme_entry": true,\n'
            '    "ui_navigation_shell": true,\n'
            '    "ui_component_imports": true,\n'
            '    "ui_banned_patterns": true,\n'
            '    "ui_framework_playbook": true,\n'
            '    "ui_framework_execution": false\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "uni-app frontend runtime framework execution missing" in closure_check.detail


def test_release_readiness_fails_when_ui_contract_missing_emoji_policy(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    contract_file = temp_project_dir / "output" / f"{temp_project_dir.name}-ui-contract.json"
    payload = json.loads(contract_file.read_text(encoding="utf-8"))
    payload.pop("emoji_policy", None)
    contract_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "ui contract incomplete" in closure_check.detail


def test_release_readiness_fails_when_cross_platform_ui_contract_missing_framework_playbook(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    contract_file = temp_project_dir / "output" / f"{temp_project_dir.name}-ui-contract.json"
    payload = json.loads(contract_file.read_text(encoding="utf-8"))
    payload["analysis"] = {"frontend": "uni-app"}
    contract_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "uni-app ui contract playbook incomplete" in closure_check.detail


def test_release_readiness_fails_when_quality_gate_evidence_identity_mismatches(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    _prepare_spec_quality_change(temp_project_dir)
    output_dir = temp_project_dir / "output"
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("# uiux", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-ui-review.json").write_text(
        json.dumps({"passed": True}, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-ui-contract-alignment.json").write_text(
        json.dumps({"aligned": True}, ensure_ascii=False),
        encoding="utf-8",
    )
    identity = build_evidence_identity(
        temp_project_dir,
        artifact_name="quality-gate",
        dependencies=[
            output_dir / f"{temp_project_dir.name}-ui-review.json",
            output_dir / f"{temp_project_dir.name}-ui-contract-alignment.json",
            output_dir / f"{temp_project_dir.name}-uiux.md",
        ],
    )
    (output_dir / f"{temp_project_dir.name}-quality-gate.json").write_text(
        json.dumps(
            {
                "passed": True,
                "total_score": 90,
                "summary": {"executive_summary": "ok"},
                "evidence_identity": identity,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("# uiux v2", encoding="utf-8")

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "quality gate evidence mismatch" in closure_check.detail


def test_release_readiness_treats_waiting_baseline_confirmation_as_blocker(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    output_dir = temp_project_dir / "output"
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n",
        encoding="utf-8",
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_baseline_confirmation",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "等待 baseline 确认",
            "recommended_command": "先确认 baseline，再继续当前流程",
        },
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认当前项目边界和差量计划",
            "actor": "pytest",
        },
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    assert report.passed is False
    recovery_check = next(check for check in report.checks if check.name == "Workflow Recovery Trail")
    assert recovery_check.passed is False
    assert "baseline confirmation pending" in recovery_check.detail
    assert "baseline" in report.executive_summary


def test_release_readiness_exposes_baseline_confirmation_check(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    output_dir = temp_project_dir / "output"
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n",
        encoding="utf-8",
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_baseline_confirmation",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "等待 baseline 确认",
            "recommended_command": "先确认 baseline，再继续当前流程",
        },
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认当前项目边界和差量计划",
            "actor": "pytest",
        },
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    baseline_check = next(check for check in report.checks if check.name == "Baseline Confirmation")
    assert baseline_check.passed is False
    assert baseline_check.severity == "critical"
    assert baseline_check.detail == "baseline confirmation pending_review"


def test_release_readiness_fails_when_frontend_runtime_evidence_identity_mismatches(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    _prepare_spec_quality_change(temp_project_dir)
    output_dir = temp_project_dir / "output"
    identity = build_evidence_identity(
        temp_project_dir,
        artifact_name="frontend-runtime",
        dependencies=[
            output_dir / f"{temp_project_dir.name}-ui-contract.json",
            output_dir / f"{temp_project_dir.name}-ui-contract-alignment.json",
        ],
    )
    runtime_file = output_dir / f"{temp_project_dir.name}-frontend-runtime.json"
    runtime_payload = json.loads(runtime_file.read_text(encoding="utf-8"))
    runtime_payload["evidence_identity"] = identity
    runtime_file.write_text(json.dumps(runtime_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "style_direction": "changed",
                "typography": {"heading": "Space Grotesk", "body": "Inter"},
                "icon_system": "lucide-react",
                "emoji_policy": {
                    "allowed_in_ui": False,
                    "allowed_as_icon": False,
                    "allowed_during_development": False,
                },
                "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},
                "design_tokens": {"color": {"primary": "#0f172a"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    closure_check = next(check for check in report.checks if check.name == "Delivery Closure")
    assert closure_check.passed is False
    assert "frontend runtime evidence mismatch" in closure_check.detail


def test_release_readiness_fails_when_active_workflow_recovery_trail_is_incomplete(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "continue",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )
    workflow_event_log_file(temp_project_dir).unlink()

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    continuity_check = next(check for check in report.checks if check.name == "Workflow Recovery Trail")
    assert continuity_check.passed is False
    assert "workflow recovery trail incomplete" in continuity_check.detail


def test_release_readiness_fails_when_hook_audit_contains_blocked_event(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    history_file = HookManager.hook_history_file(temp_project_dir)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        json.dumps(
            {
                "hook_name": "python3 scripts/guard.py",
                "event": "WorkflowEvent",
                "success": False,
                "output": "",
                "error": "blocked by policy",
                "duration_ms": 8.4,
                "blocked": True,
                "phase": "quality_revision_saved",
                "source": "config",
                "timestamp": "2026-04-06T01:02:03+00:00",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    hook_check = next(check for check in report.checks if check.name == "Hook Audit Trail")
    assert hook_check.passed is False
    assert "blocked events" in hook_check.detail
    markdown = report.to_markdown()
    assert "## Operational Continuity" in markdown
    assert "## Current Governance Focus" in markdown
    assert "## Recent Operational Timeline" in markdown
    assert "Operational Harness Trail" in markdown
    assert "Workflow Recovery Trail" in markdown
    assert "Framework Harness Trail" in markdown
    assert "Hook Audit Trail" in markdown


def test_release_readiness_fails_when_framework_harness_has_blockers(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)

    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "analysis": {"frontend": "uni-app"},
                "framework_playbook": {
                    "framework": "uni-app",
                    "implementation_modules": ["pages", "composables"],
                    "native_capabilities": [],
                    "validation_surfaces": ["微信小程序导航/支付/触控与包体策略"],
                    "delivery_evidence": ["跨端截图"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    framework_check = next(
        check for check in report.checks if check.name == "Framework Harness Trail"
    )
    assert framework_check.passed is False
    assert "uni-app harness has" in framework_check.detail


def test_release_readiness_fails_when_operational_harness_has_blockers(
    temp_project_dir: Path,
) -> None:
    _prepare_release_ready_project(temp_project_dir)

    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-ui-contract.json").write_text(
        json.dumps(
            {
                "analysis": {"frontend": "uni-app"},
                "framework_playbook": {
                    "framework": "uni-app",
                    "implementation_modules": ["pages"],
                    "native_capabilities": [],
                    "validation_surfaces": ["微信小程序导航"],
                    "delivery_evidence": ["跨端截图"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    operational_check = next(
        check for check in report.checks if check.name == "Operational Harness Trail"
    )
    assert operational_check.passed is False
    assert "需要先处理" in operational_check.detail


def test_release_readiness_fails_when_latest_spec_contains_tbd_placeholders(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    _prepare_spec_quality_change(temp_project_dir, change_id="placeholder-change")

    spec_file = next((temp_project_dir / ".super-dev" / "changes" / "placeholder-change" / "specs").rglob("spec.md"))
    spec_file.write_text(
        "# Placeholder Change\n\n## Requirements\n\n### Requirement: Example\n\nSHALL keep placeholder\n\n#### Scenario 1: TBD\n- DETAIL REQUIRED\n",
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    spec_check = next(check for check in report.checks if check.name == "Spec Quality")
    assert spec_check.passed is False
    assert "placeholder-change" in spec_check.detail


def test_release_readiness_fails_when_scope_coverage_has_high_priority_gap(temp_project_dir: Path) -> None:
    _prepare_release_ready_project(temp_project_dir)
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text(
        "\n".join(
            [
                "# PRD",
                "",
                "## 2. 功能范围",
                "",
                "### 用户登录",
                "- 支持邮箱密码登录",
                "",
                "### Canvas 工作台",
                "- 提供交互式画布编辑",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-research.md").write_text(
        "| 优先级 | 事项 | 工作量 |\n|:---:|:---|:---|\n| P0 | Canvas 工作台 | 大 |\n",
        encoding="utf-8",
    )
    change_dir = temp_project_dir / ".super-dev" / "changes" / "release-hardening-finalization"
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] 用户登录\n- [ ] Canvas 工作台\n",
        encoding="utf-8",
    )

    evaluator = ReleaseReadinessEvaluator(temp_project_dir)
    report = evaluator.evaluate(verify_tests=False)

    scope_check = next(check for check in report.checks if check.name == "Scope Coverage")
    assert scope_check.passed is False
    assert "high_priority_gaps=1" in scope_check.detail
