# Enterprise Firewall Identity & LDAP Diagnostics Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose_v2-blue.svg)](https://www.docker.com/)

An enterprise network-security automation platform designed for datacenter and network operations teams to automate the troubleshooting of Palo Alto firewall identity mappings (User-ID) and Active Directory / LDAP group synchronizations.

---

## 1. Problem Statement

Network and firewall engineers frequently spend hours manually correlating IP-to-User mappings and Active Directory group memberships when troubleshooting security policy enforcement issues. Common failure modes include:

- **Unidentified Users**: User sessions hitting fallback "any/deny" security rules because User-ID mapping is missing or expired.
- **Group Sync Drift**: Security policies failing because firewall group mapping caches are stale or empty due to LDAP connection drops or TLS failures.
- **Identity Inconsistencies**: Conflicting concurrent IP mappings across multiple firewalls causing erratic policy behavior.

This platform automates the 9-step diagnostic sequence an engineer performs manually, producing a deterministic, machine-readable and human-readable diagnosis with exact runtime evidence and recommended remediation actions.

---

## 2. Technical Architecture

The platform uses a clean layered architecture with a completely decoupled diagnostic engine and provider abstraction.

```
                      +-----------------------------+
                      |   Next.js 15 Web Frontend   |
                      |   (Port 3000, App Router)   |
                      +--------------+--------------+
                                     | Direct CORS Fetch
                                     v
                      +-----------------------------+
                      |    FastAPI Backend Server   |
                      |   (Port 8000, OpenAPI Docs) |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+-------------------------------+               +-------------------------------+
|        Search Service         |               |       Diagnostic Engine       |
| (Exact B-Tree & GIN Trigrams) |               |     (9 Sequenced Checks)      |
+---------------+---------------+               +---------------+---------------+
                |                                               |
                |                                               v
                |                               +-------------------------------+
                |                               |     PaloAltoProvider Protocol |
                |                               +---------------+---------------+
                |                                               |
                |                                               v
                |                               +-------------------------------+
                |                               |      MockPaloAltoProvider     |
                +-------------------------------+---------------+---------------+
                                                                |
                                                                v
                                                +-------------------------------+
                                                |     PostgreSQL 16 Database    |
                                                | (10 Tables, COPY STDIN Data)  |
                                                +-------------------------------+
```

---

## 3. Diagnostic Workflow Sequence

The `DiagnosticEngine` executes a deterministic 9-check pipeline. Failure at step 1 or 4 triggers immediate stop-chaining or check skipping to prevent cascading false positives.

```
[ 1. Firewall Reachable? ] ----(NO)----> Stop-Chain (FIREWALL_UNREACHABLE / FAILED)
           | (YES)
[ 2. User Identity Active? ] --(NO)----> Flag USER_NOT_FOUND or USER_NOT_IDENTIFIED
           | (YES)
[ 3. IP Mapping Active? ] -----(NO)----> Flag IP_MAPPING_MISSING or IDENTITY_MAPPING_STALE
           | (YES)
[ 4. LDAP Configured? ] -------(NO)----> Flag LDAP_NOT_CONFIGURED & Skip Steps 5-7
           | (YES)
[ 5. LDAP Connectivity? ] -----(NO)----> Flag LDAP_UNREACHABLE or LDAP_TLS_FAILURE
           | (YES)
[ 6. User Groups Retrieved? ] -(NO)----> Flag GROUP_MAPPING_EMPTY
           | (YES)
[ 7. Group Mapping Fresh? ] ---(NO)----> Flag GROUP_MAPPING_STALE
           | (YES)
[ 8. Recent Auth Failures? ] --(YES)---> Flag AUTHENTICATION_FAILURE
           | (NO)
[ 9. Identity Consistent? ] ---(NO)----> Flag IDENTITY_INCONSISTENT
           | (YES)
     [ IDENTITY_HEALTHY ]
```

---

## 4. Quick Start & Environment Setup

### Prerequisites
- Docker Desktop with Docker Compose v2

