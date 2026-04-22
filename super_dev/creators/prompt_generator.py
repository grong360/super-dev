"""
AI 提示词生成器 - 生成可直接给 AI 的提示词

开发：Excellent（11964948@qq.com）
功能：将 Spec 转换为 AI 可理解的提示词
作用：用户复制给 AI 即可开始开发
创建时间：2025-12-30
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ..specs.models import TaskStatus
from .prompt_sections import PromptBuilder, PromptSection
from .requirement_parser import RequirementParser

try:
    from ..experts.behavioral_prompts import (
        CODE_STYLE_DONTS,
        FALSE_CLAIMS_DEFENSE,
        NUMERIC_ANCHORS,
        STRUCTURED_OUTPUT_FORMAT,
        SYNTHESIS_RULES,
    )

    BEHAVIORAL_PROMPTS_AVAILABLE = True
except ImportError:
    BEHAVIORAL_PROMPTS_AVAILABLE = False
    NUMERIC_ANCHORS = {}

try:
    from ..experts.loader import load_expert_profiles

    EXPERT_LOADER_AVAILABLE = True
except ImportError:
    EXPERT_LOADER_AVAILABLE = False

try:
    from ..reminders import build_full_reminders

    REMINDERS_AVAILABLE = True
except ImportError:
    REMINDERS_AVAILABLE = False


class AIPromptGenerator:
    """AI 提示词生成器"""

    def __init__(self, project_dir: Path, name: str):
        """初始化提示词生成器"""
        self.project_dir = Path(project_dir).resolve()
        self.name = name

        # 加载专家工具箱（用于注入多维度审查指令）
        try:
            from ..experts.toolkit import load_expert_toolkits

            self._toolkits = load_expert_toolkits()
        except Exception:
            self._toolkits = {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """生成 AI 提示词"""
        import yaml  # type: ignore[import-untyped]

        from ..design import UIIntelligenceAdvisor

        config_path = self.project_dir / "super-dev.yaml"
        project_config: dict = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                project_config = yaml.safe_load(f) or {}

        description = project_config.get("description", "见 PRD 文档")
        frontend = project_config.get("frontend", "react")
        advisor = UIIntelligenceAdvisor()
        request_mode = RequirementParser().detect_request_mode(description)
        ui_profile = advisor.recommend(
            description=description,
            frontend=frontend,
            product_type=self._infer_product_type(description),
            industry=self._infer_industry(description),
            style=self._infer_style(description),
        )

        research_content = self._read_document("research")
        prd_content = self._read_document("prd")
        arch_content = self._read_document("architecture")
        uiux_content = self._read_document("uiux")
        plan_content = self._read_document("execution-plan")
        frontend_blueprint = self._read_document("frontend-blueprint")

        change_content, change_id = self._read_change_spec()

        # Build context dict shared across all sections
        ctx = {
            "name": self.name,
            "project_config": project_config,
            "description": description,
            "frontend": frontend,
            "request_mode": request_mode,
            "ui_profile": ui_profile,
            "research_content": research_content,
            "prd_content": prd_content,
            "arch_content": arch_content,
            "uiux_content": uiux_content,
            "plan_content": plan_content,
            "frontend_blueprint": frontend_blueprint,
            "change_content": change_content,
            "change_id": change_id,
        }

        builder = PromptBuilder()
        self._register_all_sections(builder)
        return builder.resolve(**ctx)

    # ------------------------------------------------------------------
    # Section registration
    # ------------------------------------------------------------------

    def _register_all_sections(self, builder: PromptBuilder) -> None:
        """Register every prompt section in priority order."""

        builder.register(
            PromptSection(
                name="critical_reminders",
                content_fn=self._section_critical_reminders,
                cacheable=True,
                priority=5,
            )
        )
        builder.register(
            PromptSection(
                name="static_intro",
                content_fn=self._section_static_intro,
                priority=10,
            )
        )
        builder.register(
            PromptSection(
                name="expert_mapping",
                content_fn=self._section_expert_mapping,
                priority=20,
            )
        )
        builder.register(
            PromptSection(
                name="execution_order",
                content_fn=self._section_execution_order,
                priority=30,
            )
        )
        builder.register(
            PromptSection(
                name="tech_stack_rules",
                content_fn=self._section_tech_stack_rules,
                cacheable=True,
                priority=35,
            )
        )
        builder.register(
            PromptSection(
                name="knowledge_constraints",
                content_fn=self._section_knowledge_constraints,
                priority=40,
            )
        )
        builder.register(
            PromptSection(
                name="document_confirmation_gate",
                content_fn=self._section_document_confirmation_gate,
                priority=50,
            )
        )
        builder.register(
            PromptSection(
                name="implementation_rules",
                content_fn=self._section_implementation_rules,
                priority=60,
            )
        )
        builder.register(
            PromptSection(
                name="session_context",
                content_fn=self._section_session_context,
                cacheable=False,
                priority=70,
            )
        )
        builder.register(
            PromptSection(
                name="compact_instructions",
                content_fn=self._section_compact_instructions,
                priority=80,
            )
        )
        builder.register(
            PromptSection(
                name="flow_contract",
                content_fn=self._section_flow_contract,
                priority=90,
            )
        )

    # ------------------------------------------------------------------
    # Section content generators
    # ------------------------------------------------------------------

    def _section_static_intro(self, **ctx: object) -> str:
        name = ctx["name"]
        project_config: dict = ctx["project_config"]  # type: ignore[assignment]
        description = ctx["description"]
        frontend = ctx["frontend"]
        request_mode = ctx["request_mode"]
        return f"""# {name} - AI 开发提示词

> 由 Super Dev 自动生成
> 生成时间: {self._get_timestamp()}

---

## 项目概述

**项目名称**: {name}
**项目描述**: {description}
**目标平台**: {project_config.get('platform', 'web').upper()}
**技术栈**:
- 前端: {frontend}
- 后端: {project_config.get('backend', 'node')}

---

## 你的任务

请根据以下规范和文档，实现 {name} 的所有功能。

**重要**:
1. **先研究，再三文档，再等待用户确认，再 Spec，再编码，严禁跳步**
2. **优先使用宿主原生联网 / browse / search 能力研究同类产品**
3. **优先读取并继承当前项目 `knowledge/` 与 `output/*-knowledge-bundle.json` 命中的本地知识**
4. **每完成一个任务，标记为 [x]**
5. **遵循规范中的所有要求**
6. **参考架构文档中的技术选型**
7. **如果用户明确表示 UI 不满意、要求改版、重做视觉、页面太 AI 味，必须先更新 `output/*-uiux.md`，再重做前端，并重新执行 frontend runtime 与 UI review**
8. **如果当前任务属于缺陷修复 / bugfix / 回归修复，也不得跳过文档与验证；必须先完成轻量复现分析与补丁文档，再实施修复**
9. **如果当前项目启用了 policy / 强治理策略，不得默认建议关闭红队、降低质量阈值或跳过门禁；只有在用户明确要求降低治理强度时，才可以说明风险后再调整 policy**

---

## 首轮响应契约（首次触发必须执行）

