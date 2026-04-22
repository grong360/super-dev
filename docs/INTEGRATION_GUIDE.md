# Super Dev 集成维护指南

> 普通用户如何在宿主里触发和继续流程，请优先看：
> [HOST_USAGE_GUIDE.md](/Users/weiyou/Documents/kaifa/super-dev/docs/HOST_USAGE_GUIDE.md)

这份文档只面向维护者。目标不是教普通用户手敲一长串 CLI，而是说明：

- Super Dev 如何注入到宿主
- 哪些规则 / Skill 文件会被写入
- 维护者何时需要 `skill / integrate / doctor`
- 如何把接入修复回当前产品边界

## 当前产品边界

普通用户公开终端命令只有：

```bash
super-dev
super-dev update
super-dev uninstall
```

普通用户的开发主路径始终在宿主里，优先只记住这些表达：

```text
/super-dev <goal>
/super-dev-seeai <goal>
继续当前流程
现在下一步是什么
```

维护者才会显式进入：

- `skill`
- `integrate`
- `doctor`
- `detect`
- `onboard`
- `/super-dev-work`
- `/super-dev-run`
- `/super-dev-review`

## 维护者接入顺序

### 1. 首次接入或修复接入面

```bash
super-dev
```

默认安装器会根据机器环境与当前仓库状态完成接入或给出修复建议。只有当报告明确提示需要维护者干预时，再进入 `doctor / skill / integrate`。

### 2. 诊断宿主状态

```bash
super-dev
```

维护者从接入/诊断报告看清：

- 当前宿主入口应该用什么
- 标准流第一句是什么
- 比赛流第一句是什么
- 是否需要重启宿主
- 是否缺少 Skill / rule / command surface
- 当前宿主是否已经 `标准流可直接开工`
- 当前宿主是否已经 `SEEAI 比赛模式可直接开工`
- 当前恢复点在哪里
- 是否需要先做 baseline / docs confirm / preview confirm

### 3. Skill / integrate 的定位

- `skill`：补装、列出、卸载宿主侧 Skill
- `integrate`：生成或修复宿主规则文件、做兼容性审计、记录真人验收
- `detect`：读当前仓库与宿主状态，输出 resume card / decision card

这些都属于维护面，不属于普通用户日常开发命令。

维护者在当前版本要特别记住：

- 默认是**项目优先接入**
- 用户级 / 系统级 surface 只有显式 `--with-user-surfaces` 才补
- “文件写入完成”不等于“宿主已经可直接开工”
- 要以 `标准流准备度 / SEEAI 准备度 / 官方工作流检查 / 接入后先验` 这 4 类信号判断是否真正闭环

## 规则文件落点

默认遵循项目优先注入：先写项目级 surfaces，再按需补齐用户 / 全局 surfaces。下面按 canonical host matrix 分组列出正式接入面，`claude` / `claude-code` 与 `codex` / `codex-cli` 都是独立 host。

### CLI hosts

