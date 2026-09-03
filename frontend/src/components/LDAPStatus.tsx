import type { LDAPServer } from '@/lib/types'
import { HealthBadge } from './HealthBadge'
import { Lock, Unlock } from 'lucide-react'

export function LDAPStatus({ server }: { server: LDAPServer }) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-semibold text-gray-900">{server.profile_name}</h4>
        <HealthBadge status={server.status} />
      </div>
      <div className="text-sm text-gray-600 mb-2 font-mono">
        {server.server_host}:{server.server_port}
      </div>
      <div className="flex items-center space-x-2 text-sm text-gray-500 mb-3">
        {server.use_tls ? (
          <><Lock className="w-4 h-4 text-green-600" /> <span className="text-green-700">TLS Enabled</span></>
        ) : (
          <><Unlock className="w-4 h-4 text-orange-500" /> <span className="text-orange-600">No TLS</span></>
        )}
      </div>
      <div className="text-xs text-gray-400">
        Last checked: {server.last_checked_at ? new Date(server.last_checked_at).toLocaleString() : 'Never'}
      </div>
    </div>
  )
}
