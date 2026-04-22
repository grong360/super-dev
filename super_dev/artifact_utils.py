from __future__ import annotations

from collections import defaultdict
from pathlib import Path

ARTIFACT_SUFFIX_WEIGHTS: dict[str, int] = {
    "-prd.md": 5,
    "-architecture.md": 5,
    "-uiux.md": 5,
    "-research.md": 4,
    "-spec-compliance.json": 4,
    "-spec-compliance.md": 4,
    "-architecture-drift.json": 4,
    "-architecture-drift.md": 4,
    "-uiux-compliance.json": 4,
    "-uiux-compliance.md": 4,
    "-ui-contract.json": 4,
    "-frontend-runtime.json": 4,
    "-ui-review.json": 3,
    "-ui-contract-alignment.json": 3,
    "-quality-gate.md": 3,
    "-proof-pack.json": 3,
    "-release-readiness.json": 3,
    "-product-audit.json": 2,
    "-knowledge-bundle.json": 1,
    "-pipeline-metrics.json": 1,
}


def sanitize_artifact_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "-").replace("_", "-")


def _artifact_prefix_for(path: Path) -> str:
    filename = path.name
    for suffix in sorted(ARTIFACT_SUFFIX_WEIGHTS.keys(), key=len, reverse=True):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return ""


def resolve_project_artifact_prefix(
    project_dir: Path,
    *,
    configured_name: str = "",
    fallback_name: str = "",
) -> str:
    project_path = Path(project_dir).resolve()
    output_dir = project_path / "output"
    configured = sanitize_artifact_name(configured_name)
    fallback = sanitize_artifact_name(fallback_name or project_path.name)

    scores: dict[str, int] = defaultdict(int)
    freshness: dict[str, float] = defaultdict(float)
    if output_dir.exists():
        for path in output_dir.rglob("*"):
            if not path.is_file():
                continue
            prefix = _artifact_prefix_for(path)
            if not prefix:
                continue
            suffix = path.name[len(prefix) :]
            scores[prefix] += ARTIFACT_SUFFIX_WEIGHTS.get(suffix, 1)
            try:
                freshness[prefix] = max(freshness[prefix], path.stat().st_mtime)
            except OSError:
                pass

    def candidate_score(prefix: str) -> tuple[int, float, int]:
        return (
            scores.get(prefix, 0),
            freshness.get(prefix, 0.0),
            1 if prefix == configured and prefix else 0,
        )

    if configured and scores.get(configured, 0) > 0:
        return configured

    if scores:
        best = max(scores.keys(), key=candidate_score)
        if scores.get(best, 0) > 0:
            return best

    return configured or fallback or "project"


def latest_artifact(
    output_dir: Path,
    pattern: str,
    *,
    preferred_prefix: str = "",
) -> Path | None:
    directory = Path(output_dir)
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    if preferred_prefix:
        prefixed = [
            path
            for path in candidates
            if path.name.startswith(f"{sanitize_artifact_name(preferred_prefix)}-")
        ]
        if prefixed:
            candidates = prefixed
    return max(candidates, key=lambda item: item.stat().st_mtime)


def is_artifact_stale(path: Path | None, *, dependencies: list[Path | None]) -> bool:
    if path is None or not path.exists() or not path.is_file():
        return False
    try:
        artifact_mtime = path.stat().st_mtime
    except OSError:
        return False
    for dependency in dependencies:
        if dependency is None or not dependency.exists() or not dependency.is_file():
            continue
        try:
            if dependency.stat().st_mtime > artifact_mtime:
                return True
        except OSError:
            continue
    return False
