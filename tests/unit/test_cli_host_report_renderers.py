from super_dev.cli_host_report_renderers import (
    render_host_compatibility_markdown,
    render_host_hardening_markdown,
    render_host_runtime_validation_markdown,
)


def _adaptation_contract() -> dict[str, object]:
    return {
        "score": 92,
        "level": "elite",
        "official_alignment": {
            "status": "official_documented",
            "label": "官方明确",
            "summary": "当前宿主协议已按官方说明收敛。",
        },
        "dimensions": {
            "official_protocol": {"status": "ready", "gaps": []},
            "entry_experience": {"status": "ready", "gaps": []},
            "continuity": {"status": "partial", "gaps": ["resume / flow probe evidence is shallow"]},
            "competition": {"status": "ready", "gaps": []},
            "docs": {"status": "ready", "gaps": []},
        },
    }


def test_render_host_compatibility_markdown_includes_adaptation_contract():
    payload = {
        "project_dir": ".",
        "selected_targets": ["claude-code"],
        "detected_hosts": ["claude-code"],
        "compatibility": {
            "overall_score": 94,
            "ready_hosts": 1,
            "total_hosts": 1,
            "enabled_checks": ["integrate", "skill"],
            "hosts": {"claude-code": {"score": 94, "ready": True, "passed": 4, "possible": 4}},
        },
        "usage_profiles": {
            "claude-code": {
                "certification_label": "Certified",
                "certification_level": "certified",
                "primary_entry": "/super-dev 你的需求",
                "usage_mode": "native-slash-and-skill",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "host",
                "restart_required_label": "否",
                "experience_profile": {
                    "label": "Flagship",
                    "tier": "flagship",
                    "best_for": "长流程商业项目开发与高密度连续协作",
                    "resume_style": "session-first",
                    "market_focus": "global",
                    "strengths": ["长会话稳定性", "slash 触发直接", "文档到交付闭环"],
                    "preferred_entries": ["/super-dev 你的需求", "/super-dev-seeai 比赛需求"],
                    "native_resume": ["/super-dev 继续当前流程", "回当前 Claude Code 会话继续"],
                },
                "adaptation_contract": _adaptation_contract(),
            }
        },
    }

    markdown = render_host_compatibility_markdown(payload)

    assert "Adaptation Maturity: 92/100 (elite)" in markdown
    assert "Official Alignment: 官方明确 (official_documented)" in markdown
    assert "Official Alignment Summary: 当前宿主协议已按官方说明收敛。" in markdown
    assert "Experience Tier: Flagship (flagship)" in markdown
    assert "Best For: 长流程商业项目开发与高密度连续协作" in markdown
    assert "Market Focus: global" in markdown
    assert "Strengths: 长会话稳定性 / slash 触发直接 / 文档到交付闭环" in markdown
    assert "Preferred Entries: /super-dev 你的需求 / /super-dev-seeai 比赛需求" in markdown
    assert "Native Resume: /super-dev 继续当前流程 / 回当前 Claude Code 会话继续" in markdown
    assert "official_protocol: ready" in markdown
    assert "continuity: partial" in markdown
    assert "resume / flow probe evidence is shallow" in markdown


