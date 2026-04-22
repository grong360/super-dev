# Super Dev 宿主使用指南（2.4.0）

## 目标

这份文档只回答一件事：

- 安装完 `Super Dev` 之后，在不同宿主里到底怎么用
- 哪些宿主可以直接 `/super-dev`
- 哪些宿主不能 `/super-dev`，应改用 Skill / 规则 / AGENTS

请始终记住：

- 宿主负责搜索、写代码、跑命令、改文件
- `Super Dev` 负责图纸、流程、设计约束、质量门和交付标准
- `Super Dev` 更像宿主教练系统，不是再给宿主额外挂一层命令壳或低层接入面

当前默认采用统一宿主矩阵。
当前公开矩阵按 `CLI / IDE / 桌面助手` 分组。
默认采用项目优先注入：先写项目级接入面，再按需补齐用户 / 全局接入面。
自动检测优先基于命令名、常见安装路径、Windows 注册信息与常见 shim 目录；若用户装在自定义目录，可再配合 `SUPER_DEV_HOST_PATH_<HOST>` 显式指定安装路径。

---

## 如果你只想最快用起来

不要先读完整手册，直接走这个顺序：

1. 在项目根目录执行 `super-dev`
2. 在安装器里选择目标宿主
3. 如果安装器提示需要重启宿主，先重启
4. 先打开 `output/maintenance/host-onboard-smoke-*.md`
5. 看 `标准流第一句` / `比赛流第一句`、`接入后先验`、`框架焦点`
6. 回到宿主里输入第一句
7. 如果是已有项目，先让宿主按 `baseline -> delta research -> 三文档` 开始，不要先回终端手工跳阶段
8. 成功标志只有两个：
   - 第一轮回复明确说当前阶段是 `research`
   - 三份核心文档完成后会停下来等你确认

如果没生效，再回来看下面的宿主矩阵和单宿主说明。

如果你已经接入过，但不知道现在该先做什么，不要先找终端流程命令，优先回到宿主里说：

- `继续当前流程`
- `现在下一步是什么`

普通用户优先只记住 3 类表达：

- `/super-dev <goal>`
- `/super-dev-seeai <goal>`
- `继续当前流程` / `现在下一步是什么`

不支持 `/` 的宿主统一回退为：

- `super-dev: <goal>`
- `super-dev-seeai: <goal>`
- `继续当前流程` / `现在下一步是什么`

`/super-dev-work`、`/super-dev-run`、`/super-dev-review` 这类高级流程口令仍保留给维护/治理场景，但不应当成普通用户的第一层入口。

工作模式固定为：

- `new`
- `evolve`
- `variant`
- `patch`
- `resume`

其中最重要的规则只有三条：

1. `evolve / variant / patch` 必须先 baseline，先分析现有项目的功能、架构、代码和 UI，再进入差量文档。
2. `resume` 是默认场景，恢复优先级高于重新开题。
3. 普通开发尽量留在宿主里，不要把 `run / review / integrate / release` 当成日常主入口。

### 真实开发场景

| 场景 | 正确动作 |
|------|----------|
| 宿主窗口关了，重新打开后继续 | 回到宿主里说 `继续当前流程` |
| 晚上下班了，第二天接着做 | 回到宿主里说 `继续当前流程` |
| 正在等三文档确认，回来继续改 | 回到宿主里继续围绕 PRD / Architecture / UIUX 补充 |
| 正在等前端预览确认，回来继续改页面 | 回到宿主里继续前端返工 |
| 不知道系统现在卡在什么地方 | 回到宿主里说 `现在下一步是什么` |
| 刚完成文档 / 预览 / 返工确认 | 回到宿主里明确说 `文档确认，可以继续`、`前端预览确认，可以继续` 等 |

恢复链的真源文件：

- `.super-dev/SESSION_BRIEF.md`
- `.super-dev/workflow-state.json`

如果宿主恢复后没有按 Super Dev 流程继续，而是滑回普通聊天，优先重新复制恢复卡里的“宿主第一句”，继续当前流程。

### 这份矩阵怎么用

