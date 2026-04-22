from __future__ import annotations

from super_dev.runtime_evidence import (
    COMPETITION_EVIDENCE_SECTIONS,
    HostRuntimeEvidence,
    IntegrationStatus,
    IntegrationStatusRecord,
    RuntimeStatus,
    RuntimeStatusRecord,
    competition_evidence_missing_sections,
    competition_evidence_ready,
    competition_evidence_shallow_sections,
    deserialize_host_runtime_evidence,
    deserialize_integration_status,
    deserialize_runtime_status,
    evaluate_competition_evidence,
    normalize_competition_evidence,
    serialize_host_runtime_evidence,
    serialize_integration_status,
    serialize_runtime_status,
)


def test_runtime_evidence_serialization_keeps_integration_and_runtime_separate():
    integration = IntegrationStatusRecord(
        status=IntegrationStatus.PROJECT_AND_GLOBAL_INSTALLED,
        evidence=("project setup completed", "global setup completed"),
        checked_at="2026-04-12T10:00:00+08:00",
        source="host-registry",
        details="project + global surfaces installed",
    )
    runtime = RuntimeStatusRecord(
        status=RuntimeStatus.PASSED,
        evidence=("smoke prompt passed", "resume prompt passed"),
        checked_at="2026-04-12T10:05:00+08:00",
        source="host-smoke",
        details="runtime smoke passed",
    )
    evidence = HostRuntimeEvidence(
        host_id="codebuddy",
        host_display_name="CodeBuddy",
        summary="integration and runtime are independently tracked",
        evidence=("evidence pack v1",),
        competition_evidence={
            "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
            "runtime_checkpoint": {"summary": "12 分钟内首个可见界面"},
            "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
            "demo_path": {"summary": "30-60 秒主演示路径"},
        },
        competition_evidence_ready=True,
        competition_evidence_missing=(),
        integration_status=integration,
        runtime_status=runtime,
    )

    payload = serialize_host_runtime_evidence(evidence)

    assert payload["host_id"] == "codebuddy"
    assert payload["host_display_name"] == "CodeBuddy"
    assert payload["summary"] == "integration and runtime are independently tracked"
    assert payload["integration_status"]["status"] == "project_and_global_installed"
    assert payload["runtime_status"]["status"] == "passed"
    assert payload["integration_status"]["evidence"] == [
        "project setup completed",
        "global setup completed",
    ]
    assert payload["runtime_status"]["evidence"] == [
        "smoke prompt passed",
        "resume prompt passed",
    ]
    assert payload["competition_evidence_ready"] is True
    assert payload["competition_evidence_missing"] == []
    assert (
        payload["competition_evidence"]["first_response"]["summary"]
        == "作品类型 / wow 点 / P0 / 放弃项"
    )

    restored = deserialize_host_runtime_evidence(payload)

    assert restored == evidence
    assert restored.integration_status.status is IntegrationStatus.PROJECT_AND_GLOBAL_INSTALLED
    assert restored.runtime_status.status is RuntimeStatus.PASSED


def test_competition_evidence_helpers_normalize_and_report_missing_sections():
    payload = {
        "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
        "runtime_checkpoint": "12 分钟内首个可见界面",
        "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
        "demo_path": "",
        "ignored": {"summary": "should be dropped"},
    }

    normalized = normalize_competition_evidence(payload)

    assert tuple(normalized.keys()) == (
        "first_response",
        "runtime_checkpoint",
        "fallback_decision",
    )
    assert competition_evidence_ready(normalized) is False
    assert competition_evidence_missing_sections(normalized) == ("demo_path",)
    assert COMPETITION_EVIDENCE_SECTIONS[-1] == "demo_path"


def test_shallow_sections_flag_thin_content_and_template_keyword_miss():
    template = {
        "first_response": {"required": ["作品类型", "评委 wow 点", "P0 主路径", "主动放弃项"]},
        "runtime_checkpoint": {"required": ["12 分钟内首个可见界面", "主路径首个可点击动作"]},
        "fallback_decision": {"required": ["失败点", "回退栈"]},
        "demo_path": {"required": ["30-60 秒主演示路径", "结果页/结束态"]},
    }
    # 所有四段都有内容，但 first_response 太短、demo_path 完全偏题
    payload = {
        "first_response": "ok",  # 太短
        "runtime_checkpoint": {"summary": "12 分钟内首个可见界面 + 主路径首个可点击动作"},
        "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
        "demo_path": {"summary": "xxxxxxxxxxxxx"},  # 偏题（无模板关键词命中）
    }
    shallow = competition_evidence_shallow_sections(payload, template)
    assert "first_response" in shallow
    assert "demo_path" in shallow
    assert "runtime_checkpoint" not in shallow
    assert "fallback_decision" not in shallow

    verdict = evaluate_competition_evidence(payload, template)
    assert verdict["ready"] is False
    assert verdict["missing"] == ()
    assert set(verdict["shallow"]) == {"first_response", "demo_path"}


def test_shallow_sections_empty_when_content_rich_and_covers_template():
    template = {
        "first_response": {"required": ["作品类型", "评委 wow 点", "P0 主路径", "主动放弃项"]},
        "runtime_checkpoint": {"required": ["12 分钟内首个可见界面"]},
        "fallback_decision": {"required": ["失败点", "回退栈"]},
        "demo_path": {"required": ["30-60 秒主演示路径"]},
    }
    payload = {
        "first_response": {"summary": "作品类型 / wow 点 / P0 / 放弃项"},
        "runtime_checkpoint": {
            "summary": "12 分钟内首个可见界面 + 主路径首个点击动作 + 真实启动模块"
        },
        "fallback_decision": {"summary": "失败点 / 回退栈 / 降级原因"},
        "demo_path": {"summary": "30-60 秒主演示路径 + 结果页/结束态 + wow 点截图"},
    }
    assert competition_evidence_shallow_sections(payload, template) == ()
    assert evaluate_competition_evidence(payload, template)["ready"] is True


def test_status_helpers_round_trip_with_unknown_and_string_payloads():
    integration_payload = {
        "status": "manual",
        "evidence": ["manual setup"],
        "checked_at": "2026-04-12T11:00:00+08:00",
        "source": "registry",
        "details": "manual host installation",
    }
    runtime_payload = {
        "status": "blocked",
        "evidence": ["missing prompt contract"],
        "checked_at": "2026-04-12T11:01:00+08:00",
        "source": "runtime-check",
        "details": "runtime validation blocked",
    }

    integration = deserialize_integration_status(integration_payload)
    runtime = deserialize_runtime_status(runtime_payload)

    assert integration == IntegrationStatusRecord(
        status=IntegrationStatus.MANUAL,
        evidence=("manual setup",),
        checked_at="2026-04-12T11:00:00+08:00",
        source="registry",
        details="manual host installation",
    )
    assert runtime == RuntimeStatusRecord(
        status=RuntimeStatus.BLOCKED,
        evidence=("missing prompt contract",),
        checked_at="2026-04-12T11:01:00+08:00",
        source="runtime-check",
        details="runtime validation blocked",
    )

    assert serialize_integration_status(integration)["status"] == "manual"
    assert serialize_runtime_status(runtime)["status"] == "blocked"
