import type { Metadata } from 'next'
import { Providers } from './providers'
import './globals.css'
import Link from 'next/link'
import { Home, Search, Server } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Firewall Identity Platform',
  description: 'Enterprise Firewall Identity & LDAP Diagnostics Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 flex min-h-screen">
        <Providers>
          <aside className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-gray-300 flex flex-col">
            <div className="p-4 bg-gray-950 text-white font-semibold text-lg flex items-center justify-between border-b border-gray-800">
              <span>Firewall Identity</span>
              <span className="text-xs bg-gray-800 px-2 py-1 rounded">v1.0</span>
            </div>
            <nav className="flex-1 p-4 space-y-2">
              <Link href="/" className="flex items-center space-x-3 px-3 py-2 rounded-md hover:bg-gray-800 hover:text-white transition-colors">
                <Home className="w-5 h-5" />
                <span>Dashboard</span>
              </Link>
              <Link href="/search?q=" className="flex items-center space-x-3 px-3 py-2 rounded-md hover:bg-gray-800 hover:text-white transition-colors">
                <Search className="w-5 h-5" />
                <span>Search</span>
              </Link>
              <Link href="/firewalls" className="flex items-center space-x-3 px-3 py-2 rounded-md hover:bg-gray-800 hover:text-white transition-colors">
                <Server className="w-5 h-5" />
                <span>Firewalls</span>
              </Link>
            </nav>
          </aside>
          <main className="ml-64 flex-1 flex flex-col min-h-screen">
            <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
              <h1 className="text-xl font-semibold">Platform Operations</h1>
            </header>
            <div className="flex-1 p-6">
              {children}
            </div>
          </main>
        </Providers>
      </body>
    </html>
  )
}
