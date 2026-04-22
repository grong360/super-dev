import Image from 'next/image';
import { HOSTS, STATS } from '@/lib/constants';
import type { SiteLocale } from '@/lib/site-locale';

const HOST_ICON_MAP: Record<string, string> = {
  'Claude': '/hosts/claude-code.ico',
  'Claude Code': '/hosts/claude-code.ico',
  'Codex': '/hosts/codex-cli.png',
  'Codex CLI': '/hosts/codex-cli.png',
  'Antigravity': '/hosts/antigravity.png',
  'Gemini CLI': '/hosts/gemini-cli.png',
  'Cursor CLI': '/hosts/cursor.ico',
  'Cursor': '/hosts/cursor.ico',
  'Windsurf': '/hosts/windsurf.ico',
  'Copilot CLI': '/hosts/copilot-cli.png',
  'Trae': '/hosts/trae.png',
  'Kiro CLI': '/hosts/kiro.ico',
  'Kiro': '/hosts/kiro.ico',
  'Cline': '/hosts/cline.png',
  'OpenCode': '/hosts/opencode.ico',
  'Qoder CLI': '/hosts/qoder.png',
  'Qoder': '/hosts/qoder.png',
  'CodeBuddy CLI': '/hosts/codebuddy.png',
  'CodeBuddy': '/hosts/codebuddy.png',
};

const HOST_URLS: Record<string, string> = {
  'Claude': 'https://claude.ai',
  'Claude Code': 'https://code.claude.com',
  'Codex': 'https://openai.com/index/introducing-codex/',
  'Codex CLI': 'https://openai.com/index/introducing-codex/',
  'Droid CLI': 'https://docs.factory.ai/reference/cli-reference',
  'CodeBuddyCN': 'https://codebuddy.ai',
  'Kimi Code': 'https://www.kimi.com/code/docs/en/kimi-cli.html',
  'Qwen Code': 'https://qwenlm.github.io/qwen-code-docs/en/',
  'Antigravity': 'https://antigravity.im/documentation',
  'Gemini CLI': 'https://github.com/google-gemini/gemini-cli',
  'Cursor CLI': 'https://cursor.com',
  'Cursor': 'https://cursor.com',
  'Windsurf': 'https://windsurf.com',
  'Copilot CLI': 'https://github.com/features/copilot',
  'Trae': 'https://trae.ai',
  'TraeCN': 'https://trae.ai',
  'Trae SOLO': 'https://trae.ai',
  'Trae SOLOCN': 'https://trae.ai',
  'Kiro CLI': 'https://kiro.dev',
  'Kiro': 'https://kiro.dev',
  'Cline': 'https://cline.bot',
  'OpenCode': 'https://opencode.ai',
  'Qoder CLI': 'https://qoder.ai',
  'Qoder': 'https://qoder.ai',
  'CodeBuddy CLI': 'https://codebuddy.ai',
  'CodeBuddy': 'https://codebuddy.ai',
};

function HostLogo({ name }: { name: string }) {
  const iconSrc = HOST_ICON_MAP[name];
  const url = HOST_URLS[name];
  const initial = name.trim().charAt(0).toUpperCase();
  const content = (
    <div className="flex shrink-0 items-center gap-2 rounded-lg border border-border-muted bg-bg-secondary/50 px-4 py-2 opacity-70 transition-opacity duration-200 hover:opacity-100 cursor-pointer" title={name}>
      {iconSrc ? (
        <Image
          src={iconSrc}
          alt={name}
          width={20}
          height={20}
          className="h-5 w-5 rounded"
          unoptimized
        />
      ) : (
        <span className="flex h-5 w-5 items-center justify-center rounded bg-bg-tertiary text-xs font-mono font-bold text-text-muted">{initial}</span>
      )}
      <span className="whitespace-nowrap text-sm text-text-secondary">{name}</span>
    </div>
  );
  if (url) {
    return <a href={url} target="_blank" rel="noopener noreferrer">{content}</a>;
  }
  return content;
}

const COPY = {
  zh: {
    hosts: '当前宿主覆盖',
    intro: '不是装完一个 Python 包就结束。安装器会把当前宿主矩阵收敛到同一条主路径：接入、复制宿主首句、回宿主里开始 research。',
    labels: STATS.zh,
  },
  en: {
    hosts: 'Current host coverage',
    intro: 'Installing a Python package is not the product. The installer pulls the current host matrix onto one path: onboard, copy the host-specific first prompt, then go back into the host and start research.',
    labels: STATS.en,
  },
} as const;

export function SocialProofBand({ locale = 'zh' }: { locale?: SiteLocale }) {
  const copy = COPY[locale];

  return (
    <section className="border-y border-border-muted bg-bg-secondary py-10" aria-label="Site trust signals">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <p className="mb-6 max-w-3xl text-sm leading-7 text-text-secondary">{copy.intro}</p>

        <dl className="mb-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {copy.labels.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-border-default bg-bg-primary/60 px-5 py-4">
              <dt className="text-sm text-text-muted">{stat.label}</dt>
              <dd className="mt-2 text-2xl font-bold font-mono text-text-primary">{stat.value}</dd>
            </div>
          ))}
        </dl>

        <div className="mb-5 flex items-center gap-4">
          <div className="h-px flex-1 bg-border-muted" />
          <span className="text-xs uppercase tracking-wider text-text-muted">{copy.hosts}</span>
          <div className="h-px flex-1 bg-border-muted" />
        </div>

        <div
          className="relative overflow-hidden group"
          aria-label={`${copy.hosts}: ${HOSTS.map((h) => h.name).join(', ')}`}
        >
          <div className="pointer-events-none absolute bottom-0 left-0 top-0 z-10 w-16 bg-gradient-to-r from-bg-secondary to-transparent" aria-hidden="true" />
          <div className="pointer-events-none absolute bottom-0 right-0 top-0 z-10 w-16 bg-gradient-to-l from-bg-secondary to-transparent" aria-hidden="true" />
          <div className="flex gap-3 group-hover:[&>div]:pause">
            <div className="flex shrink-0 gap-3 animate-scroll">
              {HOSTS.map((host) => <HostLogo key={`a-${host.name}`} name={host.name} />)}
              {HOSTS.map((host) => <HostLogo key={`b-${host.name}`} name={host.name} />)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
