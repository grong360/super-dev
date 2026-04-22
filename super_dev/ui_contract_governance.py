from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CLAUDE_DESIGN_RUNTIME_CHECKS: dict[str, str] = {
    "ui_screen_recipes": "screen_recipes",
    "ui_design_context_protocol": "design_context_protocol",
    "ui_tweak_strategy": "tweak_strategy",
    "ui_verification_handoff": "verification_handoff",
}


def ui_contract_requires_claude_design_runtime(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    return any(
        bool(payload.get(field_name))
        for field_name in CLAUDE_DESIGN_RUNTIME_CHECKS.values()
    )


def required_claude_design_runtime_checks(payload: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not ui_contract_requires_claude_design_runtime(payload):
        return ()
    return tuple(CLAUDE_DESIGN_RUNTIME_CHECKS.keys())


def missing_claude_design_runtime_checks(
    checks: Mapping[str, Any] | None,
    payload: Mapping[str, Any] | None,
) -> list[str]:
    if not isinstance(checks, Mapping):
        checks = {}
    return [
        check_name
        for check_name in required_claude_design_runtime_checks(payload)
        if not bool(checks.get(check_name, False))
    ]
