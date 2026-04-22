"""枚举目录一致性测试"""

from pathlib import Path

import pytest

from super_dev.catalogs import (
    BACKEND_TEMPLATE_CATALOG,
    CICD_PLATFORM_CATALOG,
    CICD_PLATFORM_IDS,
    CICD_PLATFORM_TARGET_IDS,
    DOMAIN_CATALOG,
    DOMAIN_IDS,
    FULL_FRONTEND_TEMPLATE_CATALOG,
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_COMMAND_CANDIDATES,
    HOST_PATH_PATTERNS,
    HOST_TOOL_ALIASES,
    HOST_TOOL_CATALOG,
    HOST_TOOL_CATEGORY_MAP,
    HOST_TOOL_IDS,
    LANGUAGE_PREFERENCE_CATALOG,
    PIPELINE_BACKEND_IDS,
    PIPELINE_FRONTEND_TEMPLATE_CATALOG,
    PIPELINE_FRONTEND_TEMPLATE_IDS,
    PLATFORM_CATALOG,
    PLATFORM_IDS,
    PRIMARY_HOST_TOOL_IDS,
    PRODUCT_HOST_TOOL_IDS,
    SPECIAL_INSTALL_HOST_TOOL_IDS,
    host_detection_path_candidates,
    host_override_path_candidates,
    host_runtime_validation_overrides,
    normalize_host_tool_id,
)
from super_dev.config import ConfigManager
from super_dev.integrations import IntegrationManager
from super_dev.skills import SkillManager


def test_backend_catalog_ids_unique():
    ids = [item["id"] for item in BACKEND_TEMPLATE_CATALOG]
    assert ids == list(PIPELINE_BACKEND_IDS)
    assert len(ids) == len(set(ids))
    assert "none" in ids


def test_language_catalog_ids_unique():
    ids = [item["id"] for item in LANGUAGE_PREFERENCE_CATALOG]
    assert len(ids) == len(set(ids))
    assert {"python", "typescript", "rust", "sql"}.issubset(set(ids))


def test_platform_catalog_ids_unique():
    ids = [item["id"] for item in PLATFORM_CATALOG]
    assert ids == list(PLATFORM_IDS)
    assert len(ids) == len(set(ids))


def test_frontend_catalog_ids_unique():
    pipeline_ids = [item["id"] for item in PIPELINE_FRONTEND_TEMPLATE_CATALOG]
    full_ids = [item["id"] for item in FULL_FRONTEND_TEMPLATE_CATALOG]
    assert pipeline_ids == list(PIPELINE_FRONTEND_TEMPLATE_IDS)
    assert full_ids == list(FULL_FRONTEND_TEMPLATE_IDS)
    assert len(pipeline_ids) == len(set(pipeline_ids))
    assert len(full_ids) == len(set(full_ids))
    assert set(pipeline_ids).issubset(set(full_ids))


def test_domain_catalog_ids_unique():
    ids = [item["id"] for item in DOMAIN_CATALOG]
    assert ids == list(DOMAIN_IDS)
    assert len(ids) == len(set(ids))
    assert "" in ids


def test_cicd_catalog_ids_unique():
    ids = [item["id"] for item in CICD_PLATFORM_CATALOG]
    assert ids == list(CICD_PLATFORM_IDS)
    assert len(ids) == len(set(ids))
    assert ids[0] == "all"
    assert set(CICD_PLATFORM_TARGET_IDS) == {"github", "gitlab", "jenkins", "azure", "bitbucket"}


def test_host_tool_catalog_ids_unique():
    ids = [item["id"] for item in HOST_TOOL_CATALOG]
    assert ids == list(HOST_TOOL_IDS)
    assert len(ids) == len(set(ids))
    assert {
        "claude",
        "claude-code",
        "cline",
        "codebuddy-cli",
        "codebuddy",
        "codebuddy-cn",
        "codex",
        "codex-cli",
        "droid-cli",
        "cursor-cli",
        "windsurf",
        "gemini-cli",
        "kimi-code",
        "kilo-code",
        "kiro-cli",
        "opencode",
        "qoder-cli",
        "qwen-code",
        "roo-code",
        "vscode-copilot",
        "cursor",
        "kiro",
        "qoder",
        "trae",
        "trae-cn",
        "trae-solo",
        "trae-solocn",
        "workbuddy",
    }.issubset(set(ids))


