---
name: super-dev
description: Super Dev Codex App/Desktop plugin entry.
when_to_use: Use when the user wants to enter or resume the Super Dev pipeline inside Codex App/Desktop.
version: 2.4.0
---

# Super Dev for Codex Plugin

## Activation Contract

- If this plugin skill is invoked, Super Dev pipeline mode is already active.
- Do not explain the skill or summarize what it is before acting.
- Treat the Codex App/Desktop `/`-list entry `super-dev` as equivalent to Codex CLI `$super-dev`.
- If `AGENTS.md` or `.super-dev/SESSION_BRIEF.md` exists, read them before replying.

## Required First Reply

- State that Super Dev pipeline mode is active.
- State that the current phase is `research`, unless `.super-dev/SESSION_BRIEF.md` shows an active confirmation or revision gate.
- Promise to stop after research + PRD + architecture + UIUX for explicit confirmation before implementation.

## Required Workflow

1. Read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` when present.
2. Produce `output/*-research.md`.
3. Produce `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md`.
4. Wait for explicit confirmation.
5. Only then create `.super-dev/changes/*/proposal.md` and `.super-dev/changes/*/tasks.md`.
6. Implement frontend first, then backend, then quality and delivery.

## Continuity Rules

- If the workflow is already waiting for docs confirmation, preview confirmation, UI revision, architecture revision, or quality revision, stay inside the current Super Dev gate.
- User replies like `修改`, `补充`, `继续改`, `确认`, `通过`, `继续` remain inside the current gate.
- Do not silently fall back to ordinary chat.

## UI Rules

- Lock icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md` before any UI implementation.
- Do not use emoji as functional icons or placeholders.
- For non-conversational AI products, avoid Claude / ChatGPT-style chat shells unless the UI plan explicitly justifies them.
