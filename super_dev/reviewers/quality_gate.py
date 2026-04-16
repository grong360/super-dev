"""
质量门禁检查器 - 确保交付物达到质量标准

开发：Excellent（11964948@qq.com）
功能：多维度质量评分和门禁检查
作用：按场景阈值（或自定义阈值）评估是否通过质量门禁
创建时间：2025-12-30
"""

import json
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict

import yaml  # type: ignore[import-untyped]
from defusedxml import ElementTree

from ..config import ConfigManager
from ..frameworks import framework_playbook_complete, is_cross_platform_frontend
from .redteam import RedTeamReport
from .validation_rules import ValidationRuleEngine

try:
    from .review_agents import build_parallel_review_prompt

    REVIEW_AGENTS_AVAILABLE = True
except ImportError:
    REVIEW_AGENTS_AVAILABLE = False


class CheckStatus(Enum):
    """检查状态"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class QualityCheck:
    """质量检查项"""

    name: str
    category: str  # documentation, security, performance, testing, code_quality
    description: str
    status: CheckStatus
    score: int  # 0-100
    weight: float = 1.0  # 权重，用于计算加权总分
    details: str = ""


@dataclass
class QualityGateResult:
    """质量门禁结果"""

    passed: bool
    total_score: int
    weighted_score: float
    checks: list[QualityCheck] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    scenario: str = "1-N+1"  # 场景类型: "0-1" 或 "1-N+1"

    @property
    def passed_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.PASSED]

    @property
    def failed_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.FAILED]

    @property
    def warning_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.WARNING]

    @property
    def expert_summary(self) -> dict[str, dict]:
        """按专家角色汇总检查结果"""
        try:
            rule_to_expert = {
                "documentation": "PM",
                "security": "SECURITY",
                "performance": "DEVOPS",
                "testing": "QA",
                "code_quality": "CODE",
                "validation_rules": "QA",
                "accessibility": "CODE",
                "ui_quality": "UI",
                "schema_drift": "CODE",
                "spec_compliance": "ARCHITECT",
                "architecture_drift": "ARCHITECT",
                "uiux_compliance": "UI",
            }

            expert_results: dict[str, dict] = {}
            for check in self.checks:
                expert = rule_to_expert.get(check.category, "CODE")
                if expert not in expert_results:
                    expert_results[expert] = {"passed": 0, "failed": 0, "score": 0, "checks": []}
                expert_results[expert]["checks"].append(check)
                if check.status == CheckStatus.PASSED:
                    expert_results[expert]["passed"] += 1
                else:
                    expert_results[expert]["failed"] += 1

            # 计算每个专家的平均分
            for expert, data in expert_results.items():
                total = data["passed"] + data["failed"]
                if total > 0:
                    data["score"] = int(sum(c.score for c in data["checks"]) / total)

            return expert_results
        except Exception:
            return {}

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        status_icon = "通过" if self.passed else "未通过"
        status_color = "green" if self.passed else "red"

        lines = [
            "# 质量门禁报告",
            "",
            f"**场景**: {self.scenario} ({'0-1 新建项目' if self.scenario == '0-1' else '1-N+1 增量开发'})",
            f"**状态**: <span style='color:{status_color}'>{status_icon}</span>",
            f"**总分**: {self.total_score}/100",
            f"**加权分**: {self.weighted_score:.1f}/100",
            "",
            "---",
            "",
            "## 检查结果摘要",
            "",
            f"- 通过: {len(self.passed_checks)} 项",
            f"- 警告: {len(self.warning_checks)} 项",
            f"- 失败: {len(self.failed_checks)} 项",
            "",
        ]

        if self.critical_failures:
            lines.extend(
                [
                    "## 关键失败项",
                    "",
                ]
            )
            for failure in self.critical_failures:
                lines.append(f"- {failure}")
            lines.append("")

        # 按类别分组展示
        categories: dict[str, list[QualityCheck]] = {}
        for check in self.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        lines.extend(
            [
                "## 详细检查结果",
                "",
            ]
        )

        for category, checks in categories.items():
            lines.extend(
                [
                    f"### {category}",
                    "",
                    "| 检查项 | 状态 | 得分 | 说明 |",
                    "|:---|:---:|:---:|:---|",
                ]
            )

            for check in checks:
                status_icon = (
                    "✓"
                    if check.status == CheckStatus.PASSED
                    else "⚠" if check.status == CheckStatus.WARNING else "✗"
                )
                lines.append(
                    f"| {check.name} | {status_icon} | {check.score}/100 | {check.description} |"
                )

            lines.append("")

        # 验证规则专属区域
        rule_checks = [c for c in self.checks if c.category == "validation_rules"]
        if rule_checks:
            lines.extend(
                [
                    "## 可编程验证规则结果",
                    "",
                    f"共触发 {len(rule_checks)} 条规则违反：",
                    "",
                    "| 规则 | 状态 | 严重程度 | 描述 | 修复建议 |",
                    "|:---|:---:|:---:|:---|:---|",
                ]
            )
            for check in rule_checks:
                status_icon = "✗" if check.status == CheckStatus.FAILED else "⚠"
                severity = "critical" if check.weight >= 1.5 else "non-critical"
                fix = check.details if check.details else "-"
                lines.append(
                    f"| {check.name} | {status_icon} | {severity} | {check.description} | {fix} |"
                )
            lines.append("")

        # 专家视角总结
        try:
            expert_data = self.expert_summary
            if expert_data:
                lines.extend(
                    [
                        "## 专家视角总结",
                        "",
                        "| 专家 | 通过 | 失败 | 平均分 | 评价 |",
                        "|------|------|------|--------|------|",
                    ]
                )

                for expert, data in expert_data.items():
                    rating = (
                        "优秀"
                        if data["score"] >= 80
                        else "需改进" if data["score"] >= 60 else "不合格"
                    )
                    lines.append(
                        f"| {expert} | {data['passed']} | {data['failed']} | {data['score']} | {rating} |"
                    )

                lines.append("")
        except Exception:
            pass

        # 改进建议
        if self.recommendations:
            lines.extend(
                [
                    "## 改进建议",
                    "",
                ]
            )
            for idx, rec in enumerate(self.recommendations, 1):
                lines.append(f"{idx}. {rec}")
            lines.append("")

        # 质量顾问建议
        try:
            from .quality_advisor import QualityAdvisor

            advisor = QualityAdvisor(Path.cwd())
            advisor_report = advisor.analyze(self)
            if advisor_report.advices:
                lines.extend(
                    [
                        "## 质量顾问建议",
                        "",
                        f"共 {len(advisor_report.advices)} 条建议"
                        f"（关键 {len(advisor_report.critical_advices)}、"
                        f"Quick Win {len(advisor_report.quick_wins)}）",
                        "",
                    ]
                )
                if advisor_report.quick_wins:
                    lines.append("### Quick Wins（高收益低成本）")
                    lines.append("")
                    for advice in advisor_report.quick_wins:
                        lines.append(
                            f"- **[{advice.priority.upper()}]** " f"{advice.title}: {advice.action}"
                        )
                    lines.append("")
                if advisor_report.critical_advices:
                    lines.append("### 关键问题（必须修复）")
                    lines.append("")
                    for advice in advisor_report.critical_advices:
                        lines.append(
                            f"- **{advice.title}** ({advice.category}): "
                            f"{advice.description} → {advice.action}"
                        )
                    lines.append("")
                remaining = [
                    a
                    for a in advisor_report.advices
                    if a.priority not in {"critical"}
                    and not (a.impact == "high" and a.effort == "small")
                ]
                if remaining:
                    lines.append("### 其他建议")
                    lines.append("")
                    for advice in remaining:
                        lines.append(
                            f"- [{advice.priority.upper()}] **{advice.title}** "
                            f"({advice.category}): {advice.description} "
                            f"[工作量: {advice.effort}, 影响: {advice.impact}]"
                        )
                    lines.append("")
        except Exception:
            pass

        # 下一步行动
        lines.extend(
            [
                "---",
                "",
                "## 下一步行动",
                "",
            ]
        )

        if self.passed:
            lines.extend(
                [
                    "[通过] 质量门禁已通过，可以继续下一步：",
                    "",
                    "1. 开始编码实现",
                    "2. 设置 CI/CD 流水线",
                    "3. 部署到测试环境",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "[未通过] 质量门禁未通过，请完成以下操作后重新检查：",
                    "",
                ]
            )

            failed_items = [f"- {c.description}" for c in self.failed_checks]
            lines.extend(failed_items)
            lines.extend(
                [
                    "",
                    "修复后运行: `super-dev quality --type all`",
                    "",
                ]
            )

        return "\n".join(lines)


class HostProfileMetrics(TypedDict):
    label: str
    overall_score: float
    ready_hosts: int
    total_hosts: int
    bounded_score: int


class QualityGateChecker:
    """质量门禁检查器"""

    # 质量门禁阈值
    PASS_THRESHOLD = 80
    WARNING_THRESHOLD = 60
    # 0-1 场景与增量场景统一使用 80+ 标准
    PASS_THRESHOLD_ZERO_TO_ONE = 80
    HOST_COMPAT_MIN_SCORE = 80
    HOST_COMPAT_MIN_READY_HOSTS = 1

    # 检查项配置
    CHECKS_CONFIG = {
        "documentation": {
            "weight": 1.0,
            "required": True,
        },
        "security": {
            "weight": 1.5,  # 安全更重要
            "required": True,
        },
        "performance": {
            "weight": 1.2,
            "required": True,
        },
        "testing": {
            "weight": 1.3,
            "required": True,
        },
        "code_quality": {
            "weight": 1.0,
            "required": False,
        },
        "accessibility": {
            "weight": 0.8,
            "required": False,
        },
        "ui_quality": {
            "weight": 1.2,
            "required": True,
        },
        "schema_drift": {
            "weight": 0.8,
            "required": False,
        },
        "spec_compliance": {
            "weight": 2.0,
            "required": True,
        },
        "architecture_drift": {
            "weight": 2.5,
            "required": True,
        },
        "uiux_compliance": {
            "weight": 2.0,
            "required": False,
        },
    }

    def __init__(
        self,
        project_dir: Path,
        name: str,
        tech_stack: dict,
        scenario_override: str | None = None,
        threshold_override: int | None = None,
        host_compatibility_min_score_override: int | None = None,
        host_compatibility_min_ready_hosts_override: int | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.tech_stack = tech_stack
        self.latest_ui_review_report = None
        self.threshold_override = threshold_override
        config = ConfigManager(self.project_dir).load()
        self.host_profile_targets = [
            item.strip()
            for item in getattr(config, "host_profile_targets", [])
            if isinstance(item, str) and item.strip()
        ]
        self.host_profile_enforce_selected = bool(
            getattr(config, "host_profile_enforce_selected", False)
        )
        self.host_compatibility_min_score = self._coerce_host_compat_score(
            host_compatibility_min_score_override
            if host_compatibility_min_score_override is not None
            else config.host_compatibility_min_score
        )
        self.host_compatibility_min_ready_hosts = self._coerce_host_compat_ready_hosts(
            host_compatibility_min_ready_hosts_override
            if host_compatibility_min_ready_hosts_override is not None
            else config.host_compatibility_min_ready_hosts
        )
        if scenario_override in {"0-1", "1-N+1"}:
            self.is_zero_to_one = scenario_override == "0-1"
        else:
            self.is_zero_to_one = self._detect_zero_to_one_scenario()

        # 可编程验证规则引擎（加载失败不影响主流程）
        self._rule_engine: ValidationRuleEngine | None = None
        try:
            self._rule_engine = ValidationRuleEngine(Path.cwd())
        except Exception:
            pass

    def _build_review_agent_prompts(self, context: dict) -> dict[str, str] | None:
        """Build parallel review agent prompts for the quality gate."""
        if not REVIEW_AGENTS_AVAILABLE:
            return None
        try:
            return build_parallel_review_prompt(
                change_description=context.get("description", ""),
                files_changed=context.get("files_changed", []),
            )
        except Exception:
            return None

    def _coerce_host_compat_score(self, value: object) -> int:
        score = self._coerce_int(value, default=self.HOST_COMPAT_MIN_SCORE)
        return max(0, min(100, score))

    def _coerce_host_compat_ready_hosts(self, value: object) -> int:
        ready_hosts = self._coerce_int(value, default=self.HOST_COMPAT_MIN_READY_HOSTS)
        return max(0, ready_hosts)

    def _coerce_float(self, value: object, default: float) -> float:
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return float(text)
            except ValueError:
                return default
        return default

    def _coerce_int(self, value: object, default: int) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return int(text)
            except ValueError:
                return default
        return default

    def _detect_zero_to_one_scenario(self) -> bool:
        """
        检测是否为 0-1 场景（空项目/新建项目）

        0-1 场景特征：
        - 没有源代码目录（src/, lib/, app/, server/, client/ 等）
        - 没有配置文件（package.json, requirements.txt, go.mod 等）
        - 只有 output/ 目录（刚生成的文档）

        Returns:
            bool: True 表示 0-1 场景，False 表示 1-N+1 场景
        """
        # 检查常见的源代码目录
        source_dirs = [
            "src",
            "lib",
            "app",
            "server",
            "client",
            "backend",
            "frontend",
            "api",
            "handlers",
            "models",
            "views",
            "controllers",
            "services",
        ]

        has_source_code = any((self.project_dir / d).exists() for d in source_dirs)

        # 检查是否有项目配置文件（表明这不是空项目）
        config_files = [
            "package.json",
            "requirements.txt",
            "go.mod",
            "Cargo.toml",
            "pom.xml",
            "build.gradle",
        ]

        has_project_config = any((self.project_dir / f).exists() for f in config_files)

        # 如果有源代码或有项目配置，说明不是 0-1 场景
        return not (has_source_code or has_project_config)

    def check(self, redteam_report: Optional["RedTeamReport"] = None) -> QualityGateResult:
        """执行质量门禁检查"""
        checks: list[QualityCheck] = []

        # 1. 文档质量检查
        checks.extend(self._check_documentation())

        # 2. 安全检查 (基于红队报告)
        checks.extend(self._check_security(redteam_report))

        # 3. 性能检查 (基于红队报告)
        checks.extend(self._check_performance(redteam_report))

        # 4. 测试检查
        checks.extend(self._check_testing())

        # 5. 代码质量检查
        checks.extend(self._check_code_quality())

        # 5.5 无障碍性检查
        checks.extend(self._check_accessibility())

        # 5.6 性能预算检查
        checks.extend(self._check_performance_budget())

        # 5.7 UI 契约执行检查
        checks.append(self._check_ui_contract_execution())

        # 6. UI 审查
        checks.append(self._check_ui_review())

        # 7. 执行可编程验证规则
        if self._rule_engine:
            try:
                context = {
                    "project_dir": str(self.project_dir),
                    "name": self.name,
                    "tech_stack": self.tech_stack,
                    "scenario": "0-1" if self.is_zero_to_one else "1-N+1",
                }
                rule_report = self._rule_engine.validate("quality", context)
                for result in rule_report.results:
                    if not result.passed:
                        checks.append(
                            QualityCheck(
                                name=f"Rule: {result.rule_id}",
                                category="validation_rules",
                                description=result.message,
                                status=(
                                    CheckStatus.FAILED
                                    if result.severity == "critical"
                                    else CheckStatus.WARNING
                                ),
                                score=0,
                                weight=1.5 if result.severity == "critical" else 1.0,
                                details=result.fix_suggestion,
                            )
                        )
            except Exception:
                pass

        # 8. 加载专家特定的验证规则（如果专家工具箱可用）
        try:
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            for expert_id, toolkit in toolkits.items():
                if hasattr(toolkit, "rules") and hasattr(toolkit.rules, "validation_rule_ids"):
                    for rule_id in toolkit.rules.validation_rule_ids:
                        # 检查该规则是否已在 rule_engine 中注册
                        if self._rule_engine:
                            matching = [r for r in self._rule_engine.rules if r.id == rule_id]
                            if not matching:
                                checks.append(
                                    QualityCheck(
                                        name=f"Expert Rule Gap: {rule_id}",
                                        category="validation_rules",
                                        description=(
                                            f"专家 {expert_id} 声明了规则 {rule_id}，"
                                            f"但该规则不在验证引擎中"
                                        ),
                                        status=CheckStatus.WARNING,
                                        score=50,
                                        weight=0.5,
                                    )
                                )
        except Exception:
            pass

        # 9. 收集外部审查结果 (CodeRabbit / Qodo / GitHub PR / Custom)
        try:
            from .external_reviews import ExternalReviewCollector

            collector = ExternalReviewCollector(self.project_dir)
            external = collector.collect_all()
            for review in external:
                checks.append(
                    QualityCheck(
                        name=f"External Review: {review.source}",
                        category="external_review",
                        description=review.summary,
                        status=(CheckStatus.PASSED if review.passed else CheckStatus.WARNING),
                        score=review.score,
                    )
                )
        except Exception:
            pass

        # 10. 交叉审查协议——多专家规则引擎验证
        try:
            from ..experts.review_protocol import CrossReviewEngine
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            review_engine = CrossReviewEngine(toolkits)
            output_dir = self.project_dir / "output"

            # 对 UIUX 文档执行交叉审查
            uiux_path = output_dir / f"{self.name}-uiux.md"
            if uiux_path.exists():
                uiux_content = uiux_path.read_text(encoding="utf-8", errors="replace")
                cross_report = review_engine.validate_artifact(uiux_content, "docs")
                for finding in cross_report.findings:
                    if not finding.passed:
                        checks.append(
                            QualityCheck(
                                name=f"Cross-Review: {finding.expert_id} → {finding.dimension}",
                                category="cross_review",
                                description=finding.detail,
                                status=CheckStatus.WARNING,
                                score=60,
                                weight=0.8,
                            )
                        )

            # 对架构文档执行交叉审查
            arch_path = output_dir / f"{self.name}-architecture.md"
            if arch_path.exists():
                arch_content = arch_path.read_text(encoding="utf-8", errors="replace")
                cross_report = review_engine.validate_artifact(arch_content, "docs")
                for finding in cross_report.findings:
                    if not finding.passed:
                        checks.append(
                            QualityCheck(
                                name=f"Cross-Review: {finding.expert_id} → {finding.dimension}",
                                category="cross_review",
                                description=finding.detail,
                                status=CheckStatus.WARNING,
                                score=60,
                                weight=0.8,
                            )
                        )
        except Exception:
            pass

        # 11. 知识推送引擎约束检查
        try:
            from ..orchestrator.knowledge_pusher import KnowledgePusher

            knowledge_dir = self.project_dir / "knowledge"
            if knowledge_dir.is_dir():
                pusher = KnowledgePusher(
                    knowledge_dir=knowledge_dir,
                    tech_stack=self.tech_stack or {},
                )
                kb_constraints, kb_antipatterns = pusher.get_quality_constraints()
                if kb_constraints:
                    checks.append(
                        QualityCheck(
                            name="Knowledge Constraints",
                            category="knowledge_base",
                            description=(
                                f"知识库推送了 {len(kb_constraints)} 条硬约束 "
                                f"和 {len(kb_antipatterns)} 条反模式。"
                                f"请确保已遵守所有约束。"
                            ),
                            status=CheckStatus.PASSED,
                            score=80,
                            weight=0.8,
                            details="; ".join(kb_constraints[:5]),
                        )
                    )
                if kb_antipatterns:
                    checks.append(
                        QualityCheck(
                            name="Knowledge Anti-patterns",
                            category="knowledge_base",
                            description=(
                                f"知识库包含 {len(kb_antipatterns)} 条反模式警告，"
                                f"需确认项目未触犯。"
                            ),
                            status=CheckStatus.WARNING,
                            score=70,
                            weight=0.6,
                            details="; ".join(kb_antipatterns[:5]),
                        )
                    )
        except Exception:
            pass

        # 12. Spec compliance checks (only if compliance reports already exist)
        try:
            output_dir = self.project_dir / "output"
            spec_compliance_path = output_dir / "spec-compliance.json"
            if spec_compliance_path.exists():
                compliance_data = json.loads(spec_compliance_path.read_text(encoding="utf-8"))
                score = compliance_data.get("score", 0)
                coverage = compliance_data.get("coverage_percent", 0)
                total_reqs = compliance_data.get("total_requirements", 0)
                if total_reqs > 0:
                    status = CheckStatus.PASSED if score >= 80 else (
                        CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED
                    )
                    checks.append(
                        QualityCheck(
                            name="Spec Compliance (Requirement Traceability)",
                            category="spec_compliance",
                            description=f"Coverage: {coverage}% ({total_reqs} requirements)",
                            status=status,
                            score=score,
                            weight=2.0,
                        )
                    )
        except Exception:
            pass

        try:
            output_dir = self.project_dir / "output"
            drift_path = output_dir / "architecture-drift.json"
            if drift_path.exists():
                drift_data = json.loads(drift_path.read_text(encoding="utf-8"))
                score = drift_data.get("score", 0)
                total_drifts = drift_data.get("total_drifts", 0)
                critical_count = sum(
                    1 for d in drift_data.get("drifts", []) if d.get("severity") == "critical"
                )
                status = CheckStatus.PASSED if score >= 80 else (
                    CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED
                )
                checks.append(
                    QualityCheck(
                        name="Architecture Drift Detection",
                        category="architecture_drift",
                        description=f"Drifts: {total_drifts} (Critical: {critical_count})",
                        status=status,
                        score=score,
                        weight=2.5,
                    )
                )
        except Exception:
            pass

        try:
            output_dir = self.project_dir / "output"
            uiux_path = output_dir / "uiux-compliance.json"
            if uiux_path.exists():
                uiux_data = json.loads(uiux_path.read_text(encoding="utf-8"))
                score = uiux_data.get("score", 0)
                violations = uiux_data.get("total_violations", 0)
                files_scanned = uiux_data.get("files_scanned", 0)
                if files_scanned > 0:
                    status = CheckStatus.PASSED if score >= 80 else (
                        CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED
                    )
                    checks.append(
                        QualityCheck(
                            name="UIUX Compliance (Icon/Token/Typography)",
                            category="uiux_compliance",
                            description=f"Violations: {violations} across {files_scanned} files",
                            status=status,
                            score=score,
                            weight=2.0,
                        )
                    )
        except Exception:
            pass

        # 计算总分和加权分
        total_score = self._calculate_total_score(checks)
        weighted_score = self._calculate_weighted_score(checks)

        # 根据场景选择阈值
        threshold = (
            self.threshold_override
            if self.threshold_override is not None
            else (self.PASS_THRESHOLD_ZERO_TO_ONE if self.is_zero_to_one else self.PASS_THRESHOLD)
        )

        # 收集关键失败项
        critical_failures = []
        for check in checks:
            config = self.CHECKS_CONFIG.get(check.category, {})
            if config.get("required", False) and check.status == CheckStatus.FAILED:
                critical_failures.append(f"[{check.category}] {check.description}")

        # 检查是否通过：必须达到阈值，且必检项不能失败
        passed = total_score >= threshold and not critical_failures

        # Webhook notification on quality gate failure
        if not passed:
            try:
                from ..webhooks import send_webhook

                send_webhook(
                    "quality_fail",
                    {
                        "score": total_score,
                        "threshold": threshold,
                        "critical_failures": critical_failures,
                        "scenario": "0-1" if self.is_zero_to_one else "1-N+1",
                        "project": self.name,
                    },
                )
            except Exception:
                pass

        # 生成改进建议
        recommendations = self._generate_recommendations(checks)

        # 确定场景类型
        scenario = "0-1" if self.is_zero_to_one else "1-N+1"

        return QualityGateResult(
            passed=passed,
            total_score=total_score,
            weighted_score=weighted_score,
            checks=checks,
            critical_failures=critical_failures,
            recommendations=recommendations,
            scenario=scenario,
        )

    # ------------------------------------------------------------------
    # 文档内容深度检查（防止空壳文档自动满分）
    # ------------------------------------------------------------------

    # 各文档类型的最低非空行数
    _DOC_MIN_LINES: dict[str, int] = {"prd": 100, "architecture": 80, "uiux": 80}
    # 各文档类型的最低二级标题数
    _DOC_MIN_SECTIONS: dict[str, int] = {"prd": 5, "architecture": 4, "uiux": 4}

    def _check_document_depth(self, content: str, doc_type: str) -> tuple[int, list[str]]:
        """检查文档内容深度，而非仅检查关键词存在。

        Returns:
            (扣分后的得分 0-100, 问题列表)
        """
        issues: list[str] = []
        score = 100

        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # 1. 最小行数要求
        min_lines = self._DOC_MIN_LINES.get(doc_type, 50)
        if len(non_empty_lines) < min_lines:
            score -= 30
            issues.append(
                f"{doc_type} 文档内容过短 ({len(non_empty_lines)} 行，最低要求 {min_lines} 行)"
            )

        # 2. 章节数量要求（## 标题）
        h2_count = sum(1 for line in lines if line.startswith("## "))
        min_sections = self._DOC_MIN_SECTIONS.get(doc_type, 3)
        if h2_count < min_sections:
            score -= 20
            issues.append(
                f"{doc_type} 文档章节不足 ({h2_count} 个二级标题，最低要求 {min_sections} 个)"
            )

        # 3. 架构文档必须包含代码/配置示例
        if doc_type == "architecture":
            code_blocks = content.count("```")
            if code_blocks < 2:
                score -= 15
                issues.append("架构文档缺少代码/配置示例")

        # 4. PRD 必须包含验收标准
        if doc_type == "prd":
            has_acceptance_detail = (
                "Given" in content
                or "When" in content
                or "验收标准" in content
                or "acceptance criteria" in content.lower()
            )
            if not has_acceptance_detail:
                score -= 15
                issues.append("PRD 缺少验收标准（Given-When-Then 或明确的验收条件）")

        # 5. UIUX 必须包含 Design Token 定义
        if doc_type == "uiux":
            token_keywords = ["color", "font", "spacing", "token", "颜色", "字体", "间距"]
            token_hits = sum(1 for kw in token_keywords if kw in content.lower())
            if token_hits < 3:
                score -= 20
                issues.append("UIUX 文档缺少设计 Token 定义（颜色/字体/间距）")

            # 反模式规则
            has_antipattern_rules = (
                "emoji" in content.lower()
                or "渐变" in content
                or "anti-pattern" in content.lower()
                or "反模式" in content
            )
            if not has_antipattern_rules:
                score -= 10
                issues.append("UIUX 文档缺少 UI 反模式红线规则")

        return max(score, 0), issues

    def _check_documentation(self) -> list[QualityCheck]:
        """检查文档质量"""
        checks = []

        # 0-1 场景下文档是唯一可检查的产物，权重加倍
        doc_weight = self.CHECKS_CONFIG["documentation"]["weight"]
        if self.is_zero_to_one:
            doc_weight *= 2.0

        # 检查 PRD 是否存在
        prd_path = self.project_dir / "output" / f"{self.name}-prd.md"
        if prd_path.exists():
            content = prd_path.read_text(encoding="utf-8", errors="ignore")
            # 关键词存在性（基础分）
            has_vision = "产品愿景" in content or "vision" in content.lower()
            has_features = "功能需求" in content or "features" in content.lower()
            has_acceptance = "验收标准" in content or "acceptance" in content.lower()

            keyword_score = 100 if has_vision and has_features and has_acceptance else 70

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "prd")

            # 综合评分：关键词 40% + 深度 60%
            score = int(keyword_score * 0.4 + depth_score * 0.6)
            detail_parts = []
            if has_vision and has_features and has_acceptance:
                detail_parts.append("包含产品愿景、功能需求和验收标准")
            else:
                detail_parts.append("缺少关键章节（产品愿景/功能需求/验收标准）")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if score >= 80
                else CheckStatus.WARNING if score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="PRD 文档",
                    category="documentation",
                    description="产品需求文档完整性",
                    status=status,
                    score=score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="PRD 文档",
                    category="documentation",
                    description="产品需求文档存在性",
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details="PRD 文档不存在",
                )
            )

        # 检查架构文档是否存在
        arch_path = self.project_dir / "output" / f"{self.name}-architecture.md"
        if arch_path.exists():
            content = arch_path.read_text(encoding="utf-8", errors="ignore")
            has_tech_stack = "技术栈" in content or "tech stack" in content.lower()
            has_database = "数据库" in content or "database" in content.lower()
            has_api = "API" in content

            keyword_score = 100 if has_tech_stack and has_database and has_api else 70

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "architecture")

            # 综合评分：关键词 40% + 深度 60%
            score = int(keyword_score * 0.4 + depth_score * 0.6)
            detail_parts = []
            if has_tech_stack and has_database and has_api:
                detail_parts.append("包含技术栈、数据库设计和 API 设计")
            else:
                detail_parts.append("缺少关键章节（技术栈/数据库/API）")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if score >= 80
                else CheckStatus.WARNING if score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="架构文档",
                    category="documentation",
                    description="架构设计文档完整性",
                    status=status,
                    score=score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="架构文档",
                    category="documentation",
                    description="架构设计文档存在性",
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details="架构文档不存在",
                )
            )

        # 检查 UI/UX 文档是否存在并评估深度
        uiux_path = self.project_dir / "output" / f"{self.name}-uiux.md"
        if uiux_path.exists():
            content = uiux_path.read_text(encoding="utf-8", errors="ignore")

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "uiux")

            detail_parts = []
            if depth_score >= 80:
                detail_parts.append("UI/UX 文档内容充实")
            else:
                detail_parts.append("UI/UX 文档内容深度不足")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if depth_score >= 80
                else CheckStatus.WARNING if depth_score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="UI/UX 文档",
                    category="documentation",
                    description="UI/UX 设计文档完整性",
                    status=status,
                    score=depth_score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="UI/UX 文档",
                    category="documentation",
                    description="UI/UX 设计文档存在性",
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details="UI/UX 文档不存在（必需）",
                )
            )

        checks.append(
            self._check_document_consistency(
                prd_path=prd_path, arch_path=arch_path, uiux_path=uiux_path
            )
        )

        return checks

    def _check_document_consistency(
        self, *, prd_path: Path, arch_path: Path, uiux_path: Path
    ) -> QualityCheck:
        if not (prd_path.exists() and arch_path.exists() and uiux_path.exists()):
            return QualityCheck(
                name="三文档一致性",
                category="documentation",
                description="PRD/Architecture/UIUX 决策与证据闭环",
                status=CheckStatus.WARNING,
                score=60,
                weight=self.CHECKS_CONFIG["documentation"]["weight"],
                details="三文档未全部存在，无法进行一致性检查",
            )

        prd_content = prd_path.read_text(encoding="utf-8", errors="ignore")
        arch_content = arch_path.read_text(encoding="utf-8", errors="ignore")
        uiux_content = uiux_path.read_text(encoding="utf-8", errors="ignore")
        requirements = [
            ("PRD 证据章节", "联网研究证据与方案对比" in prd_content),
            ("PRD 决策账本", "关键决策账本" in prd_content),
            ("PRD 用户统一协议", "用户到专业交付统一协议" in prd_content),
            ("架构证据链", "架构选型取舍与证据链" in arch_content),
            ("架构决策账本", "架构决策账本" in arch_content),
            ("架构全端流水线", "Agent 执行流水线（全端）" in arch_content),
            ("UI 多端策略", "多端适配与平台化设计策略" in uiux_content),
            ("UI 质量门禁", "商业级设计质量门禁" in uiux_content),
            (
                "UI 五端覆盖",
                all(term in uiux_content for term in ("WEB", "H5", "微信小程序", "APP", "桌面端")),
            ),
            (
                "UI 风格决策冻结",
                all(
                    term in uiux_content
                    for term in ("主视觉气质", "字体组合", "配色逻辑", "图标系统")
                ),
            ),
            (
                "UI 备选与取舍",
                ("备选实现路径" in uiux_content or "可选备选方案" in uiux_content)
                and ("明确不默认采用" in uiux_content or "明确不建议默认采用" in uiux_content),
            ),
            (
                "UI Token 冻结输出",
                "Design Token 冻结输出" in uiux_content or "Token 冻结输出" in uiux_content,
            ),
            (
                "UI 双方案约束",
                "2 个视觉方向候选" in uiux_content or "主方案 + 备选方案" in uiux_content,
            ),
        ]
        passed_count = sum(1 for _, ok in requirements if ok)
        total = len(requirements)
        missing = [name for name, ok in requirements if not ok]
        score = int((passed_count / total) * 100) if total else 100
        if "UI 五端覆盖" in missing:
            status = CheckStatus.FAILED
            score = min(score, 59)
        elif score >= 85:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED
        detail = f"命中 {passed_count}/{total}"
        if missing:
            detail += f"，缺失: {', '.join(missing)}"
        return QualityCheck(
            name="三文档一致性",
            category="documentation",
            description="PRD/Architecture/UIUX 决策与证据闭环",
            status=status,
            score=score,
            weight=self.CHECKS_CONFIG["documentation"]["weight"],
            details=detail,
        )

    def _check_accessibility(self) -> list[QualityCheck]:
        """检查前端无障碍性（A11y / WCAG 2.1）"""
        checks: list[QualityCheck] = []

        # 扫描前端源文件
        source_dirs = ["frontend", "src", "app", "client", "pages", "components"]
        extensions = {".html", ".tsx", ".jsx", ".vue", ".svelte"}
        skip_dirs = {"node_modules", ".git", "dist", "build", "__pycache__", ".next", ".nuxt"}

        files_scanned = 0
        issues: dict[str, int] = {
            "missing_alt": 0,
            "missing_label": 0,
            "click_no_keyboard": 0,
            "div_click_handler": 0,
        }
        has_landmarks = False

        for src_dir_name in source_dirs:
            src_dir = self.project_dir / src_dir_name
            if not src_dir.exists():
                continue
            for file_path in src_dir.rglob("*"):
                if file_path.suffix not in extensions:
                    continue
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue
                files_scanned += 1
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                # 检查图片是否缺少 alt 属性
                img_tags = re.findall(r"<img\b[^>]*>", content, re.IGNORECASE)
                for tag in img_tags:
                    if "alt=" not in tag.lower() and "alt =" not in tag.lower():
                        issues["missing_alt"] += 1

                # 检查输入框是否缺少 label 关联
                input_tags = re.findall(r"<input\b[^>]*>", content, re.IGNORECASE)
                for tag in input_tags:
                    tag_lower = tag.lower()
                    if (
                        "aria-label" not in tag_lower
                        and "aria-labelledby" not in tag_lower
                        and "id=" not in tag_lower
                    ):
                        issues["missing_label"] += 1

                # 检查 onClick 是否缺少键盘事件处理
                onclick_count = len(re.findall(r"onClick\s*[={]", content))
                keyboard_count = len(
                    re.findall(
                        r"on(?:Key(?:Down|Up|Press)|keydown|keyup|keypress)\s*[={]",
                        content,
                    )
                )
                if onclick_count > keyboard_count:
                    issues["click_no_keyboard"] += onclick_count - keyboard_count

                # 检查 div 是否使用了 click handler（应使用 button）
                div_clicks = len(re.findall(r"<div\b[^>]*onClick", content))
                issues["div_click_handler"] += div_clicks

                # 检查 ARIA landmarks 或语义化标签
                if re.search(r"(?:role\s*=|<(?:main|nav|header|footer|aside)\b)", content):
                    has_landmarks = True

        if files_scanned == 0:
            checks.append(
                QualityCheck(
                    name="无障碍性检查",
                    category="accessibility",
                    description="前端文件无障碍性 (WCAG 2.1)",
                    status=CheckStatus.WARNING,
                    score=80,
                    weight=0.8,
                    details="未找到前端源文件，跳过无障碍性检查",
                )
            )
            return checks

        score = 100
        details_parts: list[str] = []

        if issues["missing_alt"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['missing_alt']} 个 <img> 缺少 alt 属性")

        if issues["missing_label"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['missing_label']} 个 <input> 缺少 label/aria-label")

        if issues["click_no_keyboard"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['click_no_keyboard']} 个 onClick 缺少键盘事件处理")

        if issues["div_click_handler"] > 0:
            score -= 15
            details_parts.append(
                f"发现 {issues['div_click_handler']} 个 <div> 使用 onClick（应使用 <button>）"
            )

        if not has_landmarks:
            score -= 10
            details_parts.append("未检测到 ARIA landmarks 或语义化标签")

        score = max(0, score)

        if score >= 80:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED

        details = "; ".join(details_parts) if details_parts else "无障碍性检查通过"

        checks.append(
            QualityCheck(
                name="无障碍性检查",
                category="accessibility",
                description="前端文件无障碍性 (WCAG 2.1)",
                status=status,
                score=score,
                weight=0.8,
                details=f"扫描 {files_scanned} 个文件 - {details}",
            )
        )

        return checks

    def _check_performance_budget(self) -> list[QualityCheck]:
        """检查性能预算（bundle size、依赖数量）"""
        checks: list[QualityCheck] = []
        score = 100
        details_parts: list[str] = []

        # 检查前端 bundle 产物大小
        dist_dirs = ["dist", "build", ".next", ".output", "out"]
        total_bundle_kb = 0
        bundle_dir_found = False

        for dist_name in dist_dirs:
            dist_dir = self.project_dir / "frontend" / dist_name
            if not dist_dir.exists():
                dist_dir = self.project_dir / dist_name
            if not dist_dir.exists():
                continue
            bundle_dir_found = True
            for f in dist_dir.rglob("*"):
                if f.is_file() and f.suffix in {".js", ".css", ".mjs"}:
                    total_bundle_kb += f.stat().st_size / 1024

        if bundle_dir_found:
            if total_bundle_kb > 2048:  # > 2MB
                score -= 25
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（超过 2MB 预算）")
            elif total_bundle_kb > 1024:  # > 1MB
                score -= 10
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（接近 1MB 预算）")
            else:
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（在预算内）")

        # 检查 npm 依赖数量
        pkg_json = self.project_dir / "frontend" / "package.json"
        if not pkg_json.exists():
            pkg_json = self.project_dir / "package.json"

        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                dep_count = len(pkg.get("dependencies", {}))

                if dep_count > 40:
                    score -= 15
                    details_parts.append(f"生产依赖 {dep_count} 个（超过 40 个上限）")
                elif dep_count > 25:
                    score -= 5
                    details_parts.append(f"生产依赖 {dep_count} 个（较多）")
                else:
                    details_parts.append(f"生产依赖 {dep_count} 个")
            except (json.JSONDecodeError, OSError):
                pass

        # 检查大文件（潜在性能问题）
        large_files = 0
        for src_dir_name in ["frontend/src", "src", "app"]:
            src_dir = self.project_dir / src_dir_name
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*"):
                if (
                    f.is_file()
                    and f.suffix in {".ts", ".tsx", ".js", ".jsx", ".vue"}
                    and f.stat().st_size > 50 * 1024
                ):
                    large_files += 1

        if large_files > 0:
            score -= min(15, large_files * 5)
            details_parts.append(f"{large_files} 个前端文件超过 50KB（影响代码分割）")

        score = max(0, score)

        if score >= 80:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED

        details = "; ".join(details_parts) if details_parts else "未检测到前端构建产物"

        checks.append(
            QualityCheck(
                name="性能预算检查",
                category="performance",
                description="前端性能预算（bundle size、依赖数量）",
                status=status,
                score=score,
                weight=1.0,
                details=details,
            )
        )

        return checks

    def _check_ui_contract_execution(self) -> QualityCheck:
        """检查 UI 契约、Design Token 与前端 runtime 是否闭环"""
        output_dir = self.project_dir / "output"
        ui_contract_path = output_dir / f"{self.name}-ui-contract.json"
        frontend_dir = output_dir / "frontend"
        design_tokens_path = frontend_dir / "design-tokens.css"
        runtime_path = output_dir / f"{self.name}-frontend-runtime.json"
        alignment_path = output_dir / f"{self.name}-ui-contract-alignment.json"

        if (
            not ui_contract_path.exists()
            and not frontend_dir.exists()
            and not runtime_path.exists()
        ):
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="尚未检测到前端实现阶段证据，暂无法验证 UI 契约执行闭环",
            )

        if not ui_contract_path.exists():
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="缺少 output/*-ui-contract.json，UI 系统决策尚未冻结成正式契约",
            )

        try:
            payload = json.loads(ui_contract_path.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约 JSON 不可解析",
            )

        if not isinstance(payload, dict):
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约必须是 JSON object",
            )

        component_stack = (
            payload.get("component_stack", {})
            if isinstance(payload.get("component_stack"), dict)
            else {}
        )
        analysis = payload.get("analysis", {}) if isinstance(payload.get("analysis"), dict) else {}
        frontend_value = str(analysis.get("frontend") or "").lower().strip()
        cross_platform_frontend = is_cross_platform_frontend(frontend_value)
        emoji_policy = (
            payload.get("emoji_policy") if isinstance(payload.get("emoji_policy"), dict) else {}
        )
        framework_playbook = (
            payload.get("framework_playbook")
            if isinstance(payload.get("framework_playbook"), dict)
            else {}
        )
        icon_system = (
            payload.get("icon_system")
            or component_stack.get("icon")
            or component_stack.get("icons")
            or ""
        )
        required_sections = {
            "style_direction": bool(payload.get("style_direction")),
            "typography": (
                (isinstance(payload.get("typography"), dict) and bool(payload.get("typography")))
                or (
                    isinstance(payload.get("typography_preset"), dict)
                    and bool(payload.get("typography_preset"))
                )
            ),
            "icon_system": bool(icon_system),
            "emoji_policy": (
                bool(emoji_policy)
                and emoji_policy.get("allowed_in_ui") is False
                and emoji_policy.get("allowed_as_icon") is False
                and emoji_policy.get("allowed_during_development") is False
            ),
            "ui_library_preference": isinstance(payload.get("ui_library_preference"), dict)
            and bool(payload.get("ui_library_preference")),
            "design_tokens": isinstance(payload.get("design_tokens"), dict)
            and bool(payload.get("design_tokens")),
        }
        if cross_platform_frontend:
            required_sections["framework_playbook"] = framework_playbook_complete(
                framework_playbook
            )
        missing_sections = [name for name, present in required_sections.items() if not present]
        if missing_sections:
            if cross_platform_frontend and "framework_playbook" in missing_sections:
                framework_name = str(
                    framework_playbook.get("framework") or frontend_value or "cross-platform"
                ).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=30,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        f"{framework_name} 跨平台框架 playbook 缺少冻结字段: "
                        + ", ".join(missing_sections)
                    ),
                )
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details=f"UI 契约缺少冻结字段: {', '.join(missing_sections)}",
            )

        if frontend_dir.exists() and not design_tokens_path.exists():
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="前端产物存在，但缺少 output/frontend/design-tokens.css",
            )

        if not runtime_path.exists():
            if frontend_dir.exists():
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details="前端产物已生成，但 frontend runtime 报告缺失，无法证明运行时已接入",
                )
            warning_score = 75 if self.is_zero_to_one else 55
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="已冻结 UI 契约，但尚未检测到 frontend runtime 报告，无法确认运行时已接入",
            )

        if not alignment_path.exists():
            if frontend_dir.exists():
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details="前端产物和 runtime 已存在，但 UI 契约对齐报告缺失，无法证明源码已真正遵守 UI 契约",
                )
            warning_score = 80 if self.is_zero_to_one else 60
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约和 frontend runtime 已存在，但 UI 契约对齐报告尚未生成，建议完成 UI review 后重新验证",
            )

        try:
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="frontend runtime JSON 不可解析",
            )

        if not isinstance(runtime_payload, dict):
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="frontend runtime 必须是 JSON object",
            )

        checks = runtime_payload.get("checks", {})
        runtime_ready = (
            isinstance(checks, dict)
            and bool(runtime_payload.get("passed", False))
            and bool(checks.get("ui_contract_json", False))
            and bool(checks.get("output_frontend_design_tokens", False))
            and bool(checks.get("ui_contract_alignment", False))
            and bool(checks.get("ui_theme_entry", False))
            and bool(checks.get("ui_navigation_shell", False))
            and bool(checks.get("ui_component_imports", False))
            and bool(checks.get("ui_banned_patterns", False))
            and bool(checks.get("ui_framework_playbook", True))
            and bool(checks.get("ui_framework_execution", True))
        )
        if not runtime_ready:
            if cross_platform_frontend:
                framework_name = str(
                    framework_playbook.get("framework") or frontend_value or "cross-platform"
                ).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        f"frontend runtime 未证明 {framework_name} 跨平台框架 playbook 与专项执行已真实接入前端"
                    ),
                )
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=35,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="frontend runtime 未证明 UI 契约文件、Design Token 与跨平台框架 playbook 已真实接入前端",
            )

        library = payload.get("ui_library_preference", {}).get("final_selected", "-")
        return QualityCheck(
            name="UI 契约执行",
            category="ui_quality",
            description="UI 契约、Design Token 与运行时验证闭环",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
            details=(
                "UI 契约已冻结并接入 runtime；"
                f"library={library}; icon={icon_system or '-'}; "
                "emoji_policy=forbidden"
            ),
        )

    def _check_ui_review(self) -> QualityCheck:
        """检查商业级 UI 基线和实现一致性"""
        from .ui_review import UIReviewReviewer

        reviewer = UIReviewReviewer(
            project_dir=self.project_dir,
            name=self.name,
            tech_stack=self.tech_stack,
        )
        report = reviewer.review()
        self.latest_ui_review_report = report

        blocking_titles = {
            "UI 系统决策未被完整冻结",
            "源码未落实文档冻结的图标系统",
            "源码未落实文档冻结的字体组合",
            "源码未落实文档冻结的组件生态",
        }
        has_blocking_alignment_gap = any(item.title in blocking_titles for item in report.findings)

        if report.critical_count > 0 or has_blocking_alignment_gap:
            status = CheckStatus.FAILED
        elif report.high_count > 0 or report.score < 80:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.PASSED

        detail_prefix = (
            f"score={report.score}, critical={report.critical_count}, "
            f"high={report.high_count}, medium={report.medium_count}"
        )
        if report.findings:
            details = f"{detail_prefix}; top issue: {report.findings[0].title}"
        else:
            details = f"{detail_prefix}; 未发现明显 UI 商业级违例"

        from ..design.ui_intelligence import UIIntelligenceAdvisor

        checklist = UIIntelligenceAdvisor.PRE_DELIVERY_CHECKLIST
        details += f" | 交付检查清单 ({len(checklist)} 项): " + "; ".join(checklist[:3]) + "..."

        return QualityCheck(
            name="UI 商业完成度",
            category="ui_quality",
            description="UI 设计基线、实现一致性与反模式扫描",
            status=status,
            score=report.score,
            weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
            details=details,
        )

    def _check_security(self, redteam_report: RedTeamReport | None) -> list[QualityCheck]:
        """检查安全性"""
        checks: list[QualityCheck] = []

        if redteam_report:
            critical_count = sum(
                1 for i in redteam_report.security_issues if i.severity == "critical"
            )
            high_count = sum(1 for i in redteam_report.security_issues if i.severity == "high")

            if critical_count > 0:
                score = max(0, 100 - critical_count * 30)
                status = CheckStatus.FAILED
            elif high_count > 2:
                score = max(0, 100 - high_count * 15)
                status = CheckStatus.WARNING
            else:
                score = 100
                status = CheckStatus.PASSED

            checks.append(
                QualityCheck(
                    name="安全审查",
                    category="security",
                    description=f"安全检查 ({critical_count} critical, {high_count} high)",
                    status=status,
                    score=score,
                    weight=self.CHECKS_CONFIG["security"]["weight"],
                    details=(
                        f"发现 {critical_count} 个严重问题和 {high_count} 个高危问题"
                        if critical_count + high_count > 0
                        else "未发现严重安全问题"
                    ),
                )
            )
        else:
            # 未进行红队审查，给警告
            checks.append(
                QualityCheck(
                    name="安全审查",
                    category="security",
                    description="安全检查状态",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["security"]["weight"],
                    details="未进行红队安全审查",
                )
            )

        return checks

    def _check_performance(self, redteam_report: RedTeamReport | None) -> list[QualityCheck]:
        """检查性能"""
        checks: list[QualityCheck] = []

        if redteam_report:
            critical_count = sum(
                1 for i in redteam_report.performance_issues if i.severity == "critical"
            )
            high_count = sum(1 for i in redteam_report.performance_issues if i.severity == "high")

            if critical_count > 0:
                score = max(0, 100 - critical_count * 25)
                status = CheckStatus.FAILED
            elif high_count > 2:
                score = max(0, 100 - high_count * 10)
                status = CheckStatus.WARNING
            else:
                score = 100
                status = CheckStatus.PASSED

            checks.append(
                QualityCheck(
                    name="性能审查",
                    category="performance",
                    description=f"性能检查 ({critical_count} critical, {high_count} high)",
                    status=status,
                    score=score,
                    weight=self.CHECKS_CONFIG["performance"]["weight"],
                    details=(
                        f"发现 {critical_count} 个严重问题和 {high_count} 个高危问题"
                        if critical_count + high_count > 0
                        else "未发现严重性能问题"
                    ),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="性能审查",
                    category="performance",
                    description="性能检查状态",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["performance"]["weight"],
                    details="未进行红队性能审查",
                )
            )

        return checks

    def _check_testing(self) -> list[QualityCheck]:
        """检查测试策略"""
        checks: list[QualityCheck] = []

        # 检查是否有测试配置
        has_jest = self._has_js_test_script()
        has_pytest = self._has_pytest_config()

        if has_jest or has_pytest:
            checks.append(
                QualityCheck(
                    name="测试框架",
                    category="testing",
                    description="测试框架配置",
                    status=CheckStatus.PASSED,
                    score=100,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="测试框架已配置",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="测试框架",
                    category="testing",
                    description="测试框架配置",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="测试框架未配置",
                )
            )

        python_tests = self._discover_python_tests()
        js_test_targets = self._discover_js_test_targets()

        # 真实测试执行检查（优先 Python）
        if python_tests:
            pytest_executable = shutil.which("pytest")
            if pytest_executable:
                result = self._run_command(
                    [pytest_executable, "-q", "--maxfail=1"],
                    timeout=180,
                )
                if result["timed_out"]:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.WARNING,
                            score=40,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details="pytest 执行超时，建议拆分测试或优化测试速度",
                        )
                    )
                elif result["returncode"] == 0:
                    summary = self._extract_test_summary(str(result["stdout"]))
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=summary or "pytest 执行通过",
                        )
                    )
                else:
                    summary = self._extract_test_summary(str(result["stdout"] or result["stderr"]))
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=summary or "pytest 执行失败",
                        )
                    )
            else:
                checks.append(
                    QualityCheck(
                        name="测试执行",
                        category="testing",
                        description="自动化测试执行结果",
                        status=CheckStatus.WARNING,
                        score=40,
                        weight=self.CHECKS_CONFIG["testing"]["weight"],
                        details="检测到 Python 测试，但未找到 pytest 可执行文件",
                    )
                )
        elif js_test_targets:
            npm_executable = shutil.which("npm")
            if not npm_executable:
                checks.append(
                    QualityCheck(
                        name="测试执行",
                        category="testing",
                        description="自动化测试执行结果",
                        status=CheckStatus.WARNING,
                        score=40,
                        weight=self.CHECKS_CONFIG["testing"]["weight"],
                        details="检测到 JS 测试脚本，但未找到 npm 可执行文件",
                    )
                )
            else:
                timed_out_targets: list[str] = []
                failed_targets: list[str] = []
                passed_targets: list[str] = []
                for target in js_test_targets:
                    rel = "."
                    if target != self.project_dir:
                        rel = str(target.relative_to(self.project_dir))
                    result = self._run_command(
                        [
                            npm_executable,
                            "--prefix",
                            str(target),
                            "run",
                            "test",
                            "--if-present",
                        ],
                        timeout=240,
                    )
                    if result["timed_out"]:
                        timed_out_targets.append(rel)
                    elif result["returncode"] == 0:
                        passed_targets.append(rel)
                    else:
                        failed_targets.append(rel)

                if failed_targets:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试失败: {', '.join(failed_targets)}",
                        )
                    )
                elif timed_out_targets:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.WARNING,
                            score=40,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试超时: {', '.join(timed_out_targets)}",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试通过: {', '.join(passed_targets)}",
                        )
                    )
        else:
            warning_score = 70 if self.is_zero_to_one else 40
            checks.append(
                QualityCheck(
                    name="测试执行",
                    category="testing",
                    description="自动化测试执行结果",
                    status=CheckStatus.WARNING,
                    score=warning_score,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="未检测到可执行测试用例",
                )
            )

        checks.append(self._check_spec_task_completion())
        checks.append(self._check_spec_code_consistency())
        checks.append(self._check_task_execution_review_trace())

        coverage_percent = self._read_coverage_percent()
        if coverage_percent is None:
            warning_score = 70 if self.is_zero_to_one else 50
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.WARNING,
                    score=warning_score,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="未检测到 coverage.xml 报告",
                )
            )
        elif coverage_percent >= 80:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.PASSED,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%",
                )
            )
        elif coverage_percent >= 60:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.WARNING,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%（建议提升到 80%+）",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.FAILED,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%（低于最低建议）",
                )
            )

        return checks

    def _check_task_execution_review_trace(self) -> QualityCheck:
        """检查任务执行报告是否包含最小自检轨迹"""
        output_dir = self.project_dir / "output"
        report_files = sorted(output_dir.glob("*-task-execution.md")) if output_dir.exists() else []
        if not report_files:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="任务执行自检轨迹",
                category="testing",
                description="任务执行报告中的最小自检记录",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="未发现 output/*-task-execution.md",
            )

        latest_report = max(report_files, key=lambda path: path.stat().st_mtime)
        content = latest_report.read_text(encoding="utf-8", errors="ignore")
        required_markers = [
            "## 执行期验证摘要",
            "## 宿主补充自检（交付前必做）",
            "build / compile / type-check / test / runtime smoke",
            "新增函数、方法、字段、模块都已接入真实调用链",
            "新增 warning",
            "对本次 diff 做最小自审",
        ]
        missing_markers = [marker for marker in required_markers if marker not in content]
        if missing_markers:
            return QualityCheck(
                name="任务执行自检轨迹",
                category="testing",
                description="任务执行报告中的最小自检记录",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details=f"任务执行报告缺少自检字段: {', '.join(missing_markers)}",
            )

        return QualityCheck(
            name="任务执行自检轨迹",
            category="testing",
            description="任务执行报告中的最小自检记录",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["testing"]["weight"],
            details=f"已记录最小自检轨迹（{latest_report.name}）",
        )

    def _check_spec_task_completion(self) -> QualityCheck:
        """检查 Spec 任务完成度"""
        task_files = list((self.project_dir / ".super-dev" / "changes").glob("*/tasks.md"))
        if not task_files:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="未发现 .super-dev/changes/*/tasks.md",
            )

        latest_task_file = max(task_files, key=lambda path: path.stat().st_mtime)
        total = 0
        completed = 0
        in_progress = 0
        for line in latest_task_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ["):
                continue
            marker = stripped[2:5]
            if not re.match(r"^\[[ x~_]\]$", marker):
                continue
            total += 1
            if marker == "[x]":
                completed += 1
            elif marker == "[~]":
                in_progress += 1

        if total == 0:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="发现 tasks.md 但未解析到任务项",
            )

        pending = total - completed
        completion_rate = int((completed / total) * 100) if total else 0
        if pending == 0 and in_progress == 0:
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details=f"任务完成 {completed}/{total}（{latest_task_file.parent.name}）",
            )

        score = max(20, completion_rate)
        check_status = CheckStatus.FAILED if completion_rate < 80 else CheckStatus.WARNING
        return QualityCheck(
            name="Spec任务完成度",
            category="testing",
            description="Spec 任务闭环状态",
            status=check_status,
            score=score,
            weight=self.CHECKS_CONFIG["testing"]["weight"],
            details=f"任务完成 {completed}/{total}，未完成 {pending}（{latest_task_file.parent.name}）",
        )

    def _check_spec_code_consistency(self) -> QualityCheck:
        """检查 Spec-Code 一致性（可选维度，失败不阻塞门禁）"""
        try:
            from ..specs.consistency_checker import SpecConsistencyChecker

            changes_dir = self.project_dir / ".super-dev" / "changes"
            if not changes_dir.exists():
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.WARNING,
                    score=70 if self.is_zero_to_one else 50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="未找到 .super-dev/changes/ 目录",
                )

            # 取最近修改的变更
            change_dirs = [
                d for d in changes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]
            if not change_dirs:
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.WARNING,
                    score=70 if self.is_zero_to_one else 50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="无活跃变更",
                )

            latest = max(change_dirs, key=lambda d: d.stat().st_mtime)
            checker = SpecConsistencyChecker(self.project_dir)
            report = checker.check(latest.name)

            if report.consistency_score >= 90:
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.PASSED,
                    score=report.consistency_score,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details=f"一致性分数 {report.consistency_score}/100（{latest.name}）",
                )

            status = CheckStatus.WARNING if report.consistency_score >= 60 else CheckStatus.FAILED
            return QualityCheck(
                name="Spec-Code一致性",
                category="code_quality",
                description="Spec 与代码实现一致性检测",
                status=status,
                score=report.consistency_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    f"一致性分数 {report.consistency_score}/100，"
                    f"问题 {len(report.issues)} 项（{latest.name}）"
                ),
            )
        except Exception:
            return QualityCheck(
                name="Spec-Code一致性",
                category="code_quality",
                description="Spec 与代码实现一致性检测",
                status=CheckStatus.WARNING,
                score=50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="一致性检测执行异常，已跳过",
            )

    def _check_code_quality(self) -> list[QualityCheck]:
        """检查代码质量工具"""
        checks: list[QualityCheck] = []

        # 检查 Linter
        has_eslint = (self.project_dir / ".eslintrc.js").exists() or (
            self.project_dir / ".eslintrc.json"
        ).exists()
        has_pylint = (self.project_dir / "pylint.ini").exists()
        try:
            has_black = (self.project_dir / "pyproject.toml").exists() and "black" in (
                self.project_dir / "pyproject.toml"
            ).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            has_black = False

        if has_eslint or has_pylint or has_black:
            checks.append(
                QualityCheck(
                    name="Linter",
                    category="code_quality",
                    description="代码静态检查工具",
                    status=CheckStatus.PASSED,
                    score=100,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="Linter 已配置",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="Linter",
                    category="code_quality",
                    description="代码静态检查工具",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="Linter 未配置",
                )
            )

        python_roots = self._discover_python_source_roots()
        if python_roots:
            python_exec = shutil.which("python3") or shutil.which("python")
            if python_exec:
                cmd = [python_exec, "-m", "compileall", "-q", *[str(p) for p in python_roots]]
                result = self._run_command(cmd, timeout=120)
                if result["timed_out"]:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.WARNING,
                            score=50,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="compileall 执行超时",
                        )
                    )
                elif result["returncode"] == 0:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="Python 语法检查通过",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="Python 语法检查失败",
                        )
                    )
            else:
                checks.append(
                    QualityCheck(
                        name="Python 语法检查",
                        category="code_quality",
                        description="compileall 语法检查",
                        status=CheckStatus.WARNING,
                        score=50,
                        weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                        details="未找到 python 解释器，跳过语法检查",
                    )
                )

        checks.append(self._check_pipeline_observability())
        checks.append(self._check_host_compatibility())
        checks.append(self._check_knowledge_governance())
        checks.append(self._check_launch_rehearsal())
        checks.append(self._check_rehearsal_verification_report())

        # Schema drift 检测
        checks.append(self._check_schema_drift())

        return checks

    def _check_pipeline_observability(self) -> QualityCheck:
        output_dir = self.project_dir / "output"
        metric_files = (
            sorted(output_dir.glob("*-pipeline-metrics.json")) if output_dir.exists() else []
        )
        if not metric_files:
            return QualityCheck(
                name="Pipeline 可观测性",
                category="code_quality",
                description="流水线指标报告",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/*-pipeline-metrics.json",
            )

        latest = max(metric_files, key=lambda path: path.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="Pipeline 可观测性",
                category="code_quality",
                description="流水线指标报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"指标文件不可解析: {latest.name}",
            )

        success = bool(payload.get("success", False))
        success_rate = float(payload.get("success_rate", 0))
        if success and success_rate >= 90:
            status = CheckStatus.PASSED
            score = 100
        elif success:
            status = CheckStatus.WARNING
            score = 80
        else:
            status = CheckStatus.FAILED
            score = 40

        return QualityCheck(
            name="Pipeline 可观测性",
            category="code_quality",
            description="流水线指标报告",
            status=status,
            score=score,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"{latest.name} | success_rate={success_rate:.1f}%",
        )

    def _check_host_compatibility(self) -> QualityCheck:
        min_score = float(self.host_compatibility_min_score)
        min_ready_hosts = self.host_compatibility_min_ready_hosts
        warning_threshold = max(40.0, min_score - 20.0)

        output_dir = self.project_dir / "output"
        reports = (
            sorted(output_dir.glob("*-host-compatibility.json")) if output_dir.exists() else []
        )
        if not reports:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.WARNING,
                score=70 if self.is_zero_to_one else 60,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    "未发现 output/*-host-compatibility.json "
                    f"(目标阈值: score>={min_score:.0f}, ready_hosts>={min_ready_hosts})"
                ),
            )

        latest = max(reports, key=lambda path: path.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"兼容性报告不可解析: {latest.name}",
            )

        compatibility = payload.get("compatibility", {}) if isinstance(payload, dict) else {}
        if not isinstance(compatibility, dict):
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"兼容性报告结构非法: {latest.name}",
            )

        try:
            overall_score = float(compatibility.get("overall_score", 0))
        except (TypeError, ValueError):
            overall_score = 0.0
        try:
            ready_hosts = int(compatibility.get("ready_hosts", 0))
        except (TypeError, ValueError):
            ready_hosts = 0
        try:
            total_hosts = int(compatibility.get("total_hosts", 0))
        except (TypeError, ValueError):
            total_hosts = 0

        bounded_score = max(0, min(100, int(round(overall_score))))
        details = (
            f"{latest.name} | overall={overall_score:.2f} | " f"ready={ready_hosts}/{total_hosts}"
        )

        profile = self._host_profile_metrics(compatibility)
        if profile is not None:
            overall_score = self._coerce_float(profile.get("overall_score"), default=0.0)
            ready_hosts = self._coerce_int(profile.get("ready_hosts"), default=0)
            total_hosts = self._coerce_int(profile.get("total_hosts"), default=0)
            bounded_score = self._coerce_int(profile.get("bounded_score"), default=0)
            details = (
                f"{latest.name} | profile={profile.get('label', 'unknown')} | overall={overall_score:.2f} | "
                f"ready={ready_hosts}/{total_hosts}"
            )

        if overall_score >= min_score and ready_hosts >= min_ready_hosts:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.PASSED,
                score=bounded_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=details,
            )

        if overall_score >= warning_threshold:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.WARNING,
                score=bounded_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    f"{details}（建议至少 {min_score:.0f} 分且 "
                    f"ready host >= {min_ready_hosts}）"
                ),
            )

        return QualityCheck(
            name="宿主兼容性",
            category="code_quality",
            description="AI Coding 宿主接入兼容性报告",
            status=CheckStatus.FAILED,
            score=max(20, bounded_score),
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"{details}（低于最低建议阈值）",
        )

    def _host_profile_metrics(self, compatibility: dict[str, object]) -> HostProfileMetrics | None:
        if not self.host_profile_enforce_selected or not self.host_profile_targets:
            return None

        hosts_obj = compatibility.get("hosts", {})
        hosts = hosts_obj if isinstance(hosts_obj, dict) else {}
        selected = [item for item in self.host_profile_targets if item in hosts]
        if not selected:
            return {
                "label": ",".join(self.host_profile_targets),
                "overall_score": 0.0,
                "ready_hosts": 0,
                "total_hosts": len(self.host_profile_targets),
                "bounded_score": 0,
            }

        score_values: list[float] = []
        ready_hosts = 0
        for target in selected:
            host_data = hosts.get(target, {})
            if isinstance(host_data, dict):
                try:
                    score_values.append(float(host_data.get("score", 0.0)))
                except (TypeError, ValueError):
                    score_values.append(0.0)
                if bool(host_data.get("ready", False)):
                    ready_hosts += 1
            else:
                score_values.append(0.0)

        overall_score = sum(score_values) / len(score_values) if score_values else 0.0
        bounded_score = max(0, min(100, int(round(overall_score))))
        return {
            "label": ",".join(selected),
            "overall_score": overall_score,
            "ready_hosts": ready_hosts,
            "total_hosts": len(selected),
            "bounded_score": bounded_score,
        }

    def _check_knowledge_governance(self) -> QualityCheck:
        config_file = self.project_dir / "super-dev.yaml"
        config_domains: list[str] = []
        config_ttl = 1800
        if config_file.exists():
            try:
                raw_config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
                if isinstance(raw_config, dict):
                    domains_raw = raw_config.get("knowledge_allowed_domains", [])
                    if isinstance(domains_raw, list):
                        config_domains = [
                            str(item).strip().lower() for item in domains_raw if str(item).strip()
                        ]
                    ttl_raw = raw_config.get("knowledge_cache_ttl_seconds", 1800)
                    if isinstance(ttl_raw, int):
                        config_ttl = ttl_raw
                    elif isinstance(ttl_raw, str) and ttl_raw.strip().isdigit():
                        config_ttl = int(ttl_raw.strip())
            except Exception:
                pass

        cache_dir = self.project_dir / "output" / "knowledge-cache"
        bundles = sorted(cache_dir.glob("*-knowledge-bundle.json")) if cache_dir.exists() else []
        if not bundles:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=70 if self.is_zero_to_one else 60,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/knowledge-cache/*-knowledge-bundle.json",
            )

        latest = max(bundles, key=lambda path: path.stat().st_mtime)
        try:
            bundle = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"知识缓存不可解析: {latest.name}",
            )
        if not isinstance(bundle, dict):
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"知识缓存结构非法: {latest.name}",
            )

        signature = str(bundle.get("cache_signature", "")).strip()
        if not signature:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="知识缓存缺少 cache_signature",
            )

        ttl_value = bundle.get("cache_ttl_seconds", config_ttl)
        bundle_ttl = ttl_value if isinstance(ttl_value, int) else config_ttl
        metadata = bundle.get("metadata", {})
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        web_enabled = bool(metadata_dict.get("web_enabled", False))
        bundle_domains_raw = metadata_dict.get("allowed_web_domains", [])
        bundle_domains = (
            [str(item).strip().lower() for item in bundle_domains_raw if str(item).strip()]
            if isinstance(bundle_domains_raw, list)
            else []
        )
        web_stats = metadata_dict.get("web_stats", {})
        filtered_out_count = 0
        if isinstance(web_stats, dict):
            raw_filtered = web_stats.get("filtered_out_count", 0)
            if isinstance(raw_filtered, int):
                filtered_out_count = raw_filtered

        if bundle_ttl <= 0:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=70,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="knowledge_cache_ttl_seconds <= 0，缓存治理策略关闭",
            )

        if web_enabled and not bundle_domains:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=75,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="联网知识未配置白名单域名",
            )

        config_domain_set = set(config_domains)
        bundle_domain_set = set(bundle_domains)
        if config_domain_set and bundle_domain_set and config_domain_set != bundle_domain_set:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=80,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="缓存白名单与项目配置不一致",
            )

        details = (
            f"{latest.name} | ttl={bundle_ttl}s | "
            f"domains={len(bundle_domains)} | filtered_out={filtered_out_count}"
        )
        return QualityCheck(
            name="知识增强治理",
            category="code_quality",
            description="知识来源白名单与缓存可审计性",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=details,
        )

    def _check_launch_rehearsal(self) -> QualityCheck:
        rehearsal_dir = self.project_dir / "output" / "rehearsal"
        required_patterns = [
            "*-launch-rehearsal.md",
            "*-rollback-playbook.md",
            "*-smoke-checklist.md",
        ]
        found = 0
        if rehearsal_dir.exists():
            for pattern in required_patterns:
                if any(rehearsal_dir.glob(pattern)):
                    found += 1

        if found == len(required_patterns):
            return QualityCheck(
                name="发布演练准备",
                category="code_quality",
                description="发布演练与回滚手册",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="发布演练文档齐全",
            )
        if found == 0:
            return QualityCheck(
                name="发布演练准备",
                category="code_quality",
                description="发布演练与回滚手册",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/rehearsal/* 发布演练文档",
            )
        return QualityCheck(
            name="发布演练准备",
            category="code_quality",
            description="发布演练与回滚手册",
            status=CheckStatus.WARNING,
            score=75,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"发布演练文档不完整 ({found}/{len(required_patterns)})",
        )

    def _check_rehearsal_verification_report(self) -> QualityCheck:
        rehearsal_dir = self.project_dir / "output" / "rehearsal"
        if not rehearsal_dir.exists():
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/rehearsal 目录",
            )

        has_md = any(rehearsal_dir.glob("*-rehearsal-report.md"))
        has_json = any(rehearsal_dir.glob("*-rehearsal-report.json"))
        if has_md and has_json:
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="已生成 rehearsal markdown + json 报告",
            )
        if has_md or has_json:
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.WARNING,
                score=80,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="发布演练报告格式不完整（需同时包含 md 与 json）",
            )
        return QualityCheck(
            name="发布演练验证报告",
            category="code_quality",
            description="发布演练验证结果",
            status=CheckStatus.WARNING,
            score=70 if self.is_zero_to_one else 60,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details="未发现 output/rehearsal/*-rehearsal-report.(md|json)",
        )

    def _check_schema_drift(self) -> QualityCheck:
        """检测 ORM 模型文件是否比最新迁移文件更新（schema drift）"""
        weight = self.CHECKS_CONFIG["schema_drift"]["weight"]

        model_patterns = [
            "**/models.py",
            "**/models/*.py",
            "**/schema.py",
            "**/entities/*.py",
            "**/*.entity.ts",
            "**/prisma/schema.prisma",
        ]
        migration_patterns = [
            "**/migrations/**",
            "**/alembic/**",
            "**/prisma/migrations/**",
            "**/drizzle/**",
        ]

        # Collect model files with their latest mtime
        model_files: list[Path] = []
        for pattern in model_patterns:
            model_files.extend(self.project_dir.glob(pattern))

        # Filter out __pycache__, node_modules, .git, and migration dirs themselves
        skip_segments = {"__pycache__", "node_modules", ".git", "migrations", "alembic"}
        model_files = [f for f in model_files if f.is_file() and not (skip_segments & set(f.parts))]

        if not model_files:
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.PASSED,
                score=100,
                weight=weight,
                details="未发现 ORM 模型文件，跳过检测",
            )

        latest_model_mtime = max(f.stat().st_mtime for f in model_files)

        # Collect migration files
        migration_files: list[Path] = []
        for pattern in migration_patterns:
            migration_files.extend(f for f in self.project_dir.glob(pattern) if f.is_file())
        migration_files = [
            f
            for f in migration_files
            if not ({"__pycache__", "node_modules", ".git"} & set(f.parts))
        ]

        if not migration_files:
            # Models exist but no migrations at all — warn
            model_names = ", ".join(sorted(f.name for f in model_files[:5]))
            suffix = "..." if len(model_files) > 5 else ""
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.WARNING,
                score=60,
                weight=weight,
                details=(
                    f"发现 {len(model_files)} 个模型文件 ({model_names}{suffix}) "
                    "但未找到任何迁移文件，可能存在 schema drift"
                ),
            )

        latest_migration_mtime = max(f.stat().st_mtime for f in migration_files)

        if latest_model_mtime > latest_migration_mtime:
            # Find which model files are newer than latest migration
            drifted = [f for f in model_files if f.stat().st_mtime > latest_migration_mtime]
            drifted_names = ", ".join(
                sorted(str(f.relative_to(self.project_dir)) for f in drifted[:5])
            )
            suffix = "..." if len(drifted) > 5 else ""
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.WARNING,
                score=65,
                weight=weight,
                details=(
                    f"模型文件 ({drifted_names}{suffix}) 比最新迁移文件更新，"
                    "可能需要生成新的数据库迁移"
                ),
            )

        return QualityCheck(
            name="Schema Drift 检测",
            category="schema_drift",
            description="ORM 模型与数据库迁移文件一致性",
            status=CheckStatus.PASSED,
            score=100,
            weight=weight,
            details="模型文件与迁移文件时间戳一致，未检测到 schema drift",
        )

    def _calculate_total_score(self, checks: list[QualityCheck]) -> int:
        """计算总分"""
        score_checks = self._score_bearing_checks(checks)
        if not score_checks:
            return 0

        return round(sum(c.score for c in score_checks) / len(score_checks))

    def _calculate_weighted_score(self, checks: list[QualityCheck]) -> float:
        """计算加权分"""
        score_checks = self._score_bearing_checks(checks)
        if not score_checks:
            return 0.0

        total_weight = sum(c.weight for c in score_checks)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c.score * c.weight for c in score_checks)
        return weighted_sum / total_weight

    def _score_bearing_checks(self, checks: list[QualityCheck]) -> list[QualityCheck]:
        """返回参与门禁总分计算的检查项。

        advisory 型交叉审查和非阻断验证规则仍然保留在报告里，
        但不应把默认 0-1 流水线直接压成失败。
        """
        filtered: list[QualityCheck] = []
        for check in checks:
            if check.category == "cross_review":
                continue
            if check.category == "validation_rules" and check.status != CheckStatus.FAILED:
                continue
            filtered.append(check)
        return filtered

    def _generate_recommendations(self, checks: list[QualityCheck]) -> list[str]:
        """生成改进建议"""
        recommendations: list[str] = []

        fix_command_map = [
            ("PRD 文档", "运行 `super-dev run` 生成文档"),
            ("架构文档", "运行 `super-dev run` 生成文档"),
            ("UI/UX 文档", "运行 `super-dev run` 生成文档"),
            ("安全", "运行 `super-dev quality --type security` 查看详情"),
            ("测试", "运行 `pytest` 执行测试"),
            ("Spec 任务", "运行 `super-dev spec list` 查看任务状态"),
            ("宿主兼容性", "运行 `super-dev doctor --repair` 修复"),
            ("演练", "运行 `super-dev release readiness` 检查"),
            ("UI 质量", "运行 `super-dev review ui` 查看 UI 审查报告"),
        ]

        for check in checks:
            if check.status == CheckStatus.FAILED:
                prefix = "修复"
            elif check.status == CheckStatus.WARNING:
                prefix = "建议"
            else:
                continue

            description = check.description
            fix_hint = ""
            for keyword, command in fix_command_map:
                if keyword in description:
                    fix_hint = f" [修复: {command}]"
                    break

            recommendations.append(f"{prefix}: {description}{fix_hint}")

        return recommendations

    def _discover_python_tests(self) -> list[Path]:
        roots = [self.project_dir / "tests", self.project_dir / "backend" / "tests"]
        files: list[Path] = []
        for tests_dir in roots:
            if not tests_dir.exists():
                continue
            files.extend(list(tests_dir.rglob("test_*.py")))
            files.extend(list(tests_dir.rglob("*_test.py")))
        return files

    def _has_pytest_config(self) -> bool:
        if (self.project_dir / "pytest.ini").exists():
            return True

        setup_cfg = self.project_dir / "setup.cfg"
        if setup_cfg.exists():
            content = setup_cfg.read_text(encoding="utf-8", errors="ignore")
            if "[tool:pytest]" in content:
                return True

        tox_ini = self.project_dir / "tox.ini"
        if tox_ini.exists():
            content = tox_ini.read_text(encoding="utf-8", errors="ignore")
            if "[pytest]" in content:
                return True

        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            if "pytest.ini_options" in content:
                return True

        backend_pyproject = self.project_dir / "backend" / "pyproject.toml"
        if backend_pyproject.exists():
            content = backend_pyproject.read_text(encoding="utf-8", errors="ignore")
            if "pytest.ini_options" in content:
                return True

        return False

    def _discover_python_source_roots(self) -> list[Path]:
        roots: list[Path] = []
        candidates = ["super_dev", "src", "app", "backend", "server", "api", "services", "lib"]
        for name in candidates:
            path = self.project_dir / name
            if path.exists() and path.is_dir():
                roots.append(path)

        top_level_py = list(self.project_dir.glob("*.py"))
        roots.extend(top_level_py)

        # 去重并限制数量，避免无界扫描
        unique: list[Path] = []
        seen = set()
        for path in roots:
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        return unique[:8]

    def _discover_js_test_targets(self) -> list[Path]:
        targets: list[Path] = []
        for root in (self.project_dir, self.project_dir / "frontend", self.project_dir / "backend"):
            package_json = root / "package.json"
            if not package_json.exists():
                continue
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                continue
            scripts = data.get("scripts", {})
            test_script = str(scripts.get("test", "")).strip()
            if not test_script:
                continue
            if test_script == 'echo "Error: no test specified" && exit 1':
                continue
            targets.append(root)
        return targets

    def _has_js_test_script(self) -> bool:
        return bool(self._discover_js_test_targets())

    def _extract_test_summary(self, output: str) -> str:
        if not output:
            return ""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in reversed(lines):
            if "passed" in line or "failed" in line or "error" in line:
                return line[:240]
        return lines[-1][:240] if lines else ""

    def _read_coverage_percent(self) -> int | None:
        coverage_candidates = [
            self.project_dir / "coverage.xml",
            self.project_dir / "backend" / "coverage.xml",
            self.project_dir / "frontend" / "coverage.xml",
            self.project_dir / "coverage" / "cobertura-coverage.xml",
            self.project_dir / "frontend" / "coverage" / "cobertura-coverage.xml",
            self.project_dir / "backend" / "coverage" / "cobertura-coverage.xml",
        ]

        parsed_values: list[int] = []
        for coverage_xml in coverage_candidates:
            if not coverage_xml.exists():
                continue
            try:
                root = ElementTree.fromstring(coverage_xml.read_text(encoding="utf-8"))
                line_rate = root.attrib.get("line-rate")
                if line_rate is not None:
                    parsed_values.append(max(0, min(100, int(round(float(line_rate) * 100)))))
                    continue

                lines_covered = root.attrib.get("lines-covered")
                lines_valid = root.attrib.get("lines-valid")
                if lines_covered and lines_valid and float(lines_valid) > 0:
                    percent = (float(lines_covered) / float(lines_valid)) * 100
                    parsed_values.append(max(0, min(100, int(round(percent)))))
            except Exception:
                continue

        if not parsed_values:
            return None
        return max(parsed_values)

    def _run_command(self, cmd: list[str], timeout: int = 120) -> dict[str, object]:
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )  # nosec B603
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout or "",
                "stderr": completed.stderr or "",
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "returncode": -1,
                "stdout": (e.stdout or ""),
                "stderr": (e.stderr or ""),
                "timed_out": True,
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
            }
