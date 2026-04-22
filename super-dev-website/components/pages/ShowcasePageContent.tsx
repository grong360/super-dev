/**
 * 开发：Excellent（11964948@qq.com）
 * 功能：案例展示页面
 * 作用：展示使用 Super Dev 流水线交付的真实项目
 * 创建时间：2026-03-26
 * 最后修改：2026-03-26
 */

import { Nav } from '@/components/layout/Nav';
import { Footer } from '@/components/layout/Footer';
import { Badge } from '@/components/ui/Badge';
import type { SiteLocale } from '@/lib/site-locale';
import {
  Layers, Globe, Music, TrendingUp, ShieldCheck, MessageCircle,
  Package, Building2, FileText, Briefcase, ShoppingCart, Image,
  Bot, MessageSquare, Monitor, Plane, Search,
} from 'lucide-react';

interface ShowcaseProject {
  name: string;
  description: string;
  tech: string[];
  category: string;
  icon: React.ElementType;
  highlight: string;
}

const PROJECTS: Record<SiteLocale, ShowcaseProject[]> = {
  zh: [
    { name: 'Goder.AI', description: 'AI Coding 在线社区平台，为开发者提供智能编程协作空间', tech: ['Next.js', 'Go', 'PostgreSQL', 'Docker'], category: '社区平台', icon: Globe, highlight: '从 PRD 到部署，全流程 Super Dev 治理' },
    { name: '咖聊 AI', description: '智能咖啡社交平台，融合 AI 推荐与线下社交场景', tech: ['React', 'FastAPI', 'PostgreSQL', 'WeChat'], category: '社交平台', icon: MessageCircle, highlight: '前后端 + 微信小程序三端同步交付' },
    { name: '淏发工程管理系统', description: '深圳市淏发工程有限公司 ERP/财务管理系统，11 个核心业务模块', tech: ['React', 'FastAPI', 'Redis', 'Docker'], category: '企业 ERP', icon: Building2, highlight: '复杂企业系统的架构设计与质量门禁' },
    { name: '熵颜 AI', description: 'AI 皮肤分析应用，基于深度学习的皮肤健康检测平台', tech: ['Next.js', 'FastAPI', 'TensorFlow', 'WeChat'], category: '医疗健康', icon: ShieldCheck, highlight: '红队安全审查确保医疗数据合规' },
    { name: 'Aurora Music', description: '在线音乐播放器，支持智能推荐与个性化播放列表', tech: ['React', 'Node.js', 'MongoDB'], category: '娱乐应用', icon: Music, highlight: 'UI/UX 设计系统驱动的前端优先交付' },
    { name: 'A 股智能推荐系统', description: '实时股票数据分析、智能选股与量化交易辅助工具', tech: ['React', 'Python', 'Redis', 'WebSocket'], category: '金融科技', icon: TrendingUp, highlight: '高性能实时数据流架构设计' },
    { name: 'Starry WMS', description: '智能仓储管理系统，集成 AI 库存预测与自动化调度', tech: ['Node.js', 'Express', 'PostgreSQL', 'Electron'], category: '物流仓储', icon: Package, highlight: 'Spec 驱动的任务拆解与增量交付' },
    { name: '小乐 WMS', description: '另一套轻量级仓储管理系统，桌面端 + 移动端双端', tech: ['Electron', 'React', 'Node.js', 'SQLite'], category: '物流仓储', icon: Package, highlight: '桌面端 + 移动端跨平台交付' },
    { name: '熵衍 Agent', description: '企业级 AI Agent 平台，多模型编排与自动化任务执行', tech: ['Python', 'FastAPI', 'LangChain', 'Docker'], category: 'AI 平台', icon: Bot, highlight: 'AI Agent 多模型编排架构设计' },
    { name: '熵衍 Chat', description: '企业级 AI 对话平台，支持多模型切换和知识库问答', tech: ['Vue.js', 'Go', 'Redis', 'Docker'], category: 'AI 对话', icon: MessageSquare, highlight: '多模型 + 知识库的完整对话系统' },
    { name: '熵衍科技官网', description: '企业官方网站，展示公司产品、技术实力和团队', tech: ['React', 'Vite', 'Tailwind CSS'], category: '企业官网', icon: Globe, highlight: '品牌化设计 + 响应式布局' },
    { name: '熵衍 Agent 落地页', description: '深色风格单页落地页，面向企业与开发者的产品介绍', tech: ['React', 'Tailwind CSS', 'Framer Motion'], category: '落地页', icon: FileText, highlight: '转化优化的 Landing Page 设计' },
    { name: 'AI 对账工具', description: '智能财务对账系统，自动匹配和核对账目数据', tech: ['Python', 'FastAPI', 'PostgreSQL'], category: '财务工具', icon: Layers, highlight: '财务数据处理的自动化流程' },
    { name: '亚洲旅运管理系统', description: '旅行社业务管理系统，涵盖订单、客户、行程全流程', tech: ['Go', 'Vue.js', 'PostgreSQL', 'Docker'], category: '旅游行业', icon: Plane, highlight: '复杂业务流程的 Spec 拆解与交付' },
    { name: '销冠培养系统', description: '销售技能培训 AI 系统，模拟真实销售场景进行训练', tech: ['React', 'Python', 'AI/ML', 'WebSocket'], category: '教育培训', icon: Briefcase, highlight: 'AI 模拟训练的交互设计' },
    { name: '敏感词检测工具', description: '高性能文本敏感词检测与过滤服务', tech: ['Python', 'FastAPI', 'Redis'], category: '安全工具', icon: Search, highlight: '高性能文本处理架构' },
    { name: 'Meiluu', description: '美容美发行业管理平台，在线预约与会员管理', tech: ['Python', 'FastAPI', 'PostgreSQL', 'Docker'], category: '行业应用', icon: ShoppingCart, highlight: '行业 SaaS 的完整交付流程' },
    { name: '图片处理工具', description: '在线图片编辑与批量处理工具', tech: ['React', 'TypeScript', 'Vite', 'Canvas'], category: '工具应用', icon: Image, highlight: '前端优先的工具型产品交付' },
    { name: 'Super Dev 官网', description: '你正在浏览的这个网站，也是 Super Dev 流水线的交付产物', tech: ['Next.js', 'Tailwind CSS', 'TypeScript', 'GitHub Pages'], category: '官方网站', icon: Monitor, highlight: '9 阶段流水线 + 质量门禁的完整实践' },
    { name: '启动合同系统', description: '软件开发委托合同自动生成与管理工具', tech: ['Python', 'FastAPI', 'Jinja2'], category: '法务工具', icon: FileText, highlight: '模板化文档生成的自动化流程' },
  ],
  en: [
    { name: 'Goder.AI', description: 'AI Coding online community platform for developers', tech: ['Next.js', 'Go', 'PostgreSQL', 'Docker'], category: 'Community', icon: Globe, highlight: 'Full pipeline governance from PRD to deployment' },
    { name: 'CafeAI', description: 'Smart coffee social platform with AI-powered matching', tech: ['React', 'FastAPI', 'PostgreSQL', 'WeChat'], category: 'Social', icon: MessageCircle, highlight: 'Three-platform delivery: web + API + mini program' },
    { name: 'Haofa ERP', description: 'Enterprise ERP/financial management system with 11 core modules', tech: ['React', 'FastAPI', 'Redis', 'Docker'], category: 'Enterprise', icon: Building2, highlight: 'Complex enterprise architecture with quality gates' },
    { name: 'EntropySkin AI', description: 'AI skin analysis with deep learning health detection', tech: ['Next.js', 'FastAPI', 'TensorFlow', 'WeChat'], category: 'Healthcare', icon: ShieldCheck, highlight: 'Red-team security audit for medical data compliance' },
    { name: 'Aurora Music', description: 'Online music player with smart recommendations', tech: ['React', 'Node.js', 'MongoDB'], category: 'Entertainment', icon: Music, highlight: 'UI/UX design system driven frontend-first delivery' },
    { name: 'A-Share Stock Analytics', description: 'Real-time stock analysis and quantitative trading tools', tech: ['React', 'Python', 'Redis', 'WebSocket'], category: 'FinTech', icon: TrendingUp, highlight: 'High-performance real-time data streaming architecture' },
    { name: 'Starry WMS', description: 'Smart warehouse management with AI inventory prediction', tech: ['Node.js', 'Express', 'PostgreSQL', 'Electron'], category: 'Logistics', icon: Package, highlight: 'Spec-driven task decomposition and incremental delivery' },
    { name: 'Xiaole WMS', description: 'Lightweight warehouse management - desktop + mobile', tech: ['Electron', 'React', 'Node.js', 'SQLite'], category: 'Logistics', icon: Package, highlight: 'Cross-platform desktop + mobile delivery' },
    { name: 'Entropy Agent', description: 'Enterprise AI Agent platform with multi-model orchestration', tech: ['Python', 'FastAPI', 'LangChain', 'Docker'], category: 'AI Platform', icon: Bot, highlight: 'Multi-model AI agent orchestration architecture' },
    { name: 'Entropy Chat', description: 'Enterprise AI chat with multi-model switching and knowledge base', tech: ['Vue.js', 'Go', 'Redis', 'Docker'], category: 'AI Chat', icon: MessageSquare, highlight: 'Multi-model + knowledge base complete chat system' },
    { name: 'Entropy Tech Website', description: 'Corporate website showcasing products and team', tech: ['React', 'Vite', 'Tailwind CSS'], category: 'Corporate', icon: Globe, highlight: 'Brand-focused design + responsive layout' },
    { name: 'Entropy Agent Landing', description: 'Dark-themed single-page landing for enterprises and developers', tech: ['React', 'Tailwind CSS', 'Framer Motion'], category: 'Landing Page', icon: FileText, highlight: 'Conversion-optimized landing page design' },
    { name: 'AI Reconciliation Tool', description: 'Smart financial reconciliation with automatic data matching', tech: ['Python', 'FastAPI', 'PostgreSQL'], category: 'Finance', icon: Layers, highlight: 'Automated financial data processing pipeline' },
    { name: 'Asia Travel Management', description: 'Travel agency management covering orders, customers, itineraries', tech: ['Go', 'Vue.js', 'PostgreSQL', 'Docker'], category: 'Travel', icon: Plane, highlight: 'Complex business flow spec decomposition' },
    { name: 'Sales Champion Trainer', description: 'AI sales training system simulating real scenarios', tech: ['React', 'Python', 'AI/ML', 'WebSocket'], category: 'Education', icon: Briefcase, highlight: 'AI simulation training interaction design' },
    { name: 'Sensitive Word Filter', description: 'High-performance text sensitive word detection service', tech: ['Python', 'FastAPI', 'Redis'], category: 'Security', icon: Search, highlight: 'High-performance text processing architecture' },
    { name: 'Meiluu', description: 'Beauty industry management - online booking and membership', tech: ['Python', 'FastAPI', 'PostgreSQL', 'Docker'], category: 'Industry SaaS', icon: ShoppingCart, highlight: 'Complete industry SaaS delivery pipeline' },
    { name: 'Image Processing Tool', description: 'Online image editing and batch processing tool', tech: ['React', 'TypeScript', 'Vite', 'Canvas'], category: 'Utilities', icon: Image, highlight: 'Frontend-first tool product delivery' },
    { name: 'Super Dev Website', description: 'The website you are browsing - also a Super Dev pipeline deliverable', tech: ['Next.js', 'Tailwind CSS', 'TypeScript', 'GitHub Pages'], category: 'Official Site', icon: Monitor, highlight: 'Full 9-stage pipeline + quality gate practice' },
    { name: 'Contract Generator', description: 'Software development contract auto-generation and management', tech: ['Python', 'FastAPI', 'Jinja2'], category: 'Legal Tools', icon: FileText, highlight: 'Template-based document automation pipeline' },
  ],
};

