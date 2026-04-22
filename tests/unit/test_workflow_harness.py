import json
from pathlib import Path

from super_dev.harness_registry import derive_operational_focus
from super_dev.review_state import save_workflow_state, workflow_event_log_file
from super_dev.workflow_harness import WorkflowHarnessBuilder


def test_workflow_harness_disabled_without_any_trail(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)

    report = WorkflowHarnessBuilder(project_dir).build()

    assert report.enabled is False
    assert report.passed is False


def test_workflow_harness_passes_with_state_snapshots_and_events(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    save_workflow_state(
        project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "continue",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )

    builder = WorkflowHarnessBuilder(project_dir)
    report = builder.build()
    files = builder.write(report)

    assert report.enabled is True
    assert report.passed is True
    assert report.checks["workflow_state_present"] is True
    assert report.checks["workflow_snapshots_present"] is True
    assert report.checks["workflow_events_present"] is True
    assert report.checks["operational_timeline_present"] is True
    assert report.recent_timeline
    assert Path(files["json"]).exists()
    payload = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["recent_timeline"]
    markdown = Path(files["markdown"]).read_text(encoding="utf-8")
    assert "流程状态已保存" in markdown
    assert "## Recent Timeline" in markdown


def test_workflow_harness_blocks_when_event_log_missing(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    save_workflow_state(
        project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "continue",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )
    workflow_event_log_file(project_dir).unlink()

    report = WorkflowHarnessBuilder(project_dir).build()

    assert report.enabled is True
    assert report.passed is False
    assert report.checks["workflow_events_present"] is False
    assert report.checks["operational_timeline_present"] is True
    assert any("workflow-events.jsonl" in item for item in report.blockers)


def test_derive_operational_focus_prefers_first_failing_harness(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    save_workflow_state(
        project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "continue",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )
    workflow_event_log_file(project_dir).unlink()

    focus = derive_operational_focus(project_dir)

    assert focus["status"] == "needs_attention"
    assert focus["kind"] == "workflow"
    assert focus["summary"]
