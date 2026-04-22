"""项目模板 — 预设的技术栈组合，加速 init 过程。"""

from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {
    "ecommerce": {
        "description": "电商平台",
        "platform": "web",
        "frontend": "next",
        "backend": "node",
        "database": "postgresql",
        "domain": "ecommerce",
        "ui_library": "shadcn-ui",
        "style": "tailwind",
        "state": "zustand",
        "testing": "vitest",
    },
    "saas": {
        "description": "SaaS 应用",
        "platform": "web",
        "frontend": "next",
        "backend": "node",
        "database": "postgresql",
        "domain": "saas",
        "ui_library": "shadcn-ui",
        "style": "tailwind",
        "state": "zustand",
        "testing": "vitest",
    },
    "dashboard": {
        "description": "数据仪表盘",
        "platform": "web",
        "frontend": "react-vite",
        "backend": "python",
        "database": "postgresql",
        "domain": "",
        "ui_library": "ant-design",
        "style": "tailwind",
        "state": "react-query",
        "testing": "vitest",
    },
    "mobile": {
        "description": "移动应用",
        "platform": "mobile",
        "frontend": "expo",
        "backend": "node",
        "database": "postgresql",
        "domain": "",
        "ui_library": "tailwind",
        "style": "tailwind",
        "state": "zustand",
        "testing": "jest",
    },
    "api": {
        "description": "纯 API 服务",
        "platform": "web",
        "frontend": "none",
        "backend": "python",
        "database": "postgresql",
        "domain": "",
        "ui_library": "tailwind",
        "style": "tailwind",
        "state": "",
        "testing": "vitest",
    },
    "blog": {
        "description": "博客 / 内容站",
        "platform": "web",
        "frontend": "astro",
        "backend": "none",
        "database": "",
        "domain": "content",
        "ui_library": "tailwind",
        "style": "tailwind",
        "state": "",
        "testing": "vitest",
    },
    "miniapp": {
        "description": "微信小程序",
        "platform": "wechat",
        "frontend": "uni-app",
        "backend": "node",
        "database": "postgresql",
        "domain": "",
        "ui_library": "element-plus",
        "style": "scss",
        "state": "pinia",
        "testing": "vitest",
    },
}


def list_templates() -> list[dict[str, str]]:
    """列出所有可用模板。"""
    return [
        {"name": name, "description": t["description"], "stack": f"{t['frontend']}+{t['backend']}"}
        for name, t in TEMPLATES.items()
    ]


def get_template(name: str) -> dict[str, str] | None:
    """获取指定模板的配置。"""
    return TEMPLATES.get(name)
