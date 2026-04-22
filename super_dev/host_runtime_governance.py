from __future__ import annotations

from pathlib import Path
from typing import Any

from .host_runtime_probe import build_host_runtime_probe
from .review_state import load_host_runtime_validation


def collect_layered_runtime_governance_gap(
    project_dir: Path,
    *,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    payload = load_host_runtime_validation(project_dir) or {}
    hosts = payload.get("hosts", {}) if isinstance(payload, dict) else {}
    if not isinstance(hosts, dict) or not hosts:
        return {}

    allowed_targets = {str(item) for item in targets} if targets else None
    impacted_hosts: list[str] = []
    next_actions: list[str] = []
    repo_probes: dict[str, dict[str, Any]] = {}

    for host_id, item in hosts.items():
        host_name = str(host_id)
        if allowed_targets is not None and host_name not in allowed_targets:
            continue
        if not isinstance(item, dict):
            continue
        manual_status = str(item.get("status", "")).strip() or "pending"
        if manual_status != "passed":
            continue
        repo_probe = build_host_runtime_probe(
            project_dir,
            target=host_name,
            surface_ready=True,
        )
        repo_probes[host_name] = repo_probe
        if str(repo_probe.get("status", "")).strip() != "failed":
            continue
        impacted_hosts.append(host_name)
        recommended_command = str(repo_probe.get("recommended_command", "")).strip()
        if recommended_command and recommended_command not in next_actions:
            next_actions.append(recommended_command)
            continue
        probe_actions = repo_probe.get("next_actions", [])
        if isinstance(probe_actions, list):
            for item_text in probe_actions:
                text = str(item_text).strip()
                if text and text not in next_actions:
                    next_actions.append(text)
                    break

    if not impacted_hosts:
        return {}

    return {
        "status": "attention",
        "impacted_hosts": impacted_hosts,
        "summary": (
            "以下宿主已人工通过 runtime validation，但仓库级 continuity / harness / runtime 证据仍未闭环："
            + "、".join(impacted_hosts[:3])
        ),
        "next_actions": next_actions,
        "repo_probes": repo_probes,
    }
