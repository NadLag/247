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

## Test Results
- Backend: 98% (34/35 tests passed)
- Frontend: 100% (18/18 UI features)
- Integration: 100% (auth, CRUD, navigation)

## Prioritized Backlog
### P0 (Next)
- Owner-specific dashboard view (filtered by their properties)
- Staff dashboard view (tasks, earnings, payout status)
- OTA Sync webhook endpoint + background processor

### P1
- JWT authentication migration (Phase 2)
- Subscription status validation middleware (auto-lock inactive)
- Audit logs for all CRUD operations
- Download reports (PDF/CSV)

### P2
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
- CSRF protection + rate limiting
