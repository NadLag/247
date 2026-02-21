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

### Core Features
- [x] Landing page with hero, features, CTAs
- [x] Google OAuth authentication (Emergent Auth)
- [x] Company setup flow for new users
- [x] Admin Dashboard with 8 KPIs + revenue trends chart
- [x] Properties CRUD (cards with owner details, units, status)
- [x] Staff CRUD (table with salary, assignments, status)
- [x] Expenses CRUD (fixed/variable tabs, property filter, recurring)
- [x] Invitations system (create, copy link, validate, accept)
- [x] Stripe subscription integration (3 plans, checkout, polling)
- [x] Settings page (profile, company info, security)
- [x] Dark/Light mode toggle
- [x] Responsive sidebar navigation with role-based items
- [x] Demo data seeding endpoint
- [x] MongoDB indexes for performance

### Role-Based Features
- [x] Owner-specific dashboard view (filtered by their properties)
- [x] Staff dashboard view (earnings, tasks completed, upcoming tasks)
- [x] OTA Sync webhook endpoint + background processor
- [x] Subscription status validation middleware (auto-lock inactive)

### New Features (Latest)
- [x] **Bookings Page Redesign** - Split into 5 status tabs (Checked-in Today, Upcoming, Confirmed, Checked-out, Cancelled)
- [x] **OTA Sync Button** - Manual sync trigger on bookings page
- [x] **Services Page** - CRUD for add-on services with categories and provider assignment
- [x] **Analytics Page** - Comprehensive analytics with KPIs, filters, and charts

## Test Results (Feb 21, 2026 - Latest)
- Backend: 100% (18/18 new feature tests passed)
- Frontend: 100% (All features verified via Playwright)
- Integration: 100% (all modules working correctly)

## Feature Details

### Bookings Page Redesign
- **Status Tabs**: Checked-in Today, Upcoming, Confirmed, Checked-out, Cancelled
- **Endpoint**: `GET /api/bookings/by-status` - returns bookings grouped by status
- **OTA Sync**: Button to refresh bookings from external OTAs
- **OTA Badge**: Shows source for OTA-synced bookings

### Services Page
- **Categories**: Airport Transfer, Meals, Excursions, Spa, Transportation, Other
- **Provider Types**: 
  - Internal (assign to staff member)
  - External (third-party with name, phone, email)
- **Price Types**: Fixed, Per Person, Per Hour
- **Endpoints**: Full CRUD at `/api/services`
- **Booking Services**: Add services to bookings via `/api/booking-services`

### Analytics Page
- **KPIs**: Revenue MTD, Net Income, Occupancy Rate, Nights Booked, ADR, RevPAN, Active Properties, Total Bookings
- **Comparisons**: Current vs previous month with percentage changes
- **Filters**: Property, Month, Year
- **Charts**: 
  - Revenue & Expenses Trend (12 months)
  - Occupancy Rate Trend
  - ADR Trend
  - Nights Booked vs Total Bookings
- **Endpoint**: `GET /api/analytics?property_id=&year=&month=`

## Navigation Structure
### Admin Sidebar
1. Dashboard
2. Properties
3. Staff
4. Bookings
5. Services
6. Expenses
7. Analytics
8. Invitations
9. Billing
10. Settings

### Owner Sidebar
1. Dashboard
2. Properties
3. Analytics
4. Settings

### Staff Sidebar
1. Dashboard
2. Bookings
3. Settings

## Prioritized Backlog

### P1 (Next)
- JWT authentication migration (Phase 2)
- Audit logs for all CRUD operations
- Download reports (PDF/CSV)
- Real OTA integration (Airbnb, Booking.com, VRBO APIs)

### P2
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
- CSRF protection + rate limiting
- Email notifications for OTA syncs

## Database Collections
- users, companies, user_sessions
- properties, staff, bookings, expenses, invitations
- payment_transactions, ota_sync_logs
- services, booking_services

## Key API Endpoints

### Bookings
- `GET /api/bookings` - List all bookings
- `GET /api/bookings/by-status` - Bookings grouped by status
- `POST /api/bookings` - Create booking
- `PUT /api/bookings/{id}` - Update booking

### Services
- `GET /api/services` - List services (with category filter)
- `POST /api/services` - Create service
- `PUT /api/services/{id}` - Update service
- `DELETE /api/services/{id}` - Delete service
- `GET /api/booking-services/{booking_id}` - Get services for a booking
- `POST /api/booking-services` - Add service to booking

### Analytics
- `GET /api/analytics?property_id=&year=&month=` - Get comprehensive analytics

### OTA Integration
- `POST /api/ota-webhook/{company_id}` - Receive OTA events
- `GET /api/ota-sync-logs` - List sync logs
