/**
 * 开发：Excellent（11964948@qq.com）
 * 功能：徽章组件
 * 作用：显示版本号、状态标签、分类标识
 * 创建时间：2026-03-08
 * 最后修改：2026-03-08
 */
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'certified' | 'compatible' | 'experimental' | 'version';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-bg-tertiary text-text-secondary border-border-default',
  certified: 'bg-status-green/10 text-status-green border-status-green/30',
  compatible: 'bg-status-yellow/10 text-status-yellow border-status-yellow/30',
  experimental: 'bg-status-yellow/10 text-status-yellow border-status-yellow/30',
  version: 'bg-bg-secondary text-text-secondary border-border-default',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 whitespace-nowrap items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