| Host | 集成规则文件 |
|:---|:---|
| claude-code | `CLAUDE.md` + `.claude/CLAUDE.md` + 可选 `.claude/settings*.json` + `.claude/skills/super-dev/SKILL.md` + `.claude/agents/super-dev.md`；`.claude/commands/super-dev.md` 仅作为兼容增强面 |
| codex-cli | `AGENTS.md` + `.agents/skills/super-dev/SKILL.md` + `.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json`；`CODEX_HOME/AGENTS.md`（默认 `~/.codex/AGENTS.md`）仅在显式 `--with-user-surfaces` 时写入 |
| opencode | `AGENTS.md` + `.opencode/commands/super-dev.md` + `.opencode/skills/super-dev/SKILL.md` + `~/.config/opencode/AGENTS.md` + `~/.config/opencode/commands/` + `~/.config/opencode/skills/`；`.opencode/agents/` 继续只作为增强面 |
| droid-cli | `AGENTS.md` + `.factory/rules/super-dev.md` + `.factory/skills/super-dev/SKILL.md` + `.factory/skills/super-dev-seeai/SKILL.md`；`.factory/commands/super-dev*.md` 作为兼容增强面补齐；`~/.factory/*` 仅在显式 `--with-user-surfaces` 时补齐 |
| gemini-cli | `GEMINI.md` + 可选 `.gemini/settings.json` + `.gemini/commands/super-dev.toml`；`~/.gemini/skills/` 仅作为兼容增强面 |
| kiro-cli | `AGENTS.md` + `.kiro/steering/super-dev.md` + `.kiro/skills/super-dev/SKILL.md`；`~/.kiro/steering/super-dev.md` 与 `~/.kiro/steering/AGENTS.md` 仅在显式 `--with-user-surfaces` 时补齐 |
| cursor-cli | `AGENTS.md` + `.cursor/rules/super-dev.mdc`；`CLAUDE.md` 只继续作为兼容上下文 |
| copilot-cli | `AGENTS.md` + `.github/copilot-instructions.md` + `.github/skills/super-dev/SKILL.md` + `.github/agents/super-dev.md`；用户级 surfaces 仅在显式 `--with-user-surfaces` 时补齐 |
| qoder-cli | `AGENTS.md` + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/super-dev/SKILL.md`；`.qoder/agents/` 继续只作为增强面 |
| codebuddy-cli | `CODEBUDDY.md` + `.codebuddy/rules/super-dev.md` + `.codebuddy/commands/super-dev.md` + `.codebuddy/skills/super-dev/SKILL.md` + `.codebuddy/agents/super-dev.md` |
| kimi-code | 当前主链按 `AGENTS.md` + 显式 `/skill:super-dev` / `/flow:super-dev` + `kimi --continue` / `/resume` 建模；`.kimi/skills/`、`~/.kimi/skills/` 与 `.kimi/AGENTS.md` 继续作为当前增强面 |
| qwen-code | `QWEN.md` + `.qwen/commands/super-dev.md` + `.qwen/skills/super-dev/SKILL.md`；`~/.qwen/QWEN.md` 仅在显式 `--with-user-surfaces` 时补齐 |

### IDE hosts

| Host | 集成规则文件 |
|:---|:---|
| antigravity | 当前推荐 `GEMINI.md` + 可选 `.gemini/settings.json` + `.gemini/commands/super-dev.toml`；`.agent/workflows/super-dev.md` 继续作为推荐增强面 |
| cursor | `AGENTS.md` + `.cursor/rules/super-dev.mdc` + 可选 `.cursor/commands/super-dev.md`（beta）；`CLAUDE.md` 只继续作为兼容上下文 |
| windsurf | `AGENTS.md` + `.windsurf/rules/super-dev.md` + `.windsurf/workflows/super-dev.md` + `.windsurf/skills/super-dev/SKILL.md` |
| kiro | `AGENTS.md` + `.kiro/steering/super-dev.md` + `.kiro/skills/super-dev/SKILL.md`；`~/.kiro/steering/super-dev.md` 与 `~/.kiro/steering/AGENTS.md` 为可选全局增强面 |
| trae | `.trae/project_rules.md` + `.trae/rules.md` |
| trae-cn | `.trae/project_rules.md` + `.trae/rules.md` + `.trae/skills/super-dev/SKILL.md` |
| codebuddy | `CODEBUDDY.md` + `.codebuddy/rules/super-dev/RULE.mdc` + `.codebuddy/commands/super-dev.md` + `.codebuddy/agents/super-dev.md` + `.codebuddy/skills/super-dev/SKILL.md` |
| codebuddy-cn | `CODEBUDDY.md` + `.codebuddy/rules/super-dev/RULE.mdc` + `.codebuddy/commands/super-dev.md` + `.codebuddy/agents/super-dev.md` + `.codebuddy/skills/super-dev/SKILL.md` |
| qoder | `AGENTS.md` + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/super-dev/SKILL.md`；`.qoder/agents/` 继续只作为增强面 |

### Desktop assistants

| Host | 集成规则文件 |
|:---|:---|
| claude | Project Instructions + Project Knowledge + desktop extensions / local MCP；不依赖项目级自动 dotfile 注入 |
| codex | `AGENTS.md` + `.agents/skills/super-dev/SKILL.md` + `.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json` |
| workbuddy | 当前推荐任务工作台模型：技能市场/技能导入 + MCP + 项目目录授权；若启用文件导入型 Skills，则会管理 `~/.workbuddy/skills/super-dev/SKILL.md` 与 `~/.workbuddy/skills/super-dev-seeai/SKILL.md` 作为补充面，而不是官方主合同 |
| trae-solo | 当前推荐工作区接入模型：`AGENTS.md` + `.trae/rules/super-dev.md` + `.trae/commands/super-dev.md` + `.trae/skills/super-dev/SKILL.md` |
| trae-solocn | 当前推荐中文工作区模型：`.trae/rules/super-dev.md` + `.trae/skills/super-dev/SKILL.md` + `~/.trae-cn/skills/`，并和内建 `/plan` `/spec`、MTC / Code 协同 |

补充约定：
- 对默认依赖用户级 Skills 的宿主，标准版 Skill 和 SEEAI 比赛版 Skill 会分开管理。
- `标准流 ready` 只要求标准版接入面闭环；`SEEAI ready` 会额外检查比赛版 Skill 或比赛补充面是否就绪。
- 这类宿主最典型的是 `Kimi Code`、`WorkBuddy`、`Trae SOLOCN` 以及带用户级 Skill 面的 CLI/IDE 宿主。

## 维护者验收重点

维护者验收的目标只有三个：

1. 普通用户执行 `super-dev` 后，宿主能被正确注入
2. 宿主内 `/super-dev ...` 真能进入 `research -> 三文档 -> 等待确认`
3. 恢复场景下能读出 `baseline / docs / preview / resume gate`

正式的运行时与交付证据会继续落到：

- `output/*-host-surface-audit.md`
- `output/*-host-runtime-validation.md`
- `output/*-proof-pack.md`
- `output/*-release-readiness.md`

## 不要在这份文档里继续做的事

- 不要把 `pipeline / task / spec / quality / release` 当普通用户公开入口
- 不要教普通用户手工跳阶段
- 不要让终端命令重新长成治理控制台

### 3. 我只想更新规则文件

```bash
super-dev integrate setup --target <target> --force
```

---

## 最佳实践

- 团队统一在宿主里使用 `/super-dev 需求` 或 `super-dev: 需求` 作为开发入口，避免再把正常开发拉回终端命令面
- 将 `output/` 和 `.super-dev/changes/` 纳入代码评审上下文
- 在合并前强制检查红队报告和质量门禁报告
- 交付前使用 `output/delivery/` 作为对外版本快照
