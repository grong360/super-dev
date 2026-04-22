import { Github } from 'lucide-react';
import { CopyCommand } from '@/components/ui/CopyCommand';
import type { SiteLocale } from '@/lib/site-locale';

const COPY = {
  zh: {
    title: '终端只做接入。真正的开发，5 分钟后就回宿主里开始。',
    body: '首页不再教你背一层额外命令。安装 Super Dev，运行 super-dev 让安装器写好项目级接入面，然后直接复制宿主首句回到当前会话。research、三文档、确认门、前端预览和交付门都会沿着这条主路径继续推进。',
    steps: [
      '1. uv tool install super-dev',
      '2. 运行 super-dev，让安装器给出推荐宿主和宿主首句',
      '3. 回宿主里直接输入 /super-dev、$super-dev 或 super-dev:',
    ],
    installNote: '首页默认只讲 uv 安装和 super-dev 引导。源码安装、版本锁定安装与 uninstall 细节留在文档中心。',
    github: '在 GitHub 查看源代码',
  },
  en: {
    title: 'The terminal only onboards. Real development moves back into the host within five minutes.',
    body: 'The homepage no longer teaches another layer of low-level commands. Install Super Dev, run super-dev so the installer writes the project-level surfaces, then copy the host-specific first prompt and return to the session you already work in. Research, the three core docs, approval gates, preview validation, and delivery all continue from there.',
    steps: [
      '1. uv tool install super-dev',
      '2. Run super-dev and let the installer print the recommended host and first prompt',
      '3. Go back into the host and start with /super-dev, $super-dev, or super-dev:',
    ],
    installNote: 'The homepage now teaches uv install and the super-dev onboarding path. Source installs, pinned versions, and uninstall details stay in the docs center.',
    github: 'View source on GitHub',
  },
} as const;

export function BottomCta({ locale = 'zh' }: { locale?: SiteLocale }) {
  const copy = COPY[locale];
  return (
    <section className="relative overflow-hidden bg-bg-primary py-24 lg:py-28" aria-labelledby="bottom-cta-title">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute left-1/2 top-1/2 h-[360px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent-blue/6 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-4xl px-4 text-center sm:px-6">
        <h2 id="bottom-cta-title" className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl lg:text-5xl">{copy.title}</h2>
        <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-text-secondary">{copy.body}</p>

        <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
          {copy.steps.map((step) => (
            <div key={step} className="rounded-2xl border border-border-default bg-bg-secondary/70 px-4 py-4 text-sm leading-7 text-text-secondary">
              {step}
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <CopyCommand command="uv tool install super-dev" className="sm:w-auto" />
          <CopyCommand command="super-dev" className="sm:w-auto" />
        </div>
        <p className="mt-4 text-sm text-text-muted">{copy.installNote}</p>

        <a
          href="https://github.com/shangyankeji/super-dev"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-8 inline-flex items-center gap-2 text-text-secondary transition-colors duration-150 hover:text-text-primary"
        >
          <Github size={16} aria-hidden="true" />
          <span>{copy.github}</span>
        </a>
      </div>
    </section>
  );
}