1. 第一轮回复必须明确说明：`Super Dev` 流水线已激活，当前不是普通聊天模式。
2. 第一轮回复必须明确说明当前阶段是 `research`，会先读取 `knowledge/` 与 `output/knowledge-cache/{name}-knowledge-bundle.json`（若存在），再使用宿主原生联网 / browse / search 研究同类产品。
2.1 第一轮回复前，优先读取 `.super-dev/WORKFLOW.md` 与 `output/{name}-bootstrap.md`（若存在），把其中的初始化契约视为当前仓库的显式 bootstrap 规则。
3. 第一轮回复必须明确说明固定顺序：
   - research
   - 三份核心文档
   - 等待用户确认
   - Spec / tasks
   - 前端优先并运行验证
   - 后端 / 测试 / 交付
4. 第一轮回复必须明确说明：三份核心文档完成后会暂停等待用户确认；未经确认不会创建 `.super-dev/changes/*`，也不会开始编码。
5. 如果当前需求明显属于 bugfix / regression / hotfix，第一轮回复必须明确说明会先整理问题现象、复现条件、影响范围与回归风险，再输出轻量 PRD / Architecture / UIUX 补丁文档。

---

## 多专家 Agent 架构

Super Dev 内置 11 位专家 Agent，每位专家有独立的角色定义、专业目标、思维框架和质量标准。在不同阶段以不同专家的专业身份工作。

### 阶段-专家映射

| 阶段 | 主导专家 | 专业视角 |
|:---|:---|:---|
| 研究 | PRODUCT + PM + ARCHITECT | 产品机会判断 + 用户价值分析 + 技术可行性评估 |
| PRD | PRODUCT + PM | 需求拆解、用户故事、验收标准、商业规则 |
| 架构 | ARCHITECT + DBA | 系统设计、技术选型、API 契约、数据建模 |
| UI/UX | UI + UX | 视觉系统、设计 Token、组件规范、交互设计 |
| Spec | PM + CODE | 任务分解、优先级排序、依赖分析 |
| 前端 | CODE + UI | 组件实现、页面搭建、状态管理、交互还原 |
| 后端 | CODE + DBA | API 实现、数据层、认证授权、性能优化 |
| 质量 | PRODUCT + QA + SECURITY | 闭环复核、测试策略、安全审查、质量门禁 |
| 交付 | PRODUCT + DEVOPS + QA | 交付证据、CI/CD、发布演练、交付打包 |

### 专家角色画像

{self._build_expert_profiles_section()}

### 执行规则

1. **角色切换**: 进入每个阶段时，必须以该阶段主导专家的身份、目标和思维框架工作
2. **交叉审查**: 每个专家完成工作后，下一阶段的专家应验证前序产出是否满足自己的需求
3. **冲突解决**: 当两个专家视角冲突时（如 ARCHITECT 要简单但 SECURITY 要复杂），以用户价值和安全底线为判断标准
4. **知识传递**: 每个阶段的产出是下一阶段的输入，专家必须读取前序文档后再开始工作

---

### 当前请求模式

