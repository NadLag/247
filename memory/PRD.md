# PropStack - Multi-Tenant Property & Hospitality Management SaaS

## Original Problem Statement
Multi-tenant Property & Hospitality Management SaaS with Google OAuth, RBAC (Admin/Owner/Staff), KPI Dashboard, Properties/Staff/Expenses/Bookings modules, Invitations system, Stripe subscription, dark/light mode.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (async MongoDB) (port 8001)
- **Database**: MongoDB with company_id row-level isolation
- **Auth**: Dual auth - Google OAuth + Password-based registration
- **Payments**: Stripe via emergentintegrations library
- **Email**: Resend for invitation emails
- **Theme**: Teal-based minimalist design with dark/light toggle

## Color Scheme (Warm Modern Teal)
- Primary: `#0D9488` (HSL 168 76% 32%)
- Background: `#F9FAFB` (Off-white)
- Text: `#111827` (Near-black)

## User Personas
1. **Company Admin** - Full CRUD on all modules, billing, invitations, staff/task management
2. **Owner** - View-only access to their properties' revenue, expenses, bookings, analytics
3. **Staff** - Tasks management, assigned properties, earnings tracking, payout status

## What's Been Implemented (Feb 22, 2026)

### Core Features
- [x] Landing page with hero, features, CTAs
- [x] **Dual Authentication** - Google OAuth + Password-based login
- [x] **Invitation-Based Registration** - Read-only info (Name, Email, Role, Company) + password setup
- [x] Company setup flow for new users
- [x] Admin Dashboard with 8 KPIs + revenue trends chart
- [x] **Role-Specific Dashboards** (Admin/Owner/Staff views)
- [x] Properties CRUD (6-column grid, Quick View, OTA import)
- [x] Staff CRUD (table with salary, assignments, status)
- [x] **Tasks CRUD** (full task management with assignments)
- [x] Expenses CRUD (fixed/variable tabs, property filter, recurring)
- [x] **Bookings - Calendar + List views** with filters
- [x] Services CRUD (add-on services with staff/external provider assignment)
- [x] Analytics page (KPIs, trends, filters by property/month/year)
- [x] Invitations system with Resend email integration
- [x] Stripe subscription integration (3 plans)
- [x] Dark/Light mode toggle
- [x] Responsive sidebar navigation with role-based items
- [x] **"Hey, {FirstName}" greeting** in header
- [x] **Audit logging** for account activation and logins

### Authentication System
- [x] Google OAuth (Emergent Auth)
- [x] Password-based registration via invitation links
- [x] Password login with bcrypt hashing
- [x] Session management with 7-day cookie expiry
- [x] Both auth methods supported for invited users

### Invitation Registration Flow (Fixed Feb 22, 2026)
1. Admin creates invitation for Staff/Owner → email sent via Resend
2. Invitee clicks link → `/invite/{token}` page loads
3. Page shows **read-only** fields: Name, Email, Role, Company (pre-filled from staff/property records)
4. User only needs to: Create Password OR Continue with Google
5. Upon success → redirected to role-specific dashboard

### Role-Based Features
- **Admin**: Full access to all modules, Tasks, Invitations, Staff management
- **Owner (View-Only)**: Properties, Bookings, Analytics (filtered to their properties)
- **Staff**: Tasks, Bookings, Earnings, Dashboard with work summary

### Tasks Module
- Task types: Cleaning, Maintenance, Check-in, Check-out, Admin, General
- Priorities: Low, Medium, High, Urgent
- Status workflow: Pending → In Progress → Completed → Cancelled
- Staff can only update their own tasks' status
- Admin can create, edit, delete, assign tasks
- Task summary cards for staff (Pending, In Progress, Completed MTD)

### OTA iCal Sync (Updated Feb 22, 2026)
- [x] **Unified "Add Property" button** with choice modal:
  - **Sync from OTA** - Creates NEW property from iCal URL, imports bookings, opens edit dialog
  - **Add Manually** - Traditional property form
