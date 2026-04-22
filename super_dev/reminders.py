"""
关键约束提醒系统 — 数据驱动的规则持续强化。

核心设计原则（成熟产品模式）:
  - 技术栈规则从 knowledge/ 文件加载，不写死在代码中
  - 图标/emoji 策略从 super-dev.yaml 配置加载，可覆盖默认值
  - 项目级自定义约束从 .super-dev/reminders/ 加载
  - 代码只提供加载、合并、注入机制，不提供具体规则内容

数据源优先级:
  1. .super-dev/reminders/*.md (项目级自定义，最高优先级)
  2. knowledge/{domain}/01-standards/{tech}.md (知识库)
  3. super-dev.yaml → ui.icon_policy / ui.style_policy (配置)
  4. 内置默认值 (最低优先级，仅在所有数据源缺失时使用)
"""

from __future__ import annotations

from pathlib import Path

# ─────────────────────────────────────────────────────────
# 标签格式化
# ─────────────────────────────────────────────────────────


def format_system_reminder(text: str) -> str:
    """用 <system-reminder> 标签包装约束文本。"""
    return f"<system-reminder>\n{text.strip()}\n</system-reminder>"


# ─────────────────────────────────────────────────────────
# 知识库驱动的技术栈规则加载
# ─────────────────────────────────────────────────────────

# 前端技术 → knowledge 文件名映射
# 前端技术 → knowledge/frontend/01-standards/ 文件名
_FRONTEND_KNOWLEDGE_MAP: dict[str, str] = {
    "next": "nextjs-complete.md",
    "nextjs": "nextjs-complete.md",
    "next.js": "nextjs-complete.md",
    "nuxt": "vue3-complete.md",
    "nuxtjs": "vue3-complete.md",
    "vue": "vue-complete.md",
    "vue3": "vue3-complete.md",
    "react": "react-complete.md",
    "react-vite": "react-complete.md",
    "remix": "react-complete.md",  # Remix 基于 React
    "gatsby": "react-complete.md",  # Gatsby 基于 React
    "solid": "react-complete.md",  # Solid 语法类似 React
}

# 后端技术 → knowledge/backend/01-standards/ 文件名
_BACKEND_KNOWLEDGE_MAP: dict[str, str] = {
    "python": "fastapi-complete.md",
    "fastapi": "fastapi-complete.md",
    "django": "django-complete.md",
    "flask": "fastapi-complete.md",  # Flask 和 FastAPI 同生态
    "node": "nestjs-complete.md",
    "nestjs": "nestjs-complete.md",
    "express": "nestjs-complete.md",  # Express 知识在 NestJS 中涵盖
    "java": "spring-boot-complete.md",
    "spring": "spring-boot-complete.md",
    "go": "",  # 待补充
    "rust": "",  # 待补充
}


def load_tech_stack_knowledge(
    frontend: str,
    knowledge_dir: Path | None = None,
    max_chars: int = 8000,
) -> str:
    """从 knowledge/ 加载技术栈知识文件。

    数据驱动：规则内容在 knowledge/ Markdown 文件中维护，
    不写死在 Python 代码里。添加新技术栈只需：
      1. 在 knowledge/frontend/01-standards/ 放一个 {tech}-complete.md
      2. 在 _FRONTEND_KNOWLEDGE_MAP 加一行映射

    Args:
        frontend: 前端技术名 (next/vue/react 等)
        knowledge_dir: knowledge/ 目录路径 (None 则自动检测)
        max_chars: 最大注入字符数 (防止过长)

    Returns:
        技术栈知识文本（截断到 max_chars）
    """
    key = frontend.lower().strip()
    filename = _FRONTEND_KNOWLEDGE_MAP.get(key)
    if not filename:
        return ""

    if knowledge_dir is None:
        # 尝试从当前工作目录和项目目录查找
        for candidate in [Path.cwd() / "knowledge", Path.cwd().parent / "knowledge"]:
            if candidate.is_dir():
                knowledge_dir = candidate
                break
    if knowledge_dir is None:
        return ""

    filepath = knowledge_dir / "frontend" / "01-standards" / filename
    if not filepath.exists():
        return ""

    try:
        content = filepath.read_text(encoding="utf-8")
        if len(content) > max_chars:
            content = (
                content[:max_chars] + "\n\n[... 知识文件截断，完整内容见 " + str(filepath) + " ...]"
            )
        return f"## 前端技术栈参考（来自项目知识库）\n\n{content}"
    except (OSError, UnicodeDecodeError):
        return ""


def load_backend_knowledge(
    backend: str,
    knowledge_dir: Path | None = None,
    max_chars: int = 6000,
) -> str:
    """从 knowledge/backend/01-standards/ 加载后端技术栈知识。"""
    key = backend.lower().strip()
    filename = _BACKEND_KNOWLEDGE_MAP.get(key, "")
    if not filename:
        return ""

    if knowledge_dir is None:
        for candidate in [Path.cwd() / "knowledge", Path.cwd().parent / "knowledge"]:
            if candidate.is_dir():
                knowledge_dir = candidate
                break
    if knowledge_dir is None:
        return ""

    filepath = knowledge_dir / "backend" / "01-standards" / filename
    if not filepath.exists():
        return ""

    try:
        content = filepath.read_text(encoding="utf-8")
        if len(content) > max_chars:
            content = (
                content[:max_chars] + "\n\n[... 知识文件截断，完整内容见 " + str(filepath) + " ...]"
            )
        return f"## 后端技术栈参考（来自项目知识库）\n\n{content}"
    except (OSError, UnicodeDecodeError):
        return ""


