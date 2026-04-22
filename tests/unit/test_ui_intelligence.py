import json
from pathlib import Path

from PIL import Image

from super_dev.design import UIIntelligenceAdvisor
from super_dev.reviewers.ui_review import UIReviewReviewer


class TestUIIntelligenceAdvisor:
    def test_recommend_react_dashboard_stack(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="构建一个金融数据分析工作台和运营后台",
            frontend="react",
            product_type="dashboard",
            industry="fintech",
            style="professional",
        )

        assert profile["primary_library"]["name"] == "shadcn/ui + Radix UI + Tailwind CSS"
        assert "TanStack Table" in profile["component_stack"]["table"]
        assert "安全" in "".join(profile["trust_modules"])
        assert any("后台" in item or "营销页" in item for item in profile["banned_patterns"])
        assert any("DaisyUI" in item["name"] or "Aceternity" in item["name"] for item in profile["alternative_libraries"])
        assert any(row["scene"] == "微信小程序" for row in profile["ui_library_matrix"])
        assert len(profile["quality_checklist"]) >= 4
        assert len(profile["design_references"]) == 3
        assert profile["design_references"][0]["name"] == "Linear"
        assert any(ref["name"] == "Stripe" for ref in profile["design_references"])

    def test_recommend_vue_stack_prefers_naive_ui(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="企业协作 SaaS 平台",
            frontend="vue",
            product_type="saas",
            industry="general",
            style="modern",
        )

        assert profile["primary_library"]["name"] == "Naive UI + Tailwind CSS"
        assert profile["component_stack"]["form"] == "vee-validate + Zod / Valibot"

    def test_recommend_miniprogram_stack_prefers_tdesign(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="微信小程序会员商城与下单流程",
            frontend="taro",
            product_type="ecommerce",
            industry="general",
            style="modern",
        )

        assert profile["normalized_frontend"] == "miniapp"
        assert "TDesign 小程序" in profile["primary_library"]["name"]
        assert "小程序" in profile["component_stack"]["form"]

    def test_recommend_uniapp_emits_framework_playbook(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="构建一个 uni-app 会员商城，覆盖 H5、微信小程序和 App 登录支付流程",
            frontend="uni-app",
            product_type="ecommerce",
            industry="general",
            style="modern",
        )

        assert profile["frontend_variant"] == "uni-app"
        assert profile["framework_playbook"]["framework"] == "uni-app"
        assert any("自定义导航栏" in item for item in profile["framework_playbook"]["implementation_modules"])
        assert any("provider" in item or "登录/支付/分享" in item for item in profile["framework_playbook"]["anti_patterns"] + profile["framework_playbook"]["platform_constraints"])

    def test_recommend_desktop_stack_prefers_electron_tauri(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="桌面端数据分析客户端，支持离线与本地文件导入",
            frontend="electron",
            product_type="dashboard",
            industry="general",
            style="professional",
        )

        assert profile["normalized_frontend"] == "desktop"
        assert "Electron / Tauri" in profile["primary_library"]["name"]
        assert "AG Grid" in profile["component_stack"]["table"]
        assert profile["design_references"][0]["name"] in {"Linear", "Raycast"}
        assert profile["framework_playbook"]["framework"] == "Desktop Web Shell"
        assert any("filesystem" in item for item in profile["framework_playbook"]["native_capabilities"])

    def test_recommend_react_native_and_flutter_emit_deep_playbooks(self):
        advisor = UIIntelligenceAdvisor()

        rn = advisor.recommend(
            description="移动端协作应用，需要推送、深链、离线缓存和系统分享",
            frontend="react-native",
            product_type="saas",
            industry="general",
            style="modern",
        )
        flutter = advisor.recommend(
            description="跨端会员应用，需要深色模式、复杂动画和平台感知组件",
            frontend="flutter",
            product_type="saas",
            industry="general",
            style="modern",
        )

        assert rn["framework_playbook"]["framework"] == "React Native"
        assert any("push notification" in item for item in rn["framework_playbook"]["native_capabilities"])
        assert any("iOS 真机" in item or "Android" in item for item in rn["framework_playbook"]["validation_surfaces"])
        assert flutter["framework_playbook"]["framework"] == "Flutter"
        assert any("ThemeData" in item for item in flutter["framework_playbook"]["delivery_evidence"])

    def test_recommend_emits_art_direction_candidates_and_guardrails(self):
        advisor = UIIntelligenceAdvisor()

        profile = advisor.recommend(
            description="高端品牌官网，需要强烈品牌张力、案例证明和清晰 CTA",
            frontend="react",
            product_type="landing",
            industry="general",
            style="luxury",
        )

        assert len(profile["art_direction_candidates"]) >= 2
        assert (
            profile["design_direction_manifest"]["selected_direction"]
            == profile["art_direction_candidates"][0]["name"]
        )
        assert len(profile["anti_ai_slop_guardrails"]["forbidden_motifs"]) >= 3
        assert profile["brand_signal_manifest"]["tone_descriptors"]
        assert profile["proof_composition_rules"]["hero_proof_stack"]
        assert profile["component_craft_requirements"]
        assert profile["layout_tension_rules"]
        critique_dimensions = {
            item["dimension"] for item in profile["critique_rubric"] if isinstance(item, dict)
        }
        assert {
            "philosophy_alignment",
            "visual_hierarchy",
            "brand_authority",
            "craft_quality",
            "functionality",
            "originality",
        }.issubset(critique_dimensions)