def test_host_detection_catalogs_reference_known_hosts():
    host_set = set(HOST_TOOL_IDS)
    assert set(HOST_COMMAND_CANDIDATES).issubset(host_set)
    assert set(HOST_PATH_PATTERNS).issubset(host_set)


def test_host_tool_category_map_is_complete():
    host_set = set(HOST_TOOL_IDS)
    assert set(HOST_TOOL_CATEGORY_MAP) == host_set
    assert set(HOST_TOOL_CATEGORY_MAP.values()).issubset({"cli", "ide", "assistant"})


def test_primary_product_host_scope_is_locked():
    assert len(PRIMARY_HOST_TOOL_IDS) == 26
    assert len(PRODUCT_HOST_TOOL_IDS) == 26
    assert SPECIAL_INSTALL_HOST_TOOL_IDS == ()
    assert "claude" in PRIMARY_HOST_TOOL_IDS
    assert "codex" in PRIMARY_HOST_TOOL_IDS
    assert "droid-cli" in PRIMARY_HOST_TOOL_IDS
    assert "droid-cli" in PRODUCT_HOST_TOOL_IDS
    assert "workbuddy" in PRIMARY_HOST_TOOL_IDS
    assert "workbuddy" in PRODUCT_HOST_TOOL_IDS
    assert "antigravity" in PRIMARY_HOST_TOOL_IDS
    assert "kimi-code" in PRIMARY_HOST_TOOL_IDS
    assert "qwen-code" in PRIMARY_HOST_TOOL_IDS
    assert "codebuddy-cn" in PRIMARY_HOST_TOOL_IDS
    assert "trae-cn" in PRIMARY_HOST_TOOL_IDS
    assert "trae-solo" in PRIMARY_HOST_TOOL_IDS
    assert "trae-solocn" in PRIMARY_HOST_TOOL_IDS


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("codex", "codex"),
        ("codex cli", "codex-cli"),
        ("claude", "claude"),
        ("claude code", "claude-code"),
        ("gemini", "gemini-cli"),
        ("kimi", "kimi-code"),
        ("copilot", "copilot-cli"),
        ("cursor", "cursor"),
        ("cursor cli", "cursor-cli"),
        ("codebuddy cn", "codebuddy-cn"),
        ("qwen", "qwen-code"),
        ("vscode", "vscode-copilot"),
        ("腾讯虾", "workbuddy"),
        ("trae cn", "trae-cn"),
        ("trae solo", "trae-solo"),
        ("trae solo cn", "trae-solocn"),
    ],
)
def test_normalize_host_tool_id_supports_product_aliases(alias: str, expected: str):
    assert normalize_host_tool_id(alias) == expected


def test_alias_entries_resolve_to_known_hosts():
    for host_id, aliases in HOST_TOOL_ALIASES.items():
        assert host_id in HOST_TOOL_IDS
        for alias in aliases:
            assert normalize_host_tool_id(alias) == host_id


def test_alias_entries_do_not_shadow_canonical_host_ids():
    host_set = set(HOST_TOOL_IDS)
    for aliases in HOST_TOOL_ALIASES.values():
        assert host_set.isdisjoint(set(aliases))


def test_runtime_validation_overrides_prefer_special_host_adapters():
    overrides = host_runtime_validation_overrides("droid-cli")

    assert overrides["runtime_checklist"]
    assert overrides["pass_criteria"]
    assert overrides["resume_checklist"]
    assert any(
        "比赛入口" in item or "super-dev-seeai" in item for item in overrides["runtime_checklist"]
    )
    assert any("droid exec --session-id" in item for item in overrides["resume_checklist"])


