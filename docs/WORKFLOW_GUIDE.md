# Super Dev 详细使用指南（2.4.0）

> 宿主详细试用方式、是否支持 `/super-dev`、各宿主正确入口，请优先查看：
> [HOST_USAGE_GUIDE.md](/Users/weiyou/Documents/kaifa/super-dev/docs/HOST_USAGE_GUIDE.md)

> 普通用户优先看：
> - [README.md](/Users/weiyou/Documents/kaifa/super-dev/README.md)
> - [QUICKSTART.md](/Users/weiyou/Documents/kaifa/super-dev/docs/QUICKSTART.md)
> - [HOST_USAGE_GUIDE.md](/Users/weiyou/Documents/kaifa/super-dev/docs/HOST_USAGE_GUIDE.md)
>
> 本文包含维护者工作流、Spec/Task 闭环和发布边界，不是普通用户的第一份入口文档。

> 本文是项目级操作手册，覆盖：
> - 指令大全（命令怎么用）
> - 0-1 从零新建项目
> - 1-N+1 增量迭代项目（包含 1-1+N 场景）
> - 商业级质量门禁与交付流程

> 先记住边界：
> - 公开主路径只有两层：终端接入/升级/卸载，宿主内推进主流水线
> - `skill / integrate` 只属于宿主接入与验收
> - `config / enforce / generate` 只属于内部维护，不是业务开发主路径

---

## 1. 概念与入口

### 1.1 推荐入口

普通用户最终只需要记住 3 个终端命令：

```bash
super-dev
super-dev update
super-dev uninstall
```

默认推荐先在宿主内触发 `Super Dev`：

```text
原生 slash 宿主: /super-dev 你的功能需求
Codex App/Desktop: 从 / 列表选择 super-dev
Codex CLI: $super-dev
自然语言回退: super-dev: 你的功能需求
```

普通用户优先只记住这些宿主表达：

```text
/super-dev <goal>
/super-dev-seeai <goal>
继续当前流程
现在下一步是什么
```

工作模式固定为：

- `new`：从 0 到 1 的新项目
- `evolve`：已有项目增量迭代
- `variant`：基于当前项目派生 1-N+1 版本
- `patch`：已有项目 bugfix / remediation
- `resume`：恢复当前中断流程

硬规则：

- `new` 可以直接进入 `research -> docs`
- `evolve / variant / patch` 必须先做 `baseline`
- `resume` 是默认场景，关窗口、关电脑、第二天继续都先恢复，不先重开题

如果你不确定当前机器该用哪个宿主，先运行：

```bash
super-dev
```

非日常主路径说明：
- `skill / integrate`：接入宿主、补协议面、做兼容性审计和真人验收时使用
- `config / enforce / generate`：内部维护与底层执行工具，不建议普通用户记忆
- 日常开发优先回到宿主，用 `/super-dev`、`super-dev:`、`继续当前流程`、`现在下一步是什么`

默认启用宿主硬门禁：若没有 `ready` 宿主，流水线会阻断并提示先接入宿主。

推荐宿主表达示例：

```text
/super-dev 做一个企业级项目管理系统，支持登录、RBAC、项目、任务、报表、审计日志
/super-dev 在当前 CRM 项目里新增 billing center
/super-dev 继续当前流程
/super-dev 文档确认，可以继续当前流程
```

系统会自动进入受治理的主流水线：

1. `new`：research -> docs -> docs_confirm -> spec -> frontend -> preview_confirm -> backend -> quality -> delivery
2. `evolve / variant / patch`：baseline -> 差量 research -> docs -> docs_confirm -> spec -> frontend -> preview_confirm -> backend -> quality -> delivery

补充规则：

- 缺陷修复不会跳过文档阶段；默认走轻量补丁路径，先写明问题现象、复现条件、影响范围和回归风险，再实施修复。
- 分析阶段默认排除 `.venv`、`site-packages`、`node_modules` 等非项目源码目录。
- 需求存在明显歧义时，先在 PRD 中提出澄清问题；架构文档默认补充关键时序图。

### 流程控制

如果项目已经进入中后段，不需要从头再跑。

普通用户优先在宿主中使用这些恢复表达：

```text
/super-dev 继续当前流程
/super-dev 现在下一步是什么
/super-dev 恢复到前端实现与运行验证
```

