"""CLI deploy/runtime mixin helpers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .evidence_identity import attach_evidence_identity
from .frameworks import framework_playbook_complete, is_cross_platform_frontend
from .ui_contract_governance import required_claude_design_runtime_checks


class CliDeployRuntimeMixin:
    _RUNTIME_UI_EMOJI_RE = re.compile(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]")
    _RUNTIME_UI_CHAT_SHELL_RE = re.compile(
        r"(anthropic|claude|chat-sidebar|conversation-list|thread-list|assistant-message|model-selector|conversation-shell|chat-shell)",
        re.IGNORECASE,
    )

    def _is_cross_platform_frontend(self, frontend: str) -> bool:
        return is_cross_platform_frontend(frontend)

    def _framework_playbook_complete(self, playbook: dict[str, Any]) -> bool:
        return framework_playbook_complete(playbook)

    def _frontend_runtime_report_paths(
        self, output_dir: Path, project_name: str
    ) -> dict[str, Path]:
        return {
            "markdown": output_dir / f"{project_name}-frontend-runtime.md",
            "json": output_dir / f"{project_name}-frontend-runtime.json",
        }

    def _export_preview_from_output_frontend(self, preview_file: Path) -> bool:
        frontend_index = preview_file.parent / "output" / "frontend" / "index.html"
        if not frontend_index.exists():
            return False
        preview_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(frontend_index, preview_file)
        return True

    def _runtime_ui_probe_files(
        self, *, project_dir: Path, frontend_dir: Path, preview_file: Path
    ) -> list[Path]:
        allowed_suffixes = {
            ".tsx",
            ".ts",
            ".jsx",
            ".js",
            ".vue",
            ".svelte",
            ".css",
            ".scss",
            ".less",
            ".html",
        }
        excluded_dirs = {
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            "coverage",
        }
        candidates: list[Path] = []
        for candidate in (
            preview_file,
            frontend_dir / "index.html",
            frontend_dir / "styles.css",
            frontend_dir / "app.js",
            project_dir / "frontend",
            project_dir / "src",
        ):
            if candidate.is_file() and candidate not in candidates:
                candidates.append(candidate)
            elif candidate.is_dir():
                for path in candidate.rglob("*"):
                    if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
                        continue
                    if any(part in excluded_dirs for part in path.parts):
                        continue
                    if path not in candidates:
                        candidates.append(path)
        return candidates[:80]

    def _probe_runtime_ui_banned_patterns(
        self,
        *,
        project_dir: Path,
        frontend_dir: Path,
        preview_file: Path,
    ) -> dict[str, Any]:
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in self._runtime_ui_probe_files(
                project_dir=project_dir,
                frontend_dir=frontend_dir,
                preview_file=preview_file,
            )
            if path.exists()
        )
        emoji_hits = sorted({item for item in self._RUNTIME_UI_EMOJI_RE.findall(combined)})[:10]
        chat_shell_hits = sorted(
            {item for item in self._RUNTIME_UI_CHAT_SHELL_RE.findall(combined)}
        )[:10]
        observed = [*emoji_hits, *chat_shell_hits]
        return {
            "passed": len(observed) == 0,
            "emoji_hits": emoji_hits,
            "chat_shell_hits": chat_shell_hits,
            "observed": observed[:10],
        }

    def _load_frontend_runtime_validation(
        self, *, output_dir: Path, project_name: str
    ) -> dict[str, Any]:
        report_file = self._frontend_runtime_report_paths(
            output_dir=output_dir, project_name=project_name
        )["json"]
        if not report_file.exists():
            return {
                "passed": False,
                "checks": {},
                "preview_file": "",
                "report_file": str(report_file),
            }
        try:
            payload = json.loads(report_file.read_text(encoding="utf-8"))
        except Exception:
            return {
                "passed": False,
                "checks": {},
                "preview_file": "",
                "report_file": str(report_file),
            }
        if not isinstance(payload, dict):
            return {
                "passed": False,
                "checks": {},
                "preview_file": "",
                "report_file": str(report_file),
            }
        payload["report_file"] = str(report_file)
        return payload

    def _runtime_ui_source_blob(
        self, *, project_dir: Path, frontend_dir: Path, preview_file: Path
    ) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in self._runtime_ui_probe_files(
                project_dir=project_dir,
                frontend_dir=frontend_dir,
                preview_file=preview_file,
            )
            if path.exists()
        )

    def _runtime_has_design_token_wiring(
        self,
        *,
        source_content: str,
        preview_content: str,
        design_tokens_content: str,
    ) -> bool:
        combined = "\n".join([source_content, preview_content]).lower()
        if "design-tokens.css" in combined:
            return True
        if "var(--color-" in combined or "var(--space-" in combined or "var(--font-" in combined:
            return True
        if design_tokens_content and (
            "--color-" in design_tokens_content or "--font-" in design_tokens_content
        ):
            return "var(--" in combined
        return False

    def _runtime_has_theme_entry_wiring(
        self,
        *,
        source_content: str,
        preview_content: str,
        design_tokens_content: str,
    ) -> bool:
        combined = "\n".join([source_content, preview_content]).lower()
        theme_signals = (
            "themeprovider",
            "configprovider",
            "cssvarsprovider",
            "chakraprovider",
            "mantineprovider",
            "vuetify",
            "createtheme",
            "theme=",
            "data-theme",
            "design-tokens.css",
        )
        if any(signal in combined for signal in theme_signals):
            return True
        if "--color-" in design_tokens_content or "--font-" in design_tokens_content:
            return "var(--" in combined
        return False

    def _runtime_navigation_markers(self, source_content: str) -> list[str]:
        lowered = source_content.lower()
        candidates = (
            ("<nav", "nav"),
            ("<header", "header"),
            ("<aside", "aside"),
            ("sidebar", "sidebar"),
            ("topbar", "topbar"),
            ("breadcrumb", "breadcrumb"),
            ("appshell", "appshell"),
            ("navigationmenu", "navigationmenu"),
            ("menubar", "menubar"),
        )
        found: list[str] = []
        for needle, label in candidates:
            if needle in lowered and label not in found:
                found.append(label)
        return found

    def _runtime_library_tokens(self, library_name: str) -> tuple[str, ...]:
        lowered = library_name.lower()
        if "shadcn" in lowered or "radix" in lowered:
            return ("@radix-ui", "radix", "@/components/ui", "components/ui", "shadcn")
        if "magic ui" in lowered or "magicui" in lowered:
            return ("magicui", "@/components/magicui", "components/magicui")
        if "aceternity" in lowered:
            return ("aceternity", "@/components/ui", "components/ui")
        if "nextui" in lowered or "heroui" in lowered:
            return ("@nextui-org", "@heroui", "nextui", "heroui")
        if "daisy" in lowered:
            return ("daisyui",)
        if "headless" in lowered:
            return ("@headlessui", "headlessui")
        if "tremor" in lowered:
            return ("@tremor", "tremor")
        return ()

    def _runtime_import_sources(self, source_content: str) -> list[str]:
        matches = re.findall(
            r"(?:from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"])",
            source_content,
            flags=re.IGNORECASE,
        )
        imports: list[str] = []
        for left, right in matches:
            candidate = (left or right or "").strip().lower()
            if candidate:
                imports.append(candidate)
        return imports

    def _runtime_framework_execution_ok(
        self,
        *,
        framework_playbook: dict[str, Any],
        source_content: str,
        preview_content: str,
        dependency_blob: str,
    ) -> bool:
        if not framework_playbook:
            return True
        combined = "\n".join([source_content, preview_content, dependency_blob]).lower()
        observed = " ".join(
            str(item).lower()
            for item in [
                *(framework_playbook.get("implementation_modules") or []),
                *(framework_playbook.get("native_capabilities") or []),
                *(framework_playbook.get("validation_surfaces") or []),
            ]
        )
        keywords = [
            token
            for token in re.findall(r"[a-zA-Z0-9_-]{3,}", observed)
            if token
            not in {"must", "with", "and", "the", "for", "are", "app", "web", "page", "pages"}
        ]
        if not keywords:
            return True
        return any(keyword in combined for keyword in keywords[:24])

    def _runtime_contains_any(self, combined: str, candidates: list[str]) -> bool:
        lowered = combined.lower()
        normalized = re.sub(r"[-_/]+", " ", lowered)
        for candidate in candidates:
            token = str(candidate).strip().lower()
            if not token:
                continue
            if "/" in token:
                token = Path(token).name.lower()
            normalized_token = re.sub(r"[-_/]+", " ", token)
            if token and (token in lowered or normalized_token in normalized):
                return True
        return False

    def _runtime_claude_design_protocol_checks(
        self,
        *,
        ui_contract: dict[str, Any],
        source_content: str,
        preview_content: str,
    ) -> dict[str, bool]:
        combined = "\n".join([source_content, preview_content])
        checks: dict[str, bool] = {}
        if not required_claude_design_runtime_checks(ui_contract):
            return checks

        screen_recipes = (
            ui_contract.get("screen_recipes")
            if isinstance(ui_contract.get("screen_recipes"), list)
            else []
        )
        if screen_recipes:
            labels = [str(item.get("label", "")).strip() for item in screen_recipes if isinstance(item, dict)]
            sections = [
                str(section).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for section in item.get("section_order", []) or []
            ]
            trust_modules = [
                str(module).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for module in item.get("trust_modules", []) or []
            ]
            required_states = [
                str(state).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for state in item.get("required_states", []) or []
            ]
            checks["ui_screen_recipes"] = (
                self._runtime_contains_any(combined, labels)
                and self._runtime_contains_any(combined, sections)
                and (
                    self._runtime_contains_any(combined, trust_modules)
                    or self._runtime_contains_any(combined, required_states)
                )
            )

        design_context_protocol = (
            ui_contract.get("design_context_protocol")
            if isinstance(ui_contract.get("design_context_protocol"), dict)
            else {}
        )
        if design_context_protocol:
            checks["ui_design_context_protocol"] = (
                self._runtime_contains_any(
                    combined,
                    [
                        *(
                            str(item).strip()
                            for item in design_context_protocol.get("preferred_import_order", []) or []
                        ),
                        *(
                            str(item).strip()
                            for item in design_context_protocol.get("github_import_targets", []) or []
                        ),
                    ],
                )
                and self._runtime_contains_any(
                    combined, [str(design_context_protocol.get("single_source_rule", "")).strip()]
                )
            )

        tweak_strategy = (
            ui_contract.get("tweak_strategy")
            if isinstance(ui_contract.get("tweak_strategy"), dict)
            else {}
        )
        if tweak_strategy:
            checks["ui_tweak_strategy"] = (
                self._runtime_contains_any(combined, [str(tweak_strategy.get("mode", "")).strip()])
                and self._runtime_contains_any(
                    combined,
                    [str(item).strip() for item in tweak_strategy.get("default_controls", []) or []],
                )
                and self._runtime_contains_any(
                    combined, [str(tweak_strategy.get("persistence_rule", "")).strip()]
                )
            )

        verification_handoff = (
            ui_contract.get("verification_handoff")
            if isinstance(ui_contract.get("verification_handoff"), dict)
            else {}
        )
        if verification_handoff:
            checks["ui_verification_handoff"] = (
                self._runtime_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("verification_order", []) or []
                    ],
                )
                and self._runtime_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("required_artifacts", []) or []
                    ],
                )
                and self._runtime_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("acceptance_checks", []) or []
                    ],
                )
            )
        return checks

    def _write_frontend_runtime_validation(
        self,
        *,
        project_dir: Path,
        output_dir: Path,
        project_name: str,
    ) -> dict[str, Any]:
        frontend_dir = output_dir / "frontend"
        index_file = frontend_dir / "index.html"
        css_file = frontend_dir / "styles.css"
        design_tokens_file = frontend_dir / "design-tokens.css"
        js_file = frontend_dir / "app.js"
        preview_file = project_dir / "preview.html"
        ui_contract_file = output_dir / f"{project_name}-ui-contract.json"
        ui_alignment_file = output_dir / f"{project_name}-ui-contract-alignment.json"
        package_json_file = project_dir / "package.json"

        exported_preview = (
            self._export_preview_from_output_frontend(preview_file)
            if index_file.exists()
            else False
        )
        checks = {
            "output_frontend_index": index_file.exists(),
            "output_frontend_styles": css_file.exists(),
            "output_frontend_design_tokens": design_tokens_file.exists(),
            "output_frontend_script": js_file.exists(),
            "preview_html": preview_file.exists(),
            "ui_contract_json": ui_contract_file.exists(),
        }
        ui_alignment_summary: dict[str, Any] = {}
        if ui_alignment_file.exists():
            try:
                loaded_alignment = json.loads(ui_alignment_file.read_text(encoding="utf-8"))
                if isinstance(loaded_alignment, dict):
                    ui_alignment_summary = loaded_alignment
            except Exception:
                ui_alignment_summary = {}
        ui_alignment_available = bool(ui_alignment_summary)
        ui_alignment_passed = bool(ui_alignment_summary) and all(
            bool(value.get("passed", False))
            for value in ui_alignment_summary.values()
            if isinstance(value, dict)
        )
        checks["ui_contract_alignment"] = ui_alignment_passed if ui_alignment_available else False
        key_alignment_checks = {
            "ui_theme_entry": "theme_entry",
            "ui_navigation_shell": "navigation_shell",
            "ui_component_imports": "component_imports",
            "ui_banned_patterns": "banned_patterns",
            "ui_framework_execution": "framework_execution",
            "ui_screen_recipes": "screen_recipes",
            "ui_design_context_protocol": "design_context_protocol",
            "ui_tweak_strategy": "tweak_strategy",
            "ui_verification_handoff": "verification_handoff",
        }
        banned_pattern_probe = self._probe_runtime_ui_banned_patterns(
            project_dir=project_dir,
            frontend_dir=frontend_dir,
            preview_file=preview_file,
        )
        source_content = self._runtime_ui_source_blob(
            project_dir=project_dir,
            frontend_dir=frontend_dir,
            preview_file=preview_file,
        )
        preview_content = (
            preview_file.read_text(encoding="utf-8", errors="ignore")
            if preview_file.exists()
            else ""
        )
        design_tokens_content = (
            design_tokens_file.read_text(encoding="utf-8", errors="ignore")
            if design_tokens_file.exists()
            else ""
        )
        for check_name, alignment_key in key_alignment_checks.items():
            item = ui_alignment_summary.get(alignment_key)
            if isinstance(item, dict):
                checks[check_name] = bool(item.get("passed", False))
            elif check_name == "ui_banned_patterns":
                checks[check_name] = bool(banned_pattern_probe.get("passed", False))
            else:
                checks[check_name] = False
        ui_contract: dict[str, Any] = {}
        if ui_contract_file.exists():
            try:
                loaded = json.loads(ui_contract_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    ui_contract = loaded
            except Exception:
                ui_contract = {}
        component_stack = (
            ui_contract.get("component_stack", {})
            if isinstance(ui_contract.get("component_stack"), dict)
            else {}
        )
        icon_system = (
            ui_contract.get("icon_system")
            or component_stack.get("icon")
            or component_stack.get("icons")
            or ""
        )
        analysis = (
            ui_contract.get("analysis", {}) if isinstance(ui_contract.get("analysis"), dict) else {}
        )
        frontend_variant = str(analysis.get("frontend") or "")
        cross_platform_frontend = self._is_cross_platform_frontend(frontend_variant)
        framework_playbook_payload = ui_contract.get("framework_playbook")
        framework_playbook: dict[str, Any] = (
            framework_playbook_payload if isinstance(framework_playbook_payload, dict) else {}
        )
        if ui_alignment_available and not framework_playbook:
            checks["ui_framework_execution"] = True
        selected_library = (
            ui_contract.get("ui_library_preference", {}).get("final_selected", "")
            if isinstance(ui_contract.get("ui_library_preference"), dict)
            else ""
        )
        dependency_blob = (
            package_json_file.read_text(encoding="utf-8", errors="ignore").lower()
            if package_json_file.exists()
            else ""
        )
        if not ui_alignment_available:
            for check_name in key_alignment_checks:
                if check_name == "ui_theme_entry":
                    checks[check_name] = self._runtime_has_theme_entry_wiring(
                        source_content=source_content,
                        preview_content=preview_content,
                        design_tokens_content=design_tokens_content,
                    )
                elif check_name == "ui_navigation_shell":
                    checks[check_name] = bool(self._runtime_navigation_markers(source_content)) or (
                        "<nav" in preview_content.lower() or "<header" in preview_content.lower()
                    )
                elif check_name == "ui_component_imports":
                    expected_import_tokens = self._runtime_library_tokens(selected_library)
                    import_sources = self._runtime_import_sources(source_content)
                    should_enforce_imports = bool(package_json_file.exists()) and bool(
                        expected_import_tokens
                    )
                    checks[check_name] = (
                        any(
                            any(expected in import_source for expected in expected_import_tokens)
                            for import_source in import_sources
                        )
                        if should_enforce_imports
                        else True
                    )
                elif check_name == "ui_framework_execution":
                    checks[check_name] = self._runtime_framework_execution_ok(
                        framework_playbook=framework_playbook,
                        source_content=source_content,
                        preview_content=preview_content,
                        dependency_blob=dependency_blob,
                    )
            checks.update(
                self._runtime_claude_design_protocol_checks(
                    ui_contract=ui_contract,
                    source_content=source_content,
                    preview_content=preview_content,
                )
            )
            checks["ui_contract_alignment"] = all(
                bool(checks.get(name, False))
                for name in (
                    *(
                        name
                        for name in key_alignment_checks
                        if name
                        not in {
                            "ui_screen_recipes",
                            "ui_design_context_protocol",
                            "ui_tweak_strategy",
                            "ui_verification_handoff",
                        }
                    ),
                    *required_claude_design_runtime_checks(ui_contract),
                )
            )
        framework_playbook_ready = self._framework_playbook_complete(framework_playbook)
        checks["ui_framework_playbook"] = (
            framework_playbook_ready if cross_platform_frontend else True
        )
        passed = all(checks.values())
        ui_alignment_key_areas: dict[str, dict[str, Any]] = {
            key: value
            for key, value in ui_alignment_summary.items()
            if key
            in {
                "theme_entry",
                "navigation_shell",
                "component_imports",
                "banned_patterns",
                "framework_execution",
                "screen_recipes",
                "design_context_protocol",
                "tweak_strategy",
                "verification_handoff",
            }
            and isinstance(value, dict)
        }
        report = {
            "project_name": project_name,
            "passed": passed,
            "checks": checks,
            "preview_file": str(preview_file) if preview_file.exists() else "",
            "generated_from_output_frontend": exported_preview,
            "ui_contract_file": str(ui_contract_file) if ui_contract_file.exists() else "",
            "design_tokens_file": str(design_tokens_file) if design_tokens_file.exists() else "",
            "ui_alignment_file": str(ui_alignment_file) if ui_alignment_file.exists() else "",
            "ui_alignment_available": ui_alignment_available,
            "ui_contract_summary": {
                "style_direction": ui_contract.get("style_direction", ""),
                "icon_system": icon_system,
                "emoji_policy": ui_contract.get("emoji_policy", {}),
                "framework_playbook": framework_playbook,
                "selected_library": selected_library,
            },
            "ui_alignment_summary": ui_alignment_summary,
            "ui_alignment_key_areas": ui_alignment_key_areas,
            "ui_banned_pattern_probe": banned_pattern_probe,
        }
        report_paths = self._frontend_runtime_report_paths(
            output_dir=output_dir, project_name=project_name
        )
        report_with_identity = attach_evidence_identity(
            report,
            project_dir=project_dir,
            artifact_name="frontend-runtime",
            dependencies=[ui_contract_file, ui_alignment_file],
        )
        report_paths["json"].write_text(
            json.dumps(report_with_identity, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        lines = [
            "# Frontend Runtime Validation",
            "",
            f"- Passed: {'yes' if passed else 'no'}",
            (
                f"- Preview file: `{preview_file}`"
                if preview_file.exists()
                else "- Preview file: missing"
            ),
            (
                f"- UI contract: `{ui_contract_file}`"
                if ui_contract_file.exists()
                else "- UI contract: missing"
            ),
            (
                f"- Design tokens: `{design_tokens_file}`"
                if design_tokens_file.exists()
                else "- Design tokens: missing"
            ),
            (
                f"- UI alignment: `{ui_alignment_file}`"
                if ui_alignment_file.exists()
                else "- UI alignment: pending (will be refreshed after UI review)"
            ),
            "",
            "## Checks",
            "",
        ]
        for key, value in checks.items():
            lines.append(f"- {key}: {'ok' if value else 'missing'}")
        if ui_contract:
            lines.extend(
                [
                    "",
                    "## UI Contract Summary",
                    "",
                    f"- Style direction: {ui_contract.get('style_direction', '-')}",
                    f"- Icon system: {icon_system or '-'}",
                    (
                        "- Emoji policy: " f"{ui_contract.get('emoji_policy', {}).get('rule', '-')}"
                        if isinstance(ui_contract.get("emoji_policy"), dict)
                        else "- Emoji policy: -"
                    ),
                    (
                        "- Selected library: "
                        f"{ui_contract.get('ui_library_preference', {}).get('final_selected', '-')}"
                        if isinstance(ui_contract.get("ui_library_preference"), dict)
                        else "- Selected library: -"
                    ),
                    (
                        "- Framework playbook: " f"{framework_playbook.get('framework', '-')}"
                        if framework_playbook
                        else "- Framework playbook: -"
                    ),
                ]
            )
        if ui_alignment_summary:
            lines.extend(["", "## UI Contract Alignment Summary", ""])
            for key, value in ui_alignment_summary.items():
                if not isinstance(value, dict):
                    continue
                lines.append(
                    f"- {value.get('label', key)}: {'ok' if value.get('passed') else 'gap'} | "
                    f"expected={value.get('expected', '-') or '-'} | observed={value.get('observed', '-') or '-'}"
                )
            key_areas = ui_alignment_key_areas
            if key_areas:
                lines.extend(["", "## Key Structural Alignment", ""])
                for key, alignment_value in key_areas.items():
                    lines.append(
                        f"- {alignment_value.get('label', key)}: "
                        f"{'ok' if alignment_value.get('passed') else 'gap'}"
                    )
        if banned_pattern_probe.get("observed"):
            lines.extend(
                [
                    "",
                    "## Runtime Banned Pattern Probe",
                    "",
                    f"- passed: {'yes' if banned_pattern_probe.get('passed') else 'no'}",
                    f"- observed: {', '.join(str(item) for item in banned_pattern_probe.get('observed', []))}",
                ]
            )
        report_paths["markdown"].write_text("\n".join(lines) + "\n", encoding="utf-8")
        report_with_identity["report_files"] = {name: str(path) for name, path in report_paths.items()}
        return report_with_identity
