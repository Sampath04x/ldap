'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFirewalls } from '@/lib/api'
import { FirewallCard } from '@/components/FirewallCard'
import { Skeleton } from '@/components/Skeleton'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { Server } from 'lucide-react'

export default function FirewallsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState<number>(1)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['firewalls', statusFilter, page],
    queryFn: () => getFirewalls({ 
      status: statusFilter === 'all' ? undefined : statusFilter, 
      page, 
      page_size: 12 
    }),
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b pb-4 gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
            <Server className="w-7 h-7 text-gray-700" />
            <span>Firewall Roster</span>
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Overview of protected Palo Alto Next-Generation Firewalls and LDAP connectors.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-gray-100 p-1 rounded-lg">
          {['all', 'reachable', 'unreachable', 'degraded'].map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1) }}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                statusFilter === s ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      )}

      {isError && (
        <ErrorState message="Failed to load firewall list" onRetry={() => refetch()} />
      )}

      {data && data.items.length === 0 && (
        <EmptyState 
          message="No firewalls found" 
          description={statusFilter !== 'all' ? `No firewalls matching status '${statusFilter}'` : "No firewalls registered in database."} 
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.items.map((fw) => (
              <FirewallCard key={fw.id} firewall={fw} />
            ))}
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between border-t pt-4 text-sm text-gray-600 font-medium">
            <span>
              Page {data.page} {data.total ? `of ${Math.ceil(data.total / data.page_size)} (${data.total} total)` : ''}
            </span>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="px-3 py-1.5 border rounded-lg hover:bg-gray-50 disabled:opacity-50 text-xs font-semibold"
              >
                Previous
              </button>
              <button
                disabled={!data.has_more}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1.5 border rounded-lg hover:bg-gray-50 disabled:opacity-50 text-xs font-semibold"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
