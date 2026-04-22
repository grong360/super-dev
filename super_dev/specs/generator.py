"""
Spec-Driven Development 生成器

开发：Excellent（11964948@qq.com）
功能：从需求或 PRD 自动生成规范和变更提案
作用：辅助用户快速创建 SDD 文档
创建时间：2025-12-30
"""

import re
from pathlib import Path

from .manager import ChangeManager, SpecManager
from .models import (
    Change,
    ChangeStatus,
    DeltaType,
    Proposal,
    Requirement,
    Scenario,
    SpecDelta,
    Task,
    TaskStatus,
)


class SpecGenerator:
    """规范生成器 - 从需求自动生成规范"""

    def __init__(self, project_dir: Path | str):
        """初始化生成器"""
        self.project_dir = Path(project_dir).resolve()
        self.spec_manager = SpecManager(self.project_dir)
        self.change_manager = ChangeManager(self.project_dir)

    def create_change(
        self, change_id: str, title: str, description: str, motivation: str = "", impact: str = ""
    ) -> Change:
        """创建新变更提案"""
        change = Change(
            id=change_id,
            title=title,
            status=ChangeStatus.PROPOSED,
            proposal=Proposal(
                title=title, description=description, motivation=motivation, impact=impact
            ),
        )
        self.change_manager.save_change(change)
        return change

    def scaffold_change_artifacts(self, change_id: str, *, force: bool = False) -> dict[str, Path]:
        """为变更生成 Spec 四件套（spec/plan/tasks/checklist）"""
        change = self.change_manager.load_change(change_id)
        if not change:
            raise FileNotFoundError(f"变更不存在: {change_id}")

        change_path = self.change_manager.get_change_path(change_id)
        change_path.mkdir(parents=True, exist_ok=True)

        spec_name = self._guess_primary_spec_name(change_id)
        spec_path = change_path / "specs" / spec_name / "spec.md"
        plan_path = change_path / "plan.md"
        tasks_path = change_path / "tasks.md"
        checklist_path = change_path / "checklist.md"

        spec_path.parent.mkdir(parents=True, exist_ok=True)

        files_and_content = {
            spec_path: self._render_spec_template(
                title=change.title,
                description=change.proposal.description if change.proposal else "",
            ),
            plan_path: self._render_plan_template(
                title=change.title,
                description=change.proposal.description if change.proposal else "",
            ),
            tasks_path: self._render_tasks_template(title=change.title),
            checklist_path: self._render_checklist_template(),
        }

        written: dict[str, Path] = {}
        for file_path, content in files_and_content.items():
            if file_path.exists() and not force:
                written[file_path.name] = file_path
                continue
            file_path.write_text(content, encoding="utf-8")
            written[file_path.name] = file_path

        return written

    def add_requirement_to_change(
        self,
        change_id: str,
        spec_name: str,
        requirement_name: str,
        description: str,
        scenarios: list[dict] | None = None,
        delta_type: DeltaType = DeltaType.ADDED,
    ) -> SpecDelta:
        """向变更添加需求"""
        change = self.change_manager.load_change(change_id)
        if not change:
            raise FileNotFoundError(f"变更不存在: {change_id}")

        # 创建场景
        req_scenarios = []
        if scenarios:
            for s in scenarios:
                req_scenarios.append(
                    Scenario(
                        given=s.get("given", ""), when=s.get("when", ""), then=s.get("then", "")
                    )
                )

        requirement = Requirement(name=requirement_name, description=description, keyword="SHALL")
        requirement.scenarios = req_scenarios

        # 查找或创建增量
        for delta in change.spec_deltas:
            if delta.spec_name == spec_name:
                delta.requirements.append(requirement)
                break
        else:
            delta = SpecDelta(
                spec_name=spec_name, delta_type=delta_type, requirements=[requirement]
            )
            change.spec_deltas.append(delta)

        self.change_manager.save_change(change)
        return delta

    def generate_tasks_from_requirements(
        self, change_id: str, tech_stack: dict | None = None
    ) -> list[Task]:
        """从需求自动生成任务"""
        change = self.change_manager.load_change(change_id)
        if not change:
            raise FileNotFoundError(f"变更不存在: {change_id}")

        tasks = []
        task_id = [1, 0]  # [major, minor]

        # 根据规范增量生成任务
        for delta in change.spec_deltas:
            for req in delta.requirements:
                # 为每个需求生成实现任务
                task_id[1] += 1
                task = Task(
                    id=f"{task_id[0]}.{task_id[1]}",
                    title=f"Implement: {req.name}",
                    description=req.description,
                    status=TaskStatus.PENDING,
                    spec_refs=[f"{delta.spec_name}::{req.name}"],
                )
                tasks.append(task)

        # 根据 tech_stack 生成差异化任务
        if tech_stack:
            task_id[0] += 1
            task_id[1] = 0
            frontend_tech = tech_stack.get("frontend")
            if frontend_tech:
                task_id[1] += 1
                tasks.append(
                    Task(
                        id=f"{task_id[0]}.{task_id[1]}",
                        title=f"前端实现: {frontend_tech} 组件开发",
                        description=f"基于 {frontend_tech} 技术栈实现前端组件与页面",
                        status=TaskStatus.PENDING,
                    )
                )
            backend_tech = tech_stack.get("backend")
            if backend_tech:
                task_id[1] += 1
                tasks.append(
                    Task(
                        id=f"{task_id[0]}.{task_id[1]}",
                        title=f"后端实现: {backend_tech} API 开发",
                        description=f"基于 {backend_tech} 技术栈实现后端 API 接口",
                        status=TaskStatus.PENDING,
                    )
                )
            database_tech = tech_stack.get("database")
            if database_tech:
                task_id[1] += 1
                tasks.append(
                    Task(
                        id=f"{task_id[0]}.{task_id[1]}",
                        title="数据库: Schema 设计与迁移脚本",
                        description=f"设计 {database_tech} 数据库 Schema 并编写迁移脚本",
                        status=TaskStatus.PENDING,
                    )
                )

        # 添加测试任务
        task_id[0] += 1
        task_id[1] = 0
        for delta in change.spec_deltas:
            task_id[1] += 1
            task = Task(
                id=f"{task_id[0]}.{task_id[1]}",
                title=f"Test: {delta.spec_name} requirements",
                description=f"Verify all scenarios for {delta.spec_name}",
                status=TaskStatus.PENDING,
                spec_refs=[delta.spec_name],
            )
            tasks.append(task)

        # 更新变更
        change.tasks = tasks
        self.change_manager.save_change(change)

        return tasks

    # PRD 标题匹配模式（支持中英文变体）
    _OVERVIEW_PATTERNS = (
        "## 概述",
        "## 产品概述",
        "## Overview",
        "## 1. 产品愿景",
        "## 简介",
        "## Introduction",
    )
    _FEATURES_PATTERNS = (
        "## 功能需求",
        "## 核心功能",
        "## Features",
        "## 2. 功能需求",
        "## 需求列表",
        "## Requirements",
    )

    def propose_from_prd(self, prd_content: str) -> Change:
        """从 PRD 内容生成变更提案 (简化版)"""
        # 解析 PRD 提取关键信息
        lines = prd_content.split("\n")

        title = "Feature from PRD"
        description = ""
        features: list[str] = []

        current_section: str | None = None
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
            elif any(line.startswith(p) for p in self._OVERVIEW_PATTERNS):
                current_section = "overview"
            elif any(line.startswith(p) for p in self._FEATURES_PATTERNS):
                current_section = "features"
            elif line.startswith("## "):
                # 遇到其他二级标题时重置 section，避免误收集
                current_section = None
            elif line.startswith("- ") or line.startswith("* "):
                if current_section == "features":
                    features.append(line[2:].strip())
            elif current_section == "overview" and line.strip():
                description += line.strip() + "\n"

        # 创建变更 ID（只保留安全字符）
        change_id = re.sub(r"[^a-z0-9_-]+", "-", title.lower()).strip("-")[:50]

        change = self.create_change(
            change_id=change_id,
            title=title,
            description=description.strip(),
            motivation="Derived from PRD",
            impact=", ".join(features[:3]),
        )

        return change

    def init_sdd(self):
        """初始化 SDD 目录结构"""
        self.spec_manager.init()
        self.change_manager.init()

        # 创建 AGENTS.md 文件
        agents_path = self.project_dir / ".super-dev" / "AGENTS.md"
        if not agents_path.exists():
            agents_content = """# Super Dev Spec-Driven Development

This project uses Super Dev's Spec-Driven Development (SDD) workflow.

## Workflow

1. **Propose**: Create a change proposal with `super-dev spec propose <id>`
2. **Review**: Review the generated specs and tasks
3. **Implement**: Work through the tasks with AI assistance
4. **Archive**: Archive the change with `super-dev spec archive <id>`

## Directory Structure

```
.super-dev/
├── specs/          # Current specifications (source of truth)
├── changes/        # Proposed changes (proposals + tasks + deltas)
└── archive/        # Archived changes
```

## Commands

- `super-dev spec show <id>` - Show change details
- `super-dev spec propose <id>` - Create new change proposal
- `super-dev spec apply <id>` - Start implementing a change
- `super-dev spec archive <id>` - Archive completed change

## AI Integration

When working with AI coding assistants, reference the change:

"Please help me implement change `add-user-auth`. The tasks are in `.super-dev/changes/add-user-auth/tasks.md` and the specs are in `.super-dev/changes/add-user-auth/specs/`."
"""
            agents_path.write_text(agents_content, encoding="utf-8")

        # 创建 project.md 模板
        project_path = self.project_dir / ".super-dev" / "project.md"
        if not project_path.exists():
            project_content = """# Project Context

## Purpose
_What is this project about?_

## Tech Stack
- **Language**: _e.g., Python, JavaScript, Go_
- **Framework**: _e.g., FastAPI, Express, Gin_
- **Database**: _e.g., PostgreSQL, MongoDB_
- **Frontend**: _e.g., React, Vue, None_

## Conventions
### Code Style
- _e.g., PEP 8 for Python, ESLint + Prettier for JS_

### Git Flow
- _e.g., main for production, develop for integration_

### Testing
- _e.g., pytest with >80% coverage required_

## Architecture Notes
_Add architectural patterns and decisions here_

## Domain Knowledge
_Add domain-specific information here_
"""
            project_path.write_text(project_content, encoding="utf-8")

        return agents_path, project_path

    def _guess_primary_spec_name(self, change_id: str) -> str:
        candidate = re.sub(r"^(add|update|remove|refactor)-", "", change_id.strip().lower())
        candidate = re.sub(r"[^a-z0-9_-]+", "-", candidate).strip("-")
        return candidate or "core"

    def _render_spec_template(self, *, title: str, description: str) -> str:
        summary = description.strip() or "请补充功能背景与范围。"
        return (
            f"# {title}\n\n"
            "## Summary\n"
            f"{summary}\n\n"
            "## ADDED Requirements\n\n"
            "### Requirement: core-behavior\n"
            "SHALL 系统必须满足核心行为定义。\n\n"
            "#### Scenario 1: Happy path\n"
            "- GIVEN 前置条件成立\n"
            "- WHEN 用户执行核心动作\n"
            "- THEN 返回预期结果\n\n"
            "## Notes\n"
            "- 用户故事：作为 <角色>，我希望 <能力>，以便 <价值>\n"
            "- 性能：定义响应时间、吞吐、并发目标\n"
            "- 可靠性：定义错误预算与恢复目标\n"
            "- 安全性：定义鉴权、审计、最小权限要求\n\n"
            "## Acceptance Checklist\n"
            "- [ ] AC1: 核心流程可验证通过\n"
            "- [ ] AC2: 失败路径有明确处理\n"
            "- [ ] AC3: 回归测试覆盖关键场景\n\n"
            "## Out of Scope\n"
            "- 明确不在本次变更范围的内容\n"
        )

    def _render_plan_template(self, *, title: str, description: str) -> str:
        summary = description.strip() or "请补充变更目标。"
        return (
            f"# Plan: {title}\n\n"
            "## Context\n"
            f"{summary}\n\n"
            "## Architecture Impact\n"
            "- 模块边界\n"
            "- 数据流\n"
            "- 兼容性\n\n"
            "## Risks & Mitigations\n"
            "- 风险1: <描述> -> 缓解: <策略>\n"
            "- 风险2: <描述> -> 缓解: <策略>\n\n"
            "## Rollout Strategy\n"
            "- 阶段发布与回滚方案\n"
            "- 观测与告警策略\n"
        )

    def _render_tasks_template(self, *, title: str) -> str:
        return (
            f"# Tasks: {title}\n\n"
            "## 1. Discovery & Design\n"
            "- [ ] 1.1 梳理边界与验收标准\n"
            "- [ ] 1.2 输出实现设计与风险评估\n\n"
            "## 2. Implementation\n"
            "- [ ] 2.1 完成核心能力实现\n"
            "- [ ] 2.2 完成失败路径与恢复逻辑\n\n"
            "## 3. Quality\n"
            "- [ ] 3.1 补齐单元与集成测试\n"
            "- [ ] 3.2 执行回归与验收验证\n\n"
            "## 4. Delivery\n"
            "- [ ] 4.1 更新文档与变更说明\n"
            "- [ ] 4.2 完成交付检查清单\n"
        )

    def _render_checklist_template(self) -> str:
        return (
            "# Checklist\n\n"
            "## Before Merge\n"
            "- [ ] 规范与任务一致\n"
            "- [ ] 所有 MUST 场景均有测试\n"
            "- [ ] 风险与回滚策略已确认\n\n"
            "## Release Readiness\n"
            "- [ ] 质量门禁通过\n"
            "- [ ] 观测指标与告警已配置\n"
            "- [ ] 发布说明已准备\n"
        )
