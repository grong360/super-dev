# Super Dev Workflow Guide (2.4.0)

> End users should start with:
> - [README.md](/Users/weiyou/Documents/kaifa/super-dev/README.md)
> - [docs/QUICKSTART.md](/Users/weiyou/Documents/kaifa/super-dev/docs/QUICKSTART.md)
> - [docs/HOST_USAGE_GUIDE.md](/Users/weiyou/Documents/kaifa/super-dev/docs/HOST_USAGE_GUIDE.md)
>
> This guide also contains maintainer workflow controls, Spec/Task loops, and release boundaries. It is not the first document most end users should read.

This is the practical handbook for running Super Dev in real projects. It covers:

- command usage and operator flow
- greenfield delivery (0 to 1)
- iterative delivery on existing systems (1 to N+1, including 1-to-1+N rollouts)
- commercial release gates and handoff standards

---

## 1. Start Here

### Recommended entrypoint

End users should only remember 3 terminal commands:

```bash
super-dev
super-dev update
super-dev uninstall
```

The preferred path is to trigger Super Dev inside the host session:

```text
Native slash hosts: /super-dev Build an enterprise project management platform with auth, RBAC, projects, tasks, and analytics
Codex App/Desktop: choose super-dev from the / list
Codex CLI: $super-dev
Natural-language fallback: super-dev: Build an enterprise project management platform with auth, RBAC, projects, tasks, and analytics
```

Regular users should primarily remember these host-side prompts:

```text
/super-dev <goal>
/super-dev-seeai <goal>
continue the current flow
what is the next step
```

Work modes are fixed as:

- `new`: greenfield 0-to-1 delivery
- `evolve`: additive work on an existing project
- `variant`: 1-N+1 derivative built from the current project
- `patch`: bugfix / remediation on the current project
- `resume`: continue the interrupted workflow

Hard rules:

- `new` can move directly into `research -> docs`
- `evolve / variant / patch` must start with `baseline`
- `resume` is the default scenario; reopening the host or returning the next day should restore the current workflow instead of restarting from scratch

If you are unsure which host to use on the current machine, run:

```bash
super-dev
```

Host hard gate is enabled by default. If no `ready` host is available, pipeline execution is blocked until onboarding is complete.

Typical host-side examples:

```text
/super-dev Build an enterprise project management platform with auth, RBAC, projects, tasks, and analytics
/super-dev Add a billing center to the current CRM
/super-dev continue the current flow
/super-dev docs confirmed, continue the current flow
```

That host-side entry triggers the governed pipeline:

1. `new`: research -> docs -> docs_confirm -> spec -> frontend -> preview_confirm -> backend -> quality -> delivery
2. `evolve / variant / patch`: baseline -> delta research -> docs -> docs_confirm -> spec -> frontend -> preview_confirm -> backend -> quality -> delivery

Additional rules:

- Bugfix work does not skip documentation; it follows a lighter patch path that captures symptoms, reproduction steps, impact scope, and regression risk before implementation.
- The analysis stage excludes non-project source directories such as `.venv`, `site-packages`, and `node_modules`.
- When the requirement is ambiguous, PRD should surface clarification questions first, and architecture should include a key sequence diagram by default.

### Workflow control

If the project is already in a later stage, you do not need to restart from zero.

End users should first rely on host-side recovery phrases:

```text
/super-dev continue the current workflow
/super-dev what is the next step
/super-dev resume frontend implementation and runtime validation
```

Resume truth sources:

- `.super-dev/SESSION_BRIEF.md`
- `.super-dev/workflow-state.json`
- `.super-dev/workflow-history/latest.json`
- `.super-dev/review-state/*`
- `output/*`

Maintainers should use lower-level CLI controls only when the reports explicitly require them:

```bash
super-dev status
super-dev run --resume
super-dev review docs
super-dev review preview
```

Usage:

- `status`: inspect the current governance state
- `run --resume`: continue the paused workflow
- `review *`: maintainer-only gate synchronization, not an end-user entrypoint

Document confirmation should normally happen inside the host. Maintainers should enter the terminal gate flow only when they need to sync state:

```bash
super-dev review docs
```

If the frontend visual quality is unsatisfactory, start a formal UI revision loop instead of making ad hoc CSS edits:

```bash
super-dev review ui
super-dev review ui --status revision_requested --comment "Hero feels empty and lacks brand presence; redesign the first screen"
super-dev review ui --status confirmed --comment "UI revision approved"
```

The required order for UI revision is:

1. Update `output/*-uiux.md`
2. Redo the frontend implementation
3. Rerun frontend runtime and UI review
4. Continue delivery only after the revision is approved

If the user says the technical plan, module boundaries, or API design are wrong, start a formal architecture revision loop:

```bash
super-dev review architecture
super-dev review architecture --status revision_requested --comment "Service boundaries are too coarse and the API contract must be redesigned"
super-dev review architecture --status confirmed --comment "Architecture revision approved"
```

The required order for architecture revision is:

