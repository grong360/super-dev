"""
红队审查器 - 安全、性能、架构审查

开发：Excellent（11964948@qq.com）
功能：模拟红队视角，全面审查项目安全性、性能和架构
作用：在开发前发现问题，确保质量
创建时间：2025-12-30
"""

import json
import os
import re
import shutil
import subprocess  # nosec B404
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

try:
    from .review_agents import (
        ADVERSARIAL_VERIFICATION_PROMPT,
        build_parallel_review_prompt,
    )

    REVIEW_AGENTS_AVAILABLE = True
except ImportError:
    REVIEW_AGENTS_AVAILABLE = False


def _coerce_optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class _IssueLike(Protocol):
    severity: str
    description: str
    recommendation: str


@dataclass
class SecurityIssue:
    """安全问题"""

    severity: str  # critical, high, medium, low
    category: str  # injection, auth, xss, csrf, etc.
    description: str
    recommendation: str
    cwe: str | None = None
    file_path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "cwe": self.cwe,
            "file_path": self.file_path,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SecurityIssue":
        return cls(
            severity=str(payload.get("severity", "")),
            category=str(payload.get("category", "")),
            description=str(payload.get("description", "")),
            recommendation=str(payload.get("recommendation", "")),
            cwe=str(payload.get("cwe")) if payload.get("cwe") is not None else None,
            file_path=(
                str(payload.get("file_path")) if payload.get("file_path") is not None else None
            ),
            line=_coerce_optional_int(payload.get("line")),
        )


@dataclass
class PerformanceIssue:
    """性能问题"""

    severity: str  # critical, high, medium, low
    category: str  # database, api, frontend, infrastructure
    description: str
    recommendation: str
    impact: str = ""
    file_path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "impact": self.impact,
            "file_path": self.file_path,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PerformanceIssue":
        return cls(
            severity=str(payload.get("severity", "")),
            category=str(payload.get("category", "")),
            description=str(payload.get("description", "")),
            recommendation=str(payload.get("recommendation", "")),
            impact=str(payload.get("impact", "")),
            file_path=(
                str(payload.get("file_path")) if payload.get("file_path") is not None else None
            ),
            line=_coerce_optional_int(payload.get("line")),
        )


@dataclass
class ArchitectureIssue:
    """架构问题"""

    severity: str  # critical, high, medium, low
    category: str  # scalability, maintainability, reliability
    description: str
    recommendation: str
    adr_needed: bool = False
    file_path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "adr_needed": self.adr_needed,
            "file_path": self.file_path,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ArchitectureIssue":
        return cls(
            severity=str(payload.get("severity", "")),
            category=str(payload.get("category", "")),
            description=str(payload.get("description", "")),
            recommendation=str(payload.get("recommendation", "")),
            adr_needed=bool(payload.get("adr_needed", False)),
            file_path=(
                str(payload.get("file_path")) if payload.get("file_path") is not None else None
            ),
            line=_coerce_optional_int(payload.get("line")),
        )


@dataclass
class RedTeamReport:
    """红队审查报告"""

    project_name: str
    security_issues: list[SecurityIssue] = field(default_factory=list)
    performance_issues: list[PerformanceIssue] = field(default_factory=list)
    architecture_issues: list[ArchitectureIssue] = field(default_factory=list)
    pass_threshold: int = 70
    scanned_files_count: int = -1  # -1 表示未设置

    @property
    def critical_count(self) -> int:
        return (
            sum(1 for i in self.security_issues if i.severity == "critical")
            + sum(1 for i in self.performance_issues if i.severity == "critical")
            + sum(1 for i in self.architecture_issues if i.severity == "critical")
        )

    @property
    def high_count(self) -> int:
        return (
            sum(1 for i in self.security_issues if i.severity == "high")
            + sum(1 for i in self.performance_issues if i.severity == "high")
            + sum(1 for i in self.architecture_issues if i.severity == "high")
        )

    @property
    def total_score(self) -> int:
        """计算总分 (0-100)"""
        base_score = 100

        # 扣分标准
        for security_issue in self.security_issues:
            if security_issue.severity == "critical":
                base_score -= 20
            elif security_issue.severity == "high":
                base_score -= 10
            elif security_issue.severity == "medium":
                base_score -= 5
            elif security_issue.severity in {"advisory", "info"}:
                base_score -= 0
            else:
                base_score -= 2

        for performance_issue in self.performance_issues:
            if performance_issue.severity == "critical":
                base_score -= 15
            elif performance_issue.severity == "high":
                base_score -= 8
            elif performance_issue.severity == "medium":
                base_score -= 4
            elif performance_issue.severity in {"advisory", "info"}:
                base_score -= 0
            else:
                base_score -= 1

        for architecture_issue in self.architecture_issues:
            if architecture_issue.severity == "critical":
                base_score -= 15
            elif architecture_issue.severity == "high":
                base_score -= 8
            elif architecture_issue.severity == "medium":
                base_score -= 4
            elif architecture_issue.severity in {"advisory", "info"}:
                base_score -= 0
            else:
                base_score -= 1

        return max(0, base_score)

    @property
    def passed(self) -> bool:
        """红队是否通过（无 critical 且得分达到阈值）"""
        return self.critical_count == 0 and self.total_score >= self.pass_threshold

    @property
    def blocking_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.critical_count > 0:
            reasons.append(f"存在 {self.critical_count} 个 critical 问题")
        if self.total_score < self.pass_threshold:
            reasons.append(f"红队评分 {self.total_score} 低于阈值 {self.pass_threshold}")
        return reasons

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        lines = [
            f"# {self.project_name} - 红队审查报告",
            "",
            "> **审查时间**: 自动生成",
            f"> **总分**: {self.total_score}/100",
            f"> **通过阈值**: {self.pass_threshold}",
            "",
            "---",
            "",
            "## 执行摘要",
            "",
            f"- **Critical 问题**: {self.critical_count}",
            f"- **High 问题**: {self.high_count}",
            f"- **总分**: {self.total_score}/100",
            "",
        ]

        if self.scanned_files_count == 0:
            lines.append(
                "**状态**: 待代码实现后重新审查 - 当前项目没有源码文件可扫描，红队审查基于架构配置和文档进行基线评估。"
            )
        elif not self.passed:
            lines.append("**状态**: 未通过质量门禁 - 需要修复关键问题后重新审查")
        elif self.total_score < 80:
            lines.append("**状态**: 有条件通过 - 建议修复 High 级别问题")
        else:
            lines.append("**状态**: 通过 - 质量良好")

        lines.extend(["", "---", ""])

        # 安全审查
        lines.extend(
            [
                "## 1. 安全审查",
                "",
            ]
        )

        if not self.security_issues:
            lines.append("未发现明显的安全问题。")
        else:
            lines.append("| 严重性 | 类别 | 描述 | 建议 |")
            lines.append("|:---|:---|:---|:---|")
            for issue in self.security_issues:
                cwe_ref = f" ({issue.cwe})" if issue.cwe else ""
                lines.append(
                    f"| {issue.severity} | {issue.category}{cwe_ref} | {issue.description} | {issue.recommendation} |"
                )

        lines.extend(["", "---", ""])

        # 性能审查
        lines.extend(
            [
                "## 2. 性能审查",
                "",
            ]
        )

        if not self.performance_issues:
            lines.append("未发现明显的性能问题。")
        else:
            lines.append("| 严重性 | 类别 | 描述 | 影响 | 建议 |")
            lines.append("|:---|:---|:---|:---|:---|")
            for performance_issue in self.performance_issues:
                lines.append(
                    f"| {performance_issue.severity} | {performance_issue.category} | {performance_issue.description} | {performance_issue.impact} | {performance_issue.recommendation} |"
                )

        lines.extend(["", "---", ""])

        # 架构审查
        lines.extend(
            [
                "## 3. 架构审查",
                "",
            ]
        )

        if not self.architecture_issues:
            lines.append("未发现明显的架构问题。")
        else:
            lines.append("| 严重性 | 类别 | 描述 | 需要 ADR | 建议 |")
            lines.append("|:---|:---|:---|:---:|:---|")
            for architecture_issue in self.architecture_issues:
                adr = "是" if architecture_issue.adr_needed else "否"
                lines.append(
                    f"| {architecture_issue.severity} | {architecture_issue.category} | {architecture_issue.description} | {adr} | {architecture_issue.recommendation} |"
                )

        lines.extend(["", "---", ""])

        # 声明式规则检测结果
        def _collect_decl_issues(
            source: Sequence[_IssueLike],
            target: list[_IssueLike],
        ) -> None:
            for issue in source:
                if issue.description.startswith("[RT-"):
                    target.append(issue)

        all_issues = cast(list[_IssueLike], [])
        all_issues.extend(self.security_issues)
        all_issues.extend(self.performance_issues)
        all_issues.extend(self.architecture_issues)

        decl_issues = cast(list[_IssueLike], [])
        _collect_decl_issues(self.security_issues, decl_issues)
        _collect_decl_issues(self.performance_issues, decl_issues)
        _collect_decl_issues(self.architecture_issues, decl_issues)
        lines.extend(
            [
                "## 4. 声明式规则检测结果",
                "",
            ]
        )
        if not decl_issues:
            lines.append("未加载声明式规则或未检测到匹配项。")
        else:
            lines.append(f"共检测到 **{len(decl_issues)}** 条声明式规则命中：")
            lines.append("")
            lines.append("| 规则 ID | 严重性 | 描述 | 文件 | 建议 |")
            lines.append("|:---|:---|:---|:---|:---|")
            for issue in cast(Sequence[_IssueLike], decl_issues):  # type: ignore[assignment]
                # 从 description 中提取规则 ID，格式为 [RT-XXX-NNN]
                rule_id_match = re.match(r"\[(RT-[A-Z]+-\d+)\]", issue.description)
                rule_id = rule_id_match.group(1) if rule_id_match else "-"
                file_ref = getattr(issue, "file_path", None) or "-"
                if file_ref != "-":
                    file_ref = Path(file_ref).name
                    line_val = getattr(issue, "line", None)
                    if line_val:
                        file_ref = f"{file_ref}:{line_val}"
                lines.append(
                    f"| {rule_id} | {issue.severity} | {issue.description} | {file_ref} | {issue.recommendation} |"
                )

        lines.extend(["", "---", ""])

        # 改进建议
        lines.extend(
            [
                "## 5. 改进建议",
                "",
                "### 优先级 P0 (立即修复)",
                "",
            ]
        )

        p0_issues = cast(list[_IssueLike], [])
        for issue in cast(Sequence[_IssueLike], all_issues):  # type: ignore[assignment]
            if issue.severity in ("critical", "high"):
                p0_issues.append(issue)

        if not p0_issues:
            lines.append("无 P0 级别问题。")
        else:
            for idx, issue_item in enumerate(p0_issues, 1):
                issue_type = (
                    "安全"
                    if isinstance(issue_item, SecurityIssue)
                    else "性能" if isinstance(issue_item, PerformanceIssue) else "架构"
                )
                lines.append(f"{idx}. [{issue_type}] {issue_item.description}")
                lines.append(f"   - 建议: {issue_item.recommendation}")
                lines.append("")

        lines.extend(
            [
                "### 优先级 P1 (尽快修复)",
                "",
            ]
        )

        p1_issues = cast(list[_IssueLike], [])
        for issue in cast(Sequence[_IssueLike], all_issues):  # type: ignore[assignment]
            if issue.severity == "medium":
                p1_issues.append(issue)

        if not p1_issues:
            lines.append("无 P1 级别问题。")
        else:
            for idx, issue_item in enumerate(p1_issues, 1):
                issue_type = (
                    "安全"
                    if isinstance(issue_item, SecurityIssue)
                    else "性能" if isinstance(issue_item, PerformanceIssue) else "架构"
                )
                lines.append(f"{idx}. [{issue_type}] {issue_item.description}")
                lines.append(f"   - 建议: {issue_item.recommendation}")
                lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "pass_threshold": self.pass_threshold,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "total_score": self.total_score,
            "passed": self.passed,
            "scanned_files_count": self.scanned_files_count,
            "blocking_reasons": list(self.blocking_reasons),
            "security_issues": [item.to_dict() for item in self.security_issues],
            "performance_issues": [item.to_dict() for item in self.performance_issues],
            "architecture_issues": [item.to_dict() for item in self.architecture_issues],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RedTeamReport":
        security_payload = payload.get("security_issues")
        performance_payload = payload.get("performance_issues")
        architecture_payload = payload.get("architecture_issues")
        return cls(
            project_name=str(payload.get("project_name", "")),
            pass_threshold=_coerce_int(payload.get("pass_threshold"), 70),
            scanned_files_count=_coerce_int(payload.get("scanned_files_count"), -1),
            security_issues=[
                SecurityIssue.from_dict(item)
                for item in security_payload
                if isinstance(item, dict)
            ]
            if isinstance(security_payload, list)
            else [],
            performance_issues=[
                PerformanceIssue.from_dict(item)
                for item in performance_payload
                if isinstance(item, dict)
            ]
            if isinstance(performance_payload, list)
            else [],
            architecture_issues=[
                ArchitectureIssue.from_dict(item)
                for item in architecture_payload
                if isinstance(item, dict)
            ]
            if isinstance(architecture_payload, list)
            else [],
        )


