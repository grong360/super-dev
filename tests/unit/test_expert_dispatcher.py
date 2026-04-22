from __future__ import annotations

import asyncio
from pathlib import Path

from super_dev.orchestrator.experts import ExpertDispatcher


def test_async_document_generation_keeps_expert_context_and_quality_checks(
    temp_project_dir: Path, monkeypatch
) -> None:
    contexts: list[tuple[str, str]] = []
    quality_checks: list[str] = []

    class FakeDocumentGenerator:
        def __init__(self, *args, **kwargs):
            self.expert_context = None

        def generate_prd(self):
            contexts.append(("prd", self.expert_context["role"]))
            return "# 产品愿景\n# 功能需求\n# 验收标准"

        def generate_architecture(self):
            contexts.append(("architecture", self.expert_context["role"]))
            return "# 技术栈\n# 数据库\n# API\n# 安全"

        def generate_uiux(self):
            contexts.append(("uiux", self.expert_context["role"]))
            return "# 设计系统\n# 色彩\n# 组件"

    monkeypatch.setattr(
        "super_dev.creators.document_generator.DocumentGenerator",
        FakeDocumentGenerator,
    )
    monkeypatch.setattr(
        ExpertDispatcher,
        "_score_document",
        lambda self, content, required_sections: 80,
    )

    def fake_quality_check(self, content, profile, base_score):
        quality_checks.append(profile.role.value)
        return base_score + 5

    monkeypatch.setattr(ExpertDispatcher, "_expert_quality_check", fake_quality_check)

    dispatcher = ExpertDispatcher(temp_project_dir)
    result = asyncio.run(
        dispatcher.dispatch_document_generation_async(
            name="demo",
            description="商业项目",
            platform="web",
            frontend="react",
            backend="node",
            domain="saas",
        )
    )

    assert len(result.outputs) == 3
    assert {item.metadata.get("expert_active") for item in result.outputs} == {True}
    assert {doc_type for doc_type, _ in contexts} == {"prd", "architecture", "uiux"}
    assert {role for _, role in contexts} == {"产品经理", "架构师", "UI 设计师"}
    assert set(quality_checks) == {"PM", "ARCHITECT", "UI"}
    assert all(item.quality_score == 85 for item in result.outputs)