恢复链真源固定为：

- `.super-dev/SESSION_BRIEF.md`
- `.super-dev/workflow-state.json`
- `.super-dev/workflow-history/latest.json`
- `.super-dev/review-state/*`
- `output/*`

维护者只在报告明确要求时，才直接使用 CLI 流程控制：

```bash
super-dev status
super-dev run --resume
super-dev review docs
super-dev review preview
```

用途：

- `status`：查看当前治理状态
- `run --resume`：继续当前暂停的流程
- `review *`：维护者同步 gate 状态，不是普通用户的日常入口

文档确认优先在宿主里完成；如果维护者需要同步 gate 状态，再进入终端：

```bash
super-dev review docs
```

如果用户对当前前端视觉不满意，需要正式发起 UI 改版，而不是直接让宿主局部改 CSS：

```bash
super-dev review ui
super-dev review ui --status revision_requested --comment "Hero 太空，品牌感不够，重做首屏"
super-dev review ui --status confirmed --comment "UI 改版已通过"
```

UI 改版的正确顺序固定为：

1. 先更新 `output/*-uiux.md`
2. 再重做前端实现
3. 重新执行 frontend runtime 与 UI review
4. 通过后再继续后续交付

如果用户认为技术方案、模块边界或接口设计不合理，需要正式发起架构返工：

```bash
super-dev review architecture
super-dev review architecture --status revision_requested --comment "服务边界过粗，接口契约需要重构"
super-dev review architecture --status confirmed --comment "架构返工已通过"
```

架构返工的正确顺序固定为：

1. 先更新 `output/*-architecture.md`
2. 再同步调整 Spec / tasks 与实现方案
3. 通过后再继续后续实施动作

如果用户认为质量、安全或交付证据仍不达标，需要正式发起质量返工：

```bash
super-dev review quality
super-dev review quality --status revision_requested --comment "质量门禁未过，仍有安全问题"
super-dev review quality --status confirmed --comment "质量返工已通过"
```

质量返工的正确顺序固定为：

1. 先修复质量 / 安全问题
2. 重新执行 quality gate，并按报告要求刷新交付证据
3. 通过后再继续交付或恢复执行

### 1.2 显式工作模式

只有当系统自动判断工作模式不准时，才在宿主里显式指定：

```text
/super-dev-work new <需求>
/super-dev-work evolve <需求>
/super-dev-work patch <缺陷描述>
/super-dev-work variant <衍生版本目标>
```

这组显式模式属于高级维护表达。普通用户优先仍然直接说需求、说“继续当前流程”、或说“现在下一步是什么”。

---

## 2. 安装与初始化

### 2.1 安装

```bash
uv tool install super-dev
```

指定版本：

```bash
uv tool install super-dev==2.4.0
```

### 2.2 Bootstrap（推荐）

```bash
mkdir my-project && cd my-project
```

这一步会显式生成：

- `.super-dev/WORKFLOW.md`

用于固定初始化规范、触发方式和阶段顺序。

### 2.3 初始化（可选，但团队项目建议）

```bash
mkdir my-project && cd my-project
super-dev init my-project --platform web --frontend react --backend node --domain saas
```

可选：在 `super-dev.yaml` 中配置企业知识增强策略：

```yaml
knowledge_allowed_domains:
  - openai.com
  - python.org
knowledge_cache_ttl_seconds: 1800
language_preferences:
  - python
  - typescript
  - rust
host_compatibility_min_score: 80
host_compatibility_min_ready_hosts: 1
host_profile_targets:
  - codex-cli
  - claude-code
  - qwen-code
host_profile_enforce_selected: true
```

推荐在项目根目录维护 `knowledge/` 目录作为团队知识资产库（已被流水线自动扫描）：

```text
knowledge/
  high-quality-engineering-playbook.md
  official-knowledge-catalog.md
  security/
    baseline.yaml
  operations/
    runbook.txt
```

建议把权威链接、业务规则、交付检查清单、故障处理手册都放入 `knowledge/`，让需求增强阶段稳定命中团队经验与官方规范。

建议按全链路结构维护深度知识库：

```text
knowledge/
  00-governance/
  product/
  design/
  architecture/
  development/
  testing/
  security/
  cicd/
  operations/
  data/
  incident/
  ai/
```

