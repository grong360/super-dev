"""
UIUX Compliance Checker — verify frontend implementation matches UIUX spec.

Parses output/*-uiux.md for declared icon library, typography, design tokens,
component ecosystem, and page skeleton, then scans frontend source files for
violations.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".next",
        ".super-dev",
        "output",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "venv",
        "env",
        ".venv",
    }
)

_FRONTEND_EXTENSIONS: frozenset[str] = frozenset(
    {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".css", ".scss", ".less", ".html"}
)

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0001ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    re.UNICODE,
)

# Icon library packages and their import patterns
_ICON_LIBRARIES: dict[str, dict[str, list[str]]] = {
    "lucide": {
        "packages": ["lucide-react", "lucide-vue", "lucide", "lucide-svelte"],
        "patterns": [r"from\s+['\"]lucide", r"import\s+.*lucide"],
    },
    "heroicons": {
        "packages": ["@heroicons/react", "heroicons"],
        "patterns": [r"from\s+['\"]@heroicons", r"import\s+.*heroicons"],
    },
    "tabler": {
        "packages": ["@tabler/icons-react", "@tabler/icons"],
        "patterns": [r"from\s+['\"]@tabler", r"import\s+.*tabler"],
    },
    "phosphor": {
        "packages": ["@phosphor-icons/react", "phosphor-react"],
        "patterns": [r"from\s+['\"]@phosphor", r"import\s+.*phosphor"],
    },
    "material": {
        "packages": ["@mui/icons-material", "@material-ui/icons"],
        "patterns": [r"from\s+['\"]@mui/icons", r"from\s+['\"]@material-ui"],
    },
}

# Hardcoded color patterns (violations of design token usage)
_HEX_COLOR = re.compile(r"(?:color|background|border|bg|text|fill|stroke)\s*[:-]\s*['\"]?(#[0-9a-fA-F]{3,8})['\"]?", re.IGNORECASE)
_RGB_COLOR = re.compile(r"rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)")
_HSL_COLOR = re.compile(r"hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)")


@dataclass
class UIUXViolation:
    """A single UIUX compliance violation."""

    rule: str
    severity: str  # critical | high | medium | low
    expected: str = ""
    actual: str = ""
    file: str = ""
    line: int = 0
    description: str = ""


@dataclass
class UIUXComplianceReport:
    """Full UIUX compliance report."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    declared_icon_library: str = ""
    declared_typography: list[str] = field(default_factory=list)
    declared_tokens: list[str] = field(default_factory=list)
    violations: list[UIUXViolation] = field(default_factory=list)
    score: int = 0
    files_scanned: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "critical")

    @property
    def total_violations(self) -> int:
        return len(self.violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "declared_icon_library": self.declared_icon_library,
            "declared_typography": self.declared_typography,
            "declared_tokens": self.declared_tokens,
            "violations": [asdict(v) for v in self.violations],
            "score": self.score,
            "files_scanned": self.files_scanned,
        }

    def to_markdown(self) -> str:
        lines = [
            "# UIUX Compliance Report",
            "",
            f"**Project**: {self.project_name}",
            f"**Generated**: {self.generated_at}",
            f"**Declared Icon Library**: {self.declared_icon_library or '(not specified)'}",
            f"**Files Scanned**: {self.files_scanned}",
            f"**Violations**: {self.total_violations} (Critical: {self.critical_count})",
            f"**Score**: {self.score}/100",
            "",
            "---",
            "",
        ]

        if self.violations:
            lines.extend(
                [
                    "| Rule | Severity | Expected | Actual | File |",
                    "|:---|:---:|:---|:---|:---|",
                ]
            )
            for v in self.violations:
                lines.append(
                    f"| {v.rule} | {v.severity} | {v.expected} | {v.actual} | {v.file}:{v.line} |"
                )
            lines.append("")
        else:
            lines.append("No violations found. All checks passed.")

        return "\n".join(lines)


def _parse_uiux_doc(uiux_path: Path) -> dict[str, Any]:
    """Extract design declarations from UIUX doc."""
    content = uiux_path.read_text(encoding="utf-8", errors="ignore")
    result: dict[str, Any] = {
        "icon_library": "",
        "typography": [],
        "tokens": [],
    }

    # Detect icon library
    content_lower = content.lower()
    for lib_name in _ICON_LIBRARIES:
        if lib_name in content_lower:
            result["icon_library"] = lib_name
            break

    # Detect typography declarations
    font_patterns = re.findall(
        r"(?:font-family|fontFace|typeface)\s*[:=]\s*['\"]?([^'\";\n,}]+)",
        content,
        re.IGNORECASE,
    )
    for f in font_patterns:
        cleaned = f.strip()
        if cleaned and cleaned not in result["typography"]:
            result["typography"].append(cleaned)

    # Detect token declarations (CSS custom properties)
    token_patterns = re.findall(r"--[\w-]+\s*:", content)
    for t in token_patterns:
        cleaned = t.rstrip(":").strip()
        if cleaned not in result["tokens"]:
            result["tokens"].append(cleaned)

    return result


def _scan_frontend_files(project_dir: Path) -> list[tuple[str, str, list[str]]]:
    """Scan frontend source files. Returns [(rel_path, content, lines)]."""
    files: list[tuple[str, str, list[str]]] = []
    for path in project_dir.rglob("*"):
        if not path.is_file() or path.suffix not in _FRONTEND_EXTENSIONS:
            continue
        parts = path.relative_to(project_dir).parts
        if any(p in _IGNORE_DIRS for p in parts):
            continue
        try:
            rel = str(path.relative_to(project_dir))
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            files.append((rel, content, lines))
        except (OSError, ValueError):
            continue
    return files


