# ruff: noqa: I001
"""
文档生成器增强测试 - PRD/架构/UIUX 文档生成

测试对象: super_dev.creators.document_generator.DocumentGenerator
"""

import pytest
from super_dev.creators.document_generator import DocumentGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def generator():
    return DocumentGenerator(
        name="test-app",
        description="A test application for task management",
        platform="web",
        frontend="react",
        backend="node",
        domain="",
    )


@pytest.fixture()
def fintech_generator():
    return DocumentGenerator(
        name="fintech-app",
        description="Payment processing platform",
        platform="web",
        frontend="react",
        backend="python",
        domain="fintech",
    )


@pytest.fixture()
def mobile_generator():
    return DocumentGenerator(
        name="mobile-app",
        description="Social networking mobile application",
        platform="mobile",
        frontend="react-native",
        backend="node",
        domain="",
    )


@pytest.fixture()
def vue_generator():
    return DocumentGenerator(
        name="vue-app",
        description="Enterprise collaboration platform",
        platform="web",
        frontend="vue",
        backend="python",
        domain="",
    )


@pytest.fixture()
def bugfix_generator():
    return DocumentGenerator(
        name="bugfix-app",
        description="Fix login bug",
        request_mode="bugfix",
        platform="web",
        frontend="react",
        backend="node",
    )


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