这套结构可覆盖从需求、设计、研发、测试、安全、发布、运维到复盘的完整环节，让每次需求增强都能命中对应领域知识。

如果你希望“开发类知识库完整内置”，可直接使用：

```text
knowledge/development/DEVELOPMENT_KB_MASTER_INDEX.md
```

该索引已内置前端、后端、API、数据库、性能、并发、重构、评审、工程效能、开发安全，以及UI卓越、全场景开发、知识图谱、成熟度治理、端到端开发全流程与全流程模板专题入口。

开发知识库审计可直接运行：

```bash
python scripts/audit_development_kb.py
```

```bash
python scripts/check_knowledge_gates.py --project-dir .
```

如果你希望“AI开发类知识库完整内置”，可直接使用：

```text
knowledge/ai/AI_KB_MASTER_INDEX.md
```

可运行AI知识库审计：

```bash
python scripts/audit_ai_kb.py
```

---

## 3. 指令大全（命令速查）

### 3.1 核心流水线

```text
原生 slash 宿主: /super-dev 需求描述
Codex App/Desktop: 从 / 列表选择 super-dev
Codex CLI: $super-dev
自然语言回退: super-dev: 需求描述
```

```text
原生 slash 宿主: /super-dev 需求描述
Codex App/Desktop: 从 / 列表选择 super-dev
Codex CLI: $super-dev
自然语言回退: super-dev: 需求描述
优先恢复: /super-dev 继续当前流程
高级维护: /super-dev-work / /super-dev-run / /super-dev-review
```

### 3.2 维护者：Spec 与任务闭环

下面这组 `spec / task` 命令只属于维护面。普通用户仍然应该在宿主里通过 `/super-dev`、`super-dev:`、`继续当前流程` 继续主流程。

```bash
super-dev spec init
super-dev spec show <change_id>
super-dev spec propose <change_id> --title "标题" --description "描述"
super-dev spec propose <change_id> --title "标题" --description "描述" --no-scaffold
super-dev spec add-req <change_id> <spec_name> <req_name> "需求描述"
super-dev spec scaffold <change_id>
super-dev spec validate
super-dev spec quality <change_id>
super-dev spec quality <change_id> --json
super-dev spec archive <change_id>

super-dev task list
super-dev task status <change_id>
```

#### Spec 质量评分与整改计划

`spec quality` 会输出六维评分（proposal/spec/plan/tasks/checklist/validation），并自动给出 `action_plan`（带优先级和可执行命令）。

```bash
super-dev spec quality add-billing
super-dev spec quality add-billing --json > output/add-billing-spec-quality.json
```

建议在 CI 中把该命令作为前置门禁：

```bash
super-dev spec quality add-billing --json > /tmp/spec-quality.json
python - <<'PY'
import json,sys
p=json.load(open('/tmp/spec-quality.json'))
ok = p.get('score', 0) >= 75
print('spec_quality_score=', p.get('score'), 'ok=', ok)
sys.exit(0 if ok else 1)
PY
```

### 3.3 质量与审查

质量与审查属于维护面。普通用户优先在宿主里继续流程；维护者只在报告明确要求时，才回终端刷新 `quality / review / release` 证据。

### 3.4 部署与交付

`release proof-pack` 与 `release readiness` 继续存在，但属于维护者交付闭环，不应作为普通用户的第一层命令心智。

`release proof-pack` 与 `release readiness` 会自动读取当前有效 change 的 `spec quality` 结果，把 proposal/spec/plan/tasks/checklist/validation 六维评分并入统一发布评分面板。
它们现在还会纳入范围覆盖率结果，用来区分“流程完成”和“PRD 全量范围完成”。

如果你需要确认宿主是否真的完成了首轮 research、三文档落盘与确认门停顿，优先使用宿主恢复卡与 `doctor / detect` 报告；只有维护者在补真人验收证据时，才进入 `integrate validate` 维护链。

如果你发现系统提示“流程完成”，但文档或差距审计里仍列出很多未实现项，请重新查看 `product-audit`、`release proof-pack`、`release readiness` 的范围覆盖率与高优先级缺口。

这样你就能区分：
- `Pipeline Completed`
- `Delivery Ready`
- `Scope Coverage`

