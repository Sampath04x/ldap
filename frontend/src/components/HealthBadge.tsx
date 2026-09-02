import { clsx } from 'clsx'

export function HealthBadge({ status, size = 'md' }: { status: string; size?: 'sm' | 'md' | 'lg' }) {
  const norm = status.toLowerCase()
  
  let colorClass = 'bg-status-unknown text-white'
  if (['reachable', 'active', 'healthy', 'success'].includes(norm)) colorClass = 'bg-status-healthy text-white'
  else if (['unreachable', 'failed', 'error'].includes(norm)) colorClass = 'bg-status-failed text-white'
  else if (['degraded', 'stale', 'inactive', 'timeout'].includes(norm)) colorClass = 'bg-status-degraded text-white'
  
  const sizeClass = {
    sm: 'text-[10px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5'
  }[size]

  return (
    <span data-testid={`status-badge-${norm}`} className={clsx('inline-flex items-center rounded-full font-medium uppercase tracking-wider', colorClass, sizeClass)}>
      {status}
    </span>
  )
}