- 静态表格只负责告诉你“这个宿主通常怎么触发”
- 真正的安装后判断，以 `output/maintenance/host-onboard-smoke-*.md` 为准
- 因为只有 smoke guide 会告诉你这个项目当前的：
  - `标准流第一句`
  - `比赛流第一句`
  - `框架焦点（Framework Coaching Focus）`
  - `官方工作流检查`
  - `标准流可直接开工 / SEEAI 可直接开工`

---

## 先看矩阵

认证等级说明：

- `Certified`：已按宿主真实能力完成专门适配，当前优先推荐。
- `Compatible`：接入链路完整，可以稳定使用，但还缺更长期的运行级认证。
- `Experimental`：已接入并可试用，但仍需更多真实项目验证。

### CLI 宿主（12）

| 宿主 | 认证等级 | 是否支持 `/super-dev` | 正确触发方式 | 接入后是否需要重启 |
| --- | --- | --- | --- | --- |
| Claude Code | Certified | 支持 | 在 Claude Code 会话中输入 `/super-dev 你的需求` | 否 |
| Codex CLI | Certified | 不支持项目级 slash | 在项目目录完成接入后，在新的 Codex CLI 会话里优先输入 `$super-dev`，回退入口是 `super-dev: 你的需求` | 是 |
| OpenCode | Experimental | 支持 | 在 OpenCode 会话中输入 `/super-dev 你的需求` | 否 |
| Droid CLI | Compatible | 支持 | 在 Droid 当前项目会话中优先输入 `/super-dev 你的需求`；比赛模式 `/super-dev-seeai`；继续当前流程时可回退 `super-dev: 你的需求` | 否 |
| Gemini CLI | Compatible | 支持 | 在 Gemini CLI 会话中输入 `/super-dev 你的需求` | 否 |
| Kiro CLI | Compatible | 支持 | 重开 Kiro CLI 后优先输入 `/super-dev 你的需求`；自然语言 `super-dev:` 为回退入口 | 是 |
| Cursor CLI | Compatible | 不支持项目级 `/super-dev` | 在 Cursor CLI 会话中输入 `super-dev: 你的需求`；若规则未刷新，再重开同一项目会话继续流程 | 否 |
| Copilot CLI | Compatible | 不支持项目级 `/super-dev` | 在 Copilot CLI 会话中输入 `super-dev: 你的需求` | 否 |
| Qoder CLI | Compatible | 支持 | 在 Qoder CLI 会话中输入 `/super-dev 你的需求` | 否 |
| CodeBuddy CLI | Compatible | 支持 | 在 CodeBuddy CLI 会话中输入 `/super-dev 你的需求` | 否 |
| Kimi Code | Compatible | 不支持项目级 `/super-dev` | 在 Kimi Code 会话中优先输入 `super-dev: 你的需求`；显式入口可用 `/skill:super-dev 你的需求` | 是 |
| Qwen Code | Compatible | 支持 | 在 Qwen Code 会话中输入 `/super-dev 你的需求` | 否 |

### IDE 宿主（9）

| 宿主 | 认证等级 | 是否支持 `/super-dev` | 正确触发方式 | 接入后是否需要重启 |
| --- | --- | --- | --- | --- |
| Antigravity | Experimental | 支持 | 在 Antigravity Agent Chat 中输入 `/super-dev 你的需求` | 是 |
| Cursor | Experimental | 支持 | 在 Cursor Agent Chat 中输入 `/super-dev 你的需求` | 否 |
| Windsurf | Experimental | 支持 | 在 Agent Chat 中输入 `/super-dev 你的需求` | 否 |
| Kiro | Experimental | 支持 | 在 Kiro IDE Agent Chat 中输入 `/super-dev 你的需求` | 是 |
| Trae | Compatible | 不支持 | 在 Trae Agent Chat 中输入 `super-dev: 你的需求` | 是 |
| TraeCN | Compatible | 不支持 | 在 TraeCN 工作区中输入 `super-dev: 你的需求` | 是 |
| CodeBuddy | Experimental | 支持 | 在 CodeBuddy 的 Agent Chat 中输入 `/super-dev 你的需求` | 否 |
| CodeBuddyCN | Experimental | 支持 | 在 Agent Chat 中输入 `/super-dev 你的需求` | 否 |
| Qoder | Experimental | 支持 | 在 Qoder IDE Agent Chat 中输入 `/super-dev 你的需求` | 否 |