### 3.5 设计与专家

```bash
super-dev design list
super-dev design recommend
super-dev design apply <slug>
```

说明：
- `design` 是 UI/UX 阶段的高级增强能力，用于参考优秀设计灵感、推荐合适方向并把设计偏好写回配置。
- 它用于增强 `uiux.md` 质量，不替代主流水线；真正的开发仍应回到宿主里继续 `research -> docs -> spec -> frontend -> backend -> quality -> delivery`。

### 3.6 集成与 Skill

这组能力仍然属于维护面：

- `integrate`：宿主规则与兼容性维护
- `skill`：宿主 Skill 安装与修复

普通用户不要先学这组命令，维护者只在宿主接入、兼容性修复或验收时再进入。

---

## 4. 0-1 场景：从零创建项目

> 适用于“还没有代码仓库，只有业务需求”的情况。

### 4.1 最短路径（推荐）

```bash
mkdir new-app && cd new-app
super-dev
```

然后回到宿主里输入：

```text
/super-dev 做一个 B2B CRM，支持线索管理、客户管理、销售漏斗、权限管理
```

### 4.2 产物检查

运行后重点看这些文件：

- `output/*-research.md`：需求增强报告（联网+知识）
- `output/*-prd.md`：产品需求文档
- `output/*-architecture.md`：架构文档
- `output/*-uiux.md`：UI/UX 文档
- `output/*-execution-plan.md`：执行路线图
- `.super-dev/changes/*/tasks.md`：Spec 任务清单
- `output/*-task-execution.md`：任务执行与自动修复记录
- `output/*-redteam.md`：红队审查报告
- `output/*-quality-gate.md`：质量门禁报告
- `output/delivery/*-delivery-manifest.json`：交付清单
- `output/delivery/*-delivery-report.md`：交付报告

### 4.3 开发推进建议

1. 先让前端实施蓝图跑起来，做演示确认需求。
2. 再按 `tasks.md` 实现后端与数据层。
3. 最后修复红队和质量门禁阻断项。

### 4.4 常见 0-1 命令组合

```bash
super-dev
```

然后在宿主里继续：

```text
/super-dev 做一个内容平台，支持发布、审核、推荐
继续当前流程
现在下一步是什么
```

---

## 5. 1-N+1 场景：现有项目增量迭代（含 1-1+N）

> 适用于“已有线上/在研项目，需要继续增加能力”的情况。

### 5.1 场景定义

- `1-1+N`：基于一个已有主项目，持续增加 N 个能力模块。
- `1-N+1`：多个子域迭代到下一阶段（本质仍是增量迭代）。

在 Super Dev 中，这些都归类为增量开发路径，核心是：
- 先分析现状
- 再建立 Spec 变更
- 最后按任务闭环推进

### 5.2 标准流程

#### 步骤 1：初始化 Spec（仅首次）

```bash
super-dev spec init
```

#### 步骤 2：创建增量提案

```bash
super-dev spec propose add-billing \
  --title "新增计费中心" \
  --description "支持套餐、订阅、账单、发票、支付回调"
```

#### 步骤 4：补充关键需求

```bash
super-dev spec add-req add-billing billing subscription "系统 SHALL 支持订阅创建和续费"
super-dev spec add-req add-billing billing invoice "系统 SHALL 生成可追溯账单"
super-dev spec add-req add-billing billing webhook "系统 SHALL 幂等处理支付回调"
```

#### 步骤 5：维护者核对任务收敛状态

```bash
super-dev task status add-billing
```

#### 步骤 6：维护者刷新质量门禁与交付证据

```bash
super-dev quality --type all
```

### 5.3 迭代批次建议

对于 `1-1+N`，建议按“单批次单变更”推进：

1. 一个 `change_id` 只做一类功能（例如 billing）。
2. 每个变更都独立过红队与质量门禁。
3. 通过后再做下一个变更（reporting / audit）。

---

## 6. 商业级交付标准（必过）

发布前必须满足：

1. 红队审查无阻断（critical 为 0）。
2. 质量门禁总分 >= 80。
3. Spec 任务完成度达到可交付标准（建议全部完成）。
4. CI/CD 五平台配置已生成并可按目标平台落地。
5. 交付包状态为 `ready`。