- `{request_mode}`
- 若为 `bugfix`，请执行轻量补丁流程，不得跳过文档与验证。"""

    def _section_critical_reminders(self, **ctx: object) -> str:
        """关键约束提醒 — 数据驱动加载，从 knowledge/ 和 config 获取规则。"""
        if REMINDERS_AVAILABLE:
            frontend = str(ctx.get("frontend", ""))
            return build_full_reminders(
                frontend=frontend,
                project_dir=self.project_dir,
                knowledge_dir=self.project_dir / "knowledge",
            )
        # Fallback: 基础版（无知识库时）
        return (
            "## 关键约束提醒（每次操作前必读）\n\n"
            "1. **图标系统**: 功能图标只能来自 Lucide / Heroicons / Tabler。"
            "绝对禁止 emoji 作为功能图标。\n\n"
            "2. **AI 模板化禁令**: 禁止紫/粉渐变、emoji 图标、无层级卡片墙。\n\n"
            "3. **自检**: 展示 UI 前自检无 emoji 字符。"
        )

    def _section_tech_stack_rules(self, **ctx: object) -> str:
        """技术栈规则 — 通用预研机制 + 框架特定知识（从 knowledge/ 加载）。"""
        frontend = str(ctx.get("frontend", "")).lower().strip()

        # 通用规则：适用于任何技术栈
        universal = (
            "## 技术栈预研规则（适用于任何框架和语言）\n\n"
            "### 编码前必须执行的预研\n"
            "1. **读取依赖文件** (package.json / requirements.txt / go.mod / Cargo.toml)\n"
            "2. **确认每个主要框架的精确版本号**\n"
            "3. **用 WebFetch 查阅该版本的官方文档**，特别是：\n"
            "   - Getting Started（基本用法）\n"
            "   - Migration Guide（breaking changes）\n"
            "   - API Reference（你即将使用的功能）\n"
            "4. **如果不确定某个 API 的正确写法，先查文档再写代码。永远不要猜。**\n\n"
            "原因：模型训练数据混合了多个版本。花 2 分钟查文档，省 2 小时 debug。\n"
        )

        # 框架特定规则（从 knowledge/ 动态加载或使用内置回退）
        framework_rules = ""
        if frontend in ("next", "nextjs", "next.js"):
            framework_rules = self._nextjs_rules()
        elif frontend in ("nuxt", "nuxtjs", "nuxt.js", "vue"):
            framework_rules = self._nuxt_vue_rules(frontend)

        parts = [universal]
        if framework_rules:
            parts.append(framework_rules)
        return "\n".join(parts)

    @staticmethod
    def _nextjs_rules() -> str:
        return (
            "## Next.js 强制开发规则（当前项目使用 Next.js）\n"
            "\n"
            "### ⚠️ 版本确认（编码前第一件事）\n"
            "运行 `cat package.json | grep next` 确认 Next.js 精确版本号。\n"
            "不同版本 API 差异巨大（v13/v14/v15 各有 breaking changes）：\n"
            "- v15: cookies()/headers() 变为 async，React 19，Turbopack 默认\n"
            "- v14: metadata API 稳定，Server Actions 稳定\n"
            "- v13: App Router 初版，部分 API 与 v14+ 不同\n"
            "**如果不确定当前版本的写法，先用 WebFetch 查看**:\n"
            "`https://nextjs.org/docs/app/building-your-application/upgrading`\n"
            "\n"
            "### 绝对禁止\n"
            "1. 禁止使用 `<img>` 标签 → 必须用 `next/image` 的 `Image` 组件\n"
            "2. 禁止使用 `<a>` 做站内跳转 → 必须用 `next/link` 的 `Link` 组件\n"
            "3. 禁止从 `next/router` 导入（Pages Router 已废弃）→ 用 `next/navigation`\n"
            "4. 禁止在 Server Component 中使用 useState / useEffect / onClick\n"
            "5. 禁止用 Express/Fastify 风格写 API → "
            "用 Route Handler (export async function GET/POST)\n"
            "6. 禁止把 API 路由放在 `pages/api/` → 放在 `app/api/[route]/route.ts`\n"
            "7. 禁止用 `useEffect + fetch` 获取数据 → Server Component 直接 await fetch\n"
            '8. 禁止忘记 "use client" 指令就在组件里用 hooks\n'
            "9. 禁止用 `<title>` 标签 → 用 metadata 导出或 generateMetadata\n"
            "10. 禁止在环境变量不加 NEXT_PUBLIC_ 前缀就在浏览器端使用\n"
            "\n"
            "### 正确模式\n"
            '**Server Component (默认，不需要 "use client"):**\n'
            "```tsx\n"
            "// app/page.tsx — 直接 async/await 获取数据\n"
            "export default async function Page() {\n"
            "  const data = await fetch('https://api.example.com/data',"
            " { cache: 'force-cache' })\n"
            "  const json = await data.json()\n"
            "  return <div>{json.title}</div>\n"
            "}\n"
            "```\n"
            "\n"
            "**Client Component (仅交互部分):**\n"
            "```tsx\n"
            '// components/Counter.tsx — 需要 "use client"\n'
            '"use client"\n'
            "import { useState } from 'react'\n"
            "export function Counter() {\n"
            "  const [count, setCount] = useState(0)\n"
            "  return <button onClick={() => setCount(c => c + 1)}>{count}</button>\n"
            "}\n"
            "```\n"
            "\n"
            "**Route Handler (API):**\n"
            "```typescript\n"
            "// app/api/users/route.ts\n"
            "import { NextRequest, NextResponse } from 'next/server'\n"
            "export async function GET(request: NextRequest) {\n"
            "  return NextResponse.json({ users: [] })\n"
            "}\n"
            "export async function POST(request: NextRequest) {\n"
            "  const body = await request.json()\n"
            "  return NextResponse.json({ created: true }, { status: 201 })\n"
            "}\n"
            "```\n"
            "\n"
            "**图片（必须用 next/image）:**\n"
            "```tsx\n"
            "import Image from 'next/image'\n"
            '<Image src="/hero.jpg" alt="描述" width={1200} height={600} priority />\n'
            "```\n"
            "\n"
            "**导航（必须用 next/link）:**\n"
            "```tsx\n"
            "import Link from 'next/link'\n"
            '<Link href="/about">关于我们</Link>\n'
            "```\n"
            "\n"
            "**Metadata (SEO):**\n"
            "```tsx\n"
            "// app/layout.tsx\n"
            "export const metadata = {\n"
            "  title: '网站标题',\n"
            "  description: '网站描述',\n"
            "}\n"
            "```\n"
            "\n"
            "### 项目结构\n"
            "```\n"
            "app/\n"
            "├── layout.tsx          ← 根布局（必须存在）\n"
            "├── page.tsx            ← 首页\n"
            "├── globals.css         ← 全局样式\n"
            "├── api/\n"
            "│   └── users/route.ts  ← API Route Handler\n"
            "├── dashboard/\n"
            "│   ├── layout.tsx      ← 嵌套布局\n"
            "│   └── page.tsx        ← 子页面\n"
            "├── middleware.ts       ← 中间件（可选）\n"
            "└── next.config.ts      ← 框架配置\n"
            "```\n"
            "\n"
            "### 开始编码前必须做\n"
            "1. 确认使用 App Router（不是 Pages Router）\n"
            '2. 明确哪些组件是 Server Component，哪些需要 "use client"\n'
            "3. 锁定 next/image 作为唯一图片组件\n"
            "4. 锁定 next/link 作为唯一站内导航组件\n"
            "5. 读取当前项目的 next.config.ts 了解已有配置"
        )

    @staticmethod
    def _nuxt_vue_rules(frontend: str) -> str:
        if frontend in ("nuxt", "nuxtjs", "nuxt.js"):
            return (
                "## Nuxt 3 强制开发规则（当前项目使用 Nuxt）\n"
                "\n"
                "### 绝对禁止\n"
                "1. 禁止使用 `<img>` 标签 → 必须用 `<NuxtImg>` 或 `<NuxtPicture>`\n"
                "2. 禁止使用 `<a>` 做站内跳转 → 必须用 `<NuxtLink>`\n"
                "3. 禁止使用 `vue-router` 的 `createRouter` → Nuxt 自动生成路由\n"
                "4. 禁止手动配置 webpack/vite → 使用 `nuxt.config.ts`\n"
                "5. 禁止把 API 写成独立 Express 服务 → 用 `server/api/` 目录\n"
                "6. 禁止用 `axios` 发请求 → 用 `useFetch` / `useAsyncData` / `$fetch`\n"
                "7. 禁止在 `setup()` 之外调用 composables\n"
                "\n"
                "### 正确模式\n"
                "- 页面放 `pages/`，布局放 `layouts/`，组件放 `components/`\n"
                "- API 路由放 `server/api/`，中间件放 `server/middleware/`\n"
                "- 数据获取用 `useFetch` / `useAsyncData`\n"
                "- 状态管理用 `useState` composable 或 Pinia\n"
                "- SEO 用 `useHead` / `useSeoMeta`\n"
                "\n"
                "### 开始编码前必须做\n"
                "1. 确认使用 Nuxt 3（不是 Nuxt 2）\n"
                "2. 读取 `nuxt.config.ts` 了解已有配置\n"
                "3. 明确使用 `<NuxtImg>` 和 `<NuxtLink>`\n"
                "4. 锁定组件库（如 Nuxt UI / PrimeVue / Element Plus）"
            )
        # Plain Vue
        return (
            "## Vue 3 强制开发规则（当前项目使用 Vue）\n"
            "\n"
            "### 绝对禁止\n"
            "1. 禁止使用 Options API → 统一使用 Composition API + `<script setup>`\n"
            "2. 禁止使用 `<a>` 做站内跳转 → 必须用 `<RouterLink>`\n"
            "3. 禁止用 `this.$refs` → 用 `ref()` / `useTemplateRef()`\n"
            "4. 禁止在 `<script setup>` 外调用 composables\n"
            "5. 禁止使用 Vuex → 用 Pinia 作为状态管理\n"
            "\n"
            "### 正确模式\n"
            '- 使用 `<script setup lang="ts">` 单文件组件\n'
            "- 路由用 Vue Router 4，状态管理用 Pinia\n"
            "- 数据获取封装到 composables (`use*.ts`)\n"
            "- 类型安全：Props 用 `defineProps<T>()`，Emits 用 `defineEmits<T>()`\n"
            "\n"
            "### 开始编码前必须做\n"
            "1. 确认使用 Vue 3 + Composition API\n"
            "2. 读取 `vite.config.ts` 了解已有配置\n"
            "3. 锁定组件库（如 Element Plus / Naive UI / Vuetify / PrimeVue）\n"
            "4. 锁定图标方案（如 `unplugin-icons` 或组件库内置图标）"
        )

    def _section_expert_mapping(self, **ctx: object) -> str:
        # Expert profiles are already embedded in static_intro via
        # _build_expert_profiles_section().  This section returns empty
        # so there is no duplication; the mapping table lives in static_intro.
        return ""

    def _section_execution_order(self, **ctx: object) -> str:
        name = ctx["name"]
        return f"""## 强制执行顺序

### 阶段 0. 同类产品研究（PM + ARCHITECT 专家主导）

> 以产品经理的市场洞察 + 架构师的技术评估双重视角工作

1. 如果当前宿主支持联网 / browse / search / web，请先使用宿主原生能力搜索与本需求相近的产品、官网、案例、文档或体验流程。
2. 同时读取当前项目内的本地知识上下文：
   - `knowledge/` 目录下与当前需求相关的知识文件
   - `output/{name}-research.md`
   - `output/knowledge-cache/{name}-knowledge-bundle.json`（若存在）
