"""
终端输出兼容层。

作用：
- 在 UTF-8 终端中保留 Rich/Unicode 视觉符号
- 在非 UTF-8 终端（例如 Windows cp936）中自动降级为 ASCII
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from typing import Any

try:
    from rich.console import Console
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - rich 在主环境中始终可用
    class Console:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class Text(str):  # type: ignore[no-redef]
        pass

    RICH_AVAILABLE = False


UNICODE_FALLBACKS = {
    "✓": "*",
    "✗": "X",
    "⚠": "!",
    "●": ">",
    "▸": ">",
    "○": "o",
    "→": "->",
    "…": "...",
    "•": "-",
}

SYMBOL_MAP = {
    "success": "✓",
    "failure": "✗",
    "warning": "⚠",
    "cursor": ">",
    "selected": "✓",
    "unselected": "○",
}


def terminal_output_mode() -> str:
    """输出模式：auto / unicode / ascii。"""
    mode = os.environ.get("SUPER_DEV_OUTPUT_MODE", "auto").strip().lower()
    if mode in {"unicode", "ascii"}:
        return mode
    return "auto"


def _set_windows_console_utf8() -> bool:
    """尽量把 Windows 控制台切到 UTF-8。失败时返回 False。"""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        return False

    success = False
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
                success = True
            except Exception:
                continue
    return success


def initialize_terminal_output() -> None:
    """初始化终端输出策略。"""
    mode = terminal_output_mode()
    if mode == "ascii":
        return
    _set_windows_console_utf8()


def supports_unicode_output() -> bool:
    """判断当前标准输出是否适合直接输出 Unicode UI 符号。

    检测策略参考 Inquirer.js / @inquirer/figures 的 isUnicodeSupported：
    - 非 Windows: 除了 linux console (TERM=linux) 外都支持
    - Windows: 检测 Windows Terminal / VS Code / ConEmu 等现代终端
    - 兜底: 检查 stdout encoding 是否包含 utf
    """
    mode = terminal_output_mode()
    if mode == "unicode":
        return True
    if mode == "ascii":
        return False

    # 非 Windows 平台：macOS / Linux 桌面终端几乎都支持 Unicode
    if sys.platform != "win32":
        # Linux console (kernel tty) 不支持 Unicode
        term = os.environ.get("TERM", "")
        if term == "linux":
            return False
        # macOS Terminal / iTerm / Alacritty / Kitty 等都支持
        return True

    # Windows 平台：检测现代终端
    if (
        os.environ.get("WT_SESSION")  # Windows Terminal
        or os.environ.get("TERMINUS_SUBLIME")  # Terminus
        or os.environ.get("ConEmuTask") == "{cmd::Cmder}"  # ConEmu/Cmder
        or os.environ.get("TERM_PROGRAM") == "vscode"  # VS Code terminal
        or os.environ.get("TERM") in ("xterm-256color", "alacritty")
        or os.environ.get("TERMINAL_EMULATOR") == "JetBrains-JediTerm"
    ):
        return True

    # 兜底：检查 encoding
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in encoding


def output_mode_label() -> str:
    """当前终端输出模式标签。"""
    return "unicode" if supports_unicode_output() else "ascii-fallback"


def output_mode_reason() -> str:
    """输出模式原因说明。"""
    mode = terminal_output_mode()
    if mode == "unicode":
        return "SUPER_DEV_OUTPUT_MODE=unicode"
    if mode == "ascii":
        return "SUPER_DEV_OUTPUT_MODE=ascii"
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    if "utf" in encoding:
        return f"stdout encoding={encoding}"
    return f"stdout encoding={encoding or 'unknown'}"


def normalize_terminal_text(value: str) -> str:
    """将不安全的 Unicode 终端符号降级为 ASCII。"""
    if supports_unicode_output():
        return value
    normalized = value
    for src, dst in UNICODE_FALLBACKS.items():
        normalized = normalized.replace(src, dst)
    return normalized


def symbol(name: str) -> str:
    """返回当前终端模式下安全的符号。"""
    return normalize_terminal_text(SYMBOL_MAP[name])


def _normalize_args(args: tuple[Any, ...]) -> tuple[Any, ...]:
    normalized: list[Any] = []
    for arg in args:
        if isinstance(arg, str):
            normalized.append(normalize_terminal_text(arg))
        elif RICH_AVAILABLE and isinstance(arg, Text):
            cloned = arg.copy()
            cloned.plain = normalize_terminal_text(cloned.plain)
            normalized.append(cloned)
        else:
            normalized.append(arg)
    return tuple(normalized)


def patch_console_print(console: Console) -> Console:
    """为 Rich Console 注入输出兼容层。"""
    original_print: Callable[..., Any] = console.print

    def _wrapped_print(*args: Any, **kwargs: Any) -> Any:
        return original_print(*_normalize_args(args), **kwargs)

    console.print = _wrapped_print  # type: ignore[method-assign]
    return console


class FallbackConsole:
    """当 rich 不可用时的降级 Console，提供基本 print 功能。"""

    def print(self, *args: Any, **kwargs: Any) -> None:
        """降级为内置 print，忽略 rich 专用参数。"""
        rich_only_keys = {"style", "highlight", "markup", "justify", "overflow", "end"}
        filtered = {k: v for k, v in kwargs.items() if k not in rich_only_keys}
        texts = []
        for arg in args:
            text = str(arg)
            # 移除 rich markup 标签
            text = re.sub(r"\[/?[a-zA-Z_ ]+\]", "", text)
            texts.append(normalize_terminal_text(text))
        print(*texts, **filtered)

    def rule(self, title: str = "", **kwargs: Any) -> None:
        line = f"--- {title} ---" if title else "---"
        print(normalize_terminal_text(line))

    def log(self, *args: Any, **kwargs: Any) -> None:
        self.print(*args, **kwargs)

    @property
    def width(self) -> int:
        import shutil

        return shutil.get_terminal_size().columns


def create_console() -> Console | FallbackConsole:
    """创建兼容当前终端编码的 Console。rich 不可用时返回 FallbackConsole。"""
    if not RICH_AVAILABLE:
        return FallbackConsole()
    initialize_terminal_output()
    console = Console(safe_box=not supports_unicode_output())
    return patch_console_print(console)