def test_render_host_hardening_markdown_includes_adaptation_contract():
    payload = {
        "project_dir": ".",
        "selected_targets": ["claude-code"],
        "compatibility": {"overall_score": 94, "flow_consistency_score": 100},
        "official_compare_summary": {"score": 100},
        "host_parity_summary": {"score": 100},
        "host_gate_summary": {"score": 100, "hosts": {"claude-code": {"passed": True}}},
        "host_runtime_script_summary": {"score": 100, "hosts": {"claude-code": {"passed": True}}},
        "host_recovery_summary": {"score": 100, "hosts": {"claude-code": {"passed": True}}},
        "usage_profiles": {
            "claude-code": {
                "experience_profile": {
                    "label": "Flagship",
                    "tier": "flagship",
                    "best_for": "长流程商业项目开发与高密度连续协作",
                    "native_resume": ["/super-dev 继续当前流程", "回当前 Claude Code 会话继续"],
                },
                "adaptation_contract": _adaptation_contract(),
            }
        },
        "hardening_results": {
            "claude-code": {
                "plan": {"final_trigger": "/super-dev 你的需求", "trigger_mode": "slash"},
                "contract": {"ok": True, "invalid_surfaces": {}},
                "official_compare": {"status": "ok", "reachable_urls": 1, "checked_urls": 1},
            }
        },
    }

    markdown = render_host_hardening_markdown(payload)

    assert "Adaptation Maturity: 92/100 (elite)" in markdown
    assert "Official Alignment: 官方明确 (official_documented)" in markdown
    assert "Experience Tier: Flagship (flagship)" in markdown
    assert "Native Resume: /super-dev 继续当前流程 / 回当前 Claude Code 会话继续" in markdown
    assert "Adaptation Contract:" in markdown
    assert "official_protocol: ready" in markdown
    assert "continuity: partial" in markdown