# ─────────────────────────────────────────────────────────
# 配置驱动的 UI 策略加载
# ─────────────────────────────────────────────────────────

_DEFAULT_ICON_POLICY = (
    "功能图标只能来自 Lucide / Heroicons / Tabler 图标库。"
    "绝对禁止使用 emoji 表情作为功能图标、装饰图标或临时占位。"
    "如果你即将输出包含 emoji 的 UI 代码，停下来，改用图标库组件。"
    "在向用户展示 UI 代码前，自检源码中不存在 emoji 字符。"
)

_DEFAULT_STYLE_POLICY = (
    "禁止紫/粉渐变主色调。禁止 emoji 图标。"
    "禁止无信息层级的卡片墙。禁止默认系统字体直出。"
    "不允许'先用 emoji 顶上后面再换'。"
)


def load_ui_policy(project_dir: Path | None = None) -> dict[str, str]:
    """从 super-dev.yaml 加载 UI 策略配置。

    配置示例 (super-dev.yaml):
    ```yaml
    ui:
      icon_policy: "功能图标使用 Phosphor Icons，允许品牌 emoji"
      style_policy: "允许渐变但必须与品牌色一致"
      icon_library: "phosphor-react"
    ```

    未配置时使用内置默认值。
    """
    icon_policy = _DEFAULT_ICON_POLICY
    style_policy = _DEFAULT_STYLE_POLICY
    icon_library = "Lucide"

    if project_dir:
        config_path = project_dir / "super-dev.yaml"
        if config_path.exists():
            try:
                import yaml  # type: ignore[import-untyped]

                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                ui_config = config.get("ui", {})
                if isinstance(ui_config, dict):
                    if ui_config.get("icon_policy"):
                        icon_policy = str(ui_config["icon_policy"])
                    if ui_config.get("style_policy"):
                        style_policy = str(ui_config["style_policy"])
                    if ui_config.get("icon_library"):
                        icon_library = str(ui_config["icon_library"])
            except Exception:
                pass

    return {
        "icon_policy": icon_policy,
        "style_policy": style_policy,
        "icon_library": icon_library,
    }


# ─────────────────────────────────────────────────────────
# 项目级自定义提醒加载
# ─────────────────────────────────────────────────────────


def load_project_reminders(project_dir: Path | None = None) -> str:
    """从 .super-dev/reminders/*.md 加载项目级自定义约束。

    用户可以在此目录放置任意 .md 文件，内容会被合并注入到 prompt。
    例如：
      .super-dev/reminders/brand-rules.md — 品牌视觉约束
      .super-dev/reminders/api-conventions.md — API 命名约定
      .super-dev/reminders/security-policy.md — 安全策略
    """
    if not project_dir:
        return ""

    reminders_dir = project_dir / ".super-dev" / "reminders"
    if not reminders_dir.is_dir():
        return ""

    parts: list[str] = []
    for md_file in sorted(reminders_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)
        except (OSError, UnicodeDecodeError):
            continue

    if not parts:
        return ""
    return "## 项目自定义约束\n\n" + "\n\n---\n\n".join(parts)


# ─────────────────────────────────────────────────────────
# 主入口：构建完整提醒
# ─────────────────────────────────────────────────────────


def build_full_reminders(
    frontend: str = "",
    backend: str = "",
    project_dir: Path | None = None,
    knowledge_dir: Path | None = None,
) -> str:
    """构建完整的关键约束提醒。

    数据源合并顺序：
      1. 核心约束（始终存在）
      2. UI 策略（从 config 或默认值）
      3. 前端技术栈知识（从 knowledge/frontend/ 加载）
      4. 后端技术栈知识（从 knowledge/backend/ 加载）
      5. 项目自定义提醒（从 .super-dev/reminders/ 加载）

    Args:
        frontend: 前端技术名
        backend: 后端技术名
        project_dir: 项目根目录
        knowledge_dir: knowledge/ 目录 (None 自动检测)
    """
    ui_policy = load_ui_policy(project_dir)

    parts: list[str] = []

    # 1. 核心约束
    parts.append(
        "## 关键约束提醒（每次操作前必读）\n\n"
        "⛔ 以下规则在整个开发过程中始终有效，不得以任何理由违反：\n\n"
        f"1. **图标系统**: {ui_policy['icon_policy']}\n\n"
        f"2. **视觉风格**: {ui_policy['style_policy']}\n\n"
        "3. **代码纪律**: 不要添加没被要求的功能。不要为不可能的场景添加错误处理。"
        "不要为一次性操作创建抽象。三行相似代码好过一个过早的抽象。\n\n"
        "4. **自检规则**: 在向用户展示任何 UI 代码或预览前，"
        "必须自检源码中不存在 emoji 字符。发现后先替换为正式图标库再继续。\n\n"
        "5. **输出准确性**: 如果测试失败就说失败。不要声称'所有测试通过'当输出显示失败。"
    )

    # 2. 前端技术栈知识（从文件加载，不写死）
    if knowledge_dir is None and project_dir:
        knowledge_dir = project_dir / "knowledge"
    tech_knowledge = load_tech_stack_knowledge(frontend, knowledge_dir)
    if tech_knowledge:
        parts.append(tech_knowledge)

    # 3. 后端技术栈知识（从文件加载）
    backend_knowledge = load_backend_knowledge(backend, knowledge_dir)
    if backend_knowledge:
        parts.append(backend_knowledge)

    # 4. 项目自定义提醒
    project_reminders = load_project_reminders(project_dir)
    if project_reminders:
        parts.append(project_reminders)

    return "\n\n".join(parts)