@dataclass
class RedTeamEvidence:
    path: Path
    passed: bool
    total_score: int
    pass_threshold: int
    critical_count: int
    blocking_reasons: list[str] = field(default_factory=list)
    source_format: str = "json"


def load_persisted_redteam_report(
    project_dir: Path, project_name: str | None = None
) -> tuple[Path, RedTeamReport] | None:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    pattern = f"{project_name}-redteam.json" if project_name else "*-redteam.json"
    candidates = sorted(output_dir.glob(pattern))
    if not candidates:
        return None
    file_path = max(candidates, key=lambda path: path.stat().st_mtime)
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return file_path, RedTeamReport.from_dict(payload)


def load_redteam_evidence(
    project_dir: Path, project_name: str | None = None
) -> RedTeamEvidence | None:
    persisted = load_persisted_redteam_report(project_dir, project_name)
    if persisted is not None:
        file_path, report = persisted
        return RedTeamEvidence(
            path=file_path,
            passed=report.passed,
            total_score=report.total_score,
            pass_threshold=report.pass_threshold,
            critical_count=report.critical_count,
            blocking_reasons=list(report.blocking_reasons),
            source_format="json",
        )

    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    pattern = f"{project_name}-redteam.md" if project_name else "*-redteam.md"
    candidates = sorted(output_dir.glob(pattern))
    if not candidates:
        return None
    file_path = max(candidates, key=lambda path: path.stat().st_mtime)
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    critical_match = re.search(r"Critical 问题\*\*:\s*(\d+)", text)
    score_match = re.search(r"总分\*\*:\s*(\d+)/100", text)
    threshold_match = re.search(r"通过阈值\*\*:\s*(\d+)", text)
    critical_count = int(critical_match.group(1)) if critical_match else 0
    total_score = int(score_match.group(1)) if score_match else 0
    pass_threshold = int(threshold_match.group(1)) if threshold_match else 70
    status_passed = "未通过质量门禁" not in text and (
        "通过 - 质量良好" in text or "有条件通过" in text
    )
    if not score_match and status_passed:
        total_score = pass_threshold
    passed = "未通过质量门禁" not in text and critical_count == 0 and total_score >= pass_threshold
    blocking_reasons: list[str] = []
    if critical_count > 0:
        blocking_reasons.append(f"存在 {critical_count} 个 critical 问题")
    if total_score < pass_threshold:
        blocking_reasons.append(f"红队评分 {total_score} 低于阈值 {pass_threshold}")
    return RedTeamEvidence(
        path=file_path,
        passed=passed,
        total_score=total_score,
        pass_threshold=pass_threshold,
        critical_count=critical_count,
        blocking_reasons=blocking_reasons,
        source_format="markdown",
    )


