# Release Runbook

面向生产发布的标准流程（商业级），用于降低发布失败和回滚风险。

> 维护者专用。普通用户不需要进入这份文档。

## 发布标准

一版只有在下面条件同时成立时，才算真正可发布：

- 版本号与 release notes 已更新
- 工作树干净
- `./scripts/preflight.sh` 正式通过，且没有使用 `--allow-dirty`
- 发布、Tag、GitHub Release、回滚策略都已按 runbook 走完

## 1. 发布前准备

- 确认版本号已更新：`pyproject.toml`
- 确认更新日志或 Release Notes 已准备：`CHANGELOG.md` / `docs/releases/*.md`
- 确认主分支状态与发布分支策略（建议从 `main` 发布）
- 确认 PyPI Token 可用（`PYPI_API_TOKEN`）

## 2. 预检（必须通过）

运行非交互预检：

```bash
./scripts/preflight.sh
```

调试模式（工作区有未提交内容时）：

```bash
./scripts/preflight.sh --allow-dirty --skip-package
```

注意：

- `--allow-dirty` 只用于本地调试、并行改动阶段或临时验收。
- 正式发版前必须整理工作树，并在干净状态下重新跑一次不带 `--allow-dirty` 的预检。
- 只有干净工作树上的正式预检通过，才算真正达到发布标准。

如需临时跳过交付门禁烟雾验证（仅本地调试）：

```bash
./scripts/preflight.sh --skip-delivery-smoke
```

预检覆盖项：

- `ruff`
- `type-gates`（release 核心类型门）
- `mypy-full`（advisory）
- `pytest`
- `knowledge-audit`
- `knowledge-gates`
- `scripts/check_delivery_ready.py --smoke`（交付门禁烟雾验证）
- `bandit`（`-ll`，仅阻断 medium/high）
- `pip-audit --local`
- `tests/benchmark.py`
- `python -m build`
- `twine check dist/*`

报告输出目录：

- `output/release/preflight-<timestamp>/summary.txt`
- 对应步骤日志和安全扫描 JSON 文件

## 3. 正式发布步骤

1. 运行预检并确保通过。
2. 确认工作树干净，并且这次通过的是不带 `--allow-dirty` 的正式预检。
3. 执行发布脚本（非交互）：
   - `export PYPI_API_TOKEN="<your-token>"`
   - `./scripts/release.sh --repository pypi --yes`
4. 如需自动打 Tag 并推送：
   - `./scripts/release.sh --repository pypi --push-tag --yes`
5. 手动打 Tag 并推送（可选）：
   - `git tag v<version>`
   - `git push origin v<version>`
6. 自动创建 GitHub Release（附变更说明和风险提示）：
   - `./scripts/release.sh --repository pypi --push-tag --github-release --generate-notes --yes`
7. 如果 tag 已存在、只缺 GitHub Release：
   - `./scripts/release.sh --skip-publish --github-release --generate-notes --yes`

当前仓库不依赖 GitHub Actions 自动发布，发布链路以本地预检 + 本地脚本发布为准。

## 4. 发布后验证

- `uv tool install super-dev==<version>`
- 核心命令冒烟：
  - `super-dev --help`
  - `super-dev`
  - 宿主内 `/super-dev 构建一个包含登录和订单的系统`

## 5. 回滚策略（必须预案）

注意：PyPI 不允许删除已发布版本，推荐以下流程：

1. 若发现严重问题，先在 PyPI 对问题版本执行 `yank`。
2. 立即发布修复补丁版本（`x.y.(z+1)`）。
3. 在 GitHub Release 和 CHANGELOG 明确标注受影响版本和规避方案。

示例：

```bash
# 发布补丁版本（非交互）
export PYPI_API_TOKEN="<your-token>"
./scripts/publish.sh --repository pypi --yes
```

## 6. 紧急处理

- 发现安全问题：优先发补丁版本并在 CHANGELOG 增加 `Security` 分类。
- 发现安装失败：先做 yanked，再发布修复版本并验证干净环境安装。
- 发现 CLI 关键命令回归：先阻断对外公告，修复后再发布。