1. Update `output/*-architecture.md`
2. Realign Spec / tasks and the implementation plan
3. Continue only after the architecture revision is approved

If the user says quality, security, or delivery evidence is still unacceptable, start a formal quality revision loop:

```bash
super-dev review quality
super-dev review quality --status revision_requested --comment "Quality gate still fails and security issues remain"
super-dev review quality --status confirmed --comment "Quality revision approved"
```

The required order for quality revision is:

1. Fix the quality / security issues
2. Rerun the quality gate and refresh delivery evidence if the reports require it
3. Continue delivery or resume execution only after the revision is approved

### Explicit work modes

Only specify the mode manually when auto-detection is not enough:

```text
/super-dev-work new <goal>
/super-dev-work evolve <goal>
/super-dev-work patch <bug>
/super-dev-work variant <goal>
```

These explicit modes are advanced maintainer-facing prompts. Regular users should still prefer plain host-side requirements, "continue the current flow", or "what is the next step".

Optional: set enterprise knowledge controls in `super-dev.yaml`:

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

---

## 2. Command Map

### Core orchestration

```text
Native slash hosts: /super-dev <requirement>
Codex App/Desktop: choose super-dev from the / list
Codex CLI: $super-dev
Natural-language fallback: super-dev: <requirement>
```

```text
Slash-native host: /super-dev <requirement>
Codex App/Desktop: choose super-dev from the / list
Codex CLI: $super-dev
Natural-language fallback: super-dev: <requirement>
Preferred recovery: /super-dev continue the current flow
Maintainer controls: /super-dev-work / /super-dev-run / /super-dev-review
```

### Maintainer loop: spec and task execution

The `spec / task` commands below are maintenance-facing workflow controls. Regular users should still stay inside the host and continue through `/super-dev`, `super-dev:`, or plain-language recovery prompts.

```bash
super-dev spec init
super-dev spec show <change_id>
super-dev spec propose <change_id> --title "<title>" --description "<description>"
super-dev spec propose <change_id> --title "<title>" --description "<description>" --no-scaffold
super-dev spec add-req <change_id> <spec_name> <req_name> "<requirement text>"
super-dev spec scaffold <change_id>
super-dev spec validate
super-dev spec quality <change_id>
super-dev spec quality <change_id> --json
super-dev spec archive <change_id>

super-dev task list
super-dev task status <change_id>
```

These `spec / task` commands are maintainer-only. Regular users should continue inside the host through `/super-dev`, `/super-dev-work`, and `/super-dev-review`.

#### Spec quality score and remediation plan

`spec quality` evaluates six dimensions (proposal/spec/plan/tasks/checklist/validation) and returns an `action_plan` with priority and executable commands.

```bash
super-dev spec quality add-billing
super-dev spec quality add-billing --json > output/add-billing-spec-quality.json
```

Recommended CI gate:

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

### Quality, risk, and release prep

`quality / review / release` remain part of the maintenance surface. End users should keep working inside the host; maintainers only return to these commands when the reports explicitly call for evidence refresh or gate synchronization.

### Design tooling

```bash
super-dev design list
super-dev design recommend
super-dev design apply <slug>
```

Notes:
- `design` is an advanced UI/UX enhancement capability for curated inspiration, direction recommendation, and writing the chosen design preference back into project config.
- It improves the quality of `uiux.md`, but it is not the main delivery path. Day-to-day delivery should still continue inside the host through the core pipeline.

### Integration and skills

`integrate` and `skill` remain maintainer-only. They are for host injection, validation, and repair, not for normal delivery work.

---

## 3. 0-to-1 Delivery (Greenfield)

Use this path when you have requirements but no production codebase yet.

### Maintainer step-by-step flow

```bash
mkdir new-product && cd new-product
super-dev
```

Then return to the host and say:

```text
/super-dev Build a B2B CRM with leads, accounts, opportunities, role-based access, and audit trail
```

### What to inspect after generation

- `output/*-research.md` (enriched requirement context)
- `output/*-prd.md` (product contract)
- `output/*-architecture.md` (technical contract)
- `output/*-uiux.md` (design contract)
- `.super-dev/changes/*/tasks.md` (implementation queue)
- `output/*-task-execution.md` (execution and auto-repair trace)
- `output/*-redteam.md` (security/performance/architecture risk report)
- `output/*-quality-gate.md` (delivery score and blockers)
- `output/delivery/*-delivery-manifest.json` (delivery readiness state)

### Recommended execution rhythm

1. Validate generated docs with product and architecture owners.
2. Land frontend demo paths first for requirement validation.
3. Implement backend/data tasks from Spec in order.
4. Resolve red-team blockers and quality gate failures.
5. Package and hand off using `output/delivery/` artifacts.

---

## 4. 1-to-N+1 Delivery (Existing Project Iteration)

Use this when your system already exists and you are adding capabilities in controlled increments.

This includes the common `1-to-1+N` pattern: one established product, multiple staged capability rollouts.

