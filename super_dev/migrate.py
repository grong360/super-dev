"""版本迁移工具。"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from . import __version__
from .integrations import IntegrationManager
from .integrations.install_manifest import load_install_manifest, record_install_manifest


def _legacy_skill_alias() -> str:
    return "super-dev" + "-core"


def _legacy_agent_file() -> str:
    return _legacy_skill_alias() + ".md"


def _detect_onboarded_hosts(project_dir: Path) -> list[str]:
    """检测项目中已经接入过的宿主。"""
    mgr = IntegrationManager(project_dir=project_dir)
    manifest = load_install_manifest(project_dir)
    manifest_targets = manifest.get("targets", {})
    if isinstance(manifest_targets, dict) and manifest_targets:
        resolved: list[str] = []
        for raw_target, item in manifest_targets.items():
            if not isinstance(item, dict):
                continue
            target = str(item.get("host", "")).strip() or str(raw_target).strip()
            if target in mgr.TARGETS and target not in resolved:
                resolved.append(target)
        if resolved:
            return resolved

    families: dict[str, list[str]] = {}
    for target_name in mgr.TARGETS:
        markers = IntegrationManager.target_detection_markers(target_name)
        if not markers:
            continue
        if any((project_dir / marker).exists() for marker in markers):
            family = IntegrationManager.host_family(target_name)
            families.setdefault(family, []).append(target_name)

    detected: list[str] = []
    for family, candidates in families.items():
        preferred = IntegrationManager.preferred_target_for_family(family, candidates)
        if preferred in mgr.TARGETS and preferred not in detected:
            detected.append(preferred)
    return detected


def _cleanup_claude_code_legacy(project_dir: Path, changes: list[str]) -> None:
    """清理 Claude Code 旧版技能别名残留。"""
    legacy_paths = [
        Path.home() / ".claude" / "skills" / _legacy_skill_alias(),
        Path.home() / ".claude" / "agents" / _legacy_agent_file(),
        project_dir / ".claude" / "agents" / _legacy_agent_file(),
    ]
    for legacy in legacy_paths:
        if legacy.exists():
            try:
                if legacy.is_dir():
                    shutil.rmtree(legacy)
                else:
                    legacy.unlink()
                changes.append(f"已清理旧版残留: {legacy.name}")
            except Exception:
                pass


def _cleanup_legacy_skill_for_target(project_dir: Path, target: str, changes: list[str]) -> None:
    """清理指定宿主的旧版技能别名残留。"""
    from .skills.manager import SkillManager

    sm = SkillManager(project_dir=project_dir)

    try:
        removed = sm.cleanup_legacy_skill_aliases(target)
        if removed:
            changes.append(f"{target}: 已清理旧版 Super Dev Skill 残留")
    except Exception:
        pass

    # 清理宿主特定的 agent 文件
    legacy_agent_map: dict[str, list[Path]] = {
        "claude-code": [
            Path.home() / ".claude" / "agents" / _legacy_agent_file(),
            project_dir / ".claude" / "agents" / _legacy_agent_file(),
        ],
        "codebuddy": [
            project_dir / ".codebuddy" / "agents" / _legacy_agent_file(),
            Path.home() / ".codebuddy" / "agents" / _legacy_agent_file(),
        ],
        "codebuddy-cli": [
            project_dir / ".codebuddy" / "agents" / _legacy_agent_file(),
            Path.home() / ".codebuddy" / "agents" / _legacy_agent_file(),
        ],
    }
    for legacy_path in legacy_agent_map.get(target, []):
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                changes.append(f"{target}: 已清理旧版 {legacy_path.name}")
            except Exception:
                pass


def migrate_project(project_dir: Path) -> list[str]:
    """将旧版项目迁移到当前版本。

    自动检测已接入的宿主，重新生成所有配置文件和 Skill。
    返回变更描述列表。
    """
    changes: list[str] = []

    # 1. 更新 super-dev.yaml 版本号
    config_path = project_dir / "super-dev.yaml"
    if config_path.exists():
        try:
            text = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
            old_version = data.get("version", "")
            if old_version != __version__:
                data["version"] = __version__
                config_path.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )
                changes.append(f"super-dev.yaml 版本号 {old_version} -> {__version__}")
        except Exception as exc:
            changes.append(f"super-dev.yaml 更新失败: {exc}")

    # 2. 检测所有已接入宿主并重新生成配置
    detected_hosts = _detect_onboarded_hosts(project_dir)

    if detected_hosts:
        from .skills.manager import SkillManager

        mgr = IntegrationManager(project_dir=project_dir)
        sm = SkillManager(project_dir=project_dir)

        for target in detected_hosts:
            written: list[Path] = []
            try:
                written = mgr.setup(target=target, force=True)
                if written:
                    changes.append(f"已重新生成 {target} 集成配置")
            except Exception as exc:
                changes.append(f"{target} 集成配置更新失败: {exc}")

            # 重新生成 slash command
            try:
                if mgr.supports_slash(target):
                    mgr.setup_slash_command(target=target, force=True)
                    mgr.setup_global_slash_command(target=target, force=True)
                    mgr.setup_seeai_slash_command(target=target, force=True)
                    mgr.setup_global_seeai_slash_command(target=target, force=True)
            except Exception:
                pass

            # 重新生成全局协议
            try:
                mgr.setup_global_protocol(target=target, force=True)
            except Exception:
                pass

            # 重新安装 Skill
            if mgr.requires_skill(target):
                try:
                    if sm.skill_surface_available(target):
                        skill_name = sm.default_skill_name(target)
                        sm.install(
                            source="super-dev",
                            target=target,
                            name=skill_name,
                            force=True,
                        )
                        changes.append(f"已更新 {target} Skill ({skill_name})")
                except Exception as exc:
                    changes.append(f"{target} Skill 更新失败: {exc}")

            try:
                manifest_paths = [str(path) for path in written] if written else []
                global_protocol = mgr.resolve_global_protocol_path(target)
                if global_protocol is not None and global_protocol.exists():
                    manifest_paths.append(str(global_protocol))
                global_slash = mgr.resolve_global_slash_command_path(target)
                if global_slash is not None and global_slash.exists():
                    manifest_paths.append(str(global_slash))
                record_install_manifest(
                    project_dir,
                    host=target,
                    family=mgr.host_family(target),
                    scopes={
                        "project": bool(written),
                        "global": bool(
                            (global_protocol is not None and global_protocol.exists())
                            or (global_slash is not None and global_slash.exists())
                        ),
                        "runtime": target == "claude-code"
                        and any(
                            path.endswith(".claude/settings.local.json") for path in manifest_paths
                        ),
                    },
                    paths=manifest_paths,
                )
            except Exception:
                pass

        # 清理所有宿主的旧版技能别名残留
        for target in detected_hosts:
            _cleanup_legacy_skill_for_target(project_dir, target, changes)

        # Claude Code 特有的 Skill 目录清理（用户级）
        if "claude-code" in detected_hosts:
            _cleanup_claude_code_legacy(project_dir, changes)

    # 3. 创建 .super-dev/memory/ 目录
    memory_dir = project_dir / ".super-dev" / "memory"
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True, exist_ok=True)
        changes.append("已创建 .super-dev/memory/ 目录")

    if not changes:
        changes.append("项目已是最新版本，无需迁移")

    return changes
