"""
可编程验证规则引擎 - 支持 YAML 自定义质量规则

开发：Excellent（11964948@qq.com）
功能：加载内置/项目级规则，按阶段执行验证并生成报告
创建时间：2026-03-28
"""

from __future__ import annotations

import glob
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

# 合法值常量
VALID_CATEGORIES = frozenset(
    {
        "security",
        "performance",
        "documentation",
        "testing",
        "code_quality",
        "architecture",
    }
)

VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low"})

VALID_PHASES = frozenset(
    {
        "research",
        "docs",
        "spec",
        "frontend",
        "backend",
        "quality",
        "delivery",
        "all",
    }
)

VALID_CHECK_TYPES = frozenset(
    {
        "file_exists",
        "content_contains",
        "content_not_contains",
        "regex_match",
        "metric_threshold",
        "custom",
    }
)

# 严重级别权重（用于分数计算）
SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}


@dataclass
class ValidationRule:
    """单条验证规则。

    Attributes:
        id: 规则ID，如 ``SEC-001``。
        name: 规则名称。
        category: 类别，取值见 ``VALID_CATEGORIES``。
        severity: 严重级别，取值见 ``VALID_SEVERITIES``。
        phase: 适用阶段，取值见 ``VALID_PHASES``。
        description: 规则描述。
        check_type: 检查类型，取值见 ``VALID_CHECK_TYPES``。
        check_config: 检查配置（取决于 ``check_type``）。
        enabled: 是否启用。
        tags: 标签列表。
    """

    id: str
    name: str
    category: str
    severity: str
    phase: str
    description: str
    check_type: str
    check_config: dict[str, Any]
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}' for rule {self.id}. "
                f"Must be one of: {sorted(VALID_CATEGORIES)}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}' for rule {self.id}. "
                f"Must be one of: {sorted(VALID_SEVERITIES)}"
            )
        if self.phase not in VALID_PHASES:
            raise ValueError(
                f"Invalid phase '{self.phase}' for rule {self.id}. "
                f"Must be one of: {sorted(VALID_PHASES)}"
            )
        if self.check_type not in VALID_CHECK_TYPES:
            raise ValueError(
                f"Invalid check_type '{self.check_type}' for rule {self.id}. "
                f"Must be one of: {sorted(VALID_CHECK_TYPES)}"
            )


@dataclass
class ValidationResult:
    """单条规则的验证结果。

    Attributes:
        rule_id: 对应的规则 ID。
        passed: 是否通过。
        message: 结果描述。
        severity: 规则严重级别。
        fix_suggestion: 修复建议（可选）。
    """

    rule_id: str
    passed: bool
    message: str
    severity: str
    fix_suggestion: str = ""