def test_render_host_runtime_validation_markdown_includes_host_playbooks():
    payload = {
        "project_dir": ".",
        "summary": {
            "overall_status": "attention",
            "total_hosts": 1,
            "fully_ready_count": 0,
            "surface_ready_count": 1,
            "standard_flow_ready_count": 1,
            "competition_flow_ready_count": 0,
            "runtime_passed_count": 0,
            "runtime_failed_count": 0,
            "runtime_pending_count": 1,
            "repo_probe_passed_count": 0,
            "repo_probe_failed_count": 0,
            "repo_probe_pending_count": 0,
            "project_default_ready_count": 1,
            "explicit_user_surface_ready_count": 0,
            "user_surface_opt_in_available_count": 1,
            "competition_user_surface_ready_count": 0,
            "framework_focus": "next.js",
            "framework_validation_surfaces": ["SSR", "hydration"],
            "framework_coaching_summary": "当前框架焦点（Framework Coaching Focus）聚焦 next.js，重点盯住 SSR、hydration。这不是低层技术清单，而是在提前拦截首屏、路由切换、运行时稳定性和交付演示阶段的真实风险。",
            "executive_runtime_summary": "从宿主运行时视角看，当前只有 0/1 个宿主完成完整闭环，还不能把当前状态当成“注入后即可稳定工作”。 标准流可直接开工 1/1，SEEAI 比赛流可直接开工 0/1。 当前主要阻塞：1 个宿主还停在真人 runtime 待验收。 当前 workflow gate=waiting_docs_confirmation。 当前框架焦点（Framework Coaching Focus）聚焦 next.js，重点盯住 SSR、hydration。 这不是低层技术清单，而是在提前拦截首屏、路由切换、运行时稳定性和交付演示阶段的真实风险。 宿主矩阵通过只说明注入、入口和 runtime 链可用；真正的商业级 UI 质感仍要继续看截图级 UI gate、proof-pack 和 release-readiness。",
        },
        "hosts": [
            {
                "host": "claude-code",
                "surface_ready": True,
                "ready_for_delivery": False,
                "runtime_status_label": "待真人验收",
                "recommended_action": "先在 Claude Code 当前会话完成真人验收，然后继续当前流程。",
                "blocking_reason": "宿主尚未完成真人运行时验收",
                "final_trigger": "/super-dev 你的需求",
                "primary_entry": "在 Claude Code 当前项目会话里优先使用 /super-dev",
                "host_protocol_mode": "official-skills",
                "host_protocol_summary": "CLAUDE.md + .claude/skills",
                "certification_label": "Certified",
                "host_start_playbook": [
                    "起手建议: 优先在当前 Claude Code 会话里直接用 /super-dev。",
                ],
                "standard_flow_first_prompt": "/super-dev 你的需求",
                "competition_flow_first_prompt": "/super-dev-seeai 比赛需求",
                "post_onboard_self_check": [
                    "Claude Code 接入后先确认入口可用: /super-dev 你的需求 / /super-dev-seeai 比赛需求",
                ],
                "injection_closure": {
                    "scope": "project-first",
                    "label": "项目优先接入已闭环，可按需启用用户级增强面",
                    "summary": "当前宿主已完成项目优先接入；如需跨项目共享统一宿主心智，可再显式启用用户级增强面。",
                    "standard_flow_label": "标准流可直接开工",
                    "competition_flow_label": "SEEAI 比赛模式待补齐项目与用户级补充面",
                    "competition_project_surfaces_ready": False,
                    "competition_user_surfaces_ready": False,
                    "opt_in_flag": "--with-user-surfaces",
                    "missing_optional_user_surfaces": ["~/.claude/CLAUDE.md"],
                    "missing_managed_competition_project_surfaces": [
                        ".claude/skills/super-dev-seeai/SKILL.md"
                    ],
                    "missing_managed_competition_user_surfaces": [
                        "~/.claude/skills/super-dev-seeai/SKILL.md"
                    ],
                    "recommended_opt_in": "如需跨项目共享统一宿主心智，再显式加 --with-user-surfaces 重新运行 super-dev。",
                },
                "official_workflow_checks": [
                    "确认 Claude Code 按 official-skills 官方协议面真实加载 Super Dev。",
                ],
                "host_repair_playbook": "如果 slash 或技能没刷新，先重开当前 Claude Code 会话，再回到 /super-dev。",
                "runtime_checklist": ["在宿主中使用最终触发命令进入 Super Dev 流水线：/super-dev 你的需求"],
                "pass_criteria": ["Claude Code 官方工作流面、入口链和恢复链均已真人验收通过。"],
                "resume_checklist": ["原生恢复: /super-dev 继续当前流程 / 回当前 Claude Code 会话继续"],
                "framework_playbook": {
                    "framework": "next.js",
                    "implementation_modules": ["app router", "design tokens"],
                    "native_capabilities": ["metadata", "image optimization"],
                    "validation_surfaces": ["SSR", "hydration"],
                    "delivery_evidence": ["preview link", "runtime screenshot"],
                },
            }
        ],
    }

    markdown = render_host_runtime_validation_markdown(payload)

    assert "## Executive Runtime Summary" in markdown
    assert "注入后即可稳定工作" in markdown
    assert "截图级 UI gate、proof-pack 和 release-readiness" in markdown
    assert "### Host Start Playbook" in markdown
    assert "### First Prompts" in markdown
    assert "### Post-Onboard Self-Check" in markdown
    assert "### Injection Closure" in markdown
    assert "### Official Workflow Checks" in markdown
    assert "### Host Repair Playbook" in markdown
    assert "### Delivery Readiness" in markdown
    assert "### Runtime Checklist" in markdown
    assert "Claude Code 按 official-skills" in markdown
    assert "--with-user-surfaces" in markdown
    assert "Standard Flow Ready: 1/1" in markdown
    assert "SEEAI Flow Ready: 0/1" in markdown
    assert "Framework Focus: next.js" in markdown
    assert "Framework Validation Surfaces: SSR；hydration" in markdown
    assert "Framework Coaching Summary: 当前框架焦点（Framework Coaching Focus）聚焦 next.js" in markdown
    assert "SEEAI User Supplements Ready: 0/1" in markdown
    assert "SEEAI User Supplements Ready: no" in markdown
    assert "Missing SEEAI User Supplements: ~/.claude/skills/super-dev-seeai/SKILL.md" in markdown
    assert "Standard Flow: /super-dev 你的需求" in markdown
    assert "SEEAI Flow: /super-dev-seeai 比赛需求" in markdown
    assert "Standard Flow: 标准流可直接开工" in markdown
    assert "SEEAI Flow: SEEAI 比赛模式待补齐项目与用户级补充面" in markdown
    assert "Delivery Ready: no" in markdown
    assert "Blocking Reason: 宿主尚未完成真人运行时验收" in markdown
    assert "Management View: 当前仍缺最后一层真人验收" in markdown
    assert "SEEAI Project Supplements Ready: no" in markdown
    assert ".claude/skills/super-dev-seeai/SKILL.md" in markdown
