'use client'

import { useParams } from 'next/navigation'
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getFirewalls, runUserDiagnostic } from '@/lib/api'
import { DiagnosticPanel } from '@/components/DiagnosticPanel'
import { Skeleton } from '@/components/Skeleton'
import { ErrorState } from '@/components/ErrorState'
import { Play } from 'lucide-react'
import Link from 'next/link'

export default function DiagnosticPage() {
  const { username } = useParams()
  const uid = typeof username === 'string' ? username : ''
  const [selectedFirewall, setSelectedFirewall] = useState('')

  const { data: firewallsData, isLoading: firewallsLoading } = useQuery({
    queryKey: ['firewalls'],
    queryFn: () => getFirewalls({ page: 1 }),
  })

  const runMutation = useMutation({
    mutationFn: () => runUserDiagnostic(selectedFirewall, uid),
  })

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
        <Link href={`/users/${uid}`} className="hover:underline text-blue-600">{uid}</Link>
        <span>/</span>
        <span className="text-gray-900">Diagnostics</span>
      </div>

      <div className="bg-white p-6 rounded-xl border shadow-sm space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Run Diagnostic for {uid}</h1>
          <p className="text-gray-500 mt-1">Check authentication and identity state on a specific firewall.</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Firewall</label>
            {firewallsLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <select
                data-testid="firewall-select"
                value={selectedFirewall}
                onChange={e => setSelectedFirewall(e.target.value)}
                className="w-full h-10 px-3 py-2 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="" disabled>Select a firewall...</option>
                {firewallsData?.items.map(fw => (
                  <option key={fw.id} value={fw.id}>{fw.hostname} ({fw.ip_address})</option>
                ))}
              </select>
            )}
          </div>
          <button
            data-testid="run-diagnostic-submit"
            disabled={!selectedFirewall || runMutation.isPending}
            onClick={() => runMutation.mutate()}
            className="h-10 px-6 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {runMutation.isPending ? (
              <span className="animate-pulse">Running...</span>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Run Now</span>
              </>
            )}
          </button>
        </div>
      </div>

      {runMutation.isError && (
        <ErrorState message={runMutation.error?.message || 'Failed to run diagnostic'} onRetry={() => runMutation.mutate()} />
      )}

      {runMutation.data && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <DiagnosticPanel run={runMutation.data} />
        </div>
      )}
    </div>
  )
}