3. 对于本地知识库中命中的规范、清单、反模式、场景包、质量门禁，默认视为本项目硬约束，而不是可选参考。
3.1 如果 `output/knowledge-cache/{name}-knowledge-bundle.json` 中存在 `knowledge_application_plan`，必须按其中的阶段应用计划使用本地知识：
   - research 阶段只做对标研究和机会判断
   - PRD / Architecture / UIUX / Spec / Frontend / Backend / Quality / Delivery 各阶段分别继承对应知识条目
   - 标记为 hard constraints 的知识必须进入文档、Spec 或验收门禁
4. 至少总结以下内容后再进入 PRD：
   - 3 到 5 个同类产品或可借鉴对象
   - 共性功能模块
   - 关键用户流程与信息架构
   - 可借鉴的信任设计、商业化表达、交互模式
   - 不应照搬的缺点与本项目的差异化方向
5. 将研究结论写入 `output/{name}-research.md`，并在后续 PRD / 架构 / UIUX 中继承这些结论。

### 阶段 1. 冻结核心文档（PM + ARCHITECT + UI/UX 专家协作）

> PRD 由 PM 专家主导（关注用户价值、商业规则）；架构由 ARCHITECT 专家主导（关注技术选型、系统边界）；UIUX 由 UI/UX 设计师主导（关注视觉系统、组件规范、品牌一致性）

1. 先完整读取 `output/*-research.md`
1.0 先读取 `.super-dev/WORKFLOW.md` 与 `output/{name}-bootstrap.md`（若存在），确认该仓库已经完成 bootstrap，以及固定触发方式、阶段顺序和产物路径。
2. 再读取 `output/*-prd.md`
3. 再读取 `output/*-architecture.md`
4. 再读取 `output/*-uiux.md`
5. 再读取 `output/*-execution-plan.md`
6. 如果三份核心文档缺失，先补齐文档，不得直接创建 Spec 或开始编码。
7. 如果 `output/knowledge-cache/*-knowledge-bundle.json` 存在，必须先读取其中命中的 `local_knowledge`、`web_knowledge` 与 `research_summary`，并把这些结论继承到文档和实现中。

### 阶段 1.5. 文档确认门（强制暂停）

1. 完成 `output/*-prd.md`、`output/*-architecture.md`、`output/*-uiux.md` 后，必须先向用户汇报：
   - 三份文档路径
   - 每份文档的核心结论
   - 与 research 的承接关系
2. 明确要求用户做二选一反馈：
   - `确认进入 Spec / 开发`
   - `提出修改意见`
3. 如果用户提出修改意见，先只修改文档并再次汇报，不得跳过确认门。
4. **未经用户明确确认，不得创建 `.super-dev/changes/*`、不得开始前端、不得开始后端、不得声称进入实现阶段。**

### 阶段 2. 创建 Spec 与任务（PM + CODE 专家协作）

> 以产品经理的需求拆解能力 + 代码专家的技术评估能力协作

1. 仅在用户明确确认三份文档后，才允许创建 `.super-dev/changes/*/proposal.md` 与 `tasks.md`
2. Spec 必须完整继承 research、PRD、架构、UIUX 中已经冻结的结论
3. 创建 Spec 后，向用户说明本次 change id、任务总数、前后端实施顺序

### 阶段 3. 前端优先实现并运行验证（CODE + UI 专家协作）

> 以代码专家的工程能力 + UI 设计师的视觉标准协作，确保实现还原设计稿且代码质量达标

1. 依据 `.super-dev/changes/*/tasks.md` 先实现前端骨架、关键页面和核心交互
2. 前端必须先达到可运行、可演示、可审查状态，再进入后端主实现
3. 必须主动运行前端并修复明显错误，再向用户汇报预览方式、页面状态与剩余风险

### 阶段 4. 后端、联调、测试与交付（CODE + DBA + QA + DEVOPS 专家协作）

> 代码专家负责 API 实现，DBA 专家负责数据层和迁移，QA 专家负责测试策略，DEVOPS 专家负责部署配置

1. 在前端主流程可运行后，再实现后端 API、数据层、认证与联调
2. 每完成一项任务立即标记 `[x]`
3. 完成测试、质量门禁、交付清单后，才可以宣称项目完成

### 阶段 4.5. UI 改版返工（UI + UX 专家主导）

> 切换回 UI/UX 设计师身份，从设计系统层面重新审视，而不是从代码层面打补丁

1. 当用户明确表示 UI 不满意、需要改版、要重做视觉、页面太 AI 味时，禁止直接改 CSS 或局部样式。
2. 必须先回到 `output/*-uiux.md`，更新视觉方向、字体系统、版式节奏、组件状态、CTA 层级或信任设计。
3. 然后重做前端实现，并重新执行 frontend runtime 与 UI review。
4. 只有在 UI 改版通过后，才允许继续后续交付动作。

### 阶段 4.6. 架构返工（ARCHITECT + DBA 专家主导）

> 切换回架构师身份，从系统全局视角重新评估，而不是在实现层面打补丁

1. 当用户明确表示架构不合理、模块边界错误、技术方案需要重构、接口设计需要调整时，禁止直接跳到实现细节。
2. 必须先回到 `output/*-architecture.md`，更新系统边界、模块拆分、依赖关系、接口契约、容错与扩展方案。
3. 然后同步调整 Spec / tasks 与相关实现方案，再继续执行。
4. 只有在架构返工通过后，才允许恢复后续实施动作。

### 阶段 4.7. 质量返工（QA + SECURITY 专家主导）

> 切换回 QA 和安全专家身份，以质量和安全视角审视所有产出

1. 当用户明确表示质量不达标、安全问题未解决、交付证据不完整、测试或门禁结果不可接受时，禁止直接宣称完成。
2. 必须先修复相关质量问题，并重新执行 quality gate 与交付证据刷新。
3. 如问题涉及文档、架构或 UI，同步回写对应 `output/*` 文档。
4. 只有在质量返工通过后，才允许继续交付或恢复后续动作。

### 阶段 4.8. 缺陷修复轻量路径（RCA + CODE 专家协作）

> RCA 专家负责根因分析和风险评估，代码专家负责修复实现

1. 如果当前需求是修复已有问题，仍然必须输出文档，但文档应聚焦于：问题现象、复现条件、影响范围、根因假设、修复边界、回归风险。
2. 轻量 bugfix 文档也必须真实写入项目：
   - `output/*-research.md`：记录问题背景、历史行为、同类案例或错误上下文
   - `output/*-prd.md`：记录期望行为与验收条件
   - `output/*-architecture.md`：记录根因、受影响模块、回滚点与回归范围
   - `output/*-uiux.md`：若影响前端，则记录交互、状态或文案补丁
3. 未完成这些补丁文档前，不得直接跳到修复实现。
4. 修复后必须重新执行前端运行验证、测试、quality gate 与交付证据刷新。"""

    def _section_knowledge_constraints(self, **ctx: object) -> str:
        # Knowledge constraints are woven into execution_order (phase 0 steps 2-3)
        # and into session_context (expert section).  Return empty to avoid
        # duplication — the constraints are already present.
        return ""

    def _section_document_confirmation_gate(self, **ctx: object) -> str:
        # The confirmation gate is rendered inside execution_order as phase 1.5.
        # Return empty to avoid duplication.
        return ""

    def _section_implementation_rules(self, **ctx: object) -> str:
        ui_profile: dict = ctx["ui_profile"]  # type: ignore[assignment]
        research_content = cast(str | None, ctx.get("research_content"))
        prd_content = cast(str | None, ctx.get("prd_content"))
        arch_content = cast(str | None, ctx.get("arch_content"))
        uiux_content = cast(str | None, ctx.get("uiux_content"))
        plan_content = cast(str | None, ctx.get("plan_content"))
        frontend_blueprint = cast(str | None, ctx.get("frontend_blueprint"))
        return (
            f"""---

