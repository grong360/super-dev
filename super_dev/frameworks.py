"""Shared frontend framework normalization and playbook helpers."""

from __future__ import annotations

from typing import Any

FRONTEND_ALIASES: dict[str, str] = {
    "uniapp": "miniapp",
    "uni-app": "miniapp",
    "taro": "miniapp",
    "miniapp": "miniapp",
    "mp-weixin": "miniapp",
    "wechat-miniprogram": "miniapp",
    "miniprogram": "miniapp",
    "weapp": "miniapp",
    "expo": "react-native",
    "react-native": "react-native",
    "flutter": "flutter",
    "electron": "desktop",
    "tauri": "desktop",
    "wails": "desktop",
    "ionic": "hybrid-mobile",
    "capacitor": "hybrid-mobile",
    "desktop": "desktop",
}

CROSS_PLATFORM_FRONTENDS = {"miniapp", "react-native", "flutter", "desktop", "hybrid-mobile"}

FRAMEWORK_PLAYBOOK_REQUIRED_LISTS = (
    "implementation_modules",
    "platform_constraints",
    "execution_guardrails",
    "native_capabilities",
    "validation_surfaces",
    "delivery_evidence",
)


def normalize_frontend(frontend: str) -> str:
    lowered = str(frontend or "").strip().lower()
    return FRONTEND_ALIASES.get(lowered, lowered)


def is_cross_platform_frontend(frontend: str) -> bool:
    return normalize_frontend(frontend) in CROSS_PLATFORM_FRONTENDS


def framework_playbook_complete(playbook: dict[str, Any]) -> bool:
    if not isinstance(playbook, dict) or not playbook:
        return False
    return bool(playbook.get("framework")) and all(
        isinstance(playbook.get(name), list) and bool(playbook.get(name))
        for name in FRAMEWORK_PLAYBOOK_REQUIRED_LISTS
    )


def summarize_framework_playbook(playbook: dict[str, Any], limit: int = 4) -> dict[str, Any]:
    if not isinstance(playbook, dict) or not playbook:
        return {}
    return {
        "framework": str(playbook.get("framework", "")).strip(),
        "implementation_modules": [
            str(item).strip()
            for item in playbook.get("implementation_modules", [])
            if str(item).strip()
        ][:limit],
        "platform_constraints": [
            str(item).strip()
            for item in playbook.get("platform_constraints", [])
            if str(item).strip()
        ][:limit],
        "execution_guardrails": [
            str(item).strip()
            for item in playbook.get("execution_guardrails", [])
            if str(item).strip()
        ][:limit],
        "native_capabilities": [
            str(item).strip()
            for item in playbook.get("native_capabilities", [])
            if str(item).strip()
        ][:limit],
        "validation_surfaces": [
            str(item).strip()
            for item in playbook.get("validation_surfaces", [])
            if str(item).strip()
        ][:limit],
        "delivery_evidence": [
            str(item).strip() for item in playbook.get("delivery_evidence", []) if str(item).strip()
        ][:limit],
    }
