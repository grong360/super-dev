import { Badge } from '@/components/ui/Badge';
import { HOST_MATRIX_GROUPS, HOSTS, type HostCategory, type HostStatus } from '@/lib/constants';
import type { SiteLocale } from '@/lib/site-locale';

type DisplayStatus = 'recommended' | 'compatible';

const DISPLAY_BADGE_VARIANT: Record<DisplayStatus, 'certified' | 'compatible'> = {
  recommended: 'certified',
  compatible: 'compatible',
};

const CATEGORY_LABELS: Record<HostCategory, string> = {
  cli: 'CLI',
  ide: 'IDE',
  assistant: 'Desktop assistants',
};

const COPY = {
  zh: {
    eyebrow: 'Host Support',
    title: '26 个宿主不是一张支持列表，而是一张“接入后怎么立刻开工”的地图。',
    body: '首页只保留用户第一眼真需要的信息：这个宿主属于哪一类、第一句怎么说、它会先读什么、最适合拿来做哪种工作。更细的接入后先验、官方工作流检查和双模式准备度，留给安装器与文档中心。',
    matrixTitle: '宿主矩阵',
    protocol: '会先读什么',
    category: '分组',
    trigger: '宿主第一句',
    fit: '最适合',
    readiness: '状态',
    labels: { recommended: '推荐', compatible: '兼容' },
  },
  en: {
    eyebrow: 'Host Support',
    title: 'The unified host matrix is not just support coverage. It tells you how to start immediately after onboarding.',
    body: 'The homepage keeps only the signals that matter first: which class a host belongs to, the first prompt to use, what Super Dev loads first, and what that host is best suited for. Detailed self-checks, official workflow checks, and dual-mode readiness stay in the installer and docs center.',
    matrixTitle: 'Host matrix',
    protocol: 'Loads first',
    category: 'Group',
    trigger: 'First prompt',
    fit: 'Best for',
    readiness: 'Status',
    labels: { recommended: 'Recommended', compatible: 'Compatible' },
  },
} as const;

function hostDisplayStatus(host: { integration: HostStatus; runtime: HostStatus }): DisplayStatus {
  return host.integration === 'certified' || host.runtime === 'certified' ? 'recommended' : 'compatible';
}

function HostChip({ label }: { label: string }) {
  return <span className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 font-mono text-sm text-text-primary">{label}</span>;
}

export function HostCompatSection({ locale = 'zh' }: { locale?: SiteLocale }) {
  const copy = COPY[locale];

  return (
    <section id="hosts" className="section-glow border-b border-border-muted bg-bg-secondary py-20 lg:py-24" aria-labelledby="hosts-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-14 max-w-3xl">
          <p className="mb-3 text-sm font-mono uppercase tracking-wider text-accent-blue">{copy.eyebrow}</p>
          <h2 id="hosts-title" className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">{copy.title}</h2>
          <p className="mt-4 text-lg leading-8 text-text-secondary">{copy.body}</p>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          {HOST_MATRIX_GROUPS.map((group) => (
            <article key={group.key} className="rounded-2xl border border-border-default bg-bg-primary/70 p-6">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-xl font-semibold text-text-primary">{group.title}</h3>
                <Badge variant="version">{group.label}</Badge>
              </div>
              <p className="mb-5 text-sm leading-7 text-text-secondary">
                {group.key === 'cli' ? (
                  locale === 'en'
                    ? 'CLI hosts are best when you want the shortest install-to-first-prompt path and a clear terminal or app companion workflow.'
                    : 'CLI 宿主最适合“装完就回当前会话开始做事”的路径，入口最短。'
                ) : group.key === 'ide' ? (
                  locale === 'en'
                    ? 'IDE hosts keep workspace context, rules, commands, and longer-running implementation loops together.'
                    : 'IDE 宿主更适合长时间停留在同一个工作区里做实现、返工和联调。'
                ) : (
                  locale === 'en'
                    ? 'Desktop assistants are better for project instructions, knowledge-heavy work, and continuity across broader conversations.'
                    : '桌面助手更适合 Project Instructions、知识注入和跨会话继续项目。'
                )}
              </p>
              <div className="flex flex-wrap gap-2">
                {group.hosts.map((host) => (
                  <HostChip key={host.name} label={host.name} />
                ))}
              </div>
            </article>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-border-default bg-bg-primary/70 p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h3 className="text-xl font-semibold text-text-primary">{copy.matrixTitle}</h3>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(copy.labels) as DisplayStatus[]).map((status) => (
                <Badge key={status} variant={DISPLAY_BADGE_VARIANT[status]}>{copy.labels[status]}</Badge>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-y-3 text-left text-sm">
              <thead>
                <tr className="text-text-muted">
                  <th className="px-3 py-2 font-medium">Host</th>
                  <th className="px-3 py-2 font-medium">{copy.category}</th>
                  <th className="px-3 py-2 font-medium">{copy.trigger}</th>
                  <th className="px-3 py-2 font-medium">{copy.protocol}</th>
                  <th className="px-3 py-2 font-medium">{copy.fit}</th>
                  <th className="px-3 py-2 font-medium">{copy.readiness}</th>
                </tr>
              </thead>
              <tbody>
                {HOSTS.map((host) => (
                  <tr key={host.name} className="rounded-xl border border-border-default bg-bg-secondary/45">
                    <td className="rounded-l-xl whitespace-nowrap px-3 py-3 font-mono text-text-primary">{host.name}</td>
                    <td className="px-3 py-3"><Badge variant="default">{CATEGORY_LABELS[host.category]}</Badge></td>
                    <td className="whitespace-nowrap px-3 py-3 font-mono text-accent-blue">{host.triggerLabel ?? host.firstPrompt}</td>
                    <td className="px-3 py-3 text-text-secondary">{host.protocol}</td>
                    <td className="px-3 py-3 text-text-secondary">{host.bestFor}</td>
                    <td className="rounded-r-xl whitespace-nowrap px-3 py-3">
                      <Badge variant={DISPLAY_BADGE_VARIANT[hostDisplayStatus(host)]}>{copy.labels[hostDisplayStatus(host)]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