### 桌面助手（5）

| 宿主 | 认证等级 | 是否支持 `/super-dev` | 正确触发方式 | 接入后是否需要重启 |
| --- | --- | --- | --- | --- |
| Claude | Compatible | 不支持 | 在 Claude Desktop 的 Project / Instructions / Knowledge / extensions 场景里输入 `super-dev: 你的需求` | 是 |
| Codex | Certified | App/Desktop 支持技能入口 | 在 Codex App/Desktop 的 `/` 列表里选择 `super-dev`；CLI 入口另见 `Codex CLI` | 是 |
| WorkBuddy | Experimental | 不支持 | 在 WorkBuddy 当前任务会话中输入 `super-dev: 你的需求` | 是 |
| Trae SOLO | Compatible | 支持 | 在 Trae SOLO workspace 中优先输入 `/super-dev 你的需求` | 是 |
| Trae SOLOCN | Compatible | 不支持项目级 `/super-dev` | 在 Trae SOLOCN 工作区中输入 `super-dev: 你的需求` | 是 |

### 最简判断

1. 如果你的宿主在表格里标记为“支持”，直接用 `/super-dev 你的需求`。
2. 优先选择 `Certified` 宿主，其次是 `Compatible`。
3. 如果是 `Codex CLI`，不要把 `/super-dev` 理解成项目自定义 slash 文件；App/Desktop 优先从 `/` 列表选择 `super-dev`，CLI 优先用 `$super-dev`，`super-dev: 你的需求` 作为自然语言回退入口。
4. 如果是 `Codex` 桌面助手，优先从 `/` 列表选择 `super-dev`，不要把它当成 CLI 终端入口。
5. 如果是 `Trae` 或 `TraeCN`，不要试 `/super-dev`，直接在当前 Agent Chat / 工作区输入 `super-dev: 你的需求`；如果是 `Trae SOLO`，优先使用 `/super-dev`；如果是 `Trae SOLOCN`，优先使用 `super-dev: 你的需求`。

### 安装后先看这两句

- 标准项目先看宿主给出的 `标准流第一句`，直接复制进入当前项目流程。
- 比赛模式先看宿主给出的 `比赛流第一句`，不要自己猜 `/super-dev-seeai`、`super-dev-seeai:` 还是宿主内建 Skill 入口。
- 安装完成后先打开 `output/maintenance/host-onboard-smoke-*.md`，按 smoke guide 做首轮验收，不要只看终端里一闪而过的提示。
- 终端在安装完成后就该退场。真正开发回到宿主里，不要继续停留在终端维护命令里铺背景。
- 如果当前项目已经冻结了 `framework playbook`，smoke guide 会直接告诉你 `框架焦点（Framework Coaching Focus）`、必验场景和交付证据，不需要自己从 UI 合同里翻。
- UI 不是最后再补美化。截图级视觉门会正式卡掉过平、过空、模板味太重的页面，所以第一轮 UI 方案就要追求更强的视觉方向。
- `doctor / detect / validate` 现在还会直接告诉你：
  - 这个宿主是否已经 `标准流可直接开工`
  - 这个宿主是否已经 `SEEAI 比赛模式可直接开工`
  - 如果还没 ready，宿主自己的第一步动作是什么

下面的单宿主说明保留为补充参考；如果某个宿主不在上面的 canonical matrix 里，不把它当作新的公开主入口。

---

## 总体原则

无论宿主是哪一种，Super Dev 的目标都一样：

1. 先研究同类产品
2. 再生成 `research / PRD / architecture / UIUX`
3. 再生成 Spec 与 `tasks.md`
4. 最后才进入编码、质量门禁与交付

如果宿主支持联网能力，优先由宿主自己完成 research 阶段。

如果你不确定该选哪个宿主，直接运行：

```bash
super-dev
```

安装器会自动检测当前机器上的宿主，并给出推荐接入路径。

---

## 安装后通用检查

先在项目根目录执行：

```bash
super-dev
```

安装器会根据机器环境自动给出推荐宿主；`onboard --host` 留作内部维护与精确修复场景，不再是普通用户主路径。

