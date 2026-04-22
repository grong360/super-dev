"""
质量门禁检查器测试
"""

import json
from pathlib import Path
from types import SimpleNamespace

from super_dev.review_state import save_host_runtime_validation, save_workflow_state
from super_dev.reviewers.quality_gate import (
    CheckStatus,
    QualityCheck,
    QualityGateChecker,
    QualityGateResult,
)


class TestQualityGateChecker:
    def test_scenario_override_zero_to_one(self, temp_project_dir: Path):
        # 即使存在源码目录，通过 override 仍应按 0-1 判定
        (temp_project_dir / "src").mkdir(parents=True, exist_ok=True)

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="0-1",
        )
        assert checker.is_zero_to_one is True

    def test_scenario_override_one_to_many(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )
        assert checker.is_zero_to_one is False

    def test_threshold_override(self, temp_project_dir: Path, monkeypatch):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="0-1",
            threshold_override=95,
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约执行",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_calculate_total_score", lambda _c: 90)
        monkeypatch.setattr(checker, "_calculate_weighted_score", lambda _c: 90.0)
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        result = checker.check(None)
        assert result.passed is False

    def test_required_failed_check_blocks_gate_even_with_high_score(self, temp_project_dir: Path, monkeypatch):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )

        failed_required = QualityCheck(
            name="安全审查",
            category="security",
            description="存在 critical 漏洞",
            status=CheckStatus.FAILED,
            score=95,
            weight=1.5,
        )
        passing_docs = QualityCheck(
            name="PRD 文档",
            category="documentation",
            description="文档完整",
            status=CheckStatus.PASSED,
            score=100,
            weight=1.0,
        )
        checks = [failed_required, passing_docs]

        monkeypatch.setattr(checker, "_check_documentation", lambda: [passing_docs])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [failed_required])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约执行",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_calculate_total_score", lambda _c: 95)
        monkeypatch.setattr(checker, "_calculate_weighted_score", lambda _c: 95.0)
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        result = checker.check(None)
        assert result.passed is False
        assert result.critical_failures
        assert checks[0].description in result.critical_failures[0]

    def test_testing_check_runs_pytest(self, temp_project_dir: Path, monkeypatch):
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_demo.py").write_text("def test_demo(): assert True\n", encoding="utf-8")
        (temp_project_dir / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )

        monkeypatch.setattr("super_dev.reviewers.quality_gate.shutil.which", lambda _: "/usr/bin/pytest")
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 0,
                "stdout": "1 passed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 82)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert names["测试执行"].status.value == "passed"
        assert names["测试覆盖率"].score == 82

    def test_testing_check_failed_when_pytest_fails(self, temp_project_dir: Path, monkeypatch):
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_demo.py").write_text("def test_demo(): assert False\n", encoding="utf-8")

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )

        monkeypatch.setattr("super_dev.reviewers.quality_gate.shutil.which", lambda _: "/usr/bin/pytest")
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 1,
                "stdout": "1 failed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 40)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert names["测试执行"].status.value == "failed"
        assert names["测试覆盖率"].status.value == "failed"

    def test_read_coverage_percent(self, temp_project_dir: Path):
        coverage = temp_project_dir / "coverage.xml"
        coverage.write_text(
            '<?xml version="1.0" ?><coverage line-rate="0.756"></coverage>',
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._read_coverage_percent() == 76

    def test_quality_gate_runs_compliance_checks_proactively(self, temp_project_dir: Path, monkeypatch):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_accessibility", lambda: [])
        monkeypatch.setattr(checker, "_check_performance_budget", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="ok",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: QualityCheck(
                name="UI 审查",
                category="ui_quality",
                description="ok",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        monkeypatch.setattr(
            "super_dev.reviewers.spec_compliance.run_spec_compliance",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_requirements=3,
                coverage_percent=66.7,
                score=67,
            ),
        )
        monkeypatch.setattr(
            "super_dev.reviewers.architecture_drift.run_architecture_drift",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_drifts=1,
                critical_count=0,
                declared_tech_stack=["FastAPI"],
                score=78,
            ),
        )
        monkeypatch.setattr(
            "super_dev.reviewers.uiux_compliance.run_uiux_compliance",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_violations=2,
                files_scanned=4,
                score=82,
            ),
        )

        result = checker.check(None)
        categories = {check.category for check in result.checks}

        assert {"spec_compliance", "architecture_drift", "uiux_compliance"} <= categories

    def test_quality_gate_executive_summary_explains_layered_host_runtime_gap(
        self, temp_project_dir: Path, monkeypatch
    ):
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

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_accessibility", lambda: [])
        monkeypatch.setattr(checker, "_check_performance_budget", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_host_compatibility",
            lambda: QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约执行",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: QualityCheck(
                name="UI 审查",
                category="ui_quality",
                description="UI 审查",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        result = checker.check(None)

        assert "codex-cli 已人工通过" in result.executive_summary
        assert "continuity / harness / runtime 证据仍未闭环" in result.executive_summary
        markdown = result.to_markdown()
        assert "## 执行摘要" in markdown
        assert "codex-cli 已人工通过" in markdown

    def test_quality_gate_executive_summary_explains_compliance_artifact_gap(self):
        result = QualityGateResult(
            passed=False,
            total_score=72,
            weighted_score=72.0,
            checks=[
                QualityCheck(
                    name="Spec Compliance (Requirement Traceability)",
                    category="spec_compliance",
                    description="Source: missing; Coverage: 0.0% (1 requirements)",
                    status=CheckStatus.FAILED,
                    score=0,
                )
            ],
            critical_failures=[],
            recommendations=[],
            scenario="1-N+1",
            summary_context={"compliance_signal_summary": " 合规链当前优先卡在证据状态：Spec Compliance (Requirement Traceability)=missing。"},
        )
        assert "合规链当前优先卡在证据状态" in result.executive_summary
        assert "Requirement Traceability)=missing" in result.executive_summary

    def test_quality_gate_executive_summary_exposes_workflow_and_baseline_context(self):
        result = QualityGateResult(
            passed=False,
            total_score=72,
            weighted_score=72.0,
            checks=[],
            critical_failures=[],
            recommendations=[],
            scenario="1-N+1",
            summary_context={
                "workflow_signal_summary": " 当前流程状态为 waiting_baseline_confirmation，入口 gate=waiting_baseline_confirmation。 下一步：/super-dev-review baseline confirm。",
                "baseline_signal_summary": " 当前是已有项目模式，但 baseline 还没确认。 下一步：/super-dev-review baseline confirm。",
            },
        )
        assert "当前流程状态为 waiting_baseline_confirmation" in result.executive_summary
        assert "baseline 还没确认" in result.executive_summary

    def test_has_pytest_config_requires_real_marker(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._has_pytest_config() is False

    def test_has_pytest_config_from_pyproject_marker(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\naddopts='-q'\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._has_pytest_config() is True

    def test_discover_js_test_targets_and_run(self, temp_project_dir: Path, monkeypatch):
        frontend = temp_project_dir / "frontend"
        frontend.mkdir(parents=True, exist_ok=True)
        (frontend / "package.json").write_text(
            '{"name":"frontend","scripts":{"test":"vitest run"}}',
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr("super_dev.reviewers.quality_gate.shutil.which", lambda cmd: "/usr/bin/npm" if cmd == "npm" else None)
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 0,
                "stdout": "1 passed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 85)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert checker._has_js_test_script() is True
        assert names["测试执行"].status.value == "passed"

    def test_spec_task_completion_passed(self, temp_project_dir: Path):
        task_file = temp_project_dir / ".super-dev" / "changes" / "demo" / "tasks.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [x] **1.2: done**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "passed"
        assert check.score == 100

    def test_spec_task_completion_failed_with_pending(self, temp_project_dir: Path):
        task_file = temp_project_dir / ".super-dev" / "changes" / "demo" / "tasks.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [ ] **1.2: pending**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "failed"

    def test_spec_task_completion_uses_latest_change_file(self, temp_project_dir: Path):
        legacy_task_file = temp_project_dir / ".super-dev" / "changes" / "legacy" / "tasks.md"
        legacy_task_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [ ] **1.2: pending**\n",
            encoding="utf-8",
        )

        latest_task_file = temp_project_dir / ".super-dev" / "changes" / "latest" / "tasks.md"
        latest_task_file.parent.mkdir(parents=True, exist_ok=True)
        latest_task_file.write_text(
            "# Tasks\n\n- [x] **2.1: done**\n- [x] **2.2: done**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "passed"
        assert "latest" in check.details

    def test_document_consistency_passed_when_new_sections_complete(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            (
                "## 1\n主视觉气质\n字体组合\n配色逻辑\n图标系统\n备选实现路径\n明确不默认采用\n"
                "Design Token 冻结输出\n2 个视觉方向候选\n"
                "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\nWEB\nH5\n微信小程序\nAPP\n桌面端\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "passed"
        assert check.score == 100

    def test_document_consistency_failed_when_platform_coverage_missing(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "failed"
        assert "UI 五端覆盖" in check.details

    def test_document_consistency_warns_when_ui_system_decisions_missing(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\nWEB\nH5\n微信小程序\nAPP\n桌面端\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "warning"
        assert "UI 风格决策冻结" in check.details

    def test_pipeline_observability_check_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-pipeline-metrics.json").write_text(
            (
                "{\n"
                '  "project_name": "demo",\n'
                '  "success": true,\n'
                '  "success_rate": 100,\n'
                '  "stages": []\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_pipeline_observability()
        assert check.status.value == "passed"

    def test_host_compatibility_check_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 92.5,\n'
                '    "ready_hosts": 2,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"
        assert check.score == 92

    def test_host_compatibility_check_failed_when_score_low(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 48,\n'
                '    "ready_hosts": 0,\n'
                '    "total_hosts": 5\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "failed"
        assert check.score == 48

    def test_host_compatibility_check_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "warning"

    def test_host_compatibility_uses_config_thresholds(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 90\n"
                "host_compatibility_min_ready_hosts: 2\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 85,\n'
                '    "ready_hosts": 1,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "warning"
        assert "90" in check.details

    def test_host_compatibility_override_thresholds_take_precedence(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 95\n"
                "host_compatibility_min_ready_hosts: 3\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 82,\n'
                '    "ready_hosts": 1,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
            host_compatibility_min_score_override=80,
            host_compatibility_min_ready_hosts_override=1,
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"

    def test_host_compatibility_uses_selected_host_profile(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 80\n"
                "host_compatibility_min_ready_hosts: 1\n"
                "host_profile_targets:\n"
                "  - codex-cli\n"
                "  - claude-code\n"
                "host_profile_enforce_selected: true\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 20,\n'
                '    "ready_hosts": 0,\n'
                '    "total_hosts": 6,\n'
                '    "hosts": {\n'
                '      "codex-cli": {"score": 100, "ready": true},\n'
                '      "claude-code": {"score": 90, "ready": true},\n'
                '      "cursor": {"score": 0, "ready": false}\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"
        assert "profile=codex-cli,claude-code" in check.details

    def test_host_compatibility_selected_profile_missing_hosts(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_profile_targets:\n"
                "  - codex-cli\n"
                "host_profile_enforce_selected: true\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 100,\n'
                '    "ready_hosts": 3,\n'
                '    "total_hosts": 3,\n'
                '    "hosts": {\n'
                '      "cursor": {"score": 100, "ready": true}\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value in {"warning", "failed"}

    def test_launch_rehearsal_check_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_launch_rehearsal()
        assert check.status.value == "warning"

    def test_rehearsal_verification_report_passed(self, temp_project_dir: Path):
        rehearsal_dir = temp_project_dir / "output" / "rehearsal"
        rehearsal_dir.mkdir(parents=True, exist_ok=True)
        (rehearsal_dir / "demo-rehearsal-report.md").write_text("# report", encoding="utf-8")
        (rehearsal_dir / "demo-rehearsal-report.json").write_text('{"passed": true}', encoding="utf-8")

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_rehearsal_verification_report()
        assert check.status.value == "passed"

    def test_rehearsal_verification_report_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_rehearsal_verification_report()
        assert check.status.value == "warning"

    def test_task_execution_review_trace_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-task-execution.md").write_text(
            (
                "# Spec 任务执行报告\n\n"
                "## 执行期验证摘要\n\n"
                "- 任务闭环: 通过\n\n"
                "## 宿主补充自检（交付前必做）\n\n"
                "- [ ] 运行项目原生 build / compile / type-check / test / runtime smoke，并确认没有编译错误\n"
                "- [ ] 检查本轮新增函数、方法、字段、模块都已接入真实调用链；未接入则删除\n"
                "- [ ] 检查没有新增 unused code、未引用文件或新增 warning\n"
                "- [ ] 对本次 diff 做最小自审，确认新增日志、埋点、恢复逻辑真正生效\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        check = checker._check_task_execution_review_trace()
        assert check.status.value == "passed"

    def test_task_execution_review_trace_warning_when_missing_markers(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-task-execution.md").write_text("# Spec 任务执行报告\n", encoding="utf-8")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_task_execution_review_trace()
        assert check.status.value == "warning"

    def test_knowledge_governance_passed(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "knowledge_allowed_domains:\n"
                "  - openai.com\n"
                "knowledge_cache_ttl_seconds: 120\n"
            ),
            encoding="utf-8",
        )
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            (
                "{\n"
                '  "cache_signature": "abc123",\n'
                '  "cache_ttl_seconds": 120,\n'
                '  "metadata": {\n'
                '    "web_enabled": true,\n'
                '    "allowed_web_domains": ["openai.com"],\n'
                '    "web_stats": {"filtered_out_count": 1}\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "passed"

    def test_knowledge_governance_failed_when_signature_missing(self, temp_project_dir: Path):
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            (
                "{\n"
                '  "cache_ttl_seconds": 120,\n'
                '  "metadata": {"web_enabled": false}\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "failed"

    def test_knowledge_governance_warning_when_web_without_domains(self, temp_project_dir: Path):
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            (
                "{\n"
                '  "cache_signature": "abc123",\n'
                '  "cache_ttl_seconds": 120,\n'
                '  "metadata": {"web_enabled": true, "allowed_web_domains": []}\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "warning"

    def test_ui_contract_execution_passed_when_contract_tokens_and_runtime_align(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            (
                "{\n"
                '  "ui_contract": {"label": "UI 契约文件", "passed": true, "expected": "frozen", "observed": "frozen"},\n'
                '  "icon_system": {"label": "图标系统", "passed": true, "expected": "lucide-react", "observed": "lucide-react"},\n'
                '  "font_pair": {"label": "字体组合", "passed": true, "expected": "Space Grotesk / Inter", "observed": "Space Grotesk / Inter"},\n'
                '  "component_ecosystem": {"label": "组件生态", "passed": true, "expected": "shadcn/ui + Radix + Tailwind", "observed": "shadcn/ui + Radix + Tailwind"},\n'
                '  "theme_entry": {"label": "主题入口", "passed": true, "expected": "theme provider or tokens import", "observed": "tokens import"},\n'
                '  "navigation_shell": {"label": "导航骨架", "passed": true, "expected": "app shell", "observed": "app shell"},\n'
                '  "component_imports": {"label": "组件导入路径", "passed": true, "expected": "components/ui", "observed": "components/ui"},\n'
                '  "banned_patterns": {"label": "反模式约束", "passed": true, "expected": "no emoji / no chat shell", "observed": "clean"},\n'
                '  "design_tokens": {"label": "Design Token 接入", "passed": true, "expected": "wired", "observed": "wired"},\n'
                '  "token_usage": {"label": "冻结 Token 使用率", "passed": true, "expected": "majority", "observed": "majority"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_theme_entry": true,\n'
                '    "ui_navigation_shell": true,\n'
                '    "ui_component_imports": true,\n'
                '    "ui_banned_patterns": true,\n'
                '    "ui_framework_playbook": true,\n'
                '    "ui_framework_execution": true,\n'
                '    "ui_screen_recipes": true,\n'
                '    "ui_design_context_protocol": true,\n'
                '    "ui_tweak_strategy": true,\n'
                '    "ui_verification_handoff": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "passed"
        assert "library=shadcn/ui + Radix + Tailwind" in check.details

    def test_ui_contract_execution_failed_when_runtime_missing_contract_alignment(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            (
                "{\n"
                '  "ui_contract": {"label": "UI 契约文件", "passed": true, "expected": "frozen", "observed": "frozen"},\n'
                '  "icon_system": {"label": "图标系统", "passed": true, "expected": "lucide-react", "observed": "lucide-react"},\n'
                '  "font_pair": {"label": "字体组合", "passed": true, "expected": "Space Grotesk / Inter", "observed": "Space Grotesk / Inter"},\n'
                '  "component_ecosystem": {"label": "组件生态", "passed": true, "expected": "shadcn/ui + Radix + Tailwind", "observed": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"label": "Design Token 接入", "passed": true, "expected": "wired", "observed": "wired"},\n'
                '  "token_usage": {"label": "冻结 Token 使用率", "passed": true, "expected": "majority", "observed": "majority"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": false,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "frontend runtime 未证明 UI 契约文件" in check.details

    def test_ui_contract_execution_failed_when_contract_missing_emoji_policy(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_banned_patterns": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "emoji_policy" in check.details

    def test_ui_contract_execution_failed_when_claude_design_protocol_missing(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_theme_entry": true,\n'
                '    "ui_navigation_shell": true,\n'
                '    "ui_component_imports": true,\n'
                '    "ui_banned_patterns": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "screen_recipes" in check.details

    def test_ui_contract_execution_failed_when_ui_review_runtime_protocol_mismatches(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_theme_entry": true,\n'
                '    "ui_navigation_shell": true,\n'
                '    "ui_component_imports": true,\n'
                '    "ui_banned_patterns": true,\n'
                '    "ui_screen_recipes": true,\n'
                '    "ui_design_context_protocol": true,\n'
                '    "ui_tweak_strategy": true,\n'
                '    "ui_verification_handoff": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
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

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "UI review 与 frontend runtime 的 Claude-Design 协议证据未闭环" in check.details

    def test_ui_contract_execution_failed_when_ui_review_source_protocol_missing(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_theme_entry": true,\n'
                '    "ui_navigation_shell": true,\n'
                '    "ui_component_imports": true,\n'
                '    "ui_banned_patterns": true,\n'
                '    "ui_screen_recipes": true,\n'
                '    "ui_design_context_protocol": true,\n'
                '    "ui_tweak_strategy": true,\n'
                '    "ui_verification_handoff": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps(
                {
                    "alignment_summary": {
                        "runtime_claude_design_protocol": {
                            "passed": True,
                            "observed": "aligned with frontend-runtime",
                        },
                        "source_claude_design_protocol": {
                            "passed": False,
                            "observed": "design_context_protocol",
                        },
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "UI review 未在源码/预览中看到 Claude-Design 协议落地信号" in check.details

    def test_ui_contract_execution_failed_when_screenshot_visual_judge_fails(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "style_direction": "Editorial workspace",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(
            ":root { --color-primary: #0f172a; }\n", encoding="utf-8"
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_theme_entry": true,\n'
                '    "ui_navigation_shell": true,\n'
                '    "ui_component_imports": true,\n'
                '    "ui_banned_patterns": true,\n'
                '    "ui_screen_recipes": true,\n'
                '    "ui_design_context_protocol": true,\n'
                '    "ui_tweak_strategy": true,\n'
                '    "ui_verification_handoff": true\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
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

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "UI review 截图级视觉验收未通过" in check.details

    def test_ui_contract_execution_failed_when_cross_platform_contract_missing_framework_playbook(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "style_direction": "可信商城",\n'
                '  "typography": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "icon_system": "lucide-react",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + Taro / UniApp + Tailwind(TW 适配)"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "Miniapp Entry", "section_order": ["navigation", "hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["pages.json"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["导航密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["platform proof"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_framework_playbook": false\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "uni-app", "backend": "node"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "uni-app 跨平台框架 playbook" in check.details

    def test_ui_contract_execution_failed_when_cross_platform_runtime_missing_framework_execution(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "style_direction": "可信商城",\n'
                '  "typography": {"heading": "Alibaba PuHuiTi", "body": "PingFang SC"},\n'
                '  "icon_system": "TDesign Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + Taro / UniApp"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}},\n'
                '  "screen_recipes": [{"label": "Miniapp Entry", "section_order": ["navigation", "hero"], "trust_modules": ["案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["pages.json"], "single_source_rule": "single source"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["导航密度"], "persistence_rule": "persist edits"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["platform proof"]},\n'
                '  "framework_playbook": {\n'
                '    "framework": "uni-app",\n'
                '    "implementation_modules": ["自定义导航栏高度"],\n'
                '    "platform_constraints": ["status bar 与安全区"],\n'
                '    "execution_guardrails": ["先冻结 navigationStyle"],\n'
                '    "native_capabilities": ["登录 provider"],\n'
                '    "validation_surfaces": ["微信小程序导航"],\n'
                '    "delivery_evidence": ["三端差异说明"]\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_dir / "design-tokens.css").write_text(":root { --color-primary: #0f172a; }\n", encoding="utf-8")
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            '{"framework_execution":{"label":"框架 Playbook 执行","passed":false,"expected":"uni., #ifdef, provider","observed":"uni."}}',
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": false,\n'
                '  "checks": {\n'
                '    "ui_contract_json": true,\n'
                '    "output_frontend_design_tokens": true,\n'
                '    "ui_contract_alignment": true,\n'
                '    "ui_framework_playbook": true,\n'
                '    "ui_framework_execution": false\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "uni-app", "backend": "node"},
            scenario_override="1-N+1",
        )
        check = checker._check_ui_contract_execution()
        assert check.status.value == "failed"
        assert "uni-app 跨平台框架 playbook" in check.details
