from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_state import (
    load_docs_confirmation,
    load_preview_confirmation,
    review_state_dir,
    save_docs_confirmation,
    save_preview_confirmation,
)
from .workflow_stage_truth import (
    active_experts_for_stage,
    normalize_stage_key,
    stages_require_docs_confirmation,
    stages_require_preview_confirmation,
)

_DOC_PATTERNS = ("*-prd.md", "*-architecture.md", "*-uiux.md")
_PREVIEW_PATTERNS = (
    "*-frontend-runtime.json",
    "*-ui-review.md",
    "*-ui-review.json",
    "*-ui-contract.json",
    "*-ui-contract-alignment.json",
)

class WorkflowGateError(RuntimeError):
    """Raised when a workflow gate is bypassed."""

    def __init__(
        self,
        message: str,
        *,
        gate: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.gate = gate
        self.action = action
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "gate": self.gate,
            "action": self.action,
            "details": self.details,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stage_ledger_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "stage-ledger.json"


def load_stage_ledger(project_dir: Path) -> dict[str, Any]:
    file_path = stage_ledger_file(project_dir)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_stage_ledger(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    file_path = stage_ledger_file(project_dir)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def _artifact_files(project_dir: Path, patterns: tuple[str, ...]) -> list[Path]:
    output_dir = Path(project_dir).resolve() / "output"
    if not output_dir.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(output_dir.glob(pattern))
    return sorted({path.resolve() for path in files if path.is_file()})


def _binding_digest(files: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in files:
        rel_path = path.name
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except Exception:
            hasher.update(b"<unreadable>")
        hasher.update(b"\0")
    return hasher.hexdigest()


def _artifact_binding(project_dir: Path, *, stage: str, patterns: tuple[str, ...]) -> dict[str, Any]:
    files = _artifact_files(project_dir, patterns)
    return {
        "stage": stage,
        "file_count": len(files),
        "files": [str(path) for path in files],
        "digest": _binding_digest(files) if files else "",
        "generated_at": _utc_now(),
    }


def collect_docs_artifact_binding(project_dir: Path) -> dict[str, Any]:
    return _artifact_binding(project_dir, stage="docs", patterns=_DOC_PATTERNS)


def collect_preview_artifact_binding(project_dir: Path) -> dict[str, Any]:
    return _artifact_binding(project_dir, stage="preview", patterns=_PREVIEW_PATTERNS)


def _update_stage_ledger(
    project_dir: Path,
    *,
    stage: str,
    status: str,
    run_id: str = "",
    actor: str = "",
    artifact_binding: dict[str, Any] | None = None,
    active_experts: list[str] | tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
    source: str = "",
    comment: str = "",
) -> dict[str, Any]:
    ledger = load_stage_ledger(project_dir)
    artifact_binding = artifact_binding or {}
    normalized_stage = normalize_stage_key(stage)
    entry = {
        "stage": normalized_stage,
        "status": status,
        "run_id": run_id.strip(),
        "actor": actor.strip(),
        "comment": comment.strip(),
        "source": source.strip(),
        "artifact_binding": artifact_binding,
        "active_experts": [str(item).strip() for item in (active_experts or []) if str(item).strip()],
        "details": details if isinstance(details, dict) else {},
        "updated_at": _utc_now(),
    }
    ledger[normalized_stage] = entry
    ledger["updated_at"] = entry["updated_at"]
    save_stage_ledger(project_dir, ledger)
    return entry


def record_docs_generated(project_dir: Path, *, run_id: str = "", source: str = "drafting") -> dict[str, Any]:
    binding = collect_docs_artifact_binding(project_dir)
    return _update_stage_ledger(
        project_dir,
        stage="docs",
        status="generated",
        run_id=run_id,
        actor="system",
        artifact_binding=binding,
        active_experts=active_experts_for_stage("docs"),
        source=source,
    )


def record_stage_progress(
    project_dir: Path,
    *,
    stage: str,
    status: str,
    run_id: str = "",
    actor: str = "system",
    source: str = "pipeline_state",
    comment: str = "",
    artifact_binding: dict[str, Any] | None = None,
    active_experts: list[str] | tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_stage = normalize_stage_key(stage)
    experts = (
        [str(item).strip() for item in active_experts if str(item).strip()]
        if active_experts is not None
        else list(active_experts_for_stage(normalized_stage))
    )
    return _update_stage_ledger(
        project_dir,
        stage=normalized_stage,
        status=status,
        run_id=run_id,
        actor=actor,
        artifact_binding=artifact_binding,
        active_experts=experts,
        details=details,
        source=source,
        comment=comment,
    )


def save_bound_docs_confirmation(project_dir: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    binding = collect_docs_artifact_binding(project_dir)
    normalized = dict(payload)
    normalized["artifact_binding"] = binding
    file_path = save_docs_confirmation(project_dir, normalized)
    ledger_entry = _update_stage_ledger(
        project_dir,
        stage="docs_confirm",
        status=str(normalized.get("status", "")).strip() or "pending_review",
        run_id=str(normalized.get("run_id", "")).strip(),
        actor=str(normalized.get("actor", "")).strip(),
        artifact_binding=binding,
        active_experts=active_experts_for_stage("docs_confirm"),
        source="docs_confirmation",
        comment=str(normalized.get("comment", "")).strip(),
    )
    return file_path, ledger_entry


def save_bound_preview_confirmation(project_dir: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    binding = collect_preview_artifact_binding(project_dir)
    normalized = dict(payload)
    normalized["artifact_binding"] = binding
    file_path = save_preview_confirmation(project_dir, normalized)
    ledger_entry = _update_stage_ledger(
        project_dir,
        stage="preview_confirm",
        status=str(normalized.get("status", "")).strip() or "pending_review",
        run_id=str(normalized.get("run_id", "")).strip(),
        actor=str(normalized.get("actor", "")).strip(),
        artifact_binding=binding,
        active_experts=active_experts_for_stage("preview_confirm"),
        source="preview_confirmation",
        comment=str(normalized.get("comment", "")).strip(),
    )
    return file_path, ledger_entry


def requested_phases_require_docs_confirmation(requested_phases: list[str] | None) -> bool:
    return stages_require_docs_confirmation(requested_phases)


def requested_phases_require_preview_confirmation(requested_phases: list[str] | None) -> bool:
    return stages_require_preview_confirmation(requested_phases)


def docs_gate_status(project_dir: Path) -> dict[str, Any]:
    binding = collect_docs_artifact_binding(project_dir)
    confirmation = load_docs_confirmation(project_dir) or {}
    ledger = load_stage_ledger(project_dir)
    ledger_entry = ledger.get("docs_confirm", {})
    if not isinstance(ledger_entry, dict) or not ledger_entry:
        legacy_entry = ledger.get("docs", {})
        ledger_entry = legacy_entry if isinstance(legacy_entry, dict) else {}
    has_context = bool(binding.get("file_count", 0)) or bool(ledger_entry)
    status = str(confirmation.get("status", "")).strip() or "pending_review"
    confirmed_binding = confirmation.get("artifact_binding", {})
    if not isinstance(confirmed_binding, dict):
        confirmed_binding = {}
    if not confirmed_binding:
        confirmed_binding = ledger_entry.get("artifact_binding", {})
        if not isinstance(confirmed_binding, dict):
            confirmed_binding = {}
    stored_digest = str(confirmed_binding.get("digest", "")).strip()
    current_digest = str(binding.get("digest", "")).strip()
    binding_matches_current = bool(stored_digest) and stored_digest == current_digest
    confirmed = status == "confirmed" and binding_matches_current
    return {
        "has_context": has_context,
        "confirmed": confirmed,
        "status": status,
        "artifact_binding": binding,
        "confirmed_artifact_binding": confirmed_binding,
        "binding_matches_current": binding_matches_current,
        "confirmation": confirmation,
        "ledger_entry": ledger_entry,
    }


def preview_gate_status(project_dir: Path) -> dict[str, Any]:
    binding = collect_preview_artifact_binding(project_dir)
    confirmation = load_preview_confirmation(project_dir) or {}
    ledger = load_stage_ledger(project_dir)
    ledger_entry = ledger.get("preview_confirm", {})
    if not isinstance(ledger_entry, dict) or not ledger_entry:
        legacy_entry = ledger.get("preview", {})
        ledger_entry = legacy_entry if isinstance(legacy_entry, dict) else {}
    status = str(confirmation.get("status", "")).strip() or "pending_review"
    confirmed_binding = confirmation.get("artifact_binding", {})
    if not isinstance(confirmed_binding, dict):
        confirmed_binding = {}
    if not confirmed_binding:
        confirmed_binding = ledger_entry.get("artifact_binding", {})
        if not isinstance(confirmed_binding, dict):
            confirmed_binding = {}
    stored_digest = str(confirmed_binding.get("digest", "")).strip()
    current_digest = str(binding.get("digest", "")).strip()
    binding_matches_current = bool(stored_digest) and stored_digest == current_digest
    return {
        "has_context": bool(binding.get("file_count", 0)) or bool(ledger_entry),
        "confirmed": status == "confirmed" and binding_matches_current,
        "status": status,
        "artifact_binding": binding,
        "confirmed_artifact_binding": confirmed_binding,
        "binding_matches_current": binding_matches_current,
        "confirmation": confirmation,
        "ledger_entry": ledger_entry,
    }


def require_docs_confirmation(
    project_dir: Path,
    *,
    action: str,
    requested_phases: list[str] | None = None,
    require_context: bool = True,
) -> dict[str, Any]:
    gate_state = docs_gate_status(project_dir)
    if requested_phases is not None and not requested_phases_require_docs_confirmation(requested_phases):
        return gate_state
    if require_context and not gate_state["has_context"]:
        return gate_state
    if gate_state["confirmed"]:
        return gate_state
    raise WorkflowGateError(
        "三份核心文档尚未确认，不能跳过 docs_confirm 直接进入后续阶段。",
        gate="docs_confirmation",
        action=action,
        details={
            "status": gate_state["status"],
            "requested_phases": list(requested_phases or []),
            "artifact_binding": gate_state["artifact_binding"],
            "confirmed_artifact_binding": gate_state["confirmed_artifact_binding"],
            "binding_matches_current": gate_state["binding_matches_current"],
        },
    )


def require_preview_confirmation(
    project_dir: Path,
    *,
    action: str,
    requested_phases: list[str] | None = None,
    require_context: bool = True,
) -> dict[str, Any]:
    gate_state = preview_gate_status(project_dir)
    if requested_phases is not None and not requested_phases_require_preview_confirmation(
        requested_phases
    ):
        return gate_state
    if require_context and not gate_state["has_context"]:
        return gate_state
    if gate_state["confirmed"]:
        return gate_state
    raise WorkflowGateError(
        "前端预览尚未确认，不能跳过 preview_confirm 直接进入后续阶段。",
        gate="preview_confirmation",
        action=action,
        details={
            "status": gate_state["status"],
            "requested_phases": list(requested_phases or []),
            "artifact_binding": gate_state["artifact_binding"],
            "confirmed_artifact_binding": gate_state["confirmed_artifact_binding"],
            "binding_matches_current": gate_state["binding_matches_current"],
        },
    )
