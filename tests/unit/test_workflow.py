"""
Super Dev 工作流引擎单元测试
"""

import json
from pathlib import Path

import pytest

from super_dev.config import ConfigManager, ProjectConfig
from super_dev.orchestrator import Phase, PhaseResult, WorkflowContext, WorkflowEngine
from super_dev.workflow_guard import save_bound_docs_confirmation, save_bound_preview_confirmation


def _prepare_confirmed_workflow_gates(project_dir: Path) -> None:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{project_dir.name}-prd.md").write_text("# prd\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-architecture.md").write_text("# arch\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-uiux.md").write_text("# uiux\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-frontend-runtime.json").write_text(
        json.dumps({"passed": True}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_bound_docs_confirmation(project_dir, {"status": "confirmed"})
    save_bound_preview_confirmation(project_dir, {"status": "confirmed"})


class TestPhase:
    """测试 Phase 枚举"""

    def test_phase_values(self):
        """测试阶段值"""
        assert Phase.DISCOVERY.value == "discovery"
        assert Phase.INTELLIGENCE.value == "intelligence"
        assert Phase.DRAFTING.value == "drafting"
        assert Phase.REDTEAM.value == "redteam"
        assert Phase.QA.value == "qa"
        assert Phase.DELIVERY.value == "delivery"
        assert Phase.DEPLOYMENT.value == "deployment"


class TestPhaseResult:
    """测试 PhaseResult"""

    def test_successful_result(self):
        """测试成功结果"""
        result = PhaseResult(
            phase=Phase.DISCOVERY,
            success=True,
            duration=1.5,
            quality_score=85.0,
            output={"data": "test"}
        )

        assert result.phase == Phase.DISCOVERY
        assert result.success
        assert result.duration == 1.5
        assert result.quality_score == 85.0
        assert len(result.errors) == 0

    def test_failed_result(self):
        """测试失败结果"""
        result = PhaseResult(
            phase=Phase.INTELLIGENCE,
            success=False,
            duration=0.5,
            errors=["Error 1", "Error 2"]
        )

        assert not result.success
        assert len(result.errors) == 2


class TestWorkflowContext:
    """测试 WorkflowContext"""

    def test_context_creation(self, temp_project_dir: Path):
        """测试上下文创建"""
        config = ProjectConfig(name="test")
        context = WorkflowContext(
            project_dir=temp_project_dir,
            config=config  # type: ignore
        )

        assert context.project_dir == temp_project_dir
        assert context.config.name == "test"
        assert len(context.results) == 0
        assert len(context.metadata) == 0

    def test_context_shared_data(self, temp_project_dir: Path):
        """测试共享数据"""
        config = ProjectConfig(name="test")
        context = WorkflowContext(
            project_dir=temp_project_dir,
            config=config  # type: ignore
        )

        context.user_input["requirement"] = "test input"
        context.research_data["market"] = "test data"

        assert context.user_input["requirement"] == "test input"
        assert context.research_data["market"] == "test data"


class TestWorkflowEngine:
    """测试 WorkflowEngine"""

    def test_engine_initialization(self, temp_project_dir: Path):
        """测试引擎初始化"""
        engine = WorkflowEngine(temp_project_dir)

        assert engine.project_dir == temp_project_dir
        assert engine.config_manager is not None

    def test_get_phases_from_config(self, temp_project_dir: Path):
        """测试从配置获取阶段"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(
            name="test",
            phases=["discovery", "intelligence", "drafting"]
        )

        engine = WorkflowEngine(temp_project_dir)
        phases = engine._get_phases_from_config()

        # 获取阶段时会合并默认配置
        assert len(phases) >= 3
        assert Phase.DISCOVERY in phases
        assert Phase.INTELLIGENCE in phases
        assert Phase.DRAFTING in phases

    def test_get_phases_from_config_accepts_canonical_stage_names(self, temp_project_dir: Path):
        """测试从 canonical 阶段名展开 engine phases"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(
            name="test",
            phases=["research", "docs", "quality", "delivery_full"],
        )

        engine = WorkflowEngine(temp_project_dir)
        phases = engine._get_phases_from_config()

        assert phases == [
            Phase.DISCOVERY,
            Phase.INTELLIGENCE,
            Phase.DRAFTING,
            Phase.REDTEAM,
            Phase.QA,
            Phase.DELIVERY,
            Phase.DEPLOYMENT,
        ]

    def test_register_custom_handler(self, temp_project_dir: Path):
        """测试注册自定义处理器"""
        engine = WorkflowEngine(temp_project_dir)

        async def custom_handler(context):
            return {"custom": "result"}

        engine.register_phase_handler(Phase.DISCOVERY, custom_handler)
        assert Phase.DISCOVERY in engine._phase_handlers
        assert engine._phase_handlers[Phase.DISCOVERY] == custom_handler

    @pytest.mark.asyncio
    async def test_run_single_phase(self, temp_project_dir: Path, workflow_context):
        """测试运行单个阶段"""
        engine = WorkflowEngine(temp_project_dir)

        # 注册测试处理器
        async def test_handler(context):
            return {"test": "data"}

        engine.register_phase_handler(Phase.DISCOVERY, test_handler)

        results = await engine.run(phases=[Phase.DISCOVERY], context=workflow_context)

        assert Phase.DISCOVERY in results
        assert results[Phase.DISCOVERY].success
        assert results[Phase.DISCOVERY].output == {"test": "data"}

    @pytest.mark.asyncio
    async def test_run_multiple_phases(self, temp_project_dir: Path, workflow_context):
        """测试运行多个阶段"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=80)

        engine = WorkflowEngine(temp_project_dir)

        # 注册测试处理器
        async def handler(context):
            return {"handled": True}

        for phase in [Phase.DISCOVERY, Phase.INTELLIGENCE]:
            engine.register_phase_handler(phase, handler)

        # Mock 质量评分引擎，确保本测试聚焦于多阶段流程而非质量评分逻辑
        engine._calculate_quality_score = lambda phase, context: 85.0

        results = await engine.run(
            phases=[Phase.DISCOVERY, Phase.INTELLIGENCE],
            context=workflow_context
        )

        assert len(results) == 2
        assert all(r.success for r in results.values())

    @pytest.mark.asyncio
    async def test_phase_failure_stops_workflow(self, temp_project_dir: Path, workflow_context):
        """测试关键阶段失败停止工作流"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=80)
        _prepare_confirmed_workflow_gates(temp_project_dir)

        engine = WorkflowEngine(temp_project_dir)

        # 第一个阶段成功
        async def success_handler(context):
            return {"status": "ok"}

        # 第二个阶段失败（DRAFTING 是关键阶段，不可跳过）
        async def fail_handler(context):
            raise Exception("Test failure")

        engine.register_phase_handler(Phase.DISCOVERY, success_handler)
        engine.register_phase_handler(Phase.DRAFTING, fail_handler)

        # Mock 质量评分，让 discovery 通过门禁以便测试后续阶段失败逻辑
        engine._calculate_quality_score = lambda phase, context: 88.0

        results = await engine.run(
            phases=[Phase.DISCOVERY, Phase.DRAFTING, Phase.REDTEAM],
            context=workflow_context
        )

        assert results[Phase.DISCOVERY].success
        assert not results[Phase.DRAFTING].success
        # 第三阶段不应该执行
        assert Phase.REDTEAM not in results

    @pytest.mark.asyncio
    async def test_skippable_phase_failure_continues_workflow(self, temp_project_dir: Path, workflow_context):
        """测试可跳过阶段（INTELLIGENCE）失败后工作流继续"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=80)

        engine = WorkflowEngine(temp_project_dir)

        async def success_handler(context):
            return {"status": "ok"}

        async def fail_handler(context):
            raise Exception("Test failure")

        engine.register_phase_handler(Phase.DISCOVERY, success_handler)
        engine.register_phase_handler(Phase.INTELLIGENCE, fail_handler)
        engine.register_phase_handler(Phase.DRAFTING, success_handler)

        engine._calculate_quality_score = lambda phase, context: 88.0

        results = await engine.run(
            phases=[Phase.DISCOVERY, Phase.INTELLIGENCE, Phase.DRAFTING],
            context=workflow_context
        )

        assert results[Phase.DISCOVERY].success
        # INTELLIGENCE 失败但被标记为成功（可跳过）
        assert results[Phase.INTELLIGENCE].success
        assert len(results[Phase.INTELLIGENCE].errors) > 0
        # DRAFTING 应该继续执行
        assert Phase.DRAFTING in results
        assert results[Phase.DRAFTING].success

    @pytest.mark.asyncio
    async def test_quality_gate_check(self, temp_project_dir: Path):
        """测试质量门禁检查"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=90)
        _prepare_confirmed_workflow_gates(temp_project_dir)

        engine = WorkflowEngine(temp_project_dir)
        context = WorkflowContext(
            project_dir=temp_project_dir,
            config=config_manager
        )

        # discovery 低分不应触发门禁
        async def low_score_handler(context):
            from super_dev.orchestrator.engine import PhaseResult
            return PhaseResult(
                phase=Phase.DISCOVERY,
                success=True,
                duration=1.0,
                quality_score=75.0,  # 低于门禁
                output={"status": "low_score"}
            )

        # QA 低分应触发门禁并停止
        async def qa_low_score_handler(context):
            from super_dev.orchestrator.engine import PhaseResult
            return PhaseResult(
                phase=Phase.QA,
                success=True,
                duration=1.0,
                quality_score=85.0,  # 低于门禁 90
                output={"status": "qa_low_score"}
            )

        engine.register_phase_handler(Phase.DISCOVERY, low_score_handler)
        engine.register_phase_handler(Phase.QA, qa_low_score_handler)

        results = await engine.run(
            phases=[Phase.DISCOVERY, Phase.QA, Phase.DELIVERY],
            context=context
        )

        # discovery 不应被门禁阻断
        assert results[Phase.DISCOVERY].success
        # QA 阶段被门禁阻断，且被标记为失败
        assert Phase.QA in results
        assert not results[Phase.QA].success
        assert results[Phase.DISCOVERY].quality_score == 75.0
        # 后续阶段不应执行
        assert Phase.DELIVERY not in results

    @pytest.mark.asyncio
    async def test_redteam_failure_stops_workflow(self, temp_project_dir: Path):
        """测试红队不通过时工作流停止"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=80)
        _prepare_confirmed_workflow_gates(temp_project_dir)

        engine = WorkflowEngine(temp_project_dir)
        context = WorkflowContext(
            project_dir=temp_project_dir,
            config=config_manager
        )

        async def redteam_fail_handler(_context):
            return {
                "status": "redteam_complete",
                "score": 52,
                "passed": False,
                "pass_threshold": 70,
                "blocking_reasons": ["存在 1 个 critical 问题"],
            }

        async def should_not_run(_context):
            return {"status": "qa_complete"}

        engine.register_phase_handler(Phase.REDTEAM, redteam_fail_handler)
        engine.register_phase_handler(Phase.QA, should_not_run)

        results = await engine.run(
            phases=[Phase.REDTEAM, Phase.QA],
            context=context
        )

        assert Phase.REDTEAM in results
        assert not results[Phase.REDTEAM].success
        assert Phase.QA not in results

    @pytest.mark.asyncio
    async def test_deployment_persists_generated_files(self, temp_project_dir: Path):
        """测试部署阶段会落盘生成的 CI/CD 与迁移文件"""
        config_manager = ConfigManager(temp_project_dir)
        config_manager.create(name="test", quality_gate=80)
        _prepare_confirmed_workflow_gates(temp_project_dir)

        engine = WorkflowEngine(temp_project_dir)
        context = WorkflowContext(
            project_dir=temp_project_dir,
            config=config_manager,
            user_input={
                "name": "demo",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "",
            },
        )

        results = await engine.run(phases=[Phase.DEPLOYMENT], context=context)
        assert Phase.DEPLOYMENT in results
        assert results[Phase.DEPLOYMENT].success
        assert (temp_project_dir / ".github" / "workflows" / "ci.yml").exists()
        assert (temp_project_dir / "prisma" / "schema.prisma").exists()
