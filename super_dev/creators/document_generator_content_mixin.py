"""DocumentGenerator content mixin helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime


class DocumentGeneratorContentMixin:
    def _get_product_type_desc(self, product_type: str) -> str:
        """获取产品类型描述"""
        descs = {
            "saas": "SaaS 软件服务，需要专业可信的设计",
            "ecommerce": "电商平台，注重转化和购买体验",
            "landing": "营销落地页，强调 CTA 和转化",
            "dashboard": "管理后台，注重数据展示和操作效率",
            "content": "内容平台，注重阅读体验",
            "general": "通用产品",
        }
        return descs.get(product_type, "常规产品")

    def _get_industry_desc(self, industry: str) -> str:
        """获取行业描述"""
        descs = {
            "healthcare": "医疗健康行业，需要传递安全、专业感",
            "fintech": "金融科技，需要信任、安全的设计语言",
            "education": "教育行业，需要亲和力、专业性",
            "legal": "法律服务行业，需要权威、可信和清晰表达",
            "government": "政务/公共服务，需要高可读性与可访问性",
            "beauty": "美业/健康服务，需要品牌感、精致感与转化路径",
            "general": "通用行业",
        }
        return descs.get(industry, "常规行业")

    def _get_style_desc(self, style: str) -> str:
        """获取风格描述"""
        descs = {
            "minimal": "极简风格，去除冗余，突出核心",
            "professional": "专业风格，商务、正式",
            "playful": "活泼风格，有趣、生动",
            "luxury": "奢华风格，高端、精致",
            "modern": "现代风格，时尚、前沿",
        }
        return descs.get(style, "现代风格")

    def _lighten(self, hex_color: str, factor: float) -> str:
        """将颜色变浅"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"

    def _darken(self, hex_color: str, factor: float) -> str:
        """将颜色加深"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{max(r, 0):02X}{max(g, 0):02X}{max(b, 0):02X}"

    def _generate_design_principles(self, analysis: dict) -> str:
        """生成领域定制的设计理念"""
        product_type = analysis.get("product_type", "general")

        principles = {
            "landing": [
                ("视觉叙事", "用截图、流程图和数据取代抽象描述，让用户在 5 秒内理解产品价值"),
                ("转化驱动", "每个滚动屏都有明确的信息目标和行动入口，避免空洞的装饰区块"),
                ("信任优先", "客户案例、数据指标、安全标识、合作品牌等信任元素贯穿全页"),
                ("品牌识别", "通过字体、配色、间距和排版节奏建立独特的品牌感，拒绝模板化"),
            ],
            "saas": [
                ("效率至上", "工作台和操作界面以任务完成效率为第一目标，减少页面跳转"),
                ("信息层级", "数据密度适中，关键指标突出，次要信息可折叠，避免信息过载"),
                ("状态透明", "每个操作都有明确的状态反馈（加载、成功、失败、空态），减少用户焦虑"),
                ("渐进展示", "新用户看到引导和简化视图，专业用户可切换到高级功能和密集布局"),
            ],
            "dashboard": [
                ("数据可读", "数据可视化以业务洞察为目标，不追求炫酷图表，确保一眼能读出结论"),
                ("操作直达", "从数据到操作的路径不超过 2 步，关键操作始终可见"),
                ("密度适配", "高密度信息区使用紧凑间距和小字号，操作区保持舒适的点击目标"),
                ("实时感知", "关键数据支持实时/近实时更新，状态变化有视觉提示"),
            ],
            "ecommerce": [
                ("购买信心", "高质量商品图、评价系统、价格对比和配送说明降低购买决策成本"),
                ("转化漏斗", "从浏览到下单的路径清晰顺畅，减少每一步的流失"),
                ("移动优先", "所有购买流程在手机端完整可用，拇指热区布局"),
                ("信任构建", "安全支付标识、退换政策、客服入口等信任元素始终可见"),
            ],
        }

        selected = principles.get(
            product_type,
            [
                (
                    "用户价值",
                    f"围绕{self.description[:30]}的核心场景设计，每个页面都服务于明确的用户目标",
                ),
                ("专业品质", "组件、间距、字体和配色体现成熟商业产品的品质感，拒绝粗糙和模板化"),
                ("一致体验", "跨页面的视觉语言、交互模式和信息架构保持统一"),
                ("渐进增强", "核心功能简洁直观，高级功能按需展开，不同用户有不同的最优体验路径"),
            ],
        )

        lines = []
        for title, desc in selected:
            lines.append(f"- **{title}**: {desc}")

        return "\n".join(lines)

    def _generate_component_library_guide(self, profile: dict) -> str:
        """生成组件库使用指南"""
        lib_name = profile.get("primary_library", {}).get("name", "shadcn/ui")

        if "shadcn" in lib_name.lower():
            return """**必装组件（MVP 基线）**:
```bash
npx shadcn@latest add button card input label select textarea badge avatar
npx shadcn@latest add dialog sheet dropdown-menu command toast sonner
npx shadcn@latest add table tabs separator skeleton scroll-area
```

**组合示例 - 页面头部**:
```tsx
<header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
  <div className="container flex h-14 items-center">
    <nav className="flex items-center space-x-6 text-sm font-medium">
      {/* 使用 cn() 管理条件样式 */}
    </nav>
    <div className="ml-auto flex items-center space-x-4">
      <Button variant="ghost" size="icon"><Bell className="h-4 w-4" /></Button>
      <Avatar><AvatarFallback>UN</AvatarFallback></Avatar>
    </div>
  </div>
</header>
```

**组合示例 - 数据卡片**:
```tsx
<Card className="group hover:shadow-md transition-all duration-200">
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">总用户数</CardTitle>
    <Users className="h-4 w-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">12,345</div>
    <p className="text-xs text-muted-foreground">较上月 +12.5%</p>
  </CardContent>
</Card>
```

**组合示例 - 空态**:
```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <Inbox className="h-12 w-12 text-muted-foreground/50 mb-4" />
  <h3 className="text-lg font-medium">暂无数据</h3>
  <p className="text-sm text-muted-foreground mt-1 mb-4">当前没有可显示的内容</p>
  <Button>创建第一个</Button>
</div>
```

**图标库**: 统一使用 Lucide React (`lucide-react`)，禁止 emoji 替代。
**起步约束**: 进入页面实现前必须先锁定图标库，不允许“先用 emoji 顶上后面再换”。
"""
        elif "ant" in lib_name.lower():
            return """**主题定制（必须）**:
```typescript
// theme/index.ts
import type { ThemeConfig } from 'antd';

const theme: ThemeConfig = {
  token: {
    colorPrimary: 'var(--primary-500)',
    borderRadius: 8,
    fontFamily: "'Plus Jakarta Sans', 'Noto Sans SC', sans-serif",
    fontSize: 14,
    colorBgContainer: '#ffffff',
  },
  components: {
    Button: { controlHeight: 40, borderRadius: 8 },
    Card: { borderRadiusLG: 12, paddingLG: 24 },
    Input: { controlHeight: 40 },
  },
};
```

**禁止默认 Ant Design 风格直出**，必须重写 token 体系。
"""
        else:
            return """- 必须在项目初始化时重写 design token（颜色、间距、圆角、字体）
- 不允许使用组件库默认主题直接上线
- 所有交互组件必须有 hover/focus/active/disabled 四态
- 图标统一使用 Lucide / Heroicons，禁止 emoji
- 开始 UI 编码前先声明图标库，不允许临时用 emoji 占位
"""

    def _get_ui_intelligence(self, analysis: dict | None = None) -> dict:
        """获取结构化 UI Intelligence 推荐"""
        analysis = analysis or self._analyze_project_for_design()
        from super_dev.design import UIIntelligenceAdvisor

        advisor = UIIntelligenceAdvisor()
        return advisor.recommend(
            description=self.description,
            frontend=self.frontend,
            product_type=analysis["product_type"],
            industry=analysis["industry"],
            style=analysis["style"],
            ui_library=self.ui_library,
            preferred_design_reference_slug=getattr(self, "design_inspiration_slug", ""),
        )

    def _get_design_system_bundle(self, analysis: dict, profile: dict) -> dict:
        """把设计系统生成器的结果接入 UIUX 文档，而不是只停留在 CLI 里。"""
        try:
            from super_dev.design import DesignSystemGenerator

            generator = DesignSystemGenerator()
            keywords = list(
                dict.fromkeys(
                    [
                        analysis.get("style", "modern"),
                        analysis.get("product_type", "general"),
                        analysis.get("industry", "general"),
                        *profile.get("knowledge_keywords", []),
                    ]
                )
            )[:10]
            design_system = generator.generate(
                product_type=analysis.get("product_type", "general"),
                industry=analysis.get("industry", "general"),
                keywords=keywords,
                platform=self.platform,
            )
            return {
                "design_system": design_system,
                "css_variables_preview": "\n".join(
                    design_system.to_css_variables().splitlines()[:28]
                ),
                "tailwind_preview": json.dumps(
                    design_system.to_tailwind_config(), ensure_ascii=False, indent=2
                ),
            }
        except Exception as exc:
            logging.getLogger(__name__).warning("Design system bundle failed: %s", exc)
            return {"design_system": None, "css_variables_preview": "", "tailwind_preview": ""}

    def _build_ui_contract_payload(
        self, analysis: dict, profile: dict, design_bundle: dict | None = None
    ) -> dict:
        design_bundle = design_bundle or {}
        design_system = design_bundle.get("design_system")
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        stack = profile.get("component_stack", {})
        primary = profile.get("primary_library", {})
        icon_system = (
            stack.get("icon")
            or stack.get("icons")
            or profile.get("icon_system")
            or profile.get("icon_library")
            or primary.get("icon_system")
            or ""
        )
        screen_recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        design_context_protocol = self._build_design_context_protocol(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        tweak_strategy = self._build_tweak_strategy(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        verification_handoff = self._build_verification_handoff(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        payload = {
            "analysis": {
                "product_type": analysis.get("product_type", "general"),
                "industry": analysis.get("industry", "general"),
                "style": analysis.get("style", "modern"),
                "platform": self.platform,
                "frontend": self.frontend,
                "design_inspiration_slug": getattr(self, "design_inspiration_slug", ""),
            },
            "style_direction": profile.get("style_direction", {}),
            "surface": profile.get("surface"),
            "information_density": profile.get("information_density"),
            "industry_tone": profile.get("industry_tone"),
            "primary_library": primary,
            "alternative_libraries": list(profile.get("alternative_libraries", [])),
            "component_stack": stack,
            "component_priorities": list(profile.get("component_priorities", [])),
            "design_system_priorities": list(profile.get("design_system_priorities", [])),
            "art_direction_candidates": list(profile.get("art_direction_candidates", [])),
            "design_direction_manifest": dict(profile.get("design_direction_manifest", {})),
            "brand_signal_manifest": dict(profile.get("brand_signal_manifest", {})),
            "proof_composition_rules": dict(profile.get("proof_composition_rules", {})),
            "component_craft_requirements": list(
                profile.get("component_craft_requirements", [])
            ),
            "layout_tension_rules": list(profile.get("layout_tension_rules", [])),
            "anti_ai_slop_guardrails": dict(profile.get("anti_ai_slop_guardrails", {})),
            "critique_rubric": list(profile.get("critique_rubric", [])),
            "tweak_categories": list(profile.get("tweak_categories", [])),
            "state_requirements": list(profile.get("state_requirements", [])),
            "quality_checklist": list(profile.get("quality_checklist", [])),
            "banned_patterns": list(profile.get("banned_patterns", [])),
            "knowledge_keywords": list(profile.get("knowledge_keywords", [])),
            "design_references": list(profile.get("design_references", [])),
            "selected_design_reference": profile.get("selected_design_reference"),
            "framework_playbook": profile.get("framework_playbook"),
            "color_palette": palette,
            "typography_preset": typography,
            "icon_system": icon_system,
            "emoji_policy": {
                "allowed_in_ui": False,
                "allowed_as_icon": False,
                "allowed_during_development": False,
                "rule": "绝对不允许 emoji 表情作为图标，也不允许在 UI 开发过程中使用 emoji 充当占位、临时装饰或功能按钮。",
                "approved_icon_libraries": [
                    "Lucide",
                    "Heroicons",
                    "Tabler Icons",
                    "官方组件图标库",
                ],
                "enforcement": "system-wide",
            },
            "ui_library_preference": {
                "preferred": (
                    "shadcn/ui + Radix UI + Tailwind CSS"
                    if self.frontend in {"react", "next", "nextjs", "web"}
                    and self.platform in {"web", "desktop", "saas", "landing"}
                    else primary.get("name")
                ),
                "strict": False,
                "decision_rule": (
                    "React/Web 场景优先偏向 shadcn/ui + Radix + Tailwind；"
                    "但若既有设计系统、平台特性、团队生态或页面类型存在更合适方案，应由宿主选择更合适的组件生态，并把最终选择回写到 UIUX 文档。"
                ),
                "final_selected": primary.get("name"),
            },
            "design_tokens": {
                "css_variables": design_bundle.get("css_variables_preview", ""),
                "tailwind_theme": design_bundle.get("tailwind_preview", ""),
            },
            "screen_recipes": screen_recipes,
            "design_context_protocol": design_context_protocol,
            "tweak_strategy": tweak_strategy,
            "verification_handoff": verification_handoff,
        }
        if design_system is not None:
            payload["generated_design_system"] = {
                "name": getattr(design_system, "name", ""),
                "description": getattr(design_system, "description", ""),
                "colors": getattr(design_system, "colors", {}),
                "typography": getattr(design_system, "typography", {}),
                "spacing": getattr(design_system, "spacing", {}),
                "shadows": getattr(design_system, "shadows", {}),
                "radius": getattr(design_system, "radius", {}),
                "animations": getattr(design_system, "animations", {}),
                "components": getattr(design_system, "components", {}),
            }
            aesthetic = getattr(design_system, "aesthetic", None)
            if aesthetic is not None:
                payload["generated_design_system"]["aesthetic"] = {
                    "name": getattr(aesthetic, "name", ""),
                    "description": getattr(aesthetic, "description", ""),
                    "differentiation": getattr(aesthetic, "differentiation", ""),
                    "typography": {
                        "display": getattr(getattr(aesthetic, "typography", None), "display", ""),
                        "body": getattr(getattr(aesthetic, "typography", None), "body", ""),
                    },
                }
        return payload

    def _build_screen_recipes(self, analysis: dict, profile: dict) -> list[dict]:
        product_type = str(analysis.get("product_type") or "general").lower()
        surface = str(profile.get("surface") or "商业级界面")
        density = str(profile.get("information_density") or "medium")
        trust_modules = list(profile.get("trust_modules", []))
        state_requirements = list(profile.get("state_requirements", []))
        component_priorities = list(profile.get("component_priorities", []))
        direction_manifest = (
            profile.get("design_direction_manifest")
            if isinstance(profile.get("design_direction_manifest"), dict)
            else {}
        )
        anti_guardrails = (
            profile.get("anti_ai_slop_guardrails")
            if isinstance(profile.get("anti_ai_slop_guardrails"), dict)
            else {}
        )
        tweak_categories = (
            profile.get("tweak_categories")
            if isinstance(profile.get("tweak_categories"), list)
            else []
        )
        selected_reference = (
            profile.get("selected_design_reference")
            if isinstance(profile.get("selected_design_reference"), dict)
            else {}
        )
        reference_name = selected_reference.get("name") or "设计参考锚点"
        selected_direction = direction_manifest.get("selected_direction") or "Modern Commercial"
        narrative_mode = direction_manifest.get("narrative_mode") or "先价值、再证明、后功能展开"
        visual_tension = direction_manifest.get("visual_tension") or "通过层级、留白和重点色建立张力"
        density_tempo = direction_manifest.get("density_tempo") or density
        anti_cliches = list(anti_guardrails.get("forbidden_motifs", []))[:3]
        proof_rules = (
            profile.get("proof_composition_rules")
            if isinstance(profile.get("proof_composition_rules"), dict)
            else {}
        )
        layout_tension_rules = (
            profile.get("layout_tension_rules")
            if isinstance(profile.get("layout_tension_rules"), list)
            else []
        )

        def recipe(
            recipe_id: str,
            label: str,
            objective: str,
            section_order: list[str],
            components: list[str],
            trust_slice: list[str],
            states: list[str],
            variation_axes: list[str],
            starter: list[str],
        ) -> dict:
            return {
                "id": recipe_id,
                "label": label,
                "surface": surface,
                "information_density": density,
                "objective": objective,
                "section_order": section_order,
                "component_focus": components,
                "trust_modules": trust_slice,
                "required_states": states,
                "variation_axes": variation_axes,
                "starter_components": starter,
                "design_reference": reference_name,
                "art_direction": selected_direction,
                "narrative_mode": narrative_mode,
                "visual_tension": visual_tension,
                "density_tempo": density_tempo,
                "proof_composition": proof_rules.get("hero_proof_stack", [])[:4],
                "layout_tension_rules": layout_tension_rules[:3],
                "anti_cliche_bans": anti_cliches,
            }

        common_variations = [
            "信息密度（compact / balanced / spacious）",
            "强调方式（editorial headline / product proof / conversion CTA）",
            "品牌质感（neutral / premium / technical accent）",
        ]
        for category in tweak_categories[:2]:
            if not isinstance(category, dict):
                continue
            label = str(category.get("label") or category.get("name") or "").strip()
            if label and label not in common_variations:
                common_variations.append(label)
        common_states = state_requirements[:4] or ["loading", "empty", "error", "success"]
        trust_slice = trust_modules[:4] or ["案例", "安全", "FAQ", "指标"]

        if product_type in {"landing", "saas"}:
            return [
                recipe(
                    "north-star",
                    "North Star Hero",
                    "首屏必须同时讲清价值主张、可信证据与下一步动作，而不是只放大标题。",
                    ["hero", "proof bar", "product visual", "primary CTA"],
                    component_priorities[:4] or ["hero", "cta", "metrics", "feature card"],
                    trust_slice,
                    common_states,
                    common_variations,
                    ["browser-window", "trust-band", "metric-strip"],
                ),
                recipe(
                    "workflow-proof",
                    "Workflow Proof",
                    "用真实流程、模块编排和结果反馈证明产品不是概念图，而是可工作的系统。",
                    ["workflow map", "capability clusters", "before/after", "evidence rail"],
                    component_priorities[1:5]
                    or ["timeline", "panel", "table", "command area"],
                    trust_slice,
                    common_states,
                    ["布局节奏（stacked / split / rail）", "证明方式（截图 / metrics / checklist）"],
                    ["design-canvas", "browser-window"],
                ),
                recipe(
                    "conversion-closure",
                    "Conversion Closure",
                    "结尾区域要完成 FAQ、案例、合规与 CTA 收口，避免只有功能列表没有转化闭环。",
                    ["case study", "faq", "pricing or offer", "final CTA"],
                    component_priorities[:3] or ["testimonial", "faq", "cta"],
                    trust_modules[:6] or trust_slice,
                    common_states[:2],
                    ["转化风格（soft / assertive）", "信任权重（metrics / testimonial / compliance）"],
                    ["trust-band", "faq-stack"],
                ),
            ]

        if product_type in {"dashboard", "content"}:
            return [
                recipe(
                    "workspace-overview",
                    "Workspace Overview",
                    "主屏需要先建立导航骨架、关键状态和信息优先级，避免退化成内容堆叠板。",
                    ["navigation shell", "summary row", "primary work area", "secondary rail"],
                    component_priorities[:5]
                    or ["sidebar", "topbar", "table", "chart", "detail panel"],
                    trust_slice,
                    common_states,
                    common_variations,
                    ["app-shell", "metric-strip"],
                ),
                recipe(
                    "detail-flow",
                    "Detail & Action Flow",
                    "详情区要同时支持阅读、编辑和反馈，确保关键任务可以在一个清晰路径里完成。",
                    ["detail header", "tabs or split", "activity trail", "sticky actions"],
                    component_priorities[1:6]
                    or ["detail header", "tabs", "form", "history", "action footer"],
                    trust_slice[:3],
                    common_states,
                    ["详情布局（tabs / split / inspector）", "操作模式（inline / modal / drawer）"],
                    ["app-shell", "detail-rail"],
                ),
                recipe(
                    "operational-proof",
                    "Operational Proof",
                    "用审计、状态矩阵和恢复能力证明系统可靠，而不是只展示好看的卡片。",
                    ["audit summary", "status matrix", "evidence cards", "recovery cues"],
                    component_priorities[:4] or ["status card", "timeline", "badge", "log rail"],
                    trust_modules[:5] or trust_slice,
                    common_states,
                    ["证据强度（light / strong）", "审计密度（compact / expanded）"],
                    ["design-canvas", "audit-rail"],
                ),
            ]

        return [
            recipe(
                "brand-frame",
                "Brand Frame",
                "先建立品牌语气、字体层级与核心页面骨架，避免默认模板化壳层。",
                ["hero", "capability blocks", "proof", "cta"],
                component_priorities[:4] or ["hero", "feature card", "proof", "cta"],
                trust_slice,
                common_states,
                common_variations,
                ["design-canvas", "browser-window"],
            ),
            recipe(
                "core-journey",
                "Core Journey",
                "把最关键的用户旅程拆成 3-4 个高保真步骤，而不是泛化展示一堆功能点。",
                ["entry", "main action", "feedback", "completion"],
                component_priorities[:4] or ["form", "cta", "state", "summary"],
                trust_slice[:3],
                common_states,
                ["流程深度（fast lane / guided）", "反馈强度（minimal / explicit）"],
                ["browser-window", "design-canvas"],
            ),
        ]

    def _build_design_context_protocol(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        frontend = str(analysis.get("frontend") or self.frontend or "web")
        design_references = profile.get("design_references", [])
        selected_reference = (
            profile.get("selected_design_reference")
            if isinstance(profile.get("selected_design_reference"), dict)
            else {}
        )
        reference_signal = (
            selected_reference.get("name")
            or (design_references[0].get("name") if design_references else "设计参考锚点")
        )
        starter_components = []
        for recipe in screen_recipes:
            for item in recipe.get("starter_components", []):
                if item not in starter_components:
                    starter_components.append(item)

        return {
            "goal": "先吸收真实品牌、代码和组件上下文，再进入页面实现；禁止只凭记忆或截图猜 UI。",
            "required_sources": [
                "output/*-uiux.md",
                "output/*-ui-contract.json",
                "现有代码中的主题 token / 布局骨架 / 组件实现",
                "必要时补充截图、Figma 或真实产品链接",
            ],
            "preferred_import_order": [
                "主题 token / variables / theme 文件",
                "关键页面或组件源码",
                "全局样式与 layout scaffold",
                "补充截图与品牌物料",
            ],
            "github_import_targets": [
                "theme.ts / colors.ts / tokens.css / variables.scss",
                "layout / app shell / navigation components",
                "用户明确点名的页面和模块",
            ],
            "fidelity_rules": [
                f"优先复用 {reference_signal} 的可吸收信号，但必须转化为原创组合，而不是 1:1 复刻。",
                f"实现时必须围绕已选视觉哲学「{profile.get('design_direction_manifest', {}).get('selected_direction', '主方向')}」统一 hero、证据与内容节奏，禁止混搭多个热门风格。",
                "实现时先读真实代码与设计 token，再写页面；禁止只看文件名或只凭经验回忆。",
                "所有页面必须围绕 screen recipes 组织 section order、trust modules 与 state coverage。",
            ],
            "starter_components": starter_components[:5],
            "single_source_rule": "统一以一个主原型 / 主页面承载 Tweaks 和变体，减少多份分叉页面。",
            "frontend_target": frontend,
        }

    def _build_tweak_strategy(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        variation_axes: list[str] = []
        for recipe in screen_recipes:
            for axis in recipe.get("variation_axes", []):
                if axis not in variation_axes:
                    variation_axes.append(axis)
        tweak_categories = (
            profile.get("tweak_categories")
            if isinstance(profile.get("tweak_categories"), list)
            else []
        )
        return {
            "mode": "single-source prototype with tweakable variations",
            "panel_title": "Tweaks",
            "preferred_placement": "floating panel or inline handles, hidden in final view",
            "default_controls": variation_axes[:6]
            or [
                "信息密度",
                "标题张力",
                "品牌强调色",
                "CTA 风格",
            ],
            "persistence_rule": "变体默认值应可序列化并持久化，避免每次刷新丢失。",
            "selection_rule": "关键页面至少保留主方案 + 备选方案，不建议把所有变化拆成多份静态文件。",
            "screen_targets": [item.get("label", "") for item in screen_recipes[:3]],
            "categories": tweak_categories[:3],
        }

    def _build_verification_handoff(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        frontend = str(analysis.get("frontend") or self.frontend or "web")
        critique_rubric = (
            profile.get("critique_rubric")
            if isinstance(profile.get("critique_rubric"), list)
            else []
        )
        return {
            "verification_order": [
                "preview loads cleanly",
                "design tokens are wired",
                "screen recipes are represented in the preview",
                "375 / 768 / 1440 breakpoint review",
                "ui review + runtime evidence refresh",
            ],
            "required_artifacts": [
                "output/frontend/index.html",
                "output/frontend/styles.css",
                "output/frontend/design-tokens.css",
                "output/*-ui-contract-alignment.json",
                "output/*-frontend-runtime.json",
                "output/*-ui-review.md",
            ],
            "acceptance_checks": [
                "无 emoji 图标与聊天式壳层复刻",
                "关键页面覆盖 trust modules 与 state requirements",
                "主页面结构与 screen recipes 一致",
                "主题入口、导航骨架和组件生态接线清晰",
                "设计哲学、视觉层级、细节工艺、功能性与原创度五维评分均达标",
            ],
            "implementation_handoff": [
                f"frontend={frontend}",
                "冻结后的 ui-contract 作为实现真源",
                "UI review / runtime / quality gate 作为收尾证据链",
            ],
            "screen_targets": [item.get("id", "") for item in screen_recipes],
            "critique_targets": [
                str(item.get("label") or item.get("dimension") or "").strip()
                for item in critique_rubric[:5]
                if isinstance(item, dict)
            ],
        }

    def _get_state_management(self) -> str:
        """获取状态管理方案"""
        mapping = {
            "react": "Redux Toolkit / Zustand",
            "vue": "Pinia",
            "angular": "NgRx",
            "svelte": "Svelte Stores",
        }
        return mapping.get(self.frontend, "Context API")

    def _get_ui_library(self) -> str:
        """获取 UI 库"""
        return self._get_ui_intelligence()["primary_library"]["name"]

    def _get_build_tool(self) -> str:
        """获取构建工具"""
        mapping = {
            "react": "Vite",
            "vue": "Vite",
            "angular": "Angular CLI",
            "svelte": "Vite",
        }
        return mapping.get(self.frontend, "Webpack")

    def _get_backend_framework(self) -> str:
        """获取后端框架"""
        mapping = {
            "node": "Express / Fastify / NestJS",
            "python": "FastAPI / Django",
            "go": "Gin / Echo",
            "java": "Spring Boot",
            "rust": "Actix Web / Axum",
            "php": "Laravel / Symfony",
            "ruby": "Rails / Sinatra",
            "csharp": "ASP.NET Core",
            "kotlin": "Ktor / Spring Boot",
            "swift": "Vapor",
            "elixir": "Phoenix",
            "scala": "Play / Akka HTTP",
            "dart": "Shelf / Dart Frog",
        }
        return mapping.get(self.backend, "Express")

    def _get_database(self) -> str:
        """获取数据库"""
        return "PostgreSQL 14+"

    def _get_orm(self) -> str:
        """获取 ORM"""
        mapping = {
            "node": "Prisma / TypeORM",
            "python": "SQLAlchemy / Django ORM",
            "go": "GORM",
            "java": "Hibernate / JPA",
            "rust": "SeaORM / Diesel",
            "php": "Eloquent / Doctrine",
            "ruby": "Active Record",
            "csharp": "Entity Framework Core",
            "kotlin": "Exposed / Spring Data JPA",
            "swift": "Fluent",
            "elixir": "Ecto",
            "scala": "Slick / Doobie",
            "dart": "Drift / Prisma Client Dart",
        }
        return mapping.get(self.backend, "Prisma")

    def _get_file_storage(self) -> str:
        """获取文件存储"""
        return "AWS S3 / 阿里云 OSS"

    def _generate_ai_ml_stack(self) -> str:
        """生成 AI/ML 技术栈部分"""
        keywords = self._extract_tech_keywords()

        # 检查是否有任何 AI/ML 相关技术
        has_ai_content = any(
            [
                keywords["ai_frameworks"],
                keywords["agent_tools"],
                keywords["ml_libraries"],
                keywords["vector_stores"],
                keywords["orchestration"],
                keywords["other_keywords"],
            ]
        )

        if not has_ai_content:
            return ""  # 如果没有 AI/ML 内容，返回空字符串

        # 构建 AI/ML 技术栈部分
        lines = ["### 2.2.1 AI/ML 技术栈", "", "| 层级 | 技术选型 | 说明 |", "|:---|:---|:---|"]

        # AI 框架
        if keywords["ai_frameworks"]:
            for framework in keywords["ai_frameworks"]:
                lines.append(f"| **AI 框架** | {framework} | Agent 编排与开发 |")

        # Agent 工具
        if keywords["agent_tools"]:
            for tool in keywords["agent_tools"]:
                lines.append(f"| **Agent 工具** | {tool} | Agent 构建与管理 |")

        # ML 库
        if keywords["ml_libraries"]:
            for lib in keywords["ml_libraries"]:
                lines.append(f"| **ML 库** | {lib} | 机器学习模型 |")

        # 向量数据库
        if keywords["vector_stores"]:
            for store in keywords["vector_stores"]:
                lines.append(f"| **向量数据库** | {store} | 向量存储与检索 |")

        # 编排工具
        if keywords["orchestration"]:
            for tool in keywords["orchestration"]:
                lines.append(f"| **编排工具** | {tool} | 工作流编排 |")

        # 其他关键词
        if keywords["other_keywords"]:
            for keyword in keywords["other_keywords"]:
                lines.append(f"| **核心能力** | {keyword} | 关键技术特性 |")

        lines.append("")
        return "\n".join(lines)

    def _generate_vision(self) -> str:
        """生成产品愿景"""
        return f"""
