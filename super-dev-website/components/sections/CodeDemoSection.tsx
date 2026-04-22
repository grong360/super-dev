'use client';
import { useState } from 'react';
import { ArrowRight, Download, FileText, Play } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { cn } from '@/lib/utils';
import { localizedPath, type SiteLocale } from '@/lib/site-locale';

const TAB_ICONS: LucideIcon[] = [Download, Play, FileText];

const TABS = {
  zh: [
    {
      id: 'five-minute',
      label: '5 分钟上手',
      filename: 'Terminal',
      code: `uv tool install super-dev

# 进入宿主安装引导
super-dev

# 安装器会直接打印：
# - 推荐宿主
# - 标准流第一句
# - 比赛流第一句
# - 接入后先验
# - 官方工作流检查

# 终端到这里就结束
# 接下来离开终端，回宿主里开工`,
    },
    {
      id: 'host-first',
      label: '回宿主开工',
      filename: 'Host trigger',
      code: `# Slash 宿主
/super-dev 开发一个可交付的项目

# Codex CLI
$super-dev

# Codex App/Desktop
# 从 / 列表选择 super-dev

# 文本宿主
super-dev: 开发一个可交付的项目

# 第一轮不是直接写码
# 1. 先 research
# 2. 再写 research / PRD / Architecture / UIUX
# 3. 三文档完成后暂停，等你确认`,
    },
    {
      id: 'artifacts',
      label: '关键落盘',
      filename: 'output/',
      code: `output/<project>-research.md
output/<project>-prd.md
output/<project>-architecture.md
output/<project>-uiux.md
.super-dev/changes/<change>/proposal.md
.super-dev/changes/<change>/tasks.md
output/<project>-frontend-runtime.json
output/delivery/manifest.json`,
    },
  ],
  en: [
    {
      id: 'five-minute',
      label: 'Five-minute path',
      filename: 'Terminal',
      code: `uv tool install super-dev

# open the host installer
super-dev

# the installer prints:
# - the recommended host
# - the standard-flow first prompt
# - the competition-flow first prompt
# - the post-onboard self-check
# - the official workflow checks

# the terminal stops here
# real work moves back into the host`,
    },
    {
      id: 'host-first',
      label: 'Back into the host',
      filename: 'Host trigger',
      code: `# Slash hosts
/super-dev Build a shippable product

# Codex CLI
$super-dev

# Codex App/Desktop
# choose super-dev from the / list

# Text-first hosts
super-dev: Build a shippable product

# The first pass is not coding
# 1. research
# 2. research / PRD / Architecture / UIUX
# 3. stop and wait for approval before Spec or implementation`,
    },
    {
      id: 'artifacts',
      label: 'What gets written',
      filename: 'output/',
      code: `output/<project>-research.md
output/<project>-prd.md
output/<project>-architecture.md
output/<project>-uiux.md
.super-dev/changes/<change>/proposal.md
.super-dev/changes/<change>/tasks.md
output/<project>-frontend-runtime.json
output/delivery/manifest.json`,
    },
  ],
} as const;

const COPY = {
  zh: {
    eyebrow: 'How it works',
    title: '官网先讲最短路径，不再把你困在终端命令堆里。',
    body: '安装器负责告诉你“该进哪个宿主、第一句怎么说、现在能不能直接开工”。之后 research、三文档、确认门、前端预览、质量门和交付证据都在宿主里继续，而不是让你在官网背一堆底层命令。',
    docs: '查看完整文档',
  },
  en: {
    eyebrow: 'How it works',
    title: 'The homepage now teaches the shortest path instead of a pile of terminal commands.',
    body: 'The installer tells you which host to use, what the first prompt is, and whether that host is ready to start. After that, research, the three core docs, approval gates, preview validation, quality, and delivery evidence continue inside the host rather than through a pile of low-level commands.',
    docs: 'Read full docs',
  },
} as const;

export function CodeDemoSection({ locale = 'zh' }: { locale?: SiteLocale }) {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = TABS[locale];
  const copy = COPY[locale];

  return (
    <section className="border-b border-border-muted bg-bg-primary py-20 lg:py-24" aria-labelledby="workflow-demo-title">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mb-14 max-w-3xl">
          <p className="mb-3 text-sm font-mono uppercase tracking-wider text-accent-blue">{copy.eyebrow}</p>
          <h2 id="workflow-demo-title" className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">{copy.title}</h2>
          <p className="mt-4 text-lg leading-8 text-text-secondary">{copy.body}</p>
        </div>

        <div className="rounded-2xl border border-border-default bg-bg-secondary/55 p-4 sm:p-6">
          <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Workflow demo tabs">
            {tabs.map((tab, index) => {
              const Icon = TAB_ICONS[index];
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(index)}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                    activeTab === index
                      ? 'border-accent-blue/40 bg-accent-blue/10 text-text-primary'
                      : 'border-border-default bg-bg-primary/70 text-text-secondary hover:text-text-primary'
                  )}
                  role="tab"
                  aria-selected={activeTab === index}
                >
                  <Icon size={15} aria-hidden="true" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <CodeBlock code={tabs[activeTab].code} filename={tabs[activeTab].filename} />
        </div>

        <div className="mt-8">
          <Link href={localizedPath(locale, '/docs')} className="inline-flex items-center gap-2 text-sm font-medium text-accent-blue transition-colors hover:text-accent-blue-hover">
            {copy.docs}
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  );
}
