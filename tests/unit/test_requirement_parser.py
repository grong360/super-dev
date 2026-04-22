"""
需求解析与前端骨架测试
"""

import json
from pathlib import Path

from super_dev.creators.document_generator import DocumentGenerator
from super_dev.creators.frontend_builder import FrontendScaffoldBuilder
from super_dev.creators.requirement_parser import RequirementParser


class TestRequirementParser:
    def test_parse_requirements_by_keywords(self):
        parser = RequirementParser()
        requirements = parser.parse_requirements("做一个支持登录和搜索筛选的数据平台")

        spec_names = {item["spec_name"] for item in requirements}
        assert "core" in spec_names
        assert "auth" in spec_names
        assert "search" in spec_names

    def test_parse_requirements_fallback(self):
        parser = RequirementParser()
        requirements = parser.parse_requirements("构建一个特别的新产品")

        spec_names = {item["spec_name"] for item in requirements}
        # When no keyword matches, core + inferred features + operation are generated
        assert "core" in spec_names
        assert "operation" in spec_names

    def test_detect_scenario(self, temp_project_dir: Path):
        parser = RequirementParser()

        assert parser.detect_scenario(temp_project_dir) == "0-1"

        (temp_project_dir / "src").mkdir()
        assert parser.detect_scenario(temp_project_dir) == "1-N+1"

    def test_detect_request_mode(self):
        parser = RequirementParser()

        assert parser.detect_request_mode("修复登录接口报错并补充回归验证") == "bugfix"
        assert parser.detect_request_mode("开发一个新的商业官网") == "feature"

    def test_analyze_requirement_detects_cross_platform_frontend_preferences(self):
        parser = RequirementParser()

        expo_analysis = parser.analyze_requirement("做一个 Expo 的 React Native 巡检 App")
        tauri_analysis = parser.analyze_requirement("做一个 Tauri 桌面客户端，支持本地文件导入")
        capacitor_analysis = parser.analyze_requirement(
            "做一个 Ionic + Capacitor 的跨端服务工单应用"
        )

        assert expo_analysis.tech_preferences["frontend"] == "expo"
        assert tauri_analysis.tech_preferences["frontend"] == "tauri"
        assert capacitor_analysis.tech_preferences["frontend"] == "ionic"

    def test_analyze_requirement_detects_electron_and_wails_preferences(self):
        parser = RequirementParser()

        electron_analysis = parser.analyze_requirement("做一个 Electron 数据分析桌面端")
        wails_analysis = parser.analyze_requirement("做一个 Wails 桌面管理台")

        assert electron_analysis.tech_preferences["frontend"] == "electron"
        assert wails_analysis.tech_preferences["frontend"] == "wails"