class RedTeamReviewer:
    """红队审查器"""

    _CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".sql"}
    _SKIP_DIRS = {
        ".git",
        ".idea",
        ".vscode",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "output",
        ".super-dev",
        "logs",
        ".venv",
        "venv",
        ".tox",
        ".cache",
        "coverage",
        "htmlcov",
        ".next",
        ".nuxt",
        "out",
    }
    _PREFERRED_SCAN_DIRS = (
        "backend",
        "frontend",
        "src",
        "app",
        "server",
        "api",
        "services",
        "lib",
        "super_dev",
    )
    _MAX_SCAN_FILES = 220
    _MAX_FILE_SIZE = 300_000

    def __init__(self, project_dir: Path, name: str, tech_stack: dict):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.tech_stack = tech_stack
        self.platform = tech_stack.get("platform", "web")
        self.frontend = tech_stack.get("frontend", "react")
        self.backend = tech_stack.get("backend", "node")
        self.domain = tech_stack.get("domain", "")
        self._source_file_cache: list[tuple[Path, str]] | None = None
        self.enable_tool_scans = os.getenv(
            "SUPER_DEV_ENABLE_TOOL_SCANS", "1"
        ).strip().lower() not in {
            "0",
            "false",
            "no",
        }
        self._redteam_rules = self._load_redteam_rules()
        self._expert_rules = self._load_expert_rules()

    def _load_redteam_rules(self) -> list[dict[str, Any]]:
        """从 YAML 加载声明式红队规则"""
        rules_path = Path(__file__).parent / "rules" / "redteam_rules.yaml"
        if rules_path.exists():
            try:
                import yaml

                with open(rules_path, encoding="utf-8") as f:
                    data: object = yaml.safe_load(f)
                    if isinstance(data, dict):
                        rules = data.get("redteam_rules")
                        if isinstance(rules, list):
                            return cast(list[dict[str, Any]], rules)
            except Exception:
                pass
        return []

    def _load_expert_rules(self) -> list[str] | None:
        """尝试加载安全专家工具箱中的红队规则 ID 列表"""
        try:
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            security_toolkit = toolkits.get("SECURITY")
            if security_toolkit and hasattr(security_toolkit, "rules"):
                return security_toolkit.rules.redteam_rule_ids or None
        except Exception:
            pass
        return None

    def _scan_declarative_rules(
        self,
    ) -> tuple[list[SecurityIssue], list[PerformanceIssue], list[ArchitectureIssue]]:
        """使用声明式规则扫描源码文件，返回按类别分类的问题列表"""
        security_issues: list[SecurityIssue] = []
        performance_issues: list[PerformanceIssue] = []
        architecture_issues: list[ArchitectureIssue] = []

        if not self._redteam_rules:
            return security_issues, performance_issues, architecture_issues

        # 如果有专家工具箱规则 ID，只扫描匹配的规则子集
        active_rule_ids: set[str] | None = None
        if self._expert_rules:
            candidate_rule_ids = {
                str(rule.get("id", "")).strip()
                for rule in self._redteam_rules
                if str(rule.get("id", "")).strip()
            }
            expert_rule_ids = {
                str(item).strip() for item in self._expert_rules if str(item).strip()
            }
            # 自定义或测试注入规则时，如果和专家规则集完全不相交，不应把全部规则过滤掉。
            if candidate_rule_ids & expert_rule_ids:
                active_rule_ids = expert_rule_ids

        # 预编译规则的正则模式
        compiled_rules: list[tuple[dict, list[re.Pattern]]] = []
        for rule in self._redteam_rules:
            rule_id = rule.get("id", "")
            if active_rule_ids is not None and rule_id not in active_rule_ids:
                continue
            patterns = rule.get("patterns", [])
            compiled = []
            for pat in patterns:
                try:
                    compiled.append(re.compile(pat))
                except re.error:
                    continue
            if compiled or rule.get("check_type"):
                compiled_rules.append((rule, compiled))

        if not compiled_rules:
            return security_issues, performance_issues, architecture_issues

        issue_keys: set[tuple[str, str]] = set()

        for file_path, content in self._iter_source_files_with_content():
            if self._is_yaml_file(file_path):
                continue

            line_count = content.count("\n") + 1

            for rule, patterns in compiled_rules:
                rule_id = rule.get("id", "")
                rule_name = rule.get("name", rule_id)
                severity = rule.get("severity", "medium")
                category = rule.get("category", "security")
                description = rule.get("description", "")
                recommendation = rule.get("recommendation", "")
                cwe = rule.get("cwe")
                check_type = rule.get("check_type")

                # 文件行数检查（特殊规则类型）
                if check_type == "file_line_count":
                    max_lines = rule.get("check_config", {}).get("max_lines", 500)
                    if line_count > max_lines:
                        issue_key = (str(file_path), rule_id)
                        if issue_key in issue_keys:
                            continue
                        issue_keys.add(issue_key)
                        architecture_issues.append(
                            ArchitectureIssue(
                                severity=severity,
                                category="可维护性",
                                description=f"[{rule_id}] {rule_name}: {file_path.name} ({line_count} 行 > {max_lines})",
                                recommendation=recommendation,
                                adr_needed=True,
                                file_path=str(file_path),
                                line=1,
                            )
                        )
                    continue

                # 正则模式匹配
                for pattern in patterns:
                    match = pattern.search(content)
                    if not match:
                        continue
                    issue_key = (str(file_path), rule_id)
                    if issue_key in issue_keys:
                        break
                    issue_keys.add(issue_key)
                    line_no = self._line_number_from_offset(content, match.start())

                    if category == "security":
                        security_issues.append(
                            SecurityIssue(
                                severity=severity,
                                category=rule_name,
                                description=f"[{rule_id}] {description}: {file_path.name}:{line_no}",
                                recommendation=recommendation,
                                cwe=cwe,
                                file_path=str(file_path),
                                line=line_no,
                            )
                        )
                    elif category == "performance":
                        performance_issues.append(
                            PerformanceIssue(
                                severity=severity,
                                category=rule_name,
                                description=f"[{rule_id}] {description}: {file_path.name}:{line_no}",
                                recommendation=recommendation,
                                impact="声明式规则检测",
                                file_path=str(file_path),
                                line=line_no,
                            )
                        )
                    elif category == "architecture":
                        architecture_issues.append(
                            ArchitectureIssue(
                                severity=severity,
                                category=rule_name,
                                description=f"[{rule_id}] {description}: {file_path.name}:{line_no}",
                                recommendation=recommendation,
                                adr_needed=severity in ("critical", "high"),
                                file_path=str(file_path),
                                line=line_no,
                            )
                        )
                    break  # 每条规则每个文件只报一次

        return security_issues, performance_issues, architecture_issues

    def review(self) -> RedTeamReport:
        """执行完整红队审查"""
        report = RedTeamReport(project_name=self.name)

        # 记录扫描的源码文件数量
        try:
            source_files = self._iter_source_files_with_content()
            report.scanned_files_count = sum(
                1 for file_path, _content in source_files if not self._is_yaml_file(file_path)
            )
        except Exception:
            report.scanned_files_count = 0

        # 安全审查
        report.security_issues = self._review_security()

        # 性能审查
        report.performance_issues = self._review_performance()

        # 架构审查
        report.architecture_issues = self._review_architecture()

        # 声明式规则增量扫描
        decl_sec, decl_perf, decl_arch = self._scan_declarative_rules()
        report.security_issues.extend(decl_sec)
        report.performance_issues.extend(decl_perf)
        report.architecture_issues.extend(decl_arch)

        # 依赖安全扫描
        report.security_issues.extend(self._review_dependency_security())

        # API 安全扫描
        report.security_issues.extend(self._review_api_security())

        # 密钥泄漏深度扫描
        report.security_issues.extend(self._review_secrets_deep())

        return report

    # ------------------------------------------------------------------
    # Adversarial verification prompt generation
    # ------------------------------------------------------------------

    def generate_adversarial_review_prompt(self) -> str:
        """Generate a structured adversarial verification prompt.

        Combines existing red team check categories with the adversarial
        verification approach from review_agents (inspired by Claude Code's
        verification agent).  The returned prompt can be forwarded to the
        host AI for deeper, runtime-verified checks.
        """
        sections: list[str] = []

        # Header
        sections.append("# Adversarial Red Team Verification Prompt")
        sections.append("")
        sections.append(
            f"Project: **{self.name}** | Platform: {self.platform} | "
            f"Frontend: {self.frontend} | Backend: {self.backend}"
        )
        sections.append("")

        # Section 1 — existing red-team check categories
        sections.append("## 1. Red Team Check Categories")
        sections.append("")
        sections.append(
            "The following categories are already scanned by the static red "
            "team reviewer.  The host AI should use **runtime execution** to "
            "verify that no issues are missed."
        )
        sections.append("")
        sections.append("- Security: hardcoded credentials, injection, auth, CORS, secrets")
        sections.append("- Performance: sync-in-async, N+1 queries, large files")
        sections.append("- Architecture: test coverage, health endpoints, CI config, monoliths")
        sections.append("- Dependencies: supply-chain poisoning, loose versions, lockfiles")
        sections.append("- API: unauthed endpoints, rate limiting, versioning")
        sections.append("")

        # Section 2 — adversarial verification (from review_agents)
        if REVIEW_AGENTS_AVAILABLE:
            sections.append("## 2. Adversarial Verification Protocol")
            sections.append("")
            sections.append(ADVERSARIAL_VERIFICATION_PROMPT)
            sections.append("")
        else:
            sections.append("## 2. Adversarial Verification Protocol")
            sections.append("")
            sections.append("(review_agents module not available — using inline fallback)")
            sections.append("")
            sections.append("### Recognize Your Rationalizations")
            sections.append("")
            sections.append('- "The code looks correct" -> Reading is not verification. Run it.')
            sections.append(
                '- "Tests already pass" -> The implementer is an LLM, verify independently.'
            )
            sections.append('- "It is probably fine" -> "Probably" is not verified.')
            sections.append('- "This would take too long" -> Not your call.')
            sections.append("")

        # Section 3 — type-specific verification strategies
        sections.append("## 3. Type-Specific Verification Strategies")
        sections.append("")

        if self.frontend and self.frontend != "none":
            sections.append("### Frontend Verification")
            sections.append("")
            sections.append("1. Run `npm run build` / `npm run dev` and confirm zero errors")
            sections.append(
                "2. Open each route in a browser; check for blank pages, console errors"
            )
            sections.append("3. Test responsive breakpoints (mobile / tablet / desktop)")
            sections.append("4. Verify interactive elements: buttons, forms, modals actually work")
            sections.append("5. Check accessibility: keyboard navigation, screen reader labels")
            sections.append("6. Measure Lighthouse score (performance, a11y, best practices)")
            sections.append("")

        if self.backend and self.backend != "none":
            sections.append("### Backend Verification")
            sections.append("")
            sections.append("1. Start the server and confirm health endpoint responds 200")
            sections.append("2. Run the full test suite; failing tests = automatic FAIL")
            sections.append("3. Send malformed input to each endpoint (empty body, wrong types)")
            sections.append("4. Test concurrent requests to create-if-not-exists endpoints")
            sections.append("5. Verify auth: unauthenticated requests must return 401/403")
            sections.append("6. Check database migrations are idempotent")
            sections.append("")

        # CLI verification is always relevant for super-dev itself
        sections.append("### CLI Verification")
        sections.append("")
        sections.append("1. Run `--help` for every subcommand; must not crash")
        sections.append("2. Run with invalid args; must show user-friendly error, not traceback")
        sections.append("3. Test with missing config file / empty project directory")
        sections.append("4. Verify exit codes: 0 for success, non-zero for failure")
        sections.append("")

        if self.tech_stack.get("database") and self.tech_stack.get("database") != "none":
            sections.append("### Database Verification")
            sections.append("")
            sections.append("1. Run migrations on a clean database; must complete without error")
            sections.append("2. Run migrations twice; must be idempotent")
            sections.append("3. Test rollback of the latest migration")
            sections.append(
                "4. Check for missing indexes on foreign keys and frequent query columns"
            )
            sections.append("5. Verify connection pooling and timeout configuration")
            sections.append("")

        # Section 4 — output format
        sections.append("## 4. Output Format")
        sections.append("")
        sections.append("For each check:")
        sections.append("```")
        sections.append("Command run: <exact command>")
        sections.append("Output observed: <stdout/stderr snippet>")
        sections.append("Result: PASS / FAIL / SKIP (with reason)")
        sections.append("```")
        sections.append("")
        sections.append("Final: `VERDICT: PASS` or `VERDICT: FAIL` or `VERDICT: PARTIAL`")

        return "\n".join(sections)

    def get_parallel_review_prompts(
        self,
        description: str,
        files: list[str] | None = None,
        diff_content: str = "",
    ) -> dict[str, str] | None:
        """Delegate to :func:`build_parallel_review_prompt` when available.

        Returns ``None`` if the review_agents module is not importable.
        """
        if not REVIEW_AGENTS_AVAILABLE:
            return None
        return build_parallel_review_prompt(
            change_description=description,
            files_changed=files,
            diff_content=diff_content,
        )

    def _review_security(self) -> list[SecurityIssue]:
        """安全审查"""
        issues: list[SecurityIssue] = []
        issue_keys: set[tuple[str, str]] = set()

        # 1. 扫描代码中的高风险模式（真实信号）
        secret_pattern = re.compile(
            r'(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*["\']([^"\']{6,})["\']'
        )
        dangerous_rules = [
            (
                "命令执行",
                re.compile(r"\bsubprocess\.(run|call|Popen)\([^)]*shell\s*=\s*True"),
                "CWE-78",
                "避免 shell=True，改为参数数组执行并进行输入白名单校验",
            ),
            (
                "动态执行",
                re.compile(r"\b(eval|exec)\s*\("),
                "CWE-95",
                "避免 eval/exec，使用安全解析器或受限表达式引擎",
            ),
            (
                "动态命令",
                re.compile(r"child_process\.exec\s*\("),
                "CWE-78",
                "改用 execFile/spawn 并限定允许命令集合",
            ),
            (
                "SQL 注入",
                re.compile(
                    r"(?i)(select\s+.+\s+from|insert\s+into|update\s+\w+\s+set|delete\s+from)[^\n]{0,160}\+"
                ),
                "CWE-89",
                "避免字符串拼接 SQL，统一使用参数化查询/ORM",
            ),
        ]

        for file_path, content in self._iter_source_files_with_content():
            if self._is_yaml_file(file_path):
                # 对配置文件只做轻量提示，不做高危判定
                continue

            # 硬编码凭据
            for match in secret_pattern.finditer(content):
                value = match.group(2).strip()
                if self._looks_like_placeholder(value):
                    continue
                line_no = self._line_number_from_offset(content, match.start())
                issue_key = (str(file_path), "硬编码凭据")
                if issue_key in issue_keys:
                    continue
                issue_keys.add(issue_key)
                issues.append(
                    SecurityIssue(
                        severity="high",
                        category="硬编码凭据",
                        description=f"检测到疑似硬编码敏感信息: {file_path.name}:{line_no}",
                        recommendation="将密钥迁移到环境变量或密钥管理服务（Vault/KMS）",
                        cwe="CWE-798",
                        file_path=str(file_path),
                        line=line_no,
                    )
                )
                break

            for category, pattern, cwe, recommendation in dangerous_rules:
                rule_match = pattern.search(content)
                if not rule_match:
                    continue
                issue_key = (str(file_path), category)
                if issue_key in issue_keys:
                    continue
                issue_keys.add(issue_key)
                line_no = self._line_number_from_offset(content, rule_match.start())
                issues.append(
                    SecurityIssue(
                        severity="high",
                        category=category,
                        description=f"检测到高风险代码模式: {file_path.name}:{line_no}",
                        recommendation=recommendation,
                        cwe=cwe,
                        file_path=str(file_path),
                        line=line_no,
                    )
                )

        # 2. 框架级最低安全基线（中低风险建议）
        if self.backend != "none":
            issues.append(
                SecurityIssue(
                    severity="advisory",
                    category="认证",
                    description="建议统一鉴权中间件并对关键接口做细粒度权限控制",
                    recommendation="采用 JWT/Session + RBAC/ABAC，补充关键操作审计日志",
                    cwe="CWE-287",
                )
            )
            issues.append(
                SecurityIssue(
                    severity="advisory",
                    category="速率限制",
                    description="建议对登录、注册、重置密码等敏感接口启用限流",
                    recommendation="采用令牌桶/滑动窗口算法并记录触发日志",
                    cwe="CWE-770",
                )
            )

        # 领域特定安全
        if self.domain == "fintech":
            issues.extend(
                [
                    SecurityIssue(
                        severity="high",
                        category="PCI-DSS",
                        description="金融场景需完成支付数据合规评估与密钥分级管理",
                        recommendation="补充 PCI-DSS 控制项自检并输出合规矩阵",
                        cwe="CWE-320",
                    ),
                    SecurityIssue(
                        severity="high",
                        category="审计",
                        description="金融核心流程建议实施不可篡改审计链路",
                        recommendation="关键交易日志上链或做 WORM 存储并定期核验",
                        cwe="CWE-778",
                    ),
                ]
            )
        elif self.domain == "medical":
            issues.extend(
                [
                    SecurityIssue(
                        severity="high",
                        category="HIPAA",
                        description="医疗数据必须符合 HIPAA 标准",
                        recommendation="实施数据加密、访问控制、审计日志",
                        cwe="CWE-200",
                    ),
                ]
            )

        if self.enable_tool_scans:
            issues.extend(self._run_optional_security_tool_scans())

        return issues

    def _review_performance(self) -> list[PerformanceIssue]:
        """性能审查"""
        issues: list[PerformanceIssue] = []
        issue_keys: set[tuple[str, str]] = set()

        async_requests_pattern = re.compile(
            r"async\s+def[\s\S]{0,300}requests\.(get|post|put|delete)\("
        )
        n_plus_one_pattern = re.compile(r"for\s+.+:\s*[\r\n]+\s*.+\.(find|get|query|select)\(")

        for file_path, content in self._iter_source_files_with_content():
            line_count = content.count("\n") + 1

            async_match = async_requests_pattern.search(content)
            if async_match and (str(file_path), "API") not in issue_keys:
                issue_keys.add((str(file_path), "API"))
                line_no = self._line_number_from_offset(content, async_match.start())
                issues.append(
                    PerformanceIssue(
                        severity="high",
                        category="API",
                        description=f"异步上下文中检测到同步 HTTP 调用: {file_path.name}:{line_no}",
                        recommendation="在 async 流程中使用异步 HTTP 客户端（httpx.AsyncClient/aiohttp）",
                        impact="阻塞事件循环，增加高并发下请求延迟",
                        file_path=str(file_path),
                        line=line_no,
                    )
                )

            n_plus_one_match = n_plus_one_pattern.search(content)
            if n_plus_one_match and (str(file_path), "数据库") not in issue_keys:
                issue_keys.add((str(file_path), "数据库"))
                line_no = self._line_number_from_offset(content, n_plus_one_match.start())
                issues.append(
                    PerformanceIssue(
                        severity="low",
                        category="数据库",
                        description=f"疑似 N+1 查询模式: {file_path.name}:{line_no}",
                        recommendation="批量查询或预加载关联数据，减少循环内 DB 调用",
                        impact="高数据量场景响应时间线性恶化",
                        file_path=str(file_path),
                        line=line_no,
                    )
                )

            if line_count > 1200:
                issues.append(
                    PerformanceIssue(
                        severity="low",
                        category="代码结构",
                        description=f"超大文件可能影响维护与性能优化: {file_path.name} ({line_count} 行)",
                        recommendation="拆分模块并隔离热点路径，便于单点性能调优",
                        impact="性能问题定位与重构成本升高",
                    )
                )

        # 基线建议
        if self.backend != "none":
            issues.append(
                PerformanceIssue(
                    severity="low",
                    category="数据库",
                    description="建议关键查询路径补齐索引与慢查询观测",
                    recommendation="建立慢查询阈值与索引基线，持续回归",
                    impact="降低接口尾延迟并提升吞吐稳定性",
                )
            )
        if self.frontend != "none":
            issues.append(
                PerformanceIssue(
                    severity="low",
                    category="前端",
                    description="建议实施代码分割与静态资源缓存策略",
                    recommendation="按路由拆包并配置长期缓存 + 指纹文件名",
                    impact="首屏加载与重复访问体验提升",
                )
            )

        return issues

    def _review_architecture(self) -> list[ArchitectureIssue]:
        """架构审查"""
        issues: list[ArchitectureIssue] = []
        source_files = self._iter_source_files_with_content()

        if not self._has_test_assets(source_files):
            issues.append(
                ArchitectureIssue(
                    severity="high",
                    category="可维护性",
                    description="未检测到 tests 目录，回归保障不足",
                    recommendation="建立单元/集成测试目录并纳入 CI 必跑策略",
                    adr_needed=False,
                )
            )

        has_health_endpoint = False
        for _file_path, content in source_files:
            if re.search(r"/health|health_check|healthcheck", content, re.IGNORECASE):
                has_health_endpoint = True
                break

        if self.backend != "none" and not has_health_endpoint:
            issues.append(
                ArchitectureIssue(
                    severity="medium",
                    category="可靠性",
                    description="未检测到健康检查端点标记",
                    recommendation="增加 /health 与 /ready 端点并接入部署探针",
                    adr_needed=False,
                )
            )

        ci_files = [
            self.project_dir / ".github" / "workflows" / "ci.yml",
            self.project_dir / ".gitlab-ci.yml",
            self.project_dir / "Jenkinsfile",
            self.project_dir / ".azure-pipelines.yml",
            self.project_dir / "bitbucket-pipelines.yml",
        ]
        if not any(p.exists() for p in ci_files):
            issues.append(
                ArchitectureIssue(
                    severity="low",
                    category="工程化",
                    description="未检测到 CI/CD 主流程配置",
                    recommendation="补齐至少一套 CI 流水线并将质量门禁前置",
                    adr_needed=True,
                )
            )

        largest_file = None
        largest_lines = 0
        for file_path, content in source_files:
            line_count = content.count("\n") + 1
            if line_count > largest_lines:
                largest_file = file_path
                largest_lines = line_count
        if largest_file and largest_lines > 2000:
            issues.append(
                ArchitectureIssue(
                    severity="medium",
                    category="可维护性",
                    description=f"检测到超大单体文件: {largest_file.name} ({largest_lines} 行)",
                    recommendation="按业务边界拆分模块并定义明确接口契约",
                    adr_needed=True,
                    file_path=str(largest_file),
                    line=1,
                )
            )
        elif largest_file and largest_lines > 1200:
            issues.append(
                ArchitectureIssue(
                    severity="medium",
                    category="可维护性",
                    description=f"检测到大文件: {largest_file.name} ({largest_lines} 行)",
                    recommendation="逐步拆分高复杂度模块并补充针对性测试",
                    adr_needed=True,
                    file_path=str(largest_file),
                    line=1,
                )
            )

        return issues

    def _iter_source_files_with_content(self) -> list[tuple[Path, str]]:
        if self._source_file_cache is not None:
            return self._source_file_cache

        files: list[tuple[Path, str]] = []
        seen: set[Path] = set()

        # 优先扫描常见源码目录，保证信噪比
        for root_name in self._PREFERRED_SCAN_DIRS:
            root = self.project_dir / root_name
            if not root.exists() or not root.is_dir():
                continue
            self._collect_scannable_files(root, files, seen)
            if len(files) >= self._MAX_SCAN_FILES:
                self._source_file_cache = files
                return files

        # 回退到全项目扫描，避免目录命名不标准导致漏检
        if len(files) < self._MAX_SCAN_FILES:
            self._collect_scannable_files(self.project_dir, files, seen)

        self._source_file_cache = files
        return files

    def _collect_scannable_files(
        self, root: Path, files: list[tuple[Path, str]], seen: set[Path]
    ) -> None:
        for dirpath, dirnames, filenames in os.walk(root):
            # 预剪枝，避免进入大型依赖目录
            dirnames[:] = [d for d in dirnames if not self._should_skip_dir(d)]

            for filename in filenames:
                if len(files) >= self._MAX_SCAN_FILES:
                    return

                path = Path(dirpath) / filename
                if not self._is_scannable_file(path):
                    continue

                try:
                    resolved = path.resolve()
                except Exception:
                    resolved = path
                if resolved in seen:
                    continue
                seen.add(resolved)

                try:
                    if path.stat().st_size > self._MAX_FILE_SIZE:
                        continue
                except OSError:
                    continue

                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                files.append((path, content))

    def _should_skip_dir(self, dirname: str) -> bool:
        if dirname in self._SKIP_DIRS:
            return True
        return dirname.startswith(".") and dirname not in {".github"}

    def _is_scannable_file(self, path: Path) -> bool:
        if self._is_test_file(path):
            return False
        suffix = path.suffix.lower()
        return suffix in self._CODE_EXTENSIONS or self._is_yaml_file(path)

    def _is_yaml_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".yml", ".yaml"}

    def _is_test_file(self, path: Path) -> bool:
        lowered_parts = {part.lower() for part in path.parts}
        if "tests" in lowered_parts or "__tests__" in lowered_parts:
            return True

        name = path.name.lower()
        if re.match(r"^test_.*\.py$", name):
            return True
        if re.match(r".*_test\.py$", name):
            return True
        if re.match(r".*\.test\.(js|ts|jsx|tsx)$", name):
            return True
        if re.match(r".*\.spec\.(js|ts|jsx|tsx)$", name):
            return True
        return False

    def _looks_like_placeholder(self, value: str) -> bool:
        lowered = value.lower()
        placeholder_markers = (
            "your-",
            "your_",
            "your api",
            "example",
            "placeholder",
            "changeme",
            "change_me",
            "todo",
            "<value>",
            "*****",
            "dummy",
        )
        if any(marker in lowered for marker in placeholder_markers):
            return True
        if lowered in {"password", "secret", "token", "api_key", "your_api_key_here"}:
            return True
        return False

    def _line_number_from_offset(self, content: str, start: int) -> int:
        return content.count("\n", 0, start) + 1

    def _has_test_assets(self, source_files: list[tuple[Path, str]]) -> bool:
        if (self.project_dir / "tests").exists():
            return True
        test_name_patterns = [
            re.compile(r"^test_.*\.py$"),
            re.compile(r".*_test\.py$"),
            re.compile(r".*\.test\.(js|ts|jsx|tsx)$"),
            re.compile(r".*\.spec\.(js|ts|jsx|tsx)$"),
        ]

        # 优先基于文件系统快速判断（独立于漏洞扫描的文件过滤策略）
        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [d for d in dirnames if not self._should_skip_dir(d)]
            for name in filenames:
                if any(pattern.match(name) for pattern in test_name_patterns):
                    return True

        for file_path, _ in source_files:
            name = file_path.name
            if any(pattern.match(name) for pattern in test_name_patterns):
                return True
        return False

    def _run_optional_security_tool_scans(self) -> list[SecurityIssue]:
        issues: list[SecurityIssue] = []
        issues.extend(self._scan_with_bandit())
        issues.extend(self._scan_with_semgrep())
        issues.extend(self._scan_with_npm_audit())
        return issues

    def _scan_with_bandit(self) -> list[SecurityIssue]:
        if self.backend != "python":
            return []

        bandit_exec = shutil.which("bandit")
        if not bandit_exec:
            return []

        targets = self._discover_bandit_targets()
        if not targets:
            return []

        result = self._run_command(
            [bandit_exec, "-r", *targets, "-f", "json", "-q"],
            timeout=180,
        )
        if result["timed_out"]:
            return [
                SecurityIssue(
                    severity="medium",
                    category="Bandit",
                    description="Bandit 扫描超时，建议拆分扫描范围或增加超时时间",
                    recommendation="将 Bandit 拆分为增量扫描并在 CI 中并行执行",
                    cwe="CWE-693",
                )
            ]

        stdout = str(result["stdout"] or "")
        if not stdout.strip():
            return []

        try:
            payload = json.loads(stdout)
        except Exception:
            return []

        findings = payload.get("results", [])
        issues: list[SecurityIssue] = []
        for finding in findings[:10]:
            severity = self._map_tool_severity(str(finding.get("issue_severity", "medium")))
            file_name = str(finding.get("filename", "unknown"))
            line_no = finding.get("line_number")
            issue_text = str(finding.get("issue_text", "Bandit 发现潜在安全风险"))
            cwe_data = finding.get("issue_cwe", {})
            cwe_id = None
            if isinstance(cwe_data, dict) and cwe_data.get("id"):
                cwe_id = f"CWE-{cwe_data.get('id')}"
            issues.append(
                SecurityIssue(
                    severity=severity,
                    category="Bandit",
                    description=f"Bandit: {issue_text} ({Path(file_name).name}:{line_no})",
                    recommendation="参考 Bandit 建议修复并补充安全回归测试",
                    cwe=cwe_id,
                    file_path=file_name,
                    line=int(line_no) if isinstance(line_no, int) else None,
                )
            )
        return issues

    def _scan_with_semgrep(self) -> list[SecurityIssue]:
        semgrep_exec = shutil.which("semgrep")
        if not semgrep_exec:
            return []

        result = self._run_command(
            [
                semgrep_exec,
                "--config",
                "auto",
                "--json",
                "--quiet",
                "--metrics=off",
                ".",
            ],
            timeout=240,
        )
        if result["timed_out"]:
            return []

        stdout = str(result["stdout"] or "")
        if not stdout.strip():
            return []

        try:
            payload = json.loads(stdout)
        except Exception:
            return []

        matches = payload.get("results", [])
        issues: list[SecurityIssue] = []
        for finding in matches[:12]:
            extra = finding.get("extra", {}) if isinstance(finding.get("extra"), dict) else {}
            severity = self._map_tool_severity(str(extra.get("severity", "medium")))
            message = str(extra.get("message", "Semgrep 检测到潜在风险"))
            path = str(finding.get("path", "unknown"))
            start = finding.get("start", {})
            line_no = start.get("line") if isinstance(start, dict) else None
            issue_type = str(finding.get("check_id", "semgrep.rule"))
            issues.append(
                SecurityIssue(
                    severity=severity,
                    category="Semgrep",
                    description=f"Semgrep({issue_type}): {message}",
                    recommendation="按规则建议修复并补充针对性测试",
                    cwe=None,
                    file_path=path,
                    line=int(line_no) if isinstance(line_no, int) else None,
                )
            )
        return issues

    def _scan_with_npm_audit(self) -> list[SecurityIssue]:
        npm_exec = shutil.which("npm")
        if not npm_exec:
            return []

        issues: list[SecurityIssue] = []
        for target in (self.project_dir / "frontend", self.project_dir / "backend"):
            package_json = target / "package.json"
            if not package_json.exists():
                continue

            result = self._run_command(
                [npm_exec, "--prefix", str(target), "audit", "--json"],
                timeout=240,
            )
            if result["timed_out"]:
                continue

            stdout = str(result["stdout"] or "")
            if not stdout.strip():
                continue

            try:
                payload = json.loads(stdout)
            except Exception:
                continue

            metadata = (
                payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
            )
            vuln = (
                metadata.get("vulnerabilities", {})
                if isinstance(metadata.get("vulnerabilities"), dict)
                else {}
            )
            critical = int(vuln.get("critical", 0) or 0)
            high = int(vuln.get("high", 0) or 0)
            if critical <= 0 and high <= 0:
                continue

            severity = "critical" if critical > 0 else "high"
            issues.append(
                SecurityIssue(
                    severity=severity,
                    category="依赖漏洞",
                    description=f"{target.name} 依赖存在漏洞: critical={critical}, high={high}",
                    recommendation="执行 npm audit fix，并升级高危依赖版本后回归验证",
                    cwe="CWE-1104",
                    file_path=str(package_json),
                    line=None,
                )
            )

        return issues

    def _discover_bandit_targets(self) -> list[str]:
        candidates = ["super_dev", "backend", "src", "app", "server", "api", "services"]
        targets: list[str] = []
        for item in candidates:
            path = self.project_dir / item
            if path.exists() and path.is_dir():
                targets.append(str(path))
        return targets

    def _map_tool_severity(self, raw: str) -> str:
        value = raw.strip().lower()
        if value in {"error", "critical"}:
            return "critical"
        if value in {"warning", "high"}:
            return "high"
        if value in {"info", "low"}:
            return "low"
        return "medium"

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

    # ------------------------------------------------------------------
    # 依赖安全扫描
    # ------------------------------------------------------------------

    # 历史投毒/恶意包黑名单（npm 生态）
    _KNOWN_MALICIOUS_NPM_PACKAGES: set[str] = {
        "event-stream",
        "ua-parser-js",
        "coa",
        "rc",
        "colors",
        "faker",
        "flatmap-stream",
        "left-pad",
        "crossenv",
        "mongose",
        "babelcli",
        "d3.js",
        "gruntcli",
        "http-proxy.js",
        "jquery.js",
        "mariadb",
        "mysqljs",
        "node-hierarchicalsettings",
        "node-opencv",
        "node-opensl",
        "node-openssl",
        "nodecaffe",
        "nodefabric",
        "nodeffmpeg",
        "nodemailer-js",
        "noderequest",
        "nodesass",
        "nodesqlite",
        "shadowsock",
        "smb",
        "sqliter",
        "sqlserver",
        "tkinter",
    }

    # PyPI 已知恶意包（供应链攻击案例）
    _KNOWN_MALICIOUS_PYPI_PACKAGES: set[str] = {
        "python3-dateutil",
        "jeIlyfish",
        "python-sqlite",
        "libpeshka",
        "libari",
        "colourfull",
        "coloramma",
        "reqeusts",
        "beautifulsup4",
        "crytpography",
        "nmap-python",
        "opencv-python4",
        "openvc-python",
        "python-mongo",
        "setuptool",
    }

    def _review_dependency_security(self) -> list[SecurityIssue]:
        """依赖安全深度扫描：投毒检测、版本锁定、lockfile 验证。"""
        issues: list[SecurityIssue] = []

        # --- npm 生态检查 ---
        for pkg_json_path in self._find_package_json_files():
            try:
                pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            all_deps: dict[str, str] = {}
            for dep_key in (
                "dependencies",
                "devDependencies",
                "peerDependencies",
                "optionalDependencies",
            ):
                dep_section = pkg_data.get(dep_key, {})
                if isinstance(dep_section, dict):
                    all_deps.update(dep_section)

            # 检查是否引用了已知恶意包
            for pkg_name in all_deps:
                lowered_name = pkg_name.lower().strip()
                if lowered_name in self._KNOWN_MALICIOUS_NPM_PACKAGES:
                    issues.append(
                        SecurityIssue(
                            severity="critical",
                            category="供应链投毒",
                            description=(
                                f"依赖 '{pkg_name}' 属于已知恶意/投毒包: " f"{pkg_json_path.name}"
                            ),
                            recommendation=(
                                f"立即移除 '{pkg_name}'，检查 lockfile 历史和 postinstall 脚本，"
                                "确认无远程载荷执行"
                            ),
                            cwe="CWE-1357",
                            file_path=str(pkg_json_path),
                        )
                    )

            # 检查版本是否过于宽松（>=、>、*、latest）
            loose_deps: list[str] = []
            for pkg_name, version_spec in all_deps.items():
                if not isinstance(version_spec, str):
                    continue
                version_spec_stripped = version_spec.strip()
                if version_spec_stripped in ("*", "latest", ""):
                    loose_deps.append(f"{pkg_name}@{version_spec_stripped or '(empty)'}")
                elif version_spec_stripped.startswith(">=") or version_spec_stripped.startswith(
                    ">"
                ):
                    loose_deps.append(f"{pkg_name}@{version_spec_stripped}")

            if loose_deps:
                sample = loose_deps[:5]
                remaining = len(loose_deps) - len(sample)
                desc_extra = f" (及其他 {remaining} 个)" if remaining > 0 else ""
                issues.append(
                    SecurityIssue(
                        severity="medium",
                        category="版本锁定",
                        description=(
                            f"检测到 {len(loose_deps)} 个宽松版本范围依赖: "
                            f"{', '.join(sample)}{desc_extra} ({pkg_json_path.name})"
                        ),
                        recommendation="使用精确版本号（^x.y.z 或 =x.y.z）并保持 lockfile 同步",
                        cwe="CWE-1104",
                        file_path=str(pkg_json_path),
                    )
                )

            # 检查 lockfile 是否存在
            pkg_dir = pkg_json_path.parent
            has_lockfile = any(
                (pkg_dir / lockname).exists()
                for lockname in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb")
            )
            if not has_lockfile:
                issues.append(
                    SecurityIssue(
                        severity="medium",
                        category="Lockfile 缺失",
                        description=(
                            f"未检测到 lockfile (package-lock.json/yarn.lock/pnpm-lock.yaml): "
                            f"{pkg_json_path.parent.name}/"
                        ),
                        recommendation=(
                            "生成并提交 lockfile 以确保依赖版本可复现，" "防止中间人替换"
                        ),
                        cwe="CWE-1104",
                        file_path=str(pkg_json_path),
                    )
                )

        # --- Python 生态检查 ---
        pypi_deps = self._collect_python_dependencies()
        for dep_name, dep_info in pypi_deps.items():
            lowered_name = dep_name.lower().strip()
            if lowered_name in self._KNOWN_MALICIOUS_PYPI_PACKAGES:
                issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="供应链投毒",
                        description=(
                            f"Python 依赖 '{dep_name}' 属于已知恶意/投毒包 "
                            f"({dep_info.get('source', 'unknown')})"
                        ),
                        recommendation=(
                            f"立即移除 '{dep_name}'，检查安装后脚本和环境变量泄露，"
                            "核实包名拼写是否正确"
                        ),
                        cwe="CWE-1357",
                        file_path=dep_info.get("file"),
                    )
                )

            # 检查 Python 依赖版本是否过于宽松
            version_spec = dep_info["version"] or ""
            if version_spec and (">=" in version_spec and "," not in version_spec):
                issues.append(
                    SecurityIssue(
                        severity="low",
                        category="版本锁定",
                        description=(
                            f"Python 依赖 '{dep_name}' 版本范围过于宽松: {version_spec} "
                            f"({dep_info.get('source', 'unknown')})"
                        ),
                        recommendation="使用上限约束（如 >=1.0,<2.0）或 pin 精确版本",
                        cwe="CWE-1104",
                        file_path=dep_info.get("file"),
                    )
                )

        # 检查 Python lockfile
        python_lock_files = ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.txt")
        has_python_lock = any(
            (self.project_dir / lockname).exists() for lockname in python_lock_files
        )
        pyproject_exists = (self.project_dir / "pyproject.toml").exists()
        if pyproject_exists and not has_python_lock:
            issues.append(
                SecurityIssue(
                    severity="medium",
                    category="Lockfile 缺失",
                    description="Python 项目未检测到依赖锁定文件 (uv.lock/poetry.lock/Pipfile.lock)",
                    recommendation="使用 uv lock / poetry lock / pip-compile 生成锁定文件并提交版本控制",
                    cwe="CWE-1104",
                    file_path=str(self.project_dir / "pyproject.toml"),
                )
            )

        # --- 依赖安全评分 ---
        dep_score = 100
        for issue in issues:
            if issue.severity == "critical":
                dep_score -= 25
            elif issue.severity == "high":
                dep_score -= 15
            elif issue.severity == "medium":
                dep_score -= 8
            else:
                dep_score -= 3
        dep_score = max(0, dep_score)

        # 如果扫描发现了问题且评分低于 60，补充一条汇总
        if issues and dep_score < 60:
            issues.append(
                SecurityIssue(
                    severity="high",
                    category="依赖安全汇总",
                    description=f"依赖安全评分: {dep_score}/100，存在 {len(issues)} 个供应链风险项",
                    recommendation="优先修复 critical/high 级别的供应链问题后重新扫描",
                    cwe="CWE-1104",
                )
            )

        return issues

    def _find_package_json_files(self) -> list[Path]:
        """在项目中查找 package.json 文件（排除 node_modules）。"""
        results: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [
                d for d in dirnames if d not in {"node_modules", ".git", "dist", "build", ".next"}
            ]
            if "package.json" in filenames:
                results.append(Path(dirpath) / "package.json")
            if len(results) >= 20:
                break
        return results

    def _collect_python_dependencies(self) -> dict[str, dict[str, str | None]]:
        """收集 Python 项目的依赖信息（从 pyproject.toml 和 requirements*.txt）。"""
        deps: dict[str, dict[str, str | None]] = {}

        # 从 pyproject.toml 解析
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                # 简化解析：匹配 dependencies 列表中的包名
                dep_pattern = re.compile(r'"([a-zA-Z0-9_-]+)\s*([><=!~]+[^"]*)?(?:\[.*?\])?"')
                in_deps = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("dependencies") and "=" in stripped:
                        in_deps = True
                        continue
                    if in_deps:
                        if stripped == "]":
                            in_deps = False
                            continue
                        match = dep_pattern.search(stripped)
                        if match:
                            pkg_name = match.group(1)
                            version_spec = match.group(2) or ""
                            deps[pkg_name] = {
                                "version": version_spec,
                                "source": "pyproject.toml",
                                "file": str(pyproject_path),
                            }
            except Exception:
                pass

        # 从 requirements*.txt 解析
        for req_file in self.project_dir.glob("requirements*.txt"):
            try:
                for line in req_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    match = re.match(r"^([a-zA-Z0-9_-]+)\s*([><=!~]+.*)?$", line)
                    if match:
                        pkg_name = match.group(1)
                        version_spec = match.group(2) or ""
                        if pkg_name not in deps:
                            deps[pkg_name] = {
                                "version": version_spec,
                                "source": req_file.name,
                                "file": str(req_file),
                            }
            except Exception:
                continue

        return deps

    # ------------------------------------------------------------------
    # API 安全扫描
    # ------------------------------------------------------------------

    # 常见未认证端点路径模式（通常不应公开的接口）
    _SENSITIVE_UNAUTH_PATTERNS: list[tuple[str, str]] = [
        (
            r"(?:@app\.|@router\.)(get|post|put|delete|patch)\s*\(\s*['\"]/(admin|internal|debug|metrics|graphql)",
            "敏感路径可能缺少认证",
        ),
        (
            r"router\.(get|post|put|delete|patch)\s*\(\s*['\"]/(admin|internal|debug)",
            "Express 敏感路由可能缺少认证中间件",
        ),
    ]

    # CORS 宽松配置模式
    _CORS_WILDCARD_PATTERNS: list[re.Pattern] = [
        re.compile(r"""allow_origins\s*=\s*\[\s*["']\*["']\s*\]"""),
        re.compile(r"""cors\s*\(\s*\{\s*origin\s*:\s*["']\*["']"""),
        re.compile(r"""Access-Control-Allow-Origin['"]\s*[,:]\s*["']\*["']"""),
        re.compile(r"""CORS_ORIGIN_ALLOW_ALL\s*=\s*True"""),
        re.compile(r"""CORS_ALLOWED_ORIGINS\s*=\s*\[\s*["']\*["']\s*\]"""),
    ]

    def _review_api_security(self) -> list[SecurityIssue]:
        """API 安全深度扫描：认证覆盖、速率限制、CORS、版本控制。"""
        issues: list[SecurityIssue] = []
        issue_keys: set[str] = set()

        has_rate_limit = False
        has_api_versioning = False
        has_cors_config = False
        unauth_endpoints: list[dict[str, str]] = []

        rate_limit_patterns = [
            re.compile(r"rate[_-]?limit", re.IGNORECASE),
            re.compile(r"throttl", re.IGNORECASE),
            re.compile(r"express-rate-limit"),
            re.compile(r"slowapi|Limiter|RateLimitMiddleware", re.IGNORECASE),
            re.compile(r"@rate_limit|@throttle", re.IGNORECASE),
        ]

        api_version_patterns = [
            re.compile(r"""['"]/api/v\d+"""),
            re.compile(r"""prefix\s*=\s*['"]/?v\d+"""),
            re.compile(r"""API_VERSION|api[_-]version""", re.IGNORECASE),
            re.compile(r"""versioning_class\s*="""),
        ]

        # 认证中间件检测
        auth_middleware_patterns = [
            re.compile(
                r"auth[_-]?middleware|authenticate|isAuthenticated|requireAuth|verify[_-]?token|jwt[_-]?required|login[_-]?required",
                re.IGNORECASE,
            ),
            re.compile(
                r"@requires_auth|@auth_required|@jwt_required|@permission_required", re.IGNORECASE
            ),
            re.compile(r"passport\.authenticate|guards?\s*:\s*\[", re.IGNORECASE),
            re.compile(r"Depends\s*\(\s*get_current_user", re.IGNORECASE),
        ]

        for file_path, content in self._iter_source_files_with_content():
            if self._is_yaml_file(file_path):
                continue

            # 速率限制检测
            if not has_rate_limit:
                for pattern in rate_limit_patterns:
                    if pattern.search(content):
                        has_rate_limit = True
                        break

            # API 版本控制检测
            if not has_api_versioning:
                for pattern in api_version_patterns:
                    if pattern.search(content):
                        has_api_versioning = True
                        break

            # CORS 配置检测
            if re.search(r"cors|CORS|Access-Control", content):
                has_cors_config = True
                for pattern in self._CORS_WILDCARD_PATTERNS:
                    if pattern.search(content):
                        key = f"cors-wildcard:{file_path}"
                        if key not in issue_keys:
                            issue_keys.add(key)
                            line_no = 0
                            match = pattern.search(content)
                            if match:
                                line_no = self._line_number_from_offset(content, match.start())
                            issues.append(
                                SecurityIssue(
                                    severity="high",
                                    category="CORS 配置",
                                    description=f"检测到 CORS 通配符配置 (allow_origins=*): {file_path.name}:{line_no}",
                                    recommendation="限制 CORS 允许域名为实际前端域名列表，生产环境禁止使用通配符",
                                    cwe="CWE-942",
                                    file_path=str(file_path),
                                    line=line_no,
                                )
                            )
                        break

            # 未认证敏感端点检测
            for pattern_str, desc in self._SENSITIVE_UNAUTH_PATTERNS:
                pattern = re.compile(pattern_str)
                for match in pattern.finditer(content):
                    # 检查同行或前几行是否有认证中间件引用
                    match_start = match.start()
                    context_start = max(0, match_start - 500)
                    context = content[context_start : match_start + len(match.group(0)) + 200]
                    has_auth_in_context = any(
                        auth_pat.search(context) for auth_pat in auth_middleware_patterns
                    )
                    if not has_auth_in_context:
                        line_no = self._line_number_from_offset(content, match_start)
                        endpoint_key = f"unauth:{file_path}:{match.group(0)[:60]}"
                        if endpoint_key not in issue_keys:
                            issue_keys.add(endpoint_key)
                            unauth_endpoints.append(
                                {
                                    "file": str(file_path),
                                    "line": str(line_no),
                                    "endpoint": match.group(0)[:80],
                                }
                            )

        # 汇总未认证端点
        if unauth_endpoints:
            sample = unauth_endpoints[:5]
            details = "; ".join(f"{Path(ep['file']).name}:{ep['line']}" for ep in sample)
            remaining = len(unauth_endpoints) - len(sample)
            if remaining > 0:
                details += f" (及其他 {remaining} 个)"
            issues.append(
                SecurityIssue(
                    severity="high",
                    category="未认证端点",
                    description=f"检测到 {len(unauth_endpoints)} 个可能缺少认证的敏感端点: {details}",
                    recommendation="为所有 /admin, /internal, /debug 路径添加认证中间件，或移至内网专用端口",
                    cwe="CWE-306",
                )
            )

        # 速率限制缺失
        if not has_rate_limit and self.backend != "none":
            issues.append(
                SecurityIssue(
                    severity="medium",
                    category="速率限制",
                    description="未检测到 API 速率限制配置",
                    recommendation=(
                        "为公开 API 添加速率限制中间件（express-rate-limit / slowapi / "
                        "Nginx limit_req），防止暴力破解和 DDoS"
                    ),
                    cwe="CWE-770",
                )
            )

        # CORS 未配置
        if not has_cors_config and self.backend != "none":
            issues.append(
                SecurityIssue(
                    severity="medium",
                    category="CORS 配置",
                    description="未检测到显式 CORS 配置，浏览器默认同源策略可能导致合法跨域请求被拒绝",
                    recommendation="显式配置 CORS 白名单，明确允许的 origin/method/header",
                    cwe="CWE-942",
                )
            )

        # API 版本控制缺失
        if not has_api_versioning and self.backend != "none":
            issues.append(
                SecurityIssue(
                    severity="low",
                    category="API 版本控制",
                    description="未检测到 API 版本控制策略（如 /api/v1/）",
                    recommendation="采用 URL 路径版本（/api/v1/）或 Header 版本控制，确保向后兼容",
                    cwe=None,
                )
            )

        return issues

    # ------------------------------------------------------------------
    # 密钥泄漏深度扫描
    # ------------------------------------------------------------------

    # 云厂商密钥正则（高信号模式）
    _CLOUD_KEY_PATTERNS: list[tuple[str, re.Pattern, str]] = [
        ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}"), "CWE-798"),
        (
            "AWS Secret Key",
            re.compile(
                r"""(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['"]?([A-Za-z0-9/+=]{40})"""
            ),
            "CWE-798",
        ),
        ("GCP Service Account Key", re.compile(r'"type"\s*:\s*"service_account"'), "CWE-798"),
        ("GCP API Key", re.compile(r"AIza[0-9A-Za-z_-]{35}"), "CWE-798"),
        (
            "Azure Storage Key",
            re.compile(
                r"""(?i)(AccountKey|azure[_-]?storage[_-]?key)\s*[:=]\s*['"]?([A-Za-z0-9+/=]{44,88})"""
            ),
            "CWE-798",
        ),
        (
            "Azure Client Secret",
            re.compile(r"""(?i)AZURE[_-]?CLIENT[_-]?SECRET\s*[:=]\s*['"]?([A-Za-z0-9~._-]{34,})"""),
            "CWE-798",
        ),
        ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"), "CWE-798"),
        (
            "Slack Token",
            re.compile(r"xox[bporas]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}"),
            "CWE-798",
        ),
        ("Stripe Secret Key", re.compile(r"sk_live_[0-9a-zA-Z]{24,}"), "CWE-798"),
        ("SendGrid API Key", re.compile(r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}"), "CWE-798"),
        (
            "Twilio Auth Token",
            re.compile(r"""(?i)TWILIO[_-]?AUTH[_-]?TOKEN\s*[:=]\s*['"]?([a-f0-9]{32})"""),
            "CWE-798",
        ),
        (
            "Generic Private Key",
            re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
            "CWE-321",
        ),
    ]

    # JWT 硬编码密钥模式
    _JWT_SECRET_PATTERNS: list[re.Pattern] = [
        re.compile(r"""(?i)jwt[_-]?secret\s*[:=]\s*['"]([^'"]{8,})['"]"""),
        re.compile(r"""(?i)SECRET_KEY\s*[:=]\s*['"]([^'"]{8,})['"]"""),
        re.compile(r"""(?i)TOKEN[_-]?SECRET\s*[:=]\s*['"]([^'"]{8,})['"]"""),
    ]

    def _review_secrets_deep(self) -> list[SecurityIssue]:
        """密钥泄漏深度扫描：.env 追踪、云密钥、JWT 硬编码、私钥文件。"""
        issues: list[SecurityIssue] = []
        issue_keys: set[str] = set()

        # 1. 检查 .env 文件是否被 Git 跟踪
        issues.extend(self._check_env_git_tracking())

        # 2. 检查 .gitignore 是否忽略了 .env
        issues.extend(self._check_gitignore_env())

        # 3. 扫描源码中的云厂商密钥
        for file_path, content in self._iter_source_files_with_content():
            if self._is_yaml_file(file_path):
                continue
            # 跳过明显的测试/示例/模板文件
            name_lower = file_path.name.lower()
            if any(
                token in name_lower
                for token in ("example", "template", "sample", "mock", "fixture")
            ):
                continue

            for key_name, pattern, cwe in self._CLOUD_KEY_PATTERNS:
                match = pattern.search(content)
                if not match:
                    continue
                # 排除注释中的示例
                match_line_start = content.rfind("\n", 0, match.start()) + 1
                line_content = content[match_line_start : match.end() + 50]
                if line_content.lstrip().startswith(("#", "//", "/*", "*", "<!--")):
                    continue

                issue_key = f"cloud-key:{file_path}:{key_name}"
                if issue_key in issue_keys:
                    continue
                issue_keys.add(issue_key)

                line_no = self._line_number_from_offset(content, match.start())
                issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="密钥泄漏",
                        description=f"检测到疑似 {key_name}: {file_path.name}:{line_no}",
                        recommendation=(
                            f"立即撤销该 {key_name}，将密钥迁移到环境变量或密钥管理服务 "
                            "(AWS Secrets Manager / HashiCorp Vault / Azure Key Vault)，"
                            "并检查 git 历史是否有泄漏"
                        ),
                        cwe=cwe,
                        file_path=str(file_path),
                        line=line_no,
                    )
                )

            # 4. JWT secret 硬编码检测
            for jwt_pattern in self._JWT_SECRET_PATTERNS:
                match = jwt_pattern.search(content)
                if not match:
                    continue
                secret_value = match.group(1)
                if self._looks_like_placeholder(secret_value):
                    continue

                issue_key = f"jwt-secret:{file_path}"
                if issue_key in issue_keys:
                    continue
                issue_keys.add(issue_key)

                line_no = self._line_number_from_offset(content, match.start())
                issues.append(
                    SecurityIssue(
                        severity="high",
                        category="JWT 硬编码密钥",
                        description=f"检测到 JWT/Token 密钥硬编码: {file_path.name}:{line_no}",
                        recommendation=(
                            "将 JWT secret 迁移到环境变量，使用 256 位以上随机字符串，"
                            "并实施密钥轮换机制"
                        ),
                        cwe="CWE-798",
                        file_path=str(file_path),
                        line=line_no,
                    )
                )

        # 5. 私钥文件扫描
        issues.extend(self._scan_private_key_files())

        return issues

    def _check_env_git_tracking(self) -> list[SecurityIssue]:
        """检查 .env 文件是否被 git 跟踪。"""
        issues: list[SecurityIssue] = []
        git_dir = self.project_dir / ".git"
        if not git_dir.exists():
            return issues

        # 查找所有 .env 文件
        env_files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [
                d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv"}
            ]
            for filename in filenames:
                if filename == ".env" or (
                    filename.startswith(".env.") and "example" not in filename.lower()
                ):
                    env_files.append(Path(dirpath) / filename)
            if len(env_files) >= 20:
                break

        for env_file in env_files:
            try:
                rel_path = env_file.relative_to(self.project_dir)
            except ValueError:
                continue
            # 检查文件是否被 git 跟踪
            result = self._run_command(
                ["git", "ls-files", "--error-unmatch", str(rel_path)],
                timeout=10,
            )
            if result["returncode"] == 0:
                issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="密钥泄漏",
                        description=f".env 文件被 Git 跟踪: {rel_path}",
                        recommendation=(
                            f"立即执行 'git rm --cached {rel_path}' 移除跟踪，"
                            "在 .gitignore 中添加 .env*，并轮换所有已泄露的密钥"
                        ),
                        cwe="CWE-540",
                        file_path=str(env_file),
                    )
                )

        return issues

    def _check_gitignore_env(self) -> list[SecurityIssue]:
        """检查 .gitignore 是否忽略了 .env 文件。"""
        issues: list[SecurityIssue] = []
        gitignore_path = self.project_dir / ".gitignore"
        if not gitignore_path.exists():
            issues.append(
                SecurityIssue(
                    severity="low",
                    category="密钥泄漏防护",
                    description="项目缺少 .gitignore 文件",
                    recommendation="创建 .gitignore 并至少包含 .env*、node_modules/、__pycache__/ 等条目",
                    cwe="CWE-540",
                )
            )
            return issues

        try:
            content = gitignore_path.read_text(encoding="utf-8")
        except Exception:
            return issues

        env_ignored = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped in (".env", ".env*", ".env.*", "*.env", ".env.local", ".env.production"):
                env_ignored = True
                break

        if not env_ignored:
            issues.append(
                SecurityIssue(
                    severity="medium",
                    category="密钥泄漏防护",
                    description=".gitignore 中未检测到 .env 忽略规则",
                    recommendation="在 .gitignore 中添加 '.env*' 规则以防止意外提交密钥文件",
                    cwe="CWE-540",
                    file_path=str(gitignore_path),
                )
            )

        return issues

    def _scan_private_key_files(self) -> list[SecurityIssue]:
        """扫描项目中是否包含私钥文件。"""
        issues: list[SecurityIssue] = []
        key_extensions = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
        key_filenames = {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"}

        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [
                d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv"}
            ]
            for filename in filenames:
                file_path = Path(dirpath) / filename
                is_key_file = False

                if file_path.suffix.lower() in key_extensions:
                    # 排除公钥和证书文件
                    if "public" in filename.lower() or filename.endswith(".pub"):
                        continue
                    is_key_file = True

                if filename.lower() in key_filenames:
                    is_key_file = True

                if is_key_file:
                    try:
                        rel_path = file_path.relative_to(self.project_dir)
                    except ValueError:
                        rel_path = file_path
                    issues.append(
                        SecurityIssue(
                            severity="high",
                            category="私钥文件",
                            description=f"检测到私钥文件: {rel_path}",
                            recommendation=(
                                "私钥文件不应包含在代码仓库中，"
                                "迁移到密钥管理服务或使用 CI/CD 密钥注入"
                            ),
                            cwe="CWE-321",
                            file_path=str(file_path),
                        )
                    )

        return issues
