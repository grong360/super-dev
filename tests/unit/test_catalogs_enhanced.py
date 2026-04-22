# ruff: noqa: I001
"""
目录/枚举完整性增强测试

测试对象: super_dev.catalogs
"""

from super_dev.catalogs import (
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PLATFORM_IDS,
)


# ---------------------------------------------------------------------------
# Platform IDs
# ---------------------------------------------------------------------------

class TestPlatformIDs:
    def test_web_in_platforms(self):
        assert "web" in PLATFORM_IDS

    def test_mobile_in_platforms(self):
        assert "mobile" in PLATFORM_IDS

    def test_desktop_in_platforms(self):
        assert "desktop" in PLATFORM_IDS

    def test_wechat_in_platforms(self):
        assert "wechat" in PLATFORM_IDS

    def test_platforms_are_strings(self):
        for pid in PLATFORM_IDS:
            assert isinstance(pid, str)
            assert len(pid) > 0

    def test_platforms_are_lowercase(self):
        for pid in PLATFORM_IDS:
            assert pid == pid.lower()

    def test_platforms_no_duplicates(self):
        assert len(PLATFORM_IDS) == len(set(PLATFORM_IDS))

    def test_platforms_minimum_count(self):
        assert len(PLATFORM_IDS) >= 3


# ---------------------------------------------------------------------------
# Backend IDs
# ---------------------------------------------------------------------------

class TestBackendIDs:
    def test_node_in_backends(self):
        assert "node" in PIPELINE_BACKEND_IDS

    def test_python_in_backends(self):
        assert "python" in PIPELINE_BACKEND_IDS

    def test_go_in_backends(self):
        assert "go" in PIPELINE_BACKEND_IDS

    def test_java_in_backends(self):
        assert "java" in PIPELINE_BACKEND_IDS

    def test_rust_in_backends(self):
        assert "rust" in PIPELINE_BACKEND_IDS

    def test_backends_are_strings(self):
        for bid in PIPELINE_BACKEND_IDS:
            assert isinstance(bid, str)

    def test_backends_no_duplicates(self):
        assert len(PIPELINE_BACKEND_IDS) == len(set(PIPELINE_BACKEND_IDS))

    def test_backends_minimum_count(self):
        assert len(PIPELINE_BACKEND_IDS) >= 5


# ---------------------------------------------------------------------------
# Frontend Template IDs
# ---------------------------------------------------------------------------

class TestFrontendTemplateIDs:
    def test_react_in_frontends(self):
        found = any("react" in fid.lower() for fid in FULL_FRONTEND_TEMPLATE_IDS)
        assert found

    def test_vue_in_frontends(self):
        found = any("vue" in fid.lower() for fid in FULL_FRONTEND_TEMPLATE_IDS)
        assert found

    def test_next_in_frontends(self):
        found = any("next" in fid.lower() for fid in FULL_FRONTEND_TEMPLATE_IDS)
        assert found

    def test_frontends_are_strings(self):
        for fid in FULL_FRONTEND_TEMPLATE_IDS:
            assert isinstance(fid, str)

    def test_frontends_no_duplicates(self):
        assert len(FULL_FRONTEND_TEMPLATE_IDS) == len(set(FULL_FRONTEND_TEMPLATE_IDS))

    def test_frontends_minimum_count(self):
        assert len(FULL_FRONTEND_TEMPLATE_IDS) >= 5


# ---------------------------------------------------------------------------
# Host Tool IDs
# ---------------------------------------------------------------------------

class TestHostToolIDs:
    def test_host_tools_exist(self):
        assert len(HOST_TOOL_IDS) > 0

    def test_host_tools_are_strings(self):
        for hid in HOST_TOOL_IDS:
            assert isinstance(hid, str)
            assert len(hid) > 0

    def test_host_tools_no_duplicates(self):
        assert len(HOST_TOOL_IDS) == len(set(HOST_TOOL_IDS))

    def test_claude_code_in_hosts(self):
        found = any("claude" in hid.lower() for hid in HOST_TOOL_IDS)
        assert found

    def test_cursor_in_hosts(self):
        found = any("cursor" in hid.lower() for hid in HOST_TOOL_IDS)
        assert found


# ---------------------------------------------------------------------------
# Cross-catalog consistency
# ---------------------------------------------------------------------------

class TestCrossCatalogConsistency:
    def test_all_catalogs_are_tuples_or_lists(self):
        for catalog in [PLATFORM_IDS, PIPELINE_BACKEND_IDS, FULL_FRONTEND_TEMPLATE_IDS, HOST_TOOL_IDS]:
            assert isinstance(catalog, list | tuple | set | frozenset)

    def test_all_catalogs_non_empty(self):
        for catalog in [PLATFORM_IDS, PIPELINE_BACKEND_IDS, FULL_FRONTEND_TEMPLATE_IDS, HOST_TOOL_IDS]:
            assert len(catalog) > 0

    def test_no_overlap_between_platform_and_backend(self):
        platform_set = set(PLATFORM_IDS)
        backend_set = set(PIPELINE_BACKEND_IDS)
        overlap = platform_set & backend_set
        # Platforms and backends should generally not overlap
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"


# ---------------------------------------------------------------------------
# Platform ID 详细验证
# ---------------------------------------------------------------------------

class TestPlatformIDDetails:
    def test_platform_count(self):
        assert len(PLATFORM_IDS) >= 3
        assert len(PLATFORM_IDS) <= 20  # Reasonable upper bound

    def test_each_platform_is_valid_identifier(self):
        for pid in PLATFORM_IDS:
            assert pid.replace("-", "").replace("_", "").isalnum(), f"Invalid platform ID: {pid}"

    def test_each_platform_length_reasonable(self):
        for pid in PLATFORM_IDS:
            assert 2 <= len(pid) <= 30, f"Platform ID length out of range: {pid}"


