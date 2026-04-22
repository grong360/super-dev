from pathlib import Path

import pytest

from super_dev.creators import ImplementationScaffoldBuilder, SpecBuilder, SpecTaskExecutor
from super_dev.specs import ChangeManager
from super_dev.specs.models import ChangeStatus, TaskStatus
from super_dev.workflow_guard import (
    WorkflowGateError,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)


def test_task_executor_completes_generated_change(temp_project_dir: Path) -> None:
    requirements = [
        {
            "spec_name": "auth",
            "req_name": "user-login",
            "description": "support user login",
            "scenarios": [],
        },
        {
            "spec_name": "dashboard",
            "req_name": "show-metrics",
            "description": "show dashboard metrics",
            "scenarios": [],
        },
    ]
    tech_stack = {"platform": "web", "frontend": "react", "backend": "node", "domain": "auth"}

    spec_builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="demo-task-exec",
        description="demo task execution",
    )
    change_id = spec_builder.create_change(requirements, tech_stack, scenario="0-1")

    implementation_builder = ImplementationScaffoldBuilder(
        project_dir=temp_project_dir,
        name="demo-task-exec",
        frontend="react",
        backend="node",
    )
    implementation_builder.generate(requirements=requirements)

    executor = SpecTaskExecutor(project_dir=temp_project_dir, project_name="demo-task-exec")
    summary = executor.execute(change_id=change_id, tech_stack=tech_stack, max_retries=1)

    assert summary.total_tasks > 0
    assert summary.completed_tasks == summary.total_tasks
    report_path = Path(summary.report_file)
    assert report_path.exists()
    assert report_path.name == "demo-task-exec-task-execution.md"
    report = report_path.read_text(encoding="utf-8")
    assert "## 执行期验证摘要" in report
    assert "## 宿主补充自检（交付前必做）" in report
    assert "新增函数、方法、字段、模块都已接入真实调用链" in report

    change = ChangeManager(temp_project_dir).load_change(change_id)
    assert change is not None
    assert change.status == ChangeStatus.COMPLETED
    assert all(task.status == TaskStatus.COMPLETED for task in change.tasks)


def test_task_executor_uses_spec_refs_from_tasks_file(temp_project_dir: Path) -> None:
    change_dir = temp_project_dir / ".super-dev" / "changes" / "meta-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "change.yaml").write_text(
        (
            "id: meta-change\n"
            "title: Meta Change\n"
            "status: proposed\n"
            "created_at: 2026-03-02T00:00:00\n"
            "updated_at: 2026-03-02T00:00:00\n"
        ),
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        (
            "# Tasks\n\n"
            "## 2. Frontend\n\n"
            "- [ ] **2.1: 实现 auth 前端模块**\n"
            "  - Refs: `auth::*`\n\n"
            "- [ ] **2.2: 实现 dashboard 前端模块**\n"
            "  - Refs: `dashboard::*`\n"
        ),
        encoding="utf-8",
    )

    executor = SpecTaskExecutor(project_dir=temp_project_dir, project_name="meta-change")
    summary = executor.execute(
        change_id="meta-change",
        tech_stack={"platform": "web", "frontend": "react", "backend": "node", "domain": "general"},
        max_retries=0,
    )

    assert summary.failed_tasks == []
    assert summary.completed_tasks == summary.total_tasks == 2
    assert (temp_project_dir / "frontend" / "src" / "modules" / "auth.tsx").exists()
    assert (temp_project_dir / "frontend" / "src" / "modules" / "dashboard.tsx").exists()
    assert not (temp_project_dir / "frontend" / "src" / "modules" / "core.tsx").exists()


def test_task_executor_respects_dependencies(temp_project_dir: Path) -> None:
    change_dir = temp_project_dir / ".super-dev" / "changes" / "dep-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "change.yaml").write_text(
        (
            "id: dep-change\n"
            "title: Dep Change\n"
            "status: proposed\n"
            "created_at: 2026-03-02T00:00:00\n"
            "updated_at: 2026-03-02T00:00:00\n"
        ),
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        (
            "# Tasks\n\n"
            "## 4. Integration & Quality\n\n"
            "- [ ] **4.1: 执行质量门禁前检查**\n"
            "  - Depends on: 4.2\n\n"
            "- [ ] **4.2: 完成端到端联调**\n"
        ),
        encoding="utf-8",
    )

    executor = SpecTaskExecutor(project_dir=temp_project_dir, project_name="dep-change")
    summary = executor.execute(
        change_id="dep-change",
        tech_stack={"platform": "web", "frontend": "react", "backend": "node", "domain": "general"},
        max_retries=0,
    )

    assert set(summary.failed_tasks) == {"4.1", "4.2"}
    change = ChangeManager(temp_project_dir).load_change("dep-change")
    assert change is not None
    statuses = {task.id: task.status for task in change.tasks}
    assert statuses["4.1"] == TaskStatus.PENDING
    assert statuses["4.2"] == TaskStatus.IN_PROGRESS