打造一个{self.description}的{self.platform.upper()}应用，
为用户提供简单、高效、愉悦的使用体验。

我们相信：
- **用户至上**: 一切以用户价值为导向
- **简单至上**: 复杂的事情简单化
- **体验至上**: 每个细节都精益求精
"""

    def _domain_category(self) -> str:
        """根据 self.domain 和 self.description 推断领域分类"""
        combined = f"{self.domain} {self.description}".lower()
        if any(
            w in combined
            for w in [
                "教育",
                "培训",
                "education",
                "learning",
                "课程",
                "学习",
                "school",
                "university",
                "学校",
            ]
        ):
            return "education"
        if any(
            w in combined
            for w in [
                "医疗",
                "健康",
                "health",
                "medical",
                "hospital",
                "patient",
                "诊所",
                "clinic",
                "护理",
            ]
        ):
            return "healthcare"
        if any(
            w in combined
            for w in [
                "电商",
                "商城",
                "shop",
                "store",
                "mall",
                "购物",
                "ecommerce",
                "零售",
                "retail",
            ]
        ):
            return "ecommerce"
        if any(
            w in combined
            for w in [
                "金融",
                "支付",
                "fintech",
                "banking",
                "投资",
                "交易",
                "股票",
                "基金",
                "理财",
                "finance",
            ]
        ):
            return "fintech"
        if any(
            w in combined
            for w in ["内容", "社区", "content", "community", "blog", "cms", "媒体", "资讯", "新闻"]
        ):
            return "content"
        if any(
            w in combined for w in ["saas", "平台", "管理系统", "erp", "crm", "oa", "办公", "协作"]
        ):
            return "saas"
        if any(
            w in combined for w in ["求职", "招聘", "job", "resume", "career", "简历", "hr", "人才"]
        ):
            return "recruitment"
        if any(
            w in combined for w in ["物流", "配送", "logistics", "delivery", "仓储", "supply chain"]
        ):
            return "logistics"
        if any(w in combined for w in ["餐饮", "外卖", "food", "restaurant", "点餐", "菜单"]):
            return "food"
        if any(
            w in combined for w in ["旅游", "酒店", "travel", "hotel", "booking", "景点", "民宿"]
        ):
            return "travel"
        return "general"

    def _extract_description_nouns(self) -> list[str]:
        """从 self.description 中提取关键名词用于 general 场景下的内容生成"""
        desc = self.description
        # 中文关键词提取：按常见分隔符拆分后取有意义的词
        stop_words = {
            "的",
            "了",
            "和",
            "与",
            "或",
            "在",
            "是",
            "有",
            "一个",
            "这个",
            "那个",
            "可以",
            "需要",
            "支持",
            "实现",
            "使用",
            "通过",
            "进行",
            "提供",
            "包括",
            "a",
            "an",
            "the",
            "is",
            "are",
            "for",
            "to",
            "and",
            "or",
            "with",
            "that",
            "this",
        }
        tokens: list[str] = []
        # 按空格和标点拆分
        import re

        parts = re.split(r"[\s,，。、；;：:！!？?\-/\\|（）()\[\]{}]+", desc)
        for part in parts:
            part = part.strip()
            if len(part) >= 2 and part.lower() not in stop_words:
                tokens.append(part)
        return tokens[:10]

    def _generate_target_users(self) -> str:
        """生成目标用户 - 根据领域动态生成"""
        category = self._domain_category()
        segments = {
            "education": [
                (
                    "学生用户",
                    "65%",
                    "18-30 岁",
                    "在校学生、考证学员、终身学习者",
                    "追求高效学习、需要个性化学习路径、注重学习效果反馈",
                ),
                (
                    "教师/讲师",
                    "25%",
                    "25-55 岁",
                    "在职教师、培训讲师、课程创作者",
                    "需要教学管理工具、关注学生学习数据、重视内容创作效率",
                ),
                (
                    "教务管理员",
                    "10%",
                    "30-50 岁",
                    "学校教务、培训机构运营人员",
                    "关注整体运营数据、需要排课排班功能、重视报表和统计",
                ),
            ],
            "healthcare": [
                (
                    "患者/就诊者",
                    "60%",
                    "20-70 岁",
                    "慢性病患者、体检用户、门诊就诊者",
                    "需要便捷预约挂号、关注就诊记录查询、重视隐私数据安全",
                ),
                (
                    "医护人员",
                    "30%",
                    "25-55 岁",
                    "医生、护士、药剂师",
                    "需要高效查看病历、关注诊断辅助工具、重视处方管理规范",
                ),
                (
                    "医院管理者",
                    "10%",
                    "35-55 岁",
                    "科室主任、院长、运营人员",
                    "关注科室运营指标、需要排班管理、重视医疗质量监控",
                ),
            ],
            "ecommerce": [
                (
                    "消费者/买家",
                    "70%",
                    "18-45 岁",
                    "线上购物用户、比价用户、品牌忠实用户",
                    "关注商品质量与价格、需要便捷支付与物流追踪、重视售后服务",
                ),
                (
                    "商家/卖家",
                    "20%",
                    "25-50 岁",
                    "个体商户、品牌运营、供应商",
                    "需要商品管理工具、关注订单与库存、重视销售数据分析",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "平台客服、运营专员、审核人员",
                    "关注平台整体GMV、需要纠纷处理工具、重视用户投诉管理",
                ),
            ],
            "fintech": [
                (
                    "个人投资者",
                    "55%",
                    "25-55 岁",
                    "散户投资者、理财用户、储蓄用户",
                    "关注资产安全与收益、需要实时行情与交易、重视风险提示",
                ),
                (
                    "金融顾问/分析师",
                    "30%",
                    "28-50 岁",
                    "理财规划师、基金经理、风控专员",
                    "需要专业分析工具、关注客户资产配置、重视合规审查",
                ),
                (
                    "合规与风控人员",
                    "15%",
                    "30-50 岁",
                    "合规主管、审计人员、风控专员",
                    "关注交易合规性、需要反洗钱监控、重视监管报告生成",
                ),
            ],
            "recruitment": [
                (
                    "求职者",
                    "60%",
                    "20-40 岁",
                    "应届毕业生、在职跳槽者、自由职业者",
                    "需要简历优化工具、关注职位匹配度、重视面试准备与反馈",
                ),
                (
                    "HR/招聘方",
                    "30%",
                    "25-45 岁",
                    "企业HR、猎头、招聘专员",
                    "需要高效筛选简历、关注人才库管理、重视招聘流程自动化",
                ),
                (
                    "企业管理者",
                    "10%",
                    "30-55 岁",
                    "部门主管、CEO、CTO",
                    "关注团队人才结构、需要审批招聘需求、重视人力成本控制",
                ),
            ],
            "content": [
                (
                    "内容消费者",
                    "65%",
                    "18-45 岁",
                    "阅读用户、视频观众、社区浏览者",
                    "追求高质量内容、需要个性化推荐、重视互动与社交",
                ),
                (
                    "内容创作者",
                    "25%",
                    "20-40 岁",
                    "作者、博主、KOL、自媒体运营",
                    "需要创作与发布工具、关注粉丝互动与数据、重视内容变现",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "内容审核、社区运营、数据分析师",
                    "关注内容质量管控、需要审核与推荐策略、重视社区氛围维护",
                ),
            ],
            "saas": [
                (
                    "终端用户",
                    "60%",
                    "22-45 岁",
                    "企业员工、团队成员、项目参与者",
                    "需要高效完成日常工作、关注功能易用性、重视协作体验",
                ),
                (
                    "团队管理者",
                    "25%",
                    "28-50 岁",
                    "项目经理、部门主管、团队负责人",
                    "需要团队管理与权限控制、关注工作进度与报表、重视数据安全",
                ),
                (
                    "系统管理员",
                    "15%",
                    "25-45 岁",
                    "IT管理员、运维人员、安全管理员",
                    "关注系统稳定性与安全、需要配置与集成管理、重视日志与审计",
                ),
            ],
            "logistics": [
                (
                    "发货方/商家",
                    "45%",
                    "25-50 岁",
                    "电商商家、工厂、贸易公司",
                    "需要高效发货管理、关注物流成本与时效、重视包裹追踪",
                ),
                (
                    "配送人员",
                    "35%",
                    "20-45 岁",
                    "快递员、司机、仓库管理员",
                    "需要路线规划与任务分配、关注签收确认、重视工作效率",
                ),
                (
                    "收货方/消费者",
                    "20%",
                    "18-60 岁",
                    "线上购物用户、企业收件人",
                    "关注物流状态查询、需要预约送达、重视签收便捷性",
                ),
            ],
            "food": [
                (
                    "消费者/食客",
                    "65%",
                    "18-45 岁",
                    "上班族、学生、家庭用户",
                    "关注菜品质量与价格、需要便捷点餐与配送、重视用餐体验",
                ),
                (
                    "商家/餐厅",
                    "25%",
                    "25-55 岁",
                    "餐饮老板、厨师、门店管理",
                    "需要菜单与订单管理、关注营业数据、重视库存与供应链",
                ),
                (
                    "配送骑手",
                    "10%",
                    "20-40 岁",
                    "全职骑手、兼职配送员",
                    "需要订单接单与导航、关注配送时效、重视收入统计",
                ),
            ],
            "travel": [
                (
                    "旅行者/游客",
                    "65%",
                    "20-55 岁",
                    "自由行用户、商务出差、家庭游客",
                    "需要便捷预订与行程规划、关注价格与评价、重视出行体验",
                ),
                (
                    "供应商/商家",
                    "25%",
                    "30-55 岁",
                    "酒店经营者、景区管理、旅行社",
                    "需要房态与库存管理、关注订单与营收、重视用户评价",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "运营专员、客服、数据分析",
                    "关注平台交易数据、需要供应商管理、重视用户投诉处理",
                ),
            ],
        }

        if category in segments:
            user_list = segments[category]
        else:
            # general: 从描述中推断
            nouns = self._extract_description_nouns()
            desc_hint = f"（基于 {self.name} 的核心功能: {self.description[:80]}）"
            user_list = [
                (
                    "核心用户",
                    "65%",
                    "22-40 岁",
                    f"{self.name} 的主要使用者",
                    f"直接使用 {nouns[0] if nouns else '核心功能'}、追求效率与体验、{desc_hint}",
                ),
                (
                    "管理用户",
                    "25%",
                    "28-50 岁",
                    "后台管理者、运营人员、数据分析人员",
                    f"负责 {self.name} 的内容管理与运营、关注数据指标、需要管理工具",
                ),
                (
                    "外部协作者",
                    "10%",
                    "25-45 岁",
                    "合作方、第三方集成用户、API 调用方",
                    f"通过 API 或集成方式与 {self.name} 交互、关注接口稳定性与文档",
                ),
            ]

        lines = ["\n**主要用户群体**:\n"]
        for i, (name, pct, age, role, traits) in enumerate(user_list, 1):
            lines.append(
                f"""{i}. **{name}** ({pct})
   - 年龄: {age}
   - 角色: {role}
   - 特征: {traits}
"""
            )
        return "\n".join(lines)

    def _generate_value_proposition(self) -> str:
        """生成价值主张 - 根据领域和产品描述动态生成"""
        category = self._domain_category()
        propositions = {
            "education": f"""
**核心价值**:

1. **学习效率提升**: 通过个性化学习路径和智能推荐，帮助学生将知识掌握效率提升 40% 以上，告别盲目刷题和低效重复
2. **教学管理数字化**: 为教师提供一体化教学管理工具，从备课、授课到批改作业、跟踪学情，减少 60% 行政事务时间
3. **数据驱动决策**: 通过学习行为数据分析，帮助管理者精准识别教学短板、优化课程设置，提升整体教学质量
4. **随时随地学习**: 基于 {self.platform.upper()} 平台，支持碎片化学习场景，学习进度跨设备同步
""",
            "healthcare": """
**核心价值**:

1. **就医流程优化**: 将挂号-就诊-取药全流程线上化，患者平均等待时间减少 70%，告别排队难题
2. **医疗数据互通**: 打通电子病历、检查报告、处方信息，医生可在 30 秒内获取患者完整就诊历史
3. **精准诊疗辅助**: 基于历史数据和临床知识库提供诊断建议，降低误诊风险，提升诊疗质量
4. **合规安全保障**: 严格遵循医疗数据安全标准（HIPAA / 《个人信息保护法》），确保患者隐私数据全链路加密
""",
            "ecommerce": """
**核心价值**:

1. **转化率提升**: 通过个性化推荐和智能搜索，将商品发现到下单的转化率提升 35%，减少用户决策成本
2. **运营效率翻倍**: 为商家提供一站式商品管理、订单处理、库存预警工具，日均处理效率提升 50%
3. **全链路体验**: 从浏览、下单、支付到物流追踪、售后服务，每个环节都经过精心设计，NPS 目标 60+
4. **数据赋能增长**: 实时销售数据分析、用户行为洞察、智能营销建议，帮助商家科学决策
""",
            "fintech": """
**核心价值**:

1. **交易安全可靠**: 多重安全认证与实时风控系统，资金操作全链路加密，年欺诈率控制在 0.01% 以下
2. **投资决策辅助**: 实时行情数据、智能投顾建议、风险评估报告，帮助用户做出更理性的投资决策
3. **合规自动化**: 内置 KYC/AML 流程自动化、监管报告自动生成，合规工作量减少 80%
4. **资产全景视图**: 跨账户、跨资产类别的统一资产面板，一目了然掌握财务状况
""",
            "recruitment": """
**核心价值**:

1. **匹配效率提升**: 智能简历解析与职位匹配算法，将人岗匹配准确率提升至 85%，招聘周期缩短 40%
2. **求职体验优化**: 一键简历生成、智能投递建议、面试准备辅导，让求职者少走弯路
3. **招聘流程自动化**: 从职位发布、简历筛选到面试安排、录用通知，全流程线上化，HR 工作效率提升 60%
4. **人才数据洞察**: 行业薪资趋势、人才流动分析、竞争对手招聘动态，帮助企业制定更有竞争力的人才策略
""",
            "content": """
**核心价值**:

1. **内容消费效率**: 智能推荐算法匹配用户兴趣，内容发现效率提升 50%，减少信息噪音
2. **创作者赋能**: 一站式创作工具 + 数据分析面板，帮助创作者专注内容本身，粉丝增长效率提升 30%
3. **社区活力**: 优质互动机制设计，用户日均停留时长提升 40%，核心用户 7 日留存率目标 55%+
4. **内容变现通路**: 打通付费订阅、打赏、广告分成等多元变现渠道，让优质内容获得合理回报
""",
            "saas": """
**核心价值**:

1. **团队协作效率**: 统一工作平台消除信息孤岛，跨部门协作效率提升 45%，减少重复沟通
2. **流程自动化**: 将重复性工作流自动化，团队成员可将 60% 以上时间投入高价值工作
3. **数据驱动管理**: 实时项目进度、团队效能、资源利用率看板，管理者决策效率提升 50%
4. **灵活扩展**: 模块化架构支持按需启用功能，从小团队到大企业平滑扩展，无需更换系统
""",
        }

        if category in propositions:
            return propositions[category]

        # general: 基于描述生成
        nouns = self._extract_description_nouns()
        core_noun = nouns[0] if nouns else "核心功能"
        return f"""
**核心价值**:

1. **核心体验升级**: 围绕「{self.description[:40]}」的核心场景，提供比传统方案更高效、更直观的解决路径，关键操作效率提升 50%+
2. **一站式整合**: 将 {core_noun} 相关的分散工具和流程整合到统一平台，消除工具切换和数据孤岛
3. **智能化辅助**: 基于用户行为数据提供个性化建议和自动化支持，降低使用门槛和学习成本
4. **持续迭代驱动**: 内置数据分析和用户反馈闭环，确保产品持续贴合用户需求演进
"""

    def _generate_core_features(self) -> str:
        """生成核心功能"""
        # 从描述中提取业务领域关键词
        description_lower = self.description.lower()
        keywords = self._extract_tech_keywords()

        # 基础功能（所有应用都有）
        base_features = """
1. **用户认证与授权**
   - 注册/登录（邮箱/手机号）
   - 密码重置
   - JWT Token 认证
   - 第三方登录（可选）

2. **用户中心**
   - 个人资料管理
   - 账户安全设置
   - 偏好配置
"""

        # 根据业务领域生成核心功能
        business_features = ""

        # 求职招聘领域
        if any(
            word in description_lower
            for word in ["求职", "招聘", "job", "resume", "career", "简历", "职位"]
        ):
            business_features = """
3. **简历管理**
   - 在线简历创建与编辑
   - 简历模板选择
   - 简历导入（上传 PDF/Word）
   - 简历预览与导出
   - 简历智能评分与优化建议

4. **职位搜索与推荐**
   - 职位搜索（关键词/地点/薪资）
   - 智能职位推荐
   - 职位收藏与对比
   - 职位订阅通知

5. **求职助手"""
            # 如果有 AI/Agent 相关技术，添加智能功能
            if (
                keywords["ai_frameworks"]
                or keywords["agent_tools"]
                or "Multi-Agent System" in keywords["other_keywords"]
            ):
                business_features += """
   - 多 Agent 智能求职助手：
     * **简历匹配 Agent**: JD 与简历匹配度分析，识别技能差距，提供优化建议
     * **简历优化 Agent**: 自动优化简历内容，提高匹配度
     * **职位推荐 Agent**: 基于用户画像智能推荐职位
     * **面试准备 Agent**: 模拟面试，提供问题预测和回答建议
     * **薪资谈判 Agent**: 分析市场薪资，提供谈判策略
     * **职业规划 Agent**: 基于行业趋势提供职业发展建议
   - 实时对话式求职咨询
   - 智能简历投递建议"""
            else:
                business_features += """
   - 求职进度跟踪
   - 面试提醒与日程管理
   - 求职数据分析"""

        # 电商领域
        elif any(
            word in description_lower for word in ["电商", "商城", "shop", "store", "mall", "购物"]
        ):
            business_features = """
3. **商品管理**
   - 商品浏览与搜索
   - 商品分类与筛选
   - 商品详情与评价

4. **购物车与订单**
   - 购物车管理
   - 订单创建与支付
   - 物流跟踪

5. **用户中心**
   - 收藏夹
   - 浏览历史
   - 优惠券管理"""

        # 内容/社区领域
        elif any(
            word in description_lower
            for word in ["内容", "社区", "content", "community", "blog", "forum", "社交"]
        ):
            business_features = """
3. **内容管理**
   - 内容发布与编辑
   - 富文本支持
   - 图片/视频上传

4. **社交互动**
   - 点赞/评论/分享
   - 关注作者
   - 消息通知"""

        # 教育领域
        elif any(
            word in description_lower
            for word in ["教育", "培训", "education", "learning", "课程", "学习"]
        ):
            business_features = """
3. **课程管理**
   - 课程浏览与购买
   - 课程进度跟踪
   - 学习笔记

4. **学习互动**
   - 问答讨论
   - 作业提交
   - 在线测试"""

        # 通用默认
        else:
            business_features = f"""
3. **核心业务功能**
   - {self.description}
   - 数据管理与展示
   - 搜索与过滤
   - 数据导入/导出"""

        return base_features + business_features

    def _generate_extended_features(self) -> str:
        """生成扩展功能 - 根据领域生成 Phase 2 特性"""
        category = self._domain_category()
        features = {
            "education": """
1. **智能学习引擎**
   - AI 驱动的个性化学习路径推荐
   - 知识图谱可视化与薄弱点定位
   - 自适应练习题难度调节
   - 学习行为分析与效率报告

2. **互动教学升级**
   - 实时在线直播课堂
   - 互动白板与屏幕共享
   - 分组讨论与小组作业
   - 同伴互评与学习社区

3. **考试与认证体系**
   - 在线考试系统（防作弊机制）
   - 自动阅卷与成绩统计
   - 电子证书生成与验证
   - 学分管理与成绩单导出

4. **教务运营工具**
   - 智能排课与教室资源管理
   - 教师绩效评估看板
   - 家校沟通与通知系统
   - 财务对账与退费管理

5. **移动学习扩展**
   - 离线课程下载与学习
   - 碎片化学习推送（每日一练）
   - 学习打卡与激励体系
""",
            "healthcare": """
1. **远程医疗**
   - 在线问诊与视频会诊
   - 远程病情监测（可穿戴设备接入）
   - 多学科会诊协作平台
   - AI 辅助预诊与分诊

2. **智能健康管理**
   - 个性化健康档案与风险评估
   - 慢性病管理方案与用药提醒
   - 健康数据趋势分析与预警
   - 运动与饮食建议

3. **医院运营优化**
   - 床位管理与周转率优化
   - 医疗耗材与药品库存预警
   - 医保结算与费用清单
   - 满意度调查与改进追踪

4. **数据与合规**
   - 医疗数据脱敏与授权访问
   - 电子病历互联互通
   - 药品不良反应上报
   - 医疗质量指标自动采集

5. **患者服务扩展**
   - 复诊预约与随访管理
   - 检查报告在线查看与解读
   - 院内导航与排队叫号
""",
            "ecommerce": """
1. **智能营销系统**
   - 用户画像与精准营销
   - 优惠券与满减活动引擎
   - 限时秒杀与拼团功能
   - 会员等级与积分体系

2. **供应链管理**
   - 多仓库库存同步
   - 智能补货预测
   - 供应商管理与采购协同
   - 物流渠道对比与自动分单

3. **商家运营工具**
   - 店铺装修与模板编辑器
   - 多渠道（直播/社交/搜索）流量分析
   - 竞品价格监控
   - 售后工单与退换货流程

4. **社交电商**
   - 商品分享返利机制
   - 用户评价与晒单社区
   - KOL/KOC 合作管理
   - 直播带货与实时互动

5. **全球化扩展**
   - 多语言与多币种支持
   - 跨境物流与关税计算
   - 本地化支付方式接入
""",
            "fintech": """
1. **智能投顾**
   - AI 资产配置建议
   - 投资组合回测与模拟
   - 市场情绪分析与预警
   - 定投策略与自动调仓

2. **高级风控系统**
   - 实时交易异常检测
   - 反洗钱（AML）自动化审查
   - 信用评分模型
   - 欺诈行为模式识别

3. **监管合规工具**
   - 监管报告自动生成
   - KYC 文档自动化处理
   - 合规规则引擎与变更追踪
   - 审计轨迹与证据链

4. **数据分析平台**
   - 多维度财务报表
   - 实时资金流向监控
   - 客户生命周期价值分析
   - 产品收益归因分析

5. **开放银行接口**
   - 第三方账户聚合
   - 支付网关集成
   - Open API 开发者平台
""",
            "recruitment": """
1. **AI 智能匹配**
   - 简历智能解析与结构化
   - JD-简历双向匹配度评分
   - 人才推荐与被动候选人发现
   - 技能差距分析与培训建议

2. **面试流程管理**
   - 视频面试与录制回放
   - 面试评分卡与评委协同
   - 面试日程智能排期
   - 面试题库与能力模型

3. **人才运营**
   - 人才库管理与标签体系
   - 候选人关系维护（CRM）
   - 招聘渠道效果分析
   - Offer 管理与电子签约

4. **数据洞察**
   - 招聘漏斗分析
   - 行业薪资对标报告
   - 人才市场趋势洞察
   - 团队人力结构分析
""",
        }

        if category in features:
            return features[category]

        # general / other categories
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心业务"
        return f"""
1. **高级 {core} 功能**
   - {core} 数据批量导入/导出
   - 高级搜索与多维筛选
   - 自定义工作流与审批流程
   - 模板管理与快速创建

2. **协作与权限**
   - 多角色权限精细控制
   - 团队协作空间与任务分配
   - 操作审计日志与变更历史
   - 通知中心与消息订阅

3. **数据分析与报表**
   - 自定义数据看板
   - 多维度统计图表
   - 定时报告生成与邮件推送
   - 数据导出（Excel/PDF/CSV）

4. **智能化扩展**
   - 基于用户行为的智能推荐
   - 异常数据自动检测与预警
   - 自然语言搜索与查询
   - 自动化规则引擎

5. **集成与开放**
   - 第三方应用集成（钉钉/企业微信/飞书）
   - Open API 与 Webhook
   - 数据同步与 ETL 管道
"""

    def _generate_user_stories(self) -> str:
        """生成用户故事 - 根据领域生成 8-12 条具体故事"""
        category = self._domain_category()
        stories_map = {
            "education": [
                ("学生", "通过手机号或邮箱快速注册", "立即开始学习", "P0"),
                ("学生", "浏览课程目录并按分类/难度筛选", "找到适合自己水平的课程", "P0"),
                ("学生", "观看课程视频并做笔记", "高效掌握知识点", "P0"),
                ("学生", "完成课后测验并查看解析", "检验学习效果", "P0"),
                ("学生", "查看我的学习进度和统计", "了解学习情况并调整计划", "P1"),
                ("教师", "创建和发布新课程", "分享教学内容给学生", "P0"),
                ("教师", "查看学生的学习数据和成绩", "针对性地调整教学策略", "P1"),
                ("教师", "布置作业和批改学生提交", "评估学生掌握程度", "P1"),
                ("管理员", "管理用户账号和角色权限", "确保平台安全运营", "P1"),
                ("管理员", "查看平台运营数据报表", "做出运营决策", "P2"),
                ("学生", "获得课程完成证书", "证明自己的学习成果", "P2"),
                ("学生", "参与课程讨论区互动", "与同学和老师交流问题", "P2"),
            ],
            "healthcare": [
                ("患者", "在线预约挂号并选择医生", "减少到院等待时间", "P0"),
                ("患者", "查看个人就诊记录和检查报告", "了解自己的健康状况", "P0"),
                ("患者", "在线缴费和查看费用明细", "便捷完成支付流程", "P0"),
                ("医生", "查看今日接诊列表和患者病历", "高效了解患者情况", "P0"),
                ("医生", "开具电子处方并发送给药房", "规范化处方流程", "P0"),
                ("医生", "记录诊断结果和医嘱", "完善患者医疗档案", "P1"),
                ("护士", "查看护理任务和用药提醒", "按时完成护理工作", "P1"),
                ("护士", "记录患者生命体征数据", "持续监测病情变化", "P1"),
                ("管理员", "管理科室排班和医生出诊表", "合理分配医疗资源", "P1"),
                ("患者", "收到复诊提醒和用药通知", "按时就医和服药", "P2"),
                ("管理员", "查看医院运营数据和科室绩效", "优化医院管理决策", "P2"),
                ("患者", "在线咨询医生获取初步建议", "解决轻症和日常健康疑问", "P2"),
            ],
            "ecommerce": [
                ("买家", "通过关键词/分类搜索商品", "快速找到想要的商品", "P0"),
                ("买家", "查看商品详情、评价和规格", "做出购买决策", "P0"),
                ("买家", "将商品加入购物车并结算", "完成购买流程", "P0"),
                ("买家", "选择支付方式完成在线支付", "安全便捷地付款", "P0"),
                ("买家", "查看订单状态和物流轨迹", "掌握包裹配送进度", "P0"),
                ("卖家", "上架新商品并设置价格库存", "开始售卖商品", "P0"),
                ("卖家", "处理新订单并安排发货", "及时完成履约", "P0"),
                ("买家", "申请退换货并跟踪处理进度", "解决商品问题", "P1"),
                ("卖家", "查看销售数据和库存预警", "优化经营策略", "P1"),
                ("买家", "管理收货地址和常用支付方式", "简化下单流程", "P1"),
                ("买家", "收藏商品并在降价时收到通知", "以理想价格购买", "P2"),
                ("卖家", "设置优惠活动和促销规则", "提升商品销量", "P2"),
            ],
            "fintech": [
                ("投资者", "注册并完成实名认证和风险评估", "合规开通投资账户", "P0"),
                ("投资者", "查看实时行情和市场数据", "做出投资决策", "P0"),
                ("投资者", "下单买入/卖出金融产品", "执行投资操作", "P0"),
                ("投资者", "查看资产总览和持仓明细", "了解投资组合状况", "P0"),
                ("投资者", "查看交易记录和资金流水", "核对账目和报税", "P1"),
                ("顾问", "查看客户资产配置和风险偏好", "提供个性化投顾建议", "P1"),
                ("顾问", "为客户生成投资报告", "展示投资表现和策略建议", "P1"),
                ("风控人员", "查看异常交易预警", "及时发现潜在风险", "P1"),
                ("风控人员", "审核大额交易和可疑操作", "确保交易合规", "P0"),
                ("投资者", "设置价格预警和自动交易规则", "不错过投资机会", "P2"),
                ("管理员", "生成监管合规报告", "满足监管要求", "P1"),
                ("投资者", "绑定银行卡完成充值和提现", "资金便捷流转", "P0"),
            ],
            "recruitment": [
                ("求职者", "上传或在线创建个人简历", "展示自己的专业能力", "P0"),
                ("求职者", "搜索和筛选职位（地点/薪资/类型）", "找到合适的工作机会", "P0"),
                ("求职者", "一键投递简历到目标职位", "高效求职", "P0"),
                ("求职者", "查看投递状态和面试邀请", "掌握求职进度", "P0"),
                ("HR", "发布职位并设置筛选条件", "吸引目标候选人", "P0"),
                ("HR", "浏览和筛选收到的简历", "快速定位合适候选人", "P0"),
                ("HR", "安排面试并发送邀请通知", "推进招聘流程", "P1"),
                ("HR", "记录面试评价和录用决定", "团队协同招聘决策", "P1"),
                ("求职者", "获取简历优化建议和匹配度评分", "提升求职竞争力", "P1"),
                ("管理者", "查看团队招聘进度和数据看板", "把控招聘节奏", "P2"),
                ("求职者", "订阅感兴趣的职位类型通知", "第一时间获取新机会", "P2"),
                ("HR", "管理人才库和历史候选人", "积累和盘活人才资源", "P2"),
            ],
        }

        if category in stories_map:
            stories = stories_map[category]
        else:
            # general: 基于描述生成
            nouns = self._extract_description_nouns()
            core = nouns[0] if nouns else "数据"
            second = nouns[1] if len(nouns) > 1 else "内容"
            stories = [
                ("用户", "通过邮箱或手机号快速注册", "立即开始使用产品", "P0"),
                ("用户", f"浏览和搜索{core}", f"快速找到目标{core}", "P0"),
                ("用户", f"查看{core}的详细信息", "做出操作决策", "P0"),
                ("用户", f"创建和编辑{second}", f"管理自己的{second}", "P0"),
                ("用户", "配置个人偏好和通知设置", "获得个性化体验", "P1"),
                ("管理员", "管理用户账号和权限分配", "确保平台安全运营", "P1"),
                ("管理员", f"审核和管理平台{core}", "维护内容质量", "P1"),
                ("用户", f"收藏和分享{core}", "方便后续查看和传播", "P1"),
                ("用户", f"导出{core}为 Excel/PDF", "离线查看和分析", "P2"),
                ("管理员", "查看平台运营数据和统计报表", "做出运营策略调整", "P2"),
                ("用户", "在移动端使用核心功能", "随时随地完成操作", "P2"),
                ("用户", "通过消息中心接收系统通知", "及时了解重要变更", "P2"),
            ]

        header = "\n| 作为 | 我想要 | 以便于 | 优先级 |\n|:---|:---|:---|:---:|\n"
        rows = "".join(
            f"| {role} | {want} | {benefit} | {pri} |\n" for role, want, benefit, pri in stories
        )
        return header + rows

    def _generate_data_entities(self) -> str:
        """生成数据实体 - 根据领域生成特定实体"""
        category = self._domain_category()
        # 通用的用户实体
        user_entity = """
### User（用户）

**属性**:
- id (UUID, PK) - 用户唯一标识
- username (string, unique) - 用户名
- email (string, unique) - 邮箱
- phone (string, unique, nullable) - 手机号
- password_hash (string) - 密码哈希
- avatar_url (string, nullable) - 头像地址
- role (enum) - 角色类型
- status (enum: active/inactive/banned) - 账户状态
- created_at (datetime) - 创建时间
- updated_at (datetime) - 更新时间
"""

        domain_entities = {
            "education": """
### Course（课程）

**属性**:
- id (UUID, PK) - 课程唯一标识
- title (string) - 课程名称
- description (text) - 课程描述
- instructor_id (UUID, FK -> User) - 讲师ID
- category_id (UUID, FK -> Category) - 分类ID
- cover_image (string) - 封面图URL
- difficulty (enum: beginner/intermediate/advanced) - 难度级别
- price (decimal) - 课程价格
- duration_hours (float) - 总时长（小时）
- student_count (int) - 学员数量
- rating (float) - 综合评分
- status (enum: draft/published/archived) - 发布状态
- created_at (datetime) - 创建时间

### Lesson（课时）

**属性**:
- id (UUID, PK) - 课时唯一标识
- course_id (UUID, FK -> Course) - 所属课程
- title (string) - 课时标题
- content_type (enum: video/text/quiz) - 内容类型
- content_url (string) - 内容资源URL
- duration_minutes (int) - 时长（分钟）
- sort_order (int) - 排序序号
- is_free_preview (boolean) - 是否免费试看

### Enrollment（选课记录）

**属性**:
- id (UUID, PK) - 记录唯一标识
- user_id (UUID, FK -> User) - 学员ID
- course_id (UUID, FK -> Course) - 课程ID
- enrolled_at (datetime) - 选课时间
- payment_amount (decimal) - 支付金额
- status (enum: active/completed/refunded) - 状态
- completed_at (datetime, nullable) - 完成时间

### Progress（学习进度）

**属性**:
- id (UUID, PK) - 记录唯一标识
- user_id (UUID, FK -> User) - 学员ID
- lesson_id (UUID, FK -> Lesson) - 课时ID
- progress_percent (float) - 完成百分比
- last_position (int) - 上次播放位置（秒）
- is_completed (boolean) - 是否完成
- updated_at (datetime) - 更新时间

### Quiz（测验）

**属性**:
- id (UUID, PK) - 测验唯一标识
- lesson_id (UUID, FK -> Lesson) - 所属课时
- title (string) - 测验标题
- questions (JSON) - 题目列表
- pass_score (int) - 及格分数
- time_limit_minutes (int, nullable) - 限时（分钟）

### Certificate（证书）

**属性**:
- id (UUID, PK) - 证书唯一标识
- user_id (UUID, FK -> User) - 学员ID
- course_id (UUID, FK -> Course) - 课程ID
- certificate_no (string, unique) - 证书编号
- issued_at (datetime) - 颁发时间
- verify_url (string) - 验证链接
""",
            "healthcare": """
### Patient（患者）

**属性**:
- id (UUID, PK) - 患者唯一标识
- user_id (UUID, FK -> User) - 关联用户账户
- medical_record_no (string, unique) - 病历号
- gender (enum: male/female/other) - 性别
- date_of_birth (date) - 出生日期
- blood_type (enum) - 血型
- allergy_info (text, nullable) - 过敏信息
- emergency_contact (string) - 紧急联系人
- emergency_phone (string) - 紧急联系电话
- insurance_info (JSON, nullable) - 医保信息

### Doctor（医生）

**属性**:
- id (UUID, PK) - 医生唯一标识
- user_id (UUID, FK -> User) - 关联用户账户
- department_id (UUID, FK -> Department) - 所属科室
- license_no (string, unique) - 执业证号
- title (enum: resident/attending/associate_chief/chief) - 职称
- specialization (string) - 专长领域
- consultation_fee (decimal) - 挂号费
- is_available (boolean) - 是否出诊

### Department（科室）