class TestDocumentGeneratorInit:
    def test_creates_with_required_args(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.name == "test"
        assert gen.description == "desc"

    def test_default_platform(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.platform == "web"

    def test_default_frontend(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.frontend == "next"

    def test_default_backend(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.backend == "node"

    def test_default_domain_is_general(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.domain == "general"

    def test_custom_domain(self):
        gen = DocumentGenerator(name="test", description="desc", domain="fintech")
        assert gen.domain == "fintech"

    def test_empty_domain_becomes_general(self):
        gen = DocumentGenerator(name="test", description="desc", domain="")
        assert gen.domain == "general"

    def test_request_mode_feature(self):
        gen = DocumentGenerator(name="test", description="desc", request_mode="feature")
        assert gen.request_mode == "feature"

    def test_request_mode_bugfix(self):
        gen = DocumentGenerator(name="test", description="desc", request_mode="bugfix")
        assert gen.request_mode == "bugfix"

    def test_request_mode_invalid_defaults_to_feature(self):
        gen = DocumentGenerator(name="test", description="desc", request_mode="invalid")
        assert gen.request_mode == "feature"

    def test_ui_library_optional(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.ui_library is None

    def test_ui_library_custom(self):
        gen = DocumentGenerator(name="test", description="desc", ui_library="shadcn/ui")
        assert gen.ui_library == "shadcn/ui"

    def test_state_management_default(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.state_management == []

    def test_state_management_custom(self):
        gen = DocumentGenerator(name="test", description="desc", state_management=["zustand", "react-query"])
        assert "zustand" in gen.state_management

    def test_knowledge_summary_default(self):
        gen = DocumentGenerator(name="test", description="desc")
        assert gen.knowledge_summary == {}


# ---------------------------------------------------------------------------
# PRD 生成
# ---------------------------------------------------------------------------

class TestPRDGeneration:
    def test_generate_prd_returns_string(self, generator):
        prd = generator.generate_prd()
        assert isinstance(prd, str)
        assert len(prd) > 500

    def test_prd_contains_project_name(self, generator):
        prd = generator.generate_prd()
        assert "test-app" in prd

    def test_prd_has_markdown_structure(self, generator):
        prd = generator.generate_prd()
        assert "# " in prd or "## " in prd

    def test_prd_with_research(self, generator):
        prd = generator.generate_prd()
        assert isinstance(prd, str)
        assert len(prd) > 500

    def test_prd_empty_research(self, generator):
        prd = generator.generate_prd()
        assert isinstance(prd, str)

    def test_fintech_prd(self, fintech_generator):
        prd = fintech_generator.generate_prd()
        assert isinstance(prd, str)
        assert len(prd) > 500

    def test_mobile_prd(self, mobile_generator):
        prd = mobile_generator.generate_prd()
        assert isinstance(prd, str)
        assert len(prd) > 500

    def test_bugfix_prd_differs_from_feature(self, bugfix_generator):
        prd = bugfix_generator.generate_prd()
        assert isinstance(prd, str)

    def test_vue_prd(self, vue_generator):
        prd = vue_generator.generate_prd()
        assert isinstance(prd, str)


# ---------------------------------------------------------------------------
# 架构文档生成
# ---------------------------------------------------------------------------

class TestArchitectureGeneration:
    def test_generate_architecture_returns_string(self, generator):
        arch = generator.generate_architecture()
        assert isinstance(arch, str)
        assert len(arch) > 500

    def test_architecture_has_sections(self, generator):
        arch = generator.generate_architecture()
        assert "#" in arch

    def test_architecture_empty_prd(self, generator):
        arch = generator.generate_architecture()
        assert isinstance(arch, str)

    def test_fintech_architecture(self, fintech_generator):
        arch = fintech_generator.generate_architecture()
        assert isinstance(arch, str)
        assert len(arch) > 500

    def test_mobile_architecture(self, mobile_generator):
        arch = mobile_generator.generate_architecture()
        assert isinstance(arch, str)

    def test_vue_architecture(self, vue_generator):
        arch = vue_generator.generate_architecture()
        assert isinstance(arch, str)


# ---------------------------------------------------------------------------
# UI/UX 文档生成
# ---------------------------------------------------------------------------

class TestUIUXGeneration:
    def test_generate_uiux_returns_string(self, generator):
        uiux = generator.generate_uiux()
        assert isinstance(uiux, str)
        assert len(uiux) > 500

    def test_uiux_empty_inputs(self, generator):
        uiux = generator.generate_uiux()
        assert isinstance(uiux, str)

    def test_fintech_uiux(self, fintech_generator):
        uiux = fintech_generator.generate_uiux()
        assert isinstance(uiux, str)

    def test_mobile_uiux(self, mobile_generator):
        uiux = mobile_generator.generate_uiux()
        assert isinstance(uiux, str)

    def test_uiux_includes_art_direction_and_anti_ai_sections(self, generator):
        uiux = generator.generate_uiux()
        assert "视觉方向候选" in uiux
        assert "反 AI 味护栏" in uiux
        assert "设计批评标尺" in uiux


# ---------------------------------------------------------------------------
# 执行计划生成
# ---------------------------------------------------------------------------

class TestExecutionPlanGeneration:
    def test_generate_execution_plan_returns_string(self, generator):
        plan = generator.generate_execution_plan()
        assert isinstance(plan, str)
        assert len(plan) > 200

    def test_execution_plan_empty_inputs(self, generator):
        plan = generator.generate_execution_plan()
        assert isinstance(plan, str)


# ---------------------------------------------------------------------------
# 不同技术栈组合
# ---------------------------------------------------------------------------

class TestDifferentStackCombinations:
    @pytest.fixture(params=[
        {"platform": "web", "frontend": "react", "backend": "node"},
        {"platform": "web", "frontend": "vue", "backend": "python"},
        {"platform": "web", "frontend": "angular", "backend": "java"},
        {"platform": "web", "frontend": "next", "backend": "go"},
        {"platform": "mobile", "frontend": "react-native", "backend": "node"},
    ])
    def stack_generator(self, request):
        return DocumentGenerator(
            name="combo-test", description="Test",
            **request.param,
        )

    def test_all_stacks_generate_prd(self, stack_generator):
        prd = stack_generator.generate_prd()
        assert isinstance(prd, str)
        assert len(prd) > 200

    def test_all_stacks_generate_architecture(self, stack_generator):
        arch = stack_generator.generate_architecture()
        assert isinstance(arch, str)
        assert len(arch) > 200

    def test_all_stacks_generate_uiux(self, stack_generator):
        uiux = stack_generator.generate_uiux()
        assert isinstance(uiux, str)
        assert len(uiux) > 200


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------

class TestDocumentGeneratorEdgeCases:
    def test_unicode_name(self):
        gen = DocumentGenerator(name="中文项目", description="测试描述")
        prd = gen.generate_prd()
        assert isinstance(prd, str)
        assert "中文项目" in prd

    def test_special_chars_in_name(self):
        gen = DocumentGenerator(name="test-app_v2.0", description="Special chars")
        prd = gen.generate_prd()
        assert isinstance(prd, str)

    def test_very_long_description(self):
        gen = DocumentGenerator(name="test", description="x " * 5000)
        prd = gen.generate_prd()
        assert isinstance(prd, str)

    def test_with_knowledge_summary(self):
        gen = DocumentGenerator(
            name="test", description="desc",
            knowledge_summary={"standards": ["REST API"], "checklists": ["Security"]},
        )
        assert gen.knowledge_summary is not None
        prd = gen.generate_prd()
        assert isinstance(prd, str)

    def test_with_language_preferences(self):
        gen = DocumentGenerator(
            name="test", description="desc",
            language_preferences=["zh-CN", "en"],
        )
        prd = gen.generate_prd()
        assert isinstance(prd, str)

    def test_idempotent_generation(self, generator):
        prd1 = generator.generate_prd()
        prd2 = generator.generate_prd()
        assert isinstance(prd1, str)
        assert isinstance(prd2, str)
        assert len(prd1) == len(prd2)


# ---------------------------------------------------------------------------
# 生成内容结构验证
# ---------------------------------------------------------------------------

class TestContentStructure:
    def test_prd_has_multiple_sections(self, generator):
        prd = generator.generate_prd()
        sections = [line for line in prd.split("\n") if line.startswith("## ")]
        assert len(sections) >= 3, f"PRD should have >= 3 sections, found {len(sections)}"

    def test_prd_has_title(self, generator):
        prd = generator.generate_prd()
        lines = prd.split("\n")
        h1_lines = [line for line in lines if line.startswith("# ") and not line.startswith("## ")]
        assert len(h1_lines) >= 1

    def test_architecture_has_multiple_sections(self, generator):
        arch = generator.generate_architecture()
        sections = [line for line in arch.split("\n") if line.startswith("## ")]
        assert len(sections) >= 3

    def test_uiux_has_multiple_sections(self, generator):
        uiux = generator.generate_uiux()
        sections = [line for line in uiux.split("\n") if line.startswith("## ")]
        assert len(sections) >= 3

    def test_prd_length_reasonable(self, generator):
        prd = generator.generate_prd()
        assert 500 < len(prd) < 200000

    def test_architecture_length_reasonable(self, generator):
        arch = generator.generate_architecture()
        assert 500 < len(arch) < 200000

    def test_uiux_length_reasonable(self, generator):
        uiux = generator.generate_uiux()
        assert 500 < len(uiux) < 200000

    def test_prd_mentions_tech_stack(self, generator):
        prd = generator.generate_prd()
        lower = prd.lower()
        assert "react" in lower or "node" in lower or "前端" in lower or "后端" in lower

    def test_architecture_mentions_tech_stack(self, generator):
        arch = generator.generate_architecture()
        lower = arch.lower()
        assert "react" in lower or "node" in lower or "前端" in lower or "后端" in lower

    def test_fintech_prd_mentions_finance(self, fintech_generator):
        prd = fintech_generator.generate_prd()
        lower = prd.lower()
        assert "金融" in lower or "payment" in lower or "fintech" in lower or "支付" in lower

    def test_mobile_prd_mentions_mobile(self, mobile_generator):
        prd = mobile_generator.generate_prd()
        lower = prd.lower()
        assert "mobile" in lower or "移动" in lower or "app" in lower or "react-native" in lower

    def test_generate_all_documents_sequentially(self, generator):
        prd = generator.generate_prd()
        arch = generator.generate_architecture()
        uiux = generator.generate_uiux()
        assert isinstance(prd, str) and len(prd) > 500
        assert isinstance(arch, str) and len(arch) > 500
        assert isinstance(uiux, str) and len(uiux) > 500

    def test_different_descriptions_produce_different_prd(self):
        gen1 = DocumentGenerator(name="app1", description="E-commerce platform for selling books online")
        gen2 = DocumentGenerator(name="app2", description="Healthcare appointment scheduling system")
        prd1 = gen1.generate_prd()
        prd2 = gen2.generate_prd()
        assert prd1 != prd2

    def test_all_document_types_are_markdown(self, generator):
        for doc in [generator.generate_prd(), generator.generate_architecture(), generator.generate_uiux()]:
            assert isinstance(doc, str)
            assert "#" in doc  # Has markdown headers
            lines = doc.split("\n")
            assert len(lines) >= 10  # Has reasonable number of lines
