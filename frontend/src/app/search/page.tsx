'use client'

import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { search } from '@/lib/api'
import { UserCard } from '@/components/UserCard'
import { FirewallCard } from '@/components/FirewallCard'
import { Skeleton } from '@/components/Skeleton'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { useState } from 'react'
export default function SearchPage() {
  const searchParams = useSearchParams()
  const q = searchParams.get('q') || ''
  const [filter, setFilter] = useState<'all' | 'user' | 'firewall' | 'group'>('all')
  const [order, setOrder] = useState<'asc' | 'desc'>('asc')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['search', q, filter, order],
    queryFn: () => search({ q, type: filter === 'all' ? undefined : filter, order }),
    enabled: !!q,
  })

  if (!q) {
    return <EmptyState message="Enter a search term" />
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b pb-4 gap-4">
        <h2 className="text-2xl font-bold">Search Results for "{q}"</h2>
        <div className="flex items-center space-x-3 flex-wrap gap-2">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
            {['all', 'user', 'firewall', 'group'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f as any)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                  filter === f ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <select
            value={order}
            onChange={(e) => setOrder(e.target.value as 'asc' | 'desc')}
            className="text-xs bg-white border border-gray-300 rounded-lg px-2.5 py-1.5 font-medium shadow-sm"
          >
            <option value="asc">Sort: A-Z (Ascending)</option>
            <option value="desc">Sort: Z-A (Descending)</option>
          </select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
      )}

      {isError && (
        <ErrorState message="Failed to load search results" onRetry={() => refetch()} />
      )}

      {data && data.items.length === 0 && (
        <EmptyState message={`No results found for "${q}"`} description="Try adjusting your search terms or filters." />
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-4">
          {data.items.map((item, idx) => {
            if (item.type === 'user') return <UserCard key={idx} user={item.data as any} />
            if (item.type === 'firewall') return <FirewallCard key={idx} firewall={item.data as any} />
            // Minimal handling for group as it wasn't explicitly asked for a standalone card, just listing
            return (
              <div key={idx} className="bg-white p-4 border rounded-xl">
                <span className="text-xs font-semibold uppercase text-gray-500">{item.type}</span>
                <pre className="text-sm mt-2">{JSON.stringify(item.data, null, 2)}</pre>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