如果你只是普通使用，接入完成后直接回宿主开始主流程。下面这些动作只在维护者排障、真人验收或治理收尾时才需要。

维护者通常只做两件事：

1. 先重新运行 `super-dev`，让安装器先给出当前宿主与仓库的修复建议
2. 按报告建议回到宿主里继续，或在必要时记录真人验收结论

`doctor` 现在会直接告诉你：

1. 该宿主的主入口
2. 是否应该使用 `/super-dev`
3. 是否需要重启宿主
4. 接入后还要做什么
5. 如何做 Smoke 验收

如果你在做宿主级 smoke / 真人验收，维护面会继续提供：

1. 标准验收语句
2. 宿主级验收步骤
3. 什么结果才算接入真正生效
4. 如何把真人验收状态写回 `.super-dev/review-state/host-runtime-validation.json`

换句话说，普通用户不需要先学会 `integrate smoke / validate` 这些命令；只有维护者在需要留下正式验收证据时，才进入这条维护链。

真人验收状态最终会写入：

- `.super-dev/review-state/host-runtime-validation.json`
- `output/maintenance/host-onboard-smoke-*.json`
- `output/maintenance/host-onboard-smoke-*.md`

如果你是在做清理或迁移，先用：

```bash
super-dev uninstall --dry-run
```

然后再看：

- `output/maintenance/host-cleanup-*.json`
- `output/maintenance/host-cleanup-*.md`

推荐把它理解成 cleanup audit：

- 先用 `super-dev uninstall --dry-run` 看会删什么
- 确认无误后再正式清理
- 如果要留档，保留 uninstall 预演报告和最近一次 host-onboard-smoke 报告

另外，维护诊断报告会显示该宿主的前置条件项，例如：

- 是否需要先在宿主内完成鉴权
- 是否需要关闭旧会话后重开宿主
- 是否必须绑定到目标项目/工作区

---

## 每个宿主怎么用


#### 1. Claude Code

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Claude Code 当前会话后，直接在同一会话里触发。

触发命令：
```text
/super-dev 你的需求
```

