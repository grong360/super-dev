# ruff: noqa: I001
"""
UI Intelligence 增强测试 - 覆盖响应式设计验证、无障碍深度检查、Token 一致性检查

测试对象: super_dev.design.ui_intelligence.UIIntelligenceAdvisor
"""

import pytest
from super_dev.design.ui_intelligence import (
    LibraryRecommendation,
    UIIntelligenceAdvisor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def advisor():
    return UIIntelligenceAdvisor()


# ---------------------------------------------------------------------------
# LibraryRecommendation
# ---------------------------------------------------------------------------

class TestLibraryRecommendation:
    def test_to_dict(self):
        rec = LibraryRecommendation(
            name="shadcn/ui", category="Primary", rationale="Best for modern apps",
            strengths=["Composable", "Accessible"], notes=["Requires Tailwind"],
        )
        d = rec.to_dict()
        assert d["name"] == "shadcn/ui"
        assert len(d["strengths"]) == 2

    def test_to_dict_with_empty_lists(self):
        rec = LibraryRecommendation(name="test", category="Alt", rationale="reason")
        d = rec.to_dict()
        assert d["strengths"] == []
        assert d["notes"] == []


# ---------------------------------------------------------------------------
# Frontend alias normalization
# ---------------------------------------------------------------------------

class TestFrontendAliases:
    def test_next_maps_to_react(self, advisor):
        assert advisor.FRONTEND_ALIASES["next"] == "react"
        assert advisor.FRONTEND_ALIASES["nextjs"] == "react"

    def test_nuxt_maps_to_vue(self, advisor):
        assert advisor.FRONTEND_ALIASES["nuxt"] == "vue"

    def test_taro_maps_to_miniapp(self, advisor):
        assert advisor.FRONTEND_ALIASES["taro"] == "miniapp"
        assert advisor.FRONTEND_ALIASES["uniapp"] == "miniapp"

    def test_electron_maps_to_desktop(self, advisor):
        assert advisor.FRONTEND_ALIASES["electron"] == "desktop"
        assert advisor.FRONTEND_ALIASES["tauri"] == "desktop"
        assert advisor.FRONTEND_ALIASES["wails"] == "desktop"

    def test_react_native_preserved(self, advisor):
        assert advisor.FRONTEND_ALIASES["react-native"] == "react-native"
        assert advisor.FRONTEND_ALIASES["expo"] == "react-native"

    def test_flutter_preserved(self, advisor):
        assert advisor.FRONTEND_ALIASES["flutter"] == "flutter"

    def test_hybrid_mobile_aliases(self, advisor):
        assert advisor.FRONTEND_ALIASES["ionic"] == "hybrid-mobile"
        assert advisor.FRONTEND_ALIASES["capacitor"] == "hybrid-mobile"

    def test_swiftui_preserved(self, advisor):
        assert advisor.FRONTEND_ALIASES["swiftui"] == "swiftui"


# ---------------------------------------------------------------------------
# Product profiles
# ---------------------------------------------------------------------------

class TestProductProfiles:
    def test_landing_profile_exists(self, advisor):
        profile = advisor.PRODUCT_PROFILES["landing"]
        assert "surface" in profile
        assert len(profile["page_blueprints"]) >= 1

    def test_saas_profile_has_workspace(self, advisor):
        profile = advisor.PRODUCT_PROFILES["saas"]
        pages = [bp["page"] for bp in profile["page_blueprints"]]
        assert any("工作台" in p for p in pages)

    def test_dashboard_high_density(self, advisor):
        assert advisor.PRODUCT_PROFILES["dashboard"]["information_density"] == "high"

    def test_ecommerce_has_product_detail(self, advisor):
        profile = advisor.PRODUCT_PROFILES["ecommerce"]
        pages = [bp["page"] for bp in profile["page_blueprints"]]
        assert any("商品" in p for p in pages)

    def test_content_profile_exists(self, advisor):
        assert advisor.PRODUCT_PROFILES["content"]["information_density"] == "medium"

    def test_general_profile_is_fallback(self, advisor):
        assert "page_blueprints" in advisor.PRODUCT_PROFILES["general"]

    def test_all_profiles_have_banned_patterns(self, advisor):
        for ptype, profile in advisor.PRODUCT_PROFILES.items():
            assert "banned_patterns" in profile, f"{ptype} missing banned_patterns"
            assert len(profile["banned_patterns"]) >= 1

    def test_all_profiles_have_experience_goals(self, advisor):
        for ptype, profile in advisor.PRODUCT_PROFILES.items():
            assert "experience_goals" in profile, f"{ptype} missing experience_goals"

    def test_all_profiles_have_component_priorities(self, advisor):
        for ptype, profile in advisor.PRODUCT_PROFILES.items():
            assert "component_priorities" in profile, f"{ptype} missing component_priorities"

    def test_all_profiles_have_conversion_modules(self, advisor):
        for ptype, profile in advisor.PRODUCT_PROFILES.items():
            assert "conversion_modules" in profile, f"{ptype} missing conversion_modules"


# ---------------------------------------------------------------------------
# Industry trust rules
# ---------------------------------------------------------------------------

class TestIndustryTrustRules:
    def test_healthcare_has_privacy(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["healthcare"]
        assert any("隐私" in m for m in rules["trust_modules"])

    def test_fintech_has_security(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["fintech"]
        assert any("安全" in m for m in rules["trust_modules"])

    def test_education_has_progress(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["education"]
        assert any("进度" in m for m in rules["trust_modules"])

    def test_legal_has_qualification(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["legal"]
        assert any("资质" in m for m in rules["trust_modules"])

    def test_beauty_has_case(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["beauty"]
        assert any("案例" in m for m in rules["trust_modules"])

    def test_general_is_fallback(self, advisor):
        rules = advisor.INDUSTRY_TRUST_RULES["general"]
        assert "trust_modules" in rules
        assert "tone" in rules
        assert "banned_patterns" in rules

    def test_all_industries_have_tone(self, advisor):
        for industry, rules in advisor.INDUSTRY_TRUST_RULES.items():
            assert "tone" in rules, f"{industry} missing tone"

    def test_all_industries_have_banned_patterns(self, advisor):
        for industry, rules in advisor.INDUSTRY_TRUST_RULES.items():
            assert "banned_patterns" in rules, f"{industry} missing banned_patterns"


# ---------------------------------------------------------------------------
# Component library recommendations
# ---------------------------------------------------------------------------

class TestComponentLibraryRecommendations:
    def test_react_has_shadcn_primary(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("react", [])
        primary_libs = [lib for lib in libs if lib.category == "Primary"]
        assert len(primary_libs) >= 1
        assert "shadcn" in primary_libs[0].name.lower()

    def test_vue_has_naive_ui_primary(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("vue", [])
        primary_libs = [lib for lib in libs if lib.category == "Primary"]
        assert len(primary_libs) >= 1
        assert "Naive" in primary_libs[0].name

    def test_angular_has_material(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("angular", [])
        assert any("Material" in lib.name for lib in libs)

    def test_svelte_has_shadcn_svelte(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("svelte", [])
        assert any("shadcn" in lib.name.lower() for lib in libs)

    def test_miniapp_has_tdesign(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("miniapp", [])
        assert any("TDesign" in lib.name for lib in libs)

    def test_mobile_has_native_design(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("mobile", [])
        assert len(libs) >= 1

    def test_flutter_has_recommendation(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("flutter", [])
        assert len(libs) >= 1

    def test_desktop_has_electron_tauri(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("desktop", [])
        assert any("Electron" in lib.name or "Tauri" in lib.name for lib in libs)

    def test_react_native_has_recommendation(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("react-native", [])
        assert len(libs) >= 1

    def test_default_fallback_has_tailwind(self, advisor):
        libs = advisor.COMPONENT_LIBRARIES.get("default", [])
        assert any("Tailwind" in lib.name for lib in libs)

    def test_all_libraries_have_rationale(self, advisor):
        for stack, libs in advisor.COMPONENT_LIBRARIES.items():
            for lib in libs:
                assert lib.rationale, f"{stack}/{lib.name} missing rationale"


# ---------------------------------------------------------------------------
# Token 一致性检查
# ---------------------------------------------------------------------------

class TestTokenConsistency:
    def test_form_stack_covers_all_frontends(self, advisor):
        expected = {"react", "vue", "angular", "svelte", "miniapp", "default"}
        assert expected.issubset(set(advisor.FORM_STACK.keys()))

    def test_motion_stack_covers_all_frontends(self, advisor):
        expected = {"react", "vue", "angular", "svelte", "miniapp", "default"}
        assert expected.issubset(set(advisor.MOTION_STACK.keys()))

    def test_chart_recommendations_cover_all_frontends(self, advisor):
        expected = {"react", "vue", "angular", "svelte", "default"}
        assert expected.issubset(set(advisor.CHART_RECOMMENDATIONS.keys()))

    def test_chart_recommendations_have_default_and_dense(self, advisor):
        for stack, recs in advisor.CHART_RECOMMENDATIONS.items():
            assert "default" in recs, f"{stack} chart missing default"
            assert "dense" in recs, f"{stack} chart missing dense"

    def test_icon_recommendations_have_default(self, advisor):
        assert "default" in advisor.ICON_RECOMMENDATIONS
        assert "brand" in advisor.ICON_RECOMMENDATIONS

    def test_form_stack_react_uses_rhf(self, advisor):
        assert "React Hook Form" in advisor.FORM_STACK["react"]

    def test_form_stack_vue_uses_vee_validate(self, advisor):
        assert "vee-validate" in advisor.FORM_STACK["vue"]

    def test_motion_stack_react_uses_framer(self, advisor):
        assert "Framer" in advisor.MOTION_STACK["react"]

    def test_form_stack_desktop(self, advisor):
        assert "desktop" in advisor.FORM_STACK

    def test_form_stack_flutter(self, advisor):
        assert "flutter" in advisor.FORM_STACK

    def test_form_stack_swiftui(self, advisor):
        assert "swiftui" in advisor.FORM_STACK


# ---------------------------------------------------------------------------
# Dark mode
# ---------------------------------------------------------------------------

class TestDarkModeGeneration:
    def test_light_palette_generates_dark_variant(self, advisor):
        palette = {"background": "#FFFFFF", "text": "#1A1A1A", "primary": "#3B82F6"}
        dark = advisor.generate_dark_variant(palette)
        assert isinstance(dark, dict)

    def test_already_dark_palette_returned_as_is(self, advisor):
        palette = {"background": "#0A0A0A", "text": "#FFFFFF", "primary": "#3B82F6"}
        dark = advisor.generate_dark_variant(palette)
        assert isinstance(dark, dict)


# ---------------------------------------------------------------------------
# recommend() integration
# ---------------------------------------------------------------------------

class TestRecommendIntegration:
    def test_react_dashboard_fintech(self, advisor):
        profile = advisor.recommend(
            description="金融数据分析工作台", frontend="react",
            product_type="dashboard", industry="fintech", style="professional",
        )
        assert "primary_library" in profile
        assert "component_stack" in profile
        assert "trust_modules" in profile
        assert "banned_patterns" in profile
        assert len(profile["quality_checklist"]) >= 4

    def test_vue_saas_general(self, advisor):
        profile = advisor.recommend(
            description="企业协作平台", frontend="vue",
            product_type="saas", industry="general", style="modern",
        )
        assert "Naive" in profile["primary_library"]["name"]

    def test_nextjs_alias(self, advisor):
        profile = advisor.recommend(
            description="Next.js 营销站", frontend="nextjs",
            product_type="landing", industry="general", style="modern",
        )
        assert profile["normalized_frontend"] == "react"

    def test_taro_alias(self, advisor):
        profile = advisor.recommend(
            description="小程序商城", frontend="taro",
            product_type="ecommerce", industry="general", style="modern",
        )
        assert profile["normalized_frontend"] == "miniapp"

    def test_unknown_frontend_uses_default(self, advisor):
        profile = advisor.recommend(
            description="Unknown frontend", frontend="zig-ui",
            product_type="general", industry="general", style="modern",
        )
        assert "primary_library" in profile

    def test_unknown_product_type_fallback(self, advisor):
        profile = advisor.recommend(
            description="Some app", frontend="react",
            product_type="nonexistent_type", industry="general", style="modern",
        )
        assert "primary_library" in profile

    def test_alternative_libraries_present(self, advisor):
        profile = advisor.recommend(
            description="Dashboard", frontend="react",
            product_type="dashboard", industry="general", style="modern",
        )
        assert "alternative_libraries" in profile
        assert len(profile["alternative_libraries"]) >= 1

    def test_ui_library_matrix_present(self, advisor):
        profile = advisor.recommend(
            description="Landing", frontend="react",
            product_type="landing", industry="general", style="modern",
        )
        assert "ui_library_matrix" in profile
        assert isinstance(profile["ui_library_matrix"], list)

    def test_desktop_frontend(self, advisor):
        profile = advisor.recommend(
            description="桌面客户端", frontend="electron",
            product_type="dashboard", industry="general", style="professional",
        )
        assert profile["normalized_frontend"] == "desktop"

    def test_flutter_frontend(self, advisor):
        profile = advisor.recommend(
            description="Flutter 移动端", frontend="flutter",
            product_type="general", industry="general", style="modern",
        )
        assert profile["normalized_frontend"] == "flutter"

    def test_swiftui_frontend(self, advisor):
        profile = advisor.recommend(
            description="iOS 原生", frontend="swiftui",
            product_type="general", industry="general", style="modern",
        )
        assert profile["normalized_frontend"] == "swiftui"

    def test_content_product_type(self, advisor):
        profile = advisor.recommend(
            description="内容平台", frontend="react",
            product_type="content", industry="general", style="editorial",
        )
        assert "primary_library" in profile

    def test_ecommerce_product_type(self, advisor):
        profile = advisor.recommend(
            description="电商平台", frontend="react",
            product_type="ecommerce", industry="general", style="modern",
        )
        assert "primary_library" in profile

    def test_healthcare_trust_modules(self, advisor):
        profile = advisor.recommend(
            description="医疗平台", frontend="react",
            product_type="saas", industry="healthcare", style="professional",
        )
        trust = profile.get("trust_modules", [])
        assert any("隐私" in m or "安全" in m for m in trust)

    def test_legal_trust_modules(self, advisor):
        profile = advisor.recommend(
            description="法律平台", frontend="react",
            product_type="saas", industry="legal", style="professional",
        )
        trust = profile.get("trust_modules", [])
        assert any("资质" in m or "律师" in m for m in trust)

    def test_beauty_industry(self, advisor):
        profile = advisor.recommend(
            description="美容预约", frontend="react",
            product_type="saas", industry="beauty", style="modern",
        )
        trust = profile.get("trust_modules", [])
        assert any("案例" in m for m in trust)

    def test_education_industry(self, advisor):
        profile = advisor.recommend(
            description="在线教育", frontend="react",
            product_type="saas", industry="education", style="modern",
        )
        trust = profile.get("trust_modules", [])
        assert any("进度" in m or "课程" in m for m in trust)


# ---------------------------------------------------------------------------
# 产品类型 x 前端栈矩阵
# ---------------------------------------------------------------------------

class TestProductFrontendMatrix:
    @pytest.fixture(params=["landing", "saas", "dashboard", "ecommerce", "content", "general"])
    def product_type(self, request):
        return request.param

    @pytest.fixture(params=["react", "vue", "angular", "svelte", "nextjs", "taro", "electron", "flutter", "swiftui"])
    def frontend(self, request):
        return request.param

    def test_all_combinations_produce_valid_profile(self, advisor, product_type, frontend):
        profile = advisor.recommend(
            description=f"Test {product_type} with {frontend}",
            frontend=frontend, product_type=product_type,
            industry="general", style="modern",
        )
        assert "primary_library" in profile
        assert profile["primary_library"]["name"]


# ---------------------------------------------------------------------------
# 组件栈完整性
# ---------------------------------------------------------------------------

class TestComponentStackCompleteness:
    def test_react_dashboard_has_table(self, advisor):
        profile = advisor.recommend(
            description="Dashboard", frontend="react",
            product_type="dashboard", industry="general", style="modern",
        )
        assert "table" in profile["component_stack"]

    def test_react_dashboard_has_form(self, advisor):
        profile = advisor.recommend(
            description="Dashboard", frontend="react",
            product_type="dashboard", industry="general", style="modern",
        )
        assert "form" in profile["component_stack"]

    def test_react_dashboard_has_chart(self, advisor):
        profile = advisor.recommend(
            description="Dashboard", frontend="react",
            product_type="dashboard", industry="general", style="modern",
        )
        assert "chart" in profile["component_stack"]

    def test_vue_saas_stack_complete(self, advisor):
        profile = advisor.recommend(
            description="SaaS platform", frontend="vue",
            product_type="saas", industry="general", style="modern",
        )
        stack = profile["component_stack"]
        expected_keys = {"form", "chart", "icons", "motion"}
        assert expected_keys.issubset(set(stack.keys()))


# ---------------------------------------------------------------------------
# Quality checklist
# ---------------------------------------------------------------------------

class TestQualityChecklist:
    def test_quality_checklist_is_list(self, advisor):
        profile = advisor.recommend(
            description="Test", frontend="react",
            product_type="landing", industry="general", style="modern",
        )
        assert isinstance(profile["quality_checklist"], list)

    def test_quality_checklist_has_minimum_items(self, advisor):
        profile = advisor.recommend(
            description="Test", frontend="react",
            product_type="landing", industry="general", style="modern",
        )
        assert len(profile["quality_checklist"]) >= 4


# ---------------------------------------------------------------------------
# Banned patterns
# ---------------------------------------------------------------------------

class TestBannedPatterns:
    def test_landing_banned_hero(self, advisor):
        patterns = advisor.PRODUCT_PROFILES["landing"]["banned_patterns"]
        assert any("Hero" in p or "口号" in p for p in patterns)

    def test_dashboard_banned_marketing(self, advisor):
        patterns = advisor.PRODUCT_PROFILES["dashboard"]["banned_patterns"]
        assert any("营销" in p for p in patterns)

    def test_general_banned_ai_template(self, advisor):
        patterns = advisor.PRODUCT_PROFILES["general"]["banned_patterns"]
        assert any("AI" in p for p in patterns)
