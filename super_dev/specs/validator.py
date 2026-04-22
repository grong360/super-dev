"""
Spec-Driven Development 验证器

开发：Excellent（11964948@qq.com）
功能：验证规格格式和结构
作用：检查 spec.md 和 change 的格式是否符合规范标准
创建时间：2025-12-30
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationError:
    """验证错误"""

    file: str  # 文件路径
    line: int = 0  # 行号
    column: int = 0  # 列号
    message: str = ""  # 错误消息
    severity: str = "error"  # 严重程度: error, warning, info


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        """总问题数"""
        return len(self.errors) + len(self.warnings)

    def to_summary(self) -> str:
        """生成摘要报告"""
        lines = []
        if self.is_valid:
            lines.append("[通过] 规格格式验证通过")
        else:
            lines.append(f"[失败] 发现 {len(self.errors)} 个错误")

        if self.warnings:
            lines.append(f"[警告] {len(self.warnings)} 个警告")

        return "\n".join(lines)


@dataclass
class SpecQualityReport:
    change_id: str
    score: float
    level: str
    checks: dict[str, dict[str, object]]
    blockers: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    action_plan: list[dict[str, str]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.score >= 75
            and bool(self.checks.get("spec", {}).get("passed", False))
            and bool(self.checks.get("validation", {}).get("passed", False))
            and bool(self.checks.get("placeholder_free", {}).get("passed", False))
        )

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "score": self.score,
            "level": self.level,
            "checks": self.checks,
            "blockers": self.blockers,
            "suggestions": self.suggestions,
            "action_plan": self.action_plan,
        }


class SpecValidator:
    """规格验证器"""

    # 规范需求关键词
    REQUIREMENT_KEYWORDS = ["SHALL", "MUST", "SHOULD", "MAY"]

    # Delta 类型
    DELTA_TYPES = ["ADDED", "MODIFIED", "REMOVED"]
    PLACEHOLDER_PATTERNS = [
        re.compile(r"\bTBD\b", re.IGNORECASE),
        re.compile(r"\bDETAIL REQUIRED\b", re.IGNORECASE),
        re.compile(r"\bPENDING CLARIFICATION\b", re.IGNORECASE),
    ]

    def __init__(self, project_dir: Path | str):
        """初始化验证器"""
        self.project_dir = Path(project_dir).resolve()
        self.specs_dir = self.project_dir / ".super-dev" / "specs"
        self.changes_dir = self.project_dir / ".super-dev" / "changes"

    def validate_change(self, change_id: str) -> ValidationResult:
        """验证变更"""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        info: list[ValidationError] = []

        change_dir = self.changes_dir / change_id
        if not change_dir.exists():
            errors.append(
                ValidationError(file=str(change_dir), message=f"变更目录不存在: {change_id}")
            )
            return ValidationResult(is_valid=False, errors=errors)

        # 验证 proposal.md
        proposal_file = change_dir / "proposal.md"
        if proposal_file.exists():
            result = self._validate_proposal(proposal_file)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            info.extend(result.info)
        else:
            warnings.append(ValidationError(file=str(proposal_file), message="缺少 proposal.md"))

        # 验证 tasks.md
        tasks_file = change_dir / "tasks.md"
        if tasks_file.exists():
            result = self._validate_tasks(tasks_file)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            info.extend(result.info)
        else:
            warnings.append(ValidationError(file=str(tasks_file), message="缺少 tasks.md"))

        plan_file = change_dir / "plan.md"
        if plan_file.exists():
            result = self._validate_plan(plan_file)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        else:
            warnings.append(
                ValidationError(file=str(plan_file), severity="warning", message="缺少 plan.md")
            )

        checklist_file = change_dir / "checklist.md"
        if checklist_file.exists():
            result = self._validate_checklist(checklist_file)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        else:
            warnings.append(
                ValidationError(
                    file=str(checklist_file), severity="warning", message="缺少 checklist.md"
                )
            )

        # 验证 design.md (可选)
        design_file = change_dir / "design.md"
        if design_file.exists():
            result = self._validate_design(design_file)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        # 验证 specs/ 目录
        specs_dir = change_dir / "specs"
        if specs_dir.exists():
            for spec_file in specs_dir.rglob("spec.md"):
                result = self._validate_spec_delta(spec_file)
                errors.extend(result.errors)
                warnings.extend(result.warnings)
                info.extend(result.info)
        else:
            warnings.append(ValidationError(file=str(specs_dir), message="缺少 specs/ 目录"))

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings, info=info
        )

    def assess_change_quality(self, change_id: str) -> SpecQualityReport:
        change_dir = self.changes_dir / change_id
        if not change_dir.exists():
            return SpecQualityReport(
                change_id=change_id,
                score=0.0,
                level="critical",
                checks={},
                blockers=[f"变更目录不存在: {change_id}"],
                suggestions=["先运行 super-dev spec propose <change_id> 创建变更。"],
                action_plan=[
                    {
                        "step": "创建变更提案",
                        "command": f'super-dev spec propose {change_id} --title "<标题>" --description "<描述>"',
                        "priority": "P0",
                    }
                ],
            )

        checks: dict[str, dict[str, object]] = {}
        blockers: list[str] = []
        suggestions: list[str] = []
        action_plan: list[dict[str, str]] = []

        proposal_file = change_dir / "proposal.md"
        proposal_ok = (
            proposal_file.exists() and proposal_file.read_text(encoding="utf-8").strip() != ""
        )
        checks["proposal"] = {
            "passed": proposal_ok,
            "weight": 10,
            "reason": "" if proposal_ok else "缺少或空内容",
        }

        specs_dir = change_dir / "specs"
        spec_files = list(specs_dir.rglob("spec.md")) if specs_dir.exists() else []
        total_requirements = 0
        total_scenarios = 0
        for spec_file in spec_files:
            content = spec_file.read_text(encoding="utf-8")
            total_requirements += len(
                re.findall(r"^###\s+Requirement:", content, flags=re.MULTILINE)
            )
            total_scenarios += len(re.findall(r"^####\s+Scenario", content, flags=re.MULTILINE))
        spec_ok = len(spec_files) > 0 and total_requirements > 0
        checks["spec"] = {
            "passed": spec_ok,
            "weight": 30,
            "reason": "" if spec_ok else "缺少 spec.md 或未定义 Requirement",
            "spec_files": len(spec_files),
            "requirements": total_requirements,
            "scenarios": total_scenarios,
        }

        plan_file = change_dir / "plan.md"
        plan_ok = plan_file.exists() and ("## " in plan_file.read_text(encoding="utf-8"))
        checks["plan"] = {
            "passed": plan_ok,
            "weight": 15,
            "reason": "" if plan_ok else "缺少 plan.md 或结构过弱",
        }

        tasks_file = change_dir / "tasks.md"
        completed_tasks = 0
        total_tasks = 0
        tasks_ok = False
        if tasks_file.exists():
            text = tasks_file.read_text(encoding="utf-8")
            total_tasks = len(re.findall(r"^-\s*\[[ xX~_]\]", text, flags=re.MULTILINE))
            completed_tasks = len(re.findall(r"^-\s*\[[xX]\]", text, flags=re.MULTILINE))
            tasks_ok = total_tasks > 0
        checks["tasks"] = {
            "passed": tasks_ok,
            "weight": 20,
            "reason": "" if tasks_ok else "缺少 tasks.md 或无任务项",
            "total": total_tasks,
            "completed": completed_tasks,
        }

        checklist_file = change_dir / "checklist.md"
        checklist_ok = False
        checklist_total = 0
        checklist_done = 0
        if checklist_file.exists():
            text = checklist_file.read_text(encoding="utf-8")
            checklist_total = len(re.findall(r"^-\s*\[[ xX]\]", text, flags=re.MULTILINE))
            checklist_done = len(re.findall(r"^-\s*\[[xX]\]", text, flags=re.MULTILINE))
            checklist_ok = checklist_total > 0
        checks["checklist"] = {
            "passed": checklist_ok,
            "weight": 15,
            "reason": "" if checklist_ok else "缺少 checklist.md 或无勾选项",
            "total": checklist_total,
            "completed": checklist_done,
        }

        placeholder_hits = self._collect_placeholder_hits(change_dir)
        placeholder_free = len(placeholder_hits) == 0
        checks["placeholder_free"] = {
            "passed": placeholder_free,
            "weight": 10,
            "reason": "" if placeholder_free else f"发现 {len(placeholder_hits)} 处占位符",
            "hits": placeholder_hits[:10],
        }

        quality_validation = self.validate_change(change_id)
        validation_ok = quality_validation.is_valid
        checks["validation"] = {
            "passed": validation_ok,
            "weight": 10,
            "reason": "" if validation_ok else f"存在 {len(quality_validation.errors)} 个结构错误",
            "errors": len(quality_validation.errors),
            "warnings": len(quality_validation.warnings),
        }

        # 需求追溯覆盖率检查
        from .traceability import RequirementTracer

        tracer = RequirementTracer(self.project_dir)
        traced_reqs = tracer.extract_requirements(change_id)
        if traced_reqs:
            traced_reqs = tracer.trace_to_code(traced_reqs)
            traced_reqs = tracer.trace_to_tests(traced_reqs)
            shall_reqs = [r for r in traced_reqs if r.priority in ("SHALL", "MUST")]
            covered_shall = sum(
                1 for r in shall_reqs if len(r.implementations) > 0 and len(r.tests) > 0
            )
            shall_rate = (covered_shall / len(shall_reqs) * 100) if shall_reqs else 100.0
            traceability_ok = shall_rate >= 50.0
            checks["traceability"] = {
                "passed": traceability_ok,
                "weight": 0,
                "reason": (
                    "" if traceability_ok else f"SHALL/MUST 需求追溯覆盖率 {shall_rate:.0f}% < 50%"
                ),
                "total_requirements": len(traced_reqs),
                "shall_must_count": len(shall_reqs),
                "shall_covered": covered_shall,
                "shall_coverage_rate": round(shall_rate, 1),
            }
        else:
            checks["traceability"] = {
                "passed": True,
                "weight": 0,
                "reason": "未提取到 SHALL/MUST/SHOULD/MAY 需求",
                "total_requirements": 0,
            }

        total_weight = sum(int(str(item.get("weight", 0))) for item in checks.values())
        earned = sum(
            int(str(item.get("weight", 0)))
            for item in checks.values()
            if bool(item.get("passed", False))
        )
        score = (earned / total_weight * 100) if total_weight > 0 else 0.0

        if score >= 90:
            level = "excellent"
        elif score >= 75:
            level = "good"
        elif score >= 60:
            level = "fair"
        else:
            level = "critical"

        for key, item in checks.items():
            if not bool(item.get("passed", False)):
                reason = str(item.get("reason", "")).strip()
                blockers.append(f"{key}: {reason}")

        if not spec_ok:
            suggestions.append("先补齐至少一个 spec.md，且每个 spec 至少包含 1 个 Requirement。")
            action_plan.append(
                {
                    "step": "补齐规范主体",
                    "command": f"super-dev spec scaffold {change_id}",
                    "priority": "P0",
                }
            )
        if total_scenarios <= 0:
            suggestions.append("为关键 Requirement 补充 Scenario，保证可验收。")
            action_plan.append(
                {
                    "step": "补充关键场景",
                    "command": f'super-dev spec add-req {change_id} <spec> <req> "<包含场景的描述>"',
                    "priority": "P1",
                }
            )
        if not tasks_ok:
            suggestions.append("补齐 tasks.md 并拆分可执行任务项。")
            action_plan.append(
                {
                    "step": "补齐任务分解",
                    "command": f"super-dev spec scaffold {change_id} --force",
                    "priority": "P0",
                }
            )
        if checklist_total <= 0:
            suggestions.append("补齐 checklist.md 并设置发布前检查项。")
            action_plan.append(
                {
                    "step": "补齐交付清单",
                    "command": f"super-dev spec scaffold {change_id} --force",
                    "priority": "P1",
                }
            )
        if validation_ok is False:
            suggestions.append("执行 super-dev spec validate <change_id> -v 并修复结构错误。")
            action_plan.append(
                {
                    "step": "修复结构错误",
                    "command": f"super-dev spec validate {change_id} -v",
                    "priority": "P0",
                }
            )
        if not placeholder_free:
            suggestions.append(
                "移除 proposal/spec/plan/tasks/checklist 中的占位符内容，补齐真实需求与场景。"
            )
            action_plan.append(
                {
                    "step": "补齐占位内容",
                    "command": f"super-dev spec quality {change_id}",
                    "priority": "P0",
                }
            )
        if not action_plan and score >= 90:
            action_plan.append(
                {
                    "step": "进入实现闭环",
                    "command": f"在宿主里继续当前 change `{change_id}` 的实现与验证闭环",
                    "priority": "P2",
                }
            )

        return SpecQualityReport(
            change_id=change_id,
            score=round(score, 1),
            level=level,
            checks=checks,
            blockers=blockers,
            suggestions=suggestions,
            action_plan=action_plan,
        )

    def latest_change_id(self, *, exclude_ids: set[str] | None = None) -> str | None:
        exclude_ids = exclude_ids or set()
        if not self.changes_dir.exists():
            return None
        candidates: list[tuple[float, str]] = []
        for change_dir in self.changes_dir.iterdir():
            if (
                not change_dir.is_dir()
                or change_dir.name.startswith(".")
                or change_dir.name in exclude_ids
            ):
                continue
            try:
                timestamp = change_dir.stat().st_mtime
            except OSError:
                timestamp = 0.0
            candidates.append((timestamp, change_dir.name))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def assess_latest_change_quality(
        self, *, exclude_ids: set[str] | None = None
    ) -> SpecQualityReport | None:
        latest_change_id = self.latest_change_id(exclude_ids=exclude_ids)
        if not latest_change_id:
            return None
        return self.assess_change_quality(latest_change_id)

    def _collect_placeholder_hits(self, change_dir: Path) -> list[dict[str, object]]:
        files: list[Path] = []
        for name in ("proposal.md", "plan.md", "tasks.md", "checklist.md"):
            path = change_dir / name
            if path.exists():
                files.append(path)
        specs_dir = change_dir / "specs"
        if specs_dir.exists():
            files.extend(sorted(specs_dir.rglob("spec.md")))

        hits: list[dict[str, object]] = []
        for file_path in files:
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for line_number, line in enumerate(lines, 1):
                for pattern in self.PLACEHOLDER_PATTERNS:
                    if pattern.search(line):
                        hits.append(
                            {
                                "file": str(file_path.relative_to(self.project_dir)),
                                "line": line_number,
                                "text": line.strip(),
                            }
                        )
                        break
        return hits

    def validate_spec(self, spec_name: str) -> ValidationResult:
        """验证规范"""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        spec_file = self.specs_dir / spec_name / "spec.md"
        if not spec_file.exists():
            errors.append(
                ValidationError(file=str(spec_file), message=f"规范文件不存在: {spec_name}")
            )
            return ValidationResult(is_valid=False, errors=errors)

        content = spec_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # 检查标题
        has_title = False
        has_purpose = False
        has_requirements = False
        has_req_keyword = False

        for i, line in enumerate(lines, 1):
            # 检查一级标题
            if line.startswith("# ") and not has_title:
                has_title = True
                if not line[2:].strip():
                    errors.append(
                        ValidationError(file=str(spec_file), line=i, message="标题不能为空")
                    )

            # 检查 Purpose 部分
            if line.startswith("## Purpose"):
                has_purpose = True

            # 检查 Requirements 部分
            if line.startswith("## Requirements"):
                has_requirements = True

            # 检查需求格式
            if line.startswith("### Requirement:"):
                has_req_keyword = True
                if not line[16:].strip():
                    errors.append(
                        ValidationError(file=str(spec_file), line=i, message="需求名称不能为空")
                    )

            # 检查需求关键词
            if any(kw in line for kw in self.REQUIREMENT_KEYWORDS):
                has_req_keyword = True

            # 检查场景格式
            if line.startswith("#### Scenario:"):
                if not line[14:].strip():
                    warnings.append(
                        ValidationError(
                            file=str(spec_file), line=i, severity="warning", message="场景描述为空"
                        )
                    )

        # 验证结果
        if not has_title:
            errors.append(ValidationError(file=str(spec_file), message="缺少一级标题"))

        if not has_purpose:
            warnings.append(
                ValidationError(
                    file=str(spec_file), severity="warning", message="缺少 Purpose 部分"
                )
            )

        if not has_requirements:
            warnings.append(
                ValidationError(
                    file=str(spec_file), severity="warning", message="缺少 Requirements 部分"
                )
            )

        if not has_req_keyword:
            warnings.append(
                ValidationError(
                    file=str(spec_file),
                    severity="info",
                    message="建议使用 SHALL/MUST/SHOULD/MAY 关键词",
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_proposal(self, proposal_file: Path) -> ValidationResult:
        """验证提案文件"""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        content = proposal_file.read_text(encoding="utf-8")

        # 检查必需的章节
        has_title = False
        has_description = False

        for line in content.split("\n"):
            if re.match(r"^#\s+", line) and not re.match(r"^##", line):
                has_title = True
            elif re.match(r"^##\s+", line):
                if "description" in line.lower():
                    has_description = True
                elif "title" in line.lower():
                    has_title = True

        if not has_title:
            warnings.append(
                ValidationError(file=str(proposal_file), severity="warning", message="提案缺少标题")
            )

        if not has_description:
            warnings.append(
                ValidationError(file=str(proposal_file), severity="warning", message="提案缺少描述")
            )

        return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

    def _validate_tasks(self, tasks_file: Path) -> ValidationResult:
        """验证任务文件"""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        content = tasks_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        task_pattern = re.compile(
            r"^-\s*\[(?P<marker>[ xX~_])\]\s*(?:\*\*(?P<id1>[\d.]+):\s*(?P<title1>[^*]+)\*\*|(?P<id2>[\d.]+)\s*:?\s*(?P<title2>.+))\s*$"
        )

        task_ids = []
        for i, line in enumerate(lines, 1):
            match = task_pattern.match(line)
            if match:
                task_id = (match.group("id1") or match.group("id2") or "").strip()
                title = (match.group("title1") or match.group("title2") or "").strip()
                task_ids.append(task_id)

                # 检查任务标题
                if not title.strip():
                    errors.append(
                        ValidationError(file=str(tasks_file), line=i, message="任务标题不能为空")
                    )

        # 检查任务ID格式
        for task_id in task_ids:
            if not re.match(r"^\d+\.\d+$", task_id):
                warnings.append(
                    ValidationError(
                        file=str(tasks_file),
                        severity="warning",
                        message=f"任务ID格式建议为 '数字.数字' 格式: {task_id}",
                    )
                )

        if not task_ids:
            warnings.append(
                ValidationError(
                    file=str(tasks_file), severity="warning", message="没有找到任何任务"
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_plan(self, plan_file: Path) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        content = plan_file.read_text(encoding="utf-8")
        lowered = content.lower()
        if "# plan" not in lowered and "## context" not in lowered:
            warnings.append(
                ValidationError(
                    file=str(plan_file),
                    severity="warning",
                    message="plan.md 建议包含 Plan/Context 章节",
                )
            )
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_checklist(self, checklist_file: Path) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        content = checklist_file.read_text(encoding="utf-8")
        if "- [ ]" not in content and "- [x]" not in content and "- [X]" not in content:
            warnings.append(
                ValidationError(
                    file=str(checklist_file),
                    severity="warning",
                    message="checklist.md 建议包含可勾选项",
                )
            )
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_design(self, design_file: Path) -> ValidationResult:
        """验证设计文件"""
        # design.md 是可选的，只做基本检查
        content = design_file.read_text(encoding="utf-8")
        if len(content) < 10:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(file=str(design_file), message="设计文件内容过少")],
            )
        return ValidationResult(is_valid=True)

    def _validate_spec_delta(self, spec_file: Path) -> ValidationResult:
        """验证规范增量文件"""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        content = spec_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        has_delta_header = False
        current_delta_type = None
        has_requirements = False

        for i, line in enumerate(lines, 1):
            # 检查 Delta 类型标题
            if line.startswith("## "):
                for delta_type in self.DELTA_TYPES:
                    if delta_type in line.upper():
                        has_delta_header = True
                        current_delta_type = delta_type
                        break

            # 检查需求格式
            if line.startswith("### Requirement:"):
                if not current_delta_type:
                    errors.append(
                        ValidationError(
                            file=str(spec_file),
                            line=i,
                            message="需求必须在 Delta 类型 (ADDED/MODIFIED/REMOVED) 下",
                        )
                    )

                has_requirements = True

                if not line[16:].strip():
                    errors.append(
                        ValidationError(file=str(spec_file), line=i, message="需求名称不能为空")
                    )

        if not has_delta_header:
            errors.append(
                ValidationError(
                    file=str(spec_file), message="缺少 Delta 类型标题 (ADDED/MODIFIED/REMOVED)"
                )
            )

        if not has_requirements:
            warnings.append(
                ValidationError(file=str(spec_file), severity="warning", message="没有找到任何需求")
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_all(self) -> ValidationResult:
        """验证所有变更"""
        all_errors: list[ValidationError] = []
        all_warnings: list[ValidationError] = []

        if not self.changes_dir.exists():
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        file=str(self.changes_dir),
                        message="changes 目录不存在，请先运行 'super-dev spec init'",
                    )
                ],
            )

        for change_dir in self.changes_dir.iterdir():
            if change_dir.is_dir() and not change_dir.name.startswith("."):
                result = self.validate_change(change_dir.name)
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)

        return ValidationResult(
            is_valid=len(all_errors) == 0, errors=all_errors, warnings=all_warnings
        )