class TestUIReviewReviewer:
    def test_review_detects_missing_uiux_sections(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-uiux.md").write_text("# demo uiux", encoding="utf-8")

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        assert report.score < 100
        assert any("缺少关键商业级章节" in item.title for item in report.findings)

    def test_review_uses_preview_surface_signals(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "site-uiux.md").write_text(
            "# site\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n\n## 多端适配与平台化设计策略\n\n## 商业级设计质量门禁\n\n## 精美 UI 执行工作流（Stitch 范式）\n\n## 组件落地清单（Tailwind / 生态组件）\n\nWEB\nH5\n微信小程序\nAPP\n桌面端\n",
            encoding="utf-8",
        )
        (temp_project_dir / "preview.html").write_text(
            """
<!doctype html>
<html>
  <body>
    <header><nav><a href="#pricing">Pricing</a></nav></header>
    <main>
      <section><h1>Commercial Product</h1><button>Start Free</button><img src="hero.png" alt="hero" /></section>
      <section><h2>Case Study</h2><p>Trusted by enterprise customers with security and compliance.</p></section>
      <section><h2>FAQ</h2><a href="#faq">View FAQ</a></section>
    </main>
    <footer></footer>
  </body>
</html>
""",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="site",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        assert report.score > 40
        assert any("预览页已具备基础分区结构" in item for item in report.strengths)
        assert report.alignment_summary["layout_shell"]["passed"] is True
        assert report.alignment_summary["navigation_shell"]["passed"] is True
        assert report.alignment_summary["banned_patterns"]["passed"] is True
        # 验证 UI/UX 专家视角检查已注入
        expert_findings = [f for f in report.findings if f.title.startswith("[UI 专家]") or f.title.startswith("[UX 专家]")]
        assert len(expert_findings) > 0, "UI/UX 专家视角检查应产生至少一项发现"

    def test_review_flags_generic_typography_and_flat_hierarchy(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "brand-uiux.md").write_text(
            "# brand\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n",
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "styles.css").write_text(
            "body { font-family: Inter, Arial, system-ui, sans-serif; }",
            encoding="utf-8",
        )
        (temp_project_dir / "preview.html").write_text(
            """
<!doctype html>
<html>
  <body>
    <header><nav><a href="#hero">Home</a></nav></header>
    <main>
      <section><h1>Brand</h1><button>Start</button></section>
      <section><p>Evidence</p></section>
      <section><p>Pricing</p></section>
    </main>
    <footer></footer>
  </body>
</html>
""",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="brand",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("字体系统过于默认" in title for title in titles)
        assert any("页面层级不足" in title for title in titles)

    def test_review_flags_weak_hero_conversion_signals(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "landing-uiux.md").write_text(
            "# landing\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n",
            encoding="utf-8",
        )
        (temp_project_dir / "preview.html").write_text(
            """
<!doctype html>
<html>
  <body>
    <header><nav><a href="#hero">Home</a></nav></header>
    <main>
      <section><h1>Launch faster</h1><button>Start</button></section>
      <section><h2>Features</h2><p>Feature list</p></section>
      <section><h2>FAQ</h2><p>Answers</p></section>
    </main>
    <footer></footer>
  </body>
</html>
""",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="landing",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("导航信息架构不足" in title for title in titles)
        assert any("首屏 CTA 层级不足" in title for title in titles)
        assert any("首屏信息密度不足" in title for title in titles)

    def test_review_flags_missing_art_direction_guardrails(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-uiux.md").write_text(
            "# demo\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n\n## 多端适配与平台化设计策略\n\n## 商业级设计质量门禁\n\n## 精美 UI 执行工作流（Stitch 范式）\n\n## 组件落地清单（Tailwind / 生态组件）\n\nWEB\nH5\n微信小程序\nAPP\n桌面端\n",
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                        "rule": "禁止 emoji",
                    },
                    "screen_recipes": [
                        {
                            "label": "North Star Hero",
                            "section_order": ["hero", "proof", "cta"],
                            "trust_modules": ["案例", "FAQ"],
                            "required_states": ["loading", "error"],
                        }
                    ],
                    "design_context_protocol": {
                        "preferred_import_order": ["tokens", "components"],
                        "github_import_targets": ["layout"],
                        "single_source_rule": "single source",
                    },
                    "tweak_strategy": {
                        "mode": "single-source prototype with tweakable variations",
                        "default_controls": ["信息密度", "标题张力"],
                        "persistence_rule": "persist",
                    },
                    "verification_handoff": {
                        "verification_order": ["preview", "ui-review"],
                        "required_artifacts": ["output/frontend/index.html"],
                        "acceptance_checks": ["no emoji"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (temp_project_dir / "preview.html").write_text(
            """
<!doctype html>
<html>
  <body>
    <header><nav><a href="#hero">Home</a></nav></header>
    <main>
      <section><h1>Launch faster</h1><button>Start</button></section>
      <section><h2>Proof</h2><p>Case study and FAQ</p></section>
      <section><h2>CTA</h2><a href="#cta">Contact</a></section>
    </main>
    <footer></footer>
  </body>
</html>
""",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("缺少可比较的视觉方向候选" in title for title in titles)
        assert report.alignment_summary["art_direction_candidates"]["passed"] is False
        assert report.alignment_summary["anti_ai_slop_guardrails"]["passed"] is False

    def test_review_flags_emoji_icons_and_claude_like_shell(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "ops-uiux.md").write_text(
            (
                "# ops\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 可信、稳定、业务优先\n"
                "**字体组合**: Manrope / Source Sans 3\n"
                "**配色逻辑**: Fintech Blue（主色 #2563EB / 强调色 #0EA5E9）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            """
export function App() {
  return (
    <div className="conversation-shell chat-sidebar">
      <aside className="thread-list">History</aside>
      <main>
        <button>✨ 保存</button>
        <div className="assistant-message">hello</div>
      </main>
    </div>
  );
}
""",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="ops",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("emoji 功能图标" in title for title in titles)
        assert any("Claude / 聊天式产品骨架复刻痕迹" in title for title in titles)
        assert report.alignment_summary["layout_shell"]["passed"] is False
        assert report.alignment_summary["navigation_shell"]["passed"] is False
        assert report.alignment_summary["banned_patterns"]["passed"] is False

    def test_review_flags_uiux_frozen_icon_system_not_reflected_in_source(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "brand-uiux.md").write_text(
            (
                "# brand\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 现代商业产品基线，品牌感与效率并重\n"
                "**字体组合**: Manrope / Source Sans 3\n"
                "**配色逻辑**: General SaaS（主色 #2563EB / 强调色 #14B8A6）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"@heroicons/react":"^2.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "export function App(){ return <div><span>Save</span></div>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="brand",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("图标系统" in title for title in titles)

    def test_review_flags_uiux_frozen_font_pair_not_reflected_in_source(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "fonts-uiux.md").write_text(
            (
                "# fonts\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 可信、稳定、业务优先\n"
                "**字体组合**: IBM Plex Sans / Public Sans\n"
                "**配色逻辑**: Fintech Blue（主色 #2563EB / 强调色 #14B8A6）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"lucide-react":"^0.1.0","@radix-ui/react-dialog":"^1.0.0","tailwindcss":"^3.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "styles.css").write_text(
            "body { font-family: Inter, Arial, system-ui, sans-serif; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="fonts",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("字体组合" in title for title in titles)

    def test_review_flags_ui_contract_tokens_not_wired_into_source(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "contract-uiux.md").write_text(
            (
                "# contract\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 编辑感、品牌化、商业完成度优先\n"
                "**字体组合**: Space Grotesk / Inter\n"
                "**配色逻辑**: Editorial Blue（主色 #0F172A / 强调色 #2563EB）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "contract-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; --font-heading: \\"Space Grotesk\\"; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #0F172A; --font-heading: 'Space Grotesk'; }\n",
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"lucide-react":"^0.1.0","@radix-ui/react-dialog":"^1.0.0","tailwindcss":"^3.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "export function App(){ return <main className='bg-slate-950 text-white'>Hello</main>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="contract",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("Design Token 接入实现" in title for title in titles)

    def test_review_flags_missing_claude_design_protocol_fields(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "protocol-uiux.md").write_text(
            (
                "# protocol\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 编辑感、品牌化、商业完成度优先\n"
                "**字体组合**: Space Grotesk / Inter\n"
                "**配色逻辑**: Editorial Blue（主色 #0F172A / 强调色 #2563EB）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "protocol-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #0F172A; }\n",
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "import 'output/frontend/design-tokens.css';\nexport function App(){ return <main style={{color:'var(--color-primary)'}}><nav>Nav</nav><section>Ready</section></main>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="protocol",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("Claude-Design 风格执行协议未冻结" in title for title in titles)
        assert report.alignment_summary["screen_recipes"]["passed"] is False

    def test_review_flags_missing_frontend_runtime_for_claude_design_protocol(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "runtime-uiux.md").write_text(
            (
                "# runtime\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 编辑感、品牌化、商业完成度优先\n"
                "**字体组合**: Space Grotesk / Inter\n"
                "**配色逻辑**: Editorial Blue（主色 #0F172A / 强调色 #2563EB）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "runtime-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["客户案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source prototype"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist tweak decisions into the same prototype"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #0F172A; }\n",
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            (
                "import 'output/frontend/design-tokens.css';\n"
                "export function App(){ return <main>"
                "<section>North Star Hero</section><section>hero</section><section>客户案例</section>"
                "<section>tokens theme.ts single source prototype</section>"
                "<section>信息密度 persist tweak decisions into the same prototype</section>"
                "<section>preview output/frontend/index.html no emoji</section>"
                "</main>; }"
            ),
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="runtime",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("frontend runtime 缺少 Claude-Design 协议证据" in title for title in titles)
        assert report.alignment_summary["runtime_claude_design_protocol"]["passed"] is False

    def test_review_flags_runtime_mismatch_for_claude_design_protocol(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "runtime-mismatch-uiux.md").write_text(
            (
                "# runtime mismatch\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 编辑感、品牌化、商业完成度优先\n"
                "**字体组合**: Space Grotesk / Inter\n"
                "**配色逻辑**: Editorial Blue（主色 #0F172A / 强调色 #2563EB）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "runtime-mismatch-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"},\n'
                '  "screen_recipes": [{"label": "North Star Hero", "section_order": ["hero"], "trust_modules": ["客户案例"], "required_states": ["loading"]}],\n'
                '  "design_context_protocol": {"preferred_import_order": ["tokens"], "github_import_targets": ["theme.ts"], "single_source_rule": "single source prototype"},\n'
                '  "tweak_strategy": {"mode": "single-source prototype", "default_controls": ["信息密度"], "persistence_rule": "persist tweak decisions into the same prototype"},\n'
                '  "verification_handoff": {"verification_order": ["preview"], "required_artifacts": ["output/frontend/index.html"], "acceptance_checks": ["no emoji"]}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "runtime-mismatch-frontend-runtime.json").write_text(
            (
                "{\n"
                '  "passed": true,\n'
                '  "checks": {\n'
                '    "ui_screen_recipes": false,\n'
                '    "ui_design_context_protocol": true,\n'
                '    "ui_tweak_strategy": true,\n'
                '    "ui_verification_handoff": false\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #0F172A; }\n",
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            (
                "import 'output/frontend/design-tokens.css';\n"
                "export function App(){ return <main>"
                "<section>North Star Hero</section><section>hero</section><section>客户案例</section>"
                "<section>tokens theme.ts single source prototype</section>"
                "<section>信息密度 persist tweak decisions into the same prototype</section>"
                "<section>preview output/frontend/index.html no emoji</section>"
                "</main>; }"
            ),
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="runtime-mismatch",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("UI Review 与 frontend runtime 的 Claude-Design 结论不一致" in title for title in titles)
        assert report.alignment_summary["runtime_claude_design_protocol"]["passed"] is False
        assert report.alignment_summary["source_claude_design_protocol"]["passed"] is True

    def test_review_tracks_framework_playbook_execution_for_uniapp(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "uni-uiux.md").write_text(
            "# uni\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n\n## 多端适配与平台化设计策略\n",
            encoding="utf-8",
        )
        (output_dir / "uni-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "icon_system": "TDesign Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Alibaba PuHuiTi", "body": "PingFang SC"},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + Taro / UniApp"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"},\n'
                '  "framework_playbook": {\n'
                '    "framework": "uni-app",\n'
                '    "implementation_modules": ["自定义导航栏高度、状态栏占位、胶囊按钮区域必须独立建模"],\n'
                '    "platform_constraints": ["自定义导航启用后必须显式处理 status bar 与安全区"],\n'
                '    "execution_guardrails": ["先冻结 pages.json / 分包 / navigationStyle / provider 配置，再开始页面实现"],\n'
                '    "native_capabilities": ["登录/支付/分享 provider 必须按端隔离并显式验收"],\n'
                '    "validation_surfaces": ["微信小程序导航/支付/触控与包体策略"],\n'
                '    "delivery_evidence": ["三端差异说明与条件编译点清单"]\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(":root { --color-primary: #0F172A; }\n", encoding="utf-8")
        (temp_project_dir / "pages.json").write_text('{"globalStyle":{"navigationStyle":"custom"}}', encoding="utf-8")
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.vue").write_text(
            "<script setup>uni.getSystemInfoSync();</script><template><view>#ifdef MP-WEIXIN provider navigationStyle statusBarHeight</view></template>",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="uni",
            tech_stack={"frontend": "uni-app", "backend": "node", "platform": "miniapp"},
        )
        report = reviewer.review()

        assert report.alignment_summary["framework_playbook"]["passed"] is True
        assert report.alignment_summary["framework_execution"]["passed"] is True

    def test_review_flags_missing_framework_playbook_for_uniapp(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "super-dev.yaml").write_text(
            "frontend: uni-app\nbackend: node\ndescription: uni-app 商城\n",
            encoding="utf-8",
        )
        (output_dir / "uni-uiux.md").write_text(
            "# uni\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n",
            encoding="utf-8",
        )
        (output_dir / "uni-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Space Grotesk", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + Taro / UniApp + Tailwind(TW 适配)"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="uni",
            tech_stack={"frontend": "uni-app", "backend": "node", "platform": "miniapp"},
        )
        report = reviewer.review()

        assert report.alignment_summary["framework_playbook"]["passed"] is False
        assert any("跨平台框架 Playbook 未冻结" in item.title for item in report.findings)

    def test_review_flags_missing_native_capabilities_for_uniapp(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "super-dev.yaml").write_text(
            "frontend: uni-app\nbackend: node\ndescription: uni-app 商城\n",
            encoding="utf-8",
        )
        (output_dir / "uni-uiux.md").write_text(
            "# uni\n\n## 设计 Intelligence 结论\n\n## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n\n## 多端适配与平台化设计策略\n",
            encoding="utf-8",
        )
        (output_dir / "uni-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "icon_system": "TDesign Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Alibaba PuHuiTi", "body": "PingFang SC"},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + Taro / UniApp"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #0F172A; }"},\n'
                '  "framework_playbook": {\n'
                '    "framework": "uni-app",\n'
                '    "implementation_modules": ["自定义导航栏高度、状态栏占位、胶囊按钮区域必须独立建模"],\n'
                '    "platform_constraints": ["自定义导航启用后必须显式处理 status bar 与安全区"],\n'
                '    "execution_guardrails": ["先冻结 pages.json / 分包 / navigationStyle / provider 配置，再开始页面实现"],\n'
                '    "validation_surfaces": ["微信小程序导航/支付/触控与包体策略"],\n'
                '    "delivery_evidence": ["三端差异说明与条件编译点清单"]\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(":root { --color-primary: #0F172A; }\n", encoding="utf-8")
        (temp_project_dir / "pages.json").write_text('{"globalStyle":{"navigationStyle":"custom"}}', encoding="utf-8")
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.vue").write_text(
            "<script setup>uni.getSystemInfoSync();</script><template><view>#ifdef MP-WEIXIN provider navigationStyle statusBarHeight</view></template>",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="uni",
            tech_stack={"frontend": "uni-app", "backend": "node", "platform": "miniapp"},
        )
        report = reviewer.review()

        assert report.alignment_summary["framework_playbook"]["passed"] is False
        assert report.alignment_summary["native_capabilities"]["passed"] is False
        assert any("跨平台框架治理仍缺少关键面" in item.title for item in report.findings)

    def test_review_accepts_magic_ui_when_ui_contract_selects_it(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "magic-uiux.md").write_text(
            (
                "# magic\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 展示增强、品牌驱动、轻动效\n"
                "**字体组合**: Sora / Inter\n"
                "**配色逻辑**: Midnight Contrast（主色 #111827 / 强调色 #22C55E）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: Magic UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "magic-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "Sora", "body": "Inter"},\n'
                '  "ui_library_preference": {"final_selected": "Magic UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #111827; --font-heading: \\"Sora\\"; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #111827; --font-heading: 'Sora'; }\n",
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"magicui":"^1.0.0","lucide-react":"^0.1.0","tailwindcss":"^3.0.0","framer-motion":"^11.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "import 'output/frontend/design-tokens.css';\nimport { MagicCard } from 'magicui';\nexport function App(){ return <main style={{color:'var(--color-primary)'}}><MagicCard>Magic</MagicCard></main>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="magic",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert not any("组件生态" in title for title in titles)

    def test_review_flags_component_import_drift_when_dependency_exists_but_source_not_using_contract(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "imports-uiux.md").write_text(
            (
                "# imports\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 可信、稳定、业务优先\n"
                "**字体组合**: IBM Plex Sans / Public Sans\n"
                "**配色逻辑**: Fintech Blue（主色 #2563EB / 强调色 #14B8A6）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "imports-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "IBM Plex Sans", "body": "Public Sans"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #2563EB; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #2563EB; }\n",
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"lucide-react":"^0.1.0","@radix-ui/react-dialog":"^1.0.0","tailwindcss":"^3.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "import './styles.css';\nimport { Button } from '@/components/common/Button';\nexport function App(){ return <main style={{color:'var(--color-primary)'}}><Button>Ready</Button></main>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="imports",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("源码 import 未落实冻结组件生态" in title for title in titles)
        assert report.alignment_summary["component_ecosystem"]["passed"] is True
        assert report.alignment_summary["component_imports"]["passed"] is False

    def test_review_flags_missing_theme_entry_and_navigation_shell(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        frontend_output = output_dir / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        frontend_output.mkdir(parents=True, exist_ok=True)
        (output_dir / "shell-uiux.md").write_text(
            (
                "# shell\n\n## 设计 Intelligence 结论\n\n"
                "**主视觉气质**: 可信、稳定、业务优先\n"
                "**字体组合**: IBM Plex Sans / Public Sans\n"
                "**配色逻辑**: Fintech Blue（主色 #2563EB / 强调色 #14B8A6）\n"
                "**图标系统**: Lucide Icons\n"
                "**首选组件生态**: shadcn/ui + Radix UI + Tailwind CSS\n"
                "## 组件生态与实现基线\n\n## 页面骨架优先级\n\n## 图标、图表与内容模块\n\n## 商业化与信任设计\n"
            ),
            encoding="utf-8",
        )
        (output_dir / "shell-ui-contract.json").write_text(
            (
                "{\n"
                '  "icon_system": "Lucide Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "typography_preset": {"heading": "IBM Plex Sans", "body": "Public Sans"},\n'
                '  "ui_library_preference": {"final_selected": "shadcn/ui + Radix UI + Tailwind CSS"},\n'
                '  "design_tokens": {"css_variables": ":root { --color-primary: #2563EB; }"}\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (frontend_output / "design-tokens.css").write_text(
            ":root { --color-primary: #2563EB; }\n",
            encoding="utf-8",
        )
        (temp_project_dir / "package.json").write_text(
            '{"dependencies":{"lucide-react":"^0.1.0","@radix-ui/react-dialog":"^1.0.0","tailwindcss":"^3.0.0"}}',
            encoding="utf-8",
        )
        frontend_dir = temp_project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "App.tsx").write_text(
            "export function App(){ return <main><section>Dashboard</section></main>; }",
            encoding="utf-8",
        )

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="shell",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("主题入口" in title for title in titles)
        assert any("导航骨架" in title for title in titles)
        assert report.alignment_summary["theme_entry"]["passed"] is False
        assert report.alignment_summary["navigation_shell"]["passed"] is False

    def test_screenshot_analysis_extracts_visual_metrics(self, temp_project_dir: Path):
        image_path = temp_project_dir / "shot.png"
        image = Image.new("RGB", (120, 80), "#ffffff")
        for x in range(20, 100):
            for y in range(20, 60):
                image.putpixel((x, y), (15, 124, 250))
        image.save(image_path)

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        metrics = reviewer._analyze_screenshot(image_path)

        assert metrics["blank_ratio"] < 1
        assert metrics["accent_ratio"] > 0
        assert metrics["unique_colors"] >= 2
        assert "dominant_color_ratio" in metrics
        assert "contrast_span" in metrics

    def test_screenshot_analysis_detects_flat_single_surface_risk(self, temp_project_dir: Path):
        image_path = temp_project_dir / "flat-shot.png"
        image = Image.new("RGB", (180, 120), "#f7f7f7")
        for x in range(70, 110):
            for y in range(48, 72):
                image.putpixel((x, y), (235, 235, 235))
        image.save(image_path)

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="flat",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        metrics = reviewer._analyze_screenshot(image_path)

        assert metrics["dominant_color_ratio"] > 0.78
        assert metrics["contrast_span"] < 0.18

    def test_review_flags_flat_screenshot_visual_risk(self, temp_project_dir: Path):
        (temp_project_dir / "preview.html").write_text(
            "<!doctype html><html><body><main><section><h1>Preview</h1></section></main></body></html>",
            encoding="utf-8",
        )
        image_path = temp_project_dir / "flat-review.png"
        image = Image.new("RGB", (200, 140), "#f7f7f7")
        for x in range(88, 112):
            for y in range(58, 82):
                image.putpixel((x, y), (236, 236, 236))
        image.save(image_path)

        reviewer = UIReviewReviewer(
            project_dir=temp_project_dir,
            name="flat-review",
            tech_stack={"frontend": "react", "backend": "node", "platform": "web"},
        )
        reviewer._capture_preview_screenshot = lambda _: image_path  # type: ignore[method-assign]

        report = reviewer.review()

        titles = [item.title for item in report.findings]
        assert any("截图明暗层级不足" in title for title in titles)
        assert any("截图视觉表面过于单一" in title for title in titles)
        assert report.alignment_summary["screenshot_visual_judge"]["passed"] is False
