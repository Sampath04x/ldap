export type UserStatus = 'active' | 'inactive' | 'disabled' | 'locked'
export type FirewallStatus = 'reachable' | 'unreachable' | 'degraded' | 'unknown'
export type DiagnosticOverallStatus = 'HEALTHY' | 'DEGRADED' | 'FAILED'
export type DiagnosticSeverity = 'info' | 'medium' | 'high' | 'critical'

export interface User {
  id: string
  username: string
  email: string
  display_name: string
  department: string | null
  job_title: string | null
  location: string | null
  status: UserStatus
  ldap_dn: string | null
  created_at: string
  updated_at: string
}

export interface Group {
  id: string
  group_name: string
  display_name: string | null
  description: string | null
  status: 'active' | 'disabled'
}

export interface Firewall {
  id: string
  hostname: string
  ip_address: string
  model: string | null
  software_version: string | null
  environment: 'production' | 'staging' | 'lab'
  location: string | null
  status: FirewallStatus
  last_seen_at: string | null
  created_at: string
  updated_at: string
}

export interface LDAPServer {
  id: string
  firewall_id: string
  profile_name: string
  server_host: string
  server_port: number
  use_tls: boolean
  base_dn: string | null
  bind_dn: string | null
  status: 'reachable' | 'unreachable' | 'tls_error' | 'misconfigured' | 'unknown'
  last_checked_at: string | null
}

export interface IPMapping {
  id: number
  user_id: string
  firewall_id: string
  ip_address: string
  mapped_at: string
  expires_at: string | null
  is_current: boolean
  source: string | null
}

export interface AuthEvent {
  id: number
  user_id: string | null
  firewall_id: string
  username_raw: string
  source_ip: string | null
  result: 'success' | 'failure' | 'timeout' | 'unknown'
  failure_reason: string | null
  auth_method: string | null
  occurred_at: string
}

export interface DiagnosticCheck {
  name: string
  passed: boolean
  code: string
  severity: DiagnosticSeverity
  detail: string
  action: string | null
}

export interface DiagnosticRun {
  run_id: string
  subject: string
  firewall: string
  overall_result: string
  overall_status: DiagnosticOverallStatus
  duration_ms: number
  checks: DiagnosticCheck[]
  summary: string
  created_at: string
}

export interface SearchItem {
  type: 'user' | 'firewall' | 'group'
  score: number
  data: User | Firewall | Group
}

export interface SearchResult {
  items: SearchItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface PagedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface HealthResponse {
  status: string
  db_connected: boolean
  provider: string
  version: string
}

export interface ApiError {
  error: {
    code: string
    message: string
    request_id?: string
  }
}
