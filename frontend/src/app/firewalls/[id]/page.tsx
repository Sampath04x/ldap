'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { getFirewall, getFirewallLDAP } from '@/lib/api'
import { HealthBadge } from '@/components/HealthBadge'
import { LDAPStatus } from '@/components/LDAPStatus'
import { Skeleton } from '@/components/Skeleton'
import { ErrorState } from '@/components/ErrorState'
import { Server, Activity, Network } from 'lucide-react'

export default function FirewallDetailPage() {
  const { id } = useParams()
  const fwid = typeof id === 'string' ? id : ''

  const { data: firewall, isLoading, isError, refetch } = useQuery({
    queryKey: ['firewall', fwid],
    queryFn: () => getFirewall(fwid),
  })

  const { data: ldapServers } = useQuery({
    queryKey: ['firewall', fwid, 'ldap'],
    queryFn: () => getFirewallLDAP(fwid),
    enabled: !!firewall,
  })

  if (isLoading) return <Skeleton className="h-64 w-full" />
  if (isError) return <ErrorState message="Failed to load firewall details" onRetry={() => refetch()} />
  if (!firewall) return null

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      <div className="bg-white border rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 bg-gray-100 rounded-xl flex items-center justify-center">
              <Server className="w-8 h-8 text-gray-700" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{firewall.hostname}</h1>
              <div className="text-gray-500 mt-1 flex items-center space-x-2">
                <span className="font-mono">{firewall.ip_address}</span>
                <span>&bull;</span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-xs uppercase">{firewall.environment}</span>
              </div>
            </div>
          </div>
          <HealthBadge status={firewall.status} size="lg" />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-6 border-t border-gray-100">
          <div>
            <div className="text-sm text-gray-500 mb-1 flex items-center"><Activity className="w-4 h-4 mr-1" /> Model</div>
            <div className="font-medium text-gray-900">{firewall.model || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1 flex items-center"><Network className="w-4 h-4 mr-1" /> Version</div>
            <div className="font-medium text-gray-900">{firewall.software_version || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Location</div>
            <div className="font-medium text-gray-900">{firewall.location || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Last Seen</div>
            <div className="font-medium text-gray-900">{firewall.last_seen_at ? new Date(firewall.last_seen_at).toLocaleString() : 'Never'}</div>
          </div>
        </div>
      </div>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-gray-900">LDAP Configuration</h2>
        {ldapServers ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ldapServers.length > 0 ? (
              ldapServers.map(server => <LDAPStatus key={server.id} server={server} />)
            ) : (
              <div className="col-span-full p-8 text-center text-gray-500 bg-gray-50 border rounded-xl">
                No LDAP profiles configured for this firewall.
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
        )}
      </section>
    </div>
  )
}
