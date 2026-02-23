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

### UI/UX Enhancements (Feb 22, 2026)
- [x] **Premium animations** - Fade-in, slide-in, scale-in transitions
- [x] **Staggered list animations** - Cards animate in sequence
- [x] **Hover lift effects** - Cards elevate on hover
- [x] **Glass morphism** - Subtle backdrop blur on sidebar/header
- [x] **Improved scrollbars** - Custom styled, theme-aware
- [x] **Better focus states** - Accessible ring styling
- [x] **Dark mode polish** - Consistent colors across all components
- [x] **Icon color consistency** - Primary color accents on icons
- [x] **Removed OTA Settings page** - Consolidated into Properties

### Blocked Dates Handling (Feb 22, 2026) - CRITICAL FIX
- [x] **Proper Data Model** - `booking_type` field: `reservation` | `blocked`
- [x] **Blocked dates NOT shown in Bookings list** - API filters them out by default
- [x] **Blocked dates ONLY in Calendar view** - Grey strikethrough styling, "Unavailable" label
- [x] **No fake "Blocked" guest name** - `guest_name: null` for blocked entries
- [x] **KPIs exclude blocked dates** - No impact on revenue, ADR, RevPAN, occupancy
- [x] **Manual booking override flow** - 409 conflict → confirmation dialog → audit log
- [x] **Separate API endpoint** - `GET /api/bookings/blocked-dates` for calendar
- [x] **Database migration** - Auto-converts `guest_name: "Blocked"` to proper blocked type

### Registration "User Already Exists" Fix (Feb 23, 2026)
- [x] **Existing user registration** - When invited user already exists (registered via Google OAuth), registration now updates their role, assigned_properties, and permissions from invitation instead of failing with "User already exists"
- [x] **Subscription middleware** - Added `/api/invitations/` and `/api/notifications/` to exempt paths so invitation management works without active subscription
- [x] **Resend free tier limitation** - Documented: Resend testing mode only allows sending to account owner email (nadir.lagnadi@gmail.com). Need to verify a domain at resend.com/domains for production. Copy-link fallback works in the meantime.

### CRITICAL FIX: Owner OAuth Registration & Property Assignment (Feb 23, 2026)
- [x] **Google OAuth invitation flow** - Fixed: InviteAccept.js now stores invitation_token in sessionStorage before redirecting to Emergent Auth, AuthCallback.js retrieves and sends to backend
- [x] **Existing user OAuth linking** - Fixed: exchange_session now checks for valid invitations BEFORE handling existing user logic, updates company_id, role, and assigned_properties for existing users
- [x] **New OAuth user properties** - Fixed: New users created via OAuth now get assigned_properties from invitation (was missing before)
- [x] **Role-based property filtering** - Fixed: Dashboard KPIs, properties list, bookings list, and revenue trends all use user.assigned_properties for owner/staff role filtering
- [x] **Owner dashboard data** - Fixed: Owners now see correct property data, bookings, and financial KPIs for their assigned properties (was showing $0 before)

### Email Delivery & Invitation Registration Fix (Feb 23, 2026)
- [x] **Email from address** - Fixed: uses `onboarding@resend.dev` for Gmail/Yahoo/Hotmail senders (Resend free-tier requirement). User's email set as reply-to.
- [x] **Invite link URL** - Fixed: uses `FRONTEND_URL` env var instead of internal `request.base_url` which was generating broken links
- [x] **Token validation** - Properly checks cancelled/expired status with clear error messages (404 invalid, 400 cancelled/expired)
- [x] **Registration flow** - Full form with first_name, last_name, phone, password. Google OAuth option. Checks cancelled tokens before registration
- [x] **Error screens** - InviteAccept page shows proper error screens: expired (with reasons list), cancelled, already used, invalid
- [x] **Email delivery logging** - Stores delivery status (sent/failed), provider response, and error in database. Visible in Invite page table
- [x] **User assigned_properties** - Registration now stores assigned_properties and permissions from invitation on the new user record

### Production Email, Staff Payouts & Owner Reports (Feb 23, 2026)
- [x] **Production Resend API** - Configured with production API key and verified sender email (nadir.lagnadi@gmail.com). Invitation emails now deliver for real.
- [x] **Staff Payouts** - Full CRUD: create/read/update/delete payouts. Staff page now has "Staff Members" and "Payouts" tabs. Payout fields: staff, property, period, task, amount, payment method, status (pending/paid). Summary cards show total/pending/paid amounts. Mark as Paid auto-sets payment_date.
- [x] **Owner Financial Reports** - New `/reports` page accessible to admins and owners. Per-property breakdown: bookings, occupancy, gross revenue (by channel), expenses, net profit, owner share %, payout amount & status. Revenue vs Expenses bar chart, Revenue by Channel pie chart. CSV export. Filters by property, month, year.

