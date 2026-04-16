"""
Host Hooks Generator — auto-generate host-specific hook configurations.

Generates hook configs for Claude Code (settings.local.json), Kiro,
Cursor, and generic shell hook scripts from Super Dev governance rules.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.hooks_generator")

_HOOK_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
\"\"\"Auto-generated Super Dev enforcement hook.

This script is called by the host's hook system when specific events fire.
It validates file writes, commands, and other tool uses against Super Dev rules.
\"\"\"

import json
import re
import sys
from pathlib import Path


def check_no_emoji_icons(file_path: str) -> list[str]:
    \"\"\"Check that no emoji characters are used as icons.\"\"\"
    violations = []
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        emoji_pattern = re.compile(
            "["
            "\\U0001F600-\\U0001F64F"
            "\\U0001F300-\\U0001F5FF"
            "\\U0001F680-\\U0001F6FF"
            "\\U0001F1E0-\\U0001F1FF"
            "\\u2600-\\u27BF"
            "]+",
            re.UNICODE,
        )
        for match in emoji_pattern.finditer(content):
            violations.append(f"Emoji icon found: {{match.group()}}")
    except OSError:
        pass
    return violations


def check_frontend_file(file_path: str) -> list[str]:
    \"\"\"Check frontend-specific rules.\"\"\"
    violations = []
    ext = Path(file_path).suffix
    if ext not in (".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"):
        return violations

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")

        # Check for hardcoded colors
        hex_pattern = re.compile(
            r"(?:color|background|border|bg)\\s*[:-]\\s*['\"]?(#[0-9a-fA-F]{{3,8}})['\"]?",
            re.IGNORECASE,
        )
        for match in hex_pattern.finditer(content):
            violations.append(f"Hardcoded hex color: {{match.group(1)}}")

    except OSError:
        pass
    return violations


def main():
    tool_input = json.loads(sys.stdin.read())
    file_path = tool_input.get("file_path", "")

    all_violations = []
    all_violations.extend(check_no_emoji_icons(file_path))
    all_violations.extend(check_frontend_file(file_path))

    if all_violations:
        print(f"Super Dev violations detected in {{file_path}}:", file=sys.stderr)
        for v in all_violations:
            print(f"  - {{v}}", file=sys.stderr)
        sys.exit(2)  # Block the tool use

    sys.exit(0)


if __name__ == "__main__":
    main()
"""


@dataclass
class HostHookConfig:
    """Hook configuration for a specific host."""

    host_id: str
    host_name: str
    config_path: str
    config_content: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "host_name": self.host_name,
            "config_path": self.config_path,
            "config_content": self.config_content,
        }


def _build_claude_code_hooks(project_dir: Path) -> HostHookConfig:
    """Generate Claude Code hooks config (settings.local.json format)."""
    hooks_dir = project_dir / ".claude"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Ensure scripts directory exists for hook scripts
    scripts_dir = project_dir / ".claude" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    hook_script_path = scripts_dir / "super-dev-enforce.py"
    hook_script_path.write_text(_HOOK_SCRIPT_TEMPLATE, encoding="utf-8")
    hook_script_path.chmod(hook_script_path.stat().st_mode | 0o755)

    config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {hook_script_path}",
                        }
                    ],
                }
            ],
        }
    }

    return HostHookConfig(
        host_id="claude-code",
        host_name="Claude Code",
        config_path=str(hooks_dir / "settings.local.json"),
        config_content=config,
    )


def _build_kiro_hooks(project_dir: Path) -> HostHookConfig:
    """Generate Kiro agent hooks config."""
    kiro_dir = project_dir / ".kiro"
    hooks_dir = kiro_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_content = """# Super Dev enforcement hooks for Kiro
#
# These hooks fire after code generation events and validate
# the output against Super Dev governance rules.

onFileCreated:
  - pattern: "**/*.{tsx,jsx,vue,svelte}"
    action: validate-frontend
    description: "Validate frontend files against UIUX spec"

onFileModified:
  - pattern: "**/*.{tsx,jsx,vue,svelte,css,scss}"
    action: check-no-emoji
    description: "Check for emoji icons in frontend code"
"""
    hook_path = hooks_dir / "super-dev-hooks.yaml"
    hook_path.write_text(hook_content, encoding="utf-8")

    return HostHookConfig(
        host_id="kiro",
        host_name="Kiro",
        config_path=str(hook_path),
        config_content={"hooks_yaml": hook_content},
    )


