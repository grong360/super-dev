import json
from pathlib import Path

from super_dev.review_state import (
    save_baseline_confirmation,
    save_docs_confirmation,
    save_host_runtime_validation,
    save_resume_gate,
    save_workflow_state,
    workflow_event_log_file,
)


def test_save_workflow_state_appends_event_log(temp_project_dir: Path) -> None:
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "revise",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )

    event_log = workflow_event_log_file(temp_project_dir)

    assert event_log.exists()
    lines = [line for line in event_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["event"] == "workflow_state_saved"
    assert payload["status"] == "waiting_docs_confirmation"
    assert payload["current_step_label"] == "等待三文档确认"


def test_review_state_updates_append_semantic_events(temp_project_dir: Path) -> None:
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "current_step_label": "等待 baseline 确认",
        },
    )
    save_docs_confirmation(
        temp_project_dir,
        {
            "status": "confirmed",
            "current_step_label": "三文档已确认",
        },
    )
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "current_step_label": "等待恢复点确认",
        },
    )
    save_host_runtime_validation(
        temp_project_dir,
        {
            "status": "ready",
            "current_step_label": "宿主运行时验证通过",
        },
    )

    event_log = workflow_event_log_file(temp_project_dir)
    events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert [item["event"] for item in events[-4:]] == [
        "baseline_confirmation_saved",
        "docs_confirmation_saved",
        "resume_gate_saved",
        "host_runtime_validation_saved",
    ]
    assert events[-4]["review_type"] == "baseline_confirmation"
    assert events[-3]["review_type"] == "docs_confirmation"
    assert events[-2]["review_type"] == "resume_gate"
    assert events[-1]["review_type"] == "host_runtime_validation"
