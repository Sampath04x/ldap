import type { AuthEvent } from '../../lib/types'
import { EmptyState } from './EmptyState'
import { HealthBadge } from './HealthBadge'

export function AuthEventFeed({ events }: { events: AuthEvent[] }) {
  if (events.length === 0) return <EmptyState message="No auth events found" />

  return (
    <div className="space-y-3">
      {events.map(ev => (
        <div key={ev.id} className="bg-white border rounded-lg p-3 flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-1">
              <span className="text-sm font-medium text-gray-900">{new Date(ev.occurred_at).toLocaleString()}</span>
              <HealthBadge status={ev.result} size="sm" />
            </div>
            <div className="text-sm text-gray-600 space-x-3">
              {ev.source_ip && <span>IP: {ev.source_ip}</span>}
              {ev.auth_method && <span>Method: {ev.auth_method}</span>}
              <span>FW: {ev.firewall_id}</span>
            </div>
          </div>
          {ev.failure_reason && (
            <div className="text-sm text-red-600 max-w-xs text-right">
              {ev.failure_reason}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