建议执行：

```bash
./scripts/preflight.sh
```

如果本地环境限制可用：

```bash
./scripts/preflight.sh --allow-dirty --skip-benchmark --skip-package
```

---

## 7. 多工具安装与使用

### 7.1 安装向导（默认，支持多选）

```bash
./install.sh
super-dev install
```

说明：

- 默认进入交互式安装引导
- 可多选宿主（CLI/IDE）
- 自动执行 onboard + doctor

### 7.2 一键安装全部目标（非交互）

```bash
./install.sh --targets all
```

### 7.3 仅安装规则，不装 skill

```bash
./install.sh --targets all --no-skill
```

### 7.4 单平台安装

```bash
super-dev integrate setup --target qoder --force
```

### 7.5 自动探测宿主并接入（推荐）

下面这一组属于维护者接入/修复链，不是普通用户日常开发入口。

```bash
super-dev detect --json
super-dev detect --auto --save-profile
super-dev onboard --auto --yes --force
super-dev doctor --auto --repair --force
```

`detect` 会默认生成：

- `output/<project>-host-compatibility.json`
- `output/<project>-host-compatibility.md`
- `output/host-compatibility-history/*.json`
- `output/host-compatibility-history/*.md`

当使用 `--save-profile` 时，会自动更新 `super-dev.yaml`：

- `host_profile_targets`
- `host_profile_enforce_selected=true`

流水线每次运行会产出契约审计：

- `output/*-pipeline-contract.json`
- `output/*-pipeline-contract.md`

企业策略建议：

2. 先执行 `super-dev detect --auto --save-profile` 产出兼容报告。
3. 按团队实际宿主填写 `required_hosts`。
4. 需要强校验时，再启用 `enforce_required_hosts_ready=true`，并设置 `min_required_host_score`。

支持目标：

- CLI: `claude-code`, `codex-cli`, `opencode`, `droid-cli`, `gemini-cli`, `kiro-cli`, `cursor-cli`, `copilot-cli`, `qoder-cli`, `codebuddy-cli`, `kimi-code`, `qwen-code`
- IDE: `antigravity`, `cursor`, `windsurf`, `kiro`, `trae`, `trae-cn`, `codebuddy`, `codebuddy-cn`, `qoder`
- Desktop assistants: `claude`, `codex`, `workbuddy`, `trae-solo`, `trae-solocn`

---

## 8. 常见问题

### Q1: 我只想用一句话驱动，能否不用 pipeline 参数？

可以。默认推荐就是：

```bash
在宿主里输入 `/super-dev 需求`
```

### Q2: 如何查看当前变更进度？

```bash
super-dev task status <change_id>
super-dev run --resume
```

### Q3: 质量门禁没过怎么办？

先看：

- `output/*-redteam.md`
- `output/*-quality-gate.md`
- `output/*-task-execution.md`

按报告里的 failed/critical 项逐条修复，再重新执行：

```bash
在宿主里继续当前 change 的修复与验证
重新生成质量门禁报告
```

### Q4: 如何准备对外发布？

这部分只属于维护者。不要把它当成普通用户的“下一步”。

正式发版入口统一看：

- [`docs/PUBLISHING.md`](/Users/weiyou/Documents/kaifa/super-dev/docs/PUBLISHING.md)
- [`docs/RELEASE_RUNBOOK.md`](/Users/weiyou/Documents/kaifa/super-dev/docs/RELEASE_RUNBOOK.md)

最短判断标准：

```bash
./scripts/preflight.sh
```

只有在干净工作树上、不带 `--allow-dirty` 的正式预检通过后，才进入发布动作。

---

## 9. 推荐日常操作模板

### 9.1 新项目模板

```bash
在宿主里输入 `/super-dev 需求`
继续当前流程
现在下一步是什么
```

### 9.2 增量迭代模板

```bash
/super-dev 在当前项目中新增一个能力
/super-dev baseline 确认，可以继续当前流程
继续当前流程
```

---

## 10. 相关文档

- 快速开始：`docs/QUICKSTART.md`
- 集成指南：`docs/INTEGRATION_GUIDE.md`
- 维护者发布入口：`docs/PUBLISHING.md`
- 维护者发布作战手册：`docs/RELEASE_RUNBOOK.md`
