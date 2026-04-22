"""E2E smoke test — runs the core CLI commands in sequence."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from super_dev import __version__

PYTHON = sys.executable
REPO_ROOT = Path(__file__).resolve().parents[2]


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "").strip()
    repo_path = str(REPO_ROOT)
    env["PYTHONPATH"] = (
        repo_path if not existing else os.pathsep.join([repo_path, existing])
    )
    return env


def test_full_init_to_status_flow():
    """Test: init -> detect -> status -> quality in a temp dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # 1. Init
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "init", "smoke-test", "-f", "next", "-b", "node"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
            env=_subprocess_env(),
        )
        assert result.returncode == 0
        assert (project / "super-dev.yaml").exists()
        assert not (project / ".claude").exists()
        assert not (project / ".cursor").exists()

        # 2. Status
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "status"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=_subprocess_env(),
        )
        # Should not crash
        assert result.returncode in (0, 1)

        # 3. Enforce status
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "enforce", "status"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=_subprocess_env(),
        )
        assert result.returncode in (0, 1)

        # 7. Version
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "--version"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=_subprocess_env(),
        )
        assert result.returncode == 0
        assert __version__ in result.stdout


def test_root_help_surfaces_public_entrypoints_only():
    """Test: root help shows the public three-command model by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "--help"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=_subprocess_env(),
        )
        assert result.returncode == 0
        assert "Super Dev Public Help" in result.stdout
        assert "super-dev           打开宿主安装 / 接入引导" in result.stdout
        assert "super-dev update    更新到最新版本" in result.stdout
        assert "super-dev uninstall 完整清理宿主接入面" in result.stdout
        assert "内部维护 / 治理命令请使用: super-dev --help-all" in result.stdout
        assert "可用命令:" not in result.stdout


def test_root_help_all_exposes_internal_command_index():
    """Test: help-all still exposes the internal command catalog."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [PYTHON, "-m", "super_dev.cli", "--help-all"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=_subprocess_env(),
        )
        assert result.returncode == 0
        assert "Super Dev Internal Command Index" in result.stdout
        assert "内部维护命令索引" in result.stdout
        assert "普通用户公开终端入口仍然只有 super-dev / super-dev update / super-dev" in result.stdout
        assert "uninstall" in result.stdout
        assert "onboard             内部维护：首次接入向导" in result.stdout
        assert "resume              回到当前仓库的 Super Dev 流程" in result.stdout
