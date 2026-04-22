from __future__ import annotations

from collections import OrderedDict

CANONICAL_WORKFLOW_STAGE_CHAIN: tuple[str, ...] = (
    "baseline",
    "research",
    "docs",
    "docs_confirm",
    "spec",
    "frontend",
    "preview_confirm",
    "backend",
    "quality",
    "delivery",
)

SEEAI_WORKFLOW_STAGE_CHAIN: tuple[str, ...] = (
    "research",
    "docs",
    "docs_confirm",
    "spec",
    "build_fullstack",
    "polish",
    "quality",
    "delivery",
)

_CANONICAL_STAGE_ALIASES: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("baseline", ("baseline", "current_state_audit")),
        ("research", ("research", "discovery", "intelligence")),
        ("docs", ("docs", "drafting")),
        ("docs_confirm", ("docs_confirm",)),
        ("spec", ("spec",)),
        ("frontend", ("frontend",)),
        ("preview_confirm", ("preview_confirm",)),
        ("backend", ("backend",)),
        ("quality", ("quality", "redteam", "qa")),
        ("delivery", ("delivery", "deployment")),
        ("build_fullstack", ("build_fullstack",)),
        ("polish", ("polish",)),
    ]
)

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _CANONICAL_STAGE_ALIASES.items()
    for alias in aliases
}

_ENGINE_PHASE_SEQUENCE: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("discovery", ("discovery",)),
        ("intelligence", ("intelligence",)),
        ("drafting", ("drafting",)),
        ("redteam", ("redteam",)),
        ("qa", ("qa",)),
        ("delivery", ("delivery",)),
        ("deployment", ("deployment",)),
        ("research", ("discovery", "intelligence")),
        ("docs", ("drafting",)),
        ("quality", ("redteam", "qa")),
        ("delivery_closure", ("delivery", "deployment")),
        ("delivery_full", ("delivery", "deployment")),
        ("delivery_bundle", ("deployment",)),
    ]
)

_ENGINE_PHASE_TO_CANONICAL_STAGE: dict[str, str] = {
    "discovery": "research",
    "intelligence": "research",
    "drafting": "docs",
    "redteam": "quality",
    "qa": "quality",
    "delivery": "delivery",
    "deployment": "delivery",
}

_DOCS_CONFIRM_LATE_STAGES = {"spec", "frontend", "preview_confirm", "backend", "quality", "delivery"}
_PREVIEW_CONFIRM_LATE_STAGES = {"backend", "quality", "delivery"}

WORKFLOW_STAGE_EXPERTS: dict[str, tuple[str, ...]] = {
    "baseline": ("PRODUCT", "ARCHITECT", "CODE"),
    "research": ("PM", "PRODUCT", "ARCHITECT"),
    "docs": ("PM", "ARCHITECT", "UI", "UX"),
    "docs_confirm": ("PRODUCT", "PM"),
    "spec": ("PM", "ARCHITECT", "CODE"),
    "frontend": ("UI", "UX", "CODE", "QA"),
    "preview_confirm": ("PRODUCT", "UI", "UX"),
    "backend": ("ARCHITECT", "CODE", "DBA", "QA"),
    "quality": ("QA", "SECURITY", "RCA", "PRODUCT"),
    "delivery": ("DEVOPS", "QA", "PRODUCT"),
    "build_fullstack": ("PM", "ARCHITECT", "UI", "CODE", "QA"),
    "polish": ("PRODUCT", "UI", "UX", "QA"),
}


def normalize_stage_key(stage: str) -> str:
    normalized = str(stage).strip().lower()
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


def canonical_stage_for_engine_phase(stage: str) -> str:
    normalized = str(stage).strip().lower()
    return _ENGINE_PHASE_TO_CANONICAL_STAGE.get(normalized, normalize_stage_key(normalized))


def resolve_engine_phase_names(requested_stages: list[str] | None) -> list[str]:
    if not requested_stages:
        return []
    resolved: list[str] = []
    seen: set[str] = set()
    for raw_stage in requested_stages:
        normalized = str(raw_stage).strip().lower()
        phase_names = _ENGINE_PHASE_SEQUENCE.get(normalized, (normalized,))
        for phase_name in phase_names:
            if phase_name in seen:
                continue
            seen.add(phase_name)
            resolved.append(phase_name)
    return resolved


def stages_require_docs_confirmation(requested_stages: list[str] | None) -> bool:
    if not requested_stages:
        return False
    normalized = {normalize_stage_key(item) for item in requested_stages if str(item).strip()}
    return bool(normalized & _DOCS_CONFIRM_LATE_STAGES)


def stages_require_preview_confirmation(requested_stages: list[str] | None) -> bool:
    if not requested_stages:
        return False
    normalized = {normalize_stage_key(item) for item in requested_stages if str(item).strip()}
    return bool(normalized & _PREVIEW_CONFIRM_LATE_STAGES)


def active_experts_for_stage(stage: str) -> tuple[str, ...]:
    return WORKFLOW_STAGE_EXPERTS.get(normalize_stage_key(stage), ())