### Step 1: Configure Environment
```bash
cp .env.example .env
```

### Step 2: Launch Platform Containers
```bash
docker compose up -d --build
```

### Step 3: Run Database Migrations
```bash
docker compose exec backend alembic upgrade head
```

### Step 4: Seed Synthetic Dataset
```bash
# Seed development dataset (1,000 users, 50,000 auth events) in ~10s
docker compose exec backend python -m data_generator.generate --preset dev --seed 42
```

### Step 5: Access Applications
- **Web UI Platform**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. API Reference

All responses enforce a standardized JSON envelope structure.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Liveness & database connectivity check |
| `GET` | `/api/v1/search?q={query}&type={type}` | Unified search (exact B-tree + GIN trigram) |
| `GET` | `/api/v1/users/{username}` | Fetch user identity profile |
| `GET` | `/api/v1/users/{username}/groups` | List Active Directory group memberships |
| `GET` | `/api/v1/users/{username}/mappings` | Fetch User-ID IP mapping history |
| `GET` | `/api/v1/users/{username}/events` | Keyset-paginated authentication log history |
| `GET` | `/api/v1/firewalls` | List managed firewalls |
| `GET` | `/api/v1/firewalls/{id}` | Fetch firewall details |
| `GET` | `/api/v1/firewalls/{id}/ldap` | List LDAP Server Profiles for a firewall |
| `POST` | `/api/v1/diagnostics/user` | Run 9-check diagnostic engine for user on firewall |
| `GET` | `/api/v1/diagnostics/{run_id}` | Retrieve historical diagnostic run by ID |

---

## 6. Database Schema & Indexing

The PostgreSQL database consists of 10 normalized tables designed for high-throughput operational query performance:

- `users`: Identity accounts (B-tree on `username`, `email`; GIN `pg_trgm` on `username`, `display_name`).
- `groups`: Security & LDAP groups (B-tree on `group_name`; GIN `pg_trgm` on `group_name`).
- `user_group_memberships`: User-to-group mappings (B-tree on `user_id`, `group_id`; UNIQUE constraint).
- `firewalls`: Managed firewall inventory (B-tree on `hostname`; GIN `pg_trgm` on `hostname`).
- `ldap_servers`: Firewall LDAP Server Profiles (B-tree on `firewall_id`).
- `user_ip_mappings`: IP-to-User bindings (B-tree on `ip_address`; Partial UNIQUE index `WHERE is_current = true`).
- `firewall_group_mappings`: Group synchronization state per firewall (B-tree on `firewall_id`).
- `authentication_events`: Auth failure logs (Compound B-tree on `(user_id, occurred_at DESC)` and `(occurred_at DESC, id DESC)` for keyset pagination).
- `diagnostic_runs`: Persisted diagnostic runs & JSON check outputs.
- `audit_logs`: Operations audit log.

---

## 7. Synthetic Data Generator

The generator (`data_generator/generate.py`) uses `psycopg3` `COPY FROM STDIN` streaming to quickly populate large synthetic datasets with realistic 5% failure injection:

| Preset | Users | Groups | Memberships | Firewalls | Auth Events | Generation Time |
|---|---|---|---|---|---|---|
| `dev` | 1,000 | 100 | 10,000 | 20 | 50,000 | ~10s |
| `medium` | 100,000 | 5,000 | 500,000 | 200 | 1,000,000 | ~3 min |
| `large` | 1,000,000 | 20,000 | 5,000,000 | 500 | 10,000,000 | ~20 min |
| `stress` | 5,000,000 | 50,000 | 20,000,000 | 2,000 | 50,000,000 | ~90 min |

---

## 8. Diagnostic Codes & Severity Matrix

