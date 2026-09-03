import type { IPMapping } from '@/lib/types'
import { EmptyState } from './EmptyState'

function formatAge(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  return `${Math.floor(hrs / 24)}d`
}

export function IPMappingTable({ mappings }: { mappings: IPMapping[] }) {
  if (mappings.length === 0) return <EmptyState message="No IP mappings found" />

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">IP Address</th>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Firewall</th>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Source</th>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Mapped At</th>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Age</th>
            <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Current</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {mappings.map(m => (
            <tr key={m.id}>
              <td className="px-6 py-4 whitespace-nowrap font-medium">{m.ip_address}</td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-500">{m.firewall_id}</td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-500">{m.source || '-'}</td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-500">{new Date(m.mapped_at).toLocaleString()}</td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                {formatAge(m.mapped_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {m.is_current ? (
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-medium">Yes</span>
                ) : (
                  <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full font-medium">No</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