自然语言回退：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 推荐作为首选 CLI 宿主。
2. 维护者如需核对接入面，可执行 `super-dev doctor --host claude-code`，确认项目根 `CLAUDE.md`、项目级 `.claude/CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户级 skills 与 agents 一起生效。
3. Claude Code 当前按官方 `CLAUDE.md + settings + project/user skills + subagents` 模型对齐；`.claude/commands/` 仅作为兼容增强面保留，不再当主协议面。
4. 如需增强层，Super Dev 还会补齐 `.claude-plugin/marketplace.json` 与 `plugins/super-dev-claude/.claude-plugin/plugin.json`。
5. 进入已有项目时，不要先在终端里手工跑阶段命令；优先在宿主里让它先做 baseline。
6. 关闭窗口或第二天回来时，优先直接在宿主里说“继续当前流程”。

#### Droid CLI

安装：
```bash
super-dev
```

触发位置：
在目标项目目录启动 Droid CLI 当前会话后，优先在同一 session 里触发。

触发命令：
```text
super-dev: 你的需求
```

回退入口：
```text
super-dev: 你的需求
```

比赛模式：
```text
/super-dev-seeai 比赛需求
```

恢复已有流程时：
```bash
droid exec --session-id <id> "continue with next steps"
```

接入后是否需要重启：否

补充说明：
1. Droid CLI 的核心接入面是 Factory 官方 `AGENTS.md + .factory/rules + .factory/skills`；`.factory/commands/` 仅作为兼容增强面补齐。
2. `/super-dev-seeai` 是比赛模式首选入口；slash 刷新慢时，再回退到 `super-dev-seeai:`。
3. 已有项目优先保持同一 Droid session，不要重新开题，这样 baseline / resume gate 才能连续。

#### 2. CodeBuddy CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 CodeBuddy CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前按 `CODEBUDDY.md` + `.codebuddy/commands/` + `.codebuddy/skills/` 接入。
2. 用户级会同步安装 `~/.codebuddy/CODEBUDDY.md` + `~/.codebuddy/commands/` + `~/.codebuddy/skills/`。
3. 如果会话已提前打开，建议重新加载项目规则后再试。

#### 3. CodeBuddy

安装：
```bash
super-dev
```

触发位置：
打开 CodeBuddy 的 Agent Chat，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 建议在项目级 Agent Chat 中使用，不要脱离项目上下文。
2. 先让宿主完成 research，再继续文档和编码。
3. 当前按 `CODEBUDDY.md` + `.codebuddy/rules/super-dev/RULE.mdc` + `.codebuddy/commands/` + `.codebuddy/agents/` + `.codebuddy/skills/` 接入。


#### 4. Cursor CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Cursor CLI 当前会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 适合终端内连续执行研究、文档和编码。
2. 官方项目上下文面是项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只继续作为兼容上下文，不再当默认主协议面。
3. 若命令列表未刷新，可重开一次 Cursor CLI 会话；恢复已有流程时优先使用 Cursor CLI 自身的会话连续性。

#### 5. Cursor IDE

安装：
```bash
super-dev
```

触发位置：
打开 Cursor 的 Agent Chat，并确保当前工作区就是目标项目。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 建议固定在同一个 Agent Chat 会话里完成整条流水线。
2. 官方项目上下文面是项目根 `AGENTS.md`、`.cursor/rules/` 与可选 `.cursor/commands/`（beta）；根 `CLAUDE.md` 只继续作为兼容上下文，Super Dev 默认把 `AGENTS.md` 作为共享项目 memory 面。
3. 如果项目规则没加载，先重新打开工作区或重新发起聊天。

#### 6. Antigravity

安装：
```bash
super-dev
```

触发位置：
打开 Antigravity 的 Agent Chat / Prompt 面板，并确保当前工作区就是目标项目。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Antigravity 当前按 `GEMINI.md + custom commands` 模式接入，`.agent/workflows` 继续作为推荐增强面。
2. 接入会写入项目级 `GEMINI.md`、`.gemini/commands/super-dev.toml`、`.agent/workflows/super-dev.md`。
3. 默认只写项目级 `GEMINI.md` 与项目命令面；用户级 `~/.gemini/GEMINI.md` 与 `~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时写入，`~/.gemini/skills/` 继续只作为兼容增强层。
4. 完成接入后请重开 Antigravity 或至少新开一个 Agent Chat，再输入 `/super-dev 你的需求`。

#### 7. Gemini CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Gemini CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 官方主面已经收口到 `GEMINI.md + settings + custom commands`；项目内优先检查 `GEMINI.md`、可选 `.gemini/settings.json` 和 `.gemini/commands/*.toml`。
2. `/super-dev` 是 Super Dev 注入后的自定义命令面，不是 Gemini CLI 自带内建命令；若命令未刷新，优先重开 Gemini CLI 会话。
3. `~/.gemini/skills/` 只作为兼容增强面保留，不再当默认主协议面。
4. 优先在同一会话中完成 research -> 三文档 -> 用户确认 -> Spec -> 前端运行验证 -> 后端/交付；若宿主支持联网，先让它完成同类产品研究。

#### 8. Kiro CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Kiro CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Kiro CLI 当前优先使用宿主已暴露的 `/super-dev` 入口；若当前会话只接受自然语言，再回退到 `super-dev: 你的需求`。
2. 官方接入面是 `AGENTS.md` + `.kiro/steering/super-dev.md` + `.kiro/skills/super-dev/SKILL.md`；全局增强面是 `~/.kiro/steering/super-dev.md`、`~/.kiro/steering/AGENTS.md` 与 `~/.kiro/skills/super-dev/SKILL.md`。
3. 如果 steering 或 skills 未刷新，重新进入项目目录后重开 Kiro CLI 会话。

#### 9. Kiro IDE

安装：
```bash
super-dev
```

触发位置：
打开 Kiro IDE 的 Agent Chat / AI 面板，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Kiro IDE 当前优先使用宿主已暴露的 `/super-dev` 入口；若当前会话只接受自然语言，再回退到 `super-dev: 你的需求`。
2. 接入会写入项目级 `AGENTS.md`、`.kiro/steering/super-dev.md`、`.kiro/skills/super-dev/SKILL.md`，并补充可选全局 steering `~/.kiro/steering/super-dev.md`、`~/.kiro/steering/AGENTS.md` 与 `~/.kiro/skills/super-dev/SKILL.md`。
3. 如果 steering 或 skills 未加载，先重开项目窗口或新开一个 Agent Chat。