- [x] **"Refresh" button** (renamed from "Sync from OTA") - refreshes all OTA feeds
- [x] iCal parser with `icalendar` library
- [x] Mock URL format for testing: `mock://source/PropertyName`
- [x] Background job processing with sync status polling
- [x] Duplicate detection by UID or (property + date range + OTA source)
- [x] OTA source badges on Bookings page

### Properties Page (Updated Feb 22, 2026)
- [x] **6-column grid** (desktop) → 4 columns (lg) → 3 columns (md) → 2 columns (sm) → 1 column (mobile)
- [x] Compact property cards: Name, Address, Owner, Status, Last Sync
- [x] **Quick View** popup with property details
- [x] Single "Add Property" button with Sync/Manual choice

### Bookings Page (Updated Feb 22, 2026)
- [x] **Calendar View** (default) - Airbnb-style monthly grid
- [x] **List View** - Sortable/filterable table
- [x] Color-coded bookings (Teal=Confirmed, Blue=CheckedIn, Grey=CheckedOut, Red=Cancelled)
- [x] Property and Status filters
- [x] Click booking → details popup with Edit option

## Test Results (Feb 22, 2026 - Latest)
- Frontend: 100% (10/10 UI features verified)
- Properties grid: 6 columns working
- Bookings Calendar/List: Both views functional
- Color theme: Teal (HSL 168 76% 32%) applied

## API Endpoints

### Authentication
- `POST /api/auth/register-with-invite` - Password registration via invitation
- `POST /api/auth/login` - Email/password login
- `GET /api/auth/google` - Google OAuth initiation
- `GET /api/auth/me` - Current user info
- `POST /api/auth/logout` - Logout

### Tasks
- `GET /api/tasks` - List tasks (role-filtered)
- `POST /api/tasks` - Create task (admin only)
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task (admin only)
- `GET /api/tasks/my-summary` - Staff task summary

### Staff Earnings
- `GET /api/staff/my-earnings` - Staff earnings data

### OTA iCal Sync
- `POST /api/ota/import-property` - **NEW**: Create property from iCal URL + import bookings
- `GET /api/ota/feeds` - List all OTA feeds
- `POST /api/ota/feeds` - Add new OTA feed (property_id, source, ical_url)
- `PUT /api/ota/feeds/{id}` - Update feed (source, ical_url, active)
- `DELETE /api/ota/feeds/{id}` - Delete feed
- `POST /api/ota/sync` - Trigger background sync for all feeds
- `GET /api/ota/sync-status` - Get current sync status (is_syncing, feeds_count, latest_sync)
- `GET /api/ota-sync-logs` - List sync logs with stats

### Properties
- `GET /api/properties` - List all properties
- `POST /api/properties` - Create property manually
- `GET /api/properties/{id}` - **NEW**: Get single property by ID
- `PUT /api/properties/{id}` - Update property
- `DELETE /api/properties/{id}` - Delete property

## Navigation by Role

### Admin Sidebar
Dashboard, Properties, Staff, Bookings, Tasks, Services, Expenses, Analytics, OTA Settings, Invitations, Billing, Settings

### Owner Sidebar
Dashboard, Properties, Bookings, Analytics, Settings

### Staff Sidebar
Dashboard, Tasks, Bookings, Settings

## Database Collections
- users (with password_hash, auth_method, first_name, last_name)
- companies, user_sessions
- properties (with last_ota_sync_at), staff, bookings (with ota_source, ota_external_id, ota_feed_id), expenses, invitations
- tasks (with assigned_staff_id, status, priority, task_type)
- services, booking_services
- payment_transactions, ota_sync_logs, ota_feeds
- audit_logs (account_activated, login events)
- payouts

## Environment Variables
```
# Backend (.env)
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
STRIPE_API_KEY=sk_test_emergent
RESEND_API_KEY=re_123456789
SENDER_EMAIL=onboarding@resend.dev
```

## Prioritized Backlog

### P1 (Next)
- Real OTA iCal URLs (replace mock:// with real Airbnb/Booking.com URLs)
- Production Resend API key for real emails
- Staff payout tracking and history
- Owner financial reports (PDF/CSV export)

### P2
- JWT authentication migration
- Audit logs viewer in admin panel
- Booking calendar view for owners
- Task notifications for staff

### P3
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
