"""
Spec-Driven Development 管理器

开发：Excellent（11964948@qq.com）
功能：管理规范和变更的文件读写
作用：处理 specs/ 和 changes/ 目录的文件操作
创建时间：2025-12-30
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]

from .models import (
    Change,
    ChangeStatus,
    DeltaType,
    Proposal,
    Requirement,
    Scenario,
    Spec,
    SpecDelta,
    Task,
    TaskStatus,
)


class SpecManager:
    """规范管理器 - 管理当前规范 (specs/)"""

    def __init__(self, project_dir: Path | str):
        """初始化规范管理器"""
        self.project_dir = Path(project_dir).resolve()
        self.specs_dir = self.project_dir / ".super-dev" / "specs"

    def init(self):
        """初始化规范目录"""
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        (self.specs_dir / ".gitkeep").touch()

    def get_spec_path(self, spec_name: str) -> Path:
        """获取规范文件路径"""
        resolved = (self.specs_dir / spec_name / "spec.md").resolve()
        if not str(resolved).startswith(str(self.specs_dir.resolve())):
            raise ValueError(f"Invalid spec name: {spec_name}")
        return self.specs_dir / spec_name / "spec.md"

    def load_spec(self, spec_name: str) -> Spec | None:
        """加载规范"""
        spec_path = self.get_spec_path(spec_name)
        if not spec_path.exists():
            return None

        content = spec_path.read_text(encoding="utf-8")
        return self._parse_spec(spec_name, content)

    def save_spec(self, spec: Spec):
        """保存规范"""
        spec_path = self.get_spec_path(spec.name)
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec.updated_at = datetime.now(timezone.utc)
        spec_path.write_text(spec.to_markdown(), encoding="utf-8")

    def list_specs(self) -> list[str]:
        """列出所有规范"""
        if not self.specs_dir.exists():
            return []
        return [
            d.name for d in self.specs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    def delete_spec(self, spec_name: str):
        """删除规范"""
        import shutil

        spec_path = self.get_spec_path(spec_name)
        if spec_path.exists():
            shutil.rmtree(spec_path.parent)

    def _parse_spec(self, spec_name: str, content: str) -> Spec:
        """从 Markdown 解析规范"""
        lines = content.split("\n")

        spec = Spec(name=spec_name)
        current_section = None
        current_req = None

        for line in lines:
            # 解析标题
            if line.startswith("# "):
                spec.title = line[2:].strip()
            elif line.startswith("## Purpose"):
                current_section = "purpose"
            elif line.startswith("## Requirements"):
                current_section = "requirements"
            elif line.startswith("### Requirement:"):
                if current_req:
                    spec.requirements.append(current_req)
                current_req = Requirement(name=line[16:].strip())
                current_section = "requirement"
            elif line.startswith("#### Scenario"):
                if current_req:
                    scenario = Scenario(when=line.split(":", 1)[-1].strip() if ":" in line else "")
                    current_req.scenarios.append(scenario)
            elif current_section == "purpose" and line.strip():
                spec.purpose += line.strip() + "\n"
            elif current_section == "requirement" and current_req:
                if line.strip().startswith(("SHALL", "MUST", "SHOULD", "MAY")):
                    parts = line.strip().split(" ", 1)
                    current_req.keyword = parts[0]
                    current_req.description = parts[1] if len(parts) > 1 else ""
                elif line.startswith("- GIVEN"):
                    if current_req.scenarios:
                        current_req.scenarios[-1].given = line[7:].strip()
                elif line.startswith("- WHEN"):
                    if current_req.scenarios:
                        current_req.scenarios[-1].when = line[6:].strip()
                elif line.startswith("- THEN"):
                    if current_req.scenarios:
                        current_req.scenarios[-1].then = line[6:].strip()

        if current_req:
            spec.requirements.append(current_req)

        spec.purpose = spec.purpose.strip()
        return spec


class ChangeManager:
    """变更管理器 - 管理变更提案 (changes/)"""

    def __init__(self, project_dir: Path | str):
        """初始化变更管理器"""
        self.project_dir = Path(project_dir).resolve()
        self.changes_dir = self.project_dir / ".super-dev" / "changes"

    def init(self):
        """初始化变更目录"""
        self.changes_dir.mkdir(parents=True, exist_ok=True)
        (self.changes_dir / ".gitkeep").touch()

    def get_change_path(self, change_id: str) -> Path:
        """获取变更目录路径"""
        resolved = (self.changes_dir / change_id).resolve()
        if not str(resolved).startswith(str(self.changes_dir.resolve())):
            raise ValueError(f"Invalid change ID: {change_id}")
        return self.changes_dir / change_id

    def load_change(self, change_id: str) -> Change | None:
        """加载变更"""
        change_path = self.get_change_path(change_id)
        if not change_path.exists():
            return None

        change = Change(id=change_id, title=change_id.replace("-", " ").title())

        # 加载元数据
        meta_path = change_path / "change.yaml"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                metadata = yaml.safe_load(f) or {}
            title = metadata.get("title")
            if isinstance(title, str) and title.strip():
                change.title = title.strip()

            raw_status = str(metadata.get("status", "")).strip().lower()
            for status in ChangeStatus:
                if status.value == raw_status:
                    change.status = status
                    break

            created_at = metadata.get("created_at")
            if isinstance(created_at, str):
                try:
                    change.created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    pass
            updated_at = metadata.get("updated_at")
            if isinstance(updated_at, str):
                try:
                    change.updated_at = datetime.fromisoformat(updated_at)
                except ValueError:
                    pass

        # 加载提案
        proposal_path = change_path / "proposal.md"
        if proposal_path.exists():
            change.proposal = self._parse_proposal(proposal_path.read_text(encoding="utf-8"))

        # 加载任务
        tasks_path = change_path / "tasks.md"
        if tasks_path.exists():
            change.tasks = self._parse_tasks(tasks_path.read_text(encoding="utf-8"))

        # 加载设计笔记
        design_path = change_path / "design.md"
        if design_path.exists():
            change.design_notes = design_path.read_text(encoding="utf-8")

        # 加载规范增量
        specs_deltas_dir = change_path / "specs"
        if specs_deltas_dir.exists():
            change.spec_deltas = self._parse_spec_deltas(specs_deltas_dir)

        return change

    def save_change(self, change: Change):
        """保存变更"""
        change_path = self.get_change_path(change.id)
        change_path.mkdir(parents=True, exist_ok=True)
        change.updated_at = datetime.now(timezone.utc)

        # 保存提案
        if change.proposal:
            proposal_path = change_path / "proposal.md"
            proposal_path.write_text(change.proposal.to_markdown(), encoding="utf-8")

        # 保存任务
        tasks_path = change_path / "tasks.md"
        tasks_path.write_text(self._format_tasks(change.tasks), encoding="utf-8")

        # 保存设计笔记
        if change.design_notes:
            design_path = change_path / "design.md"
            design_path.write_text(change.design_notes, encoding="utf-8")

        # 保存规范增量
        if change.spec_deltas:
            for delta in change.spec_deltas:
                delta_path = change_path / "specs" / delta.spec_name / "spec.md"
                delta_path.parent.mkdir(parents=True, exist_ok=True)
                delta_path.write_text(delta.to_markdown(), encoding="utf-8")

        # 保存元数据
        meta_path = change_path / "change.yaml"
        with open(meta_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "id": change.id,
                    "title": change.title,
                    "status": change.status.value,
                    "created_at": change.created_at.isoformat(),
                    "updated_at": change.updated_at.isoformat(),
                },
                f,
                allow_unicode=True,
            )

    def list_changes(self, status: ChangeStatus | None = None) -> list[Change]:
        """列出所有变更"""
        if not self.changes_dir.exists():
            return []

        changes = []
        for d in self.changes_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                change = self.load_change(d.name)
                if change and (status is None or change.status == status):
                    changes.append(change)

        return sorted(changes, key=lambda c: self._normalize_datetime(c.created_at), reverse=True)

    def delete_change(self, change_id: str):
        """删除变更"""
        change_path = self.get_change_path(change_id)
        if change_path.exists():
            import shutil

            shutil.rmtree(change_path)

    def archive_change(self, change_id: str, spec_manager: SpecManager):
        """归档变更 - 将规范增量合并到主规范"""
        change = self.load_change(change_id)
        if not change:
            raise FileNotFoundError(f"变更不存在: {change_id}")

        # 合并规范增量
        for delta in change.spec_deltas:
            spec = spec_manager.load_spec(delta.spec_name)
            if not spec:
                spec = Spec(name=delta.spec_name, title=delta.spec_name.replace("-", " ").title())

            if delta.delta_type == DeltaType.ADDED:
                spec.requirements.extend(delta.requirements)
            elif delta.delta_type == DeltaType.MODIFIED:
                # 替换同名需求
                for new_req in delta.requirements:
                    for i, existing_req in enumerate(spec.requirements):
                        if existing_req.name == new_req.name:
                            spec.requirements[i] = new_req
                            break
                    else:
                        spec.requirements.append(new_req)
            elif delta.delta_type == DeltaType.REMOVED:
                # 移除指定需求
                spec.requirements = [
                    r
                    for r in spec.requirements
                    if r.name not in {req.name for req in delta.requirements}
                ]

            spec_manager.save_spec(spec)

        # 更新状态并保存，然后移动到归档
        change.status = ChangeStatus.ARCHIVED
        self.save_change(change)

        archive_dir = self.changes_dir.parent / "archive" / change_id
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.move(str(self.get_change_path(change_id)), str(archive_dir))

        return change

    def _parse_proposal(self, content: str) -> Proposal:
        """解析提案"""
        lines = content.split("\n")
        proposal = Proposal(title="", description="")

        current_section = None
        for line in lines:
            if line.startswith("## "):
                current_section = line[3:].lower()
            elif current_section == "description" and line.strip():
                proposal.description += line.strip() + "\n"
            elif current_section == "motivation" and line.strip():
                proposal.motivation += line.strip() + "\n"
            elif current_section == "impact" and line.strip():
                proposal.impact += line.strip() + "\n"
            elif line.startswith("# ") and not proposal.title:
                proposal.title = line[2:].strip()

        proposal.description = proposal.description.strip()
        proposal.motivation = proposal.motivation.strip()
        proposal.impact = proposal.impact.strip()
        return proposal

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _parse_tasks(self, content: str) -> list[Task]:
        """解析任务"""
        tasks: list[Task] = []
        current_task: Task | None = None
        task_pattern = re.compile(
            r"^-\s*\[(?P<marker>[ xX~_])\]\s+\*\*(?P<id>[^:]+):\s*(?P<title>.*?)\*\*\s*$"
        )
        fallback_pattern = re.compile(
            r"^-\s*\[(?P<marker>[ xX~_])\]\s+(?P<id>\d+(?:\.\d+)*)\s*:?\s*(?P<title>.+)$"
        )

        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            task_match = task_pattern.match(stripped) or fallback_pattern.match(stripped)
            if task_match:
                if current_task:
                    tasks.append(current_task)
                marker = task_match.group("marker")
                status = {
                    " ": TaskStatus.PENDING,
                    "~": TaskStatus.IN_PROGRESS,
                    "x": TaskStatus.COMPLETED,
                    "X": TaskStatus.COMPLETED,
                    "_": TaskStatus.SKIPPED,
                }.get(marker, TaskStatus.PENDING)
                current_task = Task(
                    id=task_match.group("id").strip(),
                    title=task_match.group("title").strip(),
                    status=status,
                )
                continue

            if current_task is None or not stripped.startswith("-"):
                continue

            detail = stripped[1:].strip()
            detail_lower = detail.lower()
            if detail_lower.startswith("refs:"):
                refs_part = detail.split(":", 1)[1].strip() if ":" in detail else ""
                refs = [
                    token.strip().strip("`")
                    for token in refs_part.split(",")
                    if token.strip().strip("`")
                ]
                current_task.spec_refs = refs
                continue

            if detail_lower.startswith("depends on:"):
                depends_part = detail.split(":", 1)[1].strip() if ":" in detail else ""
                dependencies = [token.strip() for token in depends_part.split(",") if token.strip()]
                current_task.dependencies = dependencies
                continue

            if detail_lower.startswith("assigned to:"):
                current_task.assigned_to = detail.split(":", 1)[1].strip() if ":" in detail else ""
                continue

            if current_task.description:
                current_task.description = f"{current_task.description}\n{detail}"
            else:
                current_task.description = detail

        if current_task:
            tasks.append(current_task)

        return tasks

    def _format_tasks(self, tasks: list[Task]) -> str:
        """格式化任务为 Markdown"""
        lines = ["# Tasks", ""]
        groups: dict[str, list[Task]] = {}
        for task in tasks:
            group = task.id.split(".")[0]
            if group not in groups:
                groups[group] = []
            groups[group].append(task)

        def _group_sort_key(value: str) -> tuple[int, int | str]:
            if value.isdigit():
                return (0, int(value))
            return (1, value)

        for group in sorted(groups.keys(), key=_group_sort_key):
            group_name = {
                "1": "1. Planning",
                "2": "2. Frontend",
                "3": "3. Backend",
                "4": "4. Integration & Quality",
                "5": "5. Testing",
                "6": "6. Documentation",
            }.get(group, f"{group}. Other")
            lines.append(f"## {group_name}")
            lines.append("")
            for task in groups[group]:
                lines.append(task.to_markdown())
            lines.append("")

        return "\n".join(lines)

    def _parse_spec_deltas(self, specs_dir: Path) -> list[SpecDelta]:
        """解析规范增量"""
        deltas = []
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                spec_path = spec_dir / "spec.md"
                if spec_path.exists():
                    content = spec_path.read_text(encoding="utf-8")
                    # 解析增量类型
                    delta_type = DeltaType.ADDED
                    for line in content.split("\n"):
                        if line.startswith("## ADDED"):
                            delta_type = DeltaType.ADDED
                            break
                        elif line.startswith("## MODIFIED"):
                            delta_type = DeltaType.MODIFIED
                            break
                        elif line.startswith("## REMOVED"):
                            delta_type = DeltaType.REMOVED
                            break

                    requirements: list[Requirement] = []
                    current_req: Requirement | None = None
                    current_scenario: Scenario | None = None

                    for raw_line in content.split("\n"):
                        line = raw_line.strip()
                        if line.startswith("### Requirement:"):
                            if current_req:
                                requirements.append(current_req)
                            req_name = line[len("### Requirement:") :].strip()
                            current_req = Requirement(name=req_name)
                            current_scenario = None
                            continue

                        if current_req is None:
                            continue

                        if line.startswith(("SHALL ", "MUST ", "SHOULD ", "MAY ")):
                            parts = line.split(" ", 1)
                            current_req.keyword = parts[0]
                            current_req.description = parts[1] if len(parts) > 1 else ""
                            continue

                        if line.startswith("#### Scenario"):
                            current_scenario = Scenario()
                            current_req.scenarios.append(current_scenario)
                            continue

                        if line.startswith("- GIVEN"):
                            if current_scenario is None:
                                current_scenario = Scenario()
                                current_req.scenarios.append(current_scenario)
                            current_scenario.given = line[len("- GIVEN") :].strip()
                            continue

                        if line.startswith("- WHEN"):
                            if current_scenario is None:
                                current_scenario = Scenario()
                                current_req.scenarios.append(current_scenario)
                            current_scenario.when = line[len("- WHEN") :].strip()
                            continue

                        if line.startswith("- THEN"):
                            if current_scenario is None:
                                current_scenario = Scenario()
                                current_req.scenarios.append(current_scenario)
                            current_scenario.then = line[len("- THEN") :].strip()
                            continue

                    if current_req:
                        requirements.append(current_req)

                    deltas.append(
                        SpecDelta(
                            spec_name=spec_dir.name,
                            delta_type=delta_type,
                            description="",
                            requirements=requirements,
                        )
                    )

        return deltas

    # ------------------------------------------------------------------
    # Spec Template Differentiation
    # ------------------------------------------------------------------

    SPEC_TEMPLATES: dict[str, dict[str, str]] = {
        "feature": {
            "title_prefix": "Feature",
            "sections": (
                "## Description\n\n"
                "Describe the new feature and its user-facing value.\n\n"
                "## Motivation\n\n"
                "Why is this feature needed? What problem does it solve?\n\n"
                "## Impact\n\n"
                "Which modules / APIs / UI pages will be affected?\n\n"
                "## Acceptance Criteria\n\n"
                "- [ ] Criterion 1\n"
                "- [ ] Criterion 2\n\n"
                "## Tasks\n\n"
                "- [ ] Design\n"
                "- [ ] Implementation\n"
                "- [ ] Testing\n"
                "- [ ] Documentation\n"
            ),
        },
        "bugfix": {
            "title_prefix": "Bugfix",
            "sections": (
                "## Bug Description\n\n"
                "Describe the incorrect behavior.\n\n"
                "## Steps to Reproduce\n\n"
                "1. Step one\n"
                "2. Step two\n\n"
                "## Expected Behavior\n\n"
                "What should happen instead.\n\n"
                "## Root Cause Analysis\n\n"
                "Preliminary analysis of the root cause.\n\n"
                "## Fix Plan\n\n"
                "- [ ] Identify affected code paths\n"
                "- [ ] Implement fix\n"
                "- [ ] Add regression test\n"
                "- [ ] Verify in staging\n"
            ),
        },
        "refactor": {
            "title_prefix": "Refactor",
            "sections": (
                "## Refactoring Scope\n\n"
                "What code / modules will be restructured?\n\n"
                "## Motivation\n\n"
                "Why is this refactoring necessary? (tech debt, performance, maintainability)\n\n"
                "## Constraints\n\n"
                "- No functional behavior change\n"
                "- All existing tests must pass\n\n"
                "## Plan\n\n"
                "- [ ] Audit current code structure\n"
                "- [ ] Design target structure\n"
                "- [ ] Incremental migration steps\n"
                "- [ ] Validate with existing test suite\n"
            ),
        },
        "migration": {
            "title_prefix": "Migration",
            "sections": (
                "## Migration Target\n\n"
                "What is being migrated (framework, database, API version, etc.)?\n\n"
                "## Current State\n\n"
                "Describe the current setup and version.\n\n"
                "## Target State\n\n"
                "Describe the desired setup and version.\n\n"
                "## Rollback Plan\n\n"
                "How to revert if migration fails.\n\n"
                "## Steps\n\n"
                "- [ ] Backup current state\n"
                "- [ ] Run migration in staging\n"
                "- [ ] Validate data integrity\n"
                "- [ ] Deploy to production\n"
                "- [ ] Monitor for 24h\n"
            ),
        },
    }

    def create_change_from_template(
        self,
        change_id: str,
        title: str,
        template_type: str = "feature",
    ) -> Change:
        """根据类型模板创建变更提案"""
        template = self.SPEC_TEMPLATES.get(template_type, self.SPEC_TEMPLATES["feature"])
        prefix = template["title_prefix"]
        full_title = f"[{prefix}] {title}" if not title.startswith(f"[{prefix}]") else title

        proposal = Proposal(
            title=full_title,
            description=f"Auto-generated {template_type} proposal for: {title}",
        )

        change = Change(
            id=change_id,
            title=full_title,
            status=ChangeStatus.DRAFT,
            proposal=proposal,
        )

        # Save with template content
        change_path = self.get_change_path(change_id)
        change_path.mkdir(parents=True, exist_ok=True)

        proposal_path = change_path / "proposal.md"
        proposal_path.write_text(
            f"# {full_title}\n\n{template['sections']}",
            encoding="utf-8",
        )

        self.save_change(change)
        return change

    # ------------------------------------------------------------------
    # Spec Dependency Analysis
    # ------------------------------------------------------------------

    def analyze_dependencies(self) -> dict[str, object]:
        """
        分析所有变更之间的依赖关系。

        检查 tasks.md 中的 'Depends on:' 声明以及 spec_refs 交叉引用，
        构建依赖图并检测循环依赖。

        Returns:
            包含依赖图和问题列表的字典
        """
        changes = self.list_changes()
        dependency_graph: dict[str, list[str]] = {}
        reverse_deps: dict[str, list[str]] = {}
        issues: list[dict[str, str]] = []

        for change in changes:
            change_deps: set[str] = set()

            # Extract dependencies from tasks
            for task in change.tasks:
                for dep in task.dependencies:
                    # Deps may reference task IDs from other changes
                    dep_stripped = dep.strip()
                    if dep_stripped:
                        change_deps.add(dep_stripped)

            # Extract dependencies from spec deltas (cross-references)
            for delta in change.spec_deltas:
                for req in delta.requirements:
                    for scenario in req.scenarios:
                        given = (scenario.given or "").lower()
                        if "depends on" in given or "requires" in given:
                            # Try to extract referenced change/spec
                            for other in changes:
                                if other.id != change.id and other.id in given:
                                    change_deps.add(other.id)

            dependency_graph[change.id] = sorted(change_deps)

            for dep_id in change_deps:
                if dep_id not in reverse_deps:
                    reverse_deps[dep_id] = []
                reverse_deps[dep_id].append(change.id)

        # Detect circular dependencies
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _has_cycle(node: str, path: list[str]) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in dependency_graph.get(node, []):
                if neighbor in dependency_graph:  # Only check known changes
                    if neighbor not in visited:
                        result = _has_cycle(neighbor, path + [neighbor])
                        if result:
                            return result
                    elif neighbor in rec_stack:
                        return path + [neighbor]
            rec_stack.discard(node)
            return None

        for change_id in dependency_graph:
            if change_id not in visited:
                cycle = _has_cycle(change_id, [change_id])
                if cycle:
                    issues.append(
                        {
                            "severity": "high",
                            "message": f"循环依赖: {' -> '.join(cycle)}",
                            "fix": "移除或重构循环引用中的某个依赖",
                        }
                    )

        # Check for missing dependencies
        all_change_ids = {c.id for c in changes}
        all_task_ids: set[str] = set()
        for change in changes:
            for task in change.tasks:
                all_task_ids.add(task.id)

        for change_id, deps in dependency_graph.items():
            for dep in deps:
                if dep not in all_change_ids and dep not in all_task_ids:
                    issues.append(
                        {
                            "severity": "medium",
                            "message": f"变更 '{change_id}' 依赖未知的 '{dep}'",
                            "fix": f"确认 '{dep}' 是否存在，或移除该依赖声明",
                        }
                    )

        return {
            "dependency_graph": {k: v for k, v in dependency_graph.items() if v},
            "reverse_dependencies": reverse_deps,
            "issues": issues,
            "total_changes": len(changes),
            "changes_with_deps": len([v for v in dependency_graph.values() if v]),
        }

    # ------------------------------------------------------------------
    # Spec Time Estimation
    # ------------------------------------------------------------------

    COMPLEXITY_HOURS: dict[str, dict[str, float]] = {
        "planning": {"low": 1.0, "medium": 2.0, "high": 4.0},
        "frontend": {"low": 2.0, "medium": 6.0, "high": 16.0},
        "backend": {"low": 2.0, "medium": 8.0, "high": 20.0},
        "integration": {"low": 1.0, "medium": 3.0, "high": 8.0},
        "testing": {"low": 1.0, "medium": 4.0, "high": 10.0},
        "documentation": {"low": 0.5, "medium": 1.5, "high": 3.0},
    }

    def estimate_change_effort(self, change_id: str) -> dict[str, object]:
        """
        基于任务复杂度给出粗略工时估算。

        通过分析任务数量、任务分组（前端/后端/测试等）和描述关键词推断复杂度。

        Args:
            change_id: 变更 ID

        Returns:
            包含工时估算详情的字典
        """
        change = self.load_change(change_id)
        if not change:
            return {"error": f"变更不存在: {change_id}"}

        estimates: list[dict[str, object]] = []
        total_hours = 0.0

        group_map: dict[str, str] = {
            "1": "planning",
            "2": "frontend",
            "3": "backend",
            "4": "integration",
            "5": "testing",
            "6": "documentation",
        }

        for task in change.tasks:
            group_key = task.id.split(".")[0]
            category = group_map.get(group_key, "integration")

            # Estimate complexity from task attributes
            complexity = self._estimate_task_complexity(task)
            hours = self.COMPLEXITY_HOURS.get(category, self.COMPLEXITY_HOURS["integration"])[
                complexity
            ]

            # Adjust for dependencies
            if task.dependencies:
                hours *= 1.2  # 20% overhead for coordination

            estimates.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "category": category,
                    "complexity": complexity,
                    "estimated_hours": round(hours, 1),
                    "status": task.status.value,
                }
            )
            total_hours += hours

        # Add buffer (15% for unknowns)
        buffer_hours = total_hours * 0.15
        grand_total = total_hours + buffer_hours

        # Group by category
        by_category: dict[str, float] = {}
        for est in estimates:
            cat = str(est["category"])
            estimated_hours = cast(float, est["estimated_hours"])
            by_category[cat] = by_category.get(cat, 0.0) + estimated_hours

        return {
            "change_id": change_id,
            "title": change.title,
            "task_count": len(change.tasks),
            "estimates": estimates,
            "by_category": {k: round(v, 1) for k, v in by_category.items()},
            "subtotal_hours": round(total_hours, 1),
            "buffer_hours": round(buffer_hours, 1),
            "total_hours": round(grand_total, 1),
            "estimated_days": round(grand_total / 8, 1),
            "confidence": (
                "low" if len(change.tasks) < 3 else "medium" if len(change.tasks) < 10 else "high"
            ),
        }

    def _estimate_task_complexity(self, task: Task) -> str:
        """根据任务描述和引用推断复杂度"""
        desc = (task.description or "").lower() + " " + task.title.lower()
        high_keywords = [
            "migration",
            "架构",
            "重构",
            "database",
            "security",
            "认证",
            "auth",
            "payment",
            "支付",
            "integration",
            "集成",
            "performance",
            "性能",
            "deployment",
            "部署",
            "infra",
            "基础设施",
        ]
        medium_keywords = [
            "api",
            "接口",
            "component",
            "组件",
            "page",
            "页面",
            "form",
            "表单",
            "crud",
            "list",
            "列表",
            "filter",
            "筛选",
            "search",
            "搜索",
        ]

        if any(kw in desc for kw in high_keywords):
            return "high"
        if any(kw in desc for kw in medium_keywords):
            return "medium"
        if task.spec_refs and len(task.spec_refs) > 2:
            return "high"
        return "low"

    # ------------------------------------------------------------------
    # Spec Change Impact Analysis
    # ------------------------------------------------------------------

    def analyze_change_impact(self, change_id: str) -> dict[str, object]:
        """
        分析变更对现有代码和其他变更的影响。

        检查 spec deltas 涉及的规范、任务中引用的文件路径，
        以及与其他活跃变更之间的潜在冲突。

        Args:
            change_id: 变更 ID

        Returns:
            包含影响分析结果的字典
        """
        change = self.load_change(change_id)
        if not change:
            return {"error": f"变更不存在: {change_id}"}

        affected_specs: list[str] = []
        affected_files: list[str] = []
        affected_modules: set[str] = set()
        potential_conflicts: list[dict[str, str]] = []

        # 1. Analyze spec delta impact
        spec_manager = SpecManager(self.project_dir)
        for delta in change.spec_deltas:
            affected_specs.append(delta.spec_name)
            existing_spec = spec_manager.load_spec(delta.spec_name)
            if existing_spec:
                if delta.delta_type == DeltaType.MODIFIED:
                    for req in delta.requirements:
                        for existing_req in existing_spec.requirements:
                            if existing_req.name == req.name:
                                affected_modules.add(f"spec:{delta.spec_name}/{req.name}")
                elif delta.delta_type == DeltaType.REMOVED:
                    for req in delta.requirements:
                        affected_modules.add(f"spec:{delta.spec_name}/{req.name} (REMOVED)")

        # 2. Analyze task references
        for task in change.tasks:
            for ref in task.spec_refs:
                affected_files.append(ref)
                # Infer module from file path
                parts = ref.replace("\\", "/").split("/")
                for part in parts:
                    if part in ("src", "lib", "app", "components", "pages", "routes", "services"):
                        idx = parts.index(part)
                        if idx + 1 < len(parts):
                            affected_modules.add(parts[idx + 1])

        # 3. Check for conflicts with other active changes
        all_changes = self.list_changes()
        for other in all_changes:
            if other.id == change_id:
                continue
            if other.status in (ChangeStatus.ARCHIVED,):
                continue

            # Check spec overlap
            other_specs = {d.spec_name for d in other.spec_deltas}
            overlap = set(affected_specs) & other_specs
            if overlap:
                potential_conflicts.append(
                    {
                        "change_id": other.id,
                        "title": other.title,
                        "conflict_type": "spec_overlap",
                        "details": f"共同修改的规范: {', '.join(overlap)}",
                    }
                )

            # Check file reference overlap
            other_files = set()
            for task in other.tasks:
                other_files.update(task.spec_refs)
            file_overlap = set(affected_files) & other_files
            if file_overlap:
                potential_conflicts.append(
                    {
                        "change_id": other.id,
                        "title": other.title,
                        "conflict_type": "file_overlap",
                        "details": f"共同引用的文件: {', '.join(list(file_overlap)[:5])}",
                    }
                )

        # 4. Risk assessment
        risk_factors: list[str] = []
        risk_level = "low"

        if len(change.spec_deltas) > 3:
            risk_factors.append(f"涉及 {len(change.spec_deltas)} 个规范变更，范围较大")
            risk_level = "medium"

        has_removal = any(d.delta_type == DeltaType.REMOVED for d in change.spec_deltas)
        if has_removal:
            risk_factors.append("包含规范删除操作，可能影响下游依赖")
            risk_level = "high"

        if potential_conflicts:
            risk_factors.append(f"与 {len(potential_conflicts)} 个活跃变更存在潜在冲突")
            risk_level = "high" if len(potential_conflicts) > 2 else "medium"

        if len(change.tasks) > 15:
            risk_factors.append(f"包含 {len(change.tasks)} 个任务，变更粒度较大，建议拆分")

        return {
            "change_id": change_id,
            "title": change.title,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "affected_specs": affected_specs,
            "affected_files": affected_files,
            "affected_modules": sorted(affected_modules),
            "potential_conflicts": potential_conflicts,
            "spec_deltas_summary": [
                {
                    "spec": d.spec_name,
                    "type": d.delta_type.value,
                    "requirements_count": len(d.requirements),
                }
                for d in change.spec_deltas
            ],
            "task_count": len(change.tasks),
            "completed_tasks": len([t for t in change.tasks if t.status == TaskStatus.COMPLETED]),
        }