#### 10. OpenCode

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 OpenCode 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 按 CLI slash 模式使用。
2. 若你使用全局命令目录，也建议保留项目级接入文件。

#### 11. Qoder CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Qoder CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 适合命令行流水线开发。
2. 若 slash 未生效，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 已生成，并检查 `.qoder/rules/` 目录是否存在。
3. 官方核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/`、`.qoder/skills/` 与 `~/.qoder/AGENTS.md` / `~/.qoder/commands/` / `~/.qoder/skills/`；`.qoder/agents/` 继续只作为增强面。

#### 12. Qoder IDE

安装：
```bash
super-dev
```

触发位置：
打开 Qoder IDE 的 Agent Chat，在当前项目内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. Qoder IDE 当前优先使用项目级 `AGENTS.md + commands + rules + skills` 模式。
2. 若新增命令未出现，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 与 `.qoder/rules/super-dev.md` 已生成，再重新打开项目或新开一个 Agent Chat。
3. 官方核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/`、`.qoder/skills/` 与 `~/.qoder/AGENTS.md` / `~/.qoder/commands/` / `~/.qoder/skills/`；`.qoder/agents/` 继续只作为增强面。

#### 13. Windsurf

安装：
```bash
super-dev
```

触发位置：
打开 Windsurf 的 Agent Chat / Workflow 入口，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前按 `AGENTS.md + rules + workflow + skills` 模式适配。
2. 更适合在同一个 Workflow 里连续完成研究、文档、Spec 和编码。
3. 官方文档已公开 `AGENTS.md`、`.windsurf/workflows/` 与 `.windsurf/skills/`；仓库继续把 `.windsurf/rules/` 保留为项目约束面。

#### 14. Codex

安装：
```bash
super-dev
```

触发位置：
在项目目录完成接入后，重启 `codex`，然后在新的 Codex 会话里触发。

触发命令：
```text
Codex App/Desktop: 在 `/` 列表里选择 super-dev
Codex CLI: $super-dev
回退入口: super-dev: 你的需求
```

接入后是否需要重启：是

补充说明：
1. Codex App/Desktop 优先从 `/` 列表里直接选择 `super-dev`；这是已启用 Skill 的官方入口，不是项目级自定义 slash 文件。
2. Codex CLI 优先显式输入 `$super-dev`。
3. 如果当前已经在自然语言上下文里继续流程，也可以直接输入 `super-dev: 你的需求`。
4. 默认基础接入面是项目 `AGENTS.md`、项目 `.agents/skills/super-dev/SKILL.md` 和官方用户级 Skill `~/.agents/skills/super-dev/SKILL.md`；全局 `CODEX_HOME/AGENTS.md`（默认 `~/.codex/AGENTS.md`）仅在显式 `--with-user-surfaces` 时写入。
5. 同时会额外生成可选的 repo plugin 增强层：`.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json`，让 Codex App/Desktop 在 AGENTS + Skills 之外还能看到更完整的本地 plugin 面。
6. 历史安装会在升级时自动迁移到统一的 `super-dev` 命名。
7. 如果旧会话没加载新 Skill，重启 `codex` 再试。
8. 无论使用 `/super-dev`、`$super-dev` 还是 `super-dev:`，都必须进入同一条 Super Dev 流程；长流程里继续修改、补充、确认或恢复时，优先沿用当前入口面。

#### Kimi Code

安装：
```bash
super-dev
```

触发位置：
在目标项目目录启动 Kimi Code 当前会话后直接触发。

