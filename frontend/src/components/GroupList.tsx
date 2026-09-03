import type { Group } from '@/lib/types'
import { Users } from 'lucide-react'

export function GroupList({ groups }: { groups: Group[] }) {
  if (groups.length === 0) return <div className="text-gray-500 italic text-sm">No groups</div>

  return (
    <div className="flex flex-wrap gap-2">
      {groups.map(g => (
        <div key={g.id} className="inline-flex items-center space-x-1.5 bg-gray-100 border border-gray-200 rounded-md px-2.5 py-1 text-sm text-gray-800">
          <Users className="w-3.5 h-3.5 text-gray-500" />
          <span>{g.group_name}</span>
          <span className={`w-2 h-2 rounded-full ${g.status === 'active' ? 'bg-status-healthy' : 'bg-gray-400'}`} title={g.status} />
        </div>
      ))}
    </div>
  )
}
