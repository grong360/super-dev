from pathlib import Path

from super_dev.analyzer import ProductAuditBuilder
from super_dev.review_state import (
    save_host_runtime_validation,
    save_workflow_state,
)


def _prepare_product_docs(project_dir: Path) -> None:
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n",
        encoding="utf-8",
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n",
        encoding="utf-8",
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n",
        encoding="utf-8",
    )


def test_product_audit_detects_missing_product_audit_doc(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    assert any(item.title.startswith("缺少关键产品文档") for item in report.findings)


def test_product_audit_writes_report(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")
    (docs_dir / "PRODUCT_AUDIT.md").write_text("super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8")

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()
    files = builder.write(report)

    assert files["markdown"].exists()
    assert files["json"].exists()


def test_product_audit_detects_layered_host_runtime_gap(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")
    (docs_dir / "PRODUCT_AUDIT.md").write_text("super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8")

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

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "宿主 runtime 与交付闭环证据脱节")
    assert finding.severity == "high"
    assert "codex-cli" in finding.summary
    assert "workflow continuity" in finding.recommendation


def test_product_audit_detects_compliance_artifact_gap(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")
    (docs_dir / "PRODUCT_AUDIT.md").write_text("super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8")
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-prd.md").write_text(
        "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
        encoding="utf-8",
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "合规链证据状态未闭环")
    assert finding.severity == "high"
    assert "spec=missing" in finding.summary


def test_product_audit_distinguishes_missing_baseline_for_existing_project(
    temp_project_dir: Path,
) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")
    (docs_dir / "PRODUCT_AUDIT.md").write_text("super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8")

    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_baseline",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "先完成当前项目 baseline 扫描",
            "recommended_command": "先扫描当前项目，再继续当前流程",
        },
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "已有项目模式缺少 baseline audit")
    assert finding.severity == "high"
    assert "baseline audit" in finding.summary


def test_product_audit_distinguishes_waiting_baseline_confirmation(
    temp_project_dir: Path,
) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text("super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8")
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text("/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8")
    (docs_dir / "WORKFLOW_GUIDE.md").write_text("super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n", encoding="utf-8")
    (docs_dir / "PRODUCT_AUDIT.md").write_text("super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8")
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-baseline-audit.md").write_text("# baseline\n", encoding="utf-8")

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

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "已有项目 baseline 尚未确认")
    assert finding.severity == "high"
    assert "missing" in finding.summary