def _build_cursor_hooks(project_dir: Path) -> HostHookConfig:
    """Generate Cursor rules for enforcement."""
    rules_dir = project_dir / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rule_content = """---
description: Super Dev enforcement rules
globs: ["**/*.{tsx,jsx,vue,svelte,css,scss}"]
---

# Super Dev Enforcement Rules

## Icon Rules
- NEVER use emoji characters as functional icons
- ONLY use icons from the declared icon library (Lucide/Heroicons/Tabler)
- All icon imports must come from the declared icon package

## Color Rules
- NEVER hardcode hex/rgb color values in component files
- Use CSS custom properties (design tokens) for all colors
- No purple/pink gradient themes

## Component Rules
- Frontend fetch URLs must match backend route definitions exactly
- Define API paths as shared constants when possible
"""

    rule_path = rules_dir / "super-dev-enforcement.mdc"
    rule_path.write_text(rule_content, encoding="utf-8")

    return HostHookConfig(
        host_id="cursor",
        host_name="Cursor",
        config_path=str(rule_path),
        config_content={"rule_content": rule_content},
    )


def _build_generic_hooks(project_dir: Path) -> HostHookConfig:
    """Generate generic shell hook scripts."""
    hooks_dir = project_dir / "scripts"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    script_content = """#!/usr/bin/env bash
# Super Dev enforcement hook — validates files before commit.
# Usage: bash scripts/super-dev-pre-commit.sh <file_path>

set -euo pipefail

FILE="${1:-}"
if [ -z "$FILE" ]; then
    echo "Usage: $0 <file_path>" >&2
    exit 1
fi

EXT="${FILE##*.}"
VIOLATIONS=0

# Check for emoji in frontend files
case "$EXT" in
    tsx|jsx|vue|svelte|css|scss)
        if grep -qP '[\\x{2600}-\\x{27BF}\\x{1F300}-\\x{1FAFF}]' "$FILE" 2>/dev/null; then
            echo "VIOLATION: Emoji icon found in $FILE" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
        fi

        # Check for hardcoded hex colors
        if grep -qP '(?:color|background|border|bg)\\s*[:-]\\s*['"'"'"]?(#[0-9a-fA-F]{3,8})' "$FILE" 2>/dev/null; then
            echo "VIOLATION: Hardcoded hex color in $FILE" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
        ;;
esac

if [ "$VIOLATIONS" -gt 0 ]; then
    echo "Total violations: $VIOLATIONS. Commit blocked." >&2
    exit 1
fi

echo "Super Dev enforcement: $FILE passed."
exit 0
"""
    script_path = hooks_dir / "super-dev-pre-commit.sh"
    script_path.write_text(script_content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | 0o755)

    return HostHookConfig(
        host_id="generic",
        host_name="Generic (shell hooks)",
        config_path=str(script_path),
        config_content={"script_path": str(script_path)},
    )


# Registry of all host hook generators
_HOST_GENERATORS: dict[str, type] = {}
# We use functions instead of classes for simplicity
_HOST_GENERATOR_FUNCS: dict[str, Any] = {
    "claude-code": _build_claude_code_hooks,
    "kiro": _build_kiro_hooks,
    "cursor": _build_cursor_hooks,
    "generic": _build_generic_hooks,
}


@dataclass
class HooksGenerationResult:
    """Result of generating hooks for all hosts."""

    generated: list[HostHookConfig] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated": [g.to_dict() for g in self.generated],
            "errors": self.errors,
        }


def generate_host_hooks(
    project_dir: Path,
    hosts: list[str] | None = None,
    dry_run: bool = False,
) -> HooksGenerationResult:
    """Generate hook configurations for specified hosts.

    Args:
        project_dir: Project root directory.
        hosts: List of host IDs to generate for. None = all.
        dry_run: If True, return configs without writing files.

    Returns:
        HooksGenerationResult with generated configs.
    """
    result = HooksGenerationResult()

    target_hosts = hosts or list(_HOST_GENERATOR_FUNCS.keys())

    for host_id in target_hosts:
        gen_func = _HOST_GENERATOR_FUNCS.get(host_id)
        if not gen_func:
            result.errors.append(f"Unknown host: {host_id}")
            continue

        try:
            config = gen_func(project_dir)
            result.generated.append(config)

            if not dry_run:
                # Write the config
                config_path = Path(config.config_path)
                if config_path.suffix == ".json":
                    # Merge with existing settings
                    existing: dict[str, Any] = {}
                    if config_path.exists():
                        try:
                            existing = json.loads(config_path.read_text(encoding="utf-8"))
                        except (json.JSONDecodeError, OSError):
                            existing = {}

                    # Deep merge hooks
                    if "hooks" in config.config_content:
                        if "hooks" not in existing:
                            existing["hooks"] = {}
                        for event, hooks_list in config.config_content["hooks"].items():
                            if event not in existing["hooks"]:
                                existing["hooks"][event] = hooks_list

                    config_path.write_text(
                        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    _logger.info("Generated hooks for %s at %s", host_id, config_path)

        except Exception as e:
            result.errors.append(f"Error generating hooks for {host_id}: {e}")
            _logger.error("Error generating hooks for %s: %s", host_id, e)

    return result