def _check_emoji_usage(
    files: list[tuple[str, str, list[str]]],
) -> list[UIUXViolation]:
    """Check for emoji characters used as icons."""
    violations: list[UIUXViolation] = []
    for rel_path, _content, lines in files:
        for line_idx, line in enumerate(lines):
            emojis = _EMOJI_PATTERN.findall(line)
            if emojis:
                # Skip if inside a comment or string literal that is a comment
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("#"):
                    continue
                violations.append(
                    UIUXViolation(
                        rule="no_emoji_icons",
                        severity="critical",
                        expected="Icon from declared library",
                        actual=f"Emoji: {', '.join(emojis[:3])}",
                        file=rel_path,
                        line=line_idx + 1,
                        description="Emoji characters used as functional icons",
                    )
                )
    return violations


def _check_icon_library(
    declared_lib: str,
    files: list[tuple[str, str, list[str]]],
) -> list[UIUXViolation]:
    """Check that icon imports match the declared icon library."""
    if not declared_lib or declared_lib not in _ICON_LIBRARIES:
        return []

    violations: list[UIUXViolation] = []

    for rel_path, content, lines in files:
        for other_lib, other_info in _ICON_LIBRARIES.items():
            if other_lib == declared_lib:
                continue
            for pat in other_info["patterns"]:
                if re.search(pat, content):
                    violations.append(
                        UIUXViolation(
                            rule="icon_library_mismatch",
                            severity="high",
                            expected=f"Icons from {declared_lib}",
                            actual=f"Found imports from {other_lib}",
                            file=rel_path,
                            line=0,
                            description=f"Using {other_lib} icons instead of declared {declared_lib}",
                        )
                    )

    return violations


def _check_hardcoded_colors(
    files: list[tuple[str, str, list[str]]],
) -> list[UIUXViolation]:
    """Check for hardcoded color values instead of design tokens."""
    violations: list[UIUXViolation] = []
    for rel_path, _content, lines in files:
        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("*"):
                continue

            hex_match = _HEX_COLOR.search(line)
            if hex_match:
                color = hex_match.group(1)
                violations.append(
                    UIUXViolation(
                        rule="no_hardcoded_colors",
                        severity="medium",
                        expected="CSS custom property / design token",
                        actual=f"Hex color: {color}",
                        file=rel_path,
                        line=line_idx + 1,
                        description="Hardcoded hex color instead of design token",
                    )
                )

            rgb_match = _RGB_COLOR.search(line)
            if rgb_match:
                violations.append(
                    UIUXViolation(
                        rule="no_hardcoded_colors",
                        severity="medium",
                        expected="CSS custom property / design token",
                        actual=f"RGB color: {rgb_match.group()}",
                        file=rel_path,
                        line=line_idx + 1,
                    )
                )

    return violations


def _check_purple_gradient(
    files: list[tuple[str, str, list[str]]],
) -> list[UIUXViolation]:
    """Check for purple/pink gradient themes."""
    violations: list[UIUXViolation] = []
    purple_gradient = re.compile(
        r"(?:purple|violet|pink|magenta)\s.*(?:gradient|to\s+(?:purple|violet|pink))",
        re.IGNORECASE,
    )

    for rel_path, content, lines in files:
        if purple_gradient.search(content):
            violations.append(
                UIUXViolation(
                    rule="no_purple_gradient",
                    severity="high",
                    expected="Non-purple/pink theme",
                    actual="Purple/pink gradient detected",
                    file=rel_path,
                    line=0,
                    description="Purple/pink gradient theme violates design guidelines",
                )
            )
    return violations


def run_uiux_compliance(
    project_dir: Path,
    output_dir: Path | None = None,
) -> UIUXComplianceReport:
    """Run UIUX compliance check: spec vs. frontend implementation.

    Args:
        project_dir: Root of the project to scan.
        output_dir: Directory to write reports. Defaults to project_dir/output/.

    Returns:
        UIUXComplianceReport with violations.
    """
    if output_dir is None:
        output_dir = project_dir / "output"

    report = UIUXComplianceReport(project_name=project_dir.name)

    # Find UIUX doc
    uiux_files = list(output_dir.glob("*-uiux.md")) + list(output_dir.glob("*uiux*.md"))

    declared: dict[str, Any] = {}
    if uiux_files:
        declared = _parse_uiux_doc(uiux_files[0])
        report.declared_icon_library = declared.get("icon_library", "")
        report.declared_typography = declared.get("typography", [])
        report.declared_tokens = declared.get("tokens", [])

    # Scan frontend
    frontend_files = _scan_frontend_files(project_dir)
    report.files_scanned = len(frontend_files)

    if not frontend_files:
        report.score = 100
        return report

    # Run all checks
    violations: list[UIUXViolation] = []
    violations.extend(_check_emoji_usage(frontend_files))
    violations.extend(_check_icon_library(report.declared_icon_library, frontend_files))
    violations.extend(_check_hardcoded_colors(frontend_files))
    violations.extend(_check_purple_gradient(frontend_files))

    report.violations = violations

    # Score: start at 100, subtract for violations
    penalty = 0
    for v in violations:
        if v.severity == "critical":
            penalty += 10
        elif v.severity == "high":
            penalty += 7
        elif v.severity == "medium":
            penalty += 3
        else:
            penalty += 1
    report.score = max(0, 100 - penalty)

    # Persist
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "uiux-compliance.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "uiux-compliance.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )

    return report
