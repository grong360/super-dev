import json
from pathlib import Path

from super_dev.analyzer import BaselineAuditBuilder
from super_dev.protocols.output_schemas import OutputValidator
from super_dev.review_state import save_workflow_state


def test_baseline_audit_builder_writes_schema_valid_json(temp_project_dir: Path) -> None:
    (temp_project_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "dependencies": {"react": "^19.0.0", "next": "^15.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (temp_project_dir / "components").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "app").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "db").mkdir(parents=True, exist_ok=True)
    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_baseline",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "先建立当前项目 baseline",
            "recommended_command": "先做 baseline scan",
        },
    )

    builder = BaselineAuditBuilder(temp_project_dir)
    report = builder.build()
    files = builder.write(report)

    payload = json.loads(files["json"].read_text(encoding="utf-8"))
    is_valid, errors = OutputValidator().validate(payload, "baseline_audit")

    assert is_valid, errors
    assert payload["work_mode"] == "evolve"
    assert payload["current_state"]["summary"]
    assert payload["delta_scope"]["affected_modules"]
    assert payload["delta_scope"]["reuse_surfaces"]
    assert files["markdown"].exists()


def test_baseline_audit_builder_captures_existing_project_surfaces(temp_project_dir: Path) -> None:
    (temp_project_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "dependencies": {"react": "^19.0.0", "next": "^15.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (temp_project_dir / "pages").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "components").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "backend").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / "migrations").mkdir(parents=True, exist_ok=True)

    builder = BaselineAuditBuilder(temp_project_dir)
    report = builder.build(work_mode_override="variant")

    assert report.work_mode == "variant"
    assert "components" in report.ui_summary["component_directories"]
    assert "pages" in report.ui_summary["route_surfaces"]
    assert "backend" in report.architecture_summary["backend_surfaces"]
    assert "migrations" in report.architecture_summary["data_surfaces"]
