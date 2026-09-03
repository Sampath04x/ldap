import type {
  User, Group, IPMapping, AuthEvent, Firewall, LDAPServer,
  DiagnosticRun, SearchResult, PagedResponse, KeysetResponse, HealthResponse
} from './types'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public code: string, message: string, public request_id?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    if (errorData?.error) {
      throw new ApiError(errorData.error.code, errorData.error.message, errorData.error.request_id)
    }
    throw new ApiError('UNKNOWN_ERROR', `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

// User endpoints
export const getUser = (username: string) => apiFetch<User>(`/api/v1/users/${username}`)
export const getUserGroups = (username: string) => apiFetch<Group[]>(`/api/v1/users/${username}/groups`)
export const getUserMappings = (username: string) => apiFetch<IPMapping[]>(`/api/v1/users/${username}/mappings`)
export const getUserEvents = (username: string, params?: { after_id?: number, after_ts?: string, result?: string, page_size?: number }) => {
  const query = new URLSearchParams()
  if (params?.after_id) query.append('after_id', String(params.after_id))
  if (params?.after_ts) query.append('after_ts', params.after_ts)
  if (params?.result) query.append('result', params.result)
  if (params?.page_size) query.append('page_size', String(params.page_size))
  const qs = query.toString()
  return apiFetch<KeysetResponse<AuthEvent>>(`/api/v1/users/${username}/events${qs ? `?${qs}` : ''}`)
}

// Firewall endpoints
export const getFirewall = (id: string) => apiFetch<Firewall>(`/api/v1/firewalls/${id}`)
export const getFirewalls = (params?: { status?: string, page?: number }) => {
  const query = new URLSearchParams()
  if (params?.status) query.append('status', params.status)
  if (params?.page) query.append('page', String(params.page))
  const qs = query.toString()
  return apiFetch<PagedResponse<Firewall>>(`/api/v1/firewalls${qs ? `?${qs}` : ''}`)
}
export const getFirewallLDAP = (id: string) => apiFetch<LDAPServer[]>(`/api/v1/firewalls/${id}/ldap`)

// Diagnostic endpoints
export const runUserDiagnostic = (firewall_id: string, username: string) => apiFetch<DiagnosticRun>('/api/v1/diagnostics/user', {
  method: 'POST',
  body: JSON.stringify({ firewall_id, username })
})
export const getDiagnosticRun = (run_id: string) => apiFetch<DiagnosticRun>(`/api/v1/diagnostics/${run_id}`)

// Search
export const search = (params: { q: string, type?: string, field?: string, status?: string, page?: number, page_size?: number }) => {
  const query = new URLSearchParams()
  query.append('q', params.q)
  if (params.type) query.append('type', params.type)
  if (params.field) query.append('field', params.field)
  if (params.status) query.append('status', params.status)
  if (params.page) query.append('page', String(params.page))
  if (params.page_size) query.append('page_size', String(params.page_size))
  return apiFetch<SearchResult>(`/api/v1/search?${query.toString()}`)
}

// Health
export const getHealth = () => apiFetch<HealthResponse>('/api/v1/health')
