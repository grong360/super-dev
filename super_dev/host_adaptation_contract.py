"""Structured host adaptation contracts shared across CLI and Web surfaces."""

from __future__ import annotations

from typing import Any

from .workflow_state import build_host_flow_probe


def _dimension(
    *,
    ready: bool,
    partial: bool,
    evidence: list[str],
    gaps: list[str] | None = None,
) -> dict[str, Any]:
    status = "ready" if ready else ("partial" if partial else "missing")
    return {
        "status": status,
        "evidence": [item for item in evidence if item],
        "gaps": [item for item in (gaps or []) if item],
    }


def _build_official_alignment(profile: Any) -> dict[str, Any]:
    protocol_mode = str(getattr(profile, "host_protocol_mode", "") or "").strip()
    protocol_summary = str(getattr(profile, "host_protocol_summary", "") or "").strip()
    docs_verified = bool(getattr(profile, "docs_verified", False))
    references = list(getattr(profile, "official_docs_references", []) or [])

    if protocol_summary.startswith("官方"):
        status = "official_documented" if docs_verified else "official_partial"
        label = "官方明确" if docs_verified else "官方模式待补证据"
        summary = (
            "当前宿主协议已按官方说明收敛。"
            if docs_verified
            else "当前宿主协议按官方能力建模，但官方证据闭环仍需补齐。"
        )
    elif protocol_summary.startswith("当前推荐"):
        status = "recommended_model"
        label = "当前推荐模型"
        summary = "当前宿主按推荐接入模型收敛，增强面与兼容层不会被误报成默认官方合同。"
    elif "explicit" in protocol_summary or "显式" in protocol_summary:
        status = "current_aligned_model"
        label = "当前对齐模型"
        summary = "当前宿主按显式入口与恢复链收敛，避免把增强面误写成唯一官方合同。"
    else:
        status = "current_host_model"
        label = "当前宿主模型"
        summary = "当前宿主按现有公开能力与运行链收敛，仍需持续积累官方证据和真机样本。"

    return {
        "status": status,
        "label": label,
        "summary": summary,
        "protocol_mode": protocol_mode,
        "protocol_summary": protocol_summary,
        "docs_verified": docs_verified,
        "official_reference_count": len(references),
    }


def build_host_adaptation_contract(profile: Any, *, host_id: str, supports_slash: bool) -> dict[str, Any]:
    flow_probe = build_host_flow_probe(host_id)
    supports_slash_entry = supports_slash or any(
        str(item.get("entry", "")).strip().startswith("/")
        for item in profile.entry_variants
    )

    official_surface_count = len(profile.official_project_surfaces) + len(profile.official_user_surfaces)
    official_protocol_ready = bool(profile.host_protocol_summary and official_surface_count > 0)
    official_protocol_partial = bool(profile.host_protocol_summary or official_surface_count > 0)

    entry_ready = bool(profile.primary_entry and profile.entry_variants)
    entry_partial = bool(profile.primary_entry or profile.trigger_command)

    continuity_ready = bool(
        flow_probe.get("enabled")
        and profile.smoke_test_prompt
        and profile.smoke_test_steps
    )
    continuity_partial = bool(flow_probe.get("enabled") or profile.smoke_test_prompt)

    competition_ready = bool(
        profile.competition_smoke_test_prompt
        and profile.competition_smoke_test_steps
        and profile.competition_evidence_template
    )
    competition_partial = bool(
        profile.competition_smoke_test_prompt
        or profile.competition_smoke_test_steps
    )

    docs_ready = bool(profile.docs_verified and profile.official_docs_references)
    docs_partial = bool(profile.official_docs_url or profile.official_docs_references)

    score = 0
    score += 30 if official_protocol_ready else (18 if official_protocol_partial else 0)
    score += 20 if entry_ready else (10 if entry_partial else 0)
    score += 20 if continuity_ready else (10 if continuity_partial else 0)
    score += 20 if competition_ready else (10 if competition_partial else 0)
    score += 10 if docs_ready else (5 if docs_partial else 0)

    if score >= 90:
        level = "elite"
    elif score >= 75:
        level = "strong"
    elif score >= 55:
        level = "solid"
    else:
        level = "developing"

    dimensions = {
        "official_protocol": _dimension(
            ready=official_protocol_ready,
            partial=official_protocol_partial,
            evidence=[
                profile.host_protocol_summary,
                f"official surfaces: {official_surface_count}",
            ],
            gaps=[] if official_protocol_ready else ["official host surfaces not fully closed"],
        ),
        "entry_experience": _dimension(
            ready=entry_ready,
            partial=entry_partial,
            evidence=[
                profile.primary_entry,
                f"entry variants: {len(profile.entry_variants)}",
                "supports slash entry" if supports_slash_entry else "text-first trigger",
            ],
            gaps=[] if entry_ready else ["primary entry or fallback trigger incomplete"],
        ),
        "continuity": _dimension(
            ready=continuity_ready,
            partial=continuity_partial,
            evidence=[
                str(flow_probe.get("title", "")).strip(),
                f"smoke steps: {len(profile.smoke_test_steps)}",
            ],
            gaps=[] if continuity_ready else ["resume / flow probe evidence is shallow"],
        ),
        "competition": _dimension(
            ready=competition_ready,
            partial=competition_partial,
            evidence=[
                f"competition smoke steps: {len(profile.competition_smoke_test_steps)}",
                f"competition evidence sections: {len(profile.competition_evidence_template)}",
            ],
            gaps=[] if competition_ready else ["SEEAI competition evidence chain is incomplete"],
        ),
        "docs": _dimension(
            ready=docs_ready,
            partial=docs_partial,
            evidence=[
                profile.official_docs_url,
                f"official references: {len(profile.official_docs_references)}",
            ],
            gaps=[] if docs_ready else ["official docs verification is not closed"],
        ),
    }

    summary = (
        f"{profile.host} 宿主适配成熟度 {score}/100（{level}），"
        f"协议面、触发面、恢复面、比赛面和官方文档验证已统一建模。"
    )
    official_alignment = _build_official_alignment(profile)

    return {
        "score": score,
        "level": level,
        "summary": summary,
        "official_alignment": official_alignment,
        "official_surface_count": official_surface_count,
        "flow_probe_enabled": bool(flow_probe.get("enabled")),
        "supports_slash": supports_slash,
        "supports_slash_entry": supports_slash_entry,
        "dimensions": dimensions,
    }
