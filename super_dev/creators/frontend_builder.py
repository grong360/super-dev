"""
前端实施蓝图生成器 - 先冻结宿主可执行的前端参考面
"""

from __future__ import annotations

import html
import json
from pathlib import Path


class FrontendScaffoldBuilder:
    """生成宿主可直接评审和继续实现的前端实施参考页"""

    def __init__(
        self,
        project_dir: Path,
        name: str,
        description: str,
        frontend: str = "react",
    ):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.description = description
        self.frontend = frontend

    def generate(
        self,
        requirements: list[dict],
        phases: list[dict],
        docs: dict,
    ) -> dict:
        """写入前端实施参考文件并返回路径"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)

        html_path = output_dir / "index.html"
        css_path = output_dir / "styles.css"
        tokens_path = output_dir / "design-tokens.css"
        js_path = output_dir / "app.js"
        ui_contract = self._load_ui_contract()

        html_path.write_text(self._build_html(ui_contract), encoding="utf-8")
        css_path.write_text(self._build_css(ui_contract), encoding="utf-8")
        tokens_path.write_text(
            ui_contract.get("design_tokens", {}).get("css_variables") or ":root {}\n",
            encoding="utf-8",
        )
        js_path.write_text(
            self._build_js(requirements, phases, docs, ui_contract), encoding="utf-8"
        )

        result = {
            "html": str(html_path),
            "css": str(css_path),
            "tokens": str(tokens_path),
            "js": str(js_path),
        }
        framework_scaffold = self._generate_framework_scaffold(ui_contract)
        if framework_scaffold:
            result["framework_scaffold"] = framework_scaffold
        return result

    def _resolve_direction_profile(self, ui_contract: dict) -> dict:
        art_direction_candidates = (
            ui_contract.get("art_direction_candidates")
            if isinstance(ui_contract.get("art_direction_candidates"), list)
            else []
        )
        design_direction_manifest = (
            ui_contract.get("design_direction_manifest")
            if isinstance(ui_contract.get("design_direction_manifest"), dict)
            else {}
        )
        anti_slop_guardrails = (
            ui_contract.get("anti_ai_slop_guardrails")
            if isinstance(ui_contract.get("anti_ai_slop_guardrails"), dict)
            else {}
        )
        primary = art_direction_candidates[0] if art_direction_candidates else {}
        direction_id = (
            design_direction_manifest.get("direction_id")
            or primary.get("id")
            or "modern-commercial"
        )
        selected = next(
            (item for item in art_direction_candidates if item.get("id") == direction_id),
            primary,
        )
        anti_cliches = list(selected.get("anti_cliches", [])[:3]) or list(
            anti_slop_guardrails.get("candidate_anti_cliches", [])[:3]
        )
        return {
            "direction_id": direction_id,
            "name": (
                design_direction_manifest.get("selected_direction")
                or selected.get("name")
                or "Frozen UI Contract"
            ),
            "philosophy": (
                design_direction_manifest.get("philosophy")
                or selected.get("philosophy")
                or "先锁定视觉哲学，再组织层级、证明和交互。"
            ),
            "hero_treatment": (
                design_direction_manifest.get("hero_treatment")
                or selected.get("hero_treatment")
                or "首屏同时承担价值主张、证据和行动入口。"
            ),
            "proof_strategy": (
                design_direction_manifest.get("proof_strategy")
                or selected.get("proof_strategy")
                or "优先使用截图、案例、数据和流程证明。"
            ),
            "visual_tension": (
                design_direction_manifest.get("visual_tension")
                or selected.get("visual_tension")
                or "通过排版、留白和重点色建立张力。"
            ),
            "narrative_mode": (
                design_direction_manifest.get("narrative_mode")
                or selected.get("narrative_mode")
                or "先理解价值，再进入证明和能力模块。"
            ),
            "palette_strategy": (
                design_direction_manifest.get("palette_strategy")
                or selected.get("palette_strategy")
                or "先控制颜色数量，再决定强调色位置。"
            ),
            "why_this_direction": design_direction_manifest.get("why_this_direction") or "",
            "reference_anchor": design_direction_manifest.get("reference_anchor") or "",
            "anti_cliches": anti_cliches,
            "tweak_axes": list(selected.get("tweak_axes", [])[:4]),
            "density": (
                ui_contract.get("information_density")
                or design_direction_manifest.get("density_tempo")
                or "medium"
            ),
        }

    def _framework_ui_profile(self, ui_contract: dict) -> dict:
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        generated = ui_contract.get("generated_design_system", {})
        radius = generated.get("radius", {}) if isinstance(generated, dict) else {}
        return {
            "colors": {
                "primary": palette.get("primary", "#0f7cfa"),
                "accent": palette.get("accent", "#f65f22"),
                "background": palette.get("background", "#f5f8ff"),
                "foreground": palette.get("text", "#172133"),
                "border": palette.get("border", "#dfe7f3"),
                "muted": self._lighten(palette.get("background", "#f5f8ff"), 0.04),
                "muted_foreground": self._darken(palette.get("text", "#172133"), 0.62),
                "secondary": self._lighten(palette.get("primary", "#0f7cfa"), 0.45),
                "ring": palette.get("primary", "#0f7cfa"),
            },
            "fonts": {
                "sans": typography.get("body", "Inter"),
                "mono": "JetBrains Mono",
            },
            "radius": {
                "lg": radius.get("lg", "18px"),
                "md": radius.get("md", "12px"),
                "sm": radius.get("sm", "8px"),
            },
        }

    def _generate_framework_scaffold(self, ui_contract: dict) -> dict | None:
        frontend = str(self.frontend or "react").strip().lower()
        if frontend in {"next", "nextjs"}:
            from super_dev.creators.nextjs_scaffold import NextjsScaffoldGenerator

            files = NextjsScaffoldGenerator().generate(
                self.project_dir,
                self.name,
                ui_profile=self._framework_ui_profile(ui_contract),
            )
            root = self.project_dir / "output" / "nextjs-scaffold"
            return {
                "kind": "nextjs-app-router",
                "root": str(root),
                "files": [str(path) for path in files],
            }
        if frontend in {"vue", "vue3", "nuxt", "vue-vite"}:
            files = self.generate_vue3_project()
            root = self.project_dir / "output" / "frontend-vue3"
            return {"kind": "vue3-vite", "root": str(root), "files": list(files.values())}
        if frontend in {"angular"}:
            files = self.generate_angular_project()
            root = self.project_dir / "output" / "frontend-angular"
            return {"kind": "angular", "root": str(root), "files": list(files.values())}
        if frontend in {"svelte", "sveltekit"}:
            files = self.generate_svelte_project()
            root = self.project_dir / "output" / "frontend-svelte"
            return {"kind": "sveltekit", "root": str(root), "files": list(files.values())}
        if frontend in {"react", "react-vite", "remix", "gatsby"}:
            files = self.generate_react_vite_project(ui_contract)
            root = self.project_dir / "output" / "frontend-react"
            kind = "react-vite"
            if frontend == "remix":
                kind = "remix-family-preview"
            elif frontend == "gatsby":
                kind = "gatsby-family-preview"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"expo", "react-native"}:
            files = self.generate_expo_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-expo"
            kind = "expo-managed" if frontend == "expo" else "react-native-expo"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"flutter"}:
            files = self.generate_flutter_project(ui_contract)
            root = self.project_dir / "output" / "frontend-flutter"
            return {"kind": "flutter", "root": str(root), "files": list(files.values())}
        if frontend in {"uni-app", "uniapp", "taro"}:
            files = self.generate_miniapp_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-miniapp"
            kind = "uni-app" if frontend in {"uni-app", "uniapp"} else "taro-family-preview"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"tauri", "electron", "wails"}:
            files = self.generate_desktop_shell_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-desktop-shell"
            return {"kind": f"{frontend}-desktop-shell", "root": str(root), "files": list(files.values())}
        if frontend in {"ionic", "capacitor"}:
            files = self.generate_hybrid_shell_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-hybrid-shell"
            return {"kind": f"{frontend}-hybrid-shell", "root": str(root), "files": list(files.values())}
        return None

    def _build_html(self, ui_contract: dict) -> str:
        typography = ui_contract.get("typography_preset", {})
        style_direction = ui_contract.get("style_direction", {})
        framework_playbook = (
            ui_contract.get("framework_playbook")
            if isinstance(ui_contract.get("framework_playbook"), dict)
            else {}
        )
        component_stack = (
            ui_contract.get("component_stack", {})
            if isinstance(ui_contract.get("component_stack"), dict)
            else {}
        )
        icon_system = (
            ui_contract.get("icon_system")
            or component_stack.get("icon")
            or component_stack.get("icons")
            or "Lucide Icons"
        )
        preference = ui_contract.get("ui_library_preference", {})
        primary_library = (
            preference.get("final_selected")
            or ui_contract.get("primary_library", {}).get("name")
            or preference.get("preferred")
            or "shadcn/ui + Radix UI + Tailwind CSS"
        )
        screen_recipes = (
            ui_contract.get("screen_recipes")
            if isinstance(ui_contract.get("screen_recipes"), list)
            else []
        )
        direction_profile = self._resolve_direction_profile(ui_contract)
        primary_recipe = screen_recipes[0] if screen_recipes else {}
        verification_handoff = (
            ui_contract.get("verification_handoff")
            if isinstance(ui_contract.get("verification_handoff"), dict)
            else {}
        )
        selected_reference = (
            ui_contract.get("selected_design_reference")
            if isinstance(ui_contract.get("selected_design_reference"), dict)
            else {}
        )
        reference_name = selected_reference.get("name") or "Frozen UI Contract"
        hero_panel_title = primary_recipe.get("label") or "Design Execution Blueprint"
        hero_panel_copy = (
            primary_recipe.get("objective")
            or "把页面配方、设计上下文、Tweaks 和交付证据锁进同一条 UI 闭环。"
        )
        trust_module_count = len(primary_recipe.get("trust_modules", []))
        verification_count = len(verification_handoff.get("verification_order", []))
        direction_name = direction_profile["name"]
        anti_cliche_markup = "\n".join(
            f'              <li>{html.escape(item)}</li>'
            for item in direction_profile["anti_cliches"][:3]
        )
        axis_markup = "\n".join(
            f'              <span>{html.escape(item)}</span>'
            for item in direction_profile["tweak_axes"][:4]
        )
        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(self.name)} · Frontend Blueprint</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{self._build_google_fonts_url(typography)}" rel="stylesheet" />
    <link rel="stylesheet" href="./design-tokens.css" />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body data-direction="{html.escape(str(direction_profile['direction_id']))}" data-density="{html.escape(str(direction_profile['density']))}">
    <div class="bg-layer"></div>
    <main class="shell">
      <nav class="topbar">
        <div class="brand">
          <span class="brand-mark">SD</span>
          <span>{html.escape(self.name)}</span>
        </div>
        <div class="top-actions">
          <a href="#trust">客户证明</a>
          <a href="#recipe-map">页面配方</a>
          <a href="#design-directions">视觉方向</a>
          <a href="#workspace">交付路径</a>
          <a class="primary-link" href="#doc-links">查看文档</a>
        </div>
      </nav>

      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="eyebrow">Super Dev Frontend First Delivery</p>
          <h1 id="hero-title">{html.escape(self.name)}</h1>
          <p class="summary">{html.escape(self.description)}</p>
          <p class="style-direction">{html.escape(style_direction.get('direction', ''))}</p>
          <div class="meta">
            <span>Framework: {html.escape(self.frontend)}</span>
            <span>Mode: 需求文档驱动</span>
            <span>Icons: {html.escape(icon_system)}</span>
            <span>UI: {html.escape(primary_library)}</span>
            <span>Direction: {html.escape(str(direction_name))}</span>
            <span>Reference: {html.escape(reference_name)}</span>
          </div>
          <div class="hero-actions">
            <a class="button button-primary" href="#doc-links">打开核心文档</a>
            <a class="button button-secondary" href="#recipe-map">查看页面配方</a>
          </div>
          <ul class="trust-strip">
            <li>商业级流程治理</li>
            <li>研究报告与 UI/UX 规范先行</li>
            <li>Screen recipes / Tweaks / Runtime evidence 全链闭环</li>
          </ul>
        </div>
        <div class="hero-panel" aria-label="产品演示摘要">
          <div class="panel-card">
            <p class="panel-label">Preview Snapshot</p>
            <h2>{html.escape(hero_panel_title)}</h2>
            <p>{html.escape(hero_panel_copy)}</p>
            <div class="metric-grid">
              <div><strong>{len(screen_recipes) or 1}</strong><span>页面配方</span></div>
              <div><strong>{trust_module_count or 3}</strong><span>信任模块</span></div>
              <div><strong>{verification_count or 4}</strong><span>验证节点</span></div>
            </div>
          </div>
        </div>
      </section>

      <section class="card direction-stage" aria-labelledby="direction-stage-title">
        <div class="direction-stage-copy">
          <p class="eyebrow">Signature Art Direction</p>
          <h2 id="direction-stage-title">{html.escape(direction_name)}</h2>
          <p class="direction-philosophy">{html.escape(str(direction_profile["philosophy"]))}</p>
          <p class="direction-why">{html.escape(str(direction_profile["why_this_direction"]))}</p>
          <div class="direction-signals">
            <span>Hero: {html.escape(str(direction_profile["hero_treatment"]))}</span>
            <span>Proof: {html.escape(str(direction_profile["proof_strategy"]))}</span>
            <span>Tension: {html.escape(str(direction_profile["visual_tension"]))}</span>
          </div>
          <div class="direction-axes">
{axis_markup or '              <span>信息密度</span>'}
          </div>
        </div>
        <div class="direction-stage-proof">
          <article class="signature-proof">
            <p class="panel-label">Narrative Mode</p>
            <h3>{html.escape(str(direction_profile["narrative_mode"]))}</h3>
            <p>{html.escape(str(direction_profile["palette_strategy"]))}</p>
          </article>
          <article class="signature-proof anti-cliche-proof">
            <p class="panel-label">Anti-Cliche Guardrails</p>
            <ul class="delivery-list">
{anti_cliche_markup or '              <li>禁止流行 AI 模板化视觉。</li>'}
            </ul>
          </article>
        </div>
      </section>

      <section id="trust" class="card trust-band">
        <div class="section-head">
          <h2>可信交付信号</h2>
          <p>不是只生成页面，而是确保需求、规范、状态、质量和上线准备全部可追踪。</p>
        </div>
        <div class="trust-grid">
          <article class="trust-item">
            <h3>Research First</h3>
            <p>先研究同类产品、页面结构与商业表达，再写文档和代码。</p>
          </article>
          <article class="trust-item">
            <h3>UI/UX Baseline</h3>
            <p>先冻结组件生态、设计 token、页面骨架和状态矩阵，再实现页面。</p>
          </article>
          <article class="trust-item">
            <h3>Quality Gate</h3>
            <p>红队审查、UI 审查、质量门禁和发布演练共同保证可交付性。</p>
          </article>
        </div>
      </section>

      <section class="card doc-hub">
        <div class="section-head">
          <h2>核心文档</h2>
          <p>先完成文档，再以文档驱动实现。</p>
        </div>
        <div id="doc-links" class="doc-grid"></div>
      </section>

      <section id="workspace" class="card split">
        <div>
          <div class="section-head">
            <h2>需求模块</h2>
            <p>按需求生成页面和能力模块。</p>
          </div>
          <div id="requirements" class="chips"></div>
        </div>
        <div>
          <div class="section-head">
            <h2>执行路线</h2>
            <p>从 0-1 到 1-N+1 的阶段推进。</p>
          </div>
          <ol id="timeline" class="timeline"></ol>
        </div>
      </section>

      <section id="recipe-map" class="card">
        <div class="section-head">
          <h2>页面配方</h2>
          <p>先冻结关键页面的结构顺序、组件重点、信任模块和状态要求，再开始写页面。</p>
        </div>
        <div id="recipe-grid" class="recipe-grid"></div>
      </section>

      <section id="design-directions" class="card split">
        <div>
          <div class="section-head">
            <h2>视觉方向候选</h2>
            <p>先在 2-3 个明确设计哲学之间做选择，而不是直接输出一版模板页。</p>
          </div>
          <div id="direction-grid" class="recipe-grid"></div>
        </div>
        <div>
          <div class="section-head">
            <h2>反 AI 味护栏</h2>
            <p>禁止科技 cliché、聊天壳模板和无意义炫技，用层级、证据和工艺建立高级感。</p>
          </div>
          <ul id="anti-slop-list" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Critique Rubric</p>
            <ul id="critique-rubric" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card split preview-proof">
        <div>
          <div class="section-head">
            <h2>页面骨架</h2>
            <p>对外页面要有价值表达、信任证明、能力模块和明确 CTA，内部工作台要有导航、状态与操作路径。</p>
          </div>
          <ul class="delivery-list">
            <li>Hero + 价值主张 + CTA</li>
            <li>真实截图/演示摘要</li>
            <li>案例 / 安全 / FAQ / 证明</li>
            <li>功能分区与下一步转化入口</li>
          </ul>
        </div>
        <div>
          <div class="section-head">
            <h2>交付证明</h2>
            <p>适用于官网、产品页、工作台和商业级 MVP 验证。</p>
          </div>
          <div class="proof-card">
            <strong>Case Study Ready</strong>
            <p>支持把页面、文档、任务状态和质量报告一起用于内部评审或商业验证。</p>
            <a class="inline-link" href="#faq">查看 FAQ</a>
          </div>
        </div>
      </section>

      <section class="card split execution-protocol">
        <div>
          <div class="section-head">
            <h2>上下文与 Tweaks 协议</h2>
            <p>优先吸收真实代码与设计上下文，用单一主原型承载变体，而不是分叉出多份页面。</p>
          </div>
          <ul id="context-protocol" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Tweaks</p>
            <ul id="tweak-controls" class="delivery-list"></ul>
          </div>
        </div>
        <div>
          <div class="section-head">
            <h2>验证与交付</h2>
            <p>把 preview、runtime、UI review 和最终交付证据放进同一条前端闭环，而不是只看页面能否打开。</p>
          </div>
          <ul id="verification-steps" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Handoff</p>
            <ul id="handoff-artifacts" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card framework-playbook" {'' if framework_playbook else 'hidden'}>
        <div class="section-head">
          <h2>跨平台框架执行护栏</h2>
          <p>跨平台项目要先冻结框架专项能力、平台差异、验收面和交付证据，再进入实现。</p>
        </div>
        <div class="split">
          <div>
            <p class="eyebrow">Framework Playbook</p>
            <h3>{html.escape(str(framework_playbook.get("framework") or "跨平台框架"))}</h3>
            <ul id="framework-modules" class="delivery-list"></ul>
          </div>
          <div>
            <p class="eyebrow">Native & Validation</p>
            <ul id="framework-native" class="delivery-list"></ul>
            <ul id="framework-validation" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="section-head">
          <h2>交付清单</h2>
          <p>前端先行，随后进入系统化交付。</p>
        </div>
        <ul class="delivery-list">
          <li>阶段 1: PRD / 架构 / UIUX 文档</li>
          <li>阶段 2: 前端实施蓝图与核心页面</li>
          <li>阶段 3: 后端与数据库能力</li>
          <li>阶段 4: 联调、测试、质量门禁</li>
          <li>阶段 5: 发布、监控与迭代</li>
        </ul>
      </section>

      <section id="faq" class="card">
        <div class="section-head">
          <h2>FAQ</h2>
          <p>快速回答“为什么不是直接写代码”的问题。</p>
        </div>
        <div class="faq-list">
          <article>
            <h3>为什么先做文档？</h3>
            <p>因为商业级交付不只是把页面写出来，而是让需求、架构、UI/UX 和质量口径可审计。</p>
          </article>
          <article>
            <h3>为什么要看质量门禁？</h3>
            <p>为了尽早识别风险、状态缺失、UI 模板化和交付短板，而不是等上线前才返工。</p>
          </article>
        </div>
      </section>
    </main>
    <script src="./app.js"></script>
  </body>
</html>
"""

    def _build_css(self, ui_contract: dict) -> str:
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        primary = palette.get("primary", "#0f7cfa")
        accent = palette.get("accent", "#f65f22")
        background = palette.get("background", "#f5f8ff")
        text = palette.get("text", "#172133")
        border = palette.get("border", "#dfe7f3")
        generated = ui_contract.get("generated_design_system", {})
        radius = generated.get("radius", {}).get("lg", "18px")
        shadow = generated.get("shadows", {}).get("lg", "0 18px 40px rgba(13, 33, 57, 0.09)")
        heading_font = typography.get("heading", "Manrope")
        body_font = typography.get("body", "Source Sans 3")
        template = """
:root {
  --bg-0: __BG0__;
  --bg-1: __BG1__;
  --surface: rgba(255, 255, 255, 0.86);
  --surface-strong: rgba(255, 255, 255, 0.96);
  --panel-surface: rgba(255, 255, 255, 0.98);
  --stroke: __STROKE__;
  --text: __TEXT__;
  --muted: __MUTED__;
  --primary: __PRIMARY__;
  --accent: __ACCENT__;
  --radius: __RADIUS__;
  --shadow: __SHADOW__;
  --shell-width: 1120px;
  --hero-grid-left: 1.4fr;
  --hero-grid-right: 0.9fr;
  --hero-padding: 28px 28px 26px;
  --hero-surface: var(--surface);
  --hero-outline: none;
  --hero-radius: var(--radius);
  --section-gap: 18px;
  --recipe-surface: __PRIMARY_ALPHA_06__;
  --chip-surface: __ACCENT_ALPHA_10__;
  --panel-highlight: __PRIMARY_ALPHA_08__;
  --direction-stage-surface: rgba(255, 255, 255, 0.92);
  --display-letter-spacing: -0.03em;
  --font-heading: "__HEADING_FONT__", sans-serif;
  --font-body: "__BODY_FONT__", system-ui, sans-serif;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  color: var(--text);
  font-family: var(--font-body);
  background: var(--bg-0);
}

.bg-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle at 8% 10%, __PRIMARY_ALPHA_20__, transparent 35%),
    radial-gradient(circle at 85% 12%, __ACCENT_ALPHA_20__, transparent 28%),
    radial-gradient(circle at 50% 100%, __PRIMARY_ALPHA_12__, transparent 34%);
}

.shell {
  max-width: var(--shell-width);
  margin: 0 auto;
  padding: 40px 20px 64px;
  position: relative;
  z-index: 1;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: #172133;
  color: #ffffff;
  font-size: 13px;
}

.top-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.top-actions a {
  color: var(--text);
  text-decoration: none;
  font-weight: 700;
}

.top-actions .primary-link {
  color: var(--primary);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, var(--hero-grid-left)) minmax(280px, var(--hero-grid-right));
  gap: var(--section-gap);
  padding: var(--hero-padding);
  border: 1px solid var(--stroke);
  border-radius: var(--hero-radius);
  background: var(--hero-surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(6px);
  outline: var(--hero-outline);
  outline-offset: -1px;
}

.eyebrow {
  margin: 0;
  color: var(--primary);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 12px;
}

.hero h1 {
  margin: 10px 0 8px;
  font-family: var(--font-heading);
  font-size: clamp(28px, 4vw, 48px);
  letter-spacing: var(--display-letter-spacing);
}

.summary {
  margin: 0 0 14px;
  color: var(--muted);
}

.style-direction {
  margin: 0 0 14px;
  color: var(--text);
  opacity: 0.8;
  max-width: 58ch;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 18px 0 18px;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 12px;
  font-weight: 800;
  text-decoration: none;
}

.button-primary {
  background: var(--primary);
  color: #ffffff;
}

.button-secondary {
  background: __PRIMARY_ALPHA_08__;
  color: __PRIMARY_DARK_62__;
}

.meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.meta span {
  border-radius: 999px;
  padding: 8px 12px;
  background: __PRIMARY_ALPHA_08__;
  color: __PRIMARY_DARK_62__;
  font-size: 13px;
  font-weight: 700;
}

.trust-strip {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.trust-strip li {
  color: var(--muted);
}

.hero-panel {
  display: flex;
}

.panel-card,
.proof-card {
  width: 100%;
  border-radius: 18px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: var(--panel-surface);
  padding: 20px;
}

.direction-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.9fr);
  gap: var(--section-gap);
  background: var(--direction-stage-surface);
}

.direction-stage-copy {
  display: grid;
  align-content: start;
  gap: 14px;
}

.direction-stage-copy h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 38px);
  font-family: var(--font-heading);
  letter-spacing: var(--display-letter-spacing);
}

.direction-philosophy,
.direction-why {
  margin: 0;
  color: var(--muted);
  max-width: 60ch;
}

.direction-signals,
.direction-axes {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.direction-signals span,
.direction-axes span {
  border-radius: 999px;
  padding: 8px 12px;
  background: var(--panel-highlight);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.direction-stage-proof {
  display: grid;
  gap: 12px;
}

.signature-proof {
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: var(--panel-surface);
}

.panel-label {
  margin: 0 0 8px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-card h2,
.proof-card strong {
  display: block;
  margin: 0 0 8px;
  font-family: var(--font-heading);
}

.metric-grid,
.trust-grid,
.recipe-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-grid div,
.trust-item,
.recipe-card {
  border-radius: 14px;
  padding: 14px;
  background: var(--recipe-surface);
}

.metric-grid strong {
  display: block;
  font-size: 24px;
  font-family: var(--font-heading);
}

.metric-grid span {
  color: var(--muted);
  font-size: 13px;
}

.recipe-card h3 {
  margin: 0 0 10px;
  font-family: var(--font-heading);
}

.recipe-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.recipe-meta span {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.card {
  margin-top: 18px;
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 22px;
}

.section-head h2 {
  margin: 0;
  font-size: 22px;
  font-family: var(--font-heading);
}

.section-head p {
  margin: 6px 0 16px;
  color: var(--muted);
}

.doc-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.doc-item {
  display: block;
  text-decoration: none;
  color: inherit;
  border: 1px solid rgba(23, 33, 51, 0.1);
  border-radius: 14px;
  padding: 14px;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
  background: #ffffff;
}

.doc-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(16, 34, 61, 0.12);
}

.doc-item b {
  display: block;
  margin-bottom: 8px;
}

.split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 13px;
  background: var(--chip-surface);
  color: __ACCENT_DARK_60__;
  border: 1px solid __ACCENT_ALPHA_14__;
}

.timeline {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
}

.timeline li {
  padding-left: 4px;
}

.timeline b {
  display: block;
}

.timeline p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.delivery-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.inline-link {
  color: var(--primary);
  font-weight: 700;
  text-decoration: none;
}

.sub-card {
  margin-top: 14px;
  border-radius: 16px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: rgba(255, 255, 255, 0.78);
  padding: 16px;
}

.faq-list {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.faq-list article {
  border-radius: 14px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  padding: 16px;
  background: #ffffff;
}

.faq-list h3 {
  margin: 0 0 8px;
  font-size: 17px;
}

.faq-list p,
.trust-item p,
.proof-card p {
  margin: 0;
  color: var(--muted);
}

body[data-direction="editorial-swiss"] {
  --shell-width: 1180px;
  --hero-grid-left: 1.68fr;
  --hero-grid-right: 0.78fr;
  --hero-padding: 34px 34px 30px;
  --hero-radius: 14px;
  --hero-outline: 1px solid rgba(23, 33, 51, 0.12);
  --recipe-surface: rgba(23, 33, 51, 0.035);
  --panel-highlight: rgba(23, 33, 51, 0.045);
  --display-letter-spacing: -0.05em;
}

body[data-direction="editorial-swiss"] .topbar {
  margin-bottom: 28px;
}

body[data-direction="editorial-swiss"] .hero h1,
body[data-direction="editorial-swiss"] .direction-stage-copy h2 {
  text-transform: uppercase;
  max-width: 12ch;
}

body[data-direction="editorial-swiss"] .trust-strip {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

body[data-direction="precision-workspace"] {
  --shell-width: 1240px;
  --hero-grid-left: 1fr;
  --hero-grid-right: 1.08fr;
  --hero-padding: 24px;
  --hero-radius: 16px;
  --hero-surface: rgba(246, 249, 255, 0.92);
  --direction-stage-surface: rgba(246, 249, 255, 0.94);
  --recipe-surface: rgba(15, 124, 250, 0.045);
}

body[data-direction="precision-workspace"] .metric-grid,
body[data-direction="precision-workspace"] .recipe-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

body[data-direction="warm-trust"] {
  --hero-grid-left: 1.26fr;
  --hero-grid-right: 0.94fr;
  --hero-radius: 28px;
  --radius: 24px;
  --hero-surface: linear-gradient(135deg, rgba(255, 250, 245, 0.96), rgba(255, 255, 255, 0.92));
  --direction-stage-surface: rgba(255, 251, 247, 0.95);
  --recipe-surface: rgba(246, 95, 34, 0.07);
  --chip-surface: rgba(246, 95, 34, 0.12);
}

body[data-direction="cinematic-product"] {
  --bg-0: #081019;
  --surface: rgba(10, 17, 26, 0.82);
  --panel-surface: rgba(11, 20, 31, 0.92);
  --text: #eef4fb;
  --muted: rgba(238, 244, 251, 0.72);
  --stroke: rgba(140, 168, 199, 0.18);
  --hero-grid-left: 1.3fr;
  --hero-grid-right: 0.98fr;
  --hero-padding: 32px 32px 30px;
  --hero-radius: 24px;
  --hero-surface: linear-gradient(145deg, rgba(9, 18, 30, 0.96), rgba(12, 28, 43, 0.82));
  --direction-stage-surface: linear-gradient(145deg, rgba(9, 18, 30, 0.92), rgba(12, 23, 37, 0.82));
  --recipe-surface: rgba(255, 255, 255, 0.05);
  --panel-highlight: rgba(15, 124, 250, 0.16);
  --display-letter-spacing: -0.045em;
}

body[data-direction="cinematic-product"] .brand-mark {
  background: linear-gradient(145deg, var(--accent), var(--primary));
  color: #081019;
}

body[data-direction="quiet-luxury"] {
  --hero-grid-left: 1.18fr;
  --hero-grid-right: 0.84fr;
  --section-gap: 24px;
  --hero-padding: 38px 38px 34px;
  --hero-radius: 26px;
  --radius: 20px;
  --direction-stage-surface: rgba(252, 249, 244, 0.96);
  --recipe-surface: rgba(23, 33, 51, 0.03);
}

body[data-direction="playful-modular"] {
  --hero-grid-left: 1.24fr;
  --hero-grid-right: 0.92fr;
  --hero-radius: 32px;
  --radius: 28px;
  --direction-stage-surface: rgba(247, 251, 255, 0.96);
  --recipe-surface: rgba(15, 124, 250, 0.06);
  --chip-surface: rgba(246, 95, 34, 0.14);
}

body[data-direction="playful-modular"] .recipe-card,
body[data-direction="playful-modular"] .trust-item,
body[data-direction="playful-modular"] .faq-list article {
  border-radius: 22px;
}

@media (max-width: 860px) {
  .topbar,
  .hero,
  .direction-stage {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: flex-start;
  }

  .doc-grid {
    grid-template-columns: 1fr;
  }

  .split {
    grid-template-columns: 1fr;
  }

  .metric-grid,
  .trust-grid,
  .recipe-grid,
  .faq-list {
    grid-template-columns: 1fr;
  }
}
"""
        return (
            template.replace("__BG0__", self._lighten(background, 0.08))
            .replace("__BG1__", self._lighten(accent, 0.9))
            .replace("__STROKE__", self._alpha(border, 0.78))
            .replace("__TEXT__", text)
            .replace("__MUTED__", self._darken(text, 0.62))
            .replace("__PRIMARY__", primary)
            .replace("__ACCENT__", accent)
            .replace("__RADIUS__", radius)
            .replace("__SHADOW__", shadow)
            .replace("__HEADING_FONT__", heading_font)
            .replace("__BODY_FONT__", body_font)
            .replace("__PRIMARY_ALPHA_20__", self._alpha(primary, 0.2))
            .replace("__ACCENT_ALPHA_20__", self._alpha(accent, 0.2))
            .replace("__PRIMARY_ALPHA_12__", self._alpha(primary, 0.12))
            .replace("__PRIMARY_ALPHA_08__", self._alpha(primary, 0.08))
            .replace("__PRIMARY_ALPHA_06__", self._alpha(primary, 0.06))
            .replace("__PRIMARY_DARK_62__", self._darken(primary, 0.62))
            .replace("__ACCENT_ALPHA_10__", self._alpha(accent, 0.1))
            .replace("__ACCENT_ALPHA_14__", self._alpha(accent, 0.14))
            .replace("__ACCENT_DARK_60__", self._darken(accent, 0.6))
        )

    def _build_js(
        self, requirements: list[dict], phases: list[dict], docs: dict, ui_contract: dict
    ) -> str:
        payload = {
            "requirements": requirements,
            "phases": phases,
            "docs": docs,
            "ui_contract": {
                "ui_library_preference": ui_contract.get("ui_library_preference"),
                "icon_system": (
                    ui_contract.get("icon_system")
                    or (
                        ui_contract.get("component_stack", {}).get("icon")
                        if isinstance(ui_contract.get("component_stack"), dict)
                        else None
                    )
                    or (
                        ui_contract.get("component_stack", {}).get("icons")
                        if isinstance(ui_contract.get("component_stack"), dict)
                        else None
                    )
                ),
                "surface": ui_contract.get("surface"),
                "information_density": ui_contract.get("information_density"),
                "framework_playbook": ui_contract.get("framework_playbook"),
                "art_direction_candidates": ui_contract.get("art_direction_candidates"),
                "design_direction_manifest": ui_contract.get("design_direction_manifest"),
                "anti_ai_slop_guardrails": ui_contract.get("anti_ai_slop_guardrails"),
                "critique_rubric": ui_contract.get("critique_rubric"),
                "screen_recipes": ui_contract.get("screen_recipes"),
                "design_context_protocol": ui_contract.get("design_context_protocol"),
                "tweak_strategy": ui_contract.get("tweak_strategy"),
                "verification_handoff": ui_contract.get("verification_handoff"),
            },
        }
        payload_str = json.dumps(payload, ensure_ascii=False, indent=2)
        payload_str = payload_str.replace("</", "<\\/")
        return f"""const DATA = {payload_str};

const docContainer = document.getElementById("doc-links");
const reqContainer = document.getElementById("requirements");
const timelineContainer = document.getElementById("timeline");
const frameworkModules = document.getElementById("framework-modules");
const frameworkNative = document.getElementById("framework-native");
const frameworkValidation = document.getElementById("framework-validation");
const recipeGrid = document.getElementById("recipe-grid");
const directionGrid = document.getElementById("direction-grid");
const antiSlopList = document.getElementById("anti-slop-list");
const critiqueRubric = document.getElementById("critique-rubric");
const contextProtocol = document.getElementById("context-protocol");
const tweakControls = document.getElementById("tweak-controls");
const verificationSteps = document.getElementById("verification-steps");
const handoffArtifacts = document.getElementById("handoff-artifacts");

const docList = [
  {{ title: "PRD 文档", desc: "产品目标、需求边界、验收标准", path: DATA.docs.prd }},
  {{ title: "架构文档", desc: "模块划分、接口契约、部署策略", path: DATA.docs.architecture }},
  {{ title: "UI/UX 文档", desc: "视觉系统、交互规则、页面结构", path: DATA.docs.uiux }},
  {{ title: "执行路线图", desc: "0-1 与 1-N+1 的分阶段推进", path: DATA.docs.plan }},
  {{ title: "前端蓝图", desc: "前端模块拆分与先行交付策略", path: DATA.docs.frontend_blueprint }},
];

for (const doc of docList) {{
  if (!doc.path) continue;
  const link = document.createElement("a");
  link.className = "doc-item";
  link.href = relativePath(doc.path);
  link.target = "_blank";
  link.rel = "noreferrer";
  link.innerHTML = `<b>${{doc.title}}</b><span>${{doc.desc}}</span>`;
  docContainer.appendChild(link);
}}

for (const req of DATA.requirements) {{
  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = `${{req.spec_name}} · ${{req.req_name}}`;
  reqContainer.appendChild(chip);
}}

for (const phase of DATA.phases) {{
  const li = document.createElement("li");
  li.innerHTML = `<b>${{phase.title}}</b><p>${{phase.objective}}</p>`;
  timelineContainer.appendChild(li);
}}

for (const recipe of DATA.ui_contract.screen_recipes || []) {{
  if (!recipeGrid) break;
  const article = document.createElement("article");
  article.className = "recipe-card";
  const sections = (recipe.section_order || []).slice(0, 4).join(" / ");
  const trustCount = (recipe.trust_modules || []).length;
  const stateCount = (recipe.required_states || []).length;
  article.innerHTML = `
    <h3>${{recipe.label || "Screen Recipe"}}</h3>
    <p>${{recipe.objective || ""}}</p>
    <p><b>方向</b>: ${{recipe.art_direction || "-"}}</p>
    <p><b>结构</b>: ${{sections || "-"}}</p>
    <div class="recipe-meta">
      <span>${{recipe.surface || "-"}}</span>
      <span>Trust ${{trustCount}}</span>
      <span>States ${{stateCount}}</span>
    </div>
  `;
  recipeGrid.appendChild(article);
}}

for (const direction of DATA.ui_contract.art_direction_candidates || []) {{
  if (!directionGrid) break;
  const article = document.createElement("article");
  article.className = "recipe-card";
  article.innerHTML = `
    <h3>${{direction.name || "Art Direction"}}</h3>
    <p>${{direction.philosophy || ""}}</p>
    <p><b>Hero</b>: ${{direction.hero_treatment || "-"}}</p>
    <p><b>Proof</b>: ${{direction.proof_strategy || "-"}}</p>
  `;
  directionGrid.appendChild(article);
}}

for (const item of DATA.ui_contract.anti_ai_slop_guardrails?.forbidden_motifs || []) {{
  if (!antiSlopList) break;
  const li = document.createElement("li");
  li.textContent = item;
  antiSlopList.appendChild(li);
}}

for (const item of DATA.ui_contract.critique_rubric || []) {{
  if (!critiqueRubric) break;
  const li = document.createElement("li");
  li.textContent = `${{item.label || item.dimension || "Criterion"}} ≥ ${{item.pass_threshold || "-"}}/10`;
  critiqueRubric.appendChild(li);
}}

for (const item of DATA.ui_contract.design_context_protocol?.preferred_import_order || []) {{
  if (!contextProtocol) break;
  const li = document.createElement("li");
  li.textContent = item;
  contextProtocol.appendChild(li);
}}

for (const item of DATA.ui_contract.tweak_strategy?.default_controls || []) {{
  if (!tweakControls) break;
  const li = document.createElement("li");
  li.textContent = item;
  tweakControls.appendChild(li);
}}

for (const item of DATA.ui_contract.verification_handoff?.verification_order || []) {{
  if (!verificationSteps) break;
  const li = document.createElement("li");
  li.textContent = item;
  verificationSteps.appendChild(li);
}}

for (const item of DATA.ui_contract.verification_handoff?.required_artifacts || []) {{
  if (!handoffArtifacts) break;
  const li = document.createElement("li");
  li.textContent = item;
  handoffArtifacts.appendChild(li);
}}

const frameworkPlaybook = DATA.ui_contract.framework_playbook || null;
if (frameworkPlaybook && frameworkModules && frameworkNative && frameworkValidation) {{
  for (const item of frameworkPlaybook.implementation_modules || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkModules.appendChild(li);
  }}
  for (const item of frameworkPlaybook.native_capabilities || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkNative.appendChild(li);
  }}
  for (const item of frameworkPlaybook.validation_surfaces || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkValidation.appendChild(li);
  }}
}}

function relativePath(path) {{
  if (!path) return "#";
  const normalized = String(path).replace(/\\\\/g, "/");
  const marker = "/output/";
  const index = normalized.lastIndexOf(marker);
  if (index >= 0) {{
    return ".." + normalized.slice(index + marker.length - 1);
  }}
  return "#";
}}
"""

    def _load_ui_contract(self) -> dict:
        contract_path = self.project_dir / "output" / f"{self.name}-ui-contract.json"
        if contract_path.exists():
            try:
                return json.loads(contract_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        from super_dev.creators.document_generator import DocumentGenerator

        generator = DocumentGenerator(
            name=self.name,
            description=self.description,
            platform="web",
            frontend=self.frontend,
            backend="node",
        )
        contract = generator.generate_ui_contract()
        if isinstance(contract, dict):
            contract.setdefault(
                "_artifact_meta",
                {
                    "generated_by": "FrontendScaffoldBuilder._load_ui_contract",
                    "reason": "ui-contract artifact was missing and has been materialized for downstream stages",
                },
            )
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return contract

    def _build_google_fonts_url(self, typography: dict) -> str:
        families: list[str] = []
        for font in (typography.get("heading"), typography.get("body")):
            token = str(font or "").strip()
            if not token:
                continue
            family = token.replace(" ", "+")
            query = f"family={family}:wght@400;500;600;700;800"
            if query not in families:
                families.append(query)
        if not families:
            families = [
                "family=Manrope:wght@400;500;600;700;800",
                "family=Source+Sans+3:wght@400;500;600;700",
            ]
        return "https://fonts.googleapis.com/css2?" + "&".join(families) + "&display=swap"

    def _lighten(self, hex_color: str, factor: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"

    def _darken(self, hex_color: str, factor: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{max(r, 0):02X}{max(g, 0):02X}{max(b, 0):02X}"

    def _alpha(self, hex_color: str, alpha: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return "rgba(0, 0, 0, 0.08)"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"

    # ------------------------------------------------------------------
    # React + Vite Project Template
    # ------------------------------------------------------------------

    def generate_react_vite_project(self, ui_contract: dict) -> dict[str, str]:
        """生成 React + Vite + TypeScript 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-react"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        primary = palette.get("primary", "#0f7cfa")
        accent = palette.get("accent", "#f65f22")
        background = palette.get("background", "#f5f8ff")
        text = palette.get("text", "#172133")
        border = palette.get("border", "#dfe7f3")
        heading_font = typography.get("heading", "Manrope")
        body_font = typography.get("body", "Inter")
        anti_cliches = json.dumps(direction.get("anti_cliches", []), ensure_ascii=False, indent=2)
        tweak_axes = json.dumps(direction.get("tweak_axes", []), ensure_ascii=False, indent=2)

        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "private": True,
                    "version": "0.1.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "tsc -b && vite build",
                        "preview": "vite preview",
                    },
                    "dependencies": {
                        "react": "^19.0.0",
                        "react-dom": "^19.0.0",
                    },
                    "devDependencies": {
                        "@types/react": "^19.0.0",
                        "@types/react-dom": "^19.0.0",
                        "@vitejs/plugin-react": "^5.0.0",
                        "typescript": "^5.7.0",
                        "vite": "^6.0.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        vite_config = output_dir / "vite.config.ts"
        vite_config.write_text(
            (
                'import { defineConfig } from "vite";\n'
                'import react from "@vitejs/plugin-react";\n\n'
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "  server: {\n"
                "    port: 3000,\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.ts"] = str(vite_config)

        tsconfig = output_dir / "tsconfig.json"
        tsconfig.write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2020",
                        "useDefineForClassFields": True,
                        "lib": ["ES2020", "DOM", "DOM.Iterable"],
                        "module": "ESNext",
                        "skipLibCheck": True,
                        "moduleResolution": "Bundler",
                        "allowImportingTsExtensions": True,
                        "resolveJsonModule": True,
                        "isolatedModules": True,
                        "noEmit": True,
                        "jsx": "react-jsx",
                        "strict": True,
                    },
                    "include": ["src"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["tsconfig.json"] = str(tsconfig)

        index_html = output_dir / "index.html"
        index_html.write_text(
            (
                "<!doctype html>\n"
                '<html lang="zh-CN">\n'
                "  <head>\n"
                '    <meta charset="UTF-8" />\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                f"    <title>{html.escape(self.name)} · React Blueprint</title>\n"
                '    <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
                '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
                f'    <link href="{self._build_google_fonts_url(typography)}" rel="stylesheet" />\n'
                "  </head>\n"
                "  <body>\n"
                '    <div id="root"></div>\n'
                '    <script type="module" src="/src/main.tsx"></script>\n'
                "  </body>\n"
                "</html>\n"
            ),
            encoding="utf-8",
        )
        files["index.html"] = str(index_html)

        main_tsx = src_dir / "main.tsx"
        main_tsx.write_text(
            (
                'import { StrictMode } from "react";\n'
                'import { createRoot } from "react-dom/client";\n'
                'import "./styles.css";\n'
                'import { App } from "./App";\n\n'
                'createRoot(document.getElementById("root")!).render(\n'
                "  <StrictMode>\n"
                "    <App />\n"
                "  </StrictMode>,\n"
                ");\n"
            ),
            encoding="utf-8",
        )
        files["src/main.tsx"] = str(main_tsx)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                'const antiCliches = '
                + anti_cliches
                + " as const;\n"
                + 'const tweakAxes = '
                + tweak_axes
                + " as const;\n\n"
                + "export function App() {\n"
                + "  return (\n"
                + f'    <main className="app-shell" data-direction={json.dumps(direction["direction_id"], ensure_ascii=False)}>\n'
                + '      <section className="hero-card">\n'
                + f'        <p className="eyebrow">{html.escape(str(direction["name"]))}</p>\n'
                + f"        <h1>{html.escape(self.name)}</h1>\n"
                + f'        <p className="summary">{html.escape(self.description)}</p>\n'
                + f'        <p className="philosophy">{html.escape(str(direction["philosophy"]))}</p>\n'
                + '        <div className="meta-row">\n'
                + f'          <span>Hero: {html.escape(str(direction["hero_treatment"]))}</span>\n'
                + f'          <span>Proof: {html.escape(str(direction["proof_strategy"]))}</span>\n'
                + "        </div>\n"
                + "      </section>\n"
                + '      <section className="direction-grid">\n'
                + '        <article className="direction-card">\n'
                + '          <h2>Anti-Cliche Guardrails</h2>\n'
                + "          <ul>{antiCliches.map((item) => <li key={item}>{item}</li>)}</ul>\n"
                + "        </article>\n"
                + '        <article className="direction-card">\n'
                + '          <h2>Tweak Axes</h2>\n'
                + "          <ul>{tweakAxes.map((item) => <li key={item}>{item}</li>)}</ul>\n"
                + "        </article>\n"
                + "      </section>\n"
                + "    </main>\n"
                + "  );\n"
                + "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        styles = src_dir / "styles.css"
        styles.write_text(
            (
                ":root {\n"
                f"  --bg: {background};\n"
                f"  --surface: {self._alpha('#FFFFFF', 0.96)};\n"
                f"  --text: {text};\n"
                f"  --muted: {self._darken(text, 0.62)};\n"
                f"  --primary: {primary};\n"
                f"  --accent: {accent};\n"
                f"  --border: {self._alpha(border, 0.78)};\n"
                f'  --font-heading: "{heading_font}", sans-serif;\n'
                f'  --font-body: "{body_font}", system-ui, sans-serif;\n'
                "}\n\n"
                "* { box-sizing: border-box; }\n"
                "body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-body); }\n"
                ".app-shell { max-width: 1120px; margin: 0 auto; padding: 40px 20px 64px; }\n"
                ".hero-card, .direction-card { background: var(--surface); border: 1px solid var(--border); border-radius: 24px; box-shadow: 0 18px 40px rgba(13, 33, 57, 0.09); }\n"
                ".hero-card { padding: 32px; }\n"
                ".eyebrow { margin: 0 0 12px; color: var(--primary); text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; font-weight: 800; }\n"
                "h1, h2 { font-family: var(--font-heading); letter-spacing: -0.03em; }\n"
                "h1 { margin: 0 0 12px; font-size: clamp(34px, 5vw, 64px); }\n"
                ".summary, .philosophy { margin: 0 0 14px; max-width: 64ch; color: var(--muted); }\n"
                ".meta-row { display: flex; flex-wrap: wrap; gap: 10px; }\n"
                ".meta-row span { padding: 8px 12px; border-radius: 999px; background: rgba(15,124,250,0.08); font-size: 13px; font-weight: 700; }\n"
                ".direction-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 18px; }\n"
                ".direction-card { padding: 22px; }\n"
                ".direction-card ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; }\n"
                '.app-shell[data-direction="cinematic-product"] .hero-card { background: linear-gradient(145deg, rgba(9, 18, 30, 0.96), rgba(12, 28, 43, 0.82)); color: #eef4fb; }\n'
                '.app-shell[data-direction="editorial-swiss"] h1 { text-transform: uppercase; max-width: 10ch; }\n'
                '@media (max-width: 860px) { .direction-grid { grid-template-columns: 1fr; } }\n'
            ),
            encoding="utf-8",
        )
        files["src/styles.css"] = str(styles)

        return files

    # ------------------------------------------------------------------
    # Expo / React Native Project Template
    # ------------------------------------------------------------------

    def generate_expo_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 Expo 托管的 React Native 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-expo"
        app_dir = output_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        direction = self._resolve_direction_profile(ui_contract)

        package_path = output_dir / "package.json"
        package_path.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-mobile",
                    "private": True,
                    "version": "0.1.0",
                    "main": "expo-router/entry",
                    "scripts": {
                        "start": "expo start",
                        "android": "expo run:android",
                        "ios": "expo run:ios",
                        "web": "expo start --web",
                    },
                    "dependencies": {
                        "expo": "^54.0.0",
                        "expo-router": "^5.0.0",
                        "react": "^19.0.0",
                        "react-native": "0.81.0",
                    },
                    "devDependencies": {"typescript": "^5.7.0"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_path)

        app_json = output_dir / "app.json"
        app_json.write_text(
            json.dumps(
                {
                    "expo": {
                        "name": self.name,
                        "slug": self.name.lower().replace(" ", "-"),
                        "scheme": self.name.lower().replace(" ", "-"),
                        "orientation": "portrait",
                        "plugins": ["expo-router"],
                    }
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["app.json"] = str(app_json)

        index_tsx = app_dir / "index.tsx"
        index_tsx.write_text(
            (
                'import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";\n\n'
                f"const antiCliches = {json.dumps(direction.get('anti_cliches', []), ensure_ascii=False)};\n\n"
                "export default function HomeScreen() {\n"
                "  return (\n"
                "    <SafeAreaView style={styles.safeArea}>\n"
                "      <ScrollView contentContainerStyle={styles.container}>\n"
                f'        <Text style={{{{styles.eyebrow}}}}>{html.escape(str(direction["name"]))}</Text>\n'
                f'        <Text style={{{{styles.title}}}}>{html.escape(self.name)}</Text>\n'
                f'        <Text style={{{{styles.summary}}}}>{html.escape(self.description)}</Text>\n'
                f'        <Text style={{{{styles.philosophy}}}}>{html.escape(str(direction["philosophy"]))}</Text>\n'
                '        <View style={styles.card}>\n'
                '          <Text style={styles.cardTitle}>Native Flow Checklist</Text>\n'
                '          <Text style={styles.cardBody}>Navigation, deep link, permission, offline cache, share and notification paths should be validated on device.</Text>\n'
                "        </View>\n"
                '        <View style={styles.card}>\n'
                '          <Text style={styles.cardTitle}>Anti-Cliche Guardrails</Text>\n'
                "          {antiCliches.map((item) => (\n"
                '            <Text key={item} style={styles.listItem}>• {item}</Text>\n'
                "          ))}\n"
                "        </View>\n"
                "      </ScrollView>\n"
                "    </SafeAreaView>\n"
                "  );\n"
                "}\n\n"
                "const styles = StyleSheet.create({\n"
                f"  safeArea: {{ flex: 1, backgroundColor: {json.dumps(palette.get('background', '#F5F8FF'))} }},\n"
                '  container: { padding: 24, gap: 18 },\n'
                f"  eyebrow: {{ color: {json.dumps(palette.get('primary', '#0F7CFA'))}, fontSize: 12, fontWeight: '800', letterSpacing: 1.2, textTransform: 'uppercase' }},\n"
                f"  title: {{ color: {json.dumps(palette.get('text', '#172133'))}, fontSize: 34, lineHeight: 40, fontWeight: '800', fontFamily: {json.dumps(typography.get('heading', 'System'))} }},\n"
                f"  summary: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.62))}, fontSize: 17, lineHeight: 26, fontFamily: {json.dumps(typography.get('body', 'System'))} }},\n"
                f"  philosophy: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.72))}, fontSize: 15, lineHeight: 24 }},\n"
                f"  card: {{ backgroundColor: '#FFFFFF', borderRadius: 24, padding: 18, borderWidth: 1, borderColor: {json.dumps(self._alpha(palette.get('border', '#DFE7F3'), 0.85))} }},\n"
                f"  cardTitle: {{ color: {json.dumps(palette.get('text', '#172133'))}, fontSize: 18, fontWeight: '700', marginBottom: 8 }},\n"
                f"  cardBody: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.66))}, fontSize: 14, lineHeight: 21 }},\n"
                f"  listItem: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.7))}, fontSize: 14, lineHeight: 22, marginTop: 6 }},\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["app/index.tsx"] = str(index_tsx)

        return files

    # ------------------------------------------------------------------
    # Flutter Project Template
    # ------------------------------------------------------------------

    def generate_flutter_project(self, ui_contract: dict) -> dict[str, str]:
        """生成 Flutter 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-flutter"
        lib_dir = output_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        palette = ui_contract.get("color_palette", {})
        direction = self._resolve_direction_profile(ui_contract)

        pubspec = output_dir / "pubspec.yaml"
        pubspec.write_text(
            (
                f"name: {self.name.lower().replace(' ', '_')}_app\n"
                "description: Super Dev Flutter scaffold\n"
                "publish_to: 'none'\n"
                "environment:\n"
                "  sdk: '>=3.4.0 <4.0.0'\n"
                "dependencies:\n"
                "  flutter:\n"
                "    sdk: flutter\n"
                "  go_router: ^14.0.0\n"
                "  flutter_riverpod: ^2.5.0\n"
            ),
            encoding="utf-8",
        )
        files["pubspec.yaml"] = str(pubspec)

        main_dart = lib_dir / "main.dart"
        main_dart.write_text(
            (
                "import 'package:flutter/material.dart';\n\n"
                "void main() {\n"
                "  runApp(const SuperDevApp());\n"
                "}\n\n"
                "class SuperDevApp extends StatelessWidget {\n"
                "  const SuperDevApp({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                f"      title: {json.dumps(self.name)},\n"
                "      theme: ThemeData(\n"
                f"        colorScheme: ColorScheme.fromSeed(seedColor: const Color({self._dart_color(palette.get('primary', '#0F7CFA'))})),\n"
                "        useMaterial3: true,\n"
                "      ),\n"
                "      home: const HomePage(),\n"
                "    );\n"
                "  }\n"
                "}\n\n"
                "class HomePage extends StatelessWidget {\n"
                "  const HomePage({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return Scaffold(\n"
                "      body: SafeArea(\n"
                "        child: Padding(\n"
                "          padding: const EdgeInsets.all(24),\n"
                "          child: Column(\n"
                "            crossAxisAlignment: CrossAxisAlignment.start,\n"
                "            children: [\n"
                f"              Text({json.dumps(direction['name'])}, style: Theme.of(context).textTheme.labelSmall?.copyWith(letterSpacing: 1.2, fontWeight: FontWeight.w800)),\n"
                "              SizedBox(height: 12),\n"
                f"              Text({json.dumps(self.name)}, style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800)),\n"
                "              SizedBox(height: 12),\n"
                f"              Text({json.dumps(self.description)}),\n"
                "              SizedBox(height: 16),\n"
                f"              Text({json.dumps(direction['philosophy'])}),\n"
                "            ],\n"
                "          ),\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["lib/main.dart"] = str(main_dart)
        return files

    # ------------------------------------------------------------------
    # MiniApp Project Template
    # ------------------------------------------------------------------

    def generate_miniapp_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 uni-app / Taro 家族的小程序实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-miniapp"
        src_dir = output_dir / "src"
        pages_dir = src_dir / "pages" / "index"
        pages_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)
        is_taro = flavor == "taro"

        package_json = output_dir / "package.json"
        if is_taro:
            package_json.write_text(
                json.dumps(
                    {
                        "name": f"{self.name}-miniapp",
                        "private": True,
                        "version": "0.1.0",
                        "scripts": {"dev:weapp": "taro build --type weapp --watch"},
                        "dependencies": {"react": "^19.0.0", "@tarojs/taro": "^4.0.0"},
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["package.json"] = str(package_json)

            app_tsx = src_dir / "app.tsx"
            app_tsx.parent.mkdir(parents=True, exist_ok=True)
            app_tsx.write_text(
                "import { PropsWithChildren } from 'react';\n\n"
                "function App({ children }: PropsWithChildren) {\n"
                "  return children;\n"
                "}\n\n"
                "export default App;\n",
                encoding="utf-8",
            )
            files["src/app.tsx"] = str(app_tsx)

            page_tsx = pages_dir / "index.tsx"
            page_tsx.write_text(
                (
                    "import { View, Text } from '@tarojs/components';\n\n"
                    "export default function IndexPage() {\n"
                    "  return (\n"
                    "    <View className='page'>\n"
                    f"      <Text className='eyebrow'>{html.escape(str(direction['name']))}</Text>\n"
                    f"      <Text className='title'>{html.escape(self.name)}</Text>\n"
                    f"      <Text className='summary'>{html.escape(self.description)}</Text>\n"
                    "    </View>\n"
                    "  );\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            files["src/pages/index/index.tsx"] = str(page_tsx)
        else:
            package_json.write_text(
                json.dumps(
                    {
                        "name": f"{self.name}-miniapp",
                        "private": True,
                        "version": "0.1.0",
                        "scripts": {"dev:h5": "uni", "dev:mp-weixin": "uni"},
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["package.json"] = str(package_json)

            app_vue = src_dir / "App.vue"
            app_vue.parent.mkdir(parents=True, exist_ok=True)
            app_vue.write_text(
                "<script setup lang=\"ts\"></script>\n\n"
                "<template>\n"
                "  <slot />\n"
                "</template>\n",
                encoding="utf-8",
            )
            files["src/App.vue"] = str(app_vue)

            page_vue = pages_dir / "index.vue"
            page_vue.write_text(
                (
                    "<template>\n"
                    "  <view class=\"page\">\n"
                    f"    <text class=\"eyebrow\">{html.escape(str(direction['name']))}</text>\n"
                    f"    <text class=\"title\">{html.escape(self.name)}</text>\n"
                    f"    <text class=\"summary\">{html.escape(self.description)}</text>\n"
                    "  </view>\n"
                    "</template>\n\n"
                    "<style scoped>\n"
                    ".page { padding: 32rpx; display: flex; flex-direction: column; gap: 20rpx; }\n"
                    ".eyebrow { font-size: 24rpx; letter-spacing: 2rpx; text-transform: uppercase; color: #0F7CFA; }\n"
                    ".title { font-size: 64rpx; font-weight: 800; color: #172133; }\n"
                    ".summary { font-size: 30rpx; color: #4A5970; line-height: 1.6; }\n"
                    "</style>\n"
                ),
                encoding="utf-8",
            )
            files["src/pages/index/index.vue"] = str(page_vue)

            pages_json = output_dir / "pages.json"
            pages_json.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "path": "pages/index/index",
                                "style": {"navigationBarTitleText": self.name},
                            }
                        ]
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["pages.json"] = str(pages_json)

        return files

    # ------------------------------------------------------------------
    # Desktop Shell Project Template
    # ------------------------------------------------------------------

    def generate_desktop_shell_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成桌面壳实施参考模板（Tauri / Electron / Wails）。"""
        output_dir = self.project_dir / "output" / "frontend-desktop-shell"
        src_dir = output_dir / "src"
        shell_dir = output_dir / flavor
        src_dir.mkdir(parents=True, exist_ok=True)
        shell_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)

        package_json = output_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-desktop",
                    "private": True,
                    "version": "0.1.0",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
                    "devDependencies": {"vite": "^6.0.0", "@vitejs/plugin-react": "^5.0.0"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_json)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                "export function App() {\n"
                "  return (\n"
                "    <main style={{padding: 24, fontFamily: 'Inter, system-ui'}}> \n"
                f"      <p style={{textTransform: 'uppercase', color: '#0F7CFA', fontWeight: 800}}>{html.escape(str(direction['name']))}</p>\n"
                f"      <h1>{html.escape(self.name)}</h1>\n"
                f"      <p>{html.escape(self.description)}</p>\n"
                "      <ul>\n"
                "        <li>Window layout and restore</li>\n"
                "        <li>Native file system and import/export</li>\n"
                "        <li>Shortcut, IPC and offline recovery checks</li>\n"
                "      </ul>\n"
                "    </main>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        if flavor == "tauri":
            tauri_conf = shell_dir / "tauri.conf.json"
            tauri_conf.write_text(
                json.dumps({"productName": self.name, "build": {"beforeDevCommand": "npm run dev"}}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            files[f"{flavor}/tauri.conf.json"] = str(tauri_conf)
        elif flavor == "electron":
            electron_main = shell_dir / "main.ts"
            electron_main.write_text(
                "import { app, BrowserWindow } from 'electron';\n\n"
                "function createWindow() {\n"
                "  const win = new BrowserWindow({ width: 1440, height: 960 });\n"
                "  void win.loadURL('http://localhost:3000');\n"
                "}\n\n"
                "app.whenReady().then(createWindow);\n",
                encoding="utf-8",
            )
            files[f"{flavor}/main.ts"] = str(electron_main)
        else:
            wails_json = shell_dir / "wails.json"
            wails_json.write_text(
                json.dumps({"name": self.name, "frontend:install": "npm install"}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            files[f"{flavor}/wails.json"] = str(wails_json)
        return files

    # ------------------------------------------------------------------
    # Hybrid Shell Project Template
    # ------------------------------------------------------------------

    def generate_hybrid_shell_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 Ionic / Capacitor 混合壳实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-hybrid-shell"
        src_dir = output_dir / "src"
        native_dir = output_dir / flavor
        src_dir.mkdir(parents=True, exist_ok=True)
        native_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)

        package_json = output_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-hybrid",
                    "private": True,
                    "version": "0.1.0",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "dependencies": {"@capacitor/core": "^7.0.0", "react": "^19.0.0", "react-dom": "^19.0.0"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_json)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                "export function App() {\n"
                "  return (\n"
                "    <main style={{padding: 24, fontFamily: 'Inter, system-ui'}}> \n"
                f"      <p style={{textTransform: 'uppercase', color: '#0F7CFA', fontWeight: 800}}>{html.escape(str(direction['name']))}</p>\n"
                f"      <h1>{html.escape(self.name)}</h1>\n"
                "      <p>Hybrid shell scaffold for camera, share, push and offline validation.</p>\n"
                "    </main>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        capacitor_config = native_dir / "capacitor.config.ts"
        capacitor_config.write_text(
            (
                'import type { CapacitorConfig } from "@capacitor/cli";\n\n'
                "const config: CapacitorConfig = {\n"
                f"  appId: 'dev.super.{self.name.lower().replace(' ', '')}',\n"
                f"  appName: {json.dumps(self.name)},\n"
                '  webDir: "dist",\n'
                "};\n\n"
                "export default config;\n"
            ),
            encoding="utf-8",
        )
        files[f"{flavor}/capacitor.config.ts"] = str(capacitor_config)
        return files

    def _dart_color(self, hex_color: str) -> str:
        token = str(hex_color or "").lstrip("#")
        if len(token) != 6:
            token = "0F7CFA"
        return f"0xFF{token.upper()}"

    # ------------------------------------------------------------------
    # Vue 3 Project Template
    # ------------------------------------------------------------------

    def generate_vue3_project(self) -> dict[str, str]:
        """生成完整的 Vue 3 + Vite 项目模板"""
        output_dir = self.project_dir / "output" / "frontend-vue3"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}

        # package.json
        pkg = output_dir / "package.json"
        pkg_content = json.dumps(
            {
                "name": f"{self.name}-frontend",
                "version": "0.1.0",
                "private": True,
                "type": "module",
                "scripts": {
                    "dev": "vite",
                    "build": "vue-tsc && vite build",
                    "preview": "vite preview",
                    "test": "vitest",
                    "test:e2e": "playwright test",
                    "storybook": "storybook dev -p 6006",
                    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts",
                },
                "dependencies": {
                    "vue": "^3.4.0",
                    "vue-router": "^4.3.0",
                    "pinia": "^2.1.0",
                    "@vueuse/core": "^10.7.0",
                },
                "devDependencies": {
                    "@vitejs/plugin-vue": "^5.0.0",
                    "vite": "^5.0.0",
                    "vue-tsc": "^2.0.0",
                    "typescript": "^5.3.0",
                    "vitest": "^1.2.0",
                    "@vue/test-utils": "^2.4.0",
                    "tailwindcss": "^3.4.0",
                    "postcss": "^8.4.0",
                    "autoprefixer": "^10.4.0",
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        pkg.write_text(pkg_content, encoding="utf-8")
        files["package.json"] = str(pkg)

        # vite.config.ts
        vite_config = output_dir / "vite.config.ts"
        vite_config.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import vue from '@vitejs/plugin-vue';\n"
                "import { resolve } from 'path';\n\n"
                "export default defineConfig({\n"
                "  plugins: [vue()],\n"
                "  resolve: {\n"
                "    alias: {\n"
                "      '@': resolve(__dirname, 'src'),\n"
                "    },\n"
                "  },\n"
                "  server: {\n"
                "    port: 3000,\n"
                "    proxy: {\n"
                "      '/api': { target: 'http://localhost:3001', changeOrigin: true },\n"
                "    },\n"
                "  },\n"
                "  build: {\n"
                "    rollupOptions: {\n"
                "      output: {\n"
                "        manualChunks: {\n"
                "          vendor: ['vue', 'vue-router', 'pinia'],\n"
                "        },\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.ts"] = str(vite_config)

        # tailwind.config.js
        tw = output_dir / "tailwind.config.js"
        tw.write_text(
            (
                "/** @type {import('tailwindcss').Config} */\n"
                "export default {\n"
                "  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],\n"
                "  theme: {\n"
                "    extend: {\n"
                "      colors: {\n"
                "        primary: 'var(--color-primary)',\n"
                "        secondary: 'var(--color-secondary)',\n"
                "        accent: 'var(--color-accent)',\n"
                "      },\n"
                "      fontFamily: {\n"
                "        heading: 'var(--font-heading)',\n"
                "        body: 'var(--font-body)',\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "  plugins: [],\n"
                "};\n"
            ),
            encoding="utf-8",
        )
        files["tailwind.config.js"] = str(tw)

        # App.vue
        app_vue = src_dir / "App.vue"
        app_vue.write_text(
            (
                '<script setup lang="ts">\n'
                "import { RouterView } from 'vue-router';\n"
                "</script>\n\n"
                "<template>\n"
                "  <RouterView />\n"
                "</template>\n"
            ),
            encoding="utf-8",
        )
        files["src/App.vue"] = str(app_vue)

        # main.ts
        main_ts = src_dir / "main.ts"
        main_ts.write_text(
            (
                "import { createApp } from 'vue';\n"
                "import { createPinia } from 'pinia';\n"
                "import App from './App.vue';\n"
                "import router from './router';\n"
                "import './assets/main.css';\n\n"
                "const app = createApp(App);\n"
                "app.use(createPinia());\n"
                "app.use(router);\n"
                "app.mount('#app');\n"
            ),
            encoding="utf-8",
        )
        files["src/main.ts"] = str(main_ts)

        # Router
        router_dir = src_dir / "router"
        router_dir.mkdir(parents=True, exist_ok=True)
        (router_dir / "index.ts").write_text(
            (
                "import { createRouter, createWebHistory } from 'vue-router';\n\n"
                "const router = createRouter({\n"
                "  history: createWebHistory(),\n"
                "  routes: [\n"
                "    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },\n"
                "  ],\n"
                "});\n\n"
                "export default router;\n"
            ),
            encoding="utf-8",
        )
        files["src/router/index.ts"] = str(router_dir / "index.ts")

        # Views
        views_dir = src_dir / "views"
        views_dir.mkdir(parents=True, exist_ok=True)
        (views_dir / "HomeView.vue").write_text(
            (
                '<script setup lang="ts">\n'
                "</script>\n\n"
                "<template>\n"
                '  <main class="max-w-5xl mx-auto px-4 py-12">\n'
                f'    <h1 class="text-3xl font-heading font-bold">{html.escape(self.name)}</h1>\n'
                f'    <p class="mt-2 text-gray-600">{html.escape(self.description)}</p>\n'
                "  </main>\n"
                "</template>\n"
            ),
            encoding="utf-8",
        )
        files["src/views/HomeView.vue"] = str(views_dir / "HomeView.vue")

        return files

    # ------------------------------------------------------------------
    # Angular Project Template
    # ------------------------------------------------------------------

    def generate_angular_project(self) -> dict[str, str]:
        """生成 Angular 实施参考模板"""
        output_dir = self.project_dir / "output" / "frontend-angular"
        src_dir = output_dir / "src" / "app"
        src_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # package.json
        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "version": "0.1.0",
                    "scripts": {
                        "start": "ng serve",
                        "build": "ng build",
                        "test": "ng test",
                        "lint": "ng lint",
                    },
                    "dependencies": {
                        "@angular/animations": "^18.0.0",
                        "@angular/common": "^18.0.0",
                        "@angular/compiler": "^18.0.0",
                        "@angular/core": "^18.0.0",
                        "@angular/forms": "^18.0.0",
                        "@angular/platform-browser": "^18.0.0",
                        "@angular/router": "^18.0.0",
                        "rxjs": "^7.8.0",
                        "zone.js": "^0.14.0",
                    },
                    "devDependencies": {
                        "@angular/cli": "^18.0.0",
                        "@angular/compiler-cli": "^18.0.0",
                        "typescript": "^5.4.0",
                        "karma": "^6.4.0",
                        "jasmine-core": "^5.1.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        # app.component.ts
        comp = src_dir / "app.component.ts"
        comp.write_text(
            (
                "import { Component } from '@angular/core';\n"
                "import { RouterOutlet } from '@angular/router';\n\n"
                "@Component({\n"
                "  selector: 'app-root',\n"
                "  standalone: true,\n"
                "  imports: [RouterOutlet],\n"
                f"  template: `<h1>{html.escape(self.name)}</h1><router-outlet />`,\n"
                "})\n"
                "export class AppComponent {}\n"
            ),
            encoding="utf-8",
        )
        files["src/app/app.component.ts"] = str(comp)

        # app.routes.ts
        routes = src_dir / "app.routes.ts"
        routes.write_text(
            (
                "import { Routes } from '@angular/router';\n\n"
                "export const routes: Routes = [\n"
                "  { path: '', loadComponent: () => import('./home/home.component').then(m => m.HomeComponent) },\n"
                "];\n"
            ),
            encoding="utf-8",
        )
        files["src/app/app.routes.ts"] = str(routes)

        # home component
        home_dir = src_dir / "home"
        home_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / "home.component.ts").write_text(
            (
                "import { Component } from '@angular/core';\n\n"
                "@Component({\n"
                "  selector: 'app-home',\n"
                "  standalone: true,\n"
                f"  template: `<main><h2>Welcome to {html.escape(self.name)}</h2>"
                f"<p>{html.escape(self.description)}</p></main>`,\n"
                "})\n"
                "export class HomeComponent {}\n"
            ),
            encoding="utf-8",
        )
        files["src/app/home/home.component.ts"] = str(home_dir / "home.component.ts")

        return files

    # ------------------------------------------------------------------
    # Svelte Project Template
    # ------------------------------------------------------------------

    def generate_svelte_project(self) -> dict[str, str]:
        """生成 SvelteKit 实施参考模板"""
        output_dir = self.project_dir / "output" / "frontend-svelte"
        src_dir = output_dir / "src"
        routes_dir = src_dir / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "version": "0.1.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite dev",
                        "build": "vite build",
                        "preview": "vite preview",
                        "test": "vitest",
                    },
                    "dependencies": {
                        "@sveltejs/kit": "^2.0.0",
                        "svelte": "^4.2.0",
                    },
                    "devDependencies": {
                        "@sveltejs/adapter-auto": "^3.0.0",
                        "@sveltejs/vite-plugin-svelte": "^3.0.0",
                        "vite": "^5.0.0",
                        "vitest": "^1.2.0",
                        "tailwindcss": "^3.4.0",
                        "postcss": "^8.4.0",
                        "autoprefixer": "^10.4.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        # +page.svelte
        page = routes_dir / "+page.svelte"
        page.write_text(
            (
                "<script>\n"
                "</script>\n\n"
                f"<h1>{html.escape(self.name)}</h1>\n"
                f"<p>{html.escape(self.description)}</p>\n"
            ),
            encoding="utf-8",
        )
        files["src/routes/+page.svelte"] = str(page)

        # +layout.svelte
        layout = routes_dir / "+layout.svelte"
        layout.write_text(
            ("<script>\n" "  import '../app.css';\n" "</script>\n\n" "<slot />\n"),
            encoding="utf-8",
        )
        files["src/routes/+layout.svelte"] = str(layout)

        # app.css
        app_css = src_dir / "app.css"
        app_css.write_text(
            "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
            encoding="utf-8",
        )
        files["src/app.css"] = str(app_css)

        return files

    # ------------------------------------------------------------------
    # Design System Scaffold
    # ------------------------------------------------------------------

    def generate_design_system_scaffold(self) -> dict[str, str]:
        """生成设计系统参考模板（Token 文件、主题配置、组件模板）"""
        output_dir = self.project_dir / "output" / "design-system"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        ui_contract = self._load_ui_contract()
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})

        # Design tokens CSS
        tokens_file = output_dir / "tokens.css"
        primary = palette.get("primary", "#2563EB")
        secondary = palette.get("secondary", "#3B82F6")
        accent = palette.get("accent", "#EA580C")
        background = palette.get("background", "#FFFFFF")
        text_color = palette.get("text", "#111827")
        border = palette.get("border", "#E5E7EB")
        heading = typography.get("heading", "Manrope")
        body = typography.get("body", "Source Sans 3")

        tokens_file.write_text(
            (
                ":root {\n"
                "  /* --- Color Tokens --- */\n"
                f"  --color-primary: {primary};\n"
                f"  --color-secondary: {secondary};\n"
                f"  --color-accent: {accent};\n"
                f"  --color-background: {background};\n"
                f"  --color-text: {text_color};\n"
                f"  --color-border: {border};\n"
                "  --color-surface: #FFFFFF;\n"
                "  --color-muted: #6B7280;\n"
                "  --color-success: #059669;\n"
                "  --color-warning: #D97706;\n"
                "  --color-error: #DC2626;\n"
                "  --color-info: #2563EB;\n\n"
                "  /* --- Typography Tokens --- */\n"
                f"  --font-heading: '{heading}', system-ui, sans-serif;\n"
                f"  --font-body: '{body}', system-ui, sans-serif;\n"
                "  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;\n\n"
                "  --text-xs: 0.75rem;    /* 12px */\n"
                "  --text-sm: 0.875rem;   /* 14px */\n"
                "  --text-base: 1rem;     /* 16px */\n"
                "  --text-lg: 1.125rem;   /* 18px */\n"
                "  --text-xl: 1.25rem;    /* 20px */\n"
                "  --text-2xl: 1.5rem;    /* 24px */\n"
                "  --text-3xl: 1.875rem;  /* 30px */\n"
                "  --text-4xl: 2.25rem;   /* 36px */\n\n"
                "  /* --- Spacing Tokens --- */\n"
                "  --space-1: 0.25rem;    /* 4px */\n"
                "  --space-2: 0.5rem;     /* 8px */\n"
                "  --space-3: 0.75rem;    /* 12px */\n"
                "  --space-4: 1rem;       /* 16px */\n"
                "  --space-5: 1.25rem;    /* 20px */\n"
                "  --space-6: 1.5rem;     /* 24px */\n"
                "  --space-8: 2rem;       /* 32px */\n"
                "  --space-10: 2.5rem;    /* 40px */\n"
                "  --space-12: 3rem;      /* 48px */\n"
                "  --space-16: 4rem;      /* 64px */\n\n"
                "  /* --- Border Radius Tokens --- */\n"
                "  --radius-sm: 4px;\n"
                "  --radius-md: 8px;\n"
                "  --radius-lg: 12px;\n"
                "  --radius-xl: 16px;\n"
                "  --radius-2xl: 24px;\n"
                "  --radius-full: 9999px;\n\n"
                "  /* --- Shadow Tokens --- */\n"
                "  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);\n"
                "  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);\n"
                "  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);\n"
                "  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);\n\n"
                "  /* --- Transition Tokens --- */\n"
                "  --transition-fast: 150ms ease;\n"
                "  --transition-base: 200ms ease;\n"
                "  --transition-slow: 300ms ease;\n\n"
                "  /* --- Z-Index Tokens --- */\n"
                "  --z-dropdown: 1000;\n"
                "  --z-sticky: 1020;\n"
                "  --z-fixed: 1030;\n"
                "  --z-modal-backdrop: 1040;\n"
                "  --z-modal: 1050;\n"
                "  --z-popover: 1060;\n"
                "  --z-tooltip: 1070;\n"
                "}\n\n"
                "@media (prefers-color-scheme: dark) {\n"
                "  :root {\n"
                "    --color-background: #0F172A;\n"
                "    --color-text: #F8FAFC;\n"
                "    --color-surface: #1E293B;\n"
                "    --color-border: #334155;\n"
                "    --color-muted: #94A3B8;\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["tokens.css"] = str(tokens_file)

        # Theme config (Tailwind-compatible)
        theme_file = output_dir / "theme.ts"
        theme_file.write_text(
            (
                "/**\n"
                " * Design System Theme Configuration\n"
                " * Use with Tailwind CSS or any token-based styling system.\n"
                " */\n\n"
                "export const theme = {\n"
                "  colors: {\n"
                f"    primary: '{primary}',\n"
                f"    secondary: '{secondary}',\n"
                f"    accent: '{accent}',\n"
                f"    background: '{background}',\n"
                f"    text: '{text_color}',\n"
                f"    border: '{border}',\n"
                "    success: '#059669',\n"
                "    warning: '#D97706',\n"
                "    error: '#DC2626',\n"
                "  },\n"
                "  fonts: {\n"
                f"    heading: '{heading}',\n"
                f"    body: '{body}',\n"
                "  },\n"
                "  breakpoints: {\n"
                "    sm: '640px',\n"
                "    md: '768px',\n"
                "    lg: '1024px',\n"
                "    xl: '1280px',\n"
                "    '2xl': '1440px',\n"
                "  },\n"
                "} as const;\n"
            ),
            encoding="utf-8",
        )
        files["theme.ts"] = str(theme_file)

        # Component template (Button example)
        components_dir = output_dir / "components"
        components_dir.mkdir(parents=True, exist_ok=True)
        (components_dir / "Button.tsx").write_text(
            (
                "import React from 'react';\n\n"
                "type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';\n"
                "type ButtonSize = 'sm' | 'md' | 'lg';\n\n"
                "interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {\n"
                "  variant?: ButtonVariant;\n"
                "  size?: ButtonSize;\n"
                "  loading?: boolean;\n"
                "}\n\n"
                "const variantStyles: Record<ButtonVariant, string> = {\n"
                "  primary: 'bg-[var(--color-primary)] text-white hover:opacity-90',\n"
                "  secondary: 'bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-gray-50',\n"
                "  ghost: 'bg-transparent text-[var(--color-text)] hover:bg-gray-100',\n"
                "  destructive: 'bg-[var(--color-error)] text-white hover:opacity-90',\n"
                "};\n\n"
                "const sizeStyles: Record<ButtonSize, string> = {\n"
                "  sm: 'h-8 px-3 text-sm rounded-[var(--radius-md)]',\n"
                "  md: 'h-10 px-4 text-base rounded-[var(--radius-lg)]',\n"
                "  lg: 'h-12 px-6 text-lg rounded-[var(--radius-lg)]',\n"
                "};\n\n"
                "export function Button({ variant = 'primary', size = 'md', loading, className = '', children, disabled, ...props }: ButtonProps) {\n"
                "  return (\n"
                "    <button\n"
                "      className={`inline-flex items-center justify-center font-semibold transition-all\n"
                "        ${variantStyles[variant]} ${sizeStyles[size]}\n"
                "        ${disabled || loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}\n"
                "        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2\n"
                "        ${className}`}\n"
                "      disabled={disabled || loading}\n"
                "      {...props}\n"
                "    >\n"
                '      {loading && <span className="mr-2 animate-spin">...</span>}\n'
                "      {children}\n"
                "    </button>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["components/Button.tsx"] = str(components_dir / "Button.tsx")

        return files

    # ------------------------------------------------------------------
    # Test Configuration Generation
    # ------------------------------------------------------------------

    def generate_test_config(self) -> dict[str, str]:
        """生成测试配置（Vitest/Playwright/Storybook）"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # Vitest config
        vitest_config = output_dir / "vitest.config.ts"
        vitest_config.write_text(
            (
                "import { defineConfig } from 'vitest/config';\n"
                "import { resolve } from 'path';\n\n"
                "export default defineConfig({\n"
                "  test: {\n"
                "    globals: true,\n"
                "    environment: 'jsdom',\n"
                "    setupFiles: ['./src/test/setup.ts'],\n"
                "    include: ['src/**/*.{test,spec}.{js,ts,jsx,tsx}'],\n"
                "    coverage: {\n"
                "      reporter: ['text', 'json', 'html'],\n"
                "      include: ['src/**/*.{ts,tsx,vue}'],\n"
                "      exclude: ['src/test/**', 'src/**/*.d.ts', 'src/**/*.stories.*'],\n"
                "      thresholds: {\n"
                "        branches: 70,\n"
                "        functions: 70,\n"
                "        lines: 70,\n"
                "        statements: 70,\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "  resolve: {\n"
                "    alias: { '@': resolve(__dirname, 'src') },\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vitest.config.ts"] = str(vitest_config)

        # Test setup
        test_dir = output_dir / "src" / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "setup.ts").write_text(
            (
                "import '@testing-library/jest-dom';\n\n"
                "// Global test setup\n"
                "beforeAll(() => {\n"
                "  // Add any global setup here\n"
                "});\n\n"
                "afterAll(() => {\n"
                "  // Add any global teardown here\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["src/test/setup.ts"] = str(test_dir / "setup.ts")

        # Playwright config
        playwright_config = output_dir / "playwright.config.ts"
        playwright_config.write_text(
            (
                "import { defineConfig, devices } from '@playwright/test';\n\n"
                "export default defineConfig({\n"
                "  testDir: './e2e',\n"
                "  fullyParallel: true,\n"
                "  forbidOnly: !!process.env.CI,\n"
                "  retries: process.env.CI ? 2 : 0,\n"
                "  workers: process.env.CI ? 1 : undefined,\n"
                "  reporter: [['html', { open: 'never' }]],\n"
                "  use: {\n"
                "    baseURL: 'http://localhost:3000',\n"
                "    trace: 'on-first-retry',\n"
                "    screenshot: 'only-on-failure',\n"
                "  },\n"
                "  projects: [\n"
                "    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },\n"
                "    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },\n"
                "    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },\n"
                "    { name: 'mobile-safari', use: { ...devices['iPhone 12'] } },\n"
                "  ],\n"
                "  webServer: {\n"
                "    command: 'npm run dev',\n"
                "    url: 'http://localhost:3000',\n"
                "    reuseExistingServer: !process.env.CI,\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["playwright.config.ts"] = str(playwright_config)

        # Sample e2e test
        e2e_dir = output_dir / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        (e2e_dir / "home.spec.ts").write_text(
            (
                "import { test, expect } from '@playwright/test';\n\n"
                "test.describe('Home Page', () => {\n"
                "  test('should display the page title', async ({ page }) => {\n"
                "    await page.goto('/');\n"
                "    await expect(page).toHaveTitle(/.+/);\n"
                "  });\n\n"
                "  test('should be responsive on mobile', async ({ page }) => {\n"
                "    await page.setViewportSize({ width: 375, height: 812 });\n"
                "    await page.goto('/');\n"
                "    await expect(page.locator('main')).toBeVisible();\n"
                "  });\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["e2e/home.spec.ts"] = str(e2e_dir / "home.spec.ts")

        # Storybook main.ts
        storybook_dir = output_dir / ".storybook"
        storybook_dir.mkdir(parents=True, exist_ok=True)
        (storybook_dir / "main.ts").write_text(
            (
                "import type { StorybookConfig } from '@storybook/react-vite';\n\n"
                "const config: StorybookConfig = {\n"
                "  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx|mdx)'],\n"
                "  addons: [\n"
                "    '@storybook/addon-essentials',\n"
                "    '@storybook/addon-a11y',\n"
                "    '@storybook/addon-interactions',\n"
                "  ],\n"
                "  framework: {\n"
                "    name: '@storybook/react-vite',\n"
                "    options: {},\n"
                "  },\n"
                "};\n"
                "export default config;\n"
            ),
            encoding="utf-8",
        )
        files[".storybook/main.ts"] = str(storybook_dir / "main.ts")

        return files

    # ------------------------------------------------------------------
    # Performance Optimization Configuration
    # ------------------------------------------------------------------

    def generate_performance_config(self) -> dict[str, str]:
        """生成性能优化配置（代码分割/懒加载/预加载配置）"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # Vite optimized config
        perf_config = output_dir / "vite.config.perf.ts"
        perf_config.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import { resolve } from 'path';\n\n"
                "/**\n"
                " * Performance-optimized Vite configuration.\n"
                " * Merge this with your main vite.config.ts.\n"
                " */\n"
                "export default defineConfig({\n"
                "  build: {\n"
                "    target: 'es2022',\n"
                "    minify: 'esbuild',\n"
                "    sourcemap: false,\n"
                "    cssMinify: true,\n"
                "    rollupOptions: {\n"
                "      output: {\n"
                "        manualChunks(id) {\n"
                "          // Vendor chunk splitting\n"
                "          if (id.includes('node_modules')) {\n"
                "            if (id.includes('react') || id.includes('react-dom')) return 'vendor-react';\n"
                "            if (id.includes('vue')) return 'vendor-vue';\n"
                "            if (id.includes('lodash') || id.includes('date-fns')) return 'vendor-utils';\n"
                "            if (id.includes('chart') || id.includes('recharts') || id.includes('echarts')) return 'vendor-charts';\n"
                "            return 'vendor';\n"
                "          }\n"
                "        },\n"
                "        chunkFileNames: 'assets/js/[name]-[hash].js',\n"
                "        entryFileNames: 'assets/js/[name]-[hash].js',\n"
                "        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',\n"
                "      },\n"
                "    },\n"
                "    chunkSizeWarningLimit: 500,\n"
                "  },\n"
                "  css: {\n"
                "    devSourcemap: true,\n"
                "  },\n"
                "  optimizeDeps: {\n"
                "    include: ['react', 'react-dom'],\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.perf.ts"] = str(perf_config)

        # Lazy loading utilities
        utils_dir = output_dir / "src" / "utils"
        utils_dir.mkdir(parents=True, exist_ok=True)
        (utils_dir / "lazy.ts").write_text(
            (
                "import { lazy, Suspense, createElement, type ComponentType, type ReactNode } from 'react';\n\n"
                "/**\n"
                " * Enhanced lazy loading with preload support and error boundary.\n"
                " */\n"
                "export function lazyWithPreload<T extends ComponentType<any>>(\n"
                "  factory: () => Promise<{ default: T }>\n"
                ") {\n"
                "  const Component = lazy(factory);\n"
                "  (Component as any).preload = factory;\n"
                "  return Component;\n"
                "}\n\n"
                "/**\n"
                " * Preload a route component on hover/focus.\n"
                " */\n"
                "export function prefetchOnInteraction(preloadFn: () => Promise<any>) {\n"
                "  return {\n"
                "    onMouseEnter: () => preloadFn(),\n"
                "    onFocus: () => preloadFn(),\n"
                "  };\n"
                "}\n\n"
                "/**\n"
                " * Intersection Observer based lazy loading for below-fold sections.\n"
                " */\n"
                "export function useIntersectionLazy(ref: React.RefObject<Element>, threshold = 0.1) {\n"
                "  const [isVisible, setIsVisible] = useState(false);\n"
                "  useEffect(() => {\n"
                "    if (!ref.current) return;\n"
                "    const observer = new IntersectionObserver(\n"
                "      ([entry]) => { if (entry.isIntersecting) { setIsVisible(true); observer.disconnect(); } },\n"
                "      { threshold }\n"
                "    );\n"
                "    observer.observe(ref.current);\n"
                "    return () => observer.disconnect();\n"
                "  }, [ref, threshold]);\n"
                "  return isVisible;\n"
                "}\n\n"
                "import { useState, useEffect } from 'react';\n"
            ),
            encoding="utf-8",
        )
        files["src/utils/lazy.ts"] = str(utils_dir / "lazy.ts")

        # Resource hints helper
        (utils_dir / "resource-hints.ts").write_text(
            (
                "/**\n"
                " * Add preload/prefetch resource hints dynamically.\n"
                " */\n"
                "export function addResourceHint(\n"
                "  href: string,\n"
                "  rel: 'preload' | 'prefetch' | 'preconnect' = 'prefetch',\n"
                "  as_?: 'script' | 'style' | 'image' | 'font'\n"
                "): void {\n"
                "  if (typeof document === 'undefined') return;\n"
                '  const existing = document.querySelector(`link[href="${href}"]`);\n'
                "  if (existing) return;\n"
                "  const link = document.createElement('link');\n"
                "  link.rel = rel;\n"
                "  link.href = href;\n"
                "  if (as_) link.setAttribute('as', as_);\n"
                "  if (rel === 'preconnect') link.crossOrigin = 'anonymous';\n"
                "  document.head.appendChild(link);\n"
                "}\n\n"
                "/**\n"
                " * Preconnect to critical third-party origins.\n"
                " */\n"
                "export function preconnectCritical(): void {\n"
                "  const origins = [\n"
                "    'https://fonts.googleapis.com',\n"
                "    'https://fonts.gstatic.com',\n"
                "    'https://cdn.jsdelivr.net',\n"
                "  ];\n"
                "  origins.forEach(origin => addResourceHint(origin, 'preconnect'));\n"
                "}\n\n"
                "/**\n"
                " * Image loading optimization: generate srcSet for responsive images.\n"
                " */\n"
                "export function generateSrcSet(\n"
                "  basePath: string,\n"
                "  widths: number[] = [320, 640, 960, 1280, 1920]\n"
                "): string {\n"
                "  const ext = basePath.split('.').pop() || 'jpg';\n"
                "  const base = basePath.replace(`.${ext}`, '');\n"
                "  return widths\n"
                "    .map(w => `${base}-${w}w.${ext} ${w}w`)\n"
                "    .join(', ');\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/utils/resource-hints.ts"] = str(utils_dir / "resource-hints.ts")

        return files