**属性**:
- id (UUID, PK) - 科室唯一标识
- name (string) - 科室名称
- description (text) - 科室描述
- location (string) - 位置楼层
- head_doctor_id (UUID, FK -> Doctor, nullable) - 科主任

### Appointment（预约挂号）

**属性**:
- id (UUID, PK) - 预约唯一标识
- patient_id (UUID, FK -> Patient) - 患者ID
- doctor_id (UUID, FK -> Doctor) - 医生ID
- appointment_date (date) - 预约日期
- time_slot (string) - 时段
- status (enum: pending/confirmed/cancelled/completed/no_show) - 状态
- symptoms (text, nullable) - 主诉症状
- fee (decimal) - 挂号费

### MedicalRecord（就诊记录）

**属性**:
- id (UUID, PK) - 记录唯一标识
- patient_id (UUID, FK -> Patient) - 患者ID
- doctor_id (UUID, FK -> Doctor) - 医生ID
- appointment_id (UUID, FK -> Appointment) - 关联预约
- diagnosis (text) - 诊断结果
- symptoms (text) - 症状描述
- treatment_plan (text) - 治疗方案
- notes (text, nullable) - 医嘱备注
- visit_date (datetime) - 就诊时间

### Prescription（处方）

**属性**:
- id (UUID, PK) - 处方唯一标识
- medical_record_id (UUID, FK -> MedicalRecord) - 关联就诊记录
- doctor_id (UUID, FK -> Doctor) - 开方医生
- items (JSON) - 药品列表（名称/剂量/用法/数量）
- status (enum: pending/dispensed/cancelled) - 状态
- total_cost (decimal) - 总费用
- issued_at (datetime) - 开方时间
""",
            "ecommerce": """
### Product（商品）

**属性**:
- id (UUID, PK) - 商品唯一标识
- seller_id (UUID, FK -> User) - 卖家ID
- category_id (UUID, FK -> Category) - 分类ID
- name (string) - 商品名称
- description (text) - 商品描述
- price (decimal) - 销售价
- original_price (decimal, nullable) - 原价
- stock (int) - 库存数量
- images (JSON) - 图片列表
- specs (JSON) - 规格参数
- rating (float) - 综合评分
- sales_count (int) - 销量
- status (enum: draft/on_sale/off_shelf/sold_out) - 状态

### Category（分类）

**属性**:
- id (UUID, PK) - 分类唯一标识
- name (string) - 分类名称
- parent_id (UUID, FK -> Category, nullable) - 父分类
- icon (string, nullable) - 图标
- sort_order (int) - 排序

### Order（订单）

**属性**:
- id (UUID, PK) - 订单唯一标识
- order_no (string, unique) - 订单编号
- buyer_id (UUID, FK -> User) - 买家ID
- total_amount (decimal) - 订单总额
- discount_amount (decimal) - 优惠金额
- shipping_fee (decimal) - 运费
- payment_amount (decimal) - 实付金额
- status (enum: pending/paid/shipped/delivered/completed/cancelled/refunding) - 状态
- address_snapshot (JSON) - 收货地址快照
- payment_method (string) - 支付方式
- paid_at (datetime, nullable) - 支付时间
- shipped_at (datetime, nullable) - 发货时间

### OrderItem（订单项）

**属性**:
- id (UUID, PK) - 订单项唯一标识
- order_id (UUID, FK -> Order) - 订单ID
- product_id (UUID, FK -> Product) - 商品ID
- product_snapshot (JSON) - 商品快照（下单时信息）
- quantity (int) - 数量
- unit_price (decimal) - 单价
- subtotal (decimal) - 小计

### Payment（支付记录）

**属性**:
- id (UUID, PK) - 支付唯一标识
- order_id (UUID, FK -> Order) - 订单ID
- payment_no (string, unique) - 支付流水号
- channel (enum: wechat/alipay/card/bank) - 支付渠道
- amount (decimal) - 支付金额
- status (enum: pending/success/failed/refunded) - 状态
- paid_at (datetime, nullable) - 完成时间

### Review（评价）

**属性**:
- id (UUID, PK) - 评价唯一标识
- product_id (UUID, FK -> Product) - 商品ID
- user_id (UUID, FK -> User) - 用户ID
- order_item_id (UUID, FK -> OrderItem) - 订单项ID
- rating (int, 1-5) - 评分
- content (text) - 评价内容
- images (JSON, nullable) - 评价图片
- created_at (datetime) - 评价时间

### Address（收货地址）

**属性**:
- id (UUID, PK) - 地址唯一标识
- user_id (UUID, FK -> User) - 用户ID
- receiver_name (string) - 收件人
- phone (string) - 联系电话
- province (string) - 省
- city (string) - 市
- district (string) - 区
- detail (string) - 详细地址
- is_default (boolean) - 是否默认
""",
            "fintech": """
### Account（账户）

**属性**:
- id (UUID, PK) - 账户唯一标识
- user_id (UUID, FK -> User) - 用户ID
- account_no (string, unique) - 账户编号
- account_type (enum: savings/investment/credit) - 账户类型
- balance (decimal) - 账户余额
- currency (string) - 币种
- risk_level (enum: conservative/moderate/aggressive) - 风险等级
- kyc_status (enum: pending/verified/rejected) - KYC 状态
- frozen (boolean) - 是否冻结
- opened_at (datetime) - 开户时间

### Transaction（交易记录）

**属性**:
- id (UUID, PK) - 交易唯一标识
- transaction_no (string, unique) - 交易流水号
- account_id (UUID, FK -> Account) - 账户ID
- type (enum: deposit/withdraw/buy/sell/transfer/dividend) - 交易类型
- amount (decimal) - 交易金额
- fee (decimal) - 手续费
- balance_after (decimal) - 交易后余额
- status (enum: pending/completed/failed/cancelled) - 状态
- description (text) - 交易描述
- created_at (datetime) - 交易时间

### Portfolio（投资组合）

**属性**:
- id (UUID, PK) - 组合唯一标识
- user_id (UUID, FK -> User) - 用户ID
- name (string) - 组合名称
- total_value (decimal) - 总市值
- total_cost (decimal) - 总成本
- return_rate (float) - 收益率
- risk_score (float) - 风险评分
- updated_at (datetime) - 更新时间

### Asset（资产持仓）

**属性**:
- id (UUID, PK) - 持仓唯一标识
- portfolio_id (UUID, FK -> Portfolio) - 组合ID
- asset_code (string) - 资产代码
- asset_name (string) - 资产名称
- asset_type (enum: stock/bond/fund/crypto/cash) - 资产类型
- quantity (decimal) - 持有数量
- avg_cost (decimal) - 平均成本
- current_price (decimal) - 当前价格
- market_value (decimal) - 当前市值
- unrealized_pnl (decimal) - 未实现盈亏

### Alert（预警规则）

**属性**:
- id (UUID, PK) - 预警唯一标识
- user_id (UUID, FK -> User) - 用户ID
- asset_code (string) - 资产代码
- condition_type (enum: price_above/price_below/change_percent) - 条件类型
- threshold (decimal) - 阈值
- is_active (boolean) - 是否启用
- triggered_at (datetime, nullable) - 最后触发时间

### ComplianceReport（合规报告）

**属性**:
- id (UUID, PK) - 报告唯一标识
- report_type (enum: daily/monthly/quarterly/suspicious) - 报告类型
- period_start (date) - 统计起始日
- period_end (date) - 统计截止日
- content (JSON) - 报告内容
- generated_by (UUID, FK -> User) - 生成人
- status (enum: draft/submitted/approved) - 状态
""",
            "recruitment": """
### Resume（简历）

**属性**:
- id (UUID, PK) - 简历唯一标识
- user_id (UUID, FK -> User) - 求职者ID
- title (string) - 简历标题
- summary (text) - 个人简介
- work_experience (JSON) - 工作经历列表
- education (JSON) - 教育经历列表
- skills (JSON) - 技能标签
- expected_salary_min (decimal) - 期望薪资下限
- expected_salary_max (decimal) - 期望薪资上限
- expected_city (string) - 期望城市
- file_url (string, nullable) - 简历附件URL
- is_public (boolean) - 是否公开
- updated_at (datetime) - 更新时间

### JobPosting（职位）

**属性**:
- id (UUID, PK) - 职位唯一标识
- company_id (UUID, FK -> User) - 企业ID
- title (string) - 职位名称
- department (string) - 所属部门
- description (text) - 职位描述
- requirements (text) - 任职要求
- salary_min (decimal) - 薪资下限
- salary_max (decimal) - 薪资上限
- city (string) - 工作城市
- employment_type (enum: full_time/part_time/contract/intern) - 工作类型
- experience_years (string) - 经验要求
- education_level (string) - 学历要求
- headcount (int) - 招聘人数
- status (enum: open/paused/closed/filled) - 状态
- expires_at (datetime) - 截止日期

### Application（投递记录）

**属性**:
- id (UUID, PK) - 投递唯一标识
- resume_id (UUID, FK -> Resume) - 简历ID
- job_id (UUID, FK -> JobPosting) - 职位ID
- applicant_id (UUID, FK -> User) - 求职者ID
- status (enum: submitted/viewed/shortlisted/interview/offer/rejected/withdrawn) - 状态
- match_score (float, nullable) - 匹配度评分
- cover_letter (text, nullable) - 求职信
- applied_at (datetime) - 投递时间

### Interview（面试）

**属性**:
- id (UUID, PK) - 面试唯一标识
- application_id (UUID, FK -> Application) - 投递ID
- round (int) - 面试轮次
- interview_type (enum: phone/video/onsite) - 面试类型
- scheduled_at (datetime) - 面试时间
- duration_minutes (int) - 预计时长
- interviewer_ids (JSON) - 面试官列表
- feedback (text, nullable) - 面试反馈
- rating (int, nullable) - 面试评分
- result (enum: pending/pass/fail, nullable) - 面试结果

### Company（企业）

**属性**:
- id (UUID, PK) - 企业唯一标识
- user_id (UUID, FK -> User) - 管理者ID
- name (string) - 企业名称
- industry (string) - 所属行业
- scale (enum: startup/small/medium/large/enterprise) - 企业规模
- description (text) - 企业介绍
- logo_url (string, nullable) - LOGO
- website (string, nullable) - 官网
- address (string) - 地址
""",
        }

        if category in domain_entities:
            return user_entity + domain_entities[category]

        # general: 从描述提取实体
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "Resource"
        second = nouns[1] if len(nouns) > 1 else "Category"
        third = nouns[2] if len(nouns) > 2 else "Record"

        return (
            user_entity
            + f"""
### {core}（核心业务实体）

**属性**:
- id (UUID, PK) - 唯一标识
- title (string) - 名称/标题
- description (text) - 描述
- creator_id (UUID, FK -> User) - 创建者
- {second.lower()}_id (UUID, FK, nullable) - 关联分类
- status (enum: draft/active/archived) - 状态
- metadata (JSON) - 扩展属性
- tags (JSON) - 标签列表
- created_at (datetime) - 创建时间
- updated_at (datetime) - 更新时间

### {second}（分类）

**属性**:
- id (UUID, PK) - 唯一标识
- name (string) - 分类名称
- parent_id (UUID, FK -> {second}, nullable) - 父分类
- description (text, nullable) - 分类描述
- sort_order (int) - 排序
- created_at (datetime) - 创建时间

### {third}（操作记录）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 操作用户
- {core.lower()}_id (UUID, FK -> {core}) - 关联业务实体
- action (enum: create/update/delete/view/export) - 操作类型
- details (JSON) - 操作详情
- ip_address (string) - IP 地址
- created_at (datetime) - 操作时间

### Comment（评论/反馈）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 评论者
- target_id (UUID) - 目标实体ID
- target_type (string) - 目标实体类型
- content (text) - 评论内容
- rating (int, nullable) - 评分
- created_at (datetime) - 创建时间

### Notification（通知）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 接收用户
- type (enum: system/business/alert) - 通知类型
- title (string) - 通知标题
- content (text) - 通知内容
- is_read (boolean) - 是否已读
- created_at (datetime) - 创建时间
"""
        )

    def _generate_user_journeys(self) -> str:
        """生成用户旅程 - 根据领域生成 3-4 个具体旅程"""
        category = self._domain_category()
        journeys_map = {
            "education": """
**旅程 1: 学生选课与学习**

```
浏览课程目录 → 筛选分类/难度 → 查看课程详情与评价 → 试看免费章节
     → 购买/选课 → 观看视频课程 → 完成课后测验 → 查看学习进度
     → 获得课程证书
```

痛点: 不知道哪门课适合自己的水平；学习中途容易放弃
优化: 提供学前水平测试和个性化推荐；设置学习计划和打卡提醒机制

**旅程 2: 教师创建课程**

```
登录教师端 → 创建新课程 → 编辑课程大纲 → 上传视频/文档资料
     → 设置测验题目 → 预览课程效果 → 发布上线
     → 查看学生学习数据 → 根据反馈迭代内容
```

痛点: 视频上传慢、格式兼容问题多；缺少学生反馈渠道
优化: 支持多格式断点续传；提供实时学情数据面板和问答区

**旅程 3: 管理员日常运营**

```
查看今日运营数据 → 审核新提交课程 → 处理用户反馈/投诉
     → 管理教师账号和权限 → 生成月度运营报表 → 调整推荐策略
```

痛点: 数据分散在多个系统，运营效率低
优化: 统一运营看板，关键指标实时更新，异常自动预警
""",
            "healthcare": """
**旅程 1: 患者在线就诊**

```
搜索科室/症状 → 选择医生 → 预约挂号（选择日期时段）→ 在线缴挂号费
     → 到院签到/在线候诊 → 医生问诊 → 查看诊断和医嘱
     → 取药/在线购药 → 查看电子病历
```

痛点: 挂号难、等候时间长；纸质病历查找不便
优化: 智能推荐科室和医生；电子病历随时查看，跨院互通

**旅程 2: 医生接诊工作流**

```
查看今日排班和接诊列表 → 查阅患者历史病历和检查报告
     → 问诊记录与诊断 → 开具电子处方 → 安排复查/转诊
     → 撰写病历记录 → 查看科室工作量统计
```

痛点: 病历书写耗时；历史数据调取慢
优化: 结构化病历模板快速填写；AI 辅助病历摘要和诊断提示

**旅程 3: 慢病管理**

```
建立健康档案 → 设置用药提醒 → 定期记录健康指标（血压/血糖等）
     → 查看健康趋势图 → 收到异常预警 → 在线复诊咨询
     → 调整治疗方案
```

痛点: 慢病患者缺乏持续管理，复诊不及时
优化: 自动化指标采集和趋势分析；智能复诊提醒

**旅程 4: 医院管理**

```
查看全院运营数据 → 管理科室排班 → 审核医疗质量指标
     → 处理患者投诉 → 管理医疗耗材库存 → 生成监管报告
```

痛点: 数据采集依赖人工，报表滞后
优化: 数据自动采集和实时看板；报告一键生成
""",
            "ecommerce": """
**旅程 1: 消费者购物**

```
首页/搜索发现商品 → 浏览商品列表 → 筛选（价格/品牌/评分）
     → 查看商品详情与评价 → 选择规格加入购物车
     → 确认订单与地址 → 选择支付方式付款
     → 查看物流追踪 → 确认收货 → 评价晒单
```

痛点: 搜索结果不精准，找不到想要的商品；支付流程繁琐
优化: 智能搜索与个性化推荐；一键支付和地址智能填充

**旅程 2: 商家运营**

```
登录商家后台 → 上架新商品（编辑信息/拍照/定价）→ 管理库存
     → 处理新订单 → 打包发货 → 跟踪物流
     → 处理退换货/售后 → 查看销售数据与分析
     → 参与平台促销活动
```

痛点: 多个平台库存不同步；退换货流程复杂
优化: 多平台库存统一管理；标准化售后工单流程

**旅程 3: 售后维权**

```
发起退换货申请 → 选择原因 → 提交证据（照片/描述）
     → 等待商家审核 → 寄回商品 → 确认退款
     → 评价售后服务
```

痛点: 退换货流程长、沟通成本高
优化: 标准化退换货流程；引入平台仲裁机制

**旅程 4: 首次用户转化**

```
广告/分享链接到达落地页 → 浏览爆款/活动 → 领取新人优惠券
     → 注册/手机号登录 → 首单下单 → 收到货品
     → 推送二次复购优惠
```

痛点: 新用户注册流程摩擦大，首单犹豫
优化: 一键手机号登录；新人专属优惠降低决策门槛
""",
            "fintech": """
**旅程 1: 新用户开户**

```
下载APP/访问网站 → 手机号注册 → 实名认证（身份证/人脸）
     → 风险评估问卷 → 绑定银行卡 → 首次入金
     → 浏览理财产品/行情 → 首笔投资
```

痛点: 实名认证流程复杂，等待时间长
优化: OCR 自动识别证件；人脸比对秒级验证；清晰的进度提示

**旅程 2: 日常投资交易**

```
查看资产总览 → 浏览市场行情 → 分析目标标的
     → 下单买入/卖出 → 确认交易 → 查看成交结果
     → 查看持仓变化 → 收到风险/收益提醒
```

痛点: 行情数据延迟；交易确认不及时
优化: 实时行情推送；交易状态即时反馈；关键节点push通知

**旅程 3: 资产管理与分析**

```
查看投资组合全景 → 分析收益走势 → 查看各资产表现
     → 评估风险敞口 → 调整资产配置 → 导出投资报告
```

痛点: 资产分散难以全局把控；分析工具不够直观
优化: 跨账户资产聚合面板；可视化分析图表；一键导出报告

**旅程 4: 合规风控**

```
系统自动扫描交易 → 触发异常预警 → 风控人员审核
     → 标记/冻结可疑交易 → 联系客户确认 → 解除/上报处理
     → 生成合规报告
```

痛点: 人工审核效率低，漏报风险高
优化: AI 驱动的实时异常检测；自动化分级预警
""",
            "recruitment": """
**旅程 1: 求职者找工作**

```
注册/完善简历 → 搜索职位（关键词/城市/薪资）→ 浏览职位列表
     → 查看职位详情与公司信息 → 投递简历 → 查看投递状态
     → 收到面试邀请 → 在线/现场面试 → 等待结果通知
     → 接受Offer
```

痛点: 海投低效，匹配度差；不知道面试应该准备什么
优化: AI 匹配度评分指导精准投递；提供面试题库和公司面经

**旅程 2: HR 招聘流程**

```
创建招聘需求 → 发布职位 → 收到简历 → 筛选简历（AI 辅助排序）
     → 约候选人面试 → 面试评价打分 → 团队决策
     → 发送Offer → 入职跟踪
```

痛点: 简历量大筛选耗时；面试安排协调困难
优化: AI 简历预筛选和排序；智能排期自动匹配面试官空闲时段

**旅程 3: 简历优化**

```
上传现有简历 → 获取智能评分 → 查看优化建议（内容/格式/关键词）
     → 在线编辑修改 → 选择简历模板 → 预览效果
     → 下载 PDF 版本
```

痛点: 不知道简历哪里有问题；缺少行业针对性
优化: 基于JD的关键词匹配分析；分行业的简历优化建议
""",
        }

        if category in journeys_map:
            return journeys_map[category]

        # general
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心功能"
        return f"""
**旅程 1: 新用户首次体验**

```
发现产品（搜索/推荐/分享）→ 访问首页 → 浏览核心功能介绍
     → 注册账户（手机号/邮箱/社交登录）→ 完成引导设置
     → 体验{core}核心操作 → 完成首次任务
```

痛点: 不了解产品能做什么；注册流程摩擦大
优化: 清晰的功能引导和新手教程；支持社交一键登录

**旅程 2: 核心功能使用**

```
登录 → 进入{core}模块 → 搜索/浏览目标内容
     → 查看详情 → 执行核心操作（创建/编辑/提交）
     → 确认结果 → 收到操作反馈/通知
```

痛点: 操作步骤多、路径不清晰；等待反馈时间长
优化: 减少操作步骤；实时状态反馈；常用操作一键直达

**旅程 3: 管理与分析**

```
进入管理后台 → 查看数据概览看板 → 筛选和分析关键指标
     → 处理待办事项（审核/回复/处理）→ 导出数据报表
     → 调整系统配置
```

痛点: 数据展示不直观；导出格式有限
优化: 可视化数据看板；支持多格式导出；异常数据自动预警

**旅程 4: 问题反馈与支持**

```
遇到问题 → 查看帮助文档/FAQ → 提交反馈/工单
     → 收到客服回复 → 问题解决 → 评价服务体验
```

痛点: 找不到帮助入口；回复不及时
优化: 全局帮助入口和智能搜索；工单状态实时更新
"""

    def _generate_page_structure(self) -> str:
        """生成页面结构"""
        return """
**主要页面**:

1. **登录/注册页**
   - 登录表单
   - 注册表单
   - 忘记密码

2. **首页**
   - 欢迎信息
   - 快速入口
   - 数据概览

3. **列表页**
   - 搜索栏
   - 筛选器
   - 数据列表
   - 分页器

4. **详情页**
   - 详细信息
   - 相关操作
   - 返回按钮

5. **设置页**
   - 个人资料
   - 账户安全
   - 偏好设置
