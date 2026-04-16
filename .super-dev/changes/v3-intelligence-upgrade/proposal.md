# Super Dev v3.0 Intelligence Upgrade Proposal

## Summary

Six-tier architecture upgrade to transform Super Dev from a phase-chain governance tool into an intelligent, self-verifying, cross-host governance platform.

## Motivation

Current Super Dev enforces governance through CLAUDE.md rules + quality gate scoring. But:
- No closed-loop verification between spec artifacts and actual code
- Host hooks are statically declared, not dynamically enforced
- No cross-session memory evolution
- 18 host integrations have no parity verification
- No automated spec-to-test generation
- No feedback loop from delivery back to knowledge base

## Scope

### Tier 1: Spec Compliance Engine (P0)
- `super_dev/reviewers/spec_compliance.py` — requirement-to-code traceability matrix
- `super_dev/reviewers/architecture_drift.py` — spec vs. implementation import-graph drift detection
- `super_dev/reviewers/uiux_compliance.py` — icon/token/typography usage vs. UIUX spec

### Tier 2: Host Hooks Runtime (P0)
- `super_dev/hooks/hooks_runtime.py` — unified hook plugin interface and registry
- `super_dev/hooks/host_hooks_generator.py` — auto-generate host-specific hook configs (Claude Code, Kiro, etc.)

### Tier 3: Context Memory Evolution (P1)
- `super_dev/memory/codified_context.py` — auto-evolving project memory across sessions
- `super_dev/memory/session_auto_brief.py` — automatic SESSION_BRIEF.md generation after each phase

### Tier 4: Multi-Host Parity Verifier (P1)
- `super_dev/integrations/parity_verifier.py` — cross-host commands/skills consistency checker

### Tier 5: Spec-to-Test Pipeline (P2)
- `super_dev/creators/test_generator.py` — generate acceptance tests and API contract tests from specs

### Tier 6: Intelligence Feedback Loop (P2)
- `super_dev/reviewers/feedback_collector.py` — post-delivery lessons → knowledge base evolution

## CLI Commands Added

- `super-dev compliance` — run spec compliance check
- `super-dev parity` — run multi-host parity check
- `super-dev hooks generate` — generate host hook configurations
- `super-dev context evolve` — evolve codified context from session history
- `super-dev testgen` — generate tests from spec artifacts

## Quality Gate Integration

New quality gate dimensions added with weights:
- spec_compliance (weight: 3.0)
- architecture_drift (weight: 2.5)
- uiux_compliance (weight: 2.0)

## Risks

- Large surface area: mitigate by making each tier independently usable
- Host parity changes could break existing installs: mitigate with `--dry-run` on parity checker
- Context evolution could bloat: mitigate with token budget caps (existing 4K budget)
