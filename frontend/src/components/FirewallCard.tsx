import type { Firewall } from '@/lib/types'
import { HealthBadge } from './HealthBadge'
import Link from 'next/link'
import { Server } from 'lucide-react'

export function FirewallCard({ firewall }: { firewall: Firewall }) {
  return (
    <Link href={`/firewalls/${firewall.id}`} data-testid="search-result-firewall" className="block bg-white border rounded-xl p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-4">
        <div className="w-12 h-12 rounded-lg bg-gray-100 text-gray-700 flex items-center justify-center flex-shrink-0">
          <Server className="w-6 h-6" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <h3 className="text-lg font-semibold text-gray-900 truncate">{firewall.hostname}</h3>
            <HealthBadge status={firewall.status} />
          </div>
          <div className="text-sm text-gray-500 mt-1 space-x-2">
            <span className="px-2 py-0.5 bg-gray-100 rounded text-xs uppercase">{firewall.environment}</span>
            <span>{firewall.ip_address}</span>
          </div>
          {firewall.model && (
            <div className="text-sm text-gray-500 mt-1">
              Model: {firewall.model} {firewall.location ? `| Loc: ${firewall.location}` : ''}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
