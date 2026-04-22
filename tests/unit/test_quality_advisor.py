"""
质量顾问 (QualityAdvisor) 单元测试

测试主动质量建议引擎的各项检查功能。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from super_dev.review_state import save_host_runtime_validation, save_workflow_state
from super_dev.reviewers.quality_advisor import (
    QualityAdvice,
    QualityAdvisor,
    QualityAdvisorReport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path: Path) -> Path:
    """空项目（无源码、无测试）"""
    return tmp_path


@pytest.fixture()
def minimal_project(tmp_path: Path) -> Path:
    """最小项目：有源码目录，无测试"""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')\n")
    (tmp_path / "README.md").write_text("# My Project\n")
    return tmp_path


@pytest.fixture()
def well_structured_project(tmp_path: Path) -> Path:
    """结构良好的项目：有源码、测试、CI、Docker 等"""
    # 源码
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')\n")
    (src / "utils.py").write_text("def add(a, b): return a + b\n")

    # 测试
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    unit = tests / "unit"
    unit.mkdir()
    (unit / "test_main.py").write_text("def test_main(): pass\n")
    integration = tests / "integration"
    integration.mkdir()
    (integration / "test_api.py").write_text("def test_api(): pass\n")

    # 文档
    (tmp_path / "README.md").write_text("# Project\n## Install\n## Usage\n## Config\n")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")

    # CI/CD
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("name: CI\n")

    # Docker
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
    (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

    # 环境变量
    (tmp_path / ".env").write_text("SECRET=xxx\n")
    (tmp_path / ".env.example").write_text("SECRET=\n")
    (tmp_path / ".gitignore").write_text(".env\nnode_modules/\n")

    return tmp_path


# ---------------------------------------------------------------------------
# QualityAdvice dataclass tests
# ---------------------------------------------------------------------------


class TestQualityAdvice:
    def test_fields(self):
        advice = QualityAdvice(
            category="testing",
            priority="critical",
            title="No tests",
            description="Zero test coverage",
            action="Create tests",
            effort="large",
            impact="high",
            knowledge_ref="knowledge/testing.md",
        )
        assert advice.category == "testing"
        assert advice.priority == "critical"
        assert advice.knowledge_ref == "knowledge/testing.md"

    def test_default_knowledge_ref(self):
        advice = QualityAdvice(
            category="security",
            priority="high",
            title="t",
            description="d",
            action="a",
            effort="small",
            impact="high",
        )
        assert advice.knowledge_ref == ""


# ---------------------------------------------------------------------------
# QualityAdvisorReport tests
# ---------------------------------------------------------------------------


class TestQualityAdvisorReport:
    def _make_report(self, advices: list[QualityAdvice]) -> QualityAdvisorReport:
        return QualityAdvisorReport(
            project_name="test",
            timestamp="2026-03-28 00:00:00 UTC",
            quality_score=70,
            advices=advices,
        )

    def test_critical_advices(self):
        advices = [
            QualityAdvice("t", "critical", "A", "d", "a", "s", "h"),
            QualityAdvice("t", "high", "B", "d", "a", "s", "h"),
            QualityAdvice("t", "critical", "C", "d", "a", "s", "h"),
        ]
        report = self._make_report(advices)
        assert len(report.critical_advices) == 2
        assert {a.title for a in report.critical_advices} == {"A", "C"}

    def test_quick_wins(self):
        advices = [
            QualityAdvice("t", "high", "QW", "d", "a", "small", "high"),
            QualityAdvice("t", "high", "Big", "d", "a", "large", "high"),
            QualityAdvice("t", "low", "Easy", "d", "a", "small", "low"),
        ]
        report = self._make_report(advices)
        assert len(report.quick_wins) == 1
        assert report.quick_wins[0].title == "QW"

    def test_priority_groups(self):
        advices = [
            QualityAdvice("t", "critical", "A", "d", "a", "s", "h"),
            QualityAdvice("t", "high", "B", "d", "a", "s", "h"),
            QualityAdvice("t", "medium", "C", "d", "a", "s", "m"),
            QualityAdvice("t", "low", "D", "d", "a", "s", "l"),
        ]
        report = self._make_report(advices)
        assert len(report.high_priority) == 2  # critical + high
        assert len(report.medium_priority) == 1
        assert len(report.low_priority) == 1

    def test_to_markdown_not_empty(self):
        advices = [
            QualityAdvice("testing", "critical", "No tests", "desc", "act", "small", "high"),
        ]
        report = self._make_report(advices)
        md = report.to_markdown()
        assert "质量顾问报告" in md
        assert "No tests" in md
        assert "关键问题" in md

    def test_to_markdown_empty_advices(self):
        report = self._make_report([])
        md = report.to_markdown()
        assert "质量顾问报告" in md
        assert "建议总数**: 0" in md


# ---------------------------------------------------------------------------
# QualityAdvisor — testing gaps
# ---------------------------------------------------------------------------


class TestQualityAdvisorTestingGaps:
    def test_no_test_dir_gives_critical(self, minimal_project: Path):
        advisor = QualityAdvisor(minimal_project)
        advices = advisor._check_testing_gaps()
        assert any(a.priority == "critical" and "测试目录" in a.title for a in advices)

    def test_with_test_dir_but_no_files(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_testing_gaps()
        titles = [a.title for a in advices]
        assert "缺少测试目录" not in titles

    def test_no_integration_tests(self, tmp_path: Path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("pass\n")
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_testing_gaps()
        assert any("集成测试" in a.title for a in advices)

    def test_well_structured_no_critical(self, well_structured_project: Path):
        advisor = QualityAdvisor(well_structured_project)
        advices = advisor._check_testing_gaps()
        critical = [a for a in advices if a.priority == "critical"]
        assert len(critical) == 0


# ---------------------------------------------------------------------------
# QualityAdvisor — security gaps
# ---------------------------------------------------------------------------


class TestQualityAdvisorSecurityGaps:
    def test_env_not_in_gitignore(self, tmp_path: Path):
        (tmp_path / ".env").write_text("SECRET=abc\n")
        # No .gitignore
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_security_gaps()
        assert any(".env" in a.title and a.priority == "critical" for a in advices)

    def test_env_in_gitignore_no_critical(self, tmp_path: Path):
        (tmp_path / ".env").write_text("SECRET=abc\n")
        (tmp_path / ".gitignore").write_text(".env\n")
        (tmp_path / ".env.example").write_text("SECRET=\n")
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_security_gaps()
        critical_env = [a for a in advices if ".env" in a.title and a.priority == "critical"]
        assert len(critical_env) == 0

    def test_no_env_example(self, tmp_path: Path):
        (tmp_path / ".env").write_text("SECRET=abc\n")
        (tmp_path / ".gitignore").write_text(".env\n")
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_security_gaps()
        assert any(".env.example" in a.title for a in advices)


# ---------------------------------------------------------------------------
# QualityAdvisor — documentation gaps
# ---------------------------------------------------------------------------


class TestQualityAdvisorDocumentationGaps:
    def test_no_readme(self, empty_project: Path):
        advisor = QualityAdvisor(empty_project)
        advices = advisor._check_documentation_gaps()
        assert any("README" in a.title for a in advices)

    def test_incomplete_readme(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Hello\nSome text.\n")
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_documentation_gaps()
        assert any("README 内容不完整" in a.title for a in advices)

    def test_complete_readme_no_issue(self, tmp_path: Path):
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation\n## Usage\n## Configuration\n"
        )
        advisor = QualityAdvisor(tmp_path)
        advices = advisor._check_documentation_gaps()
        readme_advices = [a for a in advices if "README" in a.title]
        assert len(readme_advices) == 0


# ---------------------------------------------------------------------------
# QualityAdvisor — architecture gaps
# ---------------------------------------------------------------------------


class TestQualityAdvisorArchitectureGaps:
    def test_no_ci_gives_high(self, minimal_project: Path):
        advisor = QualityAdvisor(minimal_project)
        advices = advisor._check_architecture_gaps()
        assert any("CI/CD" in a.title and a.priority == "high" for a in advices)

    def test_with_ci_no_ci_advice(self, well_structured_project: Path):
        advisor = QualityAdvisor(well_structured_project)
        advices = advisor._check_architecture_gaps()
        ci_advices = [a for a in advices if "CI/CD" in a.title]
        assert len(ci_advices) == 0


# ---------------------------------------------------------------------------
# QualityAdvisor — full analyze
# ---------------------------------------------------------------------------


class TestQualityAdvisorAnalyze:
    def test_analyze_returns_report(self, minimal_project: Path):
        advisor = QualityAdvisor(minimal_project)
        report = advisor.analyze()
        assert isinstance(report, QualityAdvisorReport)
        assert report.project_name == minimal_project.name
        assert len(report.advices) > 0

    def test_analyze_with_quality_result(self, minimal_project: Path):
        class FakeResult:
            total_score = 42

        advisor = QualityAdvisor(minimal_project)
        report = advisor.analyze(quality_result=FakeResult())
        assert report.quality_score == 42

    def test_advices_sorted_by_priority(self, minimal_project: Path):
        advisor = QualityAdvisor(minimal_project)
        report = advisor.analyze()
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priorities = [priority_order.get(a.priority, 99) for a in report.advices]
        assert priorities == sorted(priorities)

    def test_well_structured_fewer_advices(self, well_structured_project: Path):
        advisor = QualityAdvisor(well_structured_project)
        report = advisor.analyze()
        critical = [advice for advice in report.critical_advices if advice.category != "governance"]
        assert len(critical) == 0

    def test_report_markdown_generation(self, minimal_project: Path):
        advisor = QualityAdvisor(minimal_project)
        report = advisor.analyze()
        md = report.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 100

    def test_analyze_emits_governance_advice_for_layered_runtime_gap(self, tmp_path: Path):
        save_workflow_state(
            tmp_path,
            {
                "status": "missing_frontend",
                "workflow_mode": "continue",
                "current_step_label": "先做前端与运行验证",
                "recommended_command": "继续当前流程，进入前端实现与运行验证",
            },
        )
        save_host_runtime_validation(
            tmp_path,
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

        advisor = QualityAdvisor(tmp_path)
        report = advisor.analyze()

        governance_advices = [a for a in report.advices if a.category == "governance"]
        assert governance_advices
        advice = governance_advices[0]
        assert advice.priority == "critical"
        assert "codex-cli" in advice.description
        assert "宿主真人验收记录" in advice.action
        assert advice.knowledge_ref.endswith("host-runtime-validation.json")

    def test_analyze_emits_governance_advice_for_compliance_artifact_gap(self, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
            encoding="utf-8",
        )

        advisor = QualityAdvisor(tmp_path)
        report = advisor.analyze()

        governance_advices = [a for a in report.advices if a.title == "合规链证据状态未闭环"]
        assert governance_advices
        advice = governance_advices[0]
        assert advice.priority == "critical"
        assert "spec=missing" in advice.description
        assert "重新生成 spec / architecture / uiux compliance artifacts" in advice.action
