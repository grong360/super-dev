# Super Dev Codex Plugin

This is an optional local Codex plugin enhancement for repositories that want a richer Codex App/Desktop surface than `AGENTS.md + Skills` alone.

It does not replace the official Super Dev Codex integration surfaces:

- `AGENTS.md`
- `.agents/skills/super-dev/SKILL.md`
- `CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`)
- `~/.agents/skills/super-dev/SKILL.md`

Use this plugin as an advanced Codex App/Desktop enhancement when you want the repository to expose a repo-local plugin entry in addition to the official AGENTS/Skills model.

Plugin root:

- `.codex-plugin/plugin.json`
- `skills/super-dev/SKILL.md`
- optional legacy compatibility alias files may still exist for cleanup or migration, but the public skill name remains `super-dev`

Marketplace entry:

- `.agents/plugins/marketplace.json`

The plugin skill should behave exactly like the main Codex Super Dev workflow:

- App/Desktop slash list entry: `super-dev`
- App/Desktop advanced maintainer control: `super-dev-run`
- CLI explicit skill mention: `$super-dev`
- AGENTS fallback: `super-dev: <需求描述>`
- Existing-project work (`evolve` / `variant` / `patch`) must baseline the current repository before docs/spec.
- Resume is a first-class default path: continue with `super-dev: 继续当前流程` when resuming a closed host session.
