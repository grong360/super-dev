#!/usr/bin/env python3
"""
交付包门禁检查工具

用途：
1. 校验当前项目 output/delivery 下最新 manifest 是否为 ready
2. 通过 --smoke 在临时目录执行一次离线 pipeline，验证交付链路端到端可用
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _latest_manifest(project_dir: Path) -> Path:
    delivery_dir = project_dir / "output" / "delivery"
    candidates = sorted(
        delivery_dir.glob("*-delivery-manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"未找到交付清单: {delivery_dir}/*-delivery-manifest.json")
    return candidates[0]


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"清单解析失败: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"清单格式非法（非 JSON object）: {path}")
    return data


def _check_manifest(path: Path) -> tuple[bool, str]:
    data = _load_manifest(path)
    status = str(data.get("status", ""))
    missing_required = data.get("missing_required", [])
    missing_count = (
        len(missing_required)
        if isinstance(missing_required, list)
        else -1
    )
    included_files = data.get("included_files", [])
    included_count = (
        len(included_files)
        if isinstance(included_files, list)
        else -1
    )

    if status != "ready":
        return False, f"交付状态非 ready: status={status}"
    if missing_count != 0:
        return False, f"仍有缺失必需项: missing_required_count={missing_count}"
    if included_count <= 0:
        return False, "交付清单为空: included_files 为空"
    return True, "交付门禁通过"


def _write_skipped_quality_gate_note(smoke_dir: Path, project_name: str) -> Path:
    report = smoke_dir / "output" / f"{project_name}-quality-gate.md"
    report.write_text(
        "\n".join(
            [
                "# 质量门禁报告",
                "",
                "> delivery smoke 使用 `--skip-quality-gate` 仅验证交付打包链路。",
                f"> generated_at: {datetime.now(timezone.utc).isoformat()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _auto_confirm_review(cli: Any, review_type: str) -> None:
    result = cli.run(
        [
            "review",
            review_type,
            "--status",
            "confirmed",
            "--comment",
            "smoke auto confirm",
        ]
    )
    if result != 0:
        raise RuntimeError(f"pipeline smoke {review_type} 确认失败: exit={result}")


def _run_smoke(project_root: Path) -> Path:
    # 延迟导入，避免仅校验 manifest 时引入额外依赖
    from super_dev.cli import SuperDevCLI
    from super_dev.workflow_guard import docs_gate_status, preview_gate_status

    with tempfile.TemporaryDirectory(prefix="super-dev-delivery-smoke-") as tmp:
        smoke_dir = Path(tmp)
        old_cwd = Path.cwd()
        old_disable_web = os.environ.get("SUPER_DEV_DISABLE_WEB")
        old_allow_no_host = os.environ.get("SUPER_DEV_ALLOW_NO_HOST")
        try:
            os.chdir(smoke_dir)
            os.environ["SUPER_DEV_DISABLE_WEB"] = "1"
            os.environ["SUPER_DEV_ALLOW_NO_HOST"] = "1"
            policy_dir = smoke_dir / ".super-dev"
            policy_dir.mkdir(parents=True, exist_ok=True)
            (policy_dir / "policy.yaml").write_text(
                (
                    "require_redteam: true\n"
                    "require_quality_gate: false\n"
                    "require_rehearsal_verify: true\n"
                    "min_quality_threshold: 70\n"
                    "allowed_cicd_platforms:\n"
                    "  - all\n"
                ),
                encoding="utf-8",
            )
            cli = SuperDevCLI()
            result = cli.run(
                [
                    "pipeline",
                    "构建一个最小登录系统",
                    "--offline",
                    "--name",
                    "release-smoke",
                    "--platform",
                    "web",
                    "--frontend",
                    "react",
                    "--backend",
                    "python",
                    "--cicd",
                    "all",
                    "--skip-quality-gate",
                    "--quality-threshold",
                    "75",
                ]
            )
            if result != 0:
                raise RuntimeError(f"pipeline smoke 执行失败: exit={result}")

            manifest = smoke_dir / "output" / "delivery" / "release-smoke-delivery-manifest.json"
            if not manifest.exists():
                resume_result = 0
                for _ in range(8):
                    docs_status = docs_gate_status(smoke_dir)
                    preview_status = preview_gate_status(smoke_dir)
                    if docs_status.get("has_context") and not docs_status.get("confirmed"):
                        _auto_confirm_review(cli, "docs")
                    elif preview_status.get("has_context") and not preview_status.get("confirmed"):
                        _auto_confirm_review(cli, "preview")
                    resume_result = cli.run(["run", "--resume"])
                    if manifest.exists():
                        break
                    try:
                        manifest = _latest_manifest(smoke_dir)
                        break
                    except FileNotFoundError:
                        continue
                if resume_result != 0 and not manifest.exists():
                    raise RuntimeError(f"pipeline smoke 恢复执行失败: exit={resume_result}")

            if not manifest.exists():
                # 回退查找最新 manifest，避免名称变更导致误判
                manifest = _latest_manifest(smoke_dir)

            data = _load_manifest(manifest)
            missing_required = data.get("missing_required", [])
            if (
                isinstance(missing_required, list)
                and data.get("status") != "ready"
                and {
                    str(item.get("path", ""))
                    for item in missing_required
                    if isinstance(item, dict)
                }
                == {"output/release-smoke-quality-gate.md"}
            ):
                from super_dev.deployers.delivery import DeliveryPackager

                _write_skipped_quality_gate_note(smoke_dir, "release-smoke")
                manifest_payload = DeliveryPackager(
                    smoke_dir,
                    "release-smoke",
                ).package(cicd_platform="all")
                manifest = Path(str(manifest_payload["manifest_file"]))

            ok, message = _check_manifest(manifest)
            if not ok:
                raise RuntimeError(f"pipeline smoke 交付门禁失败: {message}")

            # 复制清单到项目 output/release，便于发布留痕
            report_dir = project_root / "output" / "release"
            report_dir.mkdir(parents=True, exist_ok=True)
            smoke_manifest = report_dir / "delivery-smoke-manifest.json"
            smoke_manifest.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
            return smoke_manifest
        finally:
            os.chdir(old_cwd)
            if old_disable_web is None:
                os.environ.pop("SUPER_DEV_DISABLE_WEB", None)
            else:
                os.environ["SUPER_DEV_DISABLE_WEB"] = old_disable_web
            if old_allow_no_host is None:
                os.environ.pop("SUPER_DEV_ALLOW_NO_HOST", None)
            else:
                os.environ["SUPER_DEV_ALLOW_NO_HOST"] = old_allow_no_host


def main() -> int:
    parser = argparse.ArgumentParser(description="Super Dev 交付包门禁检查")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="项目根目录（默认当前目录）",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="指定 manifest 路径；不传则自动查找 output/delivery 最新文件",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="执行离线 pipeline smoke，并校验交付包 ready",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if args.smoke:
        smoke_manifest = _run_smoke(project_dir)
        print(f"[PASS] 交付门禁 smoke 通过: {smoke_manifest}")
        return 0

    try:
        manifest_path = Path(args.manifest).resolve() if args.manifest else _latest_manifest(project_dir)
        ok, message = _check_manifest(manifest_path)
    except Exception as exc:
        print(f"[FAIL] 交付门禁检查失败: {exc}")
        return 1

    if not ok:
        print(f"[FAIL] {message} ({manifest_path})")
        return 1

    print(f"[PASS] {message}: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
