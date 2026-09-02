'use client'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../../lib/api'
import { Search, ShieldAlert, Server, Users, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function Home() {
  const router = useRouter()
  const [query, setQuery] = useState('')

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query)}`)
    }
  }

  return (
    <div className="max-w-5xl mx-auto mt-8 space-y-12 pb-12">
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">Enterprise Identity & LDAP Diagnostics</h1>
        <p className="text-gray-500 text-lg max-w-2xl mx-auto">Automate Palo Alto firewall identity mappings and LDAP group diagnostics.</p>
      </div>

      <form onSubmit={handleSearch} className="relative max-w-3xl mx-auto">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search username (e.g. usr_0000001), IP, hostname, or group..."
            className="w-full pl-14 pr-32 py-4 rounded-xl border border-gray-300 shadow-md text-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 bg-gray-900 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-gray-800 transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      {/* Quick Action Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/search?q=usr&type=user" className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Users className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-gray-900 text-lg flex items-center justify-between">
            <span>Lookup Users</span>
            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
          </h3>
          <p className="text-sm text-gray-500 mt-2">Inspect user identities, IP mappings, and Active Directory group memberships.</p>
        </Link>

        <Link href="/search?q=fw&type=firewall" className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Server className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-gray-900 text-lg flex items-center justify-between">
            <span>Firewall Roster</span>
            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
          </h3>
          <p className="text-sm text-gray-500 mt-2">View Palo Alto firewall cluster health, software versions, and LDAP server profiles.</p>
        </Link>

        <Link href="/search?q=usr_0000001&type=user" className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-gray-900 text-lg flex items-center justify-between">
            <span>Run Diagnostic</span>
            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
          </h3>
          <p className="text-sm text-gray-500 mt-2">Execute 9-check automated identity & group mapping diagnostic workflow.</p>
        </Link>
      </div>

      {/* System Status Dashboard */}
      {health && (
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
          <h3 className="text-xs uppercase font-bold text-gray-400 tracking-wider mb-4">Platform Operational Health</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="flex items-center space-x-4">
              <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
              <div>
                <span className="text-xs text-gray-400 block font-semibold">API HEALTH</span>
                <span className="text-sm font-bold text-gray-900">{health.status.toUpperCase()} (v{health.version})</span>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className={`w-3 h-3 rounded-full ${health.db_connected ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <div>
                <span className="text-xs text-gray-400 block font-semibold">DATABASE CONNECTIVITY</span>
                <span className="text-sm font-bold text-gray-900">{health.db_connected ? 'PostgreSQL Active' : 'Disconnected'}</span>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <div>
                <span className="text-xs text-gray-400 block font-semibold">IDENTITY PROVIDER</span>
                <span className="text-sm font-bold text-gray-900 font-mono">{health.provider.toUpperCase()} PROVIDER</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