## 核心文档摘要

### 0. 研究报告

{self._excerpt(research_content, 1800) if research_content else f'请查看 output/{ctx["name"]}-research.md'}
...

### 1. PRD (产品需求文档)

{self._excerpt(prd_content, 1800) if prd_content else f'请查看 output/{ctx["name"]}-prd.md'}
...

### 2. 架构设计文档

{self._excerpt(arch_content, 1800) if arch_content else f'请查看 output/{ctx["name"]}-architecture.md'}
...

### 3. UI/UX 设计文档

{self._excerpt(uiux_content, 1800) if uiux_content else f'请查看 output/{ctx["name"]}-uiux.md'}
...

### 4. 执行路线图

{self._excerpt(plan_content, 1400) if plan_content else f'请查看 output/{ctx["name"]}-execution-plan.md'}
...

### 5. 前端蓝图

{self._excerpt(frontend_blueprint, 1400) if frontend_blueprint else f'请查看 output/{ctx["name"]}-frontend-blueprint.md'}
...

---

{self._build_expert_section()}

---

## 开发规范

### 代码规范

1. **遵循项目代码风格**
   - 使用 Prettier 格式化
   - 使用 ESLint 检查
   - 遵循现有命名规范

2. **提交规范**
   - Conventional Commits
   - 一个功能一个 commit
   - Commit message 清晰描述变更

3. **测试规范**
   - 单元测试覆盖率 > 80%
   - 每个功能点都有测试
   - 使用 pytest / jest

### 图标使用规范

**严格禁止**:
- 禁止使用 emoji 表情作为功能图标
- 不允许使用 emoji 来代替图标（如保存、搜索、设置）
- emoji 在不同平台显示不一致
- 可访问性差
- 不够专业

**图标使用标准**（按优先级）:
1. **首选**: UI 框架自带图标库
   - Vue: Element Plus、Naive UI、Vuetify 自带图标
   - React: Ant Design、Material-UI、Chakra UI 图标
   - 其他: 使用项目选择的 UI 库官方图标

