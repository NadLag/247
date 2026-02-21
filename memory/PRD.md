# PropStack - Multi-Tenant Property & Hospitality Management SaaS

## Original Problem Statement
Multi-tenant Property & Hospitality Management SaaS with Google OAuth, RBAC (Admin/Owner/Staff), KPI Dashboard, Properties/Staff/Expenses/Bookings modules, Invitations system, Stripe subscription, dark/light mode.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (async MongoDB) (port 8001)
- **Database**: MongoDB with company_id row-level isolation
- **Auth**: Emergent Google OAuth with session cookies in MongoDB
- **Payments**: Stripe via emergentintegrations library
- **Email**: Resend for invitation emails
- **Theme**: Dark/Light toggle with CSS variables (Deep Harbor palette)

## User Personas
1. **Company Admin** - Full CRUD on all modules, billing, invitations, staff management
2. **Owner** - View-only access to revenue, expenses, properties (their own), reports
3. **Staff** - View assigned properties, tasks, earnings, payout status

## What's Been Implemented (Feb 21, 2026)

### Core Features
- [x] Landing page with hero, features, CTAs
- [x] Google OAuth authentication (Emergent Auth)
- [x] Company setup flow for new users
- [x] Admin Dashboard with 8 KPIs + revenue trends chart
- [x] Properties CRUD (cards with owner details, units, status)
- [x] Staff CRUD (table with salary, assignments, status)
- [x] Expenses CRUD (fixed/variable tabs, property filter, recurring)
- [x] Bookings CRUD (status tabs: Checked-in, Upcoming, Confirmed, Checked-out, Cancelled)
- [x] Services CRUD (add-on services with staff/external provider assignment)
- [x] Analytics page (KPIs, trends, filters by property/month/year)
- [x] Invitations system with email sending via Resend
- [x] Stripe subscription integration (3 plans, checkout, polling)
- [x] Dark/Light mode toggle
- [x] Responsive sidebar navigation with role-based items

### Role-Based Features
- [x] Owner-specific dashboard view (filtered by their properties)
- [x] Staff dashboard view (earnings, tasks completed, upcoming tasks)
- [x] OTA Sync webhook endpoint + background processor
- [x] Subscription status validation middleware (auto-lock inactive)

### OTA Integration (MOCKED)
- [x] Mock OTA simulation for Airbnb, Booking.com, VRBO, Expedia
- [x] "Sync All OTA" button on Properties page
- [x] "Sync OTA" button on each property card
- [x] "Sync OTA" button on Bookings page
- [x] OTA source badges displayed on synced bookings
- [x] OTA sync logs tracking

### Invitation Email System
- [x] Resend email integration for invitations
- [x] Beautiful HTML email template with PropStack branding
- [x] Email status tracking (email_sent field)
- [x] Resend email button for pending invitations
- [x] Background task processing for email sending

## Test Results (Feb 21, 2026 - Latest)
- Backend: 100% (14/14 tests passed)
- Frontend: 100% (All UI features verified)

## OTA Mock Simulation Details
The OTA sync is **MOCKED** for testing/demo purposes:
- Generates fake bookings from Airbnb, Booking.com, VRBO, Expedia
- Creates realistic guest names, dates (1-30 days out), and amounts ($100-$350/night)
- Each sync creates 0-3 bookings per property
- Bookings include `ota_source` and `ota_external_id` fields

To connect real OTAs, you would need:
- Enterprise partnership agreements with Airbnb/Booking.com
- Official API credentials (requires certification)
- Or use iCal sync (supported by all OTAs without partnership)

## Email Integration Details
- **Service**: Resend
- **Current Key**: Test key (re_123456789) - emails not actually delivered
- **To enable real emails**: Replace with production Resend API key in backend/.env

## Key API Endpoints

### OTA Simulation
- `POST /api/ota/simulate-sync` - Simulate OTA sync for all properties
- `POST /api/ota/simulate-property-sync/{property_id}` - Sync specific property
- `GET /api/ota-sync-logs` - List sync logs with filters

### Invitation Emails
- `POST /api/invitations` - Create invitation (sends email automatically)
- `POST /api/invitations/{id}/resend` - Resend invitation email
- `GET /api/invitations` - List invitations with email_sent status

### Bookings
- `GET /api/bookings/by-status` - Bookings grouped by status tabs

## Navigation Structure
### Admin Sidebar
1. Dashboard
2. Properties (with OTA Sync)
3. Staff
4. Bookings (with OTA Sync)
5. Services
6. Expenses
7. Analytics
8. Invitations (with Email)
9. Billing
10. Settings

## Prioritized Backlog

### P1 (Next)
- Real OTA iCal integration (no partnership needed)
- Production Resend API key for real emails
- JWT authentication migration

### P2
- Audit logs for CRUD operations
- Download reports (PDF/CSV)
- AI revenue forecasting
- Multi-currency support

### P3
- Multi-language
- Automated owner payouts
- Smart expense categorization
- CSRF protection + rate limiting

## Database Collections
- users, companies, user_sessions
- properties, staff, bookings, expenses, invitations
- payment_transactions, ota_sync_logs
- services, booking_services

## Environment Variables
```
# Backend (.env)
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
STRIPE_API_KEY=sk_test_emergent
RESEND_API_KEY=re_123456789  # Replace with production key
SENDER_EMAIL=onboarding@resend.dev
```
