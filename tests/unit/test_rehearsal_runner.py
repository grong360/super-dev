import json
from pathlib import Path

from super_dev.deployers.rehearsal_runner import LaunchRehearsalRunner
from super_dev.evidence_identity import build_evidence_identity


def _prepare_common_artifacts(temp_project_dir: Path, project_name: str) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{project_name}-redteam.md").write_text(
        (
            "# demo-redteam\n\n"
            "- **Critical 问题**: 0\n"
            "- **总分**: 90/100\n"
            "**状态**: 通过 - 质量良好\n"
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_name}-quality-gate.md").write_text(
        (
            "# 质量门禁报告\n\n"
            "**状态**: <span style='color:green'>通过</span>\n"
            "**总分**: 88/100\n"
        ),
        encoding="utf-8",
    )
    (output_dir / f"{project_name}-pipeline-metrics.json").write_text(
        (
            "{\n"
            '  "project_name": "demo",\n'
            '  "success": true,\n'
            '  "success_rate": 100,\n'
            '  "total_duration_seconds": 11.4,\n'
            '  "stages": []\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    delivery_dir = output_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    (delivery_dir / f"{project_name}-delivery-manifest.json").write_text(
        (
            "{\n"
            '  "project_name": "demo",\n'
            '  "status": "ready"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    rehearsal_dir = output_dir / "rehearsal"
    rehearsal_dir.mkdir(parents=True, exist_ok=True)
    (rehearsal_dir / f"{project_name}-launch-rehearsal.md").write_text("# Launch", encoding="utf-8")
    (rehearsal_dir / f"{project_name}-rollback-playbook.md").write_text("# Rollback", encoding="utf-8")
    (rehearsal_dir / f"{project_name}-smoke-checklist.md").write_text("# Smoke", encoding="utf-8")

    (temp_project_dir / "backend" / "migrations").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "backend" / "migrations" / "001_init.sql").write_text(
        "-- migration",
        encoding="utf-8",
    )

    (temp_project_dir / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / ".github" / "workflows" / "ci.yml").write_text("name: ci", encoding="utf-8")
    (temp_project_dir / ".github" / "workflows" / "cd.yml").write_text("name: cd", encoding="utf-8")

    governance_dir = output_dir / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    (governance_dir / "governance-report-20260328.md").write_text(
        (
            "# Pipeline 治理报告\n\n"
            "**项目**: demo\n"
            "**Run ID**: 20260328-abc\n"
            "**状态**: PASSED\n\n"
            "命中率: 85%\n"
        ),
        encoding="utf-8",
    )


def test_rehearsal_runner_passes_when_all_artifacts_ready(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()

    assert result.passed is True
    assert result.score >= 80
    files = runner.write(result)
    assert files["markdown"].exists()
    assert files["json"].exists()


def test_rehearsal_runner_detects_quality_gate_failed_text(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)

    # 覆盖为“未通过”，验证不会被“通过”子串误判。
    (temp_project_dir / "output" / f"{project_name}-quality-gate.md").write_text(
        (
            "# 质量门禁报告\n\n"
            "**状态**: <span style='color:red'>未通过</span>\n"
            "**总分**: 78/100\n"
        ),
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    quality_checks = [item for item in result.checks if item.name == "Quality Gate"]

    assert quality_checks
    assert quality_checks[0].passed is False
    assert result.passed is False


def test_rehearsal_runner_surfaces_quality_gate_executive_summary(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)

    (temp_project_dir / "output" / f"{project_name}-quality-gate.md").write_text(
        (
            "# 质量门禁报告\n\n"
            "**状态**: <span style='color:red'>未通过</span>\n"
            "**总分**: 78/100\n\n"
            "---\n\n"
            "## 执行摘要\n\n"
            "质量门禁未通过，当前得分 78/100，加权分 76.0/100。"
            "优先修复：宿主兼容性。 宿主验收存在分层差异：codex-cli 已人工通过，"
            "但仓库级 continuity / harness / runtime 证据仍未闭环。\n"
        ),
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    quality_check = next(item for item in result.checks if item.name == "Quality Gate")

    assert quality_check.passed is False
    assert "codex-cli 已人工通过" in quality_check.detail


def test_rehearsal_runner_prefers_quality_gate_json_payload(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    (temp_project_dir / "output" / f"{project_name}-quality-gate.json").write_text(
        (
            "{\n"
            '  "passed": false,\n'
            '  "total_score": 76,\n'
            '  "summary": {\n'
            '    "executive_summary": "质量门禁未通过，当前得分 76/100。优先修复：宿主兼容性。"\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    quality_check = next(item for item in result.checks if item.name == "Quality Gate")

    assert quality_check.passed is False
    assert "quality score=76" in quality_check.detail
    assert "优先修复：宿主兼容性" in quality_check.detail


def test_rehearsal_runner_surfaces_frontend_governance_state_from_quality_gate_json(
    temp_project_dir: Path,
) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    (temp_project_dir / "output" / f"{project_name}-quality-gate.json").write_text(
        (
            "{\n"
            '  "passed": false,\n'
            '  "total_score": 74,\n'
            '  "summary": {\n'
            '    "executive_summary": "质量门禁未通过，当前得分 74/100。优先修复：UI 契约执行。 UI 阶段当前存在 source/runtime 证据漂移，mismatch=screen_recipes。"\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    quality_check = next(item for item in result.checks if item.name == "Quality Gate")

    assert quality_check.passed is False
    assert "ui_governance=source_runtime_drift" in quality_check.detail


def test_rehearsal_runner_writes_evidence_identity(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    (temp_project_dir / "output" / f"{project_name}-proof-pack.json").write_text(
        '{"status":"ready"}',
        encoding="utf-8",
    )
    (temp_project_dir / "output" / f"{project_name}-release-readiness.json").write_text(
        '{"passed":true}',
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    files = runner.write(result)
    payload = json.loads(files["json"].read_text(encoding="utf-8"))

    assert "evidence_identity" in payload
    expected = build_evidence_identity(
        temp_project_dir,
        artifact_name="rehearsal-report",
        dependencies=[
            temp_project_dir / "output" / f"{project_name}-quality-gate.json",
            temp_project_dir / "output" / f"{project_name}-quality-gate.md",
            temp_project_dir / "output" / f"{project_name}-release-readiness.json",
            temp_project_dir / "output" / f"{project_name}-proof-pack.json",
            temp_project_dir / "output" / "delivery" / f"{project_name}-delivery-manifest.json",
        ],
    )
    assert payload["evidence_identity"]["inputs_digest"] == expected["inputs_digest"]


def test_rehearsal_runner_accepts_legacy_redteam_markdown_without_score(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    (temp_project_dir / "output" / f"{project_name}-redteam.md").write_text(
        "- **Critical 问题**: 0\n**状态**: 通过 - 质量良好\n",
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    redteam_check = next(item for item in result.checks if item.name == "Redteam Report")

    assert redteam_check.passed is True


def test_rehearsal_runner_prefers_redteam_json_evidence(temp_project_dir: Path) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    (temp_project_dir / "output" / f"{project_name}-redteam.json").write_text(
        (
            "{\n"
            '  "project_name": "demo",\n'
            '  "pass_threshold": 70,\n'
            '  "critical_count": 1,\n'
            '  "high_count": 0,\n'
            '  "total_score": 62,\n'
            '  "passed": false,\n'
            '  "blocking_reasons": ["存在 1 个 critical 问题"],\n'
            '  "security_issues": [{"severity": "critical", "category": "auth", "description": "x", "recommendation": "y"}],\n'
            '  "performance_issues": [],\n'
            '  "architecture_issues": []\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    redteam_check = next(item for item in result.checks if item.name == "Redteam Report")

    assert redteam_check.passed is False
    assert "critical" in redteam_check.detail


def test_rehearsal_runner_accepts_live_governance_snapshot_without_final_report(
    temp_project_dir: Path,
) -> None:
    project_name = "demo"
    _prepare_common_artifacts(temp_project_dir, project_name=project_name)
    governance_report = (
        temp_project_dir / "output" / "governance" / "governance-report-20260328.md"
    )
    governance_report.unlink()
    (temp_project_dir / "output" / f"{project_name}-pipeline-contract.md").write_text(
        "# Pipeline Contract\n\n- Success: yes\n",
        encoding="utf-8",
    )
    (temp_project_dir / "output" / "knowledge-cache").mkdir(parents=True, exist_ok=True)
    (
        temp_project_dir
        / "output"
        / "knowledge-cache"
        / f"{project_name}-knowledge-bundle.json"
    ).write_text(
        '{"local_knowledge":[],"web_knowledge":[],"research_summary":"fixture"}',
        encoding="utf-8",
    )

    runner = LaunchRehearsalRunner(
        project_dir=temp_project_dir,
        project_name=project_name,
        cicd_platform="github",
    )
    result = runner.run()
    governance_check = next(item for item in result.checks if item.name == "Governance Status")

    assert governance_check.passed is True
    assert "pending-finalization" in governance_check.detail
