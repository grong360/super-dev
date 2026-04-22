# Super Dev 快速开始

> 面向 `2.4.0` 版本，5 分钟完成从安装到首次流水线运行。

## 1. 一句话理解

`Super Dev` 不是给宿主再塞一堆脚手架命令，而是把宿主训练成当前项目的交付教练系统。

- 终端只负责接入、升级、卸载
- 真正开发回到宿主里
- 安装后先看 smoke guide，再复制宿主第一句开工

## 2. 环境要求

- Python `3.10+`

```bash
python3 --version
```

## 3. 安装

### 方式 A：uv 安装（推荐）

```bash
uv tool install super-dev
```

源码安装、指定版本回滚等方式保留在 [INSTALL_OPTIONS.md](/Users/weiyou/Documents/kaifa/super-dev/docs/INSTALL_OPTIONS.md)。

### 方式 B：安装指定版本（复现/回滚）

```bash
uv tool install super-dev==2.4.0
```

## 4. 5 分钟路径

普通用户只需要记住这 3 条终端命令：

```bash
super-dev
super-dev update
super-dev uninstall
```

最短路径：

1. 在项目目录运行 `super-dev`
2. 在安装器里选择目标宿主，让系统默认先写项目级接入面
3. 打开 `output/maintenance/host-onboard-smoke-*.md`
4. 先看 `标准流第一句` / `比赛流第一句`
5. 再看 `接入后先验`、`框架焦点`、`官方工作流检查`
6. 回到宿主里输入第一句

宿主里的推荐表达：

```text
/super-dev 构建一个电商后台，包含登录、订单、支付
/super-dev 继续当前流程
/super-dev 现在下一步是什么
/super-dev-seeai 比赛需求

super-dev: 构建一个电商后台，包含登录、订单、支付
super-dev: 继续当前流程
super-dev: 现在下一步是什么
super-dev-seeai: 比赛需求
```

成功标志：

- 第一轮回复明确说当前阶段是 `research`
- 三份核心文档完成后会停下来等你确认
- 已有项目没有跳过 `baseline -> baseline confirmation -> 差量 research -> 三文档 -> 确认门 -> Spec -> frontend -> backend -> quality`
- 安装后烟测指南已经告诉你这个宿主当前是否 `标准流可直接开工`、`SEEAI 比赛模式可直接开工`

工作模式：

- `new`：新项目，从 0 到 1
- `evolve`：已有项目增量迭代
- `variant`：从现有项目派生新版本或新包装
- `patch`：在现有项目上修 bug / 做整改
- `resume`：恢复当前中断流程

关键规则：

- `evolve / variant / patch` 必须先 `baseline -> baseline confirmation`，系统先分析现有功能、架构、代码与 UI，再进入差量文档。
- 恢复是默认场景，不是补充场景。窗口关闭、电脑重启、第二天继续，都优先在宿主里说“继续当前流程”。

如果你是第二天回来、重开电脑、重开宿主、或者刚完成返工，不要先回终端找流程命令，优先回到宿主里说：

- `继续当前流程`
- `现在下一步是什么`
- `baseline 已确认，可以继续`
- `文档确认，可以继续`
- `前端预览确认，可以继续`

只有安装、升级、诊断、兼容修复或治理收尾时，才需要再回终端。

## 5. 安装后先验什么

安装成功不等于宿主已经真实跑通。先看这些高价值信号：

1. `output/maintenance/host-onboard-smoke-*.md`
2. `标准流第一句` / `比赛流第一句`
3. `框架焦点（Framework Coaching Focus）`
4. `官方工作流检查`
5. `修复优先级`

如果当前项目已经冻结了 `framework playbook`，smoke guide 会直接告诉你框架教练焦点、必验场景和交付证据，不需要你自己翻 UI 合同或 runtime 报告。

如果第一轮 UI 看起来过平、过空、模板味太重，不要把它留到最后再“补美化”。截图级视觉门会继续在：

- `UI review`
- `quality gate`
- `proof-pack`
- `release readiness`

里拦截这个状态。

## 6. 维护边界

其余 CLI 能力仍然存在，但属于维护 / 治理入口，不应当成日常开发主路径：
- `skill / integrate / doctor / detect / onboard`：宿主接入、兼容性诊断、真人验收
- `config / enforce / generate / clean`：内部维护与底层执行工具
- `run / review / release / quality / spec / task`：治理桥接层，只在报告明确要求时再用
- 真正的业务开发仍应优先在宿主里说“继续当前流程”“现在下一步是什么”
- 已有项目做 `evolve / variant / patch` 时，不要先到终端里手工推进阶段，优先让宿主完成 `baseline -> baseline confirmation`
- 只是恢复昨天的流程时，不要先到终端里找 `jump / confirm / next`，优先在宿主里走 `resume`

如果只是想先看卸载会删什么，用：

```bash
super-dev uninstall --dry-run
```

并查看：

- `output/maintenance/host-cleanup-*.json`
- `output/maintenance/host-cleanup-*.md`

## 7. 维护者：发布前质量门禁

```bash
./scripts/preflight.sh
```

预检会执行：`ruff`、`mypy`、`pytest`、`delivery-smoke`、`bandit(-ll)`、`pip-audit`、benchmark、build、twine check。

如果你在真实项目里用 Super Dev 编码，额外建议宿主在每轮实现后补做这 4 项：

1. 跑项目原生 `build / compile / type-check / test / runtime smoke`
2. 确认新增函数、方法、字段、模块都已经接入调用链
3. 确认没有新增 `unused code` 或新增 warning
4. 对本次 diff 做一次最小自审，再汇报完成

## 8. 下一步

- 普通用户到这里就够了，继续看全量说明：[`README.md`](../README.md)
- 只有维护者准备正式发版时，才继续阅读：
  - 发布入口：[`docs/PUBLISHING.md`](./PUBLISHING.md)
  - 完整作战手册：[`docs/RELEASE_RUNBOOK.md`](./RELEASE_RUNBOOK.md)
