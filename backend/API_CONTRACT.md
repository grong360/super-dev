# API Contract

当前仓库的服务接口主要由 `super_dev/web/api.py` 暴露。  
它不是独立产品后台，而是当前仓库的宿主治理消费面：读取 workflow、宿主接入状态、UI/质量/交付证据，并给本地控制台或内部工具消费。

## 产品边界

- 终端公开命令只保留：
  - `super-dev`
  - `super-dev update`
  - `super-dev uninstall`
- 实际开发主路径在宿主内完成：
  - `/super-dev <需求>` 或 `super-dev: <需求>`
  - `/super-dev-run <stage|resume>` 或 `super-dev-run: <stage|resume>`
  - `/super-dev-review baseline confirm`
  - `/super-dev-review <target> <action>`
- `evolve / variant / patch` 必须先 `baseline -> baseline confirmation` 当前项目，再进入三文档与实现。
- `resume` 是默认场景；窗口关闭、关机、第二天回来后应沿用 `.super-dev/` 和 `output/` 继续，而不是重新开题。

## 当前路由族

### Workflow

| Method | Path | Purpose |
|:---|:---|:---|
| POST | `/api/workflow/run` | 启动或推进 workflow 阶段；已有项目工作应先完成 `baseline -> baseline confirmation` |
| GET | `/api/workflow/status/{run_id}` | 读取当前 run 的阶段、gate、baseline confirmation / resume 状态 |
| GET/POST | `/api/workflow/baseline-confirmation` | 基线确认门 |
| GET/POST | `/api/workflow/docs-confirmation` | 文档确认门 |
| GET/POST | `/api/workflow/ui-revision` | UI 修订门 |
| GET/POST | `/api/workflow/architecture-revision` | 架构修订门 |
| GET/POST | `/api/workflow/quality-revision` | 质量修订门 |
| GET | `/api/workflow/runs` | 列出 workflow 运行记录 |
| GET | `/api/workflow/artifacts/{run_id}` | 查看当前 run 的工件 |
| GET | `/api/workflow/artifacts/{run_id}/archive` | 下载当前 run 的工件打包 |
| GET | `/api/workflow/ui-review/{run_id}` | 查看 UI 审查与 UI 治理摘要 |

### Hosts

| Method | Path | Purpose |
|:---|:---|:---|
| GET | `/api/hosts/doctor` | 读取宿主接入健康状态 |
| GET | `/api/hosts/validate` | 读取宿主接入/协议验证状态 |
| GET/POST | `/api/hosts/runtime-validation` | 读取或更新宿主 runtime 验证结果 |

### Release

| Method | Path | Purpose |
|:---|:---|:---|
| GET | `/api/release/readiness` | 读取当前交付是否具备 release readiness |
| GET | `/api/release/proof-pack` | 读取 proof-pack 摘要与关键证据 |

### Catalog / Config

| Method | Path | Purpose |
|:---|:---|:---|
| GET | `/api/health` | 基础健康检查 |
| GET/PUT | `/api/config` | 读取或更新本地项目配置 |
| POST | `/api/init` | 初始化 Super Dev 项目状态 |
| GET | `/api/catalogs` | 读取宿主、平台、技术栈等目录信息 |
| GET | `/api/phases` | 读取当前 workflow phase 定义 |
| GET | `/api/experts` | 读取当前专家编排目录 |

## 当前消费重点

当前 API 最重要的不是“发起开发”，而是消费这些状态：

- 当前 run 停在哪个 gate
- 现有项目是否完成 baseline，以及 baseline confirmation 是否已通过
- 恢复时应该继续哪一步
- UI/runtime/quality/release 证据是否闭环
- 当前宿主是否真的已接好并可继续执行

所以它应该继续保持“治理消费面”定位，而不是扩成独立平台控制台。