def test_host_usage_guide_tracks_primary_product_hosts():
    guide_path = Path(__file__).resolve().parents[2] / "docs" / "HOST_USAGE_GUIDE.md"
    content = guide_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    assert "当前默认采用统一宿主矩阵。" in content
    assert "Claude" in content
    assert "Codex CLI" in content
    assert "Codex" in content
    assert "Qwen Code" in content
    assert "CodeBuddyCN" in content
    assert "TraeCN" in content
    assert "Droid CLI" in content
    assert "WorkBuddy" in content
    assert "Kimi Code" in content
    assert "Trae SOLO" in content
    assert "Trae SOLOCN" in content

    # 只提取宿主表的行（包含 Slash/非Slash/协议列的行）
    table_rows = [
        line
        for line in lines
        if line.startswith("| ")
        and not line.startswith("| 宿主 ")
        and not line.startswith("| ---")
        and "|" in line
        and line.count("|") >= 5  # 宿主表至少5个分隔符
    ]
    assert len(table_rows) >= len(PRIMARY_HOST_TOOL_IDS)

    host_names = {row.split("|")[1].strip() for row in table_rows}
    assert {
        "Antigravity",
        "Claude",
        "Claude Code",
        "Droid CLI",
        "CodeBuddy CLI",
        "CodeBuddy",
        "CodeBuddyCN",
        "WorkBuddy",
        "Codex CLI",
        "Codex",
        "Qwen Code",
        "TraeCN",
        "Trae",
        "Trae SOLO",
        "Trae SOLOCN",
    }.issubset(host_names)


def test_host_override_path_candidates_support_explicit_env_override(temp_project_dir, monkeypatch):
    custom_path = temp_project_dir / "custom" / "Codex.exe"
    custom_path.parent.mkdir(parents=True, exist_ok=True)
    custom_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SUPER_DEV_HOST_PATH_CODEX_CLI", str(custom_path))

    candidates = host_override_path_candidates("codex-cli")

    assert str(custom_path) in candidates


def test_host_detection_path_candidates_include_override_and_registry(
    temp_project_dir, monkeypatch
):
    custom_path = temp_project_dir / "custom" / "Trae.exe"
    custom_path.parent.mkdir(parents=True, exist_ok=True)
    custom_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SUPER_DEV_HOST_PATH_TRAE", str(custom_path))
    registry_path = temp_project_dir / "registry" / "Trae.exe"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "super_dev.catalogs._windows_registry_path_candidates",
        lambda host_id: [str(registry_path)] if host_id == "trae" else [],
    )

    probes = host_detection_path_candidates("trae")

    assert ("env", str(custom_path)) in probes
    assert ("registry", str(registry_path)) in probes


def test_host_support_matrix_is_aligned_with_catalogs():
    integration_gaps = IntegrationManager.coverage_gaps()
    assert integration_gaps["missing_in_targets"] == []
    assert integration_gaps["extra_in_targets"] == []
    assert integration_gaps["missing_in_slash"] == []
    assert integration_gaps["extra_in_slash"] == []

    skill_gaps = SkillManager.coverage_gaps()
    assert skill_gaps["missing_in_skill_targets"] == []
    assert skill_gaps["extra_in_skill_targets"] == []


@pytest.mark.parametrize("backend", PIPELINE_BACKEND_IDS)
def test_config_manager_accepts_catalog_backends(temp_project_dir, backend: str):
    manager = ConfigManager(temp_project_dir)
    manager.create(name=f"catalog-{backend}", backend=backend)
    is_valid, errors = manager.validate()
    assert is_valid
    assert errors == []


@pytest.mark.parametrize("platform", PLATFORM_IDS)
def test_config_manager_accepts_catalog_platforms(temp_project_dir, platform: str):
    manager = ConfigManager(temp_project_dir)
    manager.create(name=f"catalog-{platform}", platform=platform)
    is_valid, errors = manager.validate()
    assert is_valid
    assert errors == []


@pytest.mark.parametrize("frontend", FULL_FRONTEND_TEMPLATE_IDS)
def test_config_manager_accepts_catalog_frontends(temp_project_dir, frontend: str):
    manager = ConfigManager(temp_project_dir)
    manager.create(name=f"catalog-{frontend}", frontend=frontend)
    is_valid, errors = manager.validate()
    assert is_valid
    assert errors == []