### Step-by-step flow

```bash
cd existing-project
super-dev spec init
super-dev spec propose add-billing --title "Introduce Billing Center" --description "Plans, subscriptions, invoices, callbacks"
super-dev spec add-req add-billing billing subscription "The system SHALL support subscription lifecycle management"
super-dev spec add-req add-billing billing webhook "The system SHALL process payment callbacks idempotently"
super-dev task status add-billing
```

### Increment strategy that scales

1. Keep each `change_id` narrowly scoped to one capability area.
2. Require independent quality pass for each change.
3. Merge and release in small slices instead of multi-domain bundles.
4. Treat red-team and quality outputs as hard release gates.

---

## 5. Commercial Readiness Gates

A change is considered release-ready only if all are true:

1. No red-team critical blockers remain.
2. Quality gate score is `>= 80`.
3. Spec execution status is complete or explicitly waived with rationale.
4. CI/CD assets are generated and mapped to the target platform.
5. Delivery manifest reports `ready`.
6. Delivery evidence must be aggregated and current before the change is considered release-ready.

`release proof-pack` and `release readiness` also ingest the active change's `spec quality` result so the unified release panel includes proposal/spec/plan/tasks/checklist/validation maturity. They also ingest scope coverage so pipeline completion stays separate from full PRD scope completion.

To confirm that a host really completed research, wrote the three core docs to disk, and stopped at the confirmation gate, prefer the host-side resume card plus `doctor / detect`; enter `integrate validate` only when a maintainer needs to record formal runtime acceptance evidence.

If the system says the pipeline is complete but your gap analysis still lists major unimplemented items, inspect `product-audit`, `release proof-pack`, and `release readiness` for scope coverage and high-priority gaps.

Use it to distinguish:
- `Pipeline Completed`
- `Delivery Ready`
- `Scope Coverage`

Run full preflight before tagging:

```bash
./scripts/preflight.sh
```

If you need a local constrained run:

```bash
./scripts/preflight.sh --allow-dirty --skip-benchmark --skip-package
```

---

## 6. Platform Integration Targets

Supported AI coding environments:

- CLI: `claude-code`, `codex-cli`, `opencode`, `droid-cli`, `gemini-cli`, `kiro-cli`, `cursor-cli`, `copilot-cli`, `qoder-cli`, `codebuddy-cli`, `kimi-code`, `qwen-code`
- IDE: `antigravity`, `cursor`, `windsurf`, `kiro`, `trae`, `trae-cn`, `codebuddy`, `codebuddy-cn`, `qoder`
- Desktop assistants: `claude`, `codex`, `workbuddy`, `trae-solo`, `trae-solocn`

Recommended auto-detect flow:

This is maintainer-only onboarding/repair flow, not the regular daily development path.

```bash
super-dev detect --json
super-dev detect --auto --save-profile
super-dev onboard --auto --yes --force
super-dev doctor --auto --repair --force
```

`detect` generates by default:

- `output/<project>-host-compatibility.json`
- `output/<project>-host-compatibility.md`
- `output/host-compatibility-history/*.json`
- `output/host-compatibility-history/*.md`

With `--save-profile`, Super Dev also updates `super-dev.yaml`:

- `host_profile_targets`
- `host_profile_enforce_selected=true`

Each pipeline run emits contract-audit artifacts:

- `output/*-pipeline-contract.json`
- `output/*-pipeline-contract.md`

Recommended enterprise flow:

2. Run `super-dev detect --auto --save-profile` before pipeline execution.
3. Populate `required_hosts` with the hosts your team actually uses.
4. Enable `enforce_required_hosts_ready=true` only when you want hard host readiness enforcement, then set `min_required_host_score`.

Interactive installer (default, multi-select hosts):

```bash
./install.sh
super-dev install
```

Non-interactive all-target setup:

```bash
./install.sh --targets all
```

---

## 7. Troubleshooting

### Pipeline stops at red-team

Read `output/*-redteam.md`, fix critical/high findings first, then rerun.

### Quality gate fails

Read `output/*-quality-gate.md`, then rerun task closure and quality checks:

```bash
super-dev task status <change_id>
super-dev quality --type all
```

### Need to inspect current execution state

```bash
super-dev task status <change_id>
super-dev run --resume
```

---

## 8. Daily Playbooks

### Greenfield quick playbook

```bash
super-dev
```

Then continue inside the host:

```text
/super-dev <requirement>
continue current workflow
what is the next step now
```

### Iteration quick playbook

```bash
/super-dev add a new capability to the current project
/super-dev baseline confirmed, continue current flow
continue current workflow
```

---

## 9. Related Docs

- Chinese workflow guide: `docs/WORKFLOW_GUIDE.md`
- Integration guide: `docs/INTEGRATION_GUIDE.md`
- Quickstart: `docs/QUICKSTART.md`
- Maintainer publishing entry: `docs/PUBLISHING.md`
- Maintainer release runbook: `docs/RELEASE_RUNBOOK.md`