class TestDocumentGeneratorIntegration:
    def test_document_generator_extracts_dynamic_requirements(self):
        generator = DocumentGenerator(
            name="payment-app",
            description="支付系统需要通知中心和账单功能",
            frontend="react",
            backend="node",
        )

        requirements = generator.extract_requirements()
        names = {req["spec_name"] for req in requirements}
        assert "billing" in names
        assert "notification" in names

    def test_document_generator_includes_language_preferences(self):
        generator = DocumentGenerator(
            name="polyglot-platform",
            description="构建支持多端协作的智能平台",
            frontend="react",
            backend="python",
            language_preferences=["python", "typescript", "rust"],
        )

        language_line = "Python / TypeScript / Rust"
        assert language_line in generator.generate_prd()
        assert language_line in generator.generate_architecture()
        assert language_line in generator.generate_uiux()

    def test_document_generator_includes_richer_commercial_sections(self):
        generator = DocumentGenerator(
            name="delivery-grade-app",
            description="构建一个面向企业协作的商业级工作台",
            frontend="react",
            backend="python",
        )

        prd = generator.generate_prd()
        architecture = generator.generate_architecture()
        uiux = generator.generate_uiux()

        assert "### 1.4 市场与对标结论" in prd
        assert "### 1.6 需求澄清问题" in prd
        assert "### 1.7 联网研究证据与方案对比" in prd
        assert "### 1.8 关键决策账本" in prd
        assert "### 1.9 用户到专业交付统一协议" in prd
        assert "### 2.4 功能优先级与范围边界" in prd
        assert "### 2.6 实施方案分层与取舍" in prd
        assert "### 7.4 业务验收矩阵" in prd
        assert "### 1.3 需求到架构的落地映射" in architecture
        assert "### 1.4 架构选型取舍与证据链" in architecture
        assert "### 1.5 架构决策账本" in architecture
        assert "### 1.6 Agent 执行流水线（全端）" in architecture
        assert "### 3.3 关键时序图" in architecture
        assert "### 8.3 容错与降级策略" in architecture
        assert "### 1.4 商业级体验目标" in uiux
        assert "### 1.5 设计 Intelligence 结论" in uiux
        assert "UI 系统冻结决策" in uiux
        assert "备选实现路径" in uiux
        assert "### 2.7 布局栅格与密度策略" in uiux
        assert "### 2.8 组件生态与实现基线" in uiux
        assert "### 2.10 多端适配与平台化设计策略" in uiux
        assert "### 2.11 商业级设计质量门禁" in uiux
        assert "### 2.12 精美 UI 执行工作流（Stitch 范式）" in uiux
        assert "Design Token 冻结输出" in uiux
        assert "### 5.3 组件状态矩阵" in uiux
        assert "### 5.4 图标、图表与内容模块" in uiux
        assert "### 5.5 组件落地清单（Tailwind / 生态组件）" in uiux
        assert "### 7.3 商业化与信任设计" in uiux

    def test_document_generator_embeds_ui_intelligence_stack(self):
        generator = DocumentGenerator(
            name="official-site",
            description="为一个商业级 SaaS 产品生成官方网站和产品页",
            frontend="react",
            backend="node",
        )

        uiux = generator.generate_uiux()

        assert "shadcn/ui + Radix UI + Tailwind CSS" in uiux
        assert "表单与验证" in uiux
        assert "图标体系" in uiux
        assert "多场景组件库矩阵" in uiux
        assert "设计参考锚点" in uiux
        assert "品牌信号与权威感" in uiux
        assert "证明构图规则" in uiux
        assert "组件工艺要求" in uiux
        assert "布局张力纪律" in uiux
        assert "Screen Recipes（页面配方冻结）" in uiux
        assert "Claude-Design 风格执行协议" in uiux

    def test_document_generator_emits_ui_contract(self):
        generator = DocumentGenerator(
            name="ops-suite",
            description="构建一个企业协作 SaaS 工作台",
            frontend="react",
            backend="python",
        )

        contract = generator.generate_ui_contract()

        assert contract["ui_library_preference"]["preferred"] == "shadcn/ui + Radix UI + Tailwind CSS"
        assert contract["ui_library_preference"]["strict"] is False
        assert contract["component_stack"]["icons"]
        assert contract["icon_system"] == contract["component_stack"]["icons"]
        assert contract["emoji_policy"]["allowed_in_ui"] is False
        assert contract["emoji_policy"]["allowed_as_icon"] is False
        assert contract["emoji_policy"]["allowed_during_development"] is False
        assert len(contract["design_references"]) == 3
        assert contract["design_references"][0]["name"]
        assert contract["design_tokens"]["css_variables"]
        assert contract["typography_preset"]["heading"]
        assert contract["brand_signal_manifest"]["tone_descriptors"]
        assert contract["proof_composition_rules"]["hero_proof_stack"]
        assert contract["component_craft_requirements"]
        assert contract["layout_tension_rules"]
        assert contract["screen_recipes"]
        assert contract["screen_recipes"][0]["section_order"]
        assert contract["screen_recipes"][0]["proof_composition"]
        assert contract["design_context_protocol"]["preferred_import_order"]
        assert contract["tweak_strategy"]["default_controls"]
        assert contract["verification_handoff"]["required_artifacts"]

    def test_document_generator_prefers_explicit_design_inspiration(self):
        generator = DocumentGenerator(
            name="brand-site",
            description="为一个商业级 SaaS 产品生成官方网站和产品页",
            frontend="react",
            backend="node",
            design_inspiration_slug="vercel",
        )

        contract = generator.generate_ui_contract()
        uiux = generator.generate_uiux()

        assert contract["selected_design_reference"]["slug"] == "vercel"
        assert contract["design_references"][0]["slug"] == "vercel"
        assert "Vercel（已选灵感）" in uiux

    def test_document_generator_emits_uniapp_framework_playbook(self):
        generator = DocumentGenerator(
            name="uni-shop",
            description="构建一个 uni-app 会员商城，覆盖 H5、微信小程序和 App 的登录、支付与分享",
            frontend="uni-app",
            backend="node",
        )

        contract = generator.generate_ui_contract()
        uiux = generator.generate_uiux()

        assert contract["framework_playbook"]["framework"] == "uni-app"
        assert "跨平台框架深优化 Playbook（uni-app）" in uiux
        assert "登录/支付/分享流程按平台 provider 拆分" in uiux
        assert "必须验收的真实场景" in uiux
        assert "交付证据要求" in uiux

    def test_document_generator_emits_desktop_framework_playbook(self):
        generator = DocumentGenerator(
            name="desktop-ops",
            description="构建 Electron 桌面分析客户端，支持本地文件导入、通知、快捷键和离线缓存",
            frontend="electron",
            backend="python",
        )

        contract = generator.generate_ui_contract()
        uiux = generator.generate_uiux()

        assert contract["framework_playbook"]["framework"] == "Desktop Web Shell"
        assert "快捷键清单、窗口布局说明、原生桥接清单" in uiux
        assert "文件流与离线恢复验证结果" in uiux

    def test_document_generator_consumes_research_summary_for_evidence(self):
        generator = DocumentGenerator(
            name="research-driven-app",
            description="生成证据驱动文档",
            frontend="react",
            backend="python",
            knowledge_summary={
                "research_confidence": "high",
                "evidence_distribution": {"official": 3, "industry": 1, "community": 0},
                "benchmark_products": ["Product X: benchmark"],
                "primary_sources": [("openai.com", 2)],
            },
        )

        prd = generator.generate_prd()

        assert "研究可信度" in prd
        assert "openai.com" in prd

    def test_execution_plan_switches_to_bugfix_mode(self):
        generator = DocumentGenerator(
            name="hotfix-patch",
            description="修复支付回调重复扣款 bug，并补充回归验证",
            frontend="react",
            backend="python",
        )

        plan = generator.generate_execution_plan(scenario="1-N+1")

        assert "> **请求模式**: bugfix" in plan
        assert "问题复现与影响分析" in plan
        assert "轻量文档冻结" in plan
        assert "宿主执行打法" in plan
        assert "阶段硬门禁" in plan
        assert "docs_confirm 未通过前，不允许进入补丁实现" in plan

    def test_document_generator_respects_explicit_bugfix_mode(self):
        generator = DocumentGenerator(
            name="explicit-hotfix",
            description="优化登录体验",
            request_mode="bugfix",
            frontend="react",
            backend="python",
        )

        prd = generator.generate_prd()
        architecture = generator.generate_architecture()

        assert "### 1.6 需求澄清问题" in prd
        assert "实际症状" in prd
        assert "### 3.3 关键时序图" in architecture
        assert "提交缺陷修复需求" in architecture


