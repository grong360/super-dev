from __future__ import annotations

import json
from pathlib import Path

from super_dev.reviewers.architecture_drift import run_architecture_drift
from super_dev.reviewers.spec_compliance import run_spec_compliance
from super_dev.reviewers.uiux_compliance import run_uiux_compliance


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_spec_compliance_persists_and_reuses_evidence_identity(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-prd.md", "# PRD\n\n## Login\n\n1. User login must be supported.\n")
    _write(temp_project_dir / "app.py", "def login_user():\n    return True\n")

    first = run_spec_compliance(temp_project_dir, output_dir)
    assert first.evidence_identity["artifact_name"] == "spec-compliance"
    assert first.evidence_identity["inputs_digest"]

    payload = json.loads(
        (output_dir / f"{first.project_name}-spec-compliance.json").read_text(encoding="utf-8")
    )
    assert payload["evidence_identity"]["inputs_digest"] == first.evidence_identity["inputs_digest"]

    second = run_spec_compliance(temp_project_dir, output_dir)
    assert second.to_dict() == first.to_dict()


def test_architecture_drift_recomputes_when_dependency_changes(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-architecture.md", "# Architecture\n\n## Tech Stack\n\n- FastAPI\n")
    _write(temp_project_dir / "requirements.txt", "fastapi==0.115.0\n")
    _write(temp_project_dir / "service.py", "import fastapi\n")

    first = run_architecture_drift(temp_project_dir, output_dir)
    first_digest = first.evidence_identity["inputs_digest"]
    assert first_digest

    _write(temp_project_dir / "requirements.txt", "flask==3.0.0\n")
    second = run_architecture_drift(temp_project_dir, output_dir)
    second_digest = second.evidence_identity["inputs_digest"]

    assert second_digest
    assert second_digest != first_digest


def test_uiux_compliance_persists_evidence_identity(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-uiux.md", "# UIUX\n\nicon_library: lucide\n")
    _write(
        temp_project_dir / "frontend" / "src" / "page.tsx",
        "import { Home } from 'lucide-react';\nexport function Page(){ return <Home /> }\n",
    )

    report = run_uiux_compliance(temp_project_dir, output_dir)
    assert report.evidence_identity["artifact_name"] == "uiux-compliance"
    assert report.evidence_identity["inputs_digest"]

    payload = json.loads(
        (output_dir / f"{report.project_name}-uiux-compliance.json").read_text(encoding="utf-8")
    )
    assert payload["evidence_identity"]["inputs_digest"] == report.evidence_identity["inputs_digest"]
