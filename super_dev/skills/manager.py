"""
Skill 安装管理器
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..catalogs import HOST_TOOL_IDS
from ..host_registry import HostInstallMode, get_install_mode
from .skill_template import SkillTemplate


@dataclass
class SkillInstallResult:
    name: str
    target: str
    path: Path
    source: str


class SkillManager:
    """跨平台 AI Coding 工具 Skill 管理"""

    CANONICAL_SKILL_NAMES = {
        "codex-cli": "super-dev",
        "claude-code": "super-dev",
    }

    # Default skill name for hosts not listed in CANONICAL_SKILL_NAMES.
    DEFAULT_SKILL_NAME = "super-dev"
    LEGACY_SKILL_SUFFIXES = ("-core",)

    LEGACY_SKILL_ALIASES: dict[str, list[str]] = {}
    SUPPLEMENTAL_BUILTIN_SKILLS = {
        "codex-cli": ["super-dev-seeai"],
        "codex": ["super-dev-seeai"],
        "claude-code": ["super-dev-seeai"],
        "antigravity": ["super-dev-seeai"],
        "cline": ["super-dev-seeai"],
        "codebuddy-cli": ["super-dev-seeai"],
        "codebuddy": ["super-dev-seeai"],
        "codebuddy-cn": ["super-dev-seeai"],
        "droid-cli": ["super-dev-seeai"],
        "copilot-cli": ["super-dev-seeai"],
        "cursor-cli": ["super-dev-seeai"],
        "cursor": ["super-dev-seeai"],
        "gemini-cli": ["super-dev-seeai"],
        "kimi-code": ["super-dev-seeai"],
        "kiro-cli": ["super-dev-seeai"],
        "kiro": ["super-dev-seeai"],
        "kilo-code": ["super-dev-seeai"],
        "opencode": ["super-dev-seeai"],
        "qwen-code": ["super-dev-seeai"],
        "workbuddy": ["super-dev-seeai"],
        "qoder-cli": ["super-dev-seeai"],
        "qoder": ["super-dev-seeai"],
        "roo-code": ["super-dev-seeai"],
        "trae": ["super-dev-seeai"],
        "trae-cn": ["super-dev-seeai"],
        "trae-solo": ["super-dev-seeai"],
        "trae-solocn": ["super-dev-seeai"],
        "vscode-copilot": ["super-dev-seeai"],
        "windsurf": ["super-dev-seeai"],
    }

    # Official user-level skill paths confirmed by vendor docs.
    OFFICIAL_TARGET_PATHS = {
        "antigravity": "~/.gemini/skills",
        "claude-code": "~/.claude/skills",
        "cline": "~/.cline/skills",
        "codebuddy-cli": "~/.codebuddy/skills",
        "codebuddy": "~/.codebuddy/skills",
        "codebuddy-cn": "~/.codebuddy/skills",
        "copilot-cli": "~/.copilot/skills",
        "droid-cli": "~/.factory/skills",
        "codex": "~/.agents/skills",
        "codex-cli": "~/.agents/skills",
        "kiro-cli": "~/.kiro/skills",
        "kiro": "~/.kiro/skills",
        "kimi-code": "~/.kimi/skills",
        "opencode": "~/.config/opencode/skills",
        "qwen-code": "~/.qwen/skills",
        "trae-cn": "~/.trae-cn/skills",
        "trae-solocn": "~/.trae-cn/skills",
        "workbuddy": "~/.workbuddy/skills",
        "qoder-cli": "~/.qoder/skills",
        "qoder": "~/.qoder/skills",
        "roo-code": "~/.roo/skills",
        "windsurf": "~/.codeium/windsurf/skills",
    }

    # Observed compatibility paths used when a host exposes a local skill loader
    # but the vendor docs do not yet publish a stable user-level install path.
    OBSERVED_TARGET_PATHS = {
        "cursor-cli": "~/.cursor/skills",
        "cursor": "~/.cursor/skills",
        "gemini-cli": "~/.gemini/skills",
        "kilo-code": "~/.kilocode/skills",
        "trae": "~/.trae/skills",
        "trae-solo": "~/.trae/skills",
        "vscode-copilot": "~/.copilot/skills",
    }

    COMPATIBILITY_MIRROR_PATHS: dict[str, list[str]] = {
        "kimi-code": ["~/.config/agents/skills", "~/.agents/skills"],
        "codex": ["~/.codex/skills"],
    }

    TARGET_PATHS = {
        **OBSERVED_TARGET_PATHS,
        **OFFICIAL_TARGET_PATHS,
    }

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()

    @classmethod
    def coverage_gaps(cls) -> dict[str, list[str]]:
        manual_hosts = {
            host_id
            for host_id in HOST_TOOL_IDS
            if get_install_mode(host_id) == HostInstallMode.MANUAL
        }
        declared = set(HOST_TOOL_IDS) - manual_hosts
        target_keys = set(cls.TARGET_PATHS)
        comparable_target_keys = target_keys - manual_hosts
        return {
            "missing_in_skill_targets": sorted(declared - comparable_target_keys),
            "extra_in_skill_targets": sorted(comparable_target_keys - declared),
        }

    def list_targets(self) -> list[str]:
        return list(self.TARGET_PATHS.keys())

    @classmethod
    def default_skill_name(cls, target: str) -> str:
        return cls.CANONICAL_SKILL_NAMES.get(target, cls.DEFAULT_SKILL_NAME)

    @classmethod
    def codex_home_dir(cls) -> Path:
        raw = os.getenv("CODEX_HOME", "").strip()
        if raw:
            return Path(raw).expanduser()
        return Path.home() / ".codex"

    @classmethod
    def compatibility_skill_names(cls, target: str, requested_name: str | None = None) -> list[str]:
        canonical = cls.default_skill_name(target)
        names: list[str] = []
        legacy_aliases = cls.LEGACY_SKILL_ALIASES.get(target, [])
        explicit_nonstandard = (
            isinstance(requested_name, str)
            and requested_name.strip()
            and requested_name not in {canonical, *legacy_aliases}
        )
        include_legacy = requested_name in {None, canonical, *legacy_aliases}
        seed = [requested_name] if explicit_nonstandard else [canonical, requested_name]
        if include_legacy:
            seed.extend(legacy_aliases)
        for item in seed:
            if isinstance(item, str) and item.strip() and item not in names:
                names.append(item)
        return names

    @classmethod
    def supplemental_builtin_skills(cls, target: str) -> list[str]:
        return list(cls.SUPPLEMENTAL_BUILTIN_SKILLS.get(target, []))

    @classmethod
    def managed_builtin_skill_names(cls, target: str) -> list[str]:
        names = [cls.default_skill_name(target), *cls.supplemental_builtin_skills(target)]
        managed: list[str] = []
        for name in names:
            if name not in managed:
                managed.append(name)
        return managed

    @classmethod
    def legacy_cleanup_skill_names(cls) -> list[str]:
        return [f"{cls.DEFAULT_SKILL_NAME}{suffix}" for suffix in cls.LEGACY_SKILL_SUFFIXES]

    @classmethod
    def target_path_kind(cls, target: str) -> str:
        if target in cls.OFFICIAL_TARGET_PATHS:
            return "official-user-surface"
        if target in cls.OBSERVED_TARGET_PATHS:
            return "observed-compatibility-surface"
        return "unknown"

    def skill_surface_available(self, target: str) -> bool:
        kind = self.target_path_kind(target)
        target_dir = self._target_dir(target)
        if kind == "official-user-surface":
            return True
        if kind == "observed-compatibility-surface":
            return target_dir.exists()
        return False

    def list_installed(self, target: str) -> list[str]:
        names: set[str] = set()
        for base in self._all_target_dirs(target):
            if not base.exists():
                continue
            names.update(d.name for d in base.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
        return sorted(names)

    def install(
        self,
        source: str,
        target: str,
        name: str | None = None,
        force: bool = False,
    ) -> SkillInstallResult:
        """安装 skill 到指定 target"""
        base = self._target_dir(target)
        base.mkdir(parents=True, exist_ok=True)

        if self._is_git_source(source):
            return self._install_from_git(source=source, target=target, name=name, force=force)

        source_path = Path(source).expanduser().resolve()
        if source_path.is_dir():
            return self._install_from_directory(
                source_dir=source_path,
                target=target,
                name=name,
                force=force,
            )

        # 内置 skill
        if source == "super-dev":
            skill_name = name or self.default_skill_name(target)
            target_dir = base / skill_name

            # Clean up legacy skill names for this target
            for legacy in self.legacy_cleanup_skill_names():
                if legacy == skill_name:
                    continue  # Don't remove the skill we're about to install
                legacy_dir = base / legacy
                if legacy_dir.exists():
                    shutil.rmtree(legacy_dir, ignore_errors=True)

            self._prepare_target_dir(target_dir, force=force)
            self._write_builtin_skill(target_dir, skill_name, target)
            self._mirror_skill_install(
                target=target,
                skill_name=skill_name,
                force=force,
                writer=lambda mirror_dir: self._write_builtin_skill(mirror_dir, skill_name, target),
            )
            for alias in self.compatibility_skill_names(target, skill_name):
                if alias == skill_name:
                    continue
                alias_dir = base / alias
                if alias_dir.exists() and not force:
                    continue  # 兼容 Skill 已存在且不强制 → 静默跳过
                self._prepare_target_dir(alias_dir, force=force)
                self._write_builtin_skill(alias_dir, alias, target)
                self._mirror_skill_install(
                    target=target,
                    skill_name=alias,
                    force=force,
                    writer=lambda mirror_dir, alias_name=alias: self._write_builtin_skill(
                        mirror_dir, alias_name, target
                    ),
                )
            for extra_name in self.supplemental_builtin_skills(target):
                if extra_name in {skill_name, *self.compatibility_skill_names(target, skill_name)}:
                    continue
                extra_dir = base / extra_name
                if extra_dir.exists() and not force:
                    continue  # 补充 Skill 已存在且不强制 → 静默跳过
                self._prepare_target_dir(extra_dir, force=force)
                self._write_builtin_skill(extra_dir, extra_name, target)
                self._mirror_skill_install(
                    target=target,
                    skill_name=extra_name,
                    force=force,
                    writer=lambda mirror_dir, extra_skill=extra_name: self._write_builtin_skill(
                        mirror_dir, extra_skill, target
                    ),
                )
            self._cleanup_legacy_skills(target)
            return SkillInstallResult(
                name=skill_name,
                target=target,
                path=target_dir,
                source="builtin",
            )

        raise FileNotFoundError(
            f"Skill source not found: {source}. Use a local directory, git url, or 'super-dev'."
        )

    def refresh_all_installed(self) -> list[str]:
        """Re-install skills for all hosts that already have them, updating to current version."""
        refreshed = []
        for target, target_path_str in {
            **self.OFFICIAL_TARGET_PATHS,
            **self.OBSERVED_TARGET_PATHS,
        }.items():
            target_path = Path(target_path_str).expanduser()
            # Check if super-dev skill exists for this target
            skill_dir = target_path / "super-dev"
            if skill_dir.exists() and (skill_dir / "SKILL.md").exists():
                try:
                    self.install(source="super-dev", target=target, force=True)
                    refreshed.append(target)
                except Exception:
                    pass
        return refreshed

    @classmethod
    def cleanup_all_legacy(cls) -> list[str]:
        """扫描所有已知和常见 skill 目录，删除旧版技能别名残留。"""
        cleaned: list[str] = []
        # 已知宿主路径
        all_paths = {**cls.OFFICIAL_TARGET_PATHS, **cls.OBSERVED_TARGET_PATHS}
        search_dirs = [Path(p).expanduser() for p in all_paths.values()]
        # 常见但不在列表里的旧路径
        home = Path.home()
        for pattern in (
            ".*/skills",  # ~/.xxx/skills
            ".config/*/skills",  # ~/.config/xxx/skills
        ):
            for match in home.glob(pattern):
                if match.is_dir() and match not in search_dirs:
                    search_dirs.append(match)
        # 扫描并清理
        for skill_dir in search_dirs:
            for legacy_name in cls.legacy_cleanup_skill_names():
                legacy = skill_dir / legacy_name
                if legacy.exists():
                    shutil.rmtree(legacy, ignore_errors=True)
                    cleaned.append(str(legacy))
        return cleaned

    def uninstall(self, name: str, target: str) -> Path:
        names = self.compatibility_skill_names(target, name)
        target_dir = self._target_dir(target) / name
        removed_any = False
        for candidate in names:
            primary = self._target_dir(target) / candidate
            if primary.exists():
                shutil.rmtree(primary)
                removed_any = True
            for mirror_base in self._compatibility_target_dirs(target):
                mirror_dir = mirror_base / candidate
                if mirror_dir.exists():
                    shutil.rmtree(mirror_dir)
                    removed_any = True
        if not removed_any:
            raise FileNotFoundError(f"Skill not found: {name} ({target})")
        return target_dir

    def managed_skill_cleanup_paths(self, target: str, name: str) -> list[Path]:
        paths: list[Path] = []
        for candidate in self.compatibility_skill_names(target, name):
            paths.append(self._target_dir(target) / candidate)
            for mirror_base in self._compatibility_target_dirs(target):
                paths.append(mirror_base / candidate)
        deduped: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

    def legacy_skill_cleanup_paths(self, target: str) -> list[Path]:
        paths: list[Path] = []
        for legacy_name in self.legacy_cleanup_skill_names():
            paths.append(self._target_dir(target) / legacy_name)
            for mirror_base in self._compatibility_target_dirs(target):
                paths.append(mirror_base / legacy_name)
        deduped: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

    def cleanup_legacy_skill_aliases(self, target: str) -> list[str]:
        removed: list[str] = []
        for legacy_name in self.legacy_cleanup_skill_names():
            removed_any = False
            primary = self._target_dir(target) / legacy_name
            if primary.exists():
                shutil.rmtree(primary, ignore_errors=True)
                removed_any = True
            for mirror_base in self._compatibility_target_dirs(target):
                mirror_dir = mirror_base / legacy_name
                if mirror_dir.exists():
                    shutil.rmtree(mirror_dir, ignore_errors=True)
                    removed_any = True
            if removed_any:
                removed.append(legacy_name)
        return removed

    def _target_dir(self, target: str) -> Path:
        relative = self.TARGET_PATHS.get(target)
        if relative is None:
            raise ValueError(f"Unsupported target: {target}")
        raw_path = Path(relative).expanduser()
        if raw_path.is_absolute():
            return raw_path
        return self.project_dir / relative

    def _compatibility_target_dirs(self, target: str) -> list[Path]:
        paths = self.COMPATIBILITY_MIRROR_PATHS.get(target, [])
        resolved: list[Path] = []
        for item in paths:
            raw_path = (
                self.codex_home_dir() / "skills"
                if target == "codex-cli"
                else Path(item).expanduser()
            )
            resolved.append(raw_path if raw_path.is_absolute() else self.project_dir / raw_path)
        return resolved

    def _all_target_dirs(self, target: str) -> list[Path]:
        return [self._target_dir(target), *self._compatibility_target_dirs(target)]

    def _mirror_skill_install(
        self,
        *,
        target: str,
        skill_name: str,
        force: bool,
        writer,
    ) -> None:
        for mirror_base in self._compatibility_target_dirs(target):
            mirror_dir = mirror_base / skill_name
            self._prepare_target_dir(mirror_dir, force=force)
            writer(mirror_dir)

    def _cleanup_legacy_skills(self, target: str) -> None:
        """Remove legacy skill aliases from the target host's skill directory."""
        # 清理当前宿主下的旧名称
        base = self._target_dir(target)
        for legacy_name in self.legacy_cleanup_skill_names():
            legacy_dir = base / legacy_name
            if legacy_dir.exists():
                shutil.rmtree(legacy_dir, ignore_errors=True)

        # 清理 mirror 路径下的旧名称和旧 mirror
        for mirror_base in self._compatibility_target_dirs(target):
            for old_name in (*self.legacy_cleanup_skill_names(), "super-dev", "super-dev-seeai"):
                old_dir = mirror_base / old_name
                if old_dir.exists():
                    shutil.rmtree(old_dir, ignore_errors=True)

    def _is_git_source(self, source: str) -> bool:
        return (
            source.startswith("http://") or source.startswith("https://") or source.endswith(".git")
        )

    def _validate_git_source(self, source: str) -> None:
        """验证 Git 源地址安全性"""
        dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "{", "}", "<", ">", "\n", "\r"]
        if any(c in source for c in dangerous_chars):
            raise ValueError(f"Git 源地址包含危险字符: {source}")
        if source.startswith("-") or source.startswith("--"):
            raise ValueError(f"Git 源地址不允许以 - 开头: {source}")
        if not (
            source.startswith("https://") or source.startswith("http://") or source.endswith(".git")
        ):
            raise ValueError(f"Git 源地址格式无效，必须以 https:// 或 http:// 开头: {source}")

    def _install_from_git(
        self,
        source: str,
        target: str,
        name: str | None,
        force: bool,
    ) -> SkillInstallResult:
        self._validate_git_source(source)
        git_executable = shutil.which("git")
        if not git_executable:
            raise FileNotFoundError("git executable not found in PATH")

        with tempfile.TemporaryDirectory(prefix="super-dev-skill-") as temp_dir:
            temp_path = Path(temp_dir)
            clone_dir = temp_path / "repo"
            subprocess.run(
                [git_executable, "clone", "--depth", "1", "--", source, str(clone_dir)],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603

            skill_dirs = self._find_skill_dirs(clone_dir)
            if not skill_dirs:
                raise FileNotFoundError("No SKILL.md found in git repository")

            selected_dir = self._select_skill_dir(skill_dirs, name)
            return self._install_from_directory(
                source_dir=selected_dir,
                target=target,
                name=name or selected_dir.name,
                force=force,
            )

    def _install_from_directory(
        self,
        source_dir: Path,
        target: str,
        name: str | None,
        force: bool,
    ) -> SkillInstallResult:
        if not (source_dir / "SKILL.md").exists():
            raise FileNotFoundError(f"Directory does not contain SKILL.md: {source_dir}")

        skill_name = name or source_dir.name
        target_dir = self._target_dir(target) / skill_name
        self._prepare_target_dir(target_dir, force=force)
        shutil.copytree(source_dir, target_dir)
        self._mirror_skill_install(
            target=target,
            skill_name=skill_name,
            force=force,
            writer=lambda mirror_dir: shutil.copytree(source_dir, mirror_dir),
        )
        return SkillInstallResult(
            name=skill_name,
            target=target,
            path=target_dir,
            source=str(source_dir),
        )

    def _prepare_target_dir(self, target_dir: Path, force: bool) -> None:
        if target_dir.exists():
            if not force:
                raise FileExistsError(f"Target skill already exists: {target_dir}")
            shutil.rmtree(target_dir)

    def _find_skill_dirs(self, root: Path) -> list[Path]:
        dirs = []
        for file_path in root.rglob("SKILL.md"):
            parent = file_path.parent
            if ".git" in parent.parts:
                continue
            dirs.append(parent)
        return dirs

    def _select_skill_dir(self, skill_dirs: list[Path], name: str | None) -> Path:
        if name is None:
            return skill_dirs[0]
        for skill_dir in skill_dirs:
            if skill_dir.name == name:
                return skill_dir
        raise FileNotFoundError(f"Skill '{name}' not found in repository")

    def _write_builtin_skill(self, target_dir: Path, skill_name: str, target: str) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        template = SkillTemplate.for_builtin(skill_name, target)
        skill_content = template.render(target)
        (target_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        if target == "codex-cli":
            display_name = "Super Dev SEEAI" if skill_name == "super-dev-seeai" else "Super Dev"
            short_description = (
                "Competition-fast governed delivery mode for Codex."
                if skill_name == "super-dev-seeai"
                else "Research-first governed delivery pipeline for Codex."
            )
            default_prompt = (
                "In Codex CLI use $super-dev-seeai. In Codex app choose super-dev-seeai from the slash skill list. Continue the SEEAI competition flow for the current request."
                if skill_name == "super-dev-seeai"
                else "In Codex CLI use $super-dev. In Codex app choose super-dev from the slash skill list. Continue the Super Dev pipeline for the current request."
            )
            metadata_dir = target_dir / "agents"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            openai_yaml = (
                "interface:\n"
                f'  display_name: "{display_name}"\n'
                f'  short_description: "{short_description}"\n'
                f'  default_prompt: "{default_prompt}"\n'
                "policy:\n"
                "  allow_implicit_invocation: true\n"
            )
            (metadata_dir / "openai.yaml").write_text(
                openai_yaml,
                encoding="utf-8",
            )