"""

    def _generate_business_rules(self) -> str:
        """生成业务规则 - 根据领域生成特定规则"""
        return self._build_business_rules()

    def _build_business_rules(self) -> str:
        category = self._domain_category()
        auth_rules = (
            "\n### 认证与安全规则\n"
            "- 密码最小长度 8 位，必须包含大小写字母和数字\n"
            "- 不能包含用户名或常见弱密码\n"
            "- 连续登录失败 5 次，账户锁定 30 分钟\n"
            "- Session 超时时间 2 小时，支持续期\n"
            "- 同一账户最多 5 台设备同时在线\n"
            "- 敏感操作需二次验证\n"
        )
        if category == "education":
            return auth_rules + (
                "\n### 选课与学习规则\n"
                "- 免费课程注册即可学习，付费课程需完成支付后开通\n"
                "- 购买后 7 天内未开始学习可申请全额退款\n"
                "- 已学习超过 30% 的课程不支持退款\n"
                "- 课程学习进度自动保存，支持跨设备同步\n"
                "\n### 测验评分规则\n"
                "- 每次测验最多 3 次答题机会，取最高分\n"
                "- 综合得分达到 60 分以上方可获得课程完成证书\n"
                "- 证书编号全局唯一，支持在线验证\n"
                "\n### 讲师与内容规则\n"
                "- 讲师发布课程需经过平台审核（1-3 个工作日）\n"
                "- 课程上线后修改内容需重新提交审核\n"
                "- 讲师收入每月结算，次月 15 日前到账\n"
                "\n### 运营规则\n"
                "- 学生反馈需在 24 小时内响应\n"
                "- 课程评分低于 3.0 将自动下架\n"
            )
        if category == "healthcare":
            return auth_rules + (
                "\n### 预约挂号规则\n"
                "- 每位患者同一科室同一天限挂 1 个号\n"
                "- 预约挂号需提前 1-7 天，当日号源仅限现场\n"
                "- 累计 3 次未到院将限制预约功能 30 天\n"
                "- 取消预约需在就诊前 4 小时以上\n"
                "\n### 处方与用药规则\n"
                "- 处方有效期 3 天，超期需重新开具\n"
                "- 特殊管制药品需双人核对签字\n"
                "- 患者过敏信息必须在开方前自动校验\n"
                "\n### 数据隐私规则\n"
                "- 病历数据仅限就诊医生和授权医护访问\n"
                "- 病历查看记录全程留痕，支持审计追溯\n"
                "- 数据存储和传输必须加密（AES-256 / TLS 1.3）\n"
                "- 脱敏处理：隐藏身份证号、手机号中间 4 位\n"
                "\n### 医疗质量规则\n"
                "- 门诊病历需在就诊当日完成\n"
                "- 医疗差错事件必须在 24 小时内上报\n"
            )
        if category == "ecommerce":
            return auth_rules + (
                "\n### 订单规则\n"
                "- 订单提交后 30 分钟内未支付自动取消\n"
                "- 已支付未发货可随时取消并全额退款\n"
                "- 订单完成后 15 天内可申请售后\n"
                "\n### 退换货规则\n"
                "- 非质量问题：7 天无理由退换（未拆封）\n"
                "- 质量问题：30 天内可退换，运费由商家承担\n"
                "- 退款审核通过后 1-3 个工作日退回原支付方式\n"
                "\n### 库存规则\n"
                "- 库存低于安全线自动预警\n"
                "- 下单即锁定库存，取消/超时自动释放\n"
                "\n### 营销活动规则\n"
                "- 优惠券不可叠加使用\n"
                "- 秒杀商品限购 1 件/人\n"
                "- 拼团 24 小时内未成团自动退款\n"
                "\n### 商家规则\n"
                "- 新订单需在 48 小时内发货\n"
                "- 商家评分低于 4.0 将限制活动参与\n"
            )
        if category == "fintech":
            return auth_rules + (
                "\n### 交易规则\n"
                "- 单笔交易金额上限根据风险等级设定\n"
                "- 当日撤单次数上限 20 次\n"
                "\n### KYC 与合规规则\n"
                "- 开户必须完成实名认证（身份证 + 人脸识别）\n"
                "- 风险评估问卷必须每 2 年更新一次\n"
                "- 高风险产品仅向合格投资者开放\n"
                "- 单日转账超过 5 万元触发大额报告\n"
                "\n### 风控规则\n"
                "- 高频交易自动触发审核\n"
                "- 异地登录自动触发二次验证\n"
                "- 可疑交易 24 小时内冻结并通知客户\n"
                "\n### 资金安全规则\n"
                "- 提现必须至绑定的实名银行卡\n"
                "- 新绑定银行卡 24 小时内限额 5000 元\n"
                "- 修改交易密码后 24 小时内禁止提现\n"
                "- 资金流水保留 5 年以上\n"
            )
        if category == "recruitment":
            return auth_rules + (
                "\n### 简历与投递规则\n"
                "- 每位求职者最多创建 5 份简历\n"
                "- 同一职位限投 1 次，30 天后可重新投递\n"
                "- HR 应在 7 天内给出反馈\n"
                "\n### 职位发布规则\n"
                "- 职位信息必须包含岗位名称、职责、要求、薪资范围\n"
                "- 薪资范围必须真实\n"
                "- 职位有效期默认 30 天，可续期\n"
                "\n### 面试规则\n"
                "- 面试邀请需至少提前 24 小时发出\n"
                "- 面试评价需在面试结束 48 小时内完成\n"
                "\n### 隐私规则\n"
                "- 求职者可设置简历可见范围\n"
                "- 企业下载简历需获得求职者授权\n"
                "- 账号注销后简历数据 30 天内完全清除\n"
            )
        # general
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "业务数据"
        return auth_rules + (
            f"\n### {core}管理规则\n"
            f"- 创建{core}时必填字段需完成验证后才能提交\n"
            f"- {core}状态变更需记录操作日志\n"
            f"- 已发布的{core}修改需经审核后生效\n"
            f"- 删除{core}为软删除，保留 30 天后永久清除\n"
            "\n### 权限与协作规则\n"
            "- 数据访问遵循最小权限原则\n"
            "- 管理员操作日志保留 180 天\n"
            "- 批量操作需二次确认\n"
            "\n### 数据质量规则\n"
            "- 导入数据需通过格式校验和去重检查\n"
            "- 关键业务数据每日自动备份\n"
            "- 敏感字段展示时自动脱敏\n"
        )

    def _generate_acceptance_criteria(self) -> str:
        """生成验收标准 - 根据领域生成具体标准"""
        category = self._domain_category()
        common = (
            "\n### 认证与安全验收\n"
            "- [ ] 用户可以使用邮箱/手机号注册\n"
            "- [ ] 用户可以使用密码登录\n"
            "- [ ] 用户可以重置密码\n"
            "- [ ] 登录状态保持 2 小时\n"
            "- [ ] 所有受保护接口需要认证\n"
            "- [ ] 密码使用 bcrypt 加密存储\n"
            "- [ ] Token 使用 JWT 签名\n"
            "- [ ] 所有输入验证防注入\n"
            "- [ ] 敏感操作有审计日志\n"
        )
        domain = self._acceptance_criteria_for_domain(category)
        if domain:
            return common + domain
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心功能"
        return common + (
            f"\n### {core}功能验收\n"
            f"- [ ] 用户可以创建/编辑/删除{core}\n"
            f"- [ ] 用户可以搜索和筛选{core}\n"
            f"- [ ] 用户可以查看{core}详情\n"
            f"- [ ] 用户可以导出{core}数据\n"
            "\n### 管理功能验收\n"
            "- [ ] 管理员可以管理用户和权限\n"
            "- [ ] 管理员可以查看运营数据\n"
            "\n### 性能验收\n"
            "- [ ] 列表页加载 < 2s\n"
            "- [ ] 搜索响应 < 500ms\n"
            "- [ ] API P95 < 200ms\n"
            "- [ ] 支持 1000+ 并发用户\n"
        )

    def _acceptance_criteria_for_domain(self, category: str) -> str:
        """返回领域特定的验收标准"""
        criteria = {
            "education": (
                "\n### 课程功能验收\n"
                "- [ ] 学生可以浏览和搜索课程\n"
                "- [ ] 学生可以购买付费课程\n"
                "- [ ] 学生可以观看视频（倍速/断点续播）\n"
                "- [ ] 学习进度自动保存并跨设备同步\n"
                "- [ ] 学生可以完成测验并查看成绩\n"
                "- [ ] 教师可以创建和编辑课程\n"
                "- [ ] 教师可以查看学生学习数据\n"
                "- [ ] 管理员可以审核课程\n"
                "\n### 性能验收\n"
                "- [ ] 课程页面首屏加载 < 2s\n"
                "- [ ] 视频播放启动 < 3s\n"
                "- [ ] 搜索响应 < 500ms\n"
            ),
            "healthcare": (
                "\n### 患者服务验收\n"
                "- [ ] 患者可以预约挂号\n"
                "- [ ] 患者可以查看就诊记录和检查报告\n"
                "- [ ] 患者可以在线缴费\n"
                "- [ ] 医生可以查看接诊列表和病历\n"
                "- [ ] 医生可以开具电子处方\n"
                "- [ ] 处方开具时自动校验过敏信息\n"
                "\n### 合规验收\n"
                "- [ ] 病历仅授权人员可访问\n"
                "- [ ] 数据访问记录可审计\n"
                "- [ ] 敏感数据自动脱敏\n"
                "- [ ] 数据传输和存储全程加密\n"
                "\n### 性能验收\n"
                "- [ ] 挂号页面加载 < 2s\n"
                "- [ ] 病历查询响应 < 500ms\n"
            ),
            "ecommerce": (
                "\n### 购物流程验收\n"
                "- [ ] 买家可以搜索和筛选商品\n"
                "- [ ] 买家可以加入购物车并结算\n"
                "- [ ] 买家可以完成在线支付\n"
                "- [ ] 买家可以查看订单和物流\n"
                "- [ ] 买家可以申请退换货\n"
                "- [ ] 商家可以上架商品和处理订单\n"
                "\n### 交易安全验收\n"
                "- [ ] 支付流程全程加密\n"
                "- [ ] 库存扣减保证原子性\n"
                "- [ ] 超时未支付自动取消\n"
                "\n### 性能验收\n"
                "- [ ] 商品搜索响应 < 500ms\n"
                "- [ ] 下单接口响应 < 1s\n"
                "- [ ] 支持 2000+ 并发用户\n"
            ),
            "fintech": (
                "\n### 账户与交易验收\n"
                "- [ ] 用户可以完成实名认证\n"
                "- [ ] 用户可以绑定银行卡并充值/提现\n"
                "- [ ] 用户可以查看实时行情\n"
                "- [ ] 用户可以下单买入/卖出\n"
                "- [ ] 用户可以查看资产和持仓\n"
                "\n### 风控合规验收\n"
                "- [ ] 异常交易自动预警\n"
                "- [ ] 大额交易需风控审核\n"
                "- [ ] KYC 未通过无法交易\n"
                "\n### 性能验收\n"
                "- [ ] 行情数据延迟 < 1s\n"
                "- [ ] 交易下单响应 < 500ms\n"
            ),
            "recruitment": (
                "\n### 求职功能验收\n"
                "- [ ] 求职者可以创建/编辑简历\n"
                "- [ ] 求职者可以搜索和筛选职位\n"
                "- [ ] 求职者可以一键投递\n"
                "- [ ] 求职者可以查看投递状态\n"
                "\n### 招聘功能验收\n"
                "- [ ] HR 可以发布和管理职位\n"
                "- [ ] HR 可以筛选简历\n"
                "- [ ] HR 可以安排面试\n"
                "\n### 性能验收\n"
                "- [ ] 职位搜索响应 < 500ms\n"
                "- [ ] 简历解析 < 5s\n"
                "- [ ] 页面首屏加载 < 2s\n"
            ),
        }
        return criteria.get(category, "")

    def _generate_technical_risks(self) -> str:
        """生成技术风险 - 根据技术栈和领域动态生成"""
        category = self._domain_category()
        frontend = self.frontend.lower()
        backend = self.backend.lower()
        fe_risks = {
            "react": "React 组件树深层嵌套导致渲染性能下降；大量状态更新引发不必要的 re-render",
            "next": "Next.js SSR/SSG 首屏渲染策略选择不当导致 TTFB 偏高；ISR 缓存失效策略需精细调优",
            "vue": "Vue 大型列表虚拟滚动性能优化；响应式数据过深导致性能问题",
            "angular": "Angular 变更检测策略不当导致性能瓶颈；RxJS 订阅泄漏风险",
        }
        fe_risk = fe_risks.get(frontend, f"{self.frontend} 前端框架在大数据量渲染时的性能优化挑战")
        be_risks = {
            "node": "Node.js 单线程在 CPU 密集型任务下的性能瓶颈；内存泄漏排查困难",
            "python": "Python GIL 限制多核并发能力；异步与同步混用导致性能不稳定",
            "java": "Java 服务启动时间较长影响弹性伸缩效率；GC 停顿可能影响 P99 延迟",
            "go": "Go 协程泄漏导致内存持续增长；依赖管理和版本兼容性挑战",
        }
        be_risk = be_risks.get(backend, f"{self.backend} 后端在高并发场景下的稳定性挑战")
        domain_risks = {
            "education": (
                "\n### 领域特定风险\n"
                "- **视频流媒体**: 大量并发视频播放对 CDN 和带宽的压力\n"
                "- **考试防作弊**: 在线考试防切屏、防复制等机制的技术实现复杂度\n"
                "- **学习数据分析**: 海量学习行为数据的实时采集和分析挑战\n"
                "\n**缓解方案**:\n"
                "- 采用 HLS/DASH 自适应码率 + 多 CDN 调度\n"
                "- 前端全屏监控 + 后端行为分析双重防作弊\n"
                "- 引入流式计算处理实时学习数据\n"
            ),
            "healthcare": (
                "\n### 领域特定风险\n"
                "- **数据合规**: 医疗数据需严格遵循《个人信息保护法》/HIPAA，加密方案复杂度高\n"
                "- **系统可用性**: 医疗系统不允许停机，需要 99.99% 可用性保障\n"
                "- **数据互通**: 与 HIS/LIS/PACS 等医院信息系统的集成标准不统一\n"
                "\n**缓解方案**:\n"
                "- 引入合规审计框架，数据分级分类管理\n"
                "- 多活架构 + 自动故障转移 + 定期容灾演练\n"
                "- 采用 HL7 FHIR 标准接口，渐进式集成\n"
            ),
            "ecommerce": (
                "\n### 领域特定风险\n"
                "- **秒杀高并发**: 瞬时流量峰值可能是日常的 100 倍，库存扣减需保证原子性\n"
                "- **支付安全**: 需防范重复支付、支付回调伪造等攻击\n"
                "- **数据一致性**: 订单-库存-支付三方数据一致性挑战\n"
                "\n**缓解方案**:\n"
                "- Redis 预扣库存 + 消息队列异步下单 + 令牌桶限流\n"
                "- 支付签名校验 + 幂等性设计 + 对账机制\n"
                "- Saga 模式处理分布式事务\n"
            ),
            "fintech": (
                "\n### 领域特定风险\n"
                "- **交易延迟**: 行情数据和交易执行的毫秒级延迟要求\n"
                "- **资金安全**: 资金计算精度（浮点数问题）、并发交易下的余额一致性\n"
                "- **监管合规**: PCI-DSS 安全标准、反洗钱系统的持续合规成本\n"
                "\n**缓解方案**:\n"
                "- 内存数据库 + 低延迟消息队列 + 就近部署\n"
                "- 使用 Decimal 精确计算 + 乐观锁 + 事务日志\n"
                "- 引入合规引擎自动化审查\n"
            ),
            "recruitment": (
                "\n### 领域特定风险\n"
                "- **简历解析准确性**: 不同格式简历的结构化解析准确率挑战\n"
                "- **匹配算法公平性**: AI 匹配算法可能存在隐性偏见\n"
                "- **数据隐私**: 大量简历数据的存储和使用需严格合规\n"
                "\n**缓解方案**:\n"
                "- 多格式解析引擎 + NLP 实体抽取 + 人工校验兜底\n"
                "- 定期进行偏见审计和模型调优\n"
                "- 数据最小化原则 + 自动化数据生命周期管理\n"
            ),
        }
        domain_section = domain_risks.get(
            category,
            (
                "\n### 领域特定风险\n"
                f"- **业务复杂度**: {self.description[:60]} 涉及的业务规则复杂\n"
                "- **第三方依赖**: 外部服务的稳定性直接影响系统可用性\n"
                "\n**缓解方案**:\n"
                "- 领域驱动设计（DDD）明确限界上下文\n"
                "- 第三方服务封装隔离层 + 降级预案\n"
            ),
        )
        return (
            f"\n### 前端技术风险\n"
            f"- {fe_risk}\n"
            f"- {self.platform.upper()} 平台下多设备适配的测试覆盖挑战\n"
            "\n**缓解方案**:\n"
            "- 性能监控（Web Vitals / Lighthouse）+ 性能预算机制\n"
            "- 关键路径渲染优化 + 代码分割 + 懒加载\n"
            f"\n### 后端技术风险\n"
            f"- {be_risk}\n"
            "- 数据库在数据量增长后的查询性能衰减\n"
            "\n**缓解方案**:\n"
            "- 负载测试 + APM 监控 + 自动扩缩容\n"
            "- 数据库读写分离 + 合理索引 + 缓存层\n"
            f"{domain_section}"
            "\n### 基础设施风险\n"
            "- 容器编排复杂度随服务数量增加而上升\n"
            "- 多环境配置管理一致性\n"
            "\n**缓解方案**:\n"
            "- 基础设施即代码（Terraform/Pulumi）+ GitOps\n"
            "- 配置中心统一管理\n"
        )

    def _generate_business_risks(self) -> str:
        """生成业务风险 - 根据领域和市场动态生成"""
        category = self._domain_category()
        risks = {
            "education": (
                "\n### 市场竞争风险\n"
                "- 在线教育赛道竞争激烈，头部平台已占据主要市场份额\n"
                "- 免费优质教育内容对付费课程形成替代压力\n"
                "\n**缓解方案**:\n"
                "- 聚焦垂直领域差异化内容\n"
                "- 强化互动学习体验和个性化服务\n"
                "\n### 内容质量风险\n"
                "- 讲师水平参差不齐，低质课程影响平台口碑\n"
                "\n**缓解方案**:\n"
                "- 建立严格的讲师准入和课程审核机制\n"
                "\n### 用户留存风险\n"
                "- 在线学习完课率普遍偏低（行业平均 10-15%）\n"
                "\n**缓解方案**:\n"
                "- 游戏化学习设计 + 打卡激励机制\n"
            ),
            "healthcare": (
                "\n### 监管合规风险\n"
                "- 医疗信息系统需通过等级保护测评\n"
                "- 医疗数据跨境传输受法律严格限制\n"
                "- 远程医疗服务资质审批流程复杂\n"
                "\n**缓解方案**:\n"
                "- 提前规划等保合规建设\n"
                "- 数据本地化存储\n"
                "- 与有资质的医疗机构合作运营\n"
                "\n### 医患信任风险\n"
                "- 患者对线上诊疗的信任度低于面对面就诊\n"
                "\n**缓解方案**:\n"
                "- 展示医生真实资质和患者评价\n"
                "- 明确服务协议和责任边界\n"
                "\n### 推广获客风险\n"
                "- 医院/医生端的推广依赖线下关系，获客成本高\n"
                "\n**缓解方案**:\n"
                "- 从合作医院切入，以 B2B2C 模式降低获客成本\n"
            ),
            "ecommerce": (
                "\n### 市场竞争风险\n"
                "- 电商市场高度集中，新平台获客成本极高\n"
                "- 直播电商和社交电商不断分流传统电商流量\n"
                "\n**缓解方案**:\n"
                "- 聚焦垂直品类或特定人群\n"
                "- 整合社交裂变和内容电商能力\n"
                "\n### 供应链风险\n"
                "- 商品质量不可控导致退货率高\n"
                "- 物流时效不稳定\n"
                "\n**缓解方案**:\n"
                "- 建立商家准入和商品质检机制\n"
                "- 接入多家物流服务商，智能调度\n"
                "\n### 资金安全风险\n"
                "- 需取得支付牌照或与持牌机构合作\n"
                "- 恶意刷单和虚假交易影响数据真实性\n"
                "\n**缓解方案**:\n"
                "- 与持牌支付机构合作，资金托管隔离\n"
                "- 建立反作弊系统\n"
            ),
            "fintech": (
                "\n### 监管合规风险\n"
                "- 金融行业监管政策变化频繁，合规成本持续上升\n"
                "- 需要获取相关金融牌照，审批周期长\n"
                "\n**缓解方案**:\n"
                "- 设立专职合规团队\n"
                "- 优先与持牌金融机构合作\n"
                "\n### 资金安全风险\n"
                "- 系统漏洞可能导致资金损失\n"
                "- 欺诈和洗钱行为的持续威胁\n"
                "\n**缓解方案**:\n"
                "- 多层安全防护 + 定期渗透测试\n"
                "- 实时风控引擎 + AI 异常检测\n"
                "\n### 市场波动风险\n"
                "- 市场剧烈波动可能导致系统负载骤增\n"
                "\n**缓解方案**:\n"
                "- 弹性架构设计 + 自动扩缩容 + 限流降级\n"
            ),
            "recruitment": (
                "\n### 市场竞争风险\n"
                "- 招聘市场头部平台已建立强大的网络效应\n"
                "- 新平台面临双边市场冷启动问题\n"
                "\n**缓解方案**:\n"
                "- 聚焦特定行业或地域的垂直招聘\n"
                "- 通过内容营销吸引求职者和企业\n"
                "\n### 数据隐私风险\n"
                "- 简历数据属于敏感信息，泄露面临法律责任\n"
                "\n**缓解方案**:\n"
                "- 严格的数据访问权限控制和加密存储\n"
                "\n### AI 偏见风险\n"
                "- 简历筛选算法可能存在歧视性偏见\n"
                "\n**缓解方案**:\n"
                "- 定期进行算法公平性审计\n"
                "- 人工审核兜底\n"
                "\n### 用户留存风险\n"
                "- 求职者找到工作后即离开平台\n"
                "\n**缓解方案**:\n"
                "- 拓展职业发展服务，延长用户生命周期\n"
            ),
        }
        if category in risks:
            return risks[category]
        return (
            "\n### 市场竞争风险\n"
            f"- {self.name} 所在赛道可能已有成熟竞品，用户迁移成本高\n"
            "- 大厂入局风险\n"
            "\n**缓解方案**:\n"
            "- 聚焦核心差异化功能\n"
            "- 快速迭代，保持对用户需求的敏锐响应\n"
            "\n### 用户获取与留存风险\n"
            "- 获客成本和渠道不确定\n"
            "- 试用到付费转化路径需要验证\n"
            "\n**缓解方案**:\n"
            "- MVP 阶段验证核心价值假设\n"
            "- 建立用户反馈闭环\n"
            "\n### 合规风险\n"
            f"- {self.platform.upper()} 平台的数据保护法规要求\n"
            "\n**缓解方案**:\n"
            "- 数据收集最小化原则 + 用户明确授权\n"
            "\n### 团队与资源风险\n"
            f"- 技术栈（{self.frontend}/{self.backend}）的人才招聘和培养\n"
            "\n**缓解方案**:\n"
            "- 选择主流技术栈降低招聘难度\n"
            "- 建立 CI/CD 和自动化测试保障质量\n"
        )

    def _generate_dependencies(self) -> str:
        """生成依赖关系"""
        return """
