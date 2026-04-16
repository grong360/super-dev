# Super Dev v3.0 Intelligence Upgrade — Tasks

## Phase A: Spec Compliance Engine (P0)

### A1. Create `super_dev/reviewers/spec_compliance.py`
- Parse PRD requirements from `output/*-prd.md` (markdown headings + numbered items)
- Scan implementation files in project_dir for matches (import paths, component names, route paths, class names)
- Generate traceability matrix: `{requirement_id: {status: found|missing|partial, files: [...], confidence: 0-1}}`
- Output JSON + Markdown report
- Export `run_spec_compliance(project_dir, output_dir) -> ComplianceReport`

### A2. Create `super_dev/reviewers/architecture_drift.py`
- Parse architecture doc from `output/*-architecture.md` for declared modules, dependencies, tech stack
- Build actual import graph by scanning Python/JS/TS imports
- Compare declared vs. actual, emit drift items: `{declared_module, actual_module, drift_type: missing|extra|mismatched}`
- Export `run_architecture_drift(project_dir, output_dir) -> DriftReport`

### A3. Create `super_dev/reviewers/uiux_compliance.py`
- Parse UIUX doc from `output/*-uiux.md` for declared icon_library, typography, design_tokens, components
- Scan frontend source files for icon imports, CSS variable usage, font-family declarations
- Emit violations: `{rule, expected, actual, file, line}`
- Export `run_uiux_compliance(project_dir, output_dir) -> UIUXComplianceReport`

### A4. Integrate spec compliance into quality gate
- Add spec_compliance, architecture_drift, uiux_compliance as new check categories in quality_gate.py
- Add weights and scoring logic
- Add to quality gate report output

## Phase B: Host Hooks Runtime (P0)

### B1. Create `super_dev/hooks/hooks_runtime.py`
- Define `HookPlugin` protocol: `name, trigger_event, check(context) -> HookResult, fix(context) -> bool`
- Define `HookRegistry` class to discover and load hook plugins
- Define `HookResult` dataclass: `{blocked: bool, message: str, auto_fixed: bool}`
- Support events: pre_write, post_write, pre_command, post_command, pre_test, post_test

### B2. Create `super_dev/hooks/host_hooks_generator.py`
- Generate Claude Code hooks config (settings.local.json PreToolUse/PostToolUse)
- Generate Kiro agent hooks config format
- Generate Cursor rules format
- Generate generic shell hook scripts
- Accept `--dry-run` flag to preview without writing

### B3. Add `super-dev hooks generate` CLI command
- Add parser in cli_parser_mixin.py
- Wire to host_hooks_generator.py

## Phase C: Context Memory Evolution (P1)

### C1. Create `super_dev/memory/codified_context.py`
- Parse session history from `.super-dev/workflow-history/` and `workflow-events.jsonl`
- Extract: resolved issues, discovered patterns, actual API paths, library version constraints
- Write to `.super-dev/codified-context.md` (markdown sections: constraints, discoveries, gotchas, patterns)
- Token budget enforcement (cap at 4K tokens)
- Export `evolve_codified_context(project_dir) -> CodifiedContextReport`

### C2. Create `super_dev/memory/session_auto_brief.py`
- After each phase completion, auto-generate/update SESSION_BRIEF.md
- Include: completed phases, current phase, next step, discovered risks, pending decisions
- Deduplicate with existing manual brief content

### C3. Add `super-dev context evolve` CLI command

## Phase D: Multi-Host Parity Verifier (P1)

### D1. Create `super_dev/integrations/parity_verifier.py`
- Scan all host directories (`.claude/`, `.cursor/`, `.codebuddy/`, `.codex/`, `.openclaw/`, `.opencode/`, `.qoder/`, `.kilocode/`, `.windsurf/`, `.kiro/`, `.roo/`, `.trae/`, `.junie/`, `.cline/`)
- For each command name, compare file content across hosts
- Report: `{command, hosts_with_it, hosts_missing_it, content_diffs}`
- Support `--fix` to copy from reference host (claude-code by default)

### D2. Add `super-dev parity` CLI command

## Phase E: Spec-to-Test Pipeline (P2)

### E1. Create `super_dev/creators/test_generator.py`
- Parse PRD requirements into test scenarios
- Generate Gherkin feature files for BDD acceptance tests
- Generate API contract test scaffolding from architecture doc
- Output to `tests/acceptance/` and `tests/contract/`

### E2. Add `super-dev testgen` CLI command

## Phase F: Intelligence Feedback Loop (P2)

### F1. Create `super_dev/reviewers/feedback_collector.py`
- Parse git log for recent commits (bug fixes, hotfixes, rollbacks)
- Map commit messages to knowledge domains
- Generate candidate knowledge entries for review
- Write to `.super-dev/feedback-candidates.json`

### F2. Add `super-dev feedback` CLI command

## Phase G: CLI Integration & Wiring

### G1. Add all new subcommands to cli_parser_mixin.py
### G2. Wire quality gate integration
### G3. Update __version__ to "2.4.0"
### G4. Run lint, typecheck, and tests
