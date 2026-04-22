# 发布指南（入口页）

> 维护者专用。普通用户不需要阅读这份文档。
>
> 这份文档只保留最短发布路径。完整步骤、回滚策略和紧急处理统一以 [`docs/RELEASE_RUNBOOK.md`](./RELEASE_RUNBOOK.md) 为准。

## 正式发布标准

只有同时满足下面 4 条，才算真正达到发布标准：

1. 版本号和本次版本说明已更新
2. 工作树干净
3. `./scripts/preflight.sh` 在不带 `--allow-dirty` 的情况下通过
4. 再执行正式发布动作

## 最短发布路径

1. 更新版本号：
   - `pyproject.toml`
   - `super_dev/__init__.py`
2. 更新本次版本说明：
   - `docs/releases/<version>.md`
3. 在干净工作树下运行正式预检：

```bash
./scripts/preflight.sh
```

4. 预检通过后执行发布：

```bash
export PYPI_API_TOKEN="<your-token>"
./scripts/release.sh --repository pypi --yes
```

## 重要规则

- `./scripts/preflight.sh --allow-dirty` 只用于本地调试或并行改动阶段的验收，不作为正式发版凭据。
- 正式发版前必须整理工作树，并在干净状态下重新跑一次预检。
- GitHub Release、Tag、回滚和补丁发布都统一看 [`docs/RELEASE_RUNBOOK.md`](./RELEASE_RUNBOOK.md)。

## 详细文档

- 发布作战手册：[`docs/RELEASE_RUNBOOK.md`](./RELEASE_RUNBOOK.md)
- 当前版本说明：[`docs/releases/2.4.0.md`](./releases/2.4.0.md)
