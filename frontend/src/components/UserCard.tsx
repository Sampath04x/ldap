import type { User } from '../../lib/types'
import { HealthBadge } from './HealthBadge'
import Link from 'next/link'
import { User as UserIcon } from 'lucide-react'

export function UserCard({ user }: { user: User }) {
  const initials = user.display_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
  return (
    <Link href={`/users/${user.username}`} data-testid="search-result-user" className="block bg-white border rounded-xl p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-4">
        <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg flex-shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <h3 className="text-lg font-semibold text-gray-900 truncate">{user.display_name}</h3>
            <HealthBadge status={user.status} />
          </div>
          <div className="text-sm text-gray-500 mt-1 flex items-center space-x-2">
            <UserIcon className="w-4 h-4" />
            <span className="truncate">{user.username}</span>
            <span>&bull;</span>
            <span className="truncate">{user.email}</span>
          </div>
          {user.department && (
            <div className="text-sm text-gray-500 mt-1">
              Dept: {user.department}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
