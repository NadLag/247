# PropStack - Multi-Tenant Property & Hospitality Management SaaS

## Original Problem Statement
Multi-tenant Property & Hospitality Management SaaS with Google OAuth, RBAC (Admin/Owner/Staff), KPI Dashboard, Properties/Staff/Expenses/Bookings modules, Invitations system, Stripe subscription, dark/light mode.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (async MongoDB) (port 8001)
- **Database**: MongoDB with company_id row-level isolation
- **Auth**: Emergent Google OAuth with session cookies in MongoDB
- **Payments**: Stripe via emergentintegrations library
- **Theme**: Dark/Light toggle with CSS variables (Deep Harbor palette)

## User Personas
1. **Company Admin** - Full CRUD on all modules, billing, invitations, staff management
2. **Owner** - View-only access to revenue, expenses, properties (their own), reports
3. **Staff** - View assigned properties, tasks, earnings, payout status

## Core Requirements
- Multi-tenant with strict company_id isolation on all queries
- Role-based access control middleware
- Session-based auth with httpOnly cookies
- Modular auth layer (ready for JWT migration)
- Stripe subscription (Starter $29, Professional $79, Enterprise $199)

## What's Been Implemented (Feb 21, 2026)
- [x] Landing page with hero, features, CTAs
- [x] Google OAuth authentication (Emergent Auth)
- [x] Company setup flow for new users
- [x] Admin Dashboard with 8 KPIs + revenue trends chart
- [x] Properties CRUD (cards with owner details, units, status)
- [x] Staff CRUD (table with salary, assignments, status)
- [x] Expenses CRUD (fixed/variable tabs, property filter, recurring)
- [x] Bookings CRUD (table with status management)
- [x] Invitations system (create, copy link, validate, accept)
- [x] Stripe subscription integration (3 plans, checkout, polling)
- [x] Settings page (profile, company info, security)
- [x] Dark/Light mode toggle
- [x] Responsive sidebar navigation with role-based items
- [x] Demo data seeding endpoint
- [x] MongoDB indexes for performance
- [x] **Owner-specific dashboard view** (filtered by their properties)
- [x] **Staff dashboard view** (earnings, tasks completed, upcoming tasks)
- [x] **OTA Sync webhook endpoint** + background processor
- [x] **Subscription status validation middleware** (auto-lock inactive)

## Test Results (Feb 21, 2026 - Latest)
- Backend: 100% (17/17 new feature tests passed)
- Frontend: 100% (All role-based dashboard views verified)
- Integration: 100% (auth, CRUD, role-based KPIs, OTA webhook, subscription middleware)

## New Features Added (Feb 21, 2026)

### 1. Role-Based Dashboards
- **Admin View**: All 8 KPIs (revenue, net income, occupancy, nights, ADR, RevPAN, properties, bookings), revenue trends chart, staff payments due card
- **Owner View**: Filtered KPIs for owned properties only, owner-specific revenue trends, role badge
- **Staff View**: Staff earnings (MTD), tasks completed, upcoming tasks (7 days), assigned properties, active bookings, upcoming work list

### 2. OTA Sync Webhook
- **Endpoint**: `POST /api/ota-webhook/{company_id}`
- **Events**: booking_created, booking_updated, booking_cancelled, availability_sync
- **Features**: Background processing, sync logging, external_id tracking for OTA bookings
- **Logs Endpoint**: `GET /api/ota-sync-logs` with filters for status and source

### 3. Subscription Middleware
- **Validates** subscription status on all API requests
- **Trial/Active**: Allow all operations
- **Inactive/Cancelled**: Block POST/PUT/DELETE with 402 error, allow GET
- **Exempt paths**: /api/auth/, /api/subscription/, /api/companies/, /api/webhook/

## Prioritized Backlog
### P0 (Next - User Requested)
- Redesign Bookings Page into status sections (Checked-in Today, Upcoming, Confirmed, Checked-out, Cancelled)
- Create Services Page (Airport Transfer, Meals, Excursions with staff/provider assignment)
- Create Analytics Page (earnings/performance graphs, filterable by month/year/property)

### P1
- JWT authentication migration (Phase 2)
- Audit logs for all CRUD operations
- Download reports (PDF/CSV)

### P2
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
- CSRF protection + rate limiting

## Key API Endpoints
### Dashboard
- `GET /api/dashboard/kpis` - Role-aware KPIs
- `GET /api/dashboard/revenue-trends` - 6-month trend data

### OTA Integration
- `POST /api/ota-webhook/{company_id}` - Receive OTA events
- `GET /api/ota-sync-logs` - List sync logs with filters

### Core CRUD
- Properties, Staff, Bookings, Expenses, Invitations (all support GET, POST, PUT, DELETE)

## Database Collections
- users, companies, user_sessions
- properties, staff, bookings, expenses, invitations
- payment_transactions, ota_sync_logs