# ---------------------------------------------------------------------------
# Backend ID 详细验证
# ---------------------------------------------------------------------------

class TestBackendIDDetails:
    def test_common_backends_present(self):
        backend_set = set(PIPELINE_BACKEND_IDS)
        common = {"node", "python", "go", "java"}
        assert common.issubset(backend_set)

    def test_each_backend_is_valid(self):
        for bid in PIPELINE_BACKEND_IDS:
            assert bid.replace("-", "").replace("_", "").isalnum(), f"Invalid backend ID: {bid}"

    def test_backend_count(self):
        assert len(PIPELINE_BACKEND_IDS) >= 5
        assert len(PIPELINE_BACKEND_IDS) <= 30


# ---------------------------------------------------------------------------
# Frontend Template ID 详细验证
# ---------------------------------------------------------------------------

class TestFrontendIDDetails:
    def test_angular_in_frontends(self):
        found = any("angular" in fid.lower() for fid in FULL_FRONTEND_TEMPLATE_IDS)
        assert found

    def test_svelte_in_frontends(self):
        found = any("svelte" in fid.lower() for fid in FULL_FRONTEND_TEMPLATE_IDS)
        assert found

    def test_cross_platform_frontends_present(self):
        assert "expo" in FULL_FRONTEND_TEMPLATE_IDS
        assert "react-native" in FULL_FRONTEND_TEMPLATE_IDS
        assert "flutter" in FULL_FRONTEND_TEMPLATE_IDS
        assert "uni-app" in FULL_FRONTEND_TEMPLATE_IDS
        assert "tauri" in FULL_FRONTEND_TEMPLATE_IDS
        assert "electron" in FULL_FRONTEND_TEMPLATE_IDS

    def test_each_frontend_is_valid(self):
        for fid in FULL_FRONTEND_TEMPLATE_IDS:
            assert isinstance(fid, str)
            assert len(fid) >= 2

    def test_frontend_count(self):
        assert len(FULL_FRONTEND_TEMPLATE_IDS) >= 5
        assert len(FULL_FRONTEND_TEMPLATE_IDS) <= 50


# ---------------------------------------------------------------------------
# Host Tool ID 详细验证
# ---------------------------------------------------------------------------

class TestHostToolIDDetails:
    def test_windsurf_in_hosts(self):
        found = any("windsurf" in hid.lower() for hid in HOST_TOOL_IDS)
        assert found

    def test_host_count_minimum(self):
        assert len(HOST_TOOL_IDS) >= 5

    def test_each_host_is_valid(self):
        for hid in HOST_TOOL_IDS:
            assert isinstance(hid, str)
            assert len(hid) >= 2
            assert len(hid) <= 50


# ---------------------------------------------------------------------------
# ID 格式一致性
# ---------------------------------------------------------------------------

class TestIDFormatConsistency:
    def test_platform_ids_are_kebab_or_lower(self):
        for pid in PLATFORM_IDS:
            assert pid == pid.lower(), f"Platform ID should be lowercase: {pid}"
            assert " " not in pid, f"Platform ID should not contain spaces: {pid}"

    def test_backend_ids_are_kebab_or_lower(self):
        for bid in PIPELINE_BACKEND_IDS:
            assert bid == bid.lower(), f"Backend ID should be lowercase: {bid}"
            assert " " not in bid, f"Backend ID should not contain spaces: {bid}"

    def test_host_ids_are_kebab_or_lower(self):
        for hid in HOST_TOOL_IDS:
            assert hid == hid.lower(), f"Host ID should be lowercase: {hid}"
            assert " " not in hid, f"Host ID should not contain spaces: {hid}"

    def test_frontend_ids_are_kebab_or_lower(self):
        for fid in FULL_FRONTEND_TEMPLATE_IDS:
            assert fid == fid.lower(), f"Frontend ID should be lowercase: {fid}"
            assert " " not in fid, f"Frontend ID should not contain spaces: {fid}"

    def test_all_ids_are_ascii(self):
        for catalog in [PLATFORM_IDS, PIPELINE_BACKEND_IDS, FULL_FRONTEND_TEMPLATE_IDS, HOST_TOOL_IDS]:
            for item_id in catalog:
                assert item_id.isascii(), f"ID should be ASCII: {item_id}"

    def test_no_trailing_whitespace_in_ids(self):
        for catalog in [PLATFORM_IDS, PIPELINE_BACKEND_IDS, FULL_FRONTEND_TEMPLATE_IDS, HOST_TOOL_IDS]:
            for item_id in catalog:
                assert item_id == item_id.strip(), f"ID has trailing whitespace: '{item_id}'"

    def test_php_in_backends(self):
        assert "php" in PIPELINE_BACKEND_IDS

    def test_ruby_in_backends(self):
        assert "ruby" in PIPELINE_BACKEND_IDS

    def test_csharp_in_backends(self):
        assert "csharp" in PIPELINE_BACKEND_IDS

    def test_kotlin_in_backends(self):
        assert "kotlin" in PIPELINE_BACKEND_IDS

    def test_swift_in_backends(self):
        assert "swift" in PIPELINE_BACKEND_IDS

    def test_elixir_in_backends(self):
        assert "elixir" in PIPELINE_BACKEND_IDS

    def test_scala_in_backends(self):
        assert "scala" in PIPELINE_BACKEND_IDS

    def test_dart_in_backends(self):
        assert "dart" in PIPELINE_BACKEND_IDS
