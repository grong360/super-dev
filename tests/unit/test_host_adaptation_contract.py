from pathlib import Path

from super_dev.host_adaptation_contract import build_host_adaptation_contract
from super_dev.host_usage_profile import serialize_host_usage_profile
from super_dev.integrations.manager import IntegrationManager


def test_codex_skill_entry_is_not_reported_as_slash_entry():
    manager = IntegrationManager(Path("."))
    profile = manager.get_adapter_profile("codex-cli")

    contract = build_host_adaptation_contract(
        profile,
        host_id="codex-cli",
        supports_slash=manager.supports_slash("codex-cli"),
    )

    assert contract["supports_slash"] is False
    assert contract["supports_slash_entry"] is False
    assert contract["level"] == "elite"
    assert contract["dimensions"]["entry_experience"]["status"] == "ready"
    assert "text-first trigger" in contract["dimensions"]["entry_experience"]["evidence"]


def test_droid_cli_contract_closes_official_and_competition_dimensions():
    manager = IntegrationManager(Path("."))
    profile = manager.get_adapter_profile("droid-cli")

    contract = build_host_adaptation_contract(
        profile,
        host_id="droid-cli",
        supports_slash=manager.supports_slash("droid-cli"),
    )

    assert contract["score"] >= 90
    assert contract["level"] == "elite"
    assert contract["official_alignment"]["status"] == "official_documented"
    assert contract["dimensions"]["official_protocol"]["status"] == "ready"
    assert contract["dimensions"]["competition"]["status"] == "ready"
    assert contract["flow_probe_enabled"] is True


def test_kimi_code_contract_counts_skill_and_resume_strength():
    manager = IntegrationManager(Path("."))
    profile = manager.get_adapter_profile("kimi-code")

    contract = build_host_adaptation_contract(
        profile,
        host_id="kimi-code",
        supports_slash=manager.supports_slash("kimi-code"),
    )

    assert contract["supports_slash"] is False
    assert contract["supports_slash_entry"] is True
    assert contract["official_alignment"]["status"] == "current_aligned_model"
    assert contract["dimensions"]["official_protocol"]["status"] == "ready"
    assert contract["dimensions"]["continuity"]["status"] in {"ready", "partial"}


def test_trae_solo_and_solocn_contracts_capture_entry_models():
    manager = IntegrationManager(Path("."))

    trae_solo = manager.get_adapter_profile("trae-solo")
    solo_contract = build_host_adaptation_contract(
        trae_solo,
        host_id="trae-solo",
        supports_slash=manager.supports_slash("trae-solo"),
    )
    assert solo_contract["supports_slash"] is True
    assert solo_contract["supports_slash_entry"] is True
    assert solo_contract["dimensions"]["entry_experience"]["status"] == "ready"

    trae_solocn = manager.get_adapter_profile("trae-solocn")
    solocn_contract = build_host_adaptation_contract(
        trae_solocn,
        host_id="trae-solocn",
        supports_slash=manager.supports_slash("trae-solocn"),
    )
    assert solocn_contract["supports_slash"] is False
    assert solocn_contract["supports_slash_entry"] is True
    assert solocn_contract["dimensions"]["official_protocol"]["status"] == "ready"


def test_generic_hosts_close_continuity_probe_for_qoder_and_workbuddy():
    manager = IntegrationManager(Path("."))

    qoder = manager.get_adapter_profile("qoder")
    qoder_contract = build_host_adaptation_contract(
        qoder,
        host_id="qoder",
        supports_slash=manager.supports_slash("qoder"),
    )
    assert qoder_contract["dimensions"]["entry_experience"]["status"] == "ready"
    assert qoder_contract["dimensions"]["continuity"]["status"] == "ready"

    workbuddy = manager.get_adapter_profile("workbuddy")
    workbuddy_contract = build_host_adaptation_contract(
        workbuddy,
        host_id="workbuddy",
        supports_slash=manager.supports_slash("workbuddy"),
    )
    assert workbuddy_contract["dimensions"]["official_protocol"]["status"] == "partial"
    assert workbuddy_contract["dimensions"]["continuity"]["status"] == "ready"


def test_usage_profile_serialization_embeds_adaptation_contract():
    manager = IntegrationManager(Path("."))
    profile = manager.get_adapter_profile("trae")

    payload = serialize_host_usage_profile(
        profile=profile,
        target="trae",
        final_trigger="super-dev: 你的需求",
        flow_host_id="trae",
    )

    assert "adaptation_contract" in payload
    contract = payload["adaptation_contract"]
    assert contract["score"] >= 0
    assert contract["official_alignment"]["status"] == "recommended_model"
    assert contract["dimensions"]["docs"]["status"] in {"ready", "partial", "missing"}
    assert contract["supports_slash_entry"] is False
    assert payload["host_start_playbook"]
    assert payload["post_onboard_self_check"]
    assert payload["official_workflow_checks"]
    assert payload["official_pass_criteria"]
    assert isinstance(payload["host_repair_playbook"], str)
    assert payload["standard_flow_first_prompt"]
    assert payload["competition_flow_first_prompt"]