class TestFrontendScaffoldBuilder:
    def test_generate_frontend_scaffold(self, temp_project_dir: Path):
        builder = FrontendScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo-app",
            description="一个可演示的需求驱动平台",
            frontend="react",
        )

        result = builder.generate(
            requirements=[
                {
                    "spec_name": "core",
                    "req_name": "business-core-flow",
                    "description": "核心业务流程",
                    "scenarios": [],
                }
            ],
            phases=[
                {
                    "id": "phase-1",
                    "title": "需求对齐与文档冻结",
                    "objective": "冻结文档版本",
                    "deliverables": ["PRD", "架构", "UIUX"],
                }
            ],
            docs={
                "prd": str(temp_project_dir / "output" / "demo-prd.md"),
                "architecture": str(temp_project_dir / "output" / "demo-architecture.md"),
                "uiux": str(temp_project_dir / "output" / "demo-uiux.md"),
                "plan": str(temp_project_dir / "output" / "demo-plan.md"),
                "frontend_blueprint": str(temp_project_dir / "output" / "demo-frontend-blueprint.md"),
            },
        )

        html_path = Path(result["html"])
        css_path = Path(result["css"])
        tokens_path = Path(result["tokens"])
        js_path = Path(result["js"])

        assert html_path.exists()
        assert css_path.exists()
        assert tokens_path.exists()
        assert js_path.exists()
        assert "demo-app" in html_path.read_text(encoding="utf-8")
        assert "--primary" in css_path.read_text(encoding="utf-8")

    def test_frontend_scaffold_prefers_persisted_ui_contract(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "brand-ui-contract.json").write_text(
            json.dumps(
                {
                    "typography_preset": {"heading": "IBM Plex Sans", "body": "Public Sans"},
                    "style_direction": {"direction": "可信、稳定、业务优先"},
                    "component_stack": {"icons": "Lucide Icons"},
                    "ui_library_preference": {
                        "preferred": "shadcn/ui + Radix UI + Tailwind CSS",
                        "strict": False,
                        "decision_rule": "Prefer shadcn unless something more suitable exists.",
                        "final_selected": "shadcn/ui + Radix UI + Tailwind CSS",
                    },
                    "primary_library": {"name": "shadcn/ui + Radix UI + Tailwind CSS"},
                    "color_palette": {
                        "primary": "#123456",
                        "accent": "#14B8A6",
                        "background": "#F5F8FF",
                        "text": "#172133",
                        "border": "#D9E0EA",
                    },
                    "generated_design_system": {
                        "radius": {"lg": "20px"},
                        "shadows": {"lg": "0 12px 30px rgba(0,0,0,0.12)"},
                    },
                    "design_tokens": {"css_variables": ":root { --color-primary: #123456; }\n"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        builder = FrontendScaffoldBuilder(
            project_dir=temp_project_dir,
            name="brand",
            description="品牌化工作台",
            frontend="react",
        )
        result = builder.generate(requirements=[], phases=[], docs={})

        html = Path(result["html"]).read_text(encoding="utf-8")
        css = Path(result["css"]).read_text(encoding="utf-8")
        tokens = Path(result["tokens"]).read_text(encoding="utf-8")
        js = Path(result["js"]).read_text(encoding="utf-8")

        assert "IBM+Plex+Sans" in html
        assert "Icons: Lucide Icons" in html
        assert "#123456" in css
        assert '--font-heading: "IBM Plex Sans"' in css
        assert "--color-primary: #123456" in tokens
        assert "ui_library_preference" in js
        assert "页面配方" in html
        assert "verification_handoff" in js
