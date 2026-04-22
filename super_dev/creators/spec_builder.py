"""
Spec 构建器 - 自动创建 Spec 规范

开发：Excellent（11964948@qq.com）
功能：从需求自动创建完整的 Spec 变更提案
作用：按结构化规范自动分解任务、定义场景
创建时间：2025-12-30
"""

from pathlib import Path

from ..specs import ChangeManager, SpecGenerator, SpecManager
from ..specs.models import DeltaType, Task, TaskStatus
from ..workflow_guard import require_docs_confirmation
from .requirement_parser import RequirementParser


class SpecBuilder:
    """Spec 构建器 - 自动创建 Spec 规范"""

    def __init__(self, project_dir: Path, name: str, description: str):
        """初始化 Spec 构建器"""
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.description = description

        self.spec_generator = SpecGenerator(self.project_dir)
        self.change_manager = ChangeManager(self.project_dir)
        self.spec_manager = SpecManager(self.project_dir)
        self.requirement_parser = RequirementParser()

    def create_change(
        self,
        requirements: list,
        tech_stack: dict,
        scenario: str | None = None,
    ) -> str:
        """创建 Spec 变更提案"""
        require_docs_confirmation(
            self.project_dir,
            action="spec_builder_create_change",
            require_context=True,
        )

        # 初始化 SDD 目录
        self.spec_generator.init_sdd()

        if scenario is None:
            scenario = self.requirement_parser.detect_scenario(self.project_dir)

        # 生成变更 ID (从项目名称转换)
        change_id = self.name.replace("_", "-").lower()

        # 1. 创建变更提案
        self.spec_generator.create_change(
            change_id=change_id,
            title=self.name.replace("-", " ").title(),
            description=self.description,
            motivation="用户需求驱动的功能开发",
            impact=f"涉及 {len(requirements)} 个主要功能模块",
        )

        # 2. 添加需求到变更
        for idx, req in enumerate(requirements):
            self.spec_generator.add_requirement_to_change(
                change_id=change_id,
                spec_name=req.get("spec_name", change_id),
                requirement_name=req.get("req_name", f"req-{idx}"),
                description=req.get("description", ""),
                scenarios=req.get("scenarios", []),
                delta_type=DeltaType.ADDED,
            )

        # 3. 自动生成任务
        self._generate_tasks_for_change(change_id, tech_stack, scenario)

        return change_id

    def _generate_tasks_for_change(self, change_id: str, tech_stack: dict, scenario: str):
        """为变更自动生成任务"""
        change = self.change_manager.load_change(change_id)
        if not change:
            return

        tasks = []
        major = 1

        # 根据技术栈生成任务
        backend = tech_stack.get("backend", "node")
        frontend = tech_stack.get("frontend", "react")

        if scenario == "0-1":
            tasks.extend(
                [
                    Task(
                        id=f"{major}.1",
                        title="冻结需求与文档版本",
                        description="确认 PRD、架构与 UIUX 文档的 v1 版本，避免需求漂移。",
                        status=TaskStatus.PENDING,
                        spec_refs=["core::*"],
                    ),
                    Task(
                        id=f"{major}.2",
                        title="定义前后端接口草案",
                        description="在编码前输出关键页面与 API 的契约字段。",
                        status=TaskStatus.PENDING,
                        spec_refs=["core::*"],
                    ),
                ]
            )
            major += 1
        else:
            tasks.extend(
                [
                    Task(
                        id=f"{major}.1",
                        title="梳理增量变更影响范围",
                        description="明确兼容性、风险点和回滚策略。",
                        status=TaskStatus.PENDING,
                        spec_refs=["core::*"],
                    ),
                    Task(
                        id=f"{major}.2",
                        title="确定灰度与开关策略",
                        description="对增量功能设计灰度发布与快速回滚方案。",
                        status=TaskStatus.PENDING,
                        spec_refs=["core::*"],
                    ),
                ]
            )
            major += 1

        # 前端优先任务
        if frontend != "none":
            minor = 0
            for delta in change.spec_deltas:
                minor += 1
                tasks.append(
                    Task(
                        id=f"{major}.{minor}",
                        title=f"实现 {delta.spec_name} 前端模块",
                        description=f"先交付 {delta.spec_name} 的页面框架、核心组件与交互流程。",
                        status=TaskStatus.PENDING,
                        spec_refs=[f"{delta.spec_name}::*"],
                    )
                )
            major += 1

        # 后端与数据任务
        if backend != "none":
            minor = 0
            for delta in change.spec_deltas:
                minor += 1
                tasks.append(
                    Task(
                        id=f"{major}.{minor}",
                        title=f"实现 {delta.spec_name} 后端能力",
                        description=f"完成 {delta.spec_name} 的 API、数据模型和权限控制。",
                        status=TaskStatus.PENDING,
                        spec_refs=[f"{delta.spec_name}::*"],
                    )
                )
            major += 1

        # 联调与稳定性任务
        tasks.append(
            Task(
                id=f"{major}.1",
                title="完成端到端联调",
                description="对关键链路进行联调，修复接口与交互偏差。",
                status=TaskStatus.PENDING,
                spec_refs=["core::*"],
            )
        )
        tasks.append(
            Task(
                id=f"{major}.2",
                title="执行质量门禁前检查",
                description="完成安全、性能、可用性预检查并修复阻塞项。",
                status=TaskStatus.PENDING,
                spec_refs=["core::*"],
            )
        )
        major += 1

        # 测试任务
        minor = 0
        for delta in change.spec_deltas:
            minor += 1
            tasks.append(
                Task(
                    id=f"{major}.{minor}",
                    title=f"测试 {delta.spec_name} 功能",
                    description=f"编写并执行 {delta.spec_name} 的单元、集成与回归测试。",
                    status=TaskStatus.PENDING,
                    spec_refs=[f"{delta.spec_name}::*"],
                )
            )

        # 更新变更
        change.tasks = tasks
        self.change_manager.save_change(change)
