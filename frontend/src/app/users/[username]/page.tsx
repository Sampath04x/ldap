'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { getUser, getUserGroups, getUserMappings, getUserEvents } from '../../lib/api'
import { HealthBadge } from '../../components/HealthBadge'
import { GroupList } from '../../components/GroupList'
import { IPMappingTable } from '../../components/IPMappingTable'
import { AuthEventFeed } from '../../components/AuthEventFeed'
import { Skeleton } from '../../components/Skeleton'
import { ErrorState } from '../../components/ErrorState'
import Link from 'next/link'
import { ShieldAlert, Mail, Briefcase, MapPin, Calendar } from 'lucide-react'

export default function UserDetailPage() {
  const { username } = useParams()
  const uid = typeof username === 'string' ? username : ''

  const { data: user, isLoading, isError, refetch } = useQuery({
    queryKey: ['user', uid],
    queryFn: () => getUser(uid),
  })

  const { data: groups } = useQuery({
    queryKey: ['user', uid, 'groups'],
    queryFn: () => getUserGroups(uid),
    enabled: !!user,
  })

  const { data: mappings } = useQuery({
    queryKey: ['user', uid, 'mappings'],
    queryFn: () => getUserMappings(uid),
    enabled: !!user,
  })

  const { data: events } = useQuery({
    queryKey: ['user', uid, 'events'],
    queryFn: () => getUserEvents(uid, { page_size: 20 }),
    enabled: !!user,
  })

  if (isLoading) return <Skeleton className="h-64 w-full" />
  if (isError) return <ErrorState message="Failed to load user details" onRetry={() => refetch()} />
  if (!user) return null

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div className="bg-white border rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <div className="flex items-center space-x-4 mb-2">
            <h1 className="text-3xl font-bold text-gray-900" data-testid="user-display-name">{user.display_name}</h1>
            <HealthBadge status={user.status} size="lg" />
          </div>
          <div className="text-lg text-gray-500 font-mono mb-4">@{user.username}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-3 text-sm text-gray-600">
            <div className="flex items-center space-x-2"><Mail className="w-4 h-4" /> <span>{user.email}</span></div>
            {user.job_title && <div className="flex items-center space-x-2"><Briefcase className="w-4 h-4" /> <span>{user.job_title}</span></div>}
            {user.location && <div className="flex items-center space-x-2"><MapPin className="w-4 h-4" /> <span>{user.location}</span></div>}
            <div className="flex items-center space-x-2"><Calendar className="w-4 h-4" /> <span>Created {new Date(user.created_at).toLocaleDateString()}</span></div>
          </div>
          {user.ldap_dn && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg border text-xs font-mono break-all text-gray-500">
              {user.ldap_dn}
            </div>
          )}
        </div>
        <Link 
          href={`/users/${user.username}/diagnostics`} 
          data-testid="run-diagnostic-btn"
          className="bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2 whitespace-nowrap"
        >
          <ShieldAlert className="w-5 h-5" />
          <span>Run Diagnostic</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900">IP Mappings</h2>
            {mappings ? <IPMappingTable mappings={mappings} /> : <Skeleton className="h-32" />}
          </section>
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900">Recent Auth Events</h2>
            {events ? <AuthEventFeed events={events} /> : <Skeleton className="h-64" />}
          </section>
        </div>
        <div className="space-y-8">
          <section className="bg-white border rounded-xl p-5 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 text-gray-900">Group Memberships</h2>
            {groups ? <GroupList groups={groups} /> : <Skeleton className="h-24" />}
          </section>
        </div>
      </div>
    </div>
  )
}