const COPY = {
  zh: {
    eyebrow: 'Showcase',
    title: '用 Super Dev 交付的真实项目',
    body: '这些项目均使用 Super Dev 流水线完成从需求研究到交付部署的完整过程。覆盖社交、金融、医疗、物流、AI、企业管理等多个行业。',
    stats: { label1: '交付项目', label2: '覆盖行业', label3: '平均质量分' },
    techLabel: '技术栈',
  },
  en: {
    eyebrow: 'Showcase',
    title: 'Real projects delivered with Super Dev',
    body: 'These projects were built using the full Super Dev pipeline - from requirement research to deployment. Covering social, finance, healthcare, logistics, AI, enterprise management, and more.',
    stats: { label1: 'Projects', label2: 'Industries', label3: 'Avg Quality' },
    techLabel: 'Tech Stack',
  },
} as const;

export function ShowcasePageContent({ locale = 'zh' }: { locale?: SiteLocale }) {
  const copy = COPY[locale];
  const projects = PROJECTS[locale];

  return (
    <>
      <Nav locale={locale} />
      <main className="pt-14 min-h-screen" id="main-content">
        {/* Hero */}
        <section className="section-glow py-20 lg:py-28 bg-bg-primary" aria-labelledby="showcase-title">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
            <p className="text-accent-blue text-sm font-mono font-semibold tracking-widest uppercase mb-4">{copy.eyebrow}</p>
            <h1 id="showcase-title" className="text-4xl md:text-5xl font-bold text-text-primary mb-6 tracking-tight">{copy.title}</h1>
            <p className="text-text-secondary text-lg max-w-2xl mx-auto mb-12">{copy.body}</p>

            <div className="flex justify-center gap-12 mb-16">
              <div className="text-center">
                <div className="text-3xl font-bold font-mono text-accent-blue">{projects.length}+</div>
                <div className="text-sm text-text-muted mt-1">{copy.stats.label1}</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold font-mono text-accent-blue">12</div>
                <div className="text-sm text-text-muted mt-1">{copy.stats.label2}</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold font-mono text-accent-blue">92</div>
                <div className="text-sm text-text-muted mt-1">{copy.stats.label3}</div>
              </div>
            </div>
          </div>
        </section>

        {/* Project Grid */}
        <section className="py-16 lg:py-20 bg-bg-secondary border-t border-border-muted">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {projects.map((project) => {
                const Icon = project.icon;
                return (
                  <article
                    key={project.name}
                    className="group relative rounded-2xl border border-border-default bg-bg-primary p-5 transition-all duration-300 hover:border-accent-blue/50 hover:shadow-lg hover:shadow-accent-blue/5 hover:-translate-y-1"
                  >
                    <div className="flex items-start gap-3 mb-3">
                      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-accent-blue/10 border border-accent-blue/20 flex items-center justify-center transition-colors duration-300 group-hover:bg-accent-blue/20">
                        <Icon size={20} className="text-accent-blue" aria-hidden="true" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-bold text-text-primary truncate">{project.name}</h3>
                        <Badge variant="compatible">{project.category}</Badge>
                      </div>
                    </div>

                    <p className="text-sm text-text-secondary mb-3 line-clamp-2">{project.description}</p>

                    <div className="rounded-lg bg-accent-blue/5 border border-accent-blue/10 px-3 py-1.5 mb-3">
                      <p className="text-xs text-accent-blue font-medium">{project.highlight}</p>
                    </div>

                    <div>
                      <p className="text-xs text-text-muted mb-1.5">{copy.techLabel}</p>
                      <div className="flex flex-wrap gap-1">
                        {project.tech.map((t) => (
                          <span key={t} className="px-1.5 py-0.5 rounded bg-bg-tertiary text-xs text-text-secondary font-mono">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 bg-bg-primary border-t border-border-muted">
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
            <h2 className="text-2xl font-bold text-text-primary mb-4">
              {locale === 'zh' ? '用 Super Dev 开始你的下一个项目' : 'Start your next project with Super Dev'}
            </h2>
            <p className="text-text-secondary mb-8">
              {locale === 'zh'
                ? '只需一条命令，即可获得完整的研究、文档、实现、质量和交付流水线。'
                : 'One command gives you a complete research, documentation, implementation, quality, and delivery pipeline.'}
            </p>
            <code className="inline-block px-4 py-2 rounded-lg bg-bg-tertiary border border-border-default font-mono text-sm text-accent-blue">
              uv tool install super-dev
            </code>
          </div>
        </section>
      </main>
      <Footer locale={locale} />
    </>
  );
}