### 外部依赖
- 邮件服务 (SendGrid/阿里云)
- 短信服务 (可选)
- 社交登录 (OAuth2)

### 内部依赖
- 用户服务 (提供用户信息)
- 通知服务 (发送验证消息)
- 审计服务 (记录操作日志)
"""

    def _generate_glossary(self) -> str:
        """生成术语表"""
        return """
| 术语 | 定义 |
|:---|:---|
| JWT | JSON Web Token，用于身份验证的令牌 |
| Session | 用户会话，记录登录状态 |
| 2FA | 双因素认证 |
| RBAC | 基于角色的访问控制 |
| CSRF | 跨站请求伪造 |
"""

    def _generate_references(self) -> str:
        """生成参考资料"""
        return """
### 技术标准
- OWASP Top 10
- RFC 6749 (OAuth 2.0)
- RFC 7519 (JWT)

### 最佳实践
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
"""

    # ========== Architecture Document Methods ==========

    def _generate_auth_module_design(self) -> str:
        """生成认证模块设计"""
        return """
### 认证模块 (Auth Module)

**职责**:
- 用户注册/登录
- Token 签发/验证
- 密码管理

**接口**:
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
POST /api/v1/auth/verify
```

**实现要点**:
- JWT Token 签发使用 RS256
- Refresh Token 存储在 Redis
- 密码使用 bcrypt (cost=10)
"""

    def _generate_user_module_design(self) -> str:
        """生成用户模块设计"""
        return """
### 用户模块 (User Module)

**职责**:
- 用户信息管理
- 权限验证
- 用户状态管理

**接口**:
```
GET /api/v1/users/me
PATCH /api/v1/users/me
PUT /api/v1/users/me/password
GET /api/v1/users/:id
```

**实现要点**:
- 实现乐观锁防止并发修改
- 使用 RBAC 权限模型
- 敏感操作需要二次验证
"""

    def _generate_business_module_design(self) -> str:
        """生成业务模块设计"""
        return """
### 业务模块 (Business Module)

**职责**:
- 核心业务逻辑
- 数据验证
- 业务规则执行

**接口**:
```
GET /api/v1/resources
POST /api/v1/resources
GET /api/v1/resources/:id
PATCH /api/v1/resources/:id
DELETE /api/v1/resources/:id
```

**实现要点**:
- 实现幂等性
- 数据验证使用 Pydantic/Zod
- 审计日志记录所有变更
"""

    def _generate_database_schema(self) -> str:
        """生成数据库设计"""
        return """
### 表结构

**users 表**:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email),
    INDEX idx_username (username)
);
```

**sessions 表**:
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_token (token)
);
```

**audit_logs 表**:
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```
"""

    def _generate_index_strategy(self) -> str:
        """生成索引策略"""
        return """
### 索引设计

| 表 | 索引 | 类型 | 用途 |
|:---|:---|:---|:---|
| users | idx_email | B-tree | 邮箱查询 |
| users | idx_username | B-tree | 用户名查询 |
| sessions | idx_user_id | B-tree | 用户会话查询 |
| sessions | idx_token | B-tree | Token 验证 |
| audit_logs | idx_user_id | B-tree | 用户审计日志 |
| audit_logs | idx_created_at | B-tree | 时间范围查询 |

### 查询优化
- 使用连接池 (pgbouncer)
- 实现查询缓存层
- 慢查询监控 (>100ms)
"""

    def _generate_api_endpoints(self) -> str:
        """生成 API 端点"""
        return """
### API 端点列表

#### 认证相关
```
POST   /api/v1/auth/register        # 用户注册
POST   /api/v1/auth/login           # 用户登录
POST   /api/v1/auth/logout          # 用户登出
POST   /api/v1/auth/refresh         # 刷新 Token
POST   /api/v1/auth/verify          # 验证 Token
POST   /api/v1/auth/forgot-password # 忘记密码
POST   /api/v1/auth/reset-password  # 重置密码
```

#### 用户相关
```
GET    /api/v1/users/me             # 当前用户信息
PATCH  /api/v1/users/me             # 更新用户信息
PUT    /api/v1/users/me/password    # 修改密码
GET    /api/v1/users/:id            # 用户详情 (管理员)
```

#### 业务资源
```
GET    /api/v1/resources            # 资源列表
POST   /api/v1/resources            # 创建资源
GET    /api/v1/resources/:id        # 资源详情
PATCH  /api/v1/resources/:id        # 更新资源
DELETE /api/v1/resources/:id        # 删除资源
```
"""

    def _generate_performance_optimization(self) -> str:
        """生成性能优化"""
        return """
### 后端优化

**数据库优化**:
- 连接池配置 (max_connections=100)
- 查询结果缓存 (Redis)
- 慢查询日志优化

**应用层优化**:
- 异步 I/O 处理
- 请求限流 (100 req/s)
- 响应压缩 (gzip)

**前端优化**:
- 代码分割和懒加载
- 资源 CDN 加速
- 图片优化和缓存

### 监控指标
- API 响应时间 P95 < 200ms
- 数据库查询时间 < 50ms
- 错误率 < 0.1%
"""

    def _generate_tech_comparison(self) -> str:
        """生成技术对比"""
        return """
### 技术选型对比

| 方面 | 选择 | 备选 | 理由 |
|:---|:---|:---|:---|
| 前端框架 | React | Vue, Angular | 生态成熟，组件丰富 |
| 状态管理 | Redux Toolkit | Zustand, Jotai | 标准方案，文档完善 |
| UI 库 | Ant Design | Material-UI | 设计规范完善 |
| 后端框架 | Express | Fastify, Koa | 灵活，中间件丰富 |
| ORM | Prisma | TypeORM, Sequelize | 类型安全，迁移友好 |
| 数据库 | PostgreSQL | MySQL, MongoDB | 功能强大，JSON 支持 |
| 缓存 | Redis | Memcached | 功能丰富，持久化 |
"""

    def _generate_adr(self) -> str:
        """生成架构决策记录"""
        return """
### 架构决策记录 (ADR)

#### ADR-001: 选择 JWT 作为认证方案

**状态**: 已接受

**背景**: 需要无状态的认证机制支持分布式部署

**决策**: 使用 JWT (JSON Web Token) 进行身份验证

**理由**:
- 无状态，易于横向扩展
- 标准化，跨语言支持
- 包含声明，减少数据库查询

**后果**:
- 优点: 无需 Session 存储，支持分布式
- 缺点: Token 无法撤销，需要短过期时间

#### ADR-002: 选择 PostgreSQL 作为主数据库

**状态**: 已接受

**背景**: 需要关系型数据库支持复杂查询

**决策**: 使用 PostgreSQL 作为主数据库

**理由**:
- 功能强大，支持 JSON、全文搜索
- ACID 完整，数据一致性强
- 开源免费，社区活跃

**后果**:
- 优点: 数据完整性好，扩展性强
- 缺点: 配置相对复杂
"""

    def _generate_k8s_config(self) -> str:
        """生成 Kubernetes 配置"""
        return """
### Deployment 配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### ConfigMap 配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "info"
  NODE_ENV: "production"
```

### Secret 配置

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  url: "postgresql://user:pass@host:5432/db"
```