触发命令：
```text
super-dev: 你的需求
```
显式入口：
```text
/skill:super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. 默认仍推荐 `super-dev: 你的需求`，因为它和其他宿主的统一心智最一致。
2. 如果你需要显式入口，Kimi Code 已适配 `/skill:super-dev`；需要更强结构化流程时才考虑 `/flow:super-dev`。
3. 当前集成主链按 `AGENTS.md + 显式 /skill:/flow: 入口 + native session resume` 建模；`.kimi/skills/`、`~/.kimi/skills/` 与 `.kimi/AGENTS.md` 继续只作为当前增强面。
4. 恢复时优先使用 `kimi --continue`、`kimi --session <id>`、运行中的 `/sessions` / `/resume` 或当前会话里的“继续当前流程”，不要重新开题。

#### 15. Trae IDE

安装：
```bash
super-dev
```

触发位置：
打开 Trae IDE 的 Agent Chat，在当前项目上下文内直接触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：是

补充说明：
1. 不要输入 `/super-dev`。
2. 默认只写项目级 `.trae/project_rules.md`、`.trae/rules.md`；用户级 `~/.trae/user_rules.md`、`~/.trae/rules.md` 仅在显式 `--with-user-surfaces` 时写入；如果检测到兼容技能目录，也会增强安装 `~/.trae/skills/super-dev/SKILL.md`。
3. 完成接入后建议重开 Trae 或至少新开一个 Agent Chat，使规则生效；如果兼容 Skill 已安装，也会一起生效。
4. 随后按 `output/*` 与 `.super-dev/changes/*/tasks.md` 推进开发。

#### Trae SOLO

安装：
```bash
super-dev
```

触发位置：
打开 Trae SOLO Desktop / Web 当前 workspace，并确认工作区就是目标项目。

触发命令：
```text
/super-dev 你的需求
```
比赛模式：
```text
/super-dev-seeai 你的比赛需求
```

接入后是否需要重启：是

补充说明：
1. Trae SOLO 当前优先走 `AGENTS.md + .trae/rules/ + .trae/commands/ + .trae/skills/` 这套工作区接入模型，而不是只靠自然语言热启动。
2. slash 未刷新时回退到 `super-dev: 你的需求`，但不要把它当成默认路径。
3. 恢复时优先沿用当前 workspace continuity，不要为了继续流程重新开一个工作区或会话。

#### Trae SOLOCN

安装：
```bash
super-dev
```

触发位置：
打开 Trae SOLOCN 当前工作区，并确认它就是目标项目。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：是

补充说明：
1. 当前推荐模型是 `.trae/rules/ + .trae/skills/ + ~/.trae-cn/skills/`，主入口仍然是 `super-dev:`。
2. Trae SOLOCN 自带的 `/plan`、`/spec`、MTC / Code 双模式应该和 Super Dev 协同使用，而不是两套流程相互覆盖。
3. 恢复时优先续跑当前工作区和当前任务，不要重新做 baseline。

#### 16. VS Code Copilot

安装：
```bash
super-dev
```

触发位置：
打开 VS Code 的 Copilot Chat，并确保当前工作区就是目标项目。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. VS Code Copilot 当前按 `.github/copilot-instructions.md` + `AGENTS.md` 工作。
2. 不使用 `/super-dev`，直接在 Copilot Chat 输入 `super-dev:` 或 `super-dev：`。
3. 如果当前聊天没有重新加载规则，先重开工作区或新开一个 Copilot Chat。

#### 17. Droid CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Droid CLI 当前会话后触发。

触发命令：
```text
/super-dev 你的需求
```
比赛模式：
```text
/super-dev-seeai 比赛需求
```
自然语言回退：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. Droid CLI 当前按 Factory 官方 `AGENTS.md + .factory/rules + .factory/skills` 工作；`.factory/commands/` 继续作为兼容增强面保留。
2. 安装器会写入项目级 `AGENTS.md`、`.factory/rules/super-dev.md`、`.factory/skills/super-dev/`、`.factory/skills/super-dev-seeai/`，并补齐兼容 `.factory/commands/super-dev*.md`。
3. 默认只写项目级 `.factory/*`；用户级 `~/.factory/AGENTS.md`、`~/.factory/commands/` 与 `~/.factory/skills/` 仅在显式 `--with-user-surfaces` 时补齐，用于跨项目复用同一套宿主协议面。
4. 恢复已有流程时优先保留同一个 Droid session；只有需要 headless 续跑时，再用 `droid exec --session-id <id> "continue with next steps"`。
5. SEEAI 模式下仍保留 compact 文档确认门，随后直接进入一体化比赛冲刺与最终 polish。