2. **专业图标库**:
   - [Lucide Icons](https://lucide.dev/) - 推荐，轻量且现代
   - [Heroicons](https://heroicons.com/) - Tailwind CSS 官方
   - [Tabler Icons](https://tabler-icons.io/) - 开源免费
   - [Phosphor Icons](https://phosphoricons.com/) - 精美免费

3. **自定义 SVG**:
   - 如果需要自定义图标，使用 SVG 格式
   - 确保遵循无障碍标准（添加 aria-label）

**代码示例**:
```typescript
// 正确：使用图标库
import {{ Save, Search, Settings }} from 'lucide-react';
<button><Save size={{20}} />保存</button>

// 错误：使用 emoji
<button>💾 保存</button>
```

### 商业级 UI/UX 强制规则

1. 先定义视觉方向、字体系统、颜色 token、间距 token、栅格系统，再开始页面实现。
2. 页面必须体现真实商业产品的层级关系、数据密度与任务路径，禁止只会做大色块和浅层卡片。
3. 默认避免宿主自动滑向紫色/粉色渐变主视觉、默认系统字体直出和无品牌感模板页面；只有在品牌规范、用户明确要求或产品定位匹配时才允许采用，并必须说明理由。
4. 对于非对话式 AI 产品，默认避免复刻 Claude / ChatGPT 式界面骨架、灰黑侧栏聊天布局、窄中栏对话壳层与同款中性色配色；若用户明确要求或产品本身就是聊天工作台，可采用，但必须在 UI 方案里说明为什么适合。
5. 开始任何 UI 实现前，必须先明确本轮图标库（Lucide / Heroicons / Tabler / 官方组件图标）；未声明图标库视为不能开始写页面。
6. 不允许把"图标库约束"留到后面补充；如果发现页面里出现 emoji 或临时表情符号，必须先删干净再继续。
6.1 在向用户展示任何 UI 预览前，必须自检源码和预览里不存在任何 emoji 字符；一旦发现，先替换为正式图标库再继续。
7. 必须覆盖正常态、加载态、空态、错误态、禁用态、悬停态、聚焦态、成功反馈态。
8. 关键页面必须优先保证信息架构正确、CTA 清晰、转化路径明确、信任元素完整。
9. 先完成可用、可信、可演示的界面，再做装饰性视觉。

### 本项目 UI 实现基线

{self._render_ui_profile(ui_profile)}

### 宿主 UI 生成执行契约（必须遵守）

1. 必须先输出 **UI 方案草图说明**（信息架构、页面骨架、组件生态、token 策略）再写代码。
2. 每个关键页面必须提供 **2 个视觉方案**，并说明主方案取舍原因。
2.1 在开始实现前，必须明确输出：主视觉气质、版式骨架、字体组合、图标库、配色逻辑、明确不采用的参考方向。
3. 必须按 **Token → Primitive → Pattern → Surface** 四层实现，不允许直接散写样式。
4. 若使用 Shadcn / DaisyUI / Aceternity / Magic UI，必须先声明用途边界与替换策略，禁止混搭失控。
5. 页面完成后必须自检：状态矩阵、转化路径、信任模块、可访问性、性能预算。
6. 必须把技术细节转译成"目标-步骤-结果"，保证非技术与专业用户都能使用同一套交互。
7. 若目标端为 Web/H5/微信小程序/APP/桌面端，必须切换到对应生态（TDesign 小程序 / RN / Flutter / SwiftUI / Electron / Tauri）并遵循平台交互规范。
8. 实现结束前，必须再次检查源码和设计稿说明里不存在任何 emoji 功能图标，也不存在 Claude / ChatGPT 同款聊天壳层式布局借壳复用。

### 实现收尾与自审闭环（必须遵守）

1. 每轮代码修改完成后，必须先做一次最小 diff review，再汇报"已完成"。
2. 必须运行项目原生 `build / compile / type-check / test / runtime smoke`；如果某项不存在，要明确说明原因。
3. 对本轮新增的函数、方法、字段、组件、配置、日志埋点，必须逐项确认已经接入真实调用链；未接入则删除，不允许"先留着以后用"。
4. 严禁留下新增 `unused code`、未引用文件、只定义不调用的 helper、不可达分支或无效兜底逻辑。
5. 如果新增的是日志、恢复逻辑、告警、埋点，必须验证它们会在真实路径上触发，不能只把方法写进去却不挂到入口。
6. 结束汇报时必须说明：运行了哪些命令、修掉了哪些报错或 warning、还有哪些残余风险。

### 安全规范

1. **输入验证**: 所有用户输入必须验证
2. **SQL 注入**: 使用参数化查询
3. **XSS**: 输出转义
4. **认证**: JWT Token 认证"""
            + self._build_behavioral_prompts_section()
        )

    def _section_session_context(self, **ctx: object) -> str:
        change_content = ctx["change_content"]
        change_id = ctx["change_id"]
        return f"""---

## 文件结构

请按照以下结构组织代码：

```
project-root/
├── frontend/          # 前端代码
│   ├── src/
│   │   ├── components/  # 组件
│   │   ├── pages/       # 页面
│   │   ├── services/    # API 服务
│   │   └── utils/       # 工具函数
│   ├── package.json
│   └── vite.config.js
│
├── backend/           # 后端代码
│   ├── src/
│   │   ├── controllers/ # 控制器
│   │   ├── models/      # 数据模型
│   │   ├── services/    # 业务逻辑
│   │   ├── routes/      # 路由
│   │   └── utils/       # 工具函数
│   ├── package.json
│   └── tsconfig.json
│
└── shared/            # 共享代码
    ├── types/         # 类型定义
    └── constants/     # 常量
```

---

## 任务列表

{change_content}

---

## 开始实现

请从任务 1.1 开始，按顺序实现所有任务。

**每完成一个任务**:
1. 更新 `.super-dev/changes/{change_id}/tasks.md`
2. 将任务标记为 [x] 完成状态
3. 记录本次涉及的页面、组件、API、测试与风险
4. 提交代码 (可选)
5. 继续下一个任务

---

## 遇到问题？

如果遇到不清楚的地方：
1. 优先查看研究报告，确认借鉴项与差异化方向
2. 查看架构文档中的约束、边界和风险处理
3. 查看 PRD 中的需求说明与验收口径
4. 查看 UI/UX 文档中的页面结构、状态矩阵和设计 token"""

    def _section_compact_instructions(self, **ctx: object) -> str:
        # Compact instructions are reserved for future use by the context
        # compression system.  Return empty for now to keep the output
        # identical to the pre-refactor version.
        return ""

    def _section_flow_contract(self, **ctx: object) -> str:
        return """---

## 完成标准

所有任务完成后：
- [ ] 同类产品研究结论已落入文档与实现
- [ ] 所有功能正常运行
- [ ] 所有测试通过
- [ ] 代码符合规范
- [ ] 文档已更新
- [ ] UI 达到商业级完成度而不是模板化页面"""

    # ------------------------------------------------------------------
    # Helpers (preserved from original)
    # ------------------------------------------------------------------

    def _excerpt(self, content: str | None, limit: int) -> str:
        if not content:
            return ""
        collapsed = "\n".join(line.rstrip() for line in content.strip().splitlines())
        if len(collapsed) <= limit:
            return collapsed
        return collapsed[:limit].rstrip() + "\n[...内容已截断，请继续阅读源文档...]"

    # Mapping from ExpertRole value to NUMERIC_ANCHORS key for word-limit injection.
    _EXPERT_ANCHOR_MAP: dict[str, str] = {
        "PRODUCT": "research",
        "PM": "prd",
        "ARCHITECT": "architecture",
        "UI": "uiux",
        "SECURITY": "security",
        "CODE": "code",
        "QA": "prd",
    }

    def _build_expert_profiles_section(self) -> str:
        """构建专家画像段落，注入 AI 提示词"""
        # Use Markdown-defined expert profiles when available (supports user customization)
        if EXPERT_LOADER_AVAILABLE:
            try:
                profiles = load_expert_profiles(self.project_dir)
                if profiles:
                    # Use loaded profiles instead of hardcoded ones
                    # (loaded profiles include both builtin MD + hardcoded fallback)
                    pass  # profiles are already merged in load_expert_profiles()
            except Exception:
                pass  # Fall back to hardcoded profiles

        from ..orchestrator.experts import ExpertRole, get_expert_prompt_section

        key_experts = [
            ExpertRole.PRODUCT,
            ExpertRole.PM,
            ExpertRole.ARCHITECT,
            ExpertRole.UI,
            ExpertRole.SECURITY,
            ExpertRole.CODE,
            ExpertRole.QA,
        ]
        sections = []
        anchors = NUMERIC_ANCHORS if BEHAVIORAL_PROMPTS_AVAILABLE else {}
        for role in key_experts:
            section_text = get_expert_prompt_section(role)
            # Inject numeric anchor (word-limit) for the matching expert
            try:
                anchor_key = self._EXPERT_ANCHOR_MAP.get(role.value, "")
                anchor_text = anchors.get(anchor_key, "")
                if anchor_text:
                    section_text += f"\n**字数锚点**: {anchor_text}\n"
            except Exception:
                pass
            sections.append(section_text)

        # Append cross-review protocol
        sections.append(self._build_cross_review_protocol())

        return "\n".join(sections)

    @staticmethod
    def _build_cross_review_protocol() -> str:
        """构建交叉审查协议段落。"""
        return (
            "## 交叉审查协议\n\n"
            "每位专家在开始自己的工作前，**必须**遵守以下规则：\n\n"
            "1. 用 ≤3 句话总结上一位专家的输出，明确引用具体文件路径、"
            "决策编号或章节名称作为证据。\n"
            "2. **严禁**使用\u201c基于前面的分析\u201d等模糊引用——"
            "必须指明具体的文件（如 `output/xxx-architecture.md § 3.2`）"
            "或决策（如 `ADR-002`）。\n"
            "3. 如果上一位专家的结论与自身视角存在矛盾，"
            "必须显式指出冲突并给出裁决理由，不得静默忽略。\n"
        )

    def _build_behavioral_prompts_section(self) -> str:
        """Inject behavioral prompts when available."""
        if not BEHAVIORAL_PROMPTS_AVAILABLE:
            return ""
        try:
            behavioral_section = "\n\n## 行为约束（自动注入）\n\n"
            behavioral_section += "### 代码风格约束\n\n" + CODE_STYLE_DONTS + "\n\n"
            behavioral_section += "### 输出准确性约束\n\n" + FALSE_CLAIMS_DEFENSE + "\n\n"
            behavioral_section += "### 结构化输出格式\n\n" + STRUCTURED_OUTPUT_FORMAT + "\n\n"
            behavioral_section += "### 综合规则\n\n" + SYNTHESIS_RULES + "\n\n"
            return behavioral_section
        except Exception:
            return ""

    def _current_phase(self) -> str:
        """推断当前 pipeline 阶段（基于产出物是否存在）。"""
        output_dir = self.project_dir / "output"
        changes_dir = self.project_dir / ".super-dev" / "changes"

        # 按产出物反推当前阶段
        if not (output_dir / f"{self.name}-research.md").exists():
            return "research"
        if not (output_dir / f"{self.name}-prd.md").exists():
            return "docs"
        if not (output_dir / f"{self.name}-architecture.md").exists():
            return "docs"
        if not (output_dir / f"{self.name}-uiux.md").exists():
            return "docs"
        # 有文档但还没有 spec
        if not changes_dir.exists() or not any(changes_dir.iterdir()):
            return "spec"
        # 有 spec，推断前端/后端/质量/交付
        # 默认返回 frontend，让所有相关专家都激活
        return "frontend"

    def _get_active_experts_for_phase(self) -> dict:
        """根据当前阶段返回激活的专家工具箱。"""
        try:
            from ..experts.toolkit import PHASE_EXPERT_MAP

            phase = self._current_phase()
            expert_ids = PHASE_EXPERT_MAP.get(phase, [])
            return {eid: self._toolkits[eid] for eid in expert_ids if eid in self._toolkits}
        except Exception:
            return {}

    def _build_expert_section(self) -> str:
        """构建专家视角注入区域（多维度审查要求 + 检查清单 + 交叉审查指令）。"""
        if not self._toolkits:
            return ""

        try:
            active_experts = self._get_active_experts_for_phase()
        except Exception:
            return ""

        if not active_experts:
            return ""

        phase = self._current_phase()
        lines = ["## 专家视角（多维度审查要求）", ""]
        lines.append("在开发和审查过程中，请从以下专家视角进行检查：")
        lines.append("")

        for expert_id, toolkit in active_experts.items():
            lines.append(f"### {toolkit.name}（{expert_id}）视角")
            lines.append(toolkit.system_prompt_injection)
            lines.append("")

            # 注入 Playbook 核心条目
            if toolkit.playbook:
                lines.append("**核心方法论：**")
                for item in toolkit.playbook[:3]:
                    lines.append(f"- {item}")
                lines.append("")

            # 注入当前阶段的检查清单
            checklist = toolkit.phase_checklists.get(phase, [])
            if checklist:
                lines.append("**检查清单：**")
                for item in checklist[:10]:
                    lines.append(f"- [ ] {item}")
                lines.append("")

            # 注入专家的知识约束（通过 ExpertKnowledge.resolve）
            if hasattr(toolkit, "knowledge") and hasattr(toolkit.knowledge, "resolve"):
                try:
                    knowledge_dir = Path.cwd() / "knowledge"
                    if knowledge_dir.is_dir():
                        knowledge_files = toolkit.knowledge.resolve(knowledge_dir)
                        if knowledge_files:
                            lines.append(f"**知识约束** (来自 {len(knowledge_files)} 个知识文件):")
                            for kf in knowledge_files[:3]:
                                kf_path = Path(kf)
                                if kf_path.exists():
                                    try:
                                        content = kf_path.read_text(
                                            encoding="utf-8", errors="replace"
                                        )
                                        if "Agent Checklist" in content:
                                            cl_start = content.index("Agent Checklist")
                                            checklist_text = content[cl_start : cl_start + 500]
                                            lines.append(f"  从 {kf_path.name}:")
                                            for cl_line in checklist_text.split("\n")[2:8]:
                                                if cl_line.strip().startswith("- ["):
                                                    lines.append(f"  {cl_line.strip()}")
                                    except OSError:
                                        pass
                            lines.append("")
                except Exception:
                    pass

        # 知识约束提示
        lines.append("### 知识约束")
        lines.append(
            "如果 `knowledge/` 或 `output/knowledge-cache/` 中存在与当前阶段相关的规范、"
            "清单或反模式，必须视为硬约束纳入实现和审查，不得降级为可选参考。"
        )
        lines.append("")

        # 知识推送引擎注入（按阶段自动推送精准知识子集）
        try:
            from ..orchestrator.knowledge_pusher import KnowledgePusher

            knowledge_dir = self.project_dir / "knowledge"
            if knowledge_dir.is_dir():
                import yaml as _yaml  # type: ignore[import-untyped]

                _cfg_path = self.project_dir / "super-dev.yaml"
                _tech: dict = {}
                _project_description = ""
                if _cfg_path.exists():
                    with open(_cfg_path, encoding="utf-8") as _f:
                        _cfg = _yaml.safe_load(_f) or {}
                    _tech = {
                        "frontend": _cfg.get("frontend", ""),
                        "backend": _cfg.get("backend", ""),
                        "database": _cfg.get("database", ""),
                    }
                    _project_description = str(_cfg.get("description", ""))
                pusher = KnowledgePusher(
                    knowledge_dir=knowledge_dir,
                    tech_stack=_tech,
                    project_description=_project_description,
                )
                phase_push = pusher.get_phase_knowledge(phase)
                injection = phase_push.to_prompt_injection()
                if injection.strip():
                    lines.append(injection)
        except Exception:
            pass

        # 交叉审查指令（优先从 review_protocol 动态生成）
        try:
            from ..experts.review_protocol import CrossReviewEngine

            review_engine = CrossReviewEngine(self._toolkits)
            review_prompt = review_engine.generate_review_prompt(phase, "all")
            if review_prompt:
                lines.append("### 多专家交叉审查（自动生成）")
                lines.append(review_prompt[:2000])  # 限制长度
                lines.append("")
            else:
                raise ValueError("empty review prompt")
        except Exception:
            # 降级为静态文字
            lines.append("### 交叉审查要求")
            lines.append("完成每个阶段后，请从以下角度进行自我审查：")
            lines.append(
                "1. **安全专家**：是否存在安全漏洞？认证授权是否最小权限？输入校验是否完整？"
            )
            lines.append(
                "2. **QA专家**：验收标准是否可测试？关键路径是否有自动化测试？质量门禁是否达标？"
            )
            lines.append(
                "3. **DBA专家**：数据库设计是否合理？索引策略是否覆盖高频查询？迁移是否可回滚？"
            )
            lines.append("4. **产品负责人**：用户能否走通首次上手路径？功能闭环是否完整？")
            lines.append("")

        return "\n".join(lines)

    def _infer_product_type(self, description: str) -> str:
        text = description.lower()
        if any(
            word in text for word in ["dashboard", "仪表盘", "后台", "admin", "工作台", "workspace"]
        ):
            return "dashboard"
        if any(
            word in text for word in ["landing", "落地页", "营销页", "官网", "official website"]
        ):
            return "landing"
        if any(word in text for word in ["saas", "平台", "platform", "软件服务"]):
            return "saas"
        if any(word in text for word in ["商城", "电商", "store", "shop", "checkout"]):
            return "ecommerce"
        if any(word in text for word in ["博客", "内容", "blog", "cms", "文档"]):
            return "content"
        return "general"

    def _infer_industry(self, description: str) -> str:
        text = description.lower()
        if any(word in text for word in ["医疗", "健康", "health", "medical", "care"]):
            return "healthcare"
        if any(word in text for word in ["金融", "支付", "bank", "fintech", "结算"]):
            return "fintech"
        if any(word in text for word in ["教育", "培训", "education", "learning"]):
            return "education"
        if any(word in text for word in ["法律", "法务", "legal", "律师"]):
            return "legal"
        if any(word in text for word in ["政务", "government", "public"]):
            return "government"
        if any(word in text for word in ["美容", "美业", "wellness", "beauty", "spa"]):
            return "beauty"
        return "general"

    def _infer_style(self, description: str) -> str:
        text = description.lower()
        if any(word in text for word in ["极简", "minimal", "简约"]):
            return "minimal"
        if any(word in text for word in ["专业", "商务", "professional", "business"]):
            return "professional"
        if any(word in text for word in ["活泼", "playful", "fun"]):
            return "playful"
        if any(word in text for word in ["奢华", "premium", "luxury", "高端"]):
            return "luxury"
        return "modern"

    def _render_ui_profile(self, profile: dict) -> str:
        lib = profile.get("primary_library", {})
        stack = profile.get("component_stack", {})
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        style_direction = profile.get("style_direction", {})
        lines = [
            f"- **主视觉气质**: {style_direction.get('direction', 'N/A')}",
            f"- **材质/版式提示**: {style_direction.get('materials', 'N/A')}",
            f"- **字体组合**: {typography.get('heading', 'N/A')} / {typography.get('body', 'N/A')}",
            f"- **配色逻辑**: {palette.get('name', 'N/A')}（主色 {palette.get('primary', 'N/A')} / 强调色 {palette.get('accent', 'N/A')} / 背景 {palette.get('background', 'N/A')}）",
            f"- **首选组件生态**: {lib.get('name', 'N/A')}",
            f"- **表单与验证**: {stack.get('form', 'N/A')}",
            f"- **数据展示**: {stack.get('table', 'N/A')} / {stack.get('chart', 'N/A')}",
            f"- **图标体系**: {stack.get('icons', 'N/A')}",
            f"- **动效基线**: {stack.get('motion', 'N/A')}",
            f"- **页面定位**: {profile.get('surface', 'N/A')}",
            f"- **信息密度**: {profile.get('information_density', 'N/A')}",
            "",
            "**必须优先落实的模块**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("component_priorities", []))
        priorities = profile.get("design_system_priorities", [])
        if priorities:
            lines.extend(["", "**设计系统优先级**:"])
            lines.extend(f"- {item}" for item in priorities[:8])
        lines.extend(["", "**必须出现的信任/转化模块**:"])
        lines.extend(f"- {item}" for item in profile.get("trust_modules", [])[:8])
        state_requirements = profile.get("state_requirements", [])
        if state_requirements:
            lines.extend(["", "**状态矩阵要求**:"])
            lines.extend(f"- {item}" for item in state_requirements[:8])
        alternatives = profile.get("alternative_libraries", [])
        if alternatives:
            lines.extend(["", "**备选组件生态与适用边界**:"])
            for item in alternatives[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(f"- {item.get('name', 'N/A')}: {item.get('rationale', 'N/A')}")
        lines.extend(["", "**明确禁止**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:6])
        ui_matrix = profile.get("ui_library_matrix", [])
        if ui_matrix:
            lines.extend(["", "**多端组件库映射**:"])
            for row in ui_matrix[:5]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('scene', '-')}: {row.get('libraries', '-')}（重点：{row.get('focus', '-')}）"
                )
        quality = profile.get("quality_checklist", [])
        if quality:
            lines.extend(["", "**商业级 UI 交付清单**:"])
            lines.extend(f"- [ ] {item}" for item in quality[:8])
        pre_delivery = profile.get("pre_delivery_checklist", [])
        if pre_delivery:
            lines.extend(["", "**交付前核对项**:"])
            lines.extend(f"- [ ] {item}" for item in pre_delivery[:6])
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
            lines.extend(["", "- **平台差异/限制**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("platform_constraints", [])[:4]
            )
            lines.extend(["", "- **执行护栏**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("execution_guardrails", [])[:3]
            )
            anti_patterns = framework_playbook.get("anti_patterns", [])
            if anti_patterns:
                lines.extend(["", "- **框架级反模式**:"])
                lines.extend(f"- {item}" for item in anti_patterns[:3])
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if native_capabilities:
                lines.extend(["", "- **原生能力面**:"])
                lines.extend(f"- {item}" for item in native_capabilities[:3])
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if validation_surfaces:
                lines.extend(["", "- **必须验收的真实场景**:"])
                lines.extend(f"- {item}" for item in validation_surfaces[:3])
            delivery_evidence = framework_playbook.get("delivery_evidence", [])
            if delivery_evidence:
                lines.extend(["", "- **交付时必须沉淀的证据**:"])
                lines.extend(f"- {item}" for item in delivery_evidence[:3])
        keywords = profile.get("knowledge_keywords", [])
        if keywords:
            lines.extend(["", "**设计知识库关键词**:"])
            lines.append("- " + " / ".join(keywords[:10]))
        references = profile.get("design_references", [])
        if references:
            lines.extend(["", "**高质量设计参考锚点**:"])
            for item in references[:3]:
                if not isinstance(item, dict):
                    continue
                signals = " / ".join(item.get("signals", [])[:3])
                caution = "；".join(item.get("cautions", [])[:2])
                lines.append(
                    f"- {item.get('name', 'N/A')}: {item.get('rationale', 'N/A')} 参考信号：{signals or 'N/A'}。避免：{caution or 'N/A'}。"
                )
            lines.extend(
                [
                    "",
                    "**参考使用规则**:",
                    "- 参考锚点用于锁定气质、层级、留白、配色和组件骨架，不允许整站照抄单个品牌。",
                    "- 主方案必须明确吸收了哪些参考信号、又刻意避开了哪些参考品牌的套路。",
                ]
            )
        return "\n".join(lines)

    def _read_document(self, doc_type: str) -> str | None:
        """读取生成的文档"""
        doc_path = self.project_dir / "output" / f"{self.name}-{doc_type}.md"
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8", errors="ignore")
        return None

    def _read_change_spec(self) -> tuple[str, str]:
        """读取 Spec 变更内容"""
        from ..specs import ChangeManager

        change_manager = ChangeManager(self.project_dir)
        changes = change_manager.list_changes()

        if not changes:
            return "暂无 Spec，请先运行 super-dev spec init", "unknown-change"

        change = changes[0]

        content = f"""
### 变更: {change.id}

**描述**: {change.title}

**状态**: {change.status.value if hasattr(change.status, 'value') else change.status}

### 任务
"""

        tasks_path = self.project_dir / ".super-dev" / "changes" / change.id / "tasks.md"
        if tasks_path.exists():
            content += tasks_path.read_text(encoding="utf-8", errors="ignore")
        else:
            content += "\n请查看 tasks.md 文件"

        return content, change.id

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_task_specific_prompt(self, task_id: str) -> str:
        """为特定任务生成提示词"""
        from ..specs import ChangeManager

        change_manager = ChangeManager(self.project_dir)
        changes = change_manager.list_changes()

        if not changes:
            return "暂无 Spec，请先运行 super-dev spec init"

        change = changes[0]
        task = None
        for t in change.tasks:
            if t.id == task_id:
                task = t
                break

        if not task:
            return f"任务 {task_id} 不存在"

        return f"""# 任务 {task_id} - AI 开发提示词

## 任务信息

**ID**: {task.id}
**名称**: {task.title}
**状态**: {task.status.value if hasattr(task.status, 'value') else task.status}

## 描述

{task.description}

## 要求

1. 实现此任务的所有要求
2. 遵循项目架构规范
3. 编写相应的测试
4. 完成后更新任务状态为 [x]

## 参考文档

- `output/{self.name}-prd.md`
- `output/{self.name}-architecture.md`
- `output/{self.name}-uiux.md`

请开始实现。"""

    def generate_review_prompt(self) -> str:
        """生成代码审查提示词"""
        return f"""# {self.name} - 代码审查提示词

请对 {self.name} 项目进行全面代码审查。

## 审查重点

1. **功能完整性**
   - 所有需求是否已实现
   - 业务逻辑是否正确

2. **代码质量**
   - 代码结构是否清晰
   - 是否遵循最佳实践
   - 是否有重复代码

3. **安全性**
   - 是否有安全漏洞
   - 输入验证是否完整
   - 权限控制是否正确

4. **性能**
   - 是否有性能瓶颈
   - 数据库查询是否优化
   - 前端渲染是否高效

5. **测试覆盖**
   - 测试是否充分
   - 边界情况是否覆盖

请输出详细的审查报告。"""

    def get_pending_tasks(self) -> list[dict]:
        """获取待完成任务"""
        from ..specs import ChangeManager

        change_manager = ChangeManager(self.project_dir)
        changes = change_manager.list_changes()

        if not changes:
            return []

        change = changes[0]
        pending = []

        for task in change.tasks:
            if task.status != TaskStatus.COMPLETED:
                pending.append(
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": (
                            task.status.value if hasattr(task.status, "value") else task.status
                        ),
                    }
                )

        return pending