@dataclass
class ValidationReport:
    """一次验证执行的完整报告。

    Attributes:
        phase: 验证阶段。
        timestamp: ISO 格式时间戳。
        results: 验证结果列表。
        passed: 所有 critical 规则均通过时为 True。
        score: 综合得分 0-100。
    """

    phase: str
    timestamp: str
    results: list[ValidationResult]
    passed: bool
    score: int

    @property
    def critical_failures(self) -> list[ValidationResult]:
        """返回所有 critical 级别的失败项。"""
        return [r for r in self.results if not r.passed and r.severity == "critical"]

    @property
    def failed_results(self) -> list[ValidationResult]:
        """返回所有失败项。"""
        return [r for r in self.results if not r.passed]

    @property
    def passed_results(self) -> list[ValidationResult]:
        """返回所有通过项。"""
        return [r for r in self.results if r.passed]

    def to_markdown(self) -> str:
        """生成 Markdown 格式的验证报告。"""
        status_text = "通过" if self.passed else "未通过"
        lines = [
            "# 验证规则报告",
            "",
            f"**阶段**: {self.phase}",
            f"**时间**: {self.timestamp}",
            f"**状态**: {status_text}",
            f"**得分**: {self.score}/100",
            f"**规则数**: {len(self.results)}",
            "",
            "---",
            "",
        ]

        if self.critical_failures:
            lines.append("## 关键失败项")
            lines.append("")
            for r in self.critical_failures:
                lines.append(f"- **{r.rule_id}**: {r.message}")
                if r.fix_suggestion:
                    lines.append(f"  - 修复建议: {r.fix_suggestion}")
            lines.append("")

        lines.append("## 详细结果")
        lines.append("")
        lines.append("| 规则 ID | 状态 | 严重级别 | 描述 |")
        lines.append("|:---|:---:|:---:|:---|")
        for r in self.results:
            icon = "✓" if r.passed else "✗"
            lines.append(f"| {r.rule_id} | {icon} | {r.severity} | {r.message} |")
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典，便于 JSON 输出。"""
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "score": self.score,
            "total_rules": len(self.results),
            "passed_count": len(self.passed_results),
            "failed_count": len(self.failed_results),
            "critical_failure_count": len(self.critical_failures),
            "results": [
                {
                    "rule_id": r.rule_id,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                    "fix_suggestion": r.fix_suggestion,
                }
                for r in self.results
            ],
        }


def _parse_rule_dict(data: dict[str, Any]) -> ValidationRule:
    """从字典解析出 ``ValidationRule``，缺省字段使用默认值。

    红队规则 YAML 使用 ``patterns`` 而非 ``check_config``，且可能缺少
    ``phase`` / ``check_type``。此函数自动做格式适配。
    """
    # 红队规则兼容：patterns -> check_config, 缺省 phase/check_type
    check_config = data.get("check_config", {})
    check_type = data.get("check_type", "")

    if not check_config and "patterns" in data:
        check_config = {"patterns": data["patterns"]}
    if not check_type:
        if "patterns" in data:
            check_type = "content_not_contains"
        else:
            check_type = "custom"

    # 非标准 check_type 映射为 custom，将原始类型存入 check_config
    if check_type not in VALID_CHECK_TYPES:
        check_config["_original_check_type"] = check_type
        check_type = "custom"

    return ValidationRule(
        id=data["id"],
        name=data["name"],
        category=data["category"],
        severity=data["severity"],
        phase=data.get("phase", "all"),
        description=data.get("description", ""),
        check_type=check_type,
        check_config=check_config,
        enabled=data.get("enabled", True),
        tags=data.get("tags", []),
    )


def _load_rules_from_yaml(path: Path) -> list[ValidationRule]:
    """从 YAML 文件加载规则列表。

    支持顶层 key 为 ``rules`` 或 ``redteam_rules`` 的格式。
    """
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    if not content:
        return []

    # 兼容 rules / redteam_rules 两种顶层 key
    items: list[Any] | None = None
    for key in ("rules", "redteam_rules"):
        if key in content and isinstance(content[key], list):
            items = content[key]
            break
    if not items:
        return []

    rules: list[ValidationRule] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rules.append(_parse_rule_dict(item))
    return rules


class ValidationRuleEngine:
    """可编程验证规则引擎。

    加载内置默认规则和项目级自定义规则，按阶段执行验证并生成报告。

    Args:
        project_dir: 项目根目录路径。

    Example::

        engine = ValidationRuleEngine(Path("."))
        report = engine.validate("docs", {"project_dir": "."})
        print(report.to_markdown())
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self.rules: list[ValidationRule] = []
        self._custom_checkers: dict[
            str, Callable[[ValidationRule, dict[str, Any]], ValidationResult]
        ] = {}
        self._load_default_rules()
        self._load_project_rules(project_dir)

    # ── 规则加载 ──────────────────────────────────────

    def _load_default_rules(self) -> None:
        """加载内置默认规则（含红队规则）。

        扫描 ``rules/`` 目录下所有 YAML 文件，按文件名排序依次加载。
        """
        rules_dir = Path(__file__).parent / "rules"
        if not rules_dir.is_dir():
            return
        for yaml_file in sorted(rules_dir.glob("*.yaml")):
            loaded = _load_rules_from_yaml(yaml_file)
            # 同 ID 规则后加载的覆盖先加载的
            existing_ids = {r.id for r in self.rules}
            for rule in loaded:
                if rule.id in existing_ids:
                    self.rules = [r if r.id != rule.id else rule for r in self.rules]
                else:
                    self.rules.append(rule)

    def _load_project_rules(self, project_dir: Path) -> None:
        """加载项目级自定义规则，同 ID 规则覆盖默认规则。"""
        custom_path = project_dir / ".super-dev" / "rules" / "custom_rules.yaml"
        custom_rules = _load_rules_from_yaml(custom_path)
        if not custom_rules:
            return

        rule_map: dict[str, ValidationRule] = {r.id: r for r in self.rules}
        for rule in custom_rules:
            rule_map[rule.id] = rule
        self.rules = list(rule_map.values())

    def reload_rules(self) -> None:
        """重新加载所有规则（默认 + 项目）。"""
        self.rules = []
        self._load_default_rules()
        self._load_project_rules(self.project_dir)

    # ── 规则管理 ──────────────────────────────────────

    def add_rule(self, rule: ValidationRule) -> None:
        """动态添加或替换一条规则。"""
        for i, existing in enumerate(self.rules):
            if existing.id == rule.id:
                self.rules[i] = rule
                return
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """按 ID 移除规则，返回是否成功。"""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) < before

    def get_rule(self, rule_id: str) -> ValidationRule | None:
        """按 ID 获取规则。"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def get_rules_for_phase(self, phase: str) -> list[ValidationRule]:
        """获取指定阶段的所有已启用规则。

        同时包含 ``phase="all"`` 的规则。
        """
        return [r for r in self.rules if r.enabled and (r.phase == phase or r.phase == "all")]

    def list_rules(
        self,
        category: str | None = None,
        severity: str | None = None,
        phase: str | None = None,
    ) -> list[ValidationRule]:
        """按条件筛选规则列表。"""
        result = self.rules
        if category:
            result = [r for r in result if r.category == category]
        if severity:
            result = [r for r in result if r.severity == severity]
        if phase:
            result = [r for r in result if r.phase == phase or r.phase == "all"]
        return result

    def register_custom_checker(
        self,
        check_type: str,
        checker: Callable[[ValidationRule, dict[str, Any]], ValidationResult],
    ) -> None:
        """注册自定义检查器。

        ``checker`` 需为可调用对象，签名为
        ``(rule: ValidationRule, context: dict) -> ValidationResult``。
        """
        self._custom_checkers[check_type] = checker

    # ── 验证执行 ──────────────────────────────────────

    def validate(self, phase: str, context: dict[str, Any] | None = None) -> ValidationReport:
        """对指定阶段执行所有适用规则。

        Args:
            phase: 当前阶段名称。
            context: 运行时上下文，可包含 ``project_dir``、``metrics`` 等。

        Returns:
            ``ValidationReport`` 实例。
        """
        if context is None:
            context = {}
        context.setdefault("project_dir", str(self.project_dir))

        applicable_rules = self.get_rules_for_phase(phase)
        results: list[ValidationResult] = []

        for rule in applicable_rules:
            result = self._execute_rule(rule, context)
            results.append(result)

        passed = all(r.passed for r in results if r.severity == "critical")
        score = self._calculate_score(results)

        return ValidationReport(
            phase=phase,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results,
            passed=passed,
            score=score,
        )

    def validate_file(
        self, file_path: Path, rules: list[ValidationRule] | None = None
    ) -> list[ValidationResult]:
        """验证单个文件。

        对给定的规则列表（默认使用全部已启用规则）逐一检查文件。

        Args:
            file_path: 待验证文件路径。
            rules: 规则列表，为 None 时使用全部已启用规则。

        Returns:
            验证结果列表。
        """
        if rules is None:
            rules = [r for r in self.rules if r.enabled]

        resolved = file_path.resolve()
        if not resolved.is_file():
            return [
                ValidationResult(
                    rule_id="SYS",
                    passed=False,
                    message=f"文件不存在: {file_path}",
                    severity="high",
                )
            ]

        results: list[ValidationResult] = []
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return [
                ValidationResult(
                    rule_id="SYS",
                    passed=False,
                    message=f"无法读取文件 {file_path}: {exc}",
                    severity="high",
                )
            ]

        for rule in rules:
            if rule.check_type == "content_contains":
                result = self._check_content_contains_single(rule, content, str(file_path))
            elif rule.check_type == "content_not_contains":
                result = self._check_content_not_contains_single(rule, content, str(file_path))
            elif rule.check_type == "regex_match":
                result = self._check_regex_match_single(rule, content, str(file_path))
            else:
                continue
            results.append(result)

        return results

    # ── 内部执行 ──────────────────────────────────────

    def _execute_rule(self, rule: ValidationRule, context: dict[str, Any]) -> ValidationResult:
        """执行单条规则。"""
        try:
            if rule.check_type in self._custom_checkers:
                return self._custom_checkers[rule.check_type](rule, context)

            handler = {
                "file_exists": self._check_file_exists,
                "content_contains": self._check_content_contains,
                "content_not_contains": self._check_content_not_contains,
                "regex_match": self._check_regex_match,
                "metric_threshold": self._check_metric_threshold,
                "custom": self._check_custom,
            }.get(rule.check_type)

            if handler is None:
                return ValidationResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"未知检查类型: {rule.check_type}",
                    severity=rule.severity,
                )
            return handler(rule, context)
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                rule_id=rule.id,
                passed=False,
                message=f"规则执行异常: {exc}",
                severity=rule.severity,
            )

    # ── 检查类型实现 ──────────────────────────────────

    def _check_file_exists(self, rule: ValidationRule, context: dict[str, Any]) -> ValidationResult:
        """检查是否存在匹配的文件。"""
        project_dir = Path(context.get("project_dir", self.project_dir))
        pattern = rule.check_config.get("file_pattern", "")
        min_count = rule.check_config.get("min_count", 1)

        matches = glob.glob(str(project_dir / pattern), recursive=True)
        count = len(matches)

        if count >= min_count:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 找到 {count} 个匹配文件",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 找到 {count} 个文件，需要至少 {min_count} 个",
            severity=rule.severity,
            fix_suggestion=f"确保匹配 '{pattern}' 的文件至少有 {min_count} 个",
        )

    def _check_content_contains(
        self, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """检查文件内容是否包含必需段落/关键词。"""
        project_dir = Path(context.get("project_dir", self.project_dir))
        pattern = rule.check_config.get("file_pattern", "")
        required = rule.check_config.get("required_sections", [])

        matches = glob.glob(str(project_dir / pattern), recursive=True)
        if not matches:
            return ValidationResult(
                rule_id=rule.id,
                passed=False,
                message=f"{rule.name}: 未找到匹配文件 '{pattern}'",
                severity=rule.severity,
                fix_suggestion=f"创建匹配 '{pattern}' 的文件",
            )

        missing_all: list[str] = []
        for filepath in matches:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            missing = [s for s in required if s not in content]
            if not missing:
                return ValidationResult(
                    rule_id=rule.id,
                    passed=True,
                    message=f"{rule.name}: 所有必需内容均已包含",
                    severity=rule.severity,
                )
            missing_all = missing

        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 缺少内容段落: {', '.join(missing_all)}",
            severity=rule.severity,
            fix_suggestion=f"在文件中添加以下段落: {', '.join(missing_all)}",
        )

    def _check_content_contains_single(
        self, rule: ValidationRule, content: str, filepath: str
    ) -> ValidationResult:
        """对单个文件内容执行 content_contains 检查。"""
        required = rule.check_config.get("required_sections", [])
        missing = [s for s in required if s not in content]
        if not missing:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 所有必需内容均已包含 ({filepath})",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 缺少 {', '.join(missing)} ({filepath})",
            severity=rule.severity,
            fix_suggestion=f"添加: {', '.join(missing)}",
        )

    def _check_content_not_contains(
        self, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """检查文件内容不应包含特定模式。"""
        project_dir = Path(context.get("project_dir", self.project_dir))
        pattern = rule.check_config.get("file_pattern", "")
        bad_patterns = rule.check_config.get("patterns", [])
        exclude_patterns = rule.check_config.get("exclude_patterns", [])

        matches = glob.glob(str(project_dir / pattern), recursive=True)
        violations: list[str] = []
        excluded_paths: set[Path] = set()
        for exclude_pattern in exclude_patterns:
            for filepath in glob.glob(str(project_dir / str(exclude_pattern)), recursive=True):
                excluded_paths.add(Path(filepath))

        for filepath in matches:
            candidate_path = Path(filepath)
            if candidate_path in excluded_paths:
                continue
            try:
                content = candidate_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat in bad_patterns:
                if re.search(pat, content):
                    rel = str(candidate_path.relative_to(project_dir))
                    violations.append(f"{rel} 匹配 '{pat}'")

        if not violations:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 未发现违规内容",
                severity=rule.severity,
            )

        display = violations[:5]
        extra = f" (共 {len(violations)} 处)" if len(violations) > 5 else ""
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 发现违规{extra}: {'; '.join(display)}",
            severity=rule.severity,
            fix_suggestion=f"移除或修复匹配项: {rule.description}",
        )

    def _check_content_not_contains_single(
        self, rule: ValidationRule, content: str, filepath: str
    ) -> ValidationResult:
        """对单个文件内容执行 content_not_contains 检查。"""
        bad_patterns = rule.check_config.get("patterns", [])
        found: list[str] = []
        for pat in bad_patterns:
            if re.search(pat, content):
                found.append(pat)
        if not found:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 未发现违规内容 ({filepath})",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 发现违规模式 ({filepath})",
            severity=rule.severity,
            fix_suggestion=f"移除匹配: {', '.join(found)}",
        )

    def _check_regex_match(self, rule: ValidationRule, context: dict[str, Any]) -> ValidationResult:
        """检查文件中是否存在匹配的正则模式。"""
        project_dir = Path(context.get("project_dir", self.project_dir))
        file_pattern = rule.check_config.get("file_pattern", "")
        regex = rule.check_config.get("pattern", "")
        desc = rule.check_config.get("description", rule.description)

        matches = glob.glob(str(project_dir / file_pattern), recursive=True)
        if not matches:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 无匹配文件（跳过）",
                severity=rule.severity,
            )

        found_in: list[str] = []
        for filepath in matches:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(regex, content):
                found_in.append(str(Path(filepath).relative_to(project_dir)))

        if found_in:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 在 {len(found_in)} 个文件中匹配到模式",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 未匹配到模式 — {desc}",
            severity=rule.severity,
            fix_suggestion=desc,
        )

    def _check_regex_match_single(
        self, rule: ValidationRule, content: str, filepath: str
    ) -> ValidationResult:
        """对单个文件内容执行 regex_match 检查。"""
        regex = rule.check_config.get("pattern", "")
        if re.search(regex, content):
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 匹配成功 ({filepath})",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: 未匹配到模式 ({filepath})",
            severity=rule.severity,
            fix_suggestion=rule.check_config.get("description", rule.description),
        )

    def _check_metric_threshold(
        self, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """检查指标是否满足阈值条件。"""
        metric_name = rule.check_config.get("metric", "")
        metrics: dict[str, Any] = context.get("metrics", {})
        value = metrics.get(metric_name)

        if value is None:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: 指标 '{metric_name}' 不可用（跳过）",
                severity=rule.severity,
            )

        min_val = rule.check_config.get("min_value")
        max_val = rule.check_config.get("max_value")
        passed = True
        details: list[str] = []

        if min_val is not None and value < min_val:
            passed = False
            details.append(f"当前值 {value} 低于最小值 {min_val}")
        if max_val is not None and value > max_val:
            passed = False
            details.append(f"当前值 {value} 超过最大值 {max_val}")

        if passed:
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message=f"{rule.name}: {metric_name}={value}，符合阈值",
                severity=rule.severity,
            )
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            message=f"{rule.name}: {'; '.join(details)}",
            severity=rule.severity,
            fix_suggestion=f"调整 {metric_name} 使其满足阈值要求",
        )

    def _check_custom(self, rule: ValidationRule, context: dict[str, Any]) -> ValidationResult:
        """自定义检查占位：需通过 register_custom_checker 注册。"""
        checker_name = rule.check_config.get("checker")
        if checker_name and checker_name in self._custom_checkers:
            return self._custom_checkers[checker_name](rule, context)
        return ValidationResult(
            rule_id=rule.id,
            passed=True,
            message=f"{rule.name}: 自定义检查器未注册（跳过）",
            severity=rule.severity,
        )

    # ── 分数计算 ──────────────────────────────────────

    @staticmethod
    def _calculate_score(results: list[ValidationResult]) -> int:
        """根据验证结果计算综合得分（0-100）。

        加权算法：每条规则按严重级别赋权，通过的规则累计得分，
        最终换算为 0-100 分。
        """
        if not results:
            return 100

        total_weight = 0.0
        earned_weight = 0.0

        for r in results:
            w = SEVERITY_WEIGHTS.get(r.severity, 1.0)
            total_weight += w
            if r.passed:
                earned_weight += w

        if total_weight == 0:
            return 100
        return round((earned_weight / total_weight) * 100)
