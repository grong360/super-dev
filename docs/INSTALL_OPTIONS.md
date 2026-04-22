# Super Dev 安装方式（2.4.0）

先说结论：

- 首页和默认安装口径统一以 `uv tool install super-dev` 为主
- `uv` 是默认安装方式
- `super-dev` 是跨平台入口：Windows、macOS、Linux 都先装包再直接运行 `super-dev`
- 仓库内的 `install.sh` 只是 macOS/Linux 便捷入口，不是 Windows 的唯一安装方式
- 安装真正完成的判断，不是“终端提示写入成功”，而是 `host-onboard-smoke` 里的首句、先验、框架焦点和官方工作流检查都对上了

宿主详细试用方式请看：

- [HOST_USAGE_GUIDE.md](/Users/weiyou/Documents/kaifa/super-dev/docs/HOST_USAGE_GUIDE.md)

## 方式 1：uv 安装（推荐）

```bash
uv tool install super-dev
```

适用：本机命令行工具安装、独立环境、默认官网安装路径。

升级：

```bash
super-dev update
```

## 方式 2：安装指定版本（复现/回滚）

```bash
uv tool install super-dev==2.4.0
```

适用：需要稳定复现、灰度回滚。

安装完成后，直接执行：

```bash
super-dev
```

默认会进入交互式宿主安装引导。当前矩阵统一按 `CLI / IDE / 桌面助手` 分组：

1. 顶部显示 `Super Dev` 安装入口
2. `↑ / ↓` 选择宿主
3. `Space` 勾选宿主
4. `Enter` 开始安装
5. `A` 全选
6. `C` 仅选择 CLI 宿主
7. `I` 仅选择 IDE 宿主
8. `R` 清空选择

安装完成后，终端会直接输出该宿主的最终触发方式。安装器默认采用项目优先注入：先写项目级接入面，再按需补齐用户/全局接入面。

1. 原生 slash 宿主：`/super-dev 你的需求`
2. Codex App/Desktop：从 `/` 列表选择 `super-dev`
3. Codex CLI：`$super-dev`
4. Droid CLI：优先 `/super-dev 你的需求`；比赛模式 `/super-dev-seeai 比赛需求`；回退 `super-dev: 你的需求`
5. 非 slash 宿主：`super-dev: 你的需求` 或 `super-dev：你的需求`

并且会直接显示：

1. `标准流第一句`
2. `比赛流第一句`
3. `接入后先验`
4. `框架焦点（Framework Coaching Focus）`
5. `官方工作流检查`
6. `修复优先级`

这样安装完就能直接判断：

- 这个宿主现在能不能直接开标准项目
- 这个宿主现在能不能直接开 SEEAI 比赛模式
- 对依赖用户级 Skills 的宿主，标准版 Skill 和 SEEAI 比赛版 Skill 是否分别就绪
- 如果还没 ready，第一步该怎么补

并且会在仓库里落盘安装后烟测指南：

- `output/maintenance/host-onboard-smoke-*.json`
- `output/maintenance/host-onboard-smoke-*.md`

建议先按这份 smoke guide 验收：

1. 标准流第一句
2. 比赛流第一句
3. 接入后先验
4. 框架焦点、必验场景与交付证据
5. 官方工作流检查
6. 恢复指导和修复剧本

安装结束后，终端就应该退场。真正开发回到宿主里，先复制首句，再按 smoke guide 验证；如果宿主没进入 `research -> 三文档 -> 等待确认`，再回终端跑 `doctor`。

一句话记忆：

- 安装：`super-dev`
- 升级：`super-dev update`
- 清理前先预演：`super-dev uninstall --dry-run`
- 真正开发：回宿主复制第一句，不要继续停留在终端

## 安装后 5 分钟应该完成什么

1. `uv tool install super-dev`
2. 在项目目录运行 `super-dev`
3. 让安装器写入项目级接入面
4. 打开 `output/maintenance/host-onboard-smoke-*.md`
5. 先看 `标准流第一句` / `比赛流第一句`
6. 再看 `接入后先验`、`框架焦点`、`官方工作流检查`
7. 回到宿主触发第一句，确认宿主真的进入 `research -> 三文档 -> 等待确认`

这 5 分钟路径比“看到了安装成功提示”更重要，因为它验证的是宿主是否已经被训练成当前项目的教练系统。

## 方式 3：GitHub 直装（Tag）

```bash
uv tool install --from git+https://github.com/shangyankeji/super-dev.git@v2.4.0 super-dev
```

适用：希望直接基于 GitHub Tag 安装。

## 方式 4：源码开发安装

```bash
git clone https://github.com/shangyankeji/super-dev.git
cd super-dev
uv sync
uv run super-dev --help
```

适用：二次开发、调试、提交代码。

## 验证

```bash
super-dev --help
super-dev
```

如果已接入宿主，推荐在宿主内验证：

1. 支持原生映射的宿主：`/super-dev 你的需求`
2. Codex App/Desktop：从 `/` 列表选择 `super-dev`
3. Codex CLI：在会话内输入 `$super-dev`
4. 自然语言回退宿主：输入 `super-dev: 你的需求`
5. 对需要用户级增强面的宿主，只有显式启用 `--with-user-surfaces` 时才补齐用户/全局接入面；默认仍以项目级接入面为主

如果要清理接入面，先预演：

```bash
super-dev uninstall --dry-run
```

卸载也会落盘 cleanup report：

- `output/maintenance/host-cleanup-*.json`
- `output/maintenance/host-cleanup-*.md`

先预演再清理，是当前推荐动作。它更像企业产品里的 cleanup audit，而不是“直接删完再说”。

如果你是在清理一次已经验收过的宿主接入，建议顺手保留：

- 本轮 `host-onboard-smoke` 报告
- `host-cleanup` 预演报告
- 当前宿主的 `框架焦点（Framework Coaching Focus）` 与交付证据

默认流程不是直接编码，而是：

1. 先研究同类产品，输出 `output/*-research.md`
2. 再生成 PRD、架构、UI/UX 三份核心文档
3. 等用户确认三份核心文档
4. 再生成 Spec 与 `tasks.md`
5. 最后才进入编码、质量门禁与交付

宿主接入完成后，普通用户应直接回宿主做真实触发与恢复验证。只有维护者在补正式验收证据时，才进入 `integrate smoke` 这条维护链。

## 升级到 2.4.0

```bash
# uv 方式
uv tool upgrade super-dev

# GitHub 方式
uv tool install --reinstall --from git+https://github.com/shangyankeji/super-dev.git@v2.4.0 super-dev
```

升级后建议立刻做两件事：

1. 重开终端，执行 `super-dev --version`
2. 如果宿主后续没有进入 `research -> 三文档 -> 等待确认`，再回终端执行 `super-dev doctor --host <host> --repair --force`
