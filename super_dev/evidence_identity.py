from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .artifact_utils import resolve_project_artifact_prefix
from .workflow_guard import load_stage_ledger


def _relative_label(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except Exception:
        return str(path.resolve())


def _digest_files(project_dir: Path, dependencies: Sequence[Path | None]) -> tuple[str, list[str]]:
    hasher = hashlib.sha256()
    labels: list[str] = []
    seen: set[str] = set()
    for dependency in dependencies:
        if dependency is None:
            continue
        path = Path(dependency).resolve()
        if not path.exists() or not path.is_file():
            continue
        label = _relative_label(project_dir, path)
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except Exception:
            hasher.update(b"<unreadable>")
        hasher.update(b"\0")
    return (hasher.hexdigest() if labels else "", labels)


def current_evidence_run_id(project_dir: Path) -> str:
    ledger = load_stage_ledger(project_dir)
    if not isinstance(ledger, dict):
        return ""
    for stage in ("preview", "docs"):
        entry = ledger.get(stage, {})
        if not isinstance(entry, dict):
            continue
        run_id = str(entry.get("run_id", "")).strip()
        if run_id:
            return run_id
    return ""


def build_evidence_identity(
    project_dir: Path,
    *,
    artifact_name: str,
    dependencies: Sequence[Path | None],
    run_id: str = "",
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    digest, labels = _digest_files(project_dir, dependencies)
    return {
        "artifact_name": artifact_name,
        "project_name": resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name),
        "run_id": run_id.strip() or current_evidence_run_id(project_dir),
        "inputs_digest": digest,
        "dependency_count": len(labels),
        "dependencies": labels,
    }


def attach_evidence_identity(
    payload: dict[str, Any],
    *,
    project_dir: Path,
    artifact_name: str,
    dependencies: Sequence[Path | None],
    run_id: str = "",
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["evidence_identity"] = build_evidence_identity(
        project_dir,
        artifact_name=artifact_name,
        dependencies=dependencies,
        run_id=run_id,
    )
    return normalized


def load_json_payload(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def evidence_identity_matches(
    payload: dict[str, Any] | None,
    *,
    expected: dict[str, Any],
) -> tuple[bool, str]:
    payload = payload or {}
    identity = payload.get("evidence_identity", {})
    if not isinstance(identity, dict):
        identity = {}
    expected_digest = str(expected.get("inputs_digest", "")).strip()
    actual_digest = str(identity.get("inputs_digest", "")).strip()
    if not actual_digest:
        return False, "missing"
    if expected_digest != actual_digest:
        return False, "digest_mismatch"
    return True, "matched"