def test_spec_builder_requires_docs_confirmation_when_docs_context_exists(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
    (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
    (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")

    spec_builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="demo-task-exec",
        description="demo task execution",
    )

    with pytest.raises(WorkflowGateError):
        spec_builder.create_change(
            requirements=[
                {
                    "spec_name": "auth",
                    "req_name": "user-login",
                    "description": "support user login",
                    "scenarios": [],
                }
            ],
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "auth",
            },
            scenario="0-1",
        )


def test_task_executor_requires_docs_confirmation_when_docs_context_exists(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
    (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
    (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")

    change_dir = temp_project_dir / ".super-dev" / "changes" / "blocked-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "change.yaml").write_text(
        (
            "id: blocked-change\n"
            "title: Blocked Change\n"
            "status: proposed\n"
            "created_at: 2026-03-02T00:00:00\n"
            "updated_at: 2026-03-02T00:00:00\n"
        ),
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] **2.1: 实现 auth 前端模块**\n  - Refs: `auth::*`\n",
        encoding="utf-8",
    )

    executor = SpecTaskExecutor(project_dir=temp_project_dir, project_name="blocked-change")
    with pytest.raises(WorkflowGateError):
        executor.execute(
            change_id="blocked-change",
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "general",
            },
            max_retries=0,
        )

    save_bound_docs_confirmation(
        temp_project_dir,
        {"status": "confirmed", "comment": "ok", "actor": "pytest", "run_id": "docs-ok"},
    )

    summary = executor.execute(
        change_id="blocked-change",
        tech_stack={
            "platform": "web",
            "frontend": "react",
            "backend": "node",
            "domain": "general",
        },
        max_retries=0,
    )
    assert summary.completed_tasks == 1

    (output_dir / "demo-uiux.md").write_text("# uiux v2", encoding="utf-8")
    with pytest.raises(WorkflowGateError):
        executor.execute(
            change_id="blocked-change",
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "general",
            },
            max_retries=0,
        )


def test_task_executor_requires_preview_confirmation_for_backend_and_quality_tasks(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
    (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
    (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
    (output_dir / "preview.html").write_text("<main>preview</main>", encoding="utf-8")
    (output_dir / "preview-blocked-change-ui-contract.json").write_text(
        '{"style_direction":{"direction":"可信商业产品"}}',
        encoding="utf-8",
    )

    change_dir = temp_project_dir / ".super-dev" / "changes" / "preview-blocked-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "change.yaml").write_text(
        (
            "id: preview-blocked-change\n"
            "title: Preview Blocked Change\n"
            "status: proposed\n"
            "created_at: 2026-03-02T00:00:00\n"
            "updated_at: 2026-03-02T00:00:00\n"
        ),
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        (
            "# Tasks\n\n"
            "- [ ] **2.1: 实现 auth 前端模块**\n"
            "  - Refs: `auth::*`\n\n"
            "- [ ] **3.1: 实现 auth 后端模块**\n"
            "  - Refs: `auth::*`\n\n"
            "- [ ] **4.1: 执行质量验证**\n"
        ),
        encoding="utf-8",
    )

    save_bound_docs_confirmation(
        temp_project_dir,
        {"status": "confirmed", "comment": "ok", "actor": "pytest", "run_id": "docs-ok"},
    )

    executor = SpecTaskExecutor(
        project_dir=temp_project_dir,
        project_name="preview-blocked-change",
    )
    with pytest.raises(WorkflowGateError) as exc_info:
        executor.execute(
            change_id="preview-blocked-change",
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "general",
            },
            max_retries=0,
        )
    assert exc_info.value.gate == "preview_confirmation"

    save_bound_preview_confirmation(
        temp_project_dir,
        {"status": "confirmed", "comment": "ok", "actor": "pytest", "run_id": "preview-ok"},
    )

    summary = executor.execute(
        change_id="preview-blocked-change",
        tech_stack={
            "platform": "web",
            "frontend": "react",
            "backend": "node",
            "domain": "general",
        },
        max_retries=0,
    )
    assert summary.completed_tasks == summary.total_tasks