### Ingress 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: app-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 80
```
"""

    # ========== UI/UX Document Methods ==========

    def _generate_navigation_structure(self) -> str:
        """生成导航结构"""
        return """
### 导航结构

**主导航**:
- 首页
- 功能模块
- 设置
- 帮助

**用户菜单**:
- 个人资料
- 账户安全
- 通知设置
- 退出登录

**面包屑**:
- 显示当前页面路径
- 支持快速返回上级
"""

    def _generate_login_page_design(self) -> str:
        """生成登录页设计"""
        return """
### 登录/注册页

**布局**:
- 居中卡片式设计
- 左侧品牌展示
- 右侧表单区域

**表单元素**:
- 邮箱输入框 (带验证)
- 密码输入框 (带显示/隐藏)
- 记住我复选框
- 忘记密码链接
- 登录按钮 (主操作)
- 注册链接 (次要操作)

**交互**:
- 输入框实时验证
- 登录按钮 Loading 状态
- 错误提示显示在表单顶部
"""

    def _generate_list_page_design(self) -> str:
        """生成列表页设计"""
        return """
### 列表页

**布局**:
- 顶部搜索栏
- 左侧筛选器
- 右侧数据列表
- 底部分页器

**列表项**:
- 卡片式展示
- 显示关键信息
- 操作按钮组
- 状态标签

**交互**:
- 下拉加载更多
- 搜索防抖 (300ms)
- 筛选实时更新
"""

    def _generate_detail_page_design(self) -> str:
        """生成详情页设计"""
        return """
### 详情页

**布局**:
- 顶部导航栏 (返回 + 操作)
- 主要信息区
- 相关信息区
- 操作区

**信息层级**:
- 标题 (H1)
- 摘要
- 详细内容
- 元数据

**交互**:
- 编辑/删除操作
- 相关内容推荐
- 快速导航
"""

    def _generate_form_page_design(self) -> str:
        """生成表单页设计"""
        return """
### 表单页

**布局**:
- 左侧表单
- 右侧预览 (可选)
- 底部操作按钮

**表单元素**:
- 必填项标记 (*)
- 字段提示信息
- 实时验证反馈
- 保存/取消按钮

**交互**:
- 表单验证
- 草稿自动保存
- 提交 Loading 状态
"""

    def _generate_base_components(self) -> str:
        """生成基础组件"""
        return """
### 基础组件库

**按钮 (Button)**:
- 主要按钮
- 次要按钮
- 危险按钮
- 文本按钮

**输入框 (Input)**:
- 文本输入
- 密码输入
- 数字输入
- 日期选择

**数据展示 (Data Display)**:
- 表格
- 卡片
- 列表
- 标签

**反馈 (Feedback)**:
- 消息提示
- 对话框
- 加载状态
- 空状态
"""

    def _generate_business_components(self) -> str:
        """生成业务组件"""
        return """
### 业务组件

**用户相关**:
- 用户头像
- 用户卡片
- 用户选择器

**认证相关**:
- 登录表单
- 注册表单
- 密码修改

**内容相关**:
- 内容卡片
- 内容列表
- 内容编辑器
"""

    def _generate_user_journeys_ui(self) -> str:
        """生成用户旅程 UI"""
        return """
### 用户旅程 UI 设计

**旅程 1: 新用户注册**

关键页面:
1. 访问首页 → CTA 按钮 "开始使用"
2. 注册页 → 简洁表单
3. 邮箱验证页 → 清晰提示
4. 登录页 → 自动跳转
5. 首次登录引导 → 功能介绍

**旅程 2: 日常使用**

关键页面:
1. 登录页 → 快速登录
2. 首页 → 功能概览
3. 功能页 → 核心操作
4. 设置页 → 个人配置

**交互要点**:
- 操作反馈及时
- 错误提示清晰
- 加载状态明确
"""

    def _render_ui_intelligence_summary(self, profile: dict) -> str:
        lib = profile.get("primary_library", {})
        stack = profile.get("component_stack", {})
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        lines = [
            f"- **界面定位**: {profile.get('surface', 'N/A')}",
            f"- **信息密度**: {profile.get('information_density', 'N/A')}",
            f"- **行业语气**: {profile.get('industry_tone', 'N/A')}",
            f"- **主视觉气质**: {profile.get('style_direction', {}).get('direction', 'N/A')}",
            f"- **视觉哲学主方向**: {profile.get('design_direction_manifest', {}).get('selected_direction', 'N/A')}",
            f"- **品牌信号**: {' / '.join((profile.get('brand_signal_manifest') or {}).get('tone_descriptors', [])[:3]) or 'N/A'}",
            f"- **字体组合**: {typography.get('heading', 'N/A')} / {typography.get('body', 'N/A')}",
            f"- **配色逻辑**: {palette.get('name', 'N/A')}（主色 {palette.get('primary', 'N/A')} / 强调色 {palette.get('accent', 'N/A')}）",
            f"- **图标系统**: {stack.get('icons', 'N/A')}",
            f"- **首选组件生态**: {lib.get('name', 'N/A')}",
            f"- **表单基线**: {stack.get('form', 'N/A')}",
            f"- **数据展示基线**: {stack.get('table', 'N/A')} / {stack.get('chart', 'N/A')}",
            "",
            "**优先原则**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("benchmark_principles", []))
        lines.extend(["", "**明确不建议默认采用**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:5])
        lines.extend(["", "**设计知识库关键词**:"])
        lines.append("- " + " / ".join(profile.get("knowledge_keywords", [])))
        candidates = profile.get("art_direction_candidates", [])
        if candidates:
            lines.extend(["", "**视觉方向候选**:"])
            for item in candidates[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('name', 'N/A')}**: {item.get('philosophy', 'N/A')}"
                )
        proof_rules = profile.get("proof_composition_rules", {})
        if isinstance(proof_rules, dict) and proof_rules:
            lines.extend(["", "**证明构图纪律**:"])
            lines.append(
                f"- Hero 证明栈: {' / '.join(proof_rules.get('hero_proof_stack', [])[:4]) or 'N/A'}"
            )
            lines.append(
                f"- 信任顺序: {' / '.join(proof_rules.get('trust_sequence', [])[:4]) or 'N/A'}"
            )
        return "\n".join(lines)

    def _render_ui_decision_manifest(self, profile: dict, design_bundle: dict | None = None) -> str:
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        style_direction = profile.get("style_direction", {})
        primary = profile.get("primary_library", {})
        lines = [
            "#### UI 系统冻结决策",
            "",
            "**主方案（默认实现方向）**:",
            f"- **主视觉气质**: {style_direction.get('direction', 'N/A')}",
            f"- **材质/版式逻辑**: {style_direction.get('materials', 'N/A')}",
            f"- **字体组合**: {typography.get('heading', 'N/A')} / {typography.get('body', 'N/A')}",
            f"- **配色逻辑**: {palette.get('name', 'N/A')}（主色 {palette.get('primary', 'N/A')} / 强调色 {palette.get('accent', 'N/A')} / 背景 {palette.get('background', 'N/A')}）",
            f"- **图标系统**: {profile.get('component_stack', {}).get('icons', 'N/A')}",
            f"- **首选组件生态**: {primary.get('name', 'N/A')}",
            f"- **跨平台框架 Playbook**: {(profile.get('framework_playbook') or {}).get('framework', '通用 Web / 原生约束')}",
            f"- **页面定位与密度**: {profile.get('surface', 'N/A')} / {profile.get('information_density', 'N/A')}",
            f"- **叙事方式**: {profile.get('design_direction_manifest', {}).get('narrative_mode', 'N/A')}",
            f"- **视觉张力**: {profile.get('design_direction_manifest', {}).get('visual_tension', 'N/A')}",
            f"- **证明策略**: {profile.get('design_direction_manifest', {}).get('proof_strategy', 'N/A')}",
            "",
            "**设计 token 优先级**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("design_system_priorities", [])[:6])
        lines.extend(["", "**状态矩阵要求**:"])
        lines.extend(f"- {item}" for item in profile.get("state_requirements", [])[:8])

        alternatives = profile.get("alternative_libraries", [])
        if alternatives:
            lines.extend(["", "**备选实现路径**:"])
            for item in alternatives[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(f"- **{item.get('name', 'N/A')}**: {item.get('rationale', 'N/A')}")
        references = profile.get("design_references", [])
        selected_reference = (
            profile.get("selected_design_reference")
            if isinstance(profile.get("selected_design_reference"), dict)
            else {}
        )
        selected_slug = str(selected_reference.get("slug", "")).strip()
        if references:
            lines.extend(["", "**设计参考锚点**:"])
            for item in references[:3]:
                if not isinstance(item, dict):
                    continue
                signals = " / ".join(item.get("signals", [])[:3])
                cautions = "；".join(item.get("cautions", [])[:2])
                selected_tag = (
                    "（已选灵感）" if selected_slug and item.get("slug") == selected_slug else ""
                )
                lines.append(
                    f"- **{item.get('name', 'N/A')}{selected_tag}**: {item.get('rationale', 'N/A')} 参考信号：{signals or 'N/A'}。避免：{cautions or 'N/A'}"
                )

        art_direction_candidates = profile.get("art_direction_candidates", [])
        if art_direction_candidates:
            lines.extend(["", "**视觉方向候选（主方案 + 备选方案）**:"])
            for item in art_direction_candidates[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('name', 'N/A')}**: {item.get('philosophy', 'N/A')} | Hero: {item.get('hero_treatment', 'N/A')} | 避免：{'；'.join(item.get('anti_cliches', [])[:2]) or 'N/A'}"
                )

        brand_signal_manifest = (
            profile.get("brand_signal_manifest")
            if isinstance(profile.get("brand_signal_manifest"), dict)
            else {}
        )
        if brand_signal_manifest:
            lines.extend(["", "**品牌信号与权威感**:"])
            lines.extend(
                f"- {item}" for item in brand_signal_manifest.get("tone_descriptors", [])[:4]
            )
            lines.extend(
                f"- {item}" for item in brand_signal_manifest.get("credibility_devices", [])[:3]
            )

        proof_composition_rules = (
            profile.get("proof_composition_rules")
            if isinstance(profile.get("proof_composition_rules"), dict)
            else {}
        )
        if proof_composition_rules:
            lines.extend(["", "**证明构图规则**:"])
            lines.append(
                f"- **Hero 证明栈**: {' / '.join(proof_composition_rules.get('hero_proof_stack', [])[:4]) or 'N/A'}"
            )
            lines.append(
                f"- **信任顺序**: {' / '.join(proof_composition_rules.get('trust_sequence', [])[:4]) or 'N/A'}"
            )
            lines.extend(
                f"- {item}" for item in proof_composition_rules.get("evidence_priority", [])[:3]
            )
            lines.append(
                f"- **密度规则**: {proof_composition_rules.get('proof_density_rule', 'N/A')}"
            )

        component_craft_requirements = profile.get("component_craft_requirements", [])
        if component_craft_requirements:
            lines.extend(["", "**组件工艺要求**:"])
            lines.extend(f"- {item}" for item in component_craft_requirements[:5])

        layout_tension_rules = profile.get("layout_tension_rules", [])
        if layout_tension_rules:
            lines.extend(["", "**布局张力纪律**:"])
            lines.extend(f"- {item}" for item in layout_tension_rules[:4])

        anti_guardrails = (
            profile.get("anti_ai_slop_guardrails")
            if isinstance(profile.get("anti_ai_slop_guardrails"), dict)
            else {}
        )
        if anti_guardrails:
            lines.extend(["", "**反 AI 味护栏**:"])
            lines.extend(
                f"- {item}" for item in anti_guardrails.get("forbidden_motifs", [])[:4]
            )
            lines.extend(["", "**原创度与工艺检查**:"])
            lines.extend(
                f"- {item}" for item in anti_guardrails.get("originality_checks", [])[:3]
            )
            lines.extend(
                f"- {item}" for item in anti_guardrails.get("craft_checks", [])[:3]
            )

        critique_rubric = profile.get("critique_rubric", [])
        if critique_rubric:
            lines.extend(["", "**设计批评标尺**:"])
            for item in critique_rubric[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('label', 'N/A')}**（阈值 {item.get('pass_threshold', 'N/A')}/10）: {item.get('focus', 'N/A')}"
                )

        lines.extend(["", "**明确不默认采用**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:6])
        lines.extend(
            [
                "",
                "**视觉方案输出要求**:",
                "- 每个关键页面至少提供 2 个视觉方向候选（主方案 + 备选方案），并记录为什么不用另一种方向。",
                "- 开始编码前先冻结图标库、token 策略和页面骨架，不允许边写边猜。",
                "- 主方案必须明确引用 2-3 个设计参考锚点，说明吸收哪些信号、舍弃哪些套路。",
                "- 绝对不允许 emoji 表情作为图标，也不允许在开发过程中用 emoji 充当临时占位；从文档冻结到最终交付都必须使用正式图标库。",
            ]
        )

        design_system = (design_bundle or {}).get("design_system")
        if design_system and getattr(design_system, "aesthetic", None):
            lines.extend(
                [
                    "",
                    "**内置设计系统差异化结论**:",
                    f"- **美学方向**: {design_system.aesthetic.name}",
                    f"- **差异化特征**: {design_system.aesthetic.differentiation}",
                    f"- **Display 字体**: {design_system.aesthetic.typography.display}",
                    f"- **Body 字体**: {design_system.aesthetic.typography.body}",
                ]
            )
        return "\n".join(lines)

    def _render_screen_recipe_manifest(self, analysis: dict, profile: dict) -> str:
        recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        lines = [
            "#### Screen Recipes（页面配方冻结）",
            "",
            "在进入 UI 实现前，必须先冻结每个关键页面的目标、section order、信任模块和状态覆盖，避免页面退化成泛化模板。",
            "",
        ]
        for index, recipe in enumerate(recipes, 1):
            lines.extend(
                [
                    f"**{index}. {recipe.get('label', 'N/A')}**",
                    f"- **目标**: {recipe.get('objective', 'N/A')}",
                    f"- **视觉方向**: {recipe.get('art_direction', 'N/A')}",
                    f"- **叙事方式**: {recipe.get('narrative_mode', 'N/A')}",
                    f"- **视觉张力**: {recipe.get('visual_tension', 'N/A')}",
                    f"- **证明构图**: {' / '.join(recipe.get('proof_composition', [])) or 'N/A'}",
                    f"- **结构顺序**: {' / '.join(recipe.get('section_order', [])) or 'N/A'}",
                    f"- **组件重点**: {' / '.join(recipe.get('component_focus', [])) or 'N/A'}",
                    f"- **信任模块**: {' / '.join(recipe.get('trust_modules', [])) or 'N/A'}",
                    f"- **状态要求**: {' / '.join(recipe.get('required_states', [])) or 'N/A'}",
                    f"- **变体轴**: {' / '.join(recipe.get('variation_axes', [])) or 'N/A'}",
                    f"- **布局张力纪律**: {' / '.join(recipe.get('layout_tension_rules', [])) or 'N/A'}",
                    f"- **反模板禁区**: {' / '.join(recipe.get('anti_cliche_bans', [])) or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _render_design_execution_protocol(self, analysis: dict, profile: dict) -> str:
        recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        context_protocol = self._build_design_context_protocol(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        tweak_strategy = self._build_tweak_strategy(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        verification_handoff = self._build_verification_handoff(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        anti_guardrails = (
            profile.get("anti_ai_slop_guardrails")
            if isinstance(profile.get("anti_ai_slop_guardrails"), dict)
            else {}
        )
        proof_rules = (
            profile.get("proof_composition_rules")
            if isinstance(profile.get("proof_composition_rules"), dict)
            else {}
        )
        component_craft_requirements = (
            profile.get("component_craft_requirements")
            if isinstance(profile.get("component_craft_requirements"), list)
            else []
        )
        layout_tension_rules = (
            profile.get("layout_tension_rules")
            if isinstance(profile.get("layout_tension_rules"), list)
            else []
        )
        lines = [
            "#### Claude-Design 风格执行协议",
            "",
            f"- **上下文目标**: {context_protocol.get('goal', 'N/A')}",
            "- **输入优先级**:",
        ]
        lines.extend(
            f"  - {item}" for item in context_protocol.get("preferred_import_order", [])
        )
        lines.extend(
            [
                "- **GitHub / 代码导入重点**:",
            ]
        )
        lines.extend(
            f"  - {item}" for item in context_protocol.get("github_import_targets", [])
        )
        lines.extend(
            [
                f"- **单一真源规则**: {context_protocol.get('single_source_rule', 'N/A')}",
                f"- **Tweaks 模式**: {tweak_strategy.get('mode', 'N/A')}",
                f"- **Tweaks 默认控件**: {' / '.join(tweak_strategy.get('default_controls', [])) or 'N/A'}",
                f"- **持久化规则**: {tweak_strategy.get('persistence_rule', 'N/A')}",
                "- **验证顺序**:",
            ]
        )
        lines.extend(
            f"  - {item}" for item in verification_handoff.get("verification_order", [])
        )
        lines.extend(
            [
                "- **交付证据**:",
            ]
        )
        lines.extend(
            f"  - {item}" for item in verification_handoff.get("required_artifacts", [])
        )
        if anti_guardrails:
            lines.extend(
                [
                    "- **反 AI 味护栏**:",
                ]
            )
            lines.extend(
                f"  - {item}" for item in anti_guardrails.get("hierarchy_rules", [])[:3]
            )
            lines.extend(
                f"  - {item}" for item in anti_guardrails.get("forbidden_motifs", [])[:3]
            )
        if proof_rules:
            lines.extend(["- **证明构图纪律**:"])
            lines.extend(f"  - {item}" for item in proof_rules.get("hero_proof_stack", [])[:4])
            lines.extend(f"  - {item}" for item in proof_rules.get("evidence_priority", [])[:3])
        if component_craft_requirements:
            lines.extend(["- **组件工艺要求**:"])
            lines.extend(f"  - {item}" for item in component_craft_requirements[:4])
        if layout_tension_rules:
            lines.extend(["- **布局张力纪律**:"])
            lines.extend(f"  - {item}" for item in layout_tension_rules[:4])
        critique_targets = verification_handoff.get("critique_targets", [])
        if critique_targets:
            lines.extend(["- **设计批评维度**:"])
            lines.extend(f"  - {item}" for item in critique_targets)
        return "\n".join(lines)

    def _render_design_token_freeze_output(
        self, profile: dict, design_bundle: dict | None = None
    ) -> str:
        design_system = (design_bundle or {}).get("design_system")
        if not design_system:
            return (
                "#### Design Token 冻结输出\n\n"
                "- 必须冻结 color / typography / spacing / radius / shadow / motion 六类 token。\n"
                "- 实现前先把 token 落到 CSS variables / Tailwind theme / design tokens 文件，禁止边做边写死样式。\n"
            )

        token_rows = [
            (
                "颜色 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.colors.items())[:5]
                ),
            ),
            (
                "字体 token",
                ", ".join(
                    f"{name}={value}"
                    for name, value in list(design_system.typography.items())
                    if value
                ),
            ),
            (
                "间距 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.spacing.items())[:5]
                ),
            ),
            (
                "圆角 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.radius.items())[:4]
                ),
            ),
            (
                "阴影 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.shadows.items())[:4]
                ),
            ),
            (
                "动效 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.animations.items())[:3]
                ),
            ),
        ]

        lines = [
            "#### Design Token 冻结输出",
            "",
            "| 类型 | 冻结结果 |",
            "|:---|:---|",
        ]
        for token_type, value in token_rows:
            lines.append(f"| {token_type} | {value or 'N/A'} |")

        css_preview = (design_bundle or {}).get("css_variables_preview", "")
        if css_preview:
            lines.extend(
                [
                    "",
                    "**CSS Variables 预览**:",
                    "```css",
                    css_preview,
                    "```",
                ]
            )
        tailwind_preview = (design_bundle or {}).get("tailwind_preview", "")
        if tailwind_preview:
            lines.extend(
                [
                    "",
                    "**Tailwind Theme 预览**:",
                    "```json",
                    "\n".join(tailwind_preview.splitlines()[:22]),
                    "```",
                ]
            )
        lines.extend(
            [
                "",
                "**落地要求**:",
                "- 所有页面必须引用这套 token，禁止重新发明第二套颜色和字号。",
                f"- 图标系统固定为 {profile.get('component_stack', {}).get('icons', 'N/A')}，不得再混入 emoji 或临时占位。",
            ]
        )
        return "\n".join(lines)

    def _render_component_ecosystem(self, profile: dict) -> str:
        primary = profile.get("primary_library", {})
        lines = [
            f"#### 首选方案: {primary.get('name', 'N/A')}",
            "",
            f"**适用原因**: {primary.get('rationale', 'N/A')}",
            "",
            "**核心能力**:",
        ]
        lines.extend(f"- {item}" for item in primary.get("strengths", []))
        lines.extend(
            [
                "",
                "**实现注意事项**:",
            ]
        )
        lines.extend(f"- {item}" for item in primary.get("notes", []))
        lines.extend(
            [
                "",
                "#### 配套技术基线",
                "",
                f"- **表单与验证**: {profile.get('component_stack', {}).get('form', 'N/A')}",
                f"- **图表能力**: {profile.get('component_stack', {}).get('chart', 'N/A')}",
                f"- **表格/数据工作区**: {profile.get('component_stack', {}).get('table', 'N/A')}",
                f"- **图标体系**: {profile.get('component_stack', {}).get('icons', 'N/A')}",
                f"- **动效能力**: {profile.get('component_stack', {}).get('motion', 'N/A')}",
            ]
        )

        alternatives = profile.get("alternative_libraries", [])
        if alternatives:
            lines.extend(["", "#### 可选备选方案", ""])
            for item in alternatives:
                lines.append(f"- **{item.get('name', 'N/A')}**: {item.get('rationale', 'N/A')}")
        matrix = profile.get("ui_library_matrix", [])
        if matrix:
            lines.extend(
                [
                    "",
                    "#### 多场景组件库矩阵",
                    "",
                    "| 场景 | 推荐组合 | 设计重点 |",
                    "|:---|:---|:---|",
                ]
            )
            for item in matrix:
                lines.append(
                    f"| {item.get('scene', '-')} | {item.get('libraries', '-')} | {item.get('focus', '-')} |"
                )
        return "\n".join(lines)

    def _render_cross_platform_strategy(self, profile: dict) -> str:
        lines = [
            "- **WEB**: 优先构建高信息密度布局、可检索信息架构和可见状态反馈。",
            "- **H5**: 保留品牌视觉，但减少重型动画，保证首屏性能与转化路径。",
            "- **微信小程序**: 优先贴合平台导航与触控习惯，表单/支付路径保持平台一致性。",
            "- **APP**: 使用原生交互范式（底部导航、手势、反馈节奏），品牌 token 作为统一层。",
            "- **桌面端**: 强化窗口布局、快捷键、菜单栏和本地能力（文件/通知/离线）交互一致性。",
            "",
            "**多端一致性约束**:",
            "- 核心任务路径保持一致（注册、购买、查询、提交），文案与状态语义统一。",
            "- 视觉品牌保持一致（字体、色彩、图形语言），但交互尊重平台差异。",
            "- 同一业务模块必须共享组件契约，避免 Web/H5/小程序/APP/桌面端 逻辑漂移。",
        ]
        framework_playbook = profile.get("framework_playbook") or {}
        if framework_playbook:
            lines.extend(
                [
                    "",
                    f"**跨平台框架深优化 Playbook（{framework_playbook.get('framework', '当前框架')}）**:",
                    f"- **优化焦点**: {framework_playbook.get('focus', 'N/A')}",
                    f"- **适配理由**: {framework_playbook.get('rationale', 'N/A')}",
                    "- **必须优先落实**:",
                ]
            )
            lines.extend(
                f"- {item}" for item in framework_playbook.get("implementation_modules", [])[:4]
            )
            lines.extend(["", "**平台差异/限制**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("platform_constraints", [])[:4]
            )
            lines.extend(["", "**执行护栏**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("execution_guardrails", [])[:3]
            )
            anti_patterns = framework_playbook.get("anti_patterns", [])
            if anti_patterns:
                lines.extend(["", "**框架级反模式**:"])
                lines.extend(f"- {item}" for item in anti_patterns[:3])
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if native_capabilities:
                lines.extend(["", "**原生能力面**:"])
                lines.extend(f"- {item}" for item in native_capabilities[:4])
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if validation_surfaces:
                lines.extend(["", "**必须验收的真实场景**:"])
                lines.extend(f"- {item}" for item in validation_surfaces[:4])
            delivery_evidence = framework_playbook.get("delivery_evidence", [])
            if delivery_evidence:
                lines.extend(["", "**交付证据要求**:"])
                lines.extend(f"- {item}" for item in delivery_evidence[:4])
        keywords = profile.get("knowledge_keywords", [])
        if keywords:
            lines.extend(["", "**设计检索关键词建议**:", "- " + " / ".join(keywords[:10])])
        return "\n".join(lines)

    def _render_ui_quality_gate(self, profile: dict) -> str:
        checks = profile.get("quality_checklist", [])
        if not checks:
            checks = [
                "必须输出 token 并覆盖核心组件",
                "必须覆盖关键状态矩阵",
                "必须通过可访问性与性能审查",
            ]
        lines = ["- [ ] " + check for check in checks]
        lines.extend(
            [
                "",
                "**验收阈值建议**:",
                "- 视觉一致性评分 ≥ 85/100",
                "- 无障碍基础项（对比度/焦点/键盘）通过率 100%",
                "- 首屏可交互时间满足业务基线（Web < 2.5s，H5 < 3s）",
            ]
        )
        critique_rubric = profile.get("critique_rubric", [])
        if critique_rubric:
            lines.extend(["", "**五维设计批评阈值**:"])
            for item in critique_rubric[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- {item.get('label', 'N/A')} ≥ {item.get('pass_threshold', 'N/A')}/10：{item.get('focus', 'N/A')}"
                )
        return "\n".join(lines)

    def _render_ui_execution_workflow(self, profile: dict) -> str:
        primary = profile.get("primary_library", {}).get("name", "UI 组件生态")
        alternatives = profile.get("alternative_libraries", [])
        alternative_names = " / ".join(
            item.get("name", "") for item in alternatives[:3] if isinstance(item, dict)
        )
        return (
            "1. **Intent → 目标建模**: 先明确业务目标、目标用户、转化动作、信任模块，禁止直接生成页面。\n"
            "2. **System → 设计系统编译**: 先冻结 token（颜色/字体/间距/圆角/阴影/动效）和页面骨架。\n"
            f"3. **Build → 组件实现**: 默认采用 `{primary}`，根据场景可选 `{alternative_names or '替代生态'}`。\n"
            "4. **Polish → 商业抛光**: 逐页补齐状态矩阵、文案层级、信任模块、可访问性与性能预算。\n"
            "5. **Proof → 证据沉淀**: 输出截图、关键交互说明、运行验证结果，确保宿主可复现而非一次性生成。\n"
            "\n"
            "**强制要求**: 每个页面至少提供 2 个视觉方向候选（主方案 + 备选方案），并记录取舍原因。"
        )

    def _render_component_implementation_manifest(self, profile: dict) -> str:
        matrix = profile.get("ui_library_matrix", [])
        lines = [
            "| 层级 | 推荐组合 | 目标输出 |",
            "|:---|:---|:---|",
            "| Token 层 | Tailwind theme + CSS variables | 颜色/字体/间距/圆角/阴影/动效统一约束 |",
            "| Primitive 层 | Button/Input/Card/Dialog/Nav 等基础组件 | 所有组件具备状态与可访问性 |",
            "| Pattern 层 | 页面骨架（Hero/Feature/Pricing/FAQ 或 Dashboard） | 信息架构先于视觉样式 |",
            "| Surface 层 | Web/H5/小程序/APP/桌面端 对应实现 | 品牌一致 + 平台交互差异化 |",
        ]
        if matrix:
            lines.extend(["", "**场景映射**:"])
            for row in matrix[:5]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('scene', '-')}: {row.get('libraries', '-')}（重点：{row.get('focus', '-')}）"
                )
        lines.extend(
            [
                "",
                "**落地清单**:",
                "- 至少实现 1 套品牌按钮系统（主按钮/次按钮/幽灵按钮/危险按钮）。",
                "- 至少实现 1 套表单体系（字段/校验/错误态/帮助态/成功态）。",
                "- 至少实现 1 套信息展示体系（卡片/表格/图表/筛选栏/空态）。",
                "- 所有关键组件必须提供 Tailwind class 规范与复用示例。",
            ]
        )
        return "\n".join(lines)

    def _render_page_blueprints(self, profile: dict) -> str:
        lines: list[str] = []
        for blueprint in profile.get("page_blueprints", []):
            lines.extend(
                [
                    f"#### {blueprint.get('page', '未命名页面')}",
                    "",
                    "**推荐模块顺序**:",
                ]
            )
            lines.extend(f"- {section}" for section in blueprint.get("sections", []))
            lines.extend(
                [
                    "",
                    f"**设计重点**: {blueprint.get('focus', '无')}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip()

    def _render_visual_assets_strategy(self, profile: dict) -> str:
        lines = [
            f"- **图标库**: {profile.get('component_stack', {}).get('icons', 'Lucide')}，禁止 emoji 代替功能图标。",
            f"- **图表策略**: {profile.get('component_stack', {}).get('chart', 'Recharts')}，图表先服务决策，再考虑视觉装饰。",
            "- **品牌/合作方 Logo**: 统一使用官方 SVG 或可信来源矢量资产，避免猜测版图形。",
            "- **截图策略**: 对外页面优先使用真实产品截图、流程图或数据示意，而不是空洞插画。",
            "",
            "**优先落地的组件模块**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("component_priorities", []))
        lines.extend(["", "**明确禁止**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:6])
        return "\n".join(lines)

    def _get_design_recommendations(self) -> dict:
        """获取智能设计推荐"""
        try:
            # 导入设计引擎
            import sys
            from pathlib import Path

            # 添加项目根目录到 Python 路径
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from super_dev.design import (
                DesignIntelligenceEngine,
                get_landing_generator,
                get_ux_guide,
            )

            # 分析项目特征
            analysis = self._analyze_project_for_design()

            # 初始化引擎
            design_engine = DesignIntelligenceEngine()
            landing_gen = get_landing_generator()
            ux_guide = get_ux_guide()

            # 获取推荐
            recommendations = {}

            # 1. 风格推荐
            style_query = f"{analysis['style']} {analysis['product_type']} {analysis['industry']}"
            style_results = design_engine.search(style_query, domain="style", max_results=3)
            recommendations["styles"] = style_results.get("results", [])[:3]

            # 2. 配色推荐
            color_query = (
                f"{analysis['industry']} {analysis['product_type']}"
                if analysis["industry"] != "general"
                else analysis["product_type"]
            )
            color_results = design_engine.search(color_query, domain="color", max_results=1)
            recommendations["colors"] = (color_results.get("results", []) or [None])[0]

            # 3. 字体推荐
            font_query = f"{analysis['style']} professional"
            font_results = design_engine.search(font_query, domain="typography", max_results=2)
            recommendations["fonts"] = font_results.get("results", [])[:2]

            # 4. Landing 页面推荐（如果适用）
            if analysis["product_type"] in ["landing", "saas", "ecommerce"]:
                landing_pattern = landing_gen.recommend(
                    product_type=analysis["product_type"],
                    goal="signup",
                    audience="B2C" if analysis["industry"] == "general" else "B2B",
                )
                recommendations["landing"] = (
                    landing_pattern.to_dict()
                    if landing_pattern and hasattr(landing_pattern, "to_dict")
                    else None
                )
            else:
                recommendations["landing"] = None

            # 5. UX 最佳实践
            ux_quick_wins = ux_guide.get_quick_wins(max_results=5)
            ux_tips = []
            for rec in ux_quick_wins:
                guideline = rec.guideline
                ux_tips.append(
                    {
                        "guideline": {
                            "domain": (
                                guideline.domain.value
                                if hasattr(guideline.domain, "value")
                                else str(guideline.domain)
                            ),
                            "topic": guideline.topic,
                            "best_practice": guideline.best_practice,
                            "anti_pattern": guideline.anti_pattern,
                            "impact": guideline.impact,
                            "complexity": guideline.complexity,
                        },
                        "priority": rec.priority,
                        "implementation_effort": rec.implementation_effort,
                        "user_impact": rec.user_impact,
                    }
                )
            recommendations["ux_tips"] = ux_tips

            return recommendations

        except Exception as e:
            # 如果设计引擎失败，返回空推荐
            logging.getLogger(__name__).warning(f"Design engine failed: {e}")
            return {"styles": [], "colors": None, "fonts": [], "landing": None, "ux_tips": []}

    def extract_requirements(self) -> list:
        """从描述提取需求列表"""
        return self.requirement_parser.parse_requirements(self.description)

    def generate_execution_plan(
        self, scenario: str = "0-1", request_mode: str | None = None
    ) -> str:
        """生成分阶段执行路线图（支持 0-1 / 1-N+1）"""
        requirements = self.extract_requirements()
        mode = request_mode or self.requirement_parser.detect_request_mode(self.description)
        phases = self.requirement_parser.build_execution_phases(
            scenario, requirements, request_mode=mode
        )

        lines = [
            f"# {self.name} - 执行路线图",
            "",
            f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> **场景**: {scenario}",
            f"> **请求模式**: {mode}",
            "> **策略**: 先前端可视化，再系统能力闭环",
            "",
            "---",
            "",
            "## 1. 需求范围",
            "",
            "| 模块 | 需求 | 说明 |",
            "|:---|:---|:---|",
        ]

        for req in requirements:
            lines.append(
                f"| {req.get('spec_name', 'core')} | {req.get('req_name', 'n/a')} | {req.get('description', '')} |"
            )

        lines.extend(
            [
                "",
                "## 2. 分阶段计划",
                "",
            ]
        )

        for idx, phase in enumerate(phases, 1):
            lines.extend(
                [
                    f"### Phase {idx}: {phase['title']}",
                    "",
                    f"**目标**: {phase['objective']}",
                    "",
                    "**交付物**:",
                ]
            )
            for item in phase["deliverables"]:
                lines.append(f"- {item}")
            host_playbook = phase.get("host_playbook", [])
            if host_playbook:
                lines.extend(["", "**宿主执行打法**:"])
                for item in host_playbook:
                    lines.append(f"- {item}")
            hard_gates = phase.get("hard_gates", [])
            if hard_gates:
                lines.extend(["", "**阶段硬门禁**:"])
                for item in hard_gates:
                    lines.append(f"- {item}")
            lines.append("")

        lines.extend(
            [
                "## 3. 风险与控制",
                "",
                "- 需求漂移: 每个 Phase 完成后冻结版本并复核。",
                "- 前后端脱节: 在 Phase 2 开始前产出 API 契约草案。",
                "- 质量不足: 每个阶段结束前执行红队审查和质量门禁。",
                "",
                "## 4. 完成定义",
                "",
                "- 所有核心需求存在可验收场景并被实现。",
                "- 前端模块与文档一致，关键链路可演示。",
                "- 质量门禁通过，具备交付上线条件。",
                "",
            ]
        )

        return "\n".join(lines)

    def generate_frontend_blueprint(self) -> str:
        """生成前端先行的模块蓝图"""
        requirements = self.extract_requirements()
        modules = self.requirement_parser.build_frontend_modules(requirements)

        lines = [
            f"# {self.name} - 前端蓝图",
            "",
            f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> **前端框架**: {self.frontend}",
            "> **设计重点**: 先可视化业务流程，再补齐系统深度能力",
            "",
            "---",
            "",
            "## 1. 体验目标",
            "",
            "- 一次进入即可理解产品价值和关键流程。",
            "- 文档和执行状态可追踪，避免信息散落。",
            "- 关键任务路径操作链路最短、反馈明确。",
            "",
            "## 2. 模块拆分",
            "",
        ]

        for index, module in enumerate(modules, 1):
            lines.extend(
                [
                    f"### {index}. {module['name']}",
                    "",
                    f"**目标**: {module['goal']}",
                    "",
                    "**核心元素**:",
                ]
            )
            for element in module["core_elements"]:
                lines.append(f"- {element}")
            lines.append("")

        lines.extend(
            [
                "## 3. 开发顺序",
                "",
                "1. 先实现 `需求总览面板` + `文档工作台`，确保信息结构完整。",
                "2. 再实现业务模块页面，覆盖每条核心需求的主路径。",
                "3. 最后统一交互细节、动效和可访问性。",
                "",
                "## 4. 前后端契约建议",
                "",
                "- 页面只消费稳定 DTO，避免直接绑定数据库结构。",
                "- API 响应必须包含状态码、业务码和可读错误信息。",
                "- 对列表页统一分页/筛选参数结构，减少重复实现。",
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_market_context(self) -> str:
        return (
            f"- 当前需求聚焦于“{self.description}”，在立项阶段必须先完成同类产品研究，避免凭空定义需求。\n"
            "- 研究输出至少覆盖：目标用户、核心功能组合、关键任务路径、页面层级、商业化表达与差异化方向。\n"
            "- PRD 不只描述“要做什么”，还需要明确“为什么这样做”以及“相较同类产品借鉴了什么、舍弃了什么”。\n"
            "- 对标研究更应关注流程、交互密度、信任表达和交付成熟度，而不是只模仿视觉表面。"
        )

    def _generate_research_evidence_brief(self) -> str:
        summary = self.knowledge_summary or {}
        evidence = summary.get("evidence_distribution", {}) if isinstance(summary, dict) else {}
        confidence = (
            summary.get("research_confidence", "baseline")
            if isinstance(summary, dict)
            else "baseline"
        )
        benchmark = summary.get("benchmark_products", []) if isinstance(summary, dict) else []
        sources = summary.get("primary_sources", []) if isinstance(summary, dict) else []
        lines = [
            f"- **研究可信度**: {confidence}",
            f"- **官方来源**: {evidence.get('official', 0)} 条 / **行业来源**: {evidence.get('industry', 0)} 条 / **社区来源**: {evidence.get('community', 0)} 条",
            "- **研究要求**: 所有关键决策需可追溯到联网研究证据与本地知识约束。",
            "",
            "**对标产品摘要**:",
        ]
        if isinstance(benchmark, list) and benchmark:
            lines.extend(f"- {item}" for item in benchmark[:4])
        else:
            lines.append("- 当前未命中有效对标产品，需由宿主继续联网补齐。")
        lines.extend(["", "**核心来源域名**:"])
        if isinstance(sources, list) and sources:
            for item in sources[:5]:
                if isinstance(item, list | tuple) and len(item) >= 2:
                    lines.append(f"- {item[0]}: {item[1]} 次引用")
        else:
            lines.append("- 暂无可统计域名数据")
        return "\n".join(lines)

    def _generate_knowledge_constraints_section(self) -> str:
        """生成知识约束章节（从 KnowledgePusher 推送的数据）"""
        summary = self.knowledge_summary or {}
        if not isinstance(summary, dict):
            return ""
        constraints = summary.get("pushed_constraints", [])
        antipatterns = summary.get("pushed_antipatterns", [])
        knowledge_files = summary.get("pushed_knowledge_files", [])
        if not constraints and not antipatterns and not knowledge_files:
            return ""

        lines = ["### 知识库硬约束（自动注入）", ""]
        if constraints:
            lines.append("**必须遵循：**")
            for c in constraints[:15]:
                lines.append(f"- {c}")
            lines.append("")
        if antipatterns:
            lines.append("**必须避免：**")
            for a in antipatterns[:10]:
                lines.append(f"- {a}")
            lines.append("")
        if knowledge_files:
            lines.append("**参考知识文件：**")
            for f in knowledge_files[:10]:
                if isinstance(f, dict):
                    lines.append(f"- `{f.get('path', f.get('file', str(f)))}`")
                else:
                    lines.append(f"- `{f}`")
            lines.append("")
        return "\n".join(lines)

    def _generate_solution_tradeoffs(self) -> str:
        summary = self.knowledge_summary or {}
        options = summary.get("implementation_options", []) if isinstance(summary, dict) else []
        lines = [
            "| 方案 | 适用场景 | 核心策略 | 关键权衡 |",
            "|:---|:---|:---|:---|",
        ]
        if isinstance(options, list) and options:
            for option in options:
                if not isinstance(option, dict):
                    continue
                lines.append(
                    f"| {option.get('name', '-')} | {option.get('fit', '-')} | {option.get('strategy', '-')} | {option.get('tradeoff', '-')} |"
                )
        else:
            lines.append("| 稳健商业方案 | 企业级交付 | 组件标准化 + 质量门禁 | 前期规范成本更高 |")
            lines.append(
                "| 快速验证方案 | MVP 上线 | 核心路径最小化 + 埋点先行 | 视觉与扩展能力后补 |"
            )
            lines.append(
                "| 品牌差异化方案 | 竞争市场 | 品牌 token + 叙事页面 + 转化实验 | 设计与内容投入更高 |"
            )
        return "\n".join(lines)

    def _generate_decision_ledger(self) -> str:
        return (
            "| 决策主题 | 选择结论 | 核心证据 | 放弃项 | 后续验证 |\n"
            "|:---|:---|:---|:---|:---|\n"
            "| 研究策略 | 证据分层（official/industry/community） | 联网来源可信度统计 | 无证据直接结论 | 在每次迭代复核证据比例 |\n"
            f"| 交付范围 | 围绕“{self.description}”优先主任务路径 | 需求澄清问题与用户分层矩阵 | 全量功能一次性上线 | 通过 MVP 指标验证范围是否过宽 |\n"
            "| 设计策略 | 先信息架构与组件状态矩阵，再视觉抛光 | UI/UX 质量门禁章节 | 先做视觉特效 | 通过 UI Review 与转化数据复盘 |\n"
            "| 工程策略 | 前端先行并保留可演示任务流 | 执行路线图与前端蓝图 | 只交静态壳子 | 通过运行验证和质量门禁确认 |"
        )

    def _generate_user_to_pro_protocol(self) -> str:
        return (
            "| 阶段 | 用户输入 | Agent 专业动作 | 产出结果 |\n"
            "|:---|:---|:---|:---|\n"
            "| 需求表达 | 一句话描述目标 | 顺位思考 + 联网研究 + 竞品拆解 | 研究报告与问题澄清清单 |\n"
            "| 方案定义 | 无技术细节也可继续 | 自动生成 PRD/UIUX/架构并给出方案取舍 | 三文档与决策账本 |\n"
            "| 实现执行 | 用户无需指定技术实现 | 按技术栈规范生成代码、测试、验证链路 | 可运行版本与验证证据 |\n"
            "| 交付上线 | 用户仅确认业务目标 | 质量门禁、演练、回滚、证据包自动化 | 可审计交付与上线准备 |\n"
            "\n"
            "- **核心原则**: 同一套交互对所有用户生效，用户负责业务目标，Agent 负责专业流程与交付闭环。"
        )

    def _generate_clarification_questions(self) -> str:
        mode = self._request_mode()
        if mode == "bugfix":
            return (
                "1. **实际症状**：当前报错、异常现象或错误行为是什么？\n"
                "2. **复现条件**：在哪个页面、接口、角色或环境下可以稳定复现？\n"
                "3. **期望行为**：修复后应该恢复成什么结果，是否有历史正确行为可对照？\n"
                "4. **影响范围**：受影响的是单一路径还是多个模块，是否涉及数据修复或兼容性问题？\n"
                "5. **回归风险**：这次修复最需要补哪类验证，避免把别的链路一起带坏？"
            )
        return (
            "1. **核心用户**：第一批真正会使用这个产品的人是谁？\n"
            "2. **主任务路径**：用户进入后最重要的一条路径是什么，需要几步完成？\n"
            "3. **范围边界**：MVP 必须交付什么，哪些能力明确不进入第一阶段？\n"
            "4. **依赖约束**：是否依赖现有系统、第三方服务、数据源、权限体系或组织流程？\n"
            "5. **成功标准**：上线后用什么结果判断这次开发是有效的？"
        )

    def _generate_user_segment_matrix(self) -> str:
        return (
            "| 用户分层 | 主要目标 | 关键诉求 | 设计重点 |\n"
            "|:---|:---|:---|:---|\n"
            "| 核心操作者 | 高效完成主流程 | 速度、稳定性、可追踪 | 缩短操作路径、强化状态反馈 |\n"
            "| 协作/审批角色 | 快速理解上下文并做决策 | 信息完整、风险可见 | 强化摘要、差异对比、审批反馈 |\n"
            "| 管理角色 | 掌握全局进度与质量 | 透明度、可审计性 | 仪表盘、过滤、导出、审计记录 |\n"
            "| 新用户/访客 | 理解产品价值与使用方式 | 上手门槛低、信任感强 | 首屏表达清晰、引导明确、案例可信 |"
        )

    def _generate_scope_priorities(self) -> str:
        return (
            "1. **P0 必做**: 主业务流程、关键页面、权限与状态闭环、错误处理、基础审计与测试。\n"
            "2. **P1 应做**: 搜索筛选、批量操作、运营/管理视图、埋点、性能优化、可观测性。\n"
            "3. **P2 可延后**: 高级自动化、复杂可视化、生态集成、个性化配置。\n"
            "4. **明确不在 MVP**: 任何没有用户价值验证、没有交付必要性的炫技功能不进入第一阶段。"
        )

    def _generate_edge_cases(self) -> str:
        return (
            "- 权限不足时必须提供可读解释与引导动作，而不是静默失败。\n"
            "- 异步任务、长流程、批量操作必须可见进度、可取消、可重试。\n"
            "- 网络异常、数据为空、外部依赖不可用时，页面需保留结构稳定和恢复路径。\n"
            "- 表单提交、发布、删除、审批等高风险动作必须有二次确认、撤回或审计记录。"
        )

    def _generate_delivery_requirements(self) -> str:
        return (
            "- 所有核心页面必须覆盖正常态、加载态、空态、错误态、禁用态和权限态。\n"
            "- 交付包必须可审计，文档、Spec、任务状态、测试结果与发布配置需要相互对应。\n"
            "- 前端先行，但不能只做静态壳子，至少要能演示真实任务流和关键反馈。\n"
            "- UI 必须达到商业产品完成度：有品牌感、信息层级、组件一致性和可访问性。"
        )

    def _generate_acceptance_matrix(self) -> str:
        return (
            "| 验收维度 | 必达标准 | 验证方式 |\n"
            "|:---|:---|:---|\n"
            "| 核心业务流程 | 主路径可从开始走到完成，且反馈明确 | 手测 + E2E |\n"
            "| 权限与审计 | 角色权限生效，关键动作可追踪 | 用例测试 + 日志核验 |\n"
            "| UI/UX 完成度 | 页面层级清晰、状态齐全、品牌感一致 | 设计走查 |\n"
            "| 工程质量 | Lint/Test/Build 通过 | CI + 本地验证 |\n"
            "| 上线准备 | 配置、监控、回滚说明齐备 | 发布检查单 |"
        )

    def _generate_business_kpis(self) -> str:
        return (
            "- **激活指标**: 首次完成核心流程的用户占比。\n"
            "- **效率指标**: 用户完成关键任务所需时间、步骤数与中断率。\n"
            "- **质量指标**: 错误率、异常恢复率、关键页面交互成功率。\n"
            "- **经营指标**: 试用到付费、线索到转化、复购或活跃留存。"
        )

    def _generate_launch_dependencies(self) -> str:
        return (
            "- 研究报告、PRD、架构、UIUX 与 tasks.md 版本一致。\n"
            "- 测试、质量门禁、发布配置、监控告警和回滚策略已验证。\n"
            "- 数据结构与迁移脚本已评审，关键风险有兜底方案。\n"
            "- 核心路径可现场演示，不依赖口头解释才能成立。"
        )

    def _generate_architecture_fit(self) -> str:
        return (
            "- 架构设计必须回到研究报告和 PRD 的关键流程，不能脱离实际需求做空泛微服务模板。\n"
            "- 技术选型应优先服务于当前阶段交付速度、稳定性、可维护性和团队认知成本。\n"
            "- 对高频路径优先做低延迟设计，对高风险路径优先做权限、审计、幂等和回滚设计。\n"
            "- 前后端契约应围绕页面与任务流定义，而不是围绕数据库表结构反推。"
        )

    def _generate_architecture_decision_matrix(self) -> str:
        return (
            "| 决策维度 | 主方案 | 备选方案 | 选型依据 |\n"
            "|:---|:---|:---|:---|\n"
            "| 服务形态 | 模块化单体 / 分层服务 | 早期微服务 | 优先交付速度与可维护性，避免过度拆分 |\n"
            f"| 前端生态 | {self._get_ui_library()} + Token 系统 | 纯组件库默认样式 | 必须满足商业级品牌表达与一致性 |\n"
            "| 数据策略 | 主库 + 缓存 + 搜索 | 单库直连 | 兼顾读写性能、查询能力与扩展空间 |\n"
            "| 可观测性 | 指标 + 日志 + 链路追踪 | 仅日志 | 发布演练和问题定位需要完整证据链 |\n"
            "| 发布策略 | 灰度/回滚预案 | 一次性全量发布 | 降低高风险变更对线上影响 |\n"
            "\n"
            "- 任何架构决策若无法映射到研究证据、业务目标和交付约束，则不应进入首版实现。"
        )

    def _generate_architecture_ledger(self) -> str:
        return (
            "| 架构决策 | 结论 | 备选方案 | 风险预算与补偿 |\n"
            "|:---|:---|:---|:---|\n"
            "| 服务边界 | 以业务域拆分并保持契约稳定 | 单体全集成 | 用 DTO + 版本策略降低耦合风险 |\n"
            "| 数据一致性 | 核心写路径幂等 + 审计 | 仅依赖数据库约束 | 失败补偿与手工修复入口 |\n"
            "| 发布策略 | 灰度 + 回滚预案 | 一次性全量 | 发布前演练与证据包校验 |\n"
            "| 可观测性 | 指标/日志/追踪一体 | 仅日志 | 高风险路径强制埋点与告警阈值 |\n"
        )

    def _generate_agent_delivery_pipeline(self) -> str:
        return (
            "1. **Intent Intake**: 接收用户自然语言目标并抽取业务意图与边界。\n"
            "2. **Research Engine**: 联网研究 + 本地知识命中 + 竞品能力矩阵。\n"
            "3. **Tri-Doc Compiler**: 自动生成 PRD、UIUX、架构并建立决策账本。\n"
            "4. **Stack Router**: 按 Web/H5/小程序/APP 路由到对应组件生态（含 TDesign 小程序）。\n"
            "5. **Execution & Verification**: 生成实现方案、测试方案与质量门禁结果。\n"
            "6. **Delivery Proof**: 输出可审计交付包、发布演练与回滚策略。"
        )

    def _generate_sequence_diagram(self) -> str:
        mode = self._request_mode()
        if mode == "bugfix":
            return (
                "```mermaid\n"
                "sequenceDiagram\n"
                '    participant U as "User"\n'
                '    participant H as "Host AI"\n'
                '    participant R as "Research & Docs"\n'
                '    participant C as "Code / Tests"\n'
                "    U->>H: 提交缺陷修复需求\n"
                "    H->>R: 先复现问题并更新补丁文档\n"
                "    R-->>U: 输出轻量 PRD / Architecture / UIUX 补丁说明\n"
                "    U->>H: 确认修复边界\n"
                "    H->>C: 实施定点修复与回归测试\n"
                "    C-->>U: 返回修复结果、验证证据与剩余风险\n"
                "```\n"
            )
        return (
            "```mermaid\n"
            "sequenceDiagram\n"
            '    participant U as "User"\n'
            '    participant F as "Frontend"\n'
            '    participant A as "API Gateway"\n'
            '    participant S as "Service"\n'
            '    participant D as "Database"\n'
            "    U->>F: 发起核心业务操作\n"
            "    F->>A: 提交请求与上下文\n"
            "    A->>S: 路由、鉴权、校验\n"
            "    S->>D: 读取 / 写入业务数据\n"
            "    D-->>S: 返回结果\n"
            "    S-->>A: 产出稳定 DTO 与状态\n"
            "    A-->>F: 返回业务结果\n"
            "    F-->>U: 展示反馈、下一步动作与状态变化\n"
            "```\n"
        )

    def _generate_domain_boundaries(self) -> str:
        return (
            "- 认证授权、用户与组织、核心业务流程、通知与异步任务、审计日志应作为明确边界拆分。\n"
            "- 每个边界需要定义输入输出 DTO、权限要求、状态流转与失败补偿策略。\n"
            "- 共享能力只沉淀稳定基础设施，不把业务细节塞进“common utils”。\n"
            "- 高变化模块优先与低变化模块解耦，降低后续迭代成本。"
        )

    def _generate_integration_contracts(self) -> str:
        return (
            "- API 必须有版本策略，避免前端页面被无意破坏。\n"
            "- 外部依赖需定义超时、重试、降级、熔断与错误映射规则。\n"
            "- DTO 应稳定、可验证、可测试，避免把数据库内部字段直接暴露给前端。\n"
            "- Webhook、消息、回调类接口要有幂等键与审计记录。"
        )

    def _generate_failure_strategy(self) -> str:
        return (
            "- 关键写操作采用幂等机制，防止重复提交。\n"
            "- 第三方依赖异常时优先降级核心功能而不是整体瘫痪。\n"
            "- 任务流中断后应支持恢复、补偿或人工处理入口。\n"
            "- 前端异常要给出可执行的下一步，不允许只显示技术报错。"
        )

    def _generate_audit_strategy(self) -> str:
        return (
            "- 对登录、权限变更、关键数据修改、批量操作、发布/审批动作保留审计轨迹。\n"
            "- 日志结构需支持按用户、资源、请求链路、时间窗口检索。\n"
            "- 前后端共享 trace/request id，确保问题能跨层定位。\n"
            "- 质量门禁输出应沉淀为可回溯产物，而不是一次性终端信息。"
        )

    def _generate_release_strategy(self) -> str:
        return (
            "- 使用分环境发布策略，至少区分本地、测试、预发布、生产。\n"
            "- 高风险变更建议灰度、特性开关或分批发布。\n"
            "- 发布说明需包含数据库变更、兼容性影响、回滚步骤与监控关注项。\n"
            "- 回滚方案必须在上线前验证，不接受“出问题再看”。"
        )

    def _generate_ui_strategy(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- UI 的首要目标不是“好看”，而是让用户快速理解产品价值、任务状态与下一步动作。\n"
            "- 所有页面都应体现商业级完成度：品牌感、层级感、信息密度、状态完整度与信任表达。\n"
            f"- 当前项目应以“{profile.get('surface', 'Web')}”为第一交付目标，并采用 {profile.get('information_density', '中等')} 密度策略组织信息。\n"
            "- 先解决页面结构、CTA、数据层级和组件一致性，再打磨视觉细节。\n"
            "- 对外页面强调品牌、信任与转化，对内页面强调效率、清晰度和低认知负担。"
        )

    def _generate_visual_direction(self) -> str:
        return (
            "- 视觉方向应基于产品定位建立明确气质：可信、克制、现代，而不是依赖泛滥渐变制造“高级感”。\n"
            "- 优先使用有辨识度的字体组合、清晰的字号节奏、稳定的留白和克制的强调色。\n"
            "- 图形、图标、插画、卡片阴影和分隔线应来自同一视觉系统，避免拼装感。\n"
            "- 页面应在首屏就体现主价值、核心证据、下一步 CTA 和品牌记忆点。"
        )

    def _generate_layout_system(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- 桌面端使用明确的 12 栏或等价栅格系统，控制内容宽度与节奏。\n"
            f"- 当前项目采用 {profile.get('information_density', '中等')} 信息密度，按页面目标决定视觉节奏与操作密度。\n"
            "- 控制不同页面的密度等级，避免同一产品里既过空又过挤。\n"
            "- 侧边栏、头部、主体区、辅助区、底部应有稳定布局规则。"
        )

    def _generate_component_state_matrix(self) -> str:
        return (
            "| 组件类型 | 必备状态 | 说明 |\n"
            "|:---|:---|:---|\n"
            "| 按钮 | 默认 / hover / active / disabled / loading | 强调动作反馈与禁用原因 |\n"
            "| 输入控件 | 默认 / focus / error / success / readonly | 错误文案与引导动作要清晰 |\n"
            "| 列表与表格 | loading / empty / normal / error / bulk-selected | 支持筛选、排序、批量动作 |\n"
            "| 卡片与模块 | default / hover / selected / warning / permission-limited | 用于强调优先级、状态变化和权限边界 |\n"
            "| 弹窗抽屉 | enter / exit / confirm / pending / failure | 需要防误操作和恢复路径 |"
        )

    def _generate_motion_system(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- 动效只服务于层级切换、状态反馈、焦点引导，不用作廉价装饰。\n"
            f"- 推荐实现基线: {profile.get('component_stack', {}).get('motion', 'framer-motion')}。\n"
            "- 列表进入、面板展开、Toast 反馈、模态切换应采用统一时长与缓动曲线。\n"
            "- 对关键提交动作提供即时反馈，对长操作提供进度提示。\n"
            "- 必须兼容 reduced-motion，必要时降级为无动画但保留状态反馈。"
        )

    def _generate_trust_and_conversion_rules(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        lines = [
            "- 对外页面应优先展示价值主张、能力边界、案例证明、客户证言、数据指标或合规信息。",
            "- CTA 不应只在 hero 区出现，关键转化节点要有连续但不过度打扰的引导。",
            "- 对内工作台则应突出当前任务、风险提示、审批状态、待办优先级和最近操作。",
            "- 所有高价值页面都应体现“用户为什么相信并继续使用这个产品”。",
            "",
            "**当前项目必须优先出现的信任/转化模块**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("trust_modules", [])[:8])
        return "\n".join(lines)