### Unified Invite Page & Collapsible Sidebar (Feb 23, 2026)
- [x] **Unified Invite page** - Centralized page for all invitation management (owners & staff). Renamed sidebar item from "Invitations" to "Invite"
- [x] **Enhanced invite form** - Role selection, person picker (from existing staff/owners), name, email, property multi-select, staff permissions (view financials, manage bookings, manage tasks)
- [x] **Enhanced table** - Columns: Name, Email, Role, Properties, Status, Sent, Expires, Actions
- [x] **Status filter tabs** - All, Pending, Accepted, Expired, Cancelled with count badges. Status auto-computed from expiry/used/cancelled state
- [x] **Resend logic** - Invalidates old token, generates new token, new 48h expiry, sends new email
- [x] **Cancel invitation** - Sets status to cancelled, invalidates token
- [x] **Collapsible sidebar** - Toggle button to collapse/expand sidebar (60px collapsed, 240px expanded). Shows only icons when collapsed. State persisted in localStorage
- [x] **Role-based user creation** - Accepted invitations store assigned_properties and permissions on user record

### Missing Booking Details Notification System (Feb 23, 2026)
- [x] **is_data_complete flag** - Every booking has `is_data_complete` field. Auto-calculated on create/update. Migration sets it for all existing bookings
- [x] **Notification system** - `notifications` collection with full CRUD: GET /api/notifications, GET /api/notifications/unread-count, PUT /api/notifications/{id}/read, PUT /api/notifications/read-all
- [x] **Auto-detection** - After iCal sync (new property sync, manual sync, background sync), system detects incomplete bookings (missing guest name/amount) and creates notifications
- [x] **Notification bell** - Header bell icon with unread badge counter, dropdown panel with "Review Bookings" action link
- [x] **Incomplete filter** - Bookings page has "Incomplete" toggle button. URL param `?filter=incomplete` auto-activates it and switches to list view
- [x] **Warning indicators** - Incomplete rows have yellow highlight, warning icons, and inline messages ("Guest name required", "Amount required")
- [x] **Edit & auto-resolve** - Editing a booking to add missing data auto-recalculates `is_data_complete`. When all incomplete bookings are fixed, notification auto-resolves
- [x] **Revenue protection** - Incomplete bookings (amount=0/missing) excluded from revenue KPIs and ADR calculations

### Booking Logic & UI Enhancements (Feb 22, 2026)
- [x] **Auto-checkout status** - Expired bookings auto-update to `checked_out` on startup, hourly, and on every bookings list fetch
- [x] **Past-date validation** - Backend rejects manual bookings with check-in OR check-out in the past (400 error). Frontend date inputs have `min` attribute set to today for new bookings
- [x] **iCal source tracking** - `ota_source` field consistently used: `manual` for direct bookings, platform name (e.g., `airbnb`) for iCal imports
- [x] **Source filter dropdown** - Bookings list view has Source filter with options from `/api/bookings/sources`
- [x] **Source display in table** - New "Source" column with colored badges (green for Direct, blue for OTA). Booking detail popup always shows source
- [x] **Source breakdown analytics** - New `GET /api/analytics/source-breakdown` endpoint. Two pie charts on Analytics page: "Bookings by Source" and "Revenue by Source" with percentages and values

### Bookings Page Fixes (Feb 22, 2026)
- [x] **Property filter fix** - Properly handles "all" and specific property selections
- [x] **Missing property recovery** - Auto-created missing OTA-synced property
- [x] **iCal import indicators** - Shows "via iCal sync" for imported bookings
- [x] **Amount display improvement** - Shows "Not in iCal" for missing pricing data
- [x] **Null-safe sorting** - Handles null guest names in sort

### Authentication System
- [x] Google OAuth (Emergent Auth)
- [x] Password-based registration via invitation links
- [x] Password login with bcrypt hashing
- [x] Session management with 7-day cookie expiry
- [x] Both auth methods supported for invited users

### OTA iCal Sync
- [x] Unified "Add Property" button with choice modal
- [x] "Refresh" button for syncing all OTA feeds
- [x] iCal parser with `icalendar` library
- [x] Blocked dates vs confirmed bookings handling
- [x] Background job processing with sync status polling

## Navigation by Role

### Admin Sidebar
Dashboard, Properties, Bookings, Staff, Tasks, Expenses, Services, Analytics, Invitations, Billing, Settings

### Owner Sidebar
Dashboard, Properties, Bookings, Analytics, Settings

### Staff Sidebar
Dashboard, Tasks, Bookings, Settings

## Database Collections
- users, companies, user_sessions
- properties, staff, bookings, expenses, invitations
- tasks, services, booking_services
- payment_transactions, ota_sync_logs, ota_feeds
- audit_logs, payouts

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
- Real OTA API integrations (Airbnb, Booking.com)
- PDF export for owner reports
- Backend refactoring - Split server.py into modular routes/models/services

### P2
- JWT authentication migration
- Audit logs viewer in admin panel
- Task notifications for staff

### P3
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