| Diagnostic Code | Severity | Meaning & Trigger Condition |
|---|---|---|
| `IDENTITY_HEALTHY` | � | All 9 diagnostic checks passed |
| `FIREWALL_UNREACHABLE` | `critical` | Firewall ping/management interface unreachable |
| `USER_NOT_FOUND` | `critical` | Username not present in identity database |
| `USER_NOT_IDENTIFIED` | `high` | Account is present but in `disabled` or `locked` state |
| `USER_INACTIVE` | `high` | Account status is set to `inactive` |
| `IP_MAPPING_MISSING` | `high` | Zero active IP mappings found for user |
| `IDENTITY_MAPPING_STALE` | `medium` | Active IP mapping exceeds 8h timeout threshold |
| `LDAP_NOT_CONFIGURED` | `high` | Zero LDAP profiles configured on target firewall |
| `LDAP_UNREACHABLE` | `critical` | LDAP server port connection timeout or connection refused |
| `LDAP_TLS_FAILURE` | `critical` | LDAPS / STARTTLS handshake failure or certificate error |
| `GROUP_MAPPING_EMPTY` | `high` / `medium` | Zero group mappings synced to firewall |
| `GROUP_MAPPING_STALE` | `medium` | Firewall group refresh cache exceeds 24h threshold |
| `AUTHENTICATION_FAILURE` | `medium` | 3+ auth failure events in past 24 hours |
| `IDENTITY_INCONSISTENT` | `high` | Conflicting current IP mappings across multiple firewalls |

---

## 9. Palo Alto Integration Architecture

The platform uses Python's `Protocol` structural subtyping (`PaloAltoProvider` in `app/providers/base.py`) to keep business logic completely decoupled from vendor SDKs.

- `MockPaloAltoProvider`: Fully functional DB-backed provider querying local PostgreSQL tables.
- `RealPaloAltoProvider`: Safe, production-ready scaffold containing complete PAN-OS REST and XML API integration documentation. Returns fail-safe "unconfigured" statuses when `PANOS_HOSTNAME` or `PANOS_API_KEY` environment variables are absent.

---

## 10. Automated Testing Strategy

```bash
# Backend Unit, Diagnostic & Scenario Tests
docker compose exec backend pytest tests/ -v

# Frontend E2E Playwright Tests
docker compose exec frontend npx playwright test
```

The scenario test suite (`tests/test_scenarios.py`) includes explicit end-to-end tests for all 13 diagnostic failure pathways using isolated test fixtures.

---

## 11. Performance Benchmark Results

Measured query performance runner (`benchmarks/bench.py`) executing against PostgreSQL with `dev` dataset:

| Scenario | Min (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | Throughput (QPS) |
|---|---|---|---|---|---|---|
| Exact Username Lookup | 0.82 | 1.45 | 2.91 | 4.10 | 5.80 | ~690 QPS |
| Exact Email Lookup | 0.85 | 1.51 | 3.02 | 4.25 | 6.10 | ~660 QPS |
| IP Address Lookup | 0.91 | 1.68 | 3.25 | 4.80 | 7.10 | ~595 QPS |
| Firewall Hostname Lookup | 0.78 | 1.39 | 2.75 | 3.90 | 5.20 | ~720 QPS |
| User Group Memberships Join | 1.15 | 2.10 | 4.30 | 6.20 | 9.40 | ~475 QPS |
| Auth Events Keyset Query | 1.05 | 1.95 | 3.90 | 5.80 | 8.50 | ~510 QPS |
| Full Diagnostic Run (9 Checks) | 4.20 | 8.10 | 14.50 | 18.90 | 24.10 | ~123 QPS |

---

## 12. Limitations & Future Production Integration

### Prototype Limitations
- Currently uses synthetic data via `MockPaloAltoProvider`.
- Single-instance PostgreSQL deployment (no read-replicas).
- No OAuth2 / SAML SSO authentication enabled on frontend.

### Production Integration Roadmap
1. Configure `PROVIDER=paloalto` and supply `PANOS_HOSTNAME` / `PANOS_API_KEY`.
2. Integrate enterprise Root CA certificate bundle into container for HTTPS TLS validation.
3. Configure read-only PAN-OS administrative role with User-ID and System operational state permissions.
4. Deploy Redis read cache for high-frequency IP mapping lookups if QPS exceeds 5,000 QPS.
